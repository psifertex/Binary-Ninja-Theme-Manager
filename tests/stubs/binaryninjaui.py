# Mirrors the real binaryninjaui surface confirmed in BN's console:
# ['ThemeColor', 'getActiveTheme', 'getAvailableThemes', 'getThemeColor',
#  'getThemeHighlightColor', 'initThemes', 'refreshUserThemes',
#  'resetUserThemes', 'setActiveTheme']   -- note: no `Theme` class.
CALLS = []
_active = ["Default"]
_available = ["Default", "Dark", "Light"]   # BN ships these compiled in

def setActiveTheme(name, saveToSettings=True):
    CALLS.append(("setActiveTheme", name, saveToSettings))
    if name not in _available:
        raise RuntimeError(f"unknown theme {name!r} (refreshUserThemes not called?)")
    _active[0] = name

def refreshUserThemes():
    CALLS.append(("refreshUserThemes",))
    _available[:] = ["Default", "Dark", "Light"] + _scan()

def getAvailableThemes(): return list(_available)
def getActiveTheme(): return _active[0]
def initThemes(): CALLS.append(("initThemes",))
def resetUserThemes(): CALLS.append(("resetUserThemes",))

_scan_hook = [lambda: []]
def _scan(): return _scan_hook[0]()

REGISTERED = []

class UIAction:
    def __init__(self, *a): pass
    @staticmethod
    def registerAction(name, *a):
        REGISTERED.append(name)
BOUND = []
MENU = []

class _H:
    def bindAction(self, name, action): BOUND.append(name)
class UIActionHandler:
    @staticmethod
    def globalActions(): return _H()
class _M:
    def __init__(self, menu): self.menu = menu
    def addAction(self, name, group, *a): MENU.append((self.menu, name, group))
class Menu:
    @staticmethod
    def mainMenu(name): return _M(name)
