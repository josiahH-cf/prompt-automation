from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _to_ahk(hotkey: str) -> str:
    """Convert a human hotkey like 'ctrl+shift+j' to AHK '^+j' with normalized order.

    AHK expects modifiers in a consistent order and does not care about case.
    We canonicalize modifier order to: ctrl, shift, alt, win/cmd.
    """
    mapping = {"ctrl": "^", "shift": "+", "alt": "!", "win": "#", "cmd": "#"}
    order = {"ctrl": 0, "shift": 1, "alt": 2, "win": 3, "cmd": 3}
    parts = hotkey.lower().split("+")
    mods, key = parts[:-1], parts[-1]
    # normalize modifier order
    mods_sorted = sorted((m for m in mods if m), key=lambda m: order.get(m, 99))
    return "".join(mapping.get(m, m) for m in mods_sorted) + key


def _update_windows(hotkey: str) -> None:
    # Observability: registration start
    if os.environ.get("PROMPT_AUTOMATION_DEBUG"):
        print(
            f"[prompt-automation] hotkey_registration_start os=Windows hotkey={hotkey}"
        )

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

    # Build AHK script without shell chaining operators ("||"). Each attempt is
    # a separate Run with ErrorLevel checks for deterministic fallback.
    content = (
        "#NoEnv\n#SingleInstance Force\n#InstallKeybdHook\n#InstallMouseHook\n"
        "#MaxHotkeysPerInterval 99000000\n#HotkeyInterval 99000000\n#KeyHistory 0\n\n"
        f"; {hotkey} launches prompt-automation with GUI focus and fallbacks\n"
        f"{ahk_hotkey}::\n"
        "{\n"
        "    ; Try to focus existing GUI instance via CLI entrypoints\n"
        "    Run, prompt-automation --focus,, Hide\n"
        "    if ErrorLevel\n"
        "    {\n"
        "        Run, prompt-automation --gui,, Hide\n"
        "        if ErrorLevel\n"
        "        {\n"
        "            Run, prompt-automation.exe --focus,, Hide\n"
        "            if ErrorLevel\n"
        "            {\n"
        "                Run, prompt-automation.exe --gui,, Hide\n"
        "                if ErrorLevel\n"
        "                {\n"
        "                    Run, python -m prompt_automation --focus,, Hide\n"
        "                    if ErrorLevel\n"
        "                    {\n"
        "                        Run, python -m prompt_automation --gui,, Hide\n"
        "                        if ErrorLevel\n"
        "                        {\n"
        "                            ; Python Launcher fallback (common on Windows)\n"
        "                            Run, py -m prompt_automation --focus,, Hide\n"
        "                            if ErrorLevel\n"
        "                            {\n"
        "                                Run, py -m prompt_automation --gui,, Hide\n"
        "                                if ErrorLevel\n"
        "                                {\n"
        "                                    ; Fallback to terminal mode\n"
        "                                    Run, prompt-automation --terminal\n"
        "                                    if ErrorLevel\n"
        "                                    {\n"
        "                                        Run, prompt-automation.exe --terminal\n"
        "                                        if ErrorLevel\n"
        "                                        {\n"
        "                                            Run, python -m prompt_automation --terminal\n"
        "                                            if ErrorLevel\n"
        "                                            {\n"
        "                                                Run, py -m prompt_automation --terminal\n"
        "                                                if ErrorLevel\n"
        "                                                {\n"
        "                                                    ; Final fallback - show error\n"
        "                                                    MsgBox, 16, Error, prompt-automation failed to start. Please check installation.\n"
        "                                                }\n"
        "                                            }\n"
        "                                        }\n"
        "                                    }\n"
        "                                }\n"
        "                            }\n"
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
        if os.environ.get("PROMPT_AUTOMATION_DEBUG"):
            print(
                f"[prompt-automation] hotkey_registration_success os=Windows script={script_path}"
            )
    except Exception as e:
        if os.environ.get("PROMPT_AUTOMATION_DEBUG"):
            print(
                f"[prompt-automation] hotkey_registration_failure os=Windows reason={e}"
            )
        pass
