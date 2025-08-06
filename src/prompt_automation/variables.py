"""Input handling for template placeholders."""
from __future__ import annotations

import os
import platform
import shutil
from .utils import safe_run
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

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
            # Enhanced Windows file dialog with better error handling
            cmd = [
                "powershell",
                "-Command",
                (
                    "Add-Type -AssemblyName System.Windows.Forms;"
                    "$f=New-Object System.Windows.Forms.OpenFileDialog;"
                    f'$f.Title="{safe_label}";'
                    "$f.Filter='All Files (*.*)|*.*';"
                    "$f.CheckFileExists=$true;"
                    "$null=$f.ShowDialog();$f.FileName"
                ),
            ]
        else:
            return None
        res = safe_run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            result = res.stdout.strip()
            # Validate file exists before returning
            if result and Path(result).exists():
                return result
    except Exception as e:  # pragma: no cover - GUI may be missing
        _log.error("GUI file prompt failed: %s", e)
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


def get_variables(
    placeholders: List[Dict], initial: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Return dict of placeholder values using GUI/editor/CLI fallbacks.

    ``initial`` allows pre-filled values (e.g. from a GUI) to be provided.
    Any placeholders missing from ``initial`` will fall back to the usual
    prompt mechanisms.
    """

    values: Dict[str, Any] = dict(initial or {})
    for ph in placeholders:
        name = ph["name"]
        ptype = ph.get("type")
        if name in values and (values[name] not in ("", None) or ptype == "file"):
            val: Any = values[name]
        else:
            label = ph.get("label", name)
            opts = ph.get("options")
            multiline = ph.get("multiline", False) or ptype == "list"
            val = None
            if ptype == "file":
                val = _gui_file_prompt(label)
            else:
                val = _gui_prompt(label, opts, multiline)
                if val is None:
                    val = _editor_prompt()
            if val is None:
                _log.info("CLI fallback for %s", label)
                if opts:
                    print(f"{label} options: {', '.join(opts)}")
                    while True:
                        val = input(f"{label} [{opts[0]}]: ") or opts[0]
                        if val in opts:
                            break
                        print(f"Invalid option. Choose from: {', '.join(opts)}")
                elif ptype == "list" or multiline:
                    print(f"{label} (one per line, blank line to finish):")
                    lines: List[str] = []
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                    val = lines
                elif ptype == "file":
                    while True:
                        val = input(f"{label} path: ")
                        if not val:
                            break
                        path = Path(val).expanduser()
                        if path.exists():
                            break
                        print(f"File not found: {path}")
                        retry = input("Try again? [Y/n]: ").lower()
                        if retry in {'n', 'no'}:
                            val = ""
                            break
                elif ptype == "number":
                    while True:
                        val = input(f"{label}: ")
                        try:
                            float(val)
                            break
                        except ValueError:
                            print("Please enter a valid number.")
                else:
                    val = input(f"{label}: ")

        if ptype == "file" and isinstance(val, str):
            while val:
                path = Path(val).expanduser()
                if path.exists():
                    break
                _log.error("file not found: %s", path)
                new_val = _gui_file_prompt(label) or input(
                    f"{label} not found. Enter new path or leave blank to skip: "
                )
                if not new_val:
                    val = ""
                    break
                val = new_val

        if ptype == "number":
            try:
                float(val)  # type: ignore[arg-type]
            except Exception:
                val = "0"
        if ptype == "list" and isinstance(val, str):
            val = [l for l in val.splitlines() if l]
        values[name] = val
    return values

