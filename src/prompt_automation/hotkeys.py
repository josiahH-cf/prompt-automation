"""Compatibility wrapper for the legacy hotkeys module."""
from .hotkeys import (
    HotkeyManager,
    assign_hotkey,
    capture_hotkey,
    ensure_hotkey_dependencies,
    get_current_hotkey,
    save_mapping,
    update_hotkeys,
    update_system_hotkey,
)

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
