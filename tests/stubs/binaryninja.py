import os
_UD = os.environ.get("STUB_USER_DIR") or None
def user_directory(): return _UD
def log_debug(*a): print("DEBUG:", *a)
def log_info(*a): print("INFO:", *a)
def log_warn(*a): print("WARN:", *a)
def log_error(*a): print("ERROR:", *a)
_SETTINGS = {}
_SCHEMAS = {}
_GROUPS = {}

class Settings:
    def set_string(self, key, value): _SETTINGS[key] = value
    def register_group(self, group, title): _GROUPS[group] = title; return True
    def register_setting(self, key, properties):
        import json as _json
        schema = _json.loads(properties)
        _SCHEMAS[key] = schema
        _SETTINGS.setdefault(key, schema.get("default"))
        return True
    def get_string_list(self, key, *a):
        if key not in _SCHEMAS:
            raise KeyError(f"unregistered setting {key}")
        return list(_SETTINGS.get(key) or [])
class _P: pass
import sys, types
plugin = types.ModuleType("binaryninja.plugin"); plugin.PluginCommand = _P
sys.modules["binaryninja.plugin"] = plugin
def show_message_box(title, text, *a, **k): print("MSGBOX:", title, "|", text)
