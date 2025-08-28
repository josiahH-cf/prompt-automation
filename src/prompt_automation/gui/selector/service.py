"""Legacy selector service facade delegating to shared services.

This module historically exposed a grab bag of helper functions used by the
selector GUI.  During the service refactor the underlying logic moved into
dedicated modules under :mod:`prompt_automation.services`.  To preserve the
public API we keep thin wrappers here that forward calls to the new services
while also re-exporting those service modules for advanced callers.
"""
from __future__ import annotations

from .model import (
    create_browser_state,
    ListingItem,
    TemplateEntry,
    BrowserState,
)
from ...shortcuts import (
    load_shortcuts,
    save_shortcuts,
    renumber_templates,
    SHORTCUT_FILE,
)
from ...config import PROMPTS_DIR
from ...services import (
    template_search as template_search_service,
    multi_select as multi_select_service,
    overrides as overrides_service,
    exclusions as exclusions_service,
)


# ---------------------------------------------------------------------------
# Template search helpers


def resolve_shortcut(key: str):
    return template_search_service.resolve_shortcut(key)


def load_template_by_relative(rel: str):
    return template_search_service.load_template_by_relative(rel)


def search(query: str, recursive: bool = True):
    return template_search_service.search(query, recursive=recursive)


# ---------------------------------------------------------------------------
# Overrides helpers


def reset_file_overrides():
    return overrides_service.reset_file_overrides()

def reset_file_overrides_with_backup(confirm_cb=None):
    return overrides_service.reset_file_overrides_with_backup(confirm_cb)

def undo_last_reset_file_overrides():
    return overrides_service.undo_last_reset_file_overrides()


def list_file_overrides():
    return overrides_service.list_file_overrides()


def reset_single_file_override(template_id: int, name: str) -> bool:
    return overrides_service.reset_placeholder_override(template_id, name)


def list_template_value_overrides():
    return overrides_service.list_template_value_overrides()


def reset_template_value_override(template_id: int, name: str) -> bool:
    return overrides_service.reset_template_value_override_value(template_id, name)


def set_template_value_override(template_id: int, name: str, value):
    overrides_service.update_template_value_override(template_id, name, value)


def load_overrides():
    return overrides_service.load_overrides()


def save_overrides(overrides):
    overrides_service.save_overrides(overrides)


# ---------------------------------------------------------------------------
# Exclusions helpers


def load_exclusions(template_id: int):
    return exclusions_service.load_exclusions(template_id)


def set_exclusions(template_id: int, exclusions):
    return exclusions_service.set_exclusions(template_id, exclusions)


def add_exclusion(template_id: int, name: str):
    return exclusions_service.add_exclusion(template_id, name)


def remove_exclusion(template_id: int, name: str):
    return exclusions_service.remove_exclusion(template_id, name)


def reset_exclusions(template_id: int):
    return exclusions_service.reset_exclusions(template_id)


__all__ = [
    "create_browser_state",
    "ListingItem",
    "TemplateEntry",
    "BrowserState",
    "reset_file_overrides",
    "reset_file_overrides_with_backup",
    "undo_last_reset_file_overrides",
    "list_file_overrides",
    "reset_single_file_override",
    "list_template_value_overrides",
    "reset_template_value_override",
    "set_template_value_override",
    "load_shortcuts",
    "save_shortcuts",
    "renumber_templates",
    "SHORTCUT_FILE",
    "template_search_service",
    "multi_select_service",
    "overrides_service",
    "exclusions_service",
    "resolve_shortcut",
    "load_template_by_relative",
    "search",
    "PROMPTS_DIR",
    "load_overrides",
    "save_overrides",
    "load_exclusions",
    "set_exclusions",
    "add_exclusion",
    "remove_exclusion",
    "reset_exclusions",
]
