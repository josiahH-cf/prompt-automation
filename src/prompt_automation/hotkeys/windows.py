from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _to_ahk(hotkey: str) -> str:
    mapping = {"ctrl": "^", "shift": "+", "alt": "!", "win": "#", "cmd": "#"}
    parts = hotkey.lower().split("+")
    mods, key = parts[:-1], parts[-1]
    return "".join(mapping.get(m, m) for m in mods) + key


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
