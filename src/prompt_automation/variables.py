"""Input handling for template placeholders."""
from __future__ import annotations

import os
import platform
import shutil
from .utils import safe_run
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from .config import HOME_DIR, PROMPTS_DIR
from .errorlog import get_logger


_log = get_logger(__name__)

# Persistence for file placeholders & skip flags
_PERSIST_DIR = HOME_DIR
_PERSIST_FILE = _PERSIST_DIR / "placeholder-overrides.json"

# Settings file (lives alongside templates so it can be edited via GUI / under VCS if desired)
_SETTINGS_DIR = PROMPTS_DIR / "Settings"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"

def _load_settings_payload() -> Dict[str, Any]:
    if not _SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover - corrupted file edge case
        _log.error("failed to load settings file: %s", e)
        return {}

def _write_settings_payload(payload: Dict[str, Any]) -> None:
    try:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(_SETTINGS_FILE)
    except Exception as e:  # pragma: no cover - I/O errors
        _log.error("failed to write settings file: %s", e)

def _sync_settings_from_overrides(overrides: Dict[str, Any]) -> None:
    """Persist override template entries into settings file.

    Layout inside settings.json::
      {
        "file_overrides": {"templates": { "<id>": {"<name>": {"path":...,"skip":bool}}}},
        "generated": true
      }
    """
    payload = _load_settings_payload()
    file_overrides = payload.setdefault("file_overrides", {})
    file_overrides["templates"] = overrides.get("templates", {})
    payload.setdefault("metadata", {})["last_sync"] = platform.platform()
    _write_settings_payload(payload)

def _merge_overrides_with_settings(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge settings file values into overrides (settings take precedence for path/skip).

    Returns merged dict (does not mutate original input).
    """
    settings_payload = _load_settings_payload()
    settings_templates = (
        settings_payload.get("file_overrides", {})
        .get("templates", {})
    )
    if not settings_templates:
        return overrides
    merged = json.loads(json.dumps(overrides))  # deep copy via json
    tmap = merged.setdefault("templates", {})
    for tid, entries in settings_templates.items():
        target = tmap.setdefault(tid, {})
        for name, info in entries.items():
            # Only accept known keys
            if isinstance(info, dict):
                filtered = {k: info[k] for k in ("path", "skip") if k in info}
                if filtered:
                    target[name] = {**target.get(name, {}), **filtered}
    return merged


# ----------------- GUI helpers (existing) -----------------
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


# ----------------- Persistence helpers -----------------

def _load_overrides() -> dict:
    base = {"templates": {}, "reminders": {}}
    if _PERSIST_FILE.exists():
        try:
            base = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            _log.error("failed to load overrides: %s", e)
    # Merge with settings (settings override persist file values)
    merged = _merge_overrides_with_settings(base)
    return merged


def _save_overrides(data: dict) -> None:
    """Save overrides and propagate to settings file."""
    try:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _PERSIST_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(_PERSIST_FILE)
    except Exception as e:
        _log.error("failed to save overrides: %s", e)
    # Best-effort sync (ignore failures silently after logging inside helper)
    try:
        _sync_settings_from_overrides(data)
    except Exception as e:  # pragma: no cover - defensive
        _log.error("failed to sync overrides to settings: %s", e)


def _get_template_entry(data: dict, template_id: int, name: str) -> dict | None:
    return data.get("templates", {}).get(str(template_id), {}).get(name)


def _set_template_entry(data: dict, template_id: int, name: str, payload: dict) -> None:
    data.setdefault("templates", {}).setdefault(str(template_id), {})[name] = payload


def _print_one_time_skip_reminder(data: dict, template_id: int, name: str) -> None:
    # Only print once per template/name
    key = f"{template_id}:{name}"
    reminders = data.setdefault("reminders", {})
    if reminders.get(key):
        return
    reminders[key] = True
    _log.info(
        "Reference file '%s' skipped for template %s. Remove entry in %s to re-enable.",
        name,
        template_id,
        _PERSIST_FILE,
    )
    try:
        import tkinter as tk  # type: ignore
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Reference file skipped",
            f"Reference file ‘{name}’ skipped. Use 'Reset reference files' to re-enable prompts.",
        )
        root.destroy()
    except Exception:
        print(
            f"Reference file ‘{name}’ skipped. Use 'Reset reference files' to re-enable prompts."
        )
    _save_overrides(data)


# ----------------- Extended file placeholder resolution -----------------

def _resolve_file_placeholder(ph: Dict[str, Any], template_id: int, globals_map: Dict[str, Any]) -> str:
    name = ph["name"]
    overrides = _load_overrides()
    entry = _get_template_entry(overrides, template_id, name) or {}

    # Persisted skip takes precedence (GUI/CLI user action only)
    if entry.get("skip"):
        _print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    # If path stored and exists, return
    path_str = entry.get("path")
    if path_str:
        p = Path(path_str).expanduser()
        if p.exists():
            return str(p)
        # if missing ask again

    # Offer selection or skip permanently
    label = ph.get("label", name)
    chosen = _gui_file_prompt(label)
    if not chosen:
        # Ask via CLI fallback for skip/permanent skip
        while True:
            choice = input(f"No file selected for {label}. (c)hoose again, (s)kip, (p)ermanent skip: ").lower().strip() or "c"
            if choice in {"c", "choose"}:
                chosen = _gui_file_prompt(label) or input(f"Enter path for {label} (blank to cancel): ")
                if chosen and Path(chosen).expanduser().exists():
                    break
                if not chosen:
                    continue
            elif choice in {"s", "skip"}:
                return ""
            elif choice in {"p", "perm", "permanent"}:
                _set_template_entry(overrides, template_id, name, {"skip": True})
                _save_overrides(overrides)
                _print_one_time_skip_reminder(overrides, template_id, name)
                return ""
        # fallthrough with chosen
    if chosen and Path(chosen).expanduser().exists():
        _set_template_entry(overrides, template_id, name, {"path": str(Path(chosen).expanduser()), "skip": False})
        _save_overrides(overrides)
        return str(Path(chosen).expanduser())
    return ""


# ----------------- Original functions (modified integration) -----------------
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
    except Exception as e:  # pragma: no cover
        _log.error("editor prompt failed: %s", e)
        return None


def get_variables(
    placeholders: List[Dict], initial: Optional[Dict[str, Any]] = None, template_id: int | None = None, globals_map: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Return dict of placeholder values.

    Added: persistent file placeholder handling with skip logic.
    """
    values: Dict[str, Any] = dict(initial or {})
    globals_map = globals_map or {}

    for ph in placeholders:
        name = ph["name"]
        ptype = ph.get("type")

        if ptype == "file" and template_id is not None:
            # Use extended resolution (template is source of truth)
            path_val = _resolve_file_placeholder(ph, template_id, globals_map)
            values[name] = path_val
            continue

        if name in values and values[name] not in ("", None):
            val: Any = values[name]
        else:
            label = ph.get("label", name)
            opts = ph.get("options")
            multiline = ph.get("multiline", False) or ptype == "list"
            val = None
            if ptype == "file":  # fallback when no template id
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

        if ptype == "file" and isinstance(val, str) and val and template_id is None:
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


def reset_file_overrides() -> bool:
    """Delete persistent file/skip overrides. Returns True if removed."""
    try:
        if _PERSIST_FILE.exists():
            _PERSIST_FILE.unlink()
            # Also clear settings file template section (leave other settings intact)
            if _SETTINGS_FILE.exists():
                payload = _load_settings_payload()
                if payload.get("file_overrides"):
                    payload["file_overrides"]["templates"] = {}
                    _write_settings_payload(payload)
            return True
    except Exception as e:
        _log.error("failed to reset overrides: %s", e)
    return False


def reset_single_file_override(template_id: int, name: str) -> bool:
    """Remove a single template/placeholder override (both local & settings).

    Returns True if something was removed.
    """
    changed = False
    data = _load_overrides()
    tmap = data.get("templates", {}).get(str(template_id)) or {}
    if name in tmap:
        # Remove from base file (need to reload raw file to mutate correctly)
        raw = {"templates": {}, "reminders": {}}
        if _PERSIST_FILE.exists():
            try:
                raw = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        raw_tmap = raw.setdefault("templates", {}).get(str(template_id), {})
        raw_tmap.pop(name, None)
        _save_overrides(raw)
        changed = True
    # Update settings file too
    if _SETTINGS_FILE.exists():
        payload = _load_settings_payload()
        st_tmap = payload.get("file_overrides", {}).get("templates", {}).get(str(template_id), {})
        if name in st_tmap:
            st_tmap.pop(name, None)
            _write_settings_payload(payload)
            changed = True
    return changed


def list_file_overrides() -> List[Tuple[str, str, Dict[str, Any]]]:
    """Return list of (template_id, placeholder_name, data) for current overrides."""
    data = _load_overrides()
    out: List[Tuple[str, str, Dict[str, Any]]] = []
    for tid, entries in data.get("templates", {}).items():
        for name, info in entries.items():
            out.append((tid, name, info))
    return out

