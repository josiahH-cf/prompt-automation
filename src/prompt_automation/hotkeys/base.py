from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import List

from .linux import _update_linux
from .macos import _update_macos
from .windows import _update_windows
try:
    # Lazy import so that tests can patch storage internals; optional at runtime
    from ..variables.storage import _read_hotkey_from_settings  # type: ignore
except Exception:  # pragma: no cover - defensive
    def _read_hotkey_from_settings():  # type: ignore
        return None

CONFIG_DIR = Path.home() / ".prompt-automation"
HOTKEY_FILE = CONFIG_DIR / "hotkey.json"


class HotkeyManager:
    """Manage capture, persistence and system integration of hotkeys."""

    @staticmethod
    def capture_hotkey() -> str:
        """Capture a hotkey combination from the user."""
        try:  # pragma: no cover - optional dependency
            import keyboard

            print("Press desired hotkey combination...")
            combo = keyboard.read_hotkey(suppress=False)
            print(f"Captured hotkey: {combo}")
            return combo
        except Exception:  # pragma: no cover - fallback
            return input("Enter hotkey (e.g. ctrl+shift+j): ").strip()

    @staticmethod
    def save_mapping(hotkey: str) -> None:
        """Persist the hotkey mapping and enable GUI mode."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        HOTKEY_FILE.write_text(json.dumps({"hotkey": hotkey}))
        env_file = CONFIG_DIR / "environment"
        env_file.write_text("PROMPT_AUTOMATION_GUI=1\n")

    @staticmethod
    def update_system_hotkey(hotkey: str) -> None:
        """Update platform-specific hotkey configuration."""
        system = platform.system()
        if os.environ.get("PROMPT_AUTOMATION_DEBUG"):
            print(
                f"[prompt-automation] hotkey_registration_start os={system} hotkey={hotkey}"
            )
        if system == "Windows":
            _update_windows(hotkey)
        elif system == "Linux":
            _update_linux(hotkey)
        elif system == "Darwin":
            _update_macos(hotkey)

    @classmethod
    def assign_hotkey(cls) -> None:
        hotkey = cls.capture_hotkey()
        if not hotkey:
            print("[prompt-automation] No hotkey provided")
            return
        cls.save_mapping(hotkey)
        cls.update_system_hotkey(hotkey)
        print(f"[prompt-automation] Hotkey set to {hotkey}")

    @classmethod
    def update_hotkeys(cls) -> None:
        """Update existing hotkeys to use current system configuration."""
        if not HOTKEY_FILE.exists():
            print("[prompt-automation] No existing hotkey configuration found. Setting up default hotkey...")
            cls.save_mapping("ctrl+shift+j")
            cls.update_system_hotkey("ctrl+shift+j")
            print("[prompt-automation] Default hotkey (ctrl+shift+j) configured")
            return

        try:
            config = json.loads(HOTKEY_FILE.read_text())
            hotkey = config.get("hotkey", "ctrl+shift+j")
            cls.update_system_hotkey(hotkey)

            env_file = CONFIG_DIR / "environment"
            env_file.write_text("PROMPT_AUTOMATION_GUI=1\n")

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
                    print(
                        f"[prompt-automation] Hotkey {hotkey} updated but script not found at expected location"
                    )
            elif system == "Linux":
                yaml_path = Path.home() / ".config" / "espanso" / "match" / "prompt-automation.yml"
                if yaml_path.exists():
                    print(f"[prompt-automation] Hotkey {hotkey} updated and verified at {yaml_path}")
                else:
                    print(
                        f"[prompt-automation] Hotkey {hotkey} updated but configuration not found at expected location"
                    )
            elif system == "Darwin":
                script_path = (
                    Path.home()
                    / "Library"
                    / "Application Scripts"
                    / "prompt-automation"
                    / "macos.applescript"
                )
                if script_path.exists():
                    print(f"[prompt-automation] Hotkey {hotkey} updated and verified at {script_path}")
                else:
                    print(
                        f"[prompt-automation] Hotkey {hotkey} updated but script not found at expected location"
                    )
            else:
                print(f"[prompt-automation] Hotkey {hotkey} updated for unknown platform")
        except Exception as e:
            print(f"[prompt-automation] Failed to update hotkey: {e}")
            try:
                cls.save_mapping("ctrl+shift+j")
                cls.update_system_hotkey("ctrl+shift+j")
                print("[prompt-automation] Fallback: default hotkey (ctrl+shift+j) configured")
            except Exception as e2:  # pragma: no cover - cascading failure
                print(f"[prompt-automation] Failed to configure fallback hotkey: {e2}")

    @staticmethod
    def ensure_hotkey_dependencies() -> bool:
        """Ensure platform-specific hotkey dependencies are available."""
        system = platform.system()
        missing: List[str] = []

        if system == "Windows":
            ahk_paths = [
                "AutoHotkey",
                r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe",
                r"C:\\Program Files (x86)\\AutoHotkey\\AutoHotkey.exe",
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

    @staticmethod
    def get_current_hotkey() -> str:
        """Get the currently configured hotkey."""
        if not HOTKEY_FILE.exists():
            # Fall back to settings.json provided default hotkey or project default
            hk = _read_hotkey_from_settings()
            return hk or "ctrl+shift+j"
        try:
            config = json.loads(HOTKEY_FILE.read_text())
            hk = config.get("hotkey")
            if isinstance(hk, str) and hk.strip():
                return hk.strip()
            # If file malformed / blank, fallback to settings-defined default
            settings_default = _read_hotkey_from_settings()
            return settings_default or "ctrl+shift+j"
        except Exception:
            settings_default = _read_hotkey_from_settings()
            return settings_default or "ctrl+shift+j"
