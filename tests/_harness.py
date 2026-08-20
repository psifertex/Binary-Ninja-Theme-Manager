"""Shared test setup: stub out Binary Ninja and import the plugin."""

import importlib
import os
import sys
import tempfile

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)

sys.path.insert(0, os.path.join(TESTS, "stubs"))
sys.path.insert(0, os.path.dirname(REPO))

USER_DIR = None


def load_plugin(user_dir=None):
    """Import theme_manager against the stubs.

    Pass user_dir="" to simulate Binary Ninja reporting no user directory.
    The stub reads the environment at import time, so this must run first.
    """
    global USER_DIR
    USER_DIR = tempfile.mkdtemp() if user_dir is None else user_dir
    os.environ["STUB_USER_DIR"] = USER_DIR
    return importlib.import_module(os.path.basename(REPO) + ".theme_manager")


def qt_app():
    """Return a QApplication, creating one if needed.

    Qt calls qFatal() -- which aborts the process, uncatchable from Python --
    if a QWidget is constructed with no QApplication alive. Any test that
    builds widgets must call this first.
    """
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
