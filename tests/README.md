# Tests

Run them with any Python 3:

```
python3 tests/run.py                 # everything
python3 tests/run.py test_search.py  # one file
```

`run.py` finds Binary Ninja through the `lastrun` file in BN's user folder,
then re-runs each test under `bnpython3`, so the suite exercises the same
interpreter and Qt build the plugin loads under. `BN_USER_DIRECTORY` selects a
different profile, and therefore a different install:

```
BN_USER_DIRECTORY=~/profiles/dev python3 tests/run.py
```

`stubs/` stands in for `binaryninja` and `binaryninjaui`, which cannot be
imported outside a running Binary Ninja. The `binaryninjaui` stub mirrors the
real module's theme functions, including rejecting a theme that BN has not
scanned yet, so the install-then-apply path is covered.

Tests that build widgets must call `qt_app()` before doing so. Qt aborts the
process through `qFatal()` when a `QWidget` is constructed with no
`QApplication` alive, and that is not catchable from Python.
