"""Hotkey-related CLI commands split from the main controller."""
from __future__ import annotations

import os
from pathlib import Path


def show_hotkey_status() -> None:
    from ..hotkeys.base import HotkeyManager
    hk = HotkeyManager.get_current_hotkey()
    print(f"Current hotkey: {hk}")
    import platform

    system = platform.system()
    if system == "Windows":
        startup = (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "prompt-automation.ahk"
        )
        print(f"Windows AHK script: {'OK' if startup.exists() else 'MISSING'} -> {startup}")
    elif system == "Linux":
        yaml_path = Path.home() / ".config" / "espanso" / "match" / "prompt-automation.yml"
        print(f"Espanso YAML: {'OK' if yaml_path.exists() else 'MISSING'} -> {yaml_path}")
    elif system == "Darwin":
        script_path = (
            Path.home()
            / "Library"
            / "Application Scripts"
            / "prompt-automation"
            / "macos.applescript"
        )
        print(f"AppleScript: {'OK' if script_path.exists() else 'MISSING'} -> {script_path}")
    else:
        print("Unknown platform: status not available")


def repair_hotkey() -> None:
    from ..hotkeys.base import HotkeyManager

    if not HotkeyManager.ensure_hotkey_dependencies():
        print("[prompt-automation] Hotkey dependencies missing; see above for install instructions.")
        return
    HotkeyManager.update_hotkeys()


__all__ = ["show_hotkey_status", "repair_hotkey"]

