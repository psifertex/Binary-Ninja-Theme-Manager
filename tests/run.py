#!/usr/bin/env python3
"""Run the test suite under Binary Ninja's own interpreter.

Runs with any Python 3; it locates bnpython3 via BN's `lastrun` file and
re-runs each test there, so the tests exercise the same interpreter and Qt
build the plugin will actually load under.
"""

import os
import subprocess
import sys

import bn_paths

TESTS = os.path.dirname(os.path.abspath(__file__))

TEST_FILES = [
    "test_bn_paths.py",
    "test_paths.py",
    "test_refuse.py",
    "test_backoff.py",
    "test_dialog.py",
    "test_theme_api.py",
    "test_search.py",
    "test_browse.py",
    "test_threading.py",
]


def main():
    try:
        python = bn_paths.bn_python()
        pyside = bn_paths.pyside_dir()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [pyside] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

    version = subprocess.run(
        [python, "-c", "import sys; print(sys.version.split()[0])"],
        capture_output=True, text=True, env=env).stdout.strip()
    print(f"binary ninja: {bn_paths.lastrun_dir()}")
    print(f"interpreter:  {python} ({version})\n")

    selected = sys.argv[1:] or TEST_FILES
    failures = []
    for name in selected:
        result = subprocess.run([python, os.path.join(TESTS, name)],
                                capture_output=True, text=True, env=env)
        if result.returncode == 0:
            print(f"  ok   {name}")
        else:
            failures.append(name)
            print(f"  FAIL {name} (exit {result.returncode})")
            for line in (result.stdout + result.stderr).strip().splitlines()[-8:]:
                print(f"       {line}")

    print()
    if failures:
        print(f"{len(failures)} of {len(selected)} failed: {', '.join(failures)}")
        return 1
    print(f"all {len(selected)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
