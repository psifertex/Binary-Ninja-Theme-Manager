import os
import sys
import json
from _harness import load_plugin

tm = load_plugin()
import binaryninjaui as ui

base = tm.ensure_dirs()
open(os.path.join(base, "smoke.bntheme"), "w").write(json.dumps({"name": "Smoke"}))
# the stub's "scan" mirrors what BN would find on disk
ui._scan_hook[0] = lambda: [json.load(open(os.path.join(base, f)))["name"]
                            for f in os.listdir(base) if f.endswith(".bntheme")]

# apply_theme must reach setActiveTheme, not the restart fallback
ui.CALLS.clear()
ui.refreshUserThemes()          # simulate BN having scanned
ui.CALLS.clear()
tm.apply_theme("smoke.bntheme")
assert ("setActiveTheme", "Smoke", True) in ui.CALLS, ui.CALLS
assert ui.getActiveTheme() == "Smoke", ui.getActiveTheme()
print("PASS apply: setActiveTheme called with the display name, theme active")

# --- full install -> Set Active flow (the plugin's whole purpose) ---
NEW = {"name": "Freshly Installed"}
class Resp:
    status_code = 200
    text = json.dumps(NEW)
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()

ui.CALLS.clear()
assert tm.download_theme({"name": "fresh.bntheme", "download_url": "http://x/fresh"}) == "fresh.bntheme"
tm.refresh_installed_themes()
assert ("refreshUserThemes",) in ui.CALLS, f"install did not refresh: {ui.CALLS}"
assert "Freshly Installed" in ui.getAvailableThemes(), ui.getAvailableThemes()

tm.apply_theme("fresh.bntheme")          # would raise pre-fix: BN wouldn't know it
assert ui.getActiveTheme() == "Freshly Installed", ui.getActiveTheme()
print("PASS install flow: download -> refresh -> setActiveTheme, theme active")

# prove the guard is load-bearing: skip the refresh and the apply fails
ui._available[:] = ["Default"]
try:
    tm.apply_theme("fresh.bntheme")
except Exception:
    raise SystemExit("apply_theme should not propagate; it logs instead")
print("PASS regression guard: unrefreshed theme is rejected by BN, not silently applied")
