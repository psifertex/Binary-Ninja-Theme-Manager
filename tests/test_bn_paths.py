"""bn_paths locates the Binary Ninja install the tests run against."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bn_paths

# Hermetic: the caller may already have BN_USER_DIRECTORY set.
inherited = os.environ.pop("BN_USER_DIRECTORY", None)
default = bn_paths.user_directory()
assert default, "no default user directory"
print("  platform default user directory:", default)

# BN_USER_DIRECTORY wins, matching how the core resolves it
override = tempfile.mkdtemp()
os.environ["BN_USER_DIRECTORY"] = override
assert bn_paths.user_directory() == override, bn_paths.user_directory()
print("  BN_USER_DIRECTORY honored:", override)

# an empty value is not an override
os.environ["BN_USER_DIRECTORY"] = ""
assert bn_paths.user_directory() == default
print("  empty BN_USER_DIRECTORY ignored")

# lastrun is read from whichever directory won
os.environ["BN_USER_DIRECTORY"] = override
with open(os.path.join(override, "lastrun"), "w") as f:
    f.write(os.path.dirname(os.path.abspath(__file__)) + "\n")
assert bn_paths.lastrun_dir() == os.path.dirname(os.path.abspath(__file__))
print("  lastrun read from the overridden directory")

# a missing lastrun explains itself rather than throwing IOError
os.environ["BN_USER_DIRECTORY"] = tempfile.mkdtemp()
try:
    bn_paths.lastrun_dir()
except RuntimeError as e:
    assert "Launch Binary Ninja once" in str(e), e
    print("  missing lastrun gives an actionable error")
else:
    raise SystemExit("expected RuntimeError for missing lastrun")

del os.environ["BN_USER_DIRECTORY"]
assert bn_paths.user_directory() == default
if inherited is not None:
    os.environ["BN_USER_DIRECTORY"] = inherited
print("PASS bn_paths: BN_USER_DIRECTORY override and lastrun resolution")
