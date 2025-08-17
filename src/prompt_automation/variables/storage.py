"""Persistence helpers for variable overrides and settings."""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any, Dict

from ..config import HOME_DIR, PROMPTS_DIR
from ..errorlog import get_logger


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
    settings_templates = settings_payload.get("file_overrides", {}).get("templates", {})
    if not settings_templates:
        return overrides
    merged = json.loads(json.dumps(overrides))  # deep copy via json
    tmap = merged.setdefault("templates", {})
    for tid, entries in settings_templates.items():
        target = tmap.setdefault(tid, {})
        for name, info in entries.items():
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
        txt = str(p)
        if os.name != 'nt':
            if ':' in txt and '\\' in txt:
                txt = txt.replace('\\', '/')
        return txt
    except Exception:
        return path

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
            for tid in [k for k, v in tv.items() if isinstance(v, dict) and not v]:
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
                try:
                    _save_overrides(base)
                except Exception:
                    pass
    except Exception:
        pass
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
    try:
        _sync_settings_from_overrides(data)
    except Exception as e:  # pragma: no cover - defensive
        _log.error("failed to sync overrides to settings: %s", e)

def _get_template_entry(data: dict, template_id: int, name: str) -> dict | None:
    return data.get("templates", {}).get(str(template_id), {}).get(name)

def _set_template_entry(data: dict, template_id: int, name: str, payload: dict) -> None:
    data.setdefault("templates", {}).setdefault(str(template_id), {})[name] = payload

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

def get_template_global_overrides(template_id: int) -> dict:
    data = _load_overrides()
    return data.get("template_globals", {}).get(str(template_id), {})

def ensure_template_global_snapshot(template_id: int, gph: dict) -> None:
    """If no snapshot exists for this template, persist current global placeholders."""
    if not isinstance(template_id, int):
        return
    data = _load_overrides()
    tgl = data.setdefault("template_globals", {})
    key = str(template_id)
    if key not in tgl:
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
