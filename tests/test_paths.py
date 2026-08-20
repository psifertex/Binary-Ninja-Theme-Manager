import os
import sys
import _harness as harness
from _harness import load_plugin

tm = load_plugin()

# 1. normal: user_directory() gives a path
d = tm.theme_dir()
assert d == os.path.join(harness.USER_DIR, "community-themes"), d
assert tm.ensure_dirs() == d and os.path.isdir(d)
open(os.path.join(d, "a.bntheme"), "w").write('{"name": "Alpha"}')
assert tm.get_locally_installed_files() == ["a.bntheme"]
assert tm.get_theme_display_name("a.bntheme") == "Alpha"
assert tm.load_local_theme_json("a.bntheme") == {"name": "Alpha"}
print("PASS normal:", d)

# 2. no user directory -> nothing resolved, nothing created
legacy = os.path.expanduser("~/.binaryninja")
tm.user_directory = lambda: None
assert tm.theme_dir() is None
assert tm.ensure_dirs() is None
assert tm.get_locally_installed_files() == []
assert tm.load_local_theme_json("a.bntheme") is None
assert tm.get_theme_display_name("a.bntheme") == "a.bntheme"
assert tm.download_theme({"name": "x.bntheme", "download_url": "http://127.0.0.1:1/x"}) is None
assert not os.path.isdir(legacy), "created ~/.binaryninja!"
assert not hasattr(tm, "LEGACY_BASE_DIR")
print("PASS no-user-dir: nothing resolved, ~/.binaryninja absent")
