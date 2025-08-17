"""GUI helper functions for variable prompts."""
from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import List

from ..errorlog import get_logger
from ..utils import safe_run


_log = get_logger(__name__)


def _gui_prompt(label: str, opts: List[str] | None, multiline: bool) -> str | None:
    """Try platform GUI for input; return ``None`` on failure."""
    sys = platform.system()
    try:
        safe_label = label.replace('"', '\"')
        if opts:
            clean_opts = [o.replace('"', '\"') for o in opts]
            if sys == "Linux" and shutil.which("zenity"):
                cmd = ["zenity", "--list", "--column", safe_label, *clean_opts]
            elif sys == "Darwin" and shutil.which("osascript"):
                opts_s = ",".join(clean_opts)
                cmd = ["osascript", "-e", f'choose from list {{{opts_s}}} with prompt "{safe_label}"']
            elif sys == "Windows":
                arr = ";".join(clean_opts)
                cmd = ["powershell", "-Command", f'$a="{arr}".Split(";");$a|Out-GridView -OutputMode Single -Title "{safe_label}"']
            else:
                return None
        else:
            if sys == "Linux" and shutil.which("zenity"):
                cmd = ["zenity", "--entry", "--text", safe_label]
            elif sys == "Darwin" and shutil.which("osascript"):
                cmd = ["osascript", "-e", f'display dialog "{safe_label}" default answer "']
            elif sys == "Windows":
                cmd = ["powershell", "-Command", f'Read-Host "{safe_label}"']
            else:
                return None
        res = safe_run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception as e:  # pragma: no cover - GUI may be missing
        _log.error("GUI prompt failed: %s", e)
    return None


def _gui_file_prompt(label: str) -> str | None:
    """Enhanced cross-platform file dialog with better accessibility."""
    sys = platform.system()
    try:
        safe_label = label.replace('"', '\"')
        if sys == "Linux" and shutil.which("zenity"):
            cmd = ["zenity", "--file-selection", "--title", safe_label]
        elif sys == "Darwin" and shutil.which("osascript"):
            cmd = ["osascript", "-e", f'choose file with prompt "{safe_label}"']
        elif sys == "Windows":
            cmd = [
                "powershell",
                "-Command",
                (
                    "Add-Type -AssemblyName System.Windows.Forms;",
                    "$f=New-Object System.Windows.Forms.OpenFileDialog;",
                    f'$f.Title="{safe_label}";',
                    "$f.Filter='All Files (*.*)|*.*';",
                    "$f.CheckFileExists=$true;",
                    "$null=$f.ShowDialog();$f.FileName"
                ),
            ]
        else:
            return None
        res = safe_run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            result = res.stdout.strip()
            if result and Path(result).exists():
                return result
    except Exception as e:  # pragma: no cover - GUI may be missing
        _log.error("GUI file prompt failed: %s", e)
    return None
