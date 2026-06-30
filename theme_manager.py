import os
import json
import requests

from binaryninja import Settings, log_info, log_error, user_directory
from binaryninja.plugin import PluginCommand

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel,
    QWidget, QHBoxLayout, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

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
class ThemeRow(QWidget):
    def __init__(self, theme_name, is_installed, theme_obj=None, on_change=None):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QLabel(theme_name)
        btn = QPushButton("Set Active" if is_installed else "Install")
        
        def do_action():
            if is_installed:
                apply_theme(theme_name)
            else:
                download_theme(theme_obj, on_change)

        btn.clicked.connect(do_action)
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(btn)
        self.setLayout(layout)

class ThemeManagerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Theme Manager")
        self.setMinimumSize(500, 600)
        
        self.layout = QVBoxLayout(self)

        header = QLabel(
            'Have a repo you want to add to this list? '
            f'<a href="{ISSUES_URL}">Open an issue here</a>'
        )
        header.setTextFormat(Qt.RichText)
        header.setOpenExternalLinks(False)
        header.linkActivated.connect(
            lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.layout.addWidget(header)

        # Search Bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search themes...")
        self.search.textChanged.connect(self.refresh_ui)
        self.layout.addWidget(self.search)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

        self.refresh_ui()

    def refresh_ui(self):
        # Clear UI
        for i in reversed(range(self.container_layout.count())):
            self.container_layout.itemAt(i).widget().setParent(None)

        search_query = self.search.text().lower()
        local_files = get_locally_installed_files()

        # 1. INSTALLED SECTION
        installed_header = QLabel("INSTALLED LOCALLY")
        installed_header.setStyleSheet("font-weight: bold; color: #aaa; margin-top: 10px;")
        self.container_layout.addWidget(installed_header)

        for f in local_files:
            if search_query in f.lower():
                self.container_layout.addWidget(ThemeRow(f, True))

        # 2. REMOTE SECTIONS
        for owner, repo, path in REPOS:
            themes = fetch_repo_themes(owner, repo, path)
            
            # Filter themes based on search
            filtered_themes = [t for t in themes if search_query in t["name"].lower()]
            
            if not filtered_themes:
                continue

            repo_label = QLabel(f"{owner} / {repo}")
            repo_label.setStyleSheet("font-weight: bold; color: #58a6ff; margin-top: 15px; border-bottom: 1px solid #333;")
            self.container_layout.addWidget(repo_label)

            for t in filtered_themes:
                # Check if already installed
                is_installed = t["name"] in local_files
                self.container_layout.addWidget(ThemeRow(t["name"], is_installed, t, self.refresh_ui))

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