import os
import json
import requests

from binaryninja import Settings, log_info, log_error, user_directory
from binaryninja.plugin import PluginCommand

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel,
    QWidget, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QUrl
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

# Cross-platform user dir (issue #1); falls back to the Linux default.
BASE_DIR = user_directory() or os.path.expanduser("~/.binaryninja")
THEME_DIR = os.path.join(BASE_DIR, "community-themes")

ISSUES_URL = "https://github.com/lele394/Binary-Ninja-Theme-Manager/issues/new"

# GLOBAL MEMORY CACHE (To avoid GitHub Rate Limits)
# Structure: {(owner, repo, path): [themes]}
SESSION_REMOTE_CACHE = {}

REMOTE_TEXT_CACHE = {}

def ensure_dirs():
    os.makedirs(THEME_DIR, exist_ok=True)

# -----------------------------
# THEME UTILS
# -----------------------------
def get_theme_display_name(theme_filename):
    """Reads the JSON inside the .bntheme to get the actual UI name."""
    theme_path = os.path.join(THEME_DIR, theme_filename)
    if not os.path.exists(theme_path):
        return theme_filename
    try:
        with open(theme_path, "r", encoding="utf-8") as f:
            return json.load(f).get("name", theme_filename)
    except:
        return theme_filename

def get_locally_installed_files():
    ensure_dirs()
    return [f for f in os.listdir(THEME_DIR) if f.endswith(".bntheme")]

def load_local_theme_json(theme_filename):
    """Parse an installed .bntheme into a dict (None on failure)."""
    theme_path = os.path.join(THEME_DIR, theme_filename)
    try:
        with open(theme_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"[ThemeManager] Could not read {theme_filename}: {e}")
        return None

def load_remote_theme_json(download_url):
    """Fetch (cached) and parse a remote .bntheme into a dict (None on failure)."""
    text = REMOTE_TEXT_CACHE.get(download_url)
    if text is None:
        try:
            text = requests.get(download_url, timeout=5).text
            REMOTE_TEXT_CACHE[download_url] = text
        except Exception as e:
            log_error(f"[ThemeManager] Preview fetch failed: {e}")
            return None
    try:
        return json.loads(text)
    except Exception as e:
        log_error(f"[ThemeManager] Could not parse remote theme: {e}")
        return None

# -----------------------------
# GITHUB FETCH (With caching)
# -----------------------------
def fetch_repo_themes(owner, repo, path=""):
    key = (owner, repo, path)
    if key in SESSION_REMOTE_CACHE:
        return SESSION_REMOTE_CACHE[key]

    log_info(f"[ThemeManager] Fetching remote: {owner}/{repo}")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return []
        
        themes = []
        for f in r.json():
            if f["type"] == "file" and f["name"].endswith(".bntheme"):
                themes.append({"name": f["name"], "download_url": f["download_url"]})
        
        SESSION_REMOTE_CACHE[key] = themes
        return themes
    except Exception as e:
        log_error(f"Fetch error: {e}")
        return []

def apply_theme(theme_filename):
    display_name = get_theme_display_name(theme_filename)
    Settings().set_string("ui.theme.name", display_name)
    
    # Hot reload for BN 4.0+
    # Untested, I have 3.5
    try:
        from binaryninjaui import Theme
        Theme.setTheme(display_name)
        log_info(f"Applied: {display_name}")
    except:
        log_info(f"Applied: {display_name} (Restart required)")

def download_theme(theme_obj, callback):
    try:
        data = requests.get(theme_obj["download_url"]).text
        with open(os.path.join(THEME_DIR, theme_obj["name"]), "w") as f:
            f.write(data)
        callback()
    except Exception as e:
        log_error(f"Download failed: {e}")

# -----------------------------
# UI COMPONENTS
# -----------------------------
# Theme rows store metadata here; group headers carry none (how we distinguish them).
THEME_ROLE = Qt.UserRole

def _make_group_item(text):
    """A collapsible, non-selectable section header (top-level tree node)."""
    item = QTreeWidgetItem([text])
    item.setFlags(Qt.ItemIsEnabled)  # expandable but not selectable
    font = item.font(0)
    font.setBold(True)
    item.setFont(0, font)
    return item

def _make_theme_item(label, is_installed, theme_name, theme_obj):
    item = QTreeWidgetItem([("✓ " if is_installed else "") + label])
    item.setData(0, THEME_ROLE, {
        "installed": is_installed,
        "name": theme_name,
        "obj": theme_obj,
    })
    return item


class ThemeManagerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Theme Manager")
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

        # 1. INSTALLED SECTION
        installed = [f for f in local_files if search_query in f.lower()]
        if installed:
            grp = _make_group_item("INSTALLED LOCALLY")
            self.theme_list.addTopLevelItem(grp)
            for f in installed:
                grp.addChild(_make_theme_item(f, True, f, None))

        # 2. REMOTE SECTIONS
        for owner, repo, path in REPOS:
            themes = fetch_repo_themes(owner, repo, path)
            # Filter themes based on search
            filtered = [t for t in themes if search_query in t["name"].lower()]
            if not filtered:
                continue
            grp = _make_group_item(f"{owner} / {repo}")
            self.theme_list.addTopLevelItem(grp)
            for t in filtered:
                # Check if already installed
                is_installed = t["name"] in local_files
                grp.addChild(_make_theme_item(t["name"], is_installed, t["name"], t))

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

        if meta["installed"]:
            theme_json = load_local_theme_json(meta["name"])
        else:
            theme_json = load_remote_theme_json(meta["obj"]["download_url"])

        if not theme_json:
            self.preview_title.setText("Preview — failed to load theme")
            self._set_resolver(None)
            self.action_btn.setEnabled(False)
            return

        display_name = theme_json.get("name", meta["name"])
        self.preview_title.setText(f"Preview — {display_name}")
        self._set_resolver(ThemeColorResolver(theme_json))

        self.action_btn.setEnabled(True)
        self.action_btn.setText("Set Active" if meta["installed"] else "Install")

    def _set_resolver(self, resolver):
        self.linear_preview.set_resolver(resolver)
        self.graph_preview.set_resolver(resolver)

    def _show_placeholder(self):
        self.preview_title.setText("Preview")
        self._set_resolver(None)
        self.action_btn.setText("Select a theme")
        self.action_btn.setEnabled(False)

    def on_action_clicked(self):
        meta = self._current_meta()
        if not meta:
            return
        if meta["installed"]:
            apply_theme(meta["name"])
        else:
            download_theme(meta["obj"], lambda: self.refresh_list())

# -----------------------------
# REGISTRATION
# -----------------------------
from binaryninjaui import UIAction, UIActionHandler, Menu

def open_manager(context):
    dlg = ThemeManagerDialog()
    dlg.exec()

UIAction.registerAction("Theme Manager")
UIActionHandler.globalActions().bindAction("Theme Manager", UIAction(open_manager))
Menu.mainMenu("Plugins").addAction("Theme Manager", "Themes")