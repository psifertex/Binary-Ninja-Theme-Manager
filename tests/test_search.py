import os
import sys
import json
import time

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction

tm = load_plugin()

base = tm.ensure_dirs()
# filename bears no resemblance to the display name -- the exact case that broke
open(os.path.join(base, "cat-mocha.bntheme"), "w").write(json.dumps({"name": "Catppuccin Mocha"}))

class Resp:
    status_code = 200
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()

dlg = tm.ThemeManagerDialog()
def rows(q):
    dlg.search.setText(q)
    return [i.text(0).replace("✓ ", "") for i in dlg._iter_theme_items()]

assert rows("cat-mocha") == ["cat-mocha.bntheme"], rows("cat-mocha")
print("  filename search still works")
assert rows("Catppuccin") == ["cat-mocha.bntheme"], rows("Catppuccin")
print("  display-name search now works")
assert rows("mocha") == ["cat-mocha.bntheme"], rows("mocha")
assert rows("nonsense") == [], rows("nonsense")
print("  case-insensitive, and non-matches still excluded")

# the cache must not go stale when the file changes on disk
import time
time.sleep(0.01)
open(os.path.join(base, "cat-mocha.bntheme"), "w").write(json.dumps({"name": "Renamed Theme"}))
assert tm.get_theme_display_name("cat-mocha.bntheme") == "Renamed Theme", "stale cache"
print("PASS search: matches filename and display name, cache invalidates on mtime")
