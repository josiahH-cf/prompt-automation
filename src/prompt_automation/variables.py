"""Input handling for template placeholders."""
from __future__ import annotations

import os
import platform
import shutil
from .utils import safe_run
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .errorlog import get_logger


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


def _editor_prompt() -> str | None:
    """Use ``$EDITOR`` as fallback."""
    try:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        editor = os.environ.get(
            "EDITOR", "notepad" if platform.system() == "Windows" else "nano"
        )
        safe_run([editor, path])
        return Path(path).read_text().strip()
    except Exception as e:  # pragma: no cover - depends on editor
        _log.error("editor prompt failed: %s", e)
        return None


def get_variables(placeholders: List[Dict], initial: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return dict of placeholder values using GUI/editor/CLI fallbacks.

    ``initial`` allows pre-filled values (e.g. from a GUI) to be provided.
    Any placeholders missing from ``initial`` will fall back to the usual
    prompt mechanisms.
    """

    values: Dict[str, str] = dict(initial or {})
    for ph in placeholders:
        name = ph["name"]
        if name in values and values[name] != "":
            val = values[name]
        else:
            label = ph.get("label", name)
            opts = ph.get("options")
            multiline = ph.get("multiline", False)
            val = _gui_prompt(label, opts, multiline)
            if val is None:
                val = _editor_prompt()
            if val is None:
                _log.info("CLI fallback for %s", label)
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
        values[name] = val
    return values

