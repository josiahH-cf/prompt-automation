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


def _normalize_reference_path(path: str) -> str:
    """Normalize reference file path for cross-platform consistency.

    - Expands user (~)
    - Converts Windows backslashes to forward slashes when running under WSL/Linux for consistent display
    - Resolves redundant separators / up-level references when possible
    """
    try:
        p = Path(path.strip().strip('"')).expanduser()
        # If path looks like a Windows path (contains a drive letter), keep original separators on Windows
        txt = str(p)
        if os.name != 'nt':
            # Under non-Windows, normalize backslashes to forward slashes for readability if drive pattern present
            if ':' in txt and '\\' in txt:
                txt = txt.replace('\\', '/')
        return txt
    except Exception:
        return path


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
    base = {"templates": {}, "reminders": {}, "template_globals": {}, "template_values": {}, "session": {}, "global_files": {}}
    if _PERSIST_FILE.exists():
        try:
            base = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            _log.error("failed to load overrides: %s", e)
    # Migration: consolidate legacy reference file keys to global_files.reference_file
    try:
        gfiles = base.setdefault("global_files", {})
        if "reference_file" not in gfiles:
            legacy = None
            # scan template_values and template_globals for any legacy key value
            for section in ("template_values", "template_globals"):
                seg = base.get(section, {})
                if not isinstance(seg, dict):
                    continue
                for _tid, data in seg.items():
                    if not isinstance(data, dict):
                        continue
                    for k, v in data.items():
                        if k in {"reference_file_default", "reference_file_content", "reference_file"} and isinstance(v, str) and v.strip():
                            legacy = v.strip()
                            break
                    if legacy:
                        break
                if legacy:
                    break
            if legacy and Path(legacy).expanduser().exists():
                gfiles["reference_file"] = legacy
    except Exception:
        pass
    # Remove any persisted reference_file_content snapshots (we now always re-read live)
    try:
        tv = base.get("template_values", {})
        if isinstance(tv, dict):
            for tid, mapping in list(tv.items()):
                if not isinstance(mapping, dict):
                    continue
                if "reference_file_content" in mapping:
                    mapping.pop("reference_file_content", None)
            # prune empties
            for tid in [k for k,v in tv.items() if isinstance(v, dict) and not v]:
                tv.pop(tid, None)
    except Exception:
        pass
    # Normalize global reference file path (Windows path usable under WSL etc.)
    try:
        refp = base.get("global_files", {}).get("reference_file")
        if isinstance(refp, str) and refp:
            norm = _normalize_reference_path(refp)
            if norm != refp:
                base.setdefault("global_files", {})["reference_file"] = norm
                # write back immediately so subsequent calls use normalized version
                try:
                    _save_overrides(base)
                except Exception:
                    pass
    except Exception:
        pass
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

# ----------------- Session context memory -----------------

def get_remembered_context() -> str | None:
    """Return remembered context text if set this session (persisted in overrides)."""
    data = _load_overrides()
    return data.get("session", {}).get("remembered_context")

def set_remembered_context(text: str | None) -> None:
    data = _load_overrides()
    sess = data.setdefault("session", {})
    if text:
        sess["remembered_context"] = text
    else:
        sess.pop("remembered_context", None)
    _save_overrides(data)

# ----------------- Global overrides (per-template snapshot of global_placeholders) ----

def get_template_global_overrides(template_id: int) -> dict:
    data = _load_overrides()
    return data.get("template_globals", {}).get(str(template_id), {})

def ensure_template_global_snapshot(template_id: int, gph: dict) -> None:
    """If no snapshot exists for this template, persist current global placeholders.

    This allows later renders to remain stable even if globals.json changes, while
    still letting the user manually edit the snapshot file or settings.
    """
    if not isinstance(template_id, int):
        return
    data = _load_overrides()
    tgl = data.setdefault("template_globals", {})
    key = str(template_id)
    if key not in tgl:
        # Store only scalar/string or list values (shallow copy)
        snap = {}
        for k, v in (gph or {}).items():
            if isinstance(v, (str, int, float)) or v is None:
                snap[k] = v
            elif isinstance(v, list):
                snap[k] = [x for x in v]
        tgl[key] = snap
        _save_overrides(data)

def apply_template_global_overrides(template_id: int, gph: dict) -> dict:
    """Return merged globals (snapshot overrides > template-defined > original globals)."""
    merged = dict(gph or {})
    overrides = get_template_global_overrides(template_id)
    if overrides:
        merged.update(overrides)
    return merged

__all__ = [
    # existing exports trimmed for brevity...
    "get_template_global_overrides",
    "ensure_template_global_snapshot",
    "apply_template_global_overrides",
    # new helpers
    "load_template_value_memory",
    "persist_template_values",
    "list_template_value_overrides",
    "reset_template_value_override",
    "reset_all_template_value_overrides",
    "set_template_value_override",
]


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
    # Opt-in override persistence: only persist/read if placeholder sets override=true
    persist_override = bool(ph.get("override") is True)
    if not persist_override:
        # Simple one-off selection without persistence
        label = ph.get("label", name)
        chosen = _gui_file_prompt(label) or input(f"File for {label} (leave blank to skip): ").strip()
        if chosen and Path(chosen).expanduser().exists():
            return str(Path(chosen).expanduser())
        return ""

    overrides = _load_overrides()
    entry = _get_template_entry(overrides, template_id, name) or {}

    if entry.get("skip"):
        _print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    path_str = entry.get("path")
    if path_str:
        p = Path(path_str).expanduser()
        if p.exists():
            return str(p)

    label = ph.get("label", name)
    chosen = _gui_file_prompt(label)
    if not chosen:
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
        # fallthrough
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

    # Load global notes to auto-label global-driven placeholders
    globals_notes: Dict[str, str] = {}
    try:
        gfile = PROMPTS_DIR / "globals.json"
        if gfile.exists():
            gdata = json.loads(gfile.read_text(encoding="utf-8"))
            globals_notes = gdata.get("notes", {}) or {}
    except Exception:
        pass

    # Load previously persisted simple values for this template
    persisted_values: Dict[str, Any] = {}
    try:
        if template_id is not None:
            persisted_values = (
                _load_overrides().get("template_values", {}).get(str(template_id), {}) or {}
            )
    except Exception:
        pass

    for ph in placeholders:
        name = ph["name"]
        ptype = ph.get("type")

        # Pre-fill with persisted value if user didn't supply initial value
        if name not in values and name in persisted_values:
            values[name] = persisted_values[name]

        # Augment label from globals notes if available and no explicit label
        if "label" not in ph and name in globals_notes:
            note_text = globals_notes.get(name, "")
            # If we have option spec followed by an en dash style description
            if " – " in note_text:
                opt_part, desc_part = note_text.split(" – ", 1)
                # Capture option hint for hallucinate; used to inform choices
                if name == "hallucinate" and "|" in opt_part:
                    ph.setdefault("_option_hint_raw", opt_part)
                ph["label"] = desc_part.strip() or note_text.strip()
            else:
                ph["label"] = note_text.strip() or name

        # Global reference file (single variable across templates)
        if name == "reference_file" and ptype == "file":
            ov = _load_overrides()
            gfiles = ov.setdefault("global_files", {})
            existing = gfiles.get("reference_file")
            if isinstance(existing, str) and existing and Path(existing).expanduser().exists():
                values[name] = existing
                continue
            label = ph.get("label", name)
            chosen = _gui_file_prompt(label) or input(f"File for {label} (leave blank to skip): ").strip()
            if chosen and Path(chosen).expanduser().exists():
                gfiles["reference_file"] = str(Path(chosen).expanduser())
                _save_overrides(ov)
                values[name] = gfiles["reference_file"]
            else:
                values[name] = ""
            continue

        if ptype == "file" and template_id is not None:
            # Other per-template file placeholders
            path_val = _resolve_file_placeholder(ph, template_id, globals_map)
            values[name] = path_val
            continue

        if name in values and values[name] not in ("", None):
            val: Any = values[name]
        else:
            label = ph.get("label", name)
            opts = ph.get("options")
            # Provide friendly dropdown for hallucinate if not already specified
            if name == "hallucinate" and not opts:
                # New ordering + semantics (user request):
                # critical -> Absolutely no hallucination (strict correctness)
                # normal  -> Balanced correctness & breadth
                # high    -> Some creative inference allowed
                # low     -> Maximum creative / ignore correctness (very permissive)
                # First option '(omit)' means do not include token at all (line removed)
                opts = [
                    "(omit)",
                    "Absolutely no hallucination (critical)",
                    "Balanced correctness & breadth (normal)",
                    "Some creative inference allowed (high)",
                    "Maximum creative exploration (low)",
                ]
                ph["_mapped_options"] = True
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

        if ptype == "file" and name != "reference_file" and isinstance(val, str) and val and template_id is None:
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
        # Map hallucinate friendly phrase to canonical token
        if name == "hallucinate":
            if isinstance(val, str):
                lower = val.lower()
                if "omit" in lower or not lower.strip():
                    val = None  # remove line entirely
                elif "critical" in lower:
                    val = "critical"
                elif "normal" in lower:
                    val = "normal"
                elif "high" in lower:
                    val = "high"
                elif "low" in lower:
                    val = "low"
            elif val is None:
                val = None
        values[name] = val
    # Persist simple values for future defaulting
    if template_id is not None:
        try:
            persist_template_values(template_id, placeholders, values)
        except Exception as e:  # pragma: no cover
            _log.error("failed to persist template values: %s", e)
    return values


# ----------------- Global reference file helpers -----------------
def get_global_reference_file() -> str | None:
    try:
        data = _load_overrides()
        path = data.get("global_files", {}).get("reference_file")
        if path:
            norm = _normalize_reference_path(path)
            p = Path(norm).expanduser()
            if p.exists():
                if norm != path:  # persist normalization
                    try:
                        raw = _load_overrides()
                        raw.setdefault("global_files", {})["reference_file"] = norm
                        _save_overrides(raw)
                    except Exception:
                        pass
                return str(p)
    except Exception:
        pass
    return None

def reset_global_reference_file() -> bool:
    try:
        data = _load_overrides()
        gfiles = data.get("global_files", {})
        if "reference_file" in gfiles:
            gfiles.pop("reference_file", None)
            _save_overrides(data)
            return True
    except Exception:
        pass
    return False

__all__ += ["get_global_reference_file", "reset_global_reference_file"]


# ----------------- Simple value persistence (non-file placeholders) -----------------
def load_template_value_memory(template_id: int) -> Dict[str, Any]:
    """Return previously persisted simple values for template or empty dict."""
    try:
        data = _load_overrides()
        return data.get("template_values", {}).get(str(template_id), {}) or {}
    except Exception:
        return {}


def persist_template_values(template_id: int, placeholders: List[Dict[str, Any]], values: Dict[str, Any]) -> None:
    """Store scalar/list placeholder values (excluding files) for the template."""
    overrides_data = _load_overrides()
    tvals = overrides_data.setdefault("template_values", {}).setdefault(str(template_id), {})
    for ph in placeholders:
        nm = ph.get("name")
        if not nm or ph.get("type") == "file" or nm == "reference_file_content":
            continue
        v = values.get(nm)
        if isinstance(v, (str, int, float)):
            if str(v).strip():
                tvals[nm] = v
        elif isinstance(v, list):
            cleaned = [str(x) for x in v if str(x).strip()]
            if cleaned:
                if len(cleaned) > 200:
                    cleaned = cleaned[:200]
                tvals[nm] = cleaned
    _save_overrides(overrides_data)


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


# ----------------- Template value overrides (simple non-file persistence) ---------

def list_template_value_overrides() -> List[Tuple[str, str, Any]]:
    """Return list of (template_id, name, value) for persisted simple values."""
    data = _load_overrides()
    out: List[Tuple[str, str, Any]] = []  # type: ignore[name-defined]
    for tid, entries in data.get("template_values", {}).items():
        if not isinstance(entries, dict):
            continue
        for name, val in entries.items():
            out.append((tid, name, val))
    return out


def reset_template_value_override(template_id: int, name: str) -> bool:
    """Remove a single persisted simple value for a template. Returns True if removed."""
    changed = False
    raw = _load_overrides()
    tvals = raw.get("template_values", {}).get(str(template_id)) or {}
    if name in tvals:
        # mutate underlying file structure directly
        if _PERSIST_FILE.exists():
            try:
                raw_file = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
            except Exception:
                raw_file = {}
        else:
            raw_file = {}
        rv_tvals = raw_file.setdefault("template_values", {}).get(str(template_id), {})
        if name in rv_tvals:
            rv_tvals.pop(name, None)
            # prune empty maps
            if not rv_tvals:
                raw_file.get("template_values", {}).pop(str(template_id), None)
            _save_overrides(raw_file)
            changed = True
    return changed


def reset_all_template_value_overrides(template_id: int) -> bool:
    """Remove all persisted simple values for a given template id."""
    if not _PERSIST_FILE.exists():
        return False
    try:
        raw_file = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    tv_map = raw_file.get("template_values", {})
    if str(template_id) in tv_map:
        tv_map.pop(str(template_id), None)
        _save_overrides(raw_file)
        return True
    return False


def set_template_value_override(template_id: int, name: str, value: Any) -> None:
    """Programmatically set/update a simple (non-file) placeholder value override.

    Creates parent structures as needed and persists immediately. Used by GUI
    override editor to allow direct editing of persisted values.
    """
    try:
        raw = _load_overrides()
        tvals = raw.setdefault("template_values", {}).setdefault(str(template_id), {})
        if value is None:
            # Remove if explicitly set to None
            if name in tvals:
                tvals.pop(name, None)
        else:
            tvals[name] = value
        _save_overrides(raw)
    except Exception as e:  # pragma: no cover - defensive
        _log.error("failed setting template value override %s/%s: %s", template_id, name, e)

