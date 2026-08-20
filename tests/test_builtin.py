"""Built-in themes are listed so a user can switch back to a stock theme."""

import json
import os

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction
tm = load_plugin()
import binaryninjaui as ui

base = tm.ensure_dirs()
open(os.path.join(base, "mine.bntheme"), "w").write(json.dumps({"name": "Mine"}))
ui._scan_hook[0] = lambda: ["Mine"]
ui.refreshUserThemes()

names = tm.get_builtin_themes()
assert "Dark" in names and "Light" in names, names
assert "Mine" not in names, "installed theme duplicated into the built-in list"
print("  built-ins listed, installed themes excluded:", names)

class Resp:
    status_code = 200
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()

dlg = tm.ThemeManagerDialog()
groups = [dlg.theme_list.topLevelItem(i).text(0)
          for i in range(dlg.theme_list.topLevelItemCount())]
assert groups[0] == "BUILT IN", groups
print("  BUILT IN is the first group, so resetting is easy to find")

builtin_rows = [i for i in dlg._iter_theme_items()
                if i.data(0, tm.THEME_ROLE)["kind"] == "builtin"]
assert {i.text(0) for i in builtin_rows} == {"Default", "Dark", "Light"}

# selecting one: no preview is possible, but it must still be applicable
dlg.theme_list.setCurrentItem(builtin_rows[1])
assert dlg.linear_preview._resolver is None, "built-ins have no JSON to preview"
assert dlg.action_btn.isEnabled() and dlg.action_btn.text() == "Set Active"
assert "no preview" in dlg.preview_title.text(), dlg.preview_title.text()
print("  selecting a built-in explains the missing preview, stays applicable")

ui.CALLS.clear()
dlg.action_btn.click()
applied = builtin_rows[1].text(0)
assert ("setActiveTheme", applied, True) in ui.CALLS, ui.CALLS
assert ui.getActiveTheme() == applied
print(f"  clicking Set Active switched to {applied!r}")

# an installed community theme must still work unchanged
installed_rows = [i for i in dlg._iter_theme_items()
                  if i.data(0, tm.THEME_ROLE)["kind"] == "installed"]
dlg.theme_list.setCurrentItem(installed_rows[0])
assert dlg.linear_preview._resolver is not None, "installed theme lost its preview"
dlg.action_btn.click()
assert ui.getActiveTheme() == "Mine", ui.getActiveTheme()
print("PASS builtin: stock themes listed and applicable, installed ones unaffected")


# --- previews for built-ins come from BN's bundled .bntheme resources ---
# BN registers them under ":/themes"; QDir/QFile read a plain directory the
# same way, so this exercises the identical code path.
import tempfile

bundled = tempfile.mkdtemp()
with open(os.path.join(bundled, "dark.bntheme"), "w") as f:
    json.dump({
        "name": "Dark",
        "colors": {"background": [40, 40, 40], "content": [220, 220, 220]},
        "theme-colors": {"instructionColor": ["~", "content", "background", 64],
                         "addressColor": [162, 217, 175, 255]},
        "palette": {"WindowText": "content", "Base": "background"},
    }, f)

tm.BUILTIN_THEME_RESOURCE_DIR = bundled
tm._BUILTIN_THEME_DATA = None
assert tm.builtin_theme_json("Dark")["name"] == "Dark"
assert tm.builtin_theme_json("Light") is None, "unbundled theme should not resolve"
print("  bundled themes indexed by display name")

dlg.refresh_list()
rows = {i.text(0): i for i in dlg._iter_theme_items()
        if i.data(0, tm.THEME_ROLE)["kind"] == "builtin"}

dlg.theme_list.setCurrentItem(rows["Dark"])
assert dlg.linear_preview._resolver is not None, "bundled built-in did not preview"
assert dlg.action_btn.text() == "Set Active", dlg.action_btn.text()
assert "no preview" not in dlg.preview_title.text(), dlg.preview_title.text()
from PySide6.QtGui import QPixmap
for w in (dlg.linear_preview, dlg.graph_preview):
    w.resize(400, 200); w.render(QPixmap(400, 200))
print("  built-in preview renders from the bundled .bntheme")

# a built-in BN knows but does not bundle still applies, just without a preview
dlg.theme_list.setCurrentItem(rows["Light"])
assert dlg.linear_preview._resolver is None
assert dlg.action_btn.isEnabled() and dlg.action_btn.text() == "Set Active"
assert "no preview" in dlg.preview_title.text()
print("PASS bundled: built-ins preview when bundled, stay applicable when not")
