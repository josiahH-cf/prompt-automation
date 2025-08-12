"""Hotkey management utilities."""
from .base import HotkeyManager

__all__ = [
    "HotkeyManager",
    "capture_hotkey",
    "save_mapping",
    "update_system_hotkey",
    "assign_hotkey",
    "update_hotkeys",
    "ensure_hotkey_dependencies",
    "get_current_hotkey",
]

capture_hotkey = HotkeyManager.capture_hotkey
save_mapping = HotkeyManager.save_mapping
update_system_hotkey = HotkeyManager.update_system_hotkey
assign_hotkey = HotkeyManager.assign_hotkey
update_hotkeys = HotkeyManager.update_hotkeys
ensure_hotkey_dependencies = HotkeyManager.ensure_hotkey_dependencies
get_current_hotkey = HotkeyManager.get_current_hotkey
