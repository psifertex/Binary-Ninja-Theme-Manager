import os
import sys
from _harness import load_plugin

tm = load_plugin()

calls = []
class R:
    status_code = 500
    def json(self): return []
def fake_get(url, **kw):
    calls.append(url); return R()
tm.requests.get = fake_get

# simulate 10 keystrokes over 5 repos
for _ in range(10):
    for owner, repo, path in tm.REPOS:
        tm.fetch_repo_themes(owner, repo, path)
print("HTTP calls for 10 keystrokes x 5 repos:", len(calls), "(old code would be 50)")
assert len(calls) == 5, len(calls)

# after the cooldown expires, it retries once more per repo
tm.FETCH_RETRY_SECONDS = -1
for owner, repo, path in tm.REPOS:
    tm.fetch_repo_themes(owner, repo, path)
print("after cooldown:", len(calls))
assert len(calls) == 10

# a success caches normally and clears the failure record
tm.FETCH_RETRY_SECONDS = 60
tm.FAILED_FETCH_TIMES.clear()   # leave the cooldown window
class OK:
    status_code = 200
    def json(self): return [{"type": "file", "name": "a.bntheme", "download_url": "u"}]
tm.requests.get = lambda url, **kw: (calls.append(url), OK())[1]
o, r, p = tm.REPOS[0]
print("themes:", tm.fetch_repo_themes(o, r, p))
n = len(calls)
for _ in range(5): tm.fetch_repo_themes(o, r, p)
assert len(calls) == n, "cached success re-fetched"
assert (o, r, p) not in tm.FAILED_FETCH_TIMES
print("PASS: failure backoff + success caching both correct")
