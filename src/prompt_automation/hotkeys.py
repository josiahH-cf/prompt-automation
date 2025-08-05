"""Utilities for assigning and updating global hotkeys."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path


CONFIG_DIR = Path.home() / ".prompt-automation"
HOTKEY_FILE = CONFIG_DIR / "hotkey.json"


def capture_hotkey() -> str:
    """Capture a hotkey combination from the user.

    Uses the ``keyboard`` package when available, otherwise falls back to a
    simple text prompt. Returned hotkey strings use ``ctrl+shift+j`` style
    notation.
    """
    try:  # pragma: no cover - optional dependency
        import keyboard

        print("Press desired hotkey combination...")
        combo = keyboard.read_hotkey(suppress=False)
        print(f"Captured hotkey: {combo}")
        return combo
    except Exception:  # pragma: no cover - fallback
        return input("Enter hotkey (e.g. ctrl+shift+j): ").strip()


def _to_espanso(hotkey: str) -> str:
    parts = hotkey.lower().split("+")
    mods, key = parts[:-1], parts[-1]
    if mods:
        return "+".join(f"<{m}>" for m in mods) + "+" + key
    return key


def _to_ahk(hotkey: str) -> str:
    mapping = {"ctrl": "^", "shift": "+", "alt": "!", "win": "#", "cmd": "#"}
    parts = hotkey.lower().split("+")
    mods, key = parts[:-1], parts[-1]
    return "".join(mapping.get(m, m) for m in mods) + key


def save_mapping(hotkey: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HOTKEY_FILE.write_text(json.dumps({"hotkey": hotkey}))


def _update_linux(hotkey: str) -> None:
    trigger = _to_espanso(hotkey)
    match_dir = Path.home() / ".config" / "espanso" / "match"
    match_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = match_dir / "prompt-automation.yml"
    yaml_path.write_text(
        f'matches:\n  - trigger: "{trigger}"\n    run: "prompt-automation --gui"\n    propagate: false\n'
    )
    try:  # pragma: no cover - external tool
        subprocess.run(["espanso", "restart"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _update_windows(hotkey: str) -> None:
    ahk_hotkey = _to_ahk(hotkey)
    startup = (
        Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    startup.mkdir(parents=True, exist_ok=True)
    script_path = startup / "prompt-automation.ahk"
    content = (
        "#NoEnv\n#SingleInstance Force\n#InstallKeybdHook\n#InstallMouseHook\n"
        "#MaxHotkeysPerInterval 99000000\n#HotkeyInterval 99000000\n#KeyHistory 0\n\n"
        f"; {hotkey} launches the prompt-automation GUI without opening a console\n"
        f"{ahk_hotkey}::\n"
        "{\n    Run, prompt-automation.exe --gui,, Hide\n    return\n}\n"
    )
    script_path.write_text(content)
    try:  # pragma: no cover - external tool
        subprocess.Popen(["AutoHotkey", str(script_path)])
    except Exception:
        pass


def _update_macos(hotkey: str) -> None:  # pragma: no cover - macOS specific
    script_dir = Path.home() / "Library" / "Application Scripts" / "prompt-automation"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "macos.applescript"
    script_path.write_text('on run\n    do shell script "prompt-automation --gui &"\nend run\n')
    print(
        "[prompt-automation] macOS hotkey updated. Assign the new hotkey via System Preferences > Keyboard > Shortcuts."
    )


def update_system_hotkey(hotkey: str) -> None:
    system = platform.system()
    if system == "Windows":
        _update_windows(hotkey)
    elif system == "Linux":
        _update_linux(hotkey)
    elif system == "Darwin":
        _update_macos(hotkey)


def assign_hotkey() -> None:
    hotkey = capture_hotkey()
    if not hotkey:
        print("[prompt-automation] No hotkey provided")
        return
    save_mapping(hotkey)
    update_system_hotkey(hotkey)
    print(f"[prompt-automation] Hotkey set to {hotkey}")

