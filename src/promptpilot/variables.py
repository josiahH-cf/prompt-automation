"""Input handling for template placeholders."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List


def _gui_prompt(label: str, opts: List[str] | None, multiline: bool) -> str | None:
    """Try platform GUI for input; return ``None`` on failure."""
    sys = platform.system()
    try:
        if opts:
            if sys == "Linux" and shutil.which("zenity"):
                cmd = ["zenity", "--list", "--column", label, *opts]
            elif sys == "Darwin" and shutil.which("osascript"):
                opts_s = ",".join(opts)
                cmd = ["osascript", "-e", f'choose from list {{{opts_s}}} with prompt \"{label}\"']
            elif sys == "Windows":
                arr = ";".join(opts)
                cmd = ["powershell", "-Command", f'$a="{arr}".Split(";");$a|Out-GridView -OutputMode Single -Title \"{label}\"']
            else:
                return None
        else:
            if sys == "Linux" and shutil.which("zenity"):
                cmd = ["zenity", "--entry", "--text", label]
            elif sys == "Darwin" and shutil.which("osascript"):
                cmd = ["osascript", "-e", f'display dialog \"{label}\" default answer "']
            elif sys == "Windows":
                cmd = ["powershell", "-Command", f'Read-Host \"{label}\"']
            else:
                return None
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _editor_prompt() -> str | None:
    """Use ``$EDITOR`` as fallback."""
    try:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        editor = os.environ.get("EDITOR", "notepad" if platform.system() == "Windows" else "nano")
        subprocess.run([editor, path])
        return Path(path).read_text().strip()
    except Exception:
        return None


def get_variables(placeholders: List[Dict]) -> Dict[str, str]:
    """Return dict of placeholder values using GUI/editor/CLI fallbacks."""
    values: Dict[str, str] = {}
    for ph in placeholders:
        label = ph.get("label", ph["name"])
        opts = ph.get("options")
        multiline = ph.get("multiline", False)
        val = _gui_prompt(label, opts, multiline)
        if val is None:
            val = _editor_prompt()
        if val is None:
            if opts:
                print(f"{label} options: {', '.join(opts)}")
                val = input(f"{label}: ") or opts[0]
            elif multiline:
                print(f"{label} (end blank line):")
                lines: List[str] = []
                while True:
                    line = input()
                    if not line:
                        break
                    lines.append(line)
                val = "\n".join(lines)
            else:
                val = input(f"{label}: ")
        if ph.get("type") == "number":
            try:
                float(val)
            except ValueError:
                val = "0"
        values[ph["name"]] = val
    return values
