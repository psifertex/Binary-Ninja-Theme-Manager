# Mirrors the real binaryninjaui surface confirmed in BN's console:
# ['ThemeColor', 'getActiveTheme', 'getAvailableThemes', 'getThemeColor',
#  'getThemeHighlightColor', 'initThemes', 'refreshUserThemes',
#  'resetUserThemes', 'setActiveTheme']   -- note: no `Theme` class.
CALLS = []
_active = ["Default"]
_available = ["Default"]

def setActiveTheme(name, saveToSettings=True):
    CALLS.append(("setActiveTheme", name, saveToSettings))
    if name not in _available:
        raise RuntimeError(f"unknown theme {name!r} (refreshUserThemes not called?)")
    _active[0] = name

def refreshUserThemes():
    CALLS.append(("refreshUserThemes",))
    _available[:] = ["Default"] + _scan()

def getAvailableThemes(): return list(_available)
def getActiveTheme(): return _active[0]
def initThemes(): CALLS.append(("initThemes",))
def resetUserThemes(): CALLS.append(("resetUserThemes",))

_scan_hook = [lambda: []]
def _scan(): return _scan_hook[0]()

class UIAction:
    def __init__(self, *a): pass
    @staticmethod
    def registerAction(*a): pass
class _H:
    def bindAction(self, *a): pass
class UIActionHandler:
    @staticmethod
    def globalActions(): return _H()
class _M:
    def addAction(self, *a): pass
class Menu:
    @staticmethod
    def mainMenu(*a): return _M()
