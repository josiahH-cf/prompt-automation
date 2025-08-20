from __future__ import annotations

"""Utility helpers for discovering and loading templates.

This module centralises common template listing and shortcut resolution
logic so that both GUI and non-GUI components can share behaviour.
"""

from pathlib import Path
from typing import List, Optional

from ..config import PROMPTS_DIR
from ..renderer import load_template
from ..shortcuts import load_shortcuts


def list_templates(search: str = "", recursive: bool = True) -> List[Path]:
    """Return template paths under ``PROMPTS_DIR``.

    Parameters
    ----------
    search:
        Optional case-insensitive substring filter applied to the template's
        relative path.
    recursive:
        When ``True`` (default) traverse sub-directories, otherwise only list
        templates in the root directory.
    """
    iterator = PROMPTS_DIR.rglob("*.json") if recursive else PROMPTS_DIR.glob("*.json")
    search_l = search.lower()
    results: List[Path] = []
    for path in iterator:
        if path.name.lower() == "settings.json":
            continue
        rel = path.relative_to(PROMPTS_DIR)
        if search_l and search_l not in str(rel).lower():
            continue
        results.append(path)
    return sorted(results)


def load_template_by_relative(rel: str) -> Optional[dict]:
    """Load a template given a path relative to ``PROMPTS_DIR``."""
    path = PROMPTS_DIR / rel
    if path.exists():
        try:
            return load_template(path)
        except Exception:
            return None
    return None


def resolve_shortcut(key: str) -> Optional[dict]:
    """Return template mapped to a shortcut key, if any."""
    mapping = load_shortcuts()
    rel = mapping.get(key)
    if not rel:
        return None
    return load_template_by_relative(rel)


def search(query: str, recursive: bool = True) -> List[dict]:
    """Search templates returning loaded template data.

    This is a convenience wrapper used by GUI components where the caller
    expects full template dictionaries.
    """
    results: List[dict] = []
    for path in list_templates(search=query, recursive=recursive):
        try:
            results.append(load_template(path))
        except Exception:
            continue
    return results


__all__ = [
    "list_templates",
    "load_template_by_relative",
    "resolve_shortcut",
    "search",
]
