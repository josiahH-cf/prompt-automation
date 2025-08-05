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
    # Set GUI as default mode for hotkey usage
    env_file = CONFIG_DIR / "environment"
    env_file.write_text("PROMPT_AUTOMATION_GUI=1\n")


def _update_linux(hotkey: str) -> None:
    trigger = _to_espanso(hotkey)
    match_dir = Path.home() / ".config" / "espanso" / "match"
    match_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = match_dir / "prompt-automation.yml"
    
    # Create espanso configuration with fallback
    yaml_content = (
        f'matches:\n'
        f'  - trigger: "{trigger}"\n'
        f'    run: |\n'
        f'      # Try GUI first, fall back to terminal\n'
        f'      prompt-automation --gui || prompt-automation --terminal\n'
        f'    propagate: false\n'
    )
    yaml_path.write_text(yaml_content)
    
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
        f"; {hotkey} launches the prompt-automation with GUI fallback to CLI\n"
        f"{ahk_hotkey}::\n"
        "{\n"
        "    ; Try GUI mode first\n"
        "    Run, prompt-automation --gui,, Hide\n"
        "    if ErrorLevel\n"
        "    {\n"
        "        Run, prompt-automation.exe --gui,, Hide\n"
        "        if ErrorLevel\n"
        "        {\n"
        "            Run, python -m prompt_automation --gui,, Hide\n"
        "            if ErrorLevel\n"
        "            {\n"
        "                ; If GUI fails, fall back to terminal mode\n"
        "                Run, prompt-automation --terminal\n"
        "                if ErrorLevel\n"
        "                {\n"
        "                    Run, prompt-automation.exe --terminal\n"
        "                    if ErrorLevel\n"
        "                    {\n"
        "                        Run, python -m prompt_automation --terminal\n"
        "                        if ErrorLevel\n"
        "                        {\n"
        "                            ; Final fallback - show error\n"
        "                            MsgBox, 16, Error, prompt-automation failed to start. Please check installation.\n"
        "                        }\n"
        "                    }\n"
        "                }\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    return\n"
        "}\n"
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
    
    applescript_content = (
        'on run\n'
        '    try\n'
        '        do shell script "prompt-automation --gui &"\n'
        '    on error\n'
        '        try\n'
        '            do shell script "prompt-automation --terminal &"\n'
        '        on error\n'
        '            display dialog "prompt-automation failed to start. Please check installation." buttons {"OK"} default button "OK"\n'
        '        end try\n'
        '    end try\n'
        'end run\n'
    )
    script_path.write_text(applescript_content)
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


def update_hotkeys() -> None:
    """Update existing hotkeys to use current system configuration."""
    if not HOTKEY_FILE.exists():
        print("[prompt-automation] No existing hotkey configuration found. Setting up default hotkey...")
        # Set up default hotkey
        save_mapping("ctrl+shift+j")
        update_system_hotkey("ctrl+shift+j")
        print("[prompt-automation] Default hotkey (ctrl+shift+j) configured")
        return
    
    try:
        config = json.loads(HOTKEY_FILE.read_text())
        hotkey = config.get("hotkey", "ctrl+shift+j")
        
        # Always update the system hotkey to ensure it's current
        update_system_hotkey(hotkey)
        
        # Ensure GUI mode is enabled
        env_file = CONFIG_DIR / "environment"
        env_file.write_text("PROMPT_AUTOMATION_GUI=1\n")
        
        # Verify the hotkey files are in place
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
            if startup.exists():
                print(f"[prompt-automation] Hotkey {hotkey} updated and verified at {startup}")
            else:
                print(f"[prompt-automation] Hotkey {hotkey} updated but script not found at expected location")
        elif system == "Linux":
            yaml_path = Path.home() / ".config" / "espanso" / "match" / "prompt-automation.yml"
            if yaml_path.exists():
                print(f"[prompt-automation] Hotkey {hotkey} updated and verified at {yaml_path}")
            else:
                print(f"[prompt-automation] Hotkey {hotkey} updated but configuration not found at expected location")
        elif system == "Darwin":
            script_path = Path.home() / "Library" / "Application Scripts" / "prompt-automation" / "macos.applescript"
            if script_path.exists():
                print(f"[prompt-automation] Hotkey {hotkey} updated and verified at {script_path}")
            else:
                print(f"[prompt-automation] Hotkey {hotkey} updated but script not found at expected location")
        else:
            print(f"[prompt-automation] Hotkey {hotkey} updated for unknown platform")
            
    except Exception as e:
        print(f"[prompt-automation] Failed to update hotkey: {e}")
        # Try to set up default as fallback
        try:
            save_mapping("ctrl+shift+j")
            update_system_hotkey("ctrl+shift+j")
            print("[prompt-automation] Fallback: default hotkey (ctrl+shift+j) configured")
        except Exception as e2:
            print(f"[prompt-automation] Failed to configure fallback hotkey: {e2}")


def ensure_hotkey_dependencies() -> bool:
    """Ensure platform-specific hotkey dependencies are available."""
    system = platform.system()
    missing = []
    
    if system == "Windows":
        # Check for AutoHotkey
        ahk_paths = [
            "AutoHotkey",  # In PATH
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
        ]
        
        ahk_found = False
        for path in ahk_paths:
            try:
                if path == "AutoHotkey":
                    result = subprocess.run(["where", "AutoHotkey"], capture_output=True, text=True)
                    if result.returncode == 0:
                        ahk_found = True
                        break
                else:
                    if Path(path).exists():
                        ahk_found = True
                        break
            except Exception:
                continue
                
        if not ahk_found:
            missing.append("AutoHotkey")
            
    elif system == "Linux":
        # Check for espanso
        try:
            subprocess.run(["espanso", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("espanso")
            
    if missing:
        print(f"[prompt-automation] Missing hotkey dependencies: {', '.join(missing)}")
        if system == "Windows" and "AutoHotkey" in missing:
            print("[prompt-automation] Install AutoHotkey from: https://www.autohotkey.com/")
            print("[prompt-automation] Or use: winget install AutoHotkey.AutoHotkey")
        elif system == "Linux" and "espanso" in missing:
            print("[prompt-automation] Install espanso from: https://espanso.org/install/")
        return False
        
    return True


def get_current_hotkey() -> str:
    """Get the currently configured hotkey."""
    if not HOTKEY_FILE.exists():
        return "ctrl+shift+j"  # Default
    try:
        config = json.loads(HOTKEY_FILE.read_text())
        return config.get("hotkey", "ctrl+shift+j")
    except Exception:
        return "ctrl+shift+j"

