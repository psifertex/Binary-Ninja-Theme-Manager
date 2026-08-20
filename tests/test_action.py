"""The action name carries both the brand and what it does."""

from _harness import load_plugin, qt_app

qt_app()
tm = load_plugin()
import binaryninjaui as ui

assert tm.ACTION_NAME in ui.REGISTERED, ui.REGISTERED
print("  registered action:", tm.ACTION_NAME)

# BN's command palette matches substrings, so both words must lead here
lowered = tm.ACTION_NAME.lower()
for term in ("swatch", "theme"):
    assert term in lowered, f"{term!r} would not find {tm.ACTION_NAME!r}"
print("  found by searching 'swatch' and 'theme'")
print("PASS action:", tm.ACTION_NAME)
