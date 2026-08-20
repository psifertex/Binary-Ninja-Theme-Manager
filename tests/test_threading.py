"""Network work must never run on the UI thread.

Fetches block on a gate rather than a sleep, so this proves the dialog does not
wait on them without depending on wall-clock timing (which goes flaky on a
loaded CI runner).
"""

import json
import threading
import time

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction
tm = load_plugin()
from PySide6.QtWidgets import QApplication

MAIN = threading.get_ident()
fetch_threads = []
gate = threading.Event()
THEME = {"name": "Remote Theme"}


class Resp:
    status_code = 200
    text = json.dumps(THEME)
    def json(self):
        return [{"type": "file", "name": "remote.bntheme",
                 "download_url": "http://x/remote"}]


def gated_get(url, **kw):
    fetch_threads.append(threading.get_ident())
    if not gate.wait(30):
        raise RuntimeError("gate never released")
    return Resp()
tm.requests.get = gated_get


def pump(pred, limit=30.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QApplication.processEvents()
        if pred():
            return True
        time.sleep(0.01)
    return False


# Every fetch is blocked. A synchronous implementation could not get past this.
dlg = tm.ThemeManagerDialog()
print("  dialog constructed while all fetches are blocked")
assert not tm.SESSION_REMOTE_CACHE, \
    f"fetches completed during construction: {list(tm.SESSION_REMOTE_CACHE)}"
assert dlg.theme_list.topLevelItemCount() > 0, "no loading placeholders shown"
labels = [dlg.theme_list.topLevelItem(i).text(0)
          for i in range(dlg.theme_list.topLevelItemCount())]
assert any("loading" in l for l in labels), labels
print("  loading placeholders shown while work is outstanding")

gate.set()
assert pump(lambda: len(tm.SESSION_REMOTE_CACHE) >= len(tm.get_repos())), "fetches never completed"
assert fetch_threads, "no fetch happened"
assert MAIN not in fetch_threads, "a fetch ran on the UI thread"
print(f"  {len(fetch_threads)} fetches completed, none on the UI thread")

assert pump(lambda: not any(
    "loading" in dlg.theme_list.topLevelItem(i).text(0)
    for i in range(dlg.theme_list.topLevelItemCount())))
print("  placeholders resolved into real groups")

# Selecting an uncached remote theme must not block either.
remote = [i for i in dlg._iter_theme_items()
          if i.data(0, tm.THEME_ROLE)["kind"] == "remote"]
assert remote, "no remote theme rows to fetch"
tm.REMOTE_TEXT_CACHE.clear()
gate.clear()
dlg.theme_list.setCurrentItem(remote[0])
assert dlg.linear_preview._resolver is None, "preview resolved before its fetch ran"
assert "loading" in dlg.preview_title.text().lower(), dlg.preview_title.text()
print("  selection returned immediately, preview marked as loading")

gate.set()
assert pump(lambda: dlg.linear_preview._resolver is not None), "preview never arrived"
print("PASS threading: no network on the UI thread")
