from __future__ import annotations

from pathlib import Path
from typing import Optional

from .model import (
    create_browser_state,
    ListingItem,
    TemplateEntry,
    BrowserState,
)
from ...variables import (
    reset_file_overrides,
    list_file_overrides,
    reset_single_file_override,
    list_template_value_overrides,
    reset_template_value_override,
    set_template_value_override,
)
from ...shortcuts import (
    load_shortcuts,
    save_shortcuts,
    renumber_templates,
    SHORTCUT_FILE,
)
from ...renderer import load_template
from ...config import PROMPTS_DIR


def load_template_by_relative(rel: str) -> Optional[dict]:
    """Load a template given its path relative to ``PROMPTS_DIR``."""
    path = PROMPTS_DIR / rel
    if path.exists():
        try:
            return load_template(path)
        except Exception:
            return None
    return None


def resolve_shortcut(key: str) -> Optional[dict]:
    """Return template mapped to shortcut key, if any."""
    mapping = load_shortcuts()
    rel = mapping.get(key)
    if not rel:
        return None
    return load_template_by_relative(rel)


__all__ = [
    "create_browser_state",
    "ListingItem",
    "TemplateEntry",
    "BrowserState",
    "reset_file_overrides",
    "list_file_overrides",
    "reset_single_file_override",
    "list_template_value_overrides",
    "reset_template_value_override",
    "set_template_value_override",
    "load_shortcuts",
    "save_shortcuts",
    "renumber_templates",
    "SHORTCUT_FILE",
    "resolve_shortcut",
    "load_template_by_relative",
    "PROMPTS_DIR",
]
