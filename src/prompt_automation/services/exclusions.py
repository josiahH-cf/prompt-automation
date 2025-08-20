from __future__ import annotations

"""Helpers for managing template global exclusion lists.

This module centralizes parsing of the ``exclude_globals`` metadata field
and provides convenience helpers for updating exclusion lists on disk.
Both GUI and non-GUI components can rely on these helpers instead of
manipulating template JSON files directly.
"""

from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple
import json

from ..config import PROMPTS_DIR


# ---------------------------------------------------------------------------
# Parsing helpers


def parse_exclusions(raw: object) -> Set[str]:
    """Normalize ``raw`` into a set of exclusion strings."""

    try:
        if isinstance(raw, (list, tuple, set)):
            return {str(x).strip() for x in raw if str(x).strip()}
        if isinstance(raw, str):
            items = raw.split(",") if "," in raw else [raw]
            return {s.strip() for s in items if s.strip()}
    except Exception:
        pass
    return set()


# ---------------------------------------------------------------------------
# Persistence helpers


def _load_template(template_id: int) -> Optional[Tuple[Path, dict]]:
    """Return ``(path, data)`` for template ``template_id`` if found."""

    for p in PROMPTS_DIR.rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if data.get("id") == template_id:
            return p, data
    return None


def load_exclusions(template_id: int) -> Optional[List[str]]:
    """Return the exclusion list for ``template_id``.

    Returns ``None`` when the template cannot be located.
    """

    record = _load_template(template_id)
    if not record:
        return None
    _, data = record
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return sorted(parse_exclusions(meta.get("exclude_globals")))


def _write_exclusions(path: Path, data: dict, exclusions: Iterable[str]) -> None:
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    if not isinstance(meta, dict):
        meta = {}
        data["metadata"] = meta
    cleaned = [s for s in {str(x).strip() for x in exclusions if str(x).strip()}]
    if cleaned:
        meta["exclude_globals"] = cleaned
    else:
        meta.pop("exclude_globals", None)
    path.write_text(json.dumps(data, indent=2))


def set_exclusions(template_id: int, exclusions: Iterable[str]) -> bool:
    """Replace the exclusion list for ``template_id``.

    Returns ``True`` on success, ``False`` if the template is missing or the
    file could not be written.
    """

    record = _load_template(template_id)
    if not record:
        return False
    path, data = record
    try:
        _write_exclusions(path, data, exclusions)
        return True
    except Exception:
        return False


def add_exclusion(template_id: int, name: str) -> bool:
    """Append ``name`` to the exclusion list for ``template_id``."""

    existing = load_exclusions(template_id)
    if existing is None:
        return False
    existing_set = set(existing)
    existing_set.add(name.strip())
    return set_exclusions(template_id, existing_set)


def remove_exclusion(template_id: int, name: str) -> bool:
    """Remove ``name`` from the exclusion list for ``template_id``."""

    existing = load_exclusions(template_id)
    if existing is None:
        return False
    existing_set = {x for x in existing if x != name.strip()}
    return set_exclusions(template_id, existing_set)


def reset_exclusions(template_id: int) -> bool:
    """Clear all exclusions for ``template_id``."""

    return set_exclusions(template_id, [])


__all__ = [
    "parse_exclusions",
    "load_exclusions",
    "set_exclusions",
    "add_exclusion",
    "remove_exclusion",
    "reset_exclusions",
]
