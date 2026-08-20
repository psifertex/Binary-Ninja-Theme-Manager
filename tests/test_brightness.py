"""@dark / @light search keywords, classified by background luminance."""

import json
import os
import tempfile
import time

from _harness import load_plugin, qt_app

qt_app()
tm = load_plugin()
from PySide6.QtWidgets import QApplication

# --- keyword parsing ---
assert tm.parse_search("solarized") == ("solarized", None, None)
assert tm.parse_search("@dark") == ("", "dark", None)
assert tm.parse_search("@LIGHT") == ("", "light", None)
assert tm.parse_search("solarized @dark") == ("solarized", "dark", None)
assert tm.parse_search("@dark solarized") == ("solarized", "dark", None)
assert tm.parse_search("email@dark.com") == ("email@dark.com", None, None), "only a bare keyword counts"
assert tm.parse_search("@local") == ("", None, "local")
assert tm.parse_search("@remote @dark x") == ("x", "dark", "remote")
print("  keywords parsed out of the query, text preserved")

# --- luminance classification ---
def theme(bg):
    return {"name": "T", "colors": {"background": bg, "content": [0, 0, 0]},
            "palette": {"Base": "background"}}

assert tm.theme_brightness(theme([30, 30, 30])) == "dark"
assert tm.theme_brightness(theme([250, 250, 250])) == "light"
assert tm.theme_brightness(theme([253, 246, 227])) == "light"   # solarized light
assert tm.theme_brightness(theme([0, 43, 54])) == "dark"        # solarized dark
# green weighs most in sRGB luminance, so these two differ despite equal sums
assert tm.theme_brightness(theme([0, 200, 0])) == "light"
assert tm.theme_brightness(theme([0, 0, 200])) == "dark"
assert tm.theme_brightness(None) is None
print("  luminance classifies dark/light, weighted per sRGB")

# --- filtering in the dialog ---
bundled = tempfile.mkdtemp()
for name, bg in (("Dark", [30, 30, 30]), ("Light", [250, 250, 250])):
    with open(os.path.join(bundled, f"{name.lower()}.bntheme"), "w") as f:
        json.dump({"name": name, "colors": {"background": bg, "content": [1, 1, 1]},
                   "palette": {"Base": "background"}}, f)
tm.BUILTIN_THEME_RESOURCE_DIR = bundled
tm._BUILTIN_THEME_DATA = None

base = tm.ensure_dirs()
with open(os.path.join(base, "mine-dark.bntheme"), "w") as f:
    json.dump({"name": "Mine Dark", "colors": {"background": [20, 20, 20], "content": [1, 1, 1]},
               "palette": {"Base": "background"}}, f)

REMOTE = {"name": "Remote Light", "colors": {"background": [245, 245, 245], "content": [1, 1, 1]},
          "palette": {"Base": "background"}}
class Resp:
    status_code = 200
    text = json.dumps(REMOTE)
    def json(self):
        return [{"type": "file", "name": "remote.bntheme", "download_url": "http://x/remote"}]
tm.requests.get = lambda url, **kw: Resp()

dlg = tm.ThemeManagerDialog()
def pump(pred, limit=20.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QApplication.processEvents()
        if pred(): return True
        time.sleep(0.01)
    return False
assert pump(lambda: len(tm.SESSION_REMOTE_CACHE) >= len(tm.get_repos()))

def rows(q):
    dlg.search.setText(q)
    pump(lambda: not dlg._warming, limit=10.0)
    return sorted(i.text(0).replace("✓ ", "") for i in dlg._iter_theme_items())

everything = rows("")
assert "Dark" in everything and "Light" in everything, everything
print("  unfiltered:", everything)

dark = rows("@dark")
assert "Dark" in dark and "mine-dark.bntheme" in dark, dark
assert "Light" not in dark, dark
print("  @dark  ->", dark)

light = rows("@light")
assert "Light" in light and "Dark" not in light, light
assert "mine-dark.bntheme" not in light, light
print("  @light ->", light)

# a remote theme is fetched in the background so it can be judged at all
assert "remote.bntheme" in light, f"remote light theme not classified: {light}"
print("  remote themes warmed in the background and classified")

combined = rows("mine @dark")
assert combined == ["mine-dark.bntheme"], combined
print("  text and keyword combine:", combined)

assert "@dark" in tm.SEARCH_HINT and "@dark" not in dlg.search.placeholderText(), \
    "keywords belong in the hint row, not the narrow placeholder"
print("PASS brightness: hint row is", tm.SEARCH_HINT)
