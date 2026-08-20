import os
import json
import time
import requests

from binaryninja import (
    Settings, log_info, log_error, user_directory, show_message_box
)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel,
    QWidget, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QSplitter
)
from PySide6.QtCore import (
    Qt, QUrl, QDir, QFile, QIODevice, QObject, QRunnable, QThreadPool,
    Signal, Slot
)
from PySide6.QtGui import QDesktopServices

from .theme_colors import ThemeColorResolver
from .preview_widget import LinearPreview, GraphPreview

# -----------------------------
# CONFIG
# -----------------------------
REPOS = [
    ("Vector35", "community-themes", ""),
    ("catppuccin", "binary-ninja", "themes"),
    ("dracula", "binary-ninja", "theme"),
    ("evanrichter", "base16-binary-ninja", "colors"),
    ("FuzzySecurity", "BinaryNinja-Themes", ""),
]

ISSUES_URL = "https://github.com/psifertex/Swatch/issues/new"

# GLOBAL MEMORY CACHE (To avoid GitHub Rate Limits)
# Structure: {(owner, repo, path): [themes]}
SESSION_REMOTE_CACHE = {}

REMOTE_TEXT_CACHE = {}

# A failed fetch is remembered too, so a search keystroke doesn't re-hit every
# repo (and burn the 60/hr unauthenticated rate limit) while blocking the UI.
FAILED_FETCH_TIMES = {}
FETCH_RETRY_SECONDS = 60

NO_USER_DIR_MSG = ("Binary Ninja's user directory could not be determined, so "
                   "there is nowhere to install themes.")

def theme_dir():
    """Where themes live, or None if BN's user directory is unavailable.

    Resolved lazily rather than at import time: user_directory() returns None
    outside a running core, and caching that would poison the whole session.
    """
    base = user_directory()
    if not base:
        return None
    return os.path.join(base, "community-themes")

def ensure_dirs():
    """Create and return the theme directory, or None if it can't be located."""
    path = theme_dir()
    if path is None:
        log_error(f"[Swatch] {NO_USER_DIR_MSG}")
        return None
    os.makedirs(path, exist_ok=True)
    return path

# -----------------------------
# THEME UTILS
# -----------------------------
DISPLAY_NAME_CACHE = {}

def get_theme_display_name(theme_filename):
    """Reads the JSON inside the .bntheme to get the actual UI name."""
    base = theme_dir()
    if base is None:
        return theme_filename
    theme_path = os.path.join(base, theme_filename)
    if not os.path.exists(theme_path):
        return theme_filename
    try:
        key = (theme_path, os.path.getmtime(theme_path))
    except OSError:
        key = None
    if key is not None and key in DISPLAY_NAME_CACHE:
        return DISPLAY_NAME_CACHE[key]
    try:
        with open(theme_path, "r", encoding="utf-8") as f:
            name = json.load(f).get("name", theme_filename)
        if key is not None:
            DISPLAY_NAME_CACHE[key] = name
        return name
    except Exception as e:
        log_error(f"[Swatch] Could not read {theme_filename}: {e}")
        return theme_filename

def get_locally_installed_files():
    base = ensure_dirs()
    if base is None:
        return []
    return [f for f in os.listdir(base) if f.endswith(".bntheme")]

def load_local_theme_json(theme_filename):
    """Parse an installed .bntheme into a dict (None on failure)."""
    base = theme_dir()
    if base is None:
        return None
    theme_path = os.path.join(base, theme_filename)
    try:
        with open(theme_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"[Swatch] Could not read {theme_filename}: {e}")
        return None

def load_remote_theme_json(download_url):
    """Fetch (cached) and parse a remote .bntheme into a dict (None on failure)."""
    text = REMOTE_TEXT_CACHE.get(download_url)
    if text is None:
        try:
            text = requests.get(download_url, timeout=5).text
            REMOTE_TEXT_CACHE[download_url] = text
        except Exception as e:
            log_error(f"[Swatch] Preview fetch failed: {e}")
            return None
    try:
        return json.loads(text)
    except Exception as e:
        log_error(f"[Swatch] Could not parse remote theme: {e}")
        return None

# -----------------------------
# GITHUB FETCH (With caching)
# -----------------------------
def fetch_repo_themes(owner, repo, path=""):
    key = (owner, repo, path)
    if key in SESSION_REMOTE_CACHE:
        return SESSION_REMOTE_CACHE[key]

    failed_at = FAILED_FETCH_TIMES.get(key)
    if failed_at is not None and time.monotonic() - failed_at < FETCH_RETRY_SECONDS:
        return []

    log_info(f"[Swatch] Fetching remote: {owner}/{repo}")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            log_error(f"[Swatch] {owner}/{repo} returned HTTP {r.status_code}")
            FAILED_FETCH_TIMES[key] = time.monotonic()
            return []
        
        themes = []
        for f in r.json():
            if f["type"] == "file" and f["name"].endswith(".bntheme"):
                themes.append({"name": f["name"], "download_url": f["download_url"]})
        
        SESSION_REMOTE_CACHE[key] = themes
        FAILED_FETCH_TIMES.pop(key, None)
        return themes
    except Exception as e:
        log_error(f"[Swatch] Fetch error for {owner}/{repo}: {e}")
        FAILED_FETCH_TIMES[key] = time.monotonic()
        return []

def apply_theme(theme_filename):
    apply_theme_name(get_theme_display_name(theme_filename))

def apply_theme_name(display_name):
    """Activate a theme BN already knows by name."""
    try:
        from binaryninjaui import setActiveTheme
    except Exception:
        # No UI bindings available; persist the choice for the next launch.
        Settings().set_string("ui.theme.name", display_name)
        log_info(f"Applied: {display_name} (Restart required)")
        return
    # setActiveTheme saves to settings itself (saveToSettings defaults to true).
    try:
        setActiveTheme(display_name)
    except Exception as e:
        log_error(f"[Swatch] Could not apply {display_name}: {e}")
        return
    log_info(f"Applied: {display_name}")

# BN compiles its default themes in as Qt resources under this prefix and loads
# them with QDir(":/themes") itself, so we can read the same .bntheme JSON.
# Builds older than that ship nothing here and simply get no preview.
BUILTIN_THEME_RESOURCE_DIR = ":/themes"
_BUILTIN_THEME_DATA = None

def _read_builtin_themes():
    themes = {}
    for info in QDir(BUILTIN_THEME_RESOURCE_DIR).entryInfoList(
            QDir.Files | QDir.Readable, QDir.Name):
        f = QFile(info.absoluteFilePath())
        if not f.open(QIODevice.ReadOnly):
            continue
        try:
            data = json.loads(bytes(f.readAll()).decode("utf-8"))
        except Exception as e:
            log_error(f"[Swatch] Could not parse {info.fileName()}: {e}")
            continue
        finally:
            f.close()
        name = data.get("name")
        if name:
            themes[name] = data
    return themes

def builtin_theme_json(name):
    """The .bntheme BN bundles for a default theme, or None if unavailable."""
    global _BUILTIN_THEME_DATA
    if _BUILTIN_THEME_DATA is None:
        try:
            _BUILTIN_THEME_DATA = _read_builtin_themes()
        except Exception as e:
            log_error(f"[Swatch] Could not read bundled themes: {e}")
            _BUILTIN_THEME_DATA = {}
    return _BUILTIN_THEME_DATA.get(name)

def get_builtin_themes():
    """Themes BN ships itself: everything it knows, minus what we installed.

    These are compiled into Binary Ninja rather than stored as .bntheme files,
    so they can be activated but not previewed.
    """
    try:
        from binaryninjaui import getAvailableThemes
        available = [str(t) for t in getAvailableThemes()]
    except Exception as e:
        log_error(f"[Swatch] Could not list built-in themes: {e}")
        return []
    installed = {get_theme_display_name(f) for f in get_locally_installed_files()}
    return [t for t in available if t not in installed]

def download_theme(theme_obj):
    """Fetch a theme and write it to disk; returns the filename or None.

    Network and disk only, so this is safe to run off the UI thread. Callers
    must run refresh_installed_themes() on the UI thread afterwards.
    """
    base = ensure_dirs()
    if base is None:
        return None
    name = os.path.basename(theme_obj["name"])
    if not name.endswith(".bntheme"):
        log_error(f"[Swatch] Refusing to write unexpected file: {name}")
        return None
    try:
        data = requests.get(theme_obj["download_url"], timeout=10).text
        with open(os.path.join(base, name), "w") as f:
            f.write(data)
        return name
    except Exception as e:
        log_error(f"[Swatch] Download failed: {e}")
        return None

def refresh_installed_themes():
    """Make BN rescan the theme folder. Touches the UI, so main thread only.

    Without this BN never sees a newly downloaded file, and Set Active would
    ask for a theme it has no record of.
    """
    try:
        from binaryninjaui import refreshUserThemes
        refreshUserThemes()
    except Exception as e:
        log_error(f"[Swatch] Could not refresh theme list: {e}")

def fetch_repo_task(owner, repo, path):
    """fetch_repo_themes, tagged with its key so the UI can match the reply."""
    return ((owner, repo, path), fetch_repo_themes(owner, repo, path))

# -----------------------------
# UI COMPONENTS
# -----------------------------
# Theme rows store metadata here; group headers carry none (how we distinguish them).
THEME_ROLE = Qt.UserRole


class _TaskSignals(QObject):
    # (callback, result, error) -- object so Python values survive the queue.
    finished = Signal(object, object, object)


class _Task(QRunnable):
    """Runs one function on a pool thread and reports back to the UI thread."""

    def __init__(self, fn, callback, *args):
        super().__init__()
        self._fn = fn
        self._args = args
        self.callback = callback
        self.signals = _TaskSignals()

    @Slot()
    def run(self):
        try:
            self.signals.finished.emit(self.callback, self._fn(*self._args), None)
        except Exception as e:
            self.signals.finished.emit(self.callback, None, e)

def _remote_display_name(theme_obj):
    """Display name of a remote theme, only if it was already fetched."""
    text = REMOTE_TEXT_CACHE.get(theme_obj["download_url"])
    if text is None:
        return None
    try:
        return json.loads(text).get("name")
    except Exception:
        return None

def _matches(theme_obj, query):
    if query in theme_obj["name"].lower():
        return True
    display = _remote_display_name(theme_obj)
    return bool(display) and query in display.lower()

def _make_group_item(text):
    """A collapsible, non-selectable section header (top-level tree node)."""
    item = QTreeWidgetItem([text])
    item.setFlags(Qt.ItemIsEnabled)  # expandable but not selectable
    font = item.font(0)
    font.setBold(True)
    item.setFont(0, font)
    return item

def _make_theme_item(label, kind, theme_name, theme_obj=None):
    """kind is "installed", "remote" or "builtin"."""
    item = QTreeWidgetItem([("✓ " if kind == "installed" else "") + label])
    item.setData(0, THEME_ROLE, {
        "kind": kind,
        "name": theme_name,
        "obj": theme_obj,
    })
    return item


class ThemeManagerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(4)
        self._alive = True
        self._tasks = {}          # signals object -> task, kept alive in flight
        self._loading = set()     # repos with a fetch in flight
        self._attempted = set()   # repos already tried this dialog
        self._pending_preview = None
        self.setWindowTitle("Swatch")
        self.setMinimumSize(900, 600)
        self.resize(1000, 600)

        root = QVBoxLayout(self)

        header = QLabel(
            'Select a theme to preview it. '
            'Have a repo to add to this list? '
            f'<a href="{ISSUES_URL}">Open an issue here</a>'
        )
        header.setTextFormat(Qt.RichText)
        header.setOpenExternalLinks(False)
        header.linkActivated.connect(
            lambda url: QDesktopServices.openUrl(QUrl(url)))
        root.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Search Bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search themes...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh_list)
        left_layout.addWidget(self.search)

        self.theme_list = QTreeWidget()
        self.theme_list.setHeaderHidden(True)
        self.theme_list.setRootIsDecorated(True)
        self.theme_list.setExpandsOnDoubleClick(True)
        self.theme_list.currentItemChanged.connect(self.on_selection_changed)
        self.theme_list.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.theme_list, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_title = QLabel("Preview")
        self.preview_title.setStyleSheet("font-weight: bold; color: #aaa;")
        right_layout.addWidget(self.preview_title)

        # Linear and graph previews as two sections split by a native handle.
        preview_split = QSplitter(Qt.Vertical)
        self.linear_preview = LinearPreview()
        self.graph_preview = GraphPreview()
        preview_split.addWidget(self.linear_preview)
        preview_split.addWidget(self.graph_preview)
        preview_split.setStretchFactor(0, 0)
        preview_split.setStretchFactor(1, 1)
        right_layout.addWidget(preview_split, 1)

        button_row = QHBoxLayout()
        self.browse_btn = QPushButton("Open Theme Folder")
        self.browse_btn.setToolTip(
            "Open the folder holding installed themes, e.g. to delete one")
        self.browse_btn.clicked.connect(self.on_browse_clicked)
        button_row.addWidget(self.browse_btn)
        button_row.addStretch()
        self.action_btn = QPushButton("Select a theme")
        self.action_btn.setEnabled(False)
        self.action_btn.clicked.connect(self.on_action_clicked)
        button_row.addWidget(self.action_btn)
        right_layout.addLayout(button_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 880])

        self.refresh_list()

    def _run(self, fn, on_done, *args):
        """Run fn(*args) off the UI thread; deliver its result to on_done."""
        task = _Task(fn, on_done, *args)
        # The receiver must be a bound method of this dialog: a queued signal
        # needs a QObject on the UI thread to route to, and a bare lambda has
        # none. Holding the task also keeps its signals object alive until the
        # reply lands.
        self._tasks[task.signals] = task
        task.signals.finished.connect(self._deliver, Qt.QueuedConnection)
        self._pool.start(task)

    @Slot(object, object, object)
    def _deliver(self, on_done, result, error):
        self._tasks.pop(self.sender(), None)
        if not self._alive:
            return
        if error is not None:
            log_error(f"[Swatch] Background task failed: {error}")
            return
        on_done(result)

    def closeEvent(self, event):
        # In-flight replies must not touch widgets that are on their way out.
        self._alive = False
        super().closeEvent(event)

    def _ensure_fetch(self, owner, repo, path):
        key = (owner, repo, path)
        if key in self._loading or key in self._attempted:
            return
        self._loading.add(key)
        self._attempted.add(key)
        self._run(fetch_repo_task, self._on_repo_fetched, owner, repo, path)

    def _on_repo_fetched(self, result):
        key, _themes = result
        self._loading.discard(key)
        self.refresh_list()

    def refresh_list(self, _=None):
        """Rebuild the theme tree, preserving selection and collapse state."""
        prev = self._current_meta()
        prev_name = prev["name"] if prev else None
        expanded = self._expanded_groups()  # group title -> bool

        self.theme_list.blockSignals(True)
        # Clear UI
        self.theme_list.clear()

        search_query = self.search.text().lower()
        local_files = get_locally_installed_files()

        # 0. BUILT-IN SECTION
        builtin = [t for t in get_builtin_themes() if search_query in t.lower()]
        if builtin:
            grp = _make_group_item("BUILT IN")
            self.theme_list.addTopLevelItem(grp)
            for name in builtin:
                grp.addChild(_make_theme_item(name, "builtin", name))

        # 1. INSTALLED SECTION
        installed = [f for f in local_files
                     if search_query in f.lower()
                     or search_query in get_theme_display_name(f).lower()]
        if installed:
            grp = _make_group_item("INSTALLED LOCALLY")
            self.theme_list.addTopLevelItem(grp)
            for f in installed:
                grp.addChild(_make_theme_item(f, "installed", f))

        # 2. REMOTE SECTIONS (fetched in the background; cached ones render now)
        for owner, repo, path in REPOS:
            key = (owner, repo, path)
            if key not in SESSION_REMOTE_CACHE:
                self._ensure_fetch(owner, repo, path)
                if key in self._loading:
                    self.theme_list.addTopLevelItem(
                        _make_group_item(f"{owner} / {repo}  (loading\u2026)"))
                continue
            themes = SESSION_REMOTE_CACHE[key]
            # Filter themes based on search
            filtered = [t for t in themes if _matches(t, search_query)]
            if not filtered:
                continue
            grp = _make_group_item(f"{owner} / {repo}")
            self.theme_list.addTopLevelItem(grp)
            for t in filtered:
                # Check if already installed
                kind = "installed" if t["name"] in local_files else "remote"
                grp.addChild(_make_theme_item(t["name"], kind, t["name"], t))

        # Force-expand while searching so matches aren't hidden in a collapsed group.
        searching = bool(search_query)
        for i in range(self.theme_list.topLevelItemCount()):
            grp = self.theme_list.topLevelItem(i)
            grp.setExpanded(True if searching else expanded.get(grp.text(0), True))

        self.theme_list.blockSignals(False)

        if prev_name and not self._select_by_name(prev_name):
            self._show_placeholder()

    def _iter_theme_items(self):
        for i in range(self.theme_list.topLevelItemCount()):
            grp = self.theme_list.topLevelItem(i)
            for j in range(grp.childCount()):
                yield grp.child(j)

    def _expanded_groups(self):
        state = {}
        for i in range(self.theme_list.topLevelItemCount()):
            grp = self.theme_list.topLevelItem(i)
            state[grp.text(0)] = grp.isExpanded()
        return state

    def _select_by_name(self, name):
        for item in self._iter_theme_items():
            meta = item.data(0, THEME_ROLE)
            if meta and meta["name"] == name:
                self.theme_list.setCurrentItem(item)
                return True
        return False

    def _current_meta(self):
        item = self.theme_list.currentItem()
        return item.data(0, THEME_ROLE) if item else None

    def on_item_clicked(self, item, _column):
        if item.data(0, THEME_ROLE) is None:  # header row toggles instead of selecting
            item.setExpanded(not item.isExpanded())

    def on_selection_changed(self, current, _previous):
        meta = current.data(0, THEME_ROLE) if current else None
        if not meta:
            self._show_placeholder()
            return

        if meta["kind"] == "builtin":
            self._pending_preview = None
            self._show_builtin(meta)
            return

        if meta["kind"] == "installed":
            self._pending_preview = None
            self._show_theme(load_local_theme_json(meta["name"]), meta)
            return

        url = meta["obj"]["download_url"]
        if url in REMOTE_TEXT_CACHE:
            self._pending_preview = None
            self._show_theme(load_remote_theme_json(url), meta)
            return

        # Uncached: fetch off the UI thread and show the result if the
        # selection has not moved on by the time it lands.
        self._pending_preview = meta["name"]
        self.preview_title.setText(f"Preview \u2014 loading {meta['name']}\u2026")
        self._set_resolver(None)
        self.action_btn.setEnabled(False)
        self._run(load_remote_theme_json,
                  lambda tj, m=meta: self._on_preview_fetched(tj, m), url)

    def _on_preview_fetched(self, theme_json, meta):
        if self._pending_preview != meta["name"]:
            return  # selection moved while we were fetching
        self._pending_preview = None
        self._show_theme(theme_json, meta)

    def _show_builtin(self, meta):
        theme_json = builtin_theme_json(meta["name"])
        if theme_json:
            self._show_theme(theme_json, meta)
            return
        # Not bundled (e.g. an older BN build): still applicable, just unpreviewable.
        self.preview_title.setText(
            f"Preview \u2014 {meta['name']} (built in, no preview available)")
        self._set_resolver(None)
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Set Active")

    def _show_theme(self, theme_json, meta):
        if not theme_json:
            self.preview_title.setText("Preview \u2014 failed to load theme")
            self._set_resolver(None)
            self.action_btn.setEnabled(False)
            return

        display_name = theme_json.get("name", meta["name"])
        self.preview_title.setText(f"Preview — {display_name}")
        self._set_resolver(ThemeColorResolver(theme_json))

        self.action_btn.setEnabled(True)
        self.action_btn.setText(
            "Install" if meta["kind"] == "remote" else "Set Active")

    def _set_resolver(self, resolver):
        self.linear_preview.set_resolver(resolver)
        self.graph_preview.set_resolver(resolver)

    def _show_placeholder(self):
        self.preview_title.setText("Preview")
        self._set_resolver(None)
        self.action_btn.setText("Select a theme")
        self.action_btn.setEnabled(False)

    def on_browse_clicked(self):
        base = ensure_dirs()
        if base is None:
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(base)):
            log_error(f"[Swatch] Could not open {base}")

    def on_action_clicked(self):
        meta = self._current_meta()
        if not meta:
            return
        if meta["kind"] == "builtin":
            apply_theme_name(meta["name"])
            return
        if meta["kind"] == "installed":
            apply_theme(meta["name"])
            return
        self.action_btn.setEnabled(False)
        self.action_btn.setText("Installing\u2026")
        self._run(download_theme,
                  lambda name: self._on_download_done(name), meta["obj"])

    def _on_download_done(self, name):
        self.action_btn.setEnabled(True)
        if name:
            refresh_installed_themes()
        self.refresh_list()

# -----------------------------
# REGISTRATION
# -----------------------------
from binaryninjaui import UIAction, UIActionHandler, Menu

def open_manager(context):
    if theme_dir() is None:
        log_error(f"[Swatch] {NO_USER_DIR_MSG}")
        show_message_box("Swatch", NO_USER_DIR_MSG)
        return
    dlg = ThemeManagerDialog()
    dlg.exec()

UIAction.registerAction("Swatch")
UIActionHandler.globalActions().bindAction("Swatch", UIAction(open_manager))
Menu.mainMenu("Plugins").addAction("Swatch", "Themes")