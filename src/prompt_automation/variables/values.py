"""Persistence of simple placeholder values and file overrides."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..errorlog import get_logger

from .storage import (
    _PERSIST_FILE,
    _SETTINGS_FILE,
    _load_overrides,
    _load_settings_payload,
    _save_overrides,
    _write_settings_payload,
)


_log = get_logger(__name__)

# Single-level undo snapshot for dangerous resets
def _persist_undo_file() -> Path:
    """Return path to undo snapshot alongside current overrides file.

    Computed at call time so tests that monkeypatch ``_PERSIST_FILE`` see
    the correct sibling path.
    """
    return _PERSIST_FILE.with_name('placeholder-overrides.undo.json')


def load_template_value_memory(template_id: int) -> Dict[str, Any]:
    """Return previously persisted simple values for template or empty dict."""
    try:
        data = _load_overrides()
        return data.get("template_values", {}).get(str(template_id), {}) or {}
    except Exception:
        return {}


def persist_template_values(template_id: int, placeholders: List[Dict[str, Any]], values: Dict[str, Any]) -> None:
    """Persist only placeholders explicitly marked with "persist": true.

    Rationale: Defaults already provide stable baseline; user-entered ad‑hoc
    text should not auto-fill future runs unless the template author opts in.
    File paths are persisted separately in the overrides "templates" section,
    so file placeholders (including reference_file) are excluded here.
    """
    overrides_data = _load_overrides()
    tvals = overrides_data.setdefault("template_values", {}).setdefault(str(template_id), {})
    for ph in placeholders:
        nm = ph.get("name")
        if not nm or ph.get("type") == "file" or nm == "reference_file_content":
            continue
        if not ph.get("persist"):
            # Drop previously stored value if persist flag removed
            if nm in tvals:
                tvals.pop(nm, None)
            continue
        v = values.get(nm)
        if isinstance(v, (str, int, float)):
            if str(v).strip():
                tvals[nm] = v
            else:
                tvals.pop(nm, None)
        elif isinstance(v, list):
            cleaned = [str(x) for x in v if str(x).strip()]
            if cleaned:
                if len(cleaned) > 200:
                    cleaned = cleaned[:200]
                tvals[nm] = cleaned
            else:
                tvals.pop(nm, None)
    if not tvals:
        overrides_data.get("template_values", {}).pop(str(template_id), None)
    _save_overrides(overrides_data)


def reset_file_overrides() -> bool:
    """Delete persistent file/skip overrides. Returns True if removed."""
    try:
        if _PERSIST_FILE.exists():
            _PERSIST_FILE.unlink()
            if _SETTINGS_FILE.exists():
                payload = _load_settings_payload()
                if payload.get("file_overrides"):
                    payload["file_overrides"]["templates"] = {}
                    _write_settings_payload(payload)
            return True
    except Exception as e:
        _log.error("failed to reset overrides: %s", e)
    return False


def reset_file_overrides_with_backup(confirm_cb=None) -> bool:
    """Reset overrides with confirmation and one-level undo snapshot.

    - If ``_PERSIST_FILE`` exists, copy its contents into ``_PERSIST_UNDO_FILE``.
    - Then perform the normal reset (deleting the overrides file and syncing
      settings).
    - Returns True if a reset occurred; False if declined or nothing to reset.
    """
    try:
        # Nothing to do
        if not _PERSIST_FILE.exists():
            return False
        # Confirmation gate (GUI provides a callback; tests can stub it)
        if callable(confirm_cb):
            try:
                if not bool(confirm_cb()):
                    return False
            except Exception:
                return False
        # Snapshot for undo
        try:
            raw = _PERSIST_FILE.read_text(encoding='utf-8')
            _persist_undo_file().write_text(raw, encoding='utf-8')
        except Exception:
            # If snapshot fails we still proceed with reset to honour user intent,
            # but log the error for visibility.
            _log.warning("failed to create undo snapshot")
        # Perform reset
        return reset_file_overrides()
    except Exception as e:  # pragma: no cover - defensive
        _log.error("reset with backup failed: %s", e)
        return False


def undo_last_reset_file_overrides() -> bool:
    """Restore overrides from the last reset snapshot, if available.

    Returns True if restored, False otherwise.
    """
    try:
        undo_path = _persist_undo_file()
        if not undo_path.exists():
            return False
        try:
            data = json.loads(undo_path.read_text(encoding='utf-8'))
        except Exception:
            return False
        _save_overrides(data)
        try:
            undo_path.unlink()
        except Exception:
            pass
        return True
    except Exception as e:  # pragma: no cover - defensive
        _log.error("undo reset failed: %s", e)
        return False


def reset_single_file_override(template_id: int, name: str) -> bool:
    """Remove a single template/placeholder override (both local & settings).

    Returns True if something was removed.
    """
    changed = False
    data = _load_overrides()
    tmap = data.get("templates", {}).get(str(template_id)) or {}
    if name in tmap:
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


def list_template_value_overrides() -> List[Tuple[str, str, Any]]:
    """Return list of (template_id, name, value) for persisted simple values."""
    data = _load_overrides()
    out: List[Tuple[str, str, Any]] = []
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
    """Programmatically set/update a simple (non-file) placeholder value override."""
    try:
        raw = _load_overrides()
        tvals = raw.setdefault("template_values", {}).setdefault(str(template_id), {})
        if value is None:
            if name in tvals:
                tvals.pop(name, None)
        else:
            tvals[name] = value
        _save_overrides(raw)
    except Exception as e:  # pragma: no cover - defensive
        _log.error("failed setting template value override %s/%s: %s", template_id, name, e)
