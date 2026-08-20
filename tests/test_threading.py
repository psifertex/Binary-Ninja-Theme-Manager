import os
import sys
import json
import time
import threading

from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction

tm = load_plugin()
from PySide6.QtWidgets import QApplication

MAIN = threading.get_ident()
fetch_threads = []
THEME = {"name": "Remote Theme"}

class Resp:
    status_code = 200
    text = json.dumps(THEME)
    def json(self):
        return [{"type": "file", "name": "remote.bntheme", "download_url": "http://x/remote"}]

def slow_get(url, **kw):
    fetch_threads.append(threading.get_ident())
    time.sleep(0.20)          # would freeze the UI if it ran on the main thread
    return Resp()
tm.requests.get = slow_get

t0 = time.monotonic()
dlg = tm.ThemeManagerDialog()
elapsed = time.monotonic() - t0
print(f"  dialog constructed in {elapsed*1000:.0f}ms with 5 slow repos")
assert elapsed < 0.20, f"construction blocked for {elapsed:.2f}s -- still synchronous"

def pump(pred, limit=10.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QApplication.processEvents()
        if pred(): return True
        time.sleep(0.01)
    return False

assert pump(lambda: len(tm.SESSION_REMOTE_CACHE) >= len(tm.REPOS)), "fetches never completed"
print(f"  all {len(tm.REPOS)} repos fetched in the background")
assert fetch_threads, "no fetch happened"
assert MAIN not in fetch_threads, "a fetch ran on the UI thread"
print(f"  {len(fetch_threads)} fetches, none on the UI thread")

assert pump(lambda: dlg.theme_list.topLevelItemCount() >= len(tm.REPOS))
labels = [dlg.theme_list.topLevelItem(i).text(0) for i in range(dlg.theme_list.topLevelItemCount())]
assert not any("loading" in l for l in labels), labels
print("  loading placeholders resolved into real groups")

# selecting an uncached remote theme must not block either
items = list(dlg._iter_theme_items())
tm.REMOTE_TEXT_CACHE.clear()
t0 = time.monotonic()
dlg.theme_list.setCurrentItem(items[0])
elapsed = time.monotonic() - t0
assert elapsed < 0.20, f"preview blocked for {elapsed:.2f}s"
assert pump(lambda: dlg.linear_preview._resolver is not None), "preview never arrived"
print(f"  preview fetched asynchronously ({elapsed*1000:.0f}ms to return, resolver set later)")
print("PASS threading: no network on the UI thread")
