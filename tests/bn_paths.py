"""Locate the Binary Ninja install to test against.

Binary Ninja records the last install that ran in a `lastrun` file inside its
user folder, holding the directory that contains the `binaryninja` binary and
`bnpython3`. Using it means the tests follow whichever build you last launched
instead of hardcoding a path.
"""

import os
import sys


def user_directory():
    """BN's user folder. https://docs.binary.ninja/guide/#user-folder

    BN_USER_DIRECTORY overrides the default, so tests follow the same profile
    a `BN_USER_DIRECTORY=... binaryninja` run would have written lastrun into.
    """
    override = os.environ.get("BN_USER_DIRECTORY")
    if override:
        return override
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Binary Ninja")
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA", ""), "Binary Ninja")
    return os.path.expanduser("~/.binaryninja")


def lastrun_dir():
    path = os.path.join(user_directory(), "lastrun")
    try:
        with open(path, "r", encoding="utf-8") as f:
            directory = f.read().strip()
    except OSError as e:
        raise RuntimeError(
            f"Could not read {path}: {e}\n"
            "Launch Binary Ninja once so it records the install to test against."
        )
    if not os.path.isdir(directory):
        raise RuntimeError(f"{path} points at {directory!r}, which is not a directory.")
    return directory


def bn_python():
    """Path to bnpython3, the interpreter the plugin actually runs under."""
    directory = lastrun_dir()
    exe = "bnpython3.exe" if sys.platform == "win32" else "bnpython3"
    path = os.path.join(directory, exe)
    if not os.path.exists(path):
        raise RuntimeError(f"No {exe} in {directory}")
    return path


def pyside_dir():
    """Directory holding BN's bundled PySide6.

    bnpython3 does not carry it on sys.path by default, and BN's PySide6 is
    built against BN's interpreter, so the system one must not be substituted.
    """
    directory = lastrun_dir()
    for rel in ("../Resources/python3", "python3", "../python3", "../lib/python3"):
        candidate = os.path.normpath(os.path.join(directory, rel))
        if os.path.isdir(os.path.join(candidate, "PySide6")):
            return candidate
    raise RuntimeError(f"Could not find bundled PySide6 near {directory}")


if __name__ == "__main__":
    print("user directory:", user_directory())
    print("lastrun:       ", lastrun_dir())
    print("bnpython3:     ", bn_python())
    print("PySide6:       ", pyside_dir())
