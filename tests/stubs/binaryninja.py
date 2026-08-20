import os
_UD = os.environ.get("STUB_USER_DIR") or None
def user_directory(): return _UD
def log_info(*a): print("INFO:", *a)
def log_error(*a): print("ERROR:", *a)
class Settings:
    def set_string(self, *a): pass
class _P: pass
import sys, types
plugin = types.ModuleType("binaryninja.plugin"); plugin.PluginCommand = _P
sys.modules["binaryninja.plugin"] = plugin
def show_message_box(title, text, *a, **k): print("MSGBOX:", title, "|", text)
