"""@local / @remote narrow the list to themes you have, or ones you don't."""

import json
import os
import tempfile
import time

from _harness import load_plugin, qt_app

qt_app()
tm = load_plugin()
from PySide6.QtWidgets import QApplication

THEME = {"name": "T", "colors": {"background": [20, 20, 20], "content": [1, 1, 1]},
         "palette": {"Base": "background"}}

bundled = tempfile.mkdtemp()
with open(os.path.join(bundled, "dark.bntheme"), "w") as f:
    json.dump(dict(THEME, name="Dark"), f)
tm.BUILTIN_THEME_RESOURCE_DIR = bundled
tm._BUILTIN_THEME_DATA = None

base = tm.ensure_dirs()
with open(os.path.join(base, "mine.bntheme"), "w") as f:
    json.dump(dict(THEME, name="Mine"), f)

class Resp:
    status_code = 200
    text = json.dumps(THEME)
    def json(self):
        return [{"type": "file", "name": "faraway.bntheme", "download_url": "http://x/faraway"}]
tm.requests.get = lambda url, **kw: Resp()

dlg = tm.ThemeManagerDialog()

def pump(pred, limit=20.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QApplication.processEvents()
        if pred():
            return True
        time.sleep(0.01)
    return False

# Wait on the tree, not the cache: the worker fills the cache directly, so it
# can be complete before the queued reply has rebuilt the list.
assert pump(lambda: any(i.data(0, tm.THEME_ROLE)["kind"] == "remote"
                        for i in dlg._iter_theme_items())), "remote rows never appeared"

def kinds(q):
    dlg.search.setText(q)
    return sorted({i.data(0, tm.THEME_ROLE)["kind"] for i in dlg._iter_theme_items()})

assert kinds("") == ["builtin", "installed", "remote"], kinds("")
print("  unfiltered shows all three kinds")

assert kinds("@local") == ["builtin", "installed"], kinds("@local")
print("  @local  -> built-in and installed only, all usable offline")

assert kinds("@remote") == ["remote"], kinds("@remote")
print("  @remote -> not-yet-installed themes only")

# scope composes with text and with brightness
dlg.search.setText("@local mine")
names = [i.text(0).replace("✓ ", "") for i in dlg._iter_theme_items()]
assert names == ["mine.bntheme"], names
dlg.search.setText("@local @dark")
assert kinds("@local @dark") == ["builtin", "installed"], kinds("@local @dark")
print("  composes with search text and with @dark")

assert "@local" in tm.SEARCH_HINT and "@remote" in tm.SEARCH_HINT
assert "@local" in tm.SEARCH_HINT_TOOLTIP
print("PASS scope: @local and @remote filter by availability")
