import os
import sys
import json

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction

tm = load_plugin()

THEME = {"name": "Smoke", "colors": {"background": [40, 40, 40], "content": [220, 220, 220]},
         "theme-colors": {"instructionColor": ["~", "content", "background", 64]},
         "palette": {"WindowText": "content", "Base": "background"}}

class Resp:
    status_code = 200
    def __init__(self, payload): self._p = payload
    def json(self): return self._p
    @property
    def text(self): return json.dumps(THEME)

def fake_get(url, **kw):
    if "api.github.com" in url:
        return Resp([{"type": "file", "name": "smoke.bntheme", "download_url": "http://x/smoke"}])
    return Resp(None)
tm.requests.get = fake_get

# a locally installed theme too, so both branches render
base = tm.ensure_dirs()
open(os.path.join(base, "local.bntheme"), "w").write(json.dumps(THEME))

dlg = tm.ThemeManagerDialog()
print("  dialog built, top-level rows:", dlg.theme_list.topLevelItemCount())
assert dlg.theme_list.topLevelItemCount() > 0

# select the installed theme -> preview resolver must be populated
items = list(dlg._iter_theme_items())
print("  theme rows:", len(items))
dlg.theme_list.setCurrentItem(items[0])
assert dlg.linear_preview._resolver is not None, "linear preview has no resolver"
assert dlg.graph_preview._resolver is not None, "graph preview has no resolver"

# force a real paint through both preview widgets
from PySide6.QtGui import QPixmap
for w in (dlg.linear_preview, dlg.graph_preview):
    w.resize(600, 300)
    pm = QPixmap(600, 300)
    w.render(pm)
print("  both previews painted without error")

# search filtering still works
dlg.search.setText("smoke")
dlg.search.setText("")
print("PASS dialog: constructed, previewed, painted, filtered")
