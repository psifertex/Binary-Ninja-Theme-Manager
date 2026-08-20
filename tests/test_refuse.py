from _harness import load_plugin, qt_app

qt_app()   # must precede any widget construction

tm = load_plugin(user_dir="")   # simulate BN reporting no user directory
assert tm.user_directory() is None

built = []
orig = tm.ThemeManagerDialog
class Spy(orig):
    def __init__(self, *a, **k):
        built.append(1); super().__init__(*a, **k)
tm.ThemeManagerDialog = Spy
tm.open_manager(None)
assert not built, "open_manager built a dialog despite no user directory"
print("PASS refuse: open_manager declined, dialog never constructed")
