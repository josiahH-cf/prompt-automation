from __future__ import annotations

"""Utilities for combining multiple templates into a single synthetic one.

This service exposes helpers used by GUI and CLI components to merge several
prompt templates into a synthetic template whose body is simply the
concatenation of the individual templates' lines.  It also supports loading
templates by file path or shortcut key before merging.  Duplicate templates are
ignored while preserving the order of first occurrence.
"""

from pathlib import Path
from typing import Iterable, List, Optional

from ..renderer import load_template
from .template_search import resolve_shortcut


def merge_templates(templates: Iterable[dict]) -> Optional[dict]:
    """Return a synthetic template combining ``templates``.

    Parameters
    ----------
    templates:
        Iterable of template dictionaries.  Templates that appear multiple
        times are only included once, keeping the first occurrence order.

    Returns
    -------
    dict | None
        Synthetic template dictionary with concatenated ``template`` lines, or
        ``None`` if no templates were provided.
    """
    unique: List[dict] = []
    seen_ids = set()
    for tmpl in templates:
        try:
            tid = tmpl.get("id")
        except AttributeError:
            tid = id(tmpl)
        if tid is None:
            tid = id(tmpl)
        if tid in seen_ids:
            continue
        seen_ids.add(tid)
        unique.append(tmpl)
    if not unique:
        return None
    combined_lines: List[str] = []
    for tmpl in unique:
        combined_lines.extend(tmpl.get("template", []))
    return {
        "id": -1,
        "title": f"Multi ({len(unique)})",
        "style": "multi",
        "template": combined_lines,
    }


def merge_paths(paths: Iterable[str | Path]) -> Optional[dict]:
    """Load templates from ``paths`` and merge them."""
    loaded: List[dict] = []
    seen: set[str] = set()
    for p in paths:
        path = Path(p)
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        try:
            loaded.append(load_template(path))
        except Exception:
            continue
    return merge_templates(loaded)


def merge_shortcuts(keys: Iterable[str]) -> Optional[dict]:
    """Resolve shortcut ``keys`` and merge resulting templates."""
    loaded: List[dict] = []
    seen: set[int] = set()
    for key in keys:
        tmpl = resolve_shortcut(str(key))
        if not tmpl:
            continue
        tid = tmpl.get("id", id(tmpl))
        if tid in seen:
            continue
        seen.add(tid)
        loaded.append(tmpl)
    return merge_templates(loaded)


__all__ = ["merge_templates", "merge_paths", "merge_shortcuts"]
