import os
import sys

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction

tm = load_plugin()

class Resp:
    status_code = 200
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()

opened = []
class FakeDesktopServices:          # never actually launch Finder in a test
    @staticmethod
    def openUrl(url):
        opened.append(url.toLocalFile()); return True
tm.QDesktopServices = FakeDesktopServices

dlg = tm.ThemeManagerDialog()
assert dlg.browse_btn.isEnabled(), "browse button should always be usable"
dlg.browse_btn.click()
assert opened == [tm.theme_dir()], (opened, tm.theme_dir())
print("  opens exactly the theme dir:", opened[0])

# must stay safe when there is no user directory at all
tm.user_directory = lambda: None
opened.clear()
dlg.on_browse_clicked()
assert opened == [], opened
print("PASS browse: opens the theme folder, declines safely with no user dir")
