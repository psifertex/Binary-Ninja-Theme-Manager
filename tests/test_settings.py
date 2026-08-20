"""Theme repositories come from a Binary Ninja setting, not a hardcoded list."""

import json

from _harness import load_plugin, qt_app

qt_app()
tm = load_plugin()
import binaryninja as bn

# --- registration ---
assert "swatch" in bn._GROUPS, bn._GROUPS
schema = bn._SCHEMAS[tm.REPOS_SETTING]
assert schema["type"] == "array", schema
assert schema["default"] == tm.DEFAULT_REPOS
# matches how BN declares its own array settings: no elementType key
assert "elementType" not in schema, schema
print(f"  registered {tm.REPOS_SETTING} as an array with "
      f"{len(schema['default'])} defaults")

# --- parsing owner/repo[/path] ---
assert tm.parse_repo("Vector35/community-themes") == ("Vector35", "community-themes", "")
assert tm.parse_repo("catppuccin/binary-ninja/themes") == ("catppuccin", "binary-ninja", "themes")
assert tm.parse_repo("a/b/c/d/e") == ("a", "b", "c/d/e"), tm.parse_repo("a/b/c/d/e")
assert tm.parse_repo("/Vector35/community-themes/") == ("Vector35", "community-themes", "")
assert tm.parse_repo("nope") is None
assert tm.parse_repo("") is None
print("  owner/repo/path parsed, including nested paths and stray slashes")

# --- defaults round-trip ---
repos = tm.get_repos()
assert len(repos) == len(tm.DEFAULT_REPOS), repos
assert ("Vector35", "community-themes", "") in repos
assert ("catppuccin", "binary-ninja", "themes") in repos
print("  defaults resolve to", len(repos), "repositories")

# --- a user-configured list is honored, malformed entries skipped ---
bn._SETTINGS[tm.REPOS_SETTING] = ["me/my-themes", "garbage", "you/yours/sub"]
repos = tm.get_repos()
assert repos == [("me", "my-themes", ""), ("you", "yours", "sub")], repos
print("  custom list honored, malformed entry skipped:", repos)

# --- the dialog uses the configured repos, not a constant ---
class Resp:
    status_code = 200
    def json(self): return []
tm.requests.get = lambda url, **kw: Resp()
tm.SESSION_REMOTE_CACHE.clear()
dlg = tm.ThemeManagerDialog()
assert len(dlg._attempted) == 2, dlg._attempted
assert ("me", "my-themes", "") in dlg._attempted, dlg._attempted
print("  dialog fetched exactly the configured repositories")

bn._SETTINGS[tm.REPOS_SETTING] = tm.DEFAULT_REPOS
print("PASS settings: repositories are configurable")
