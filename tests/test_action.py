"""Both actions register, and neither lives as text inside the dialog."""

from _harness import load_plugin, qt_app

qt_app()
tm = load_plugin()
import binaryninjaui as ui

for name in (tm.ACTION_NAME, tm.ISSUE_ACTION_NAME):
    assert name in ui.REGISTERED, (name, ui.REGISTERED)
    assert name in ui.BOUND, (name, ui.BOUND)
    assert ("Plugins", name, "Themes") in ui.MENU, (name, ui.MENU)
print("  registered, bound and in Plugins > Themes:")
for name in (tm.ACTION_NAME, tm.ISSUE_ACTION_NAME):
    print("   ", name)

# the command palette matches substrings, so check the words that should find them
assert "theme" in tm.ACTION_NAME.lower() and "swatch" in tm.ACTION_NAME.lower()
assert "issue" in tm.ISSUE_ACTION_NAME.lower()
print("  findable by 'swatch', 'theme' and 'issue'")

# reporting an issue opens the tracker rather than showing a link in the dialog
opened = []
class FakeDesktopServices:
    @staticmethod
    def openUrl(url): opened.append(url.toString()); return True
tm.QDesktopServices = FakeDesktopServices
tm.report_issue(None)
assert opened == [tm.ISSUES_URL], opened
print("  Report an Issue opens", opened[0])

# the dialog itself carries no instructional header any more
class Resp:
    status_code = 200
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()
dlg = tm.ThemeManagerDialog()
from PySide6.QtWidgets import QLabel
texts = [w.text() for w in dlg.findChildren(QLabel)]
assert not any(tm.ISSUES_URL in t for t in texts), texts
assert not any("Settings" in t for t in texts), texts
print("  no header text left in the dialog:", texts)
print("PASS action: two menu actions, no in-dialog instructions")
