from __future__ import annotations

"""Helpers for managing placeholder and template value overrides.

This module exposes convenience wrappers around the low level persistence
functions located in :mod:`prompt_automation.variables`.  It allows both
GUI and non-GUI components to inspect and modify override data without
needing direct access to the underlying storage implementation.
"""

from typing import Any, Dict, Optional

from ..variables import (
    _load_overrides,
    _save_overrides,
    _get_template_entry,
    _set_template_entry,
    _print_one_time_skip_reminder,
    reset_single_file_override,
    set_template_value_override,
    reset_template_value_override,
    reset_all_template_value_overrides,
    list_file_overrides,
    list_template_value_overrides,
    reset_file_overrides,
    # New safe reset helpers
    reset_file_overrides_with_backup,
    undo_last_reset_file_overrides,
)


# ---------------------------------------------------------------------------
# Basic load/save helpers


def load_overrides() -> Dict[str, Any]:
    """Return the full overrides payload.

    The underlying loader is tolerant to missing or corrupt files and will
    always return a dictionary with the expected top level keys.
    """

    return _load_overrides()


def save_overrides(overrides: Dict[str, Any]) -> None:
    """Persist the supplied overrides mapping."""

    _save_overrides(overrides)


# ---------------------------------------------------------------------------
# Template placeholder override helpers


def get_template_entry(overrides: Dict[str, Any], template_id: int, name: str) -> Optional[dict]:
    """Return a single placeholder override entry if present."""

    return _get_template_entry(overrides, template_id, name)


def set_template_entry(overrides: Dict[str, Any], template_id: int, name: str, entry: Dict[str, Any]) -> None:
    """Update a placeholder override entry within ``overrides``."""

    _set_template_entry(overrides, template_id, name, entry)


def update_placeholder_override(
    template_id: int,
    name: str,
    *,
    path: Optional[str] = None,
    skip: Optional[bool] = None,
) -> None:
    """Apply updates to a single placeholder override and persist them.

    Parameters
    ----------
    template_id:
        Identifier of the template the placeholder belongs to.
    name:
        Placeholder name.
    path:
        Optional file path to store.  ``None`` leaves the existing value
        unchanged, while an empty string removes the path.
    skip:
        When ``True`` sets the skip flag.  When ``False`` removes the flag.
        ``None`` leaves the existing value unchanged.
    """

    overrides = load_overrides()
    entry = get_template_entry(overrides, template_id, name) or {}

    if path is not None:
        if path:
            entry["path"] = path
        else:
            entry.pop("path", None)
    if skip is not None:
        if skip:
            entry["skip"] = True
        else:
            entry.pop("skip", None)
    if entry:
        set_template_entry(overrides, template_id, name, entry)
    else:
        tmpl = overrides.get("templates", {}).get(str(template_id))
        if tmpl and name in tmpl:
            tmpl.pop(name, None)
    save_overrides(overrides)


def reset_placeholder_override(template_id: int, name: str) -> bool:
    """Remove a single persisted placeholder override."""

    return reset_single_file_override(template_id, name)


def print_one_time_skip_reminder(overrides: Dict[str, Any], template_id: int, name: str) -> None:
    """Helper used by UI components to display skip reminders once per session."""

    _print_one_time_skip_reminder(overrides, template_id, name)


# ---------------------------------------------------------------------------
# Template value override helpers


def update_template_value_override(template_id: int, name: str, value: Any) -> None:
    """Persist or clear a simple placeholder value override."""

    set_template_value_override(template_id, name, value)


def reset_template_value_override_value(template_id: int, name: str) -> bool:
    """Remove a single persisted simple value override."""

    return reset_template_value_override(template_id, name)


def reset_all_template_value_overrides_for_template(template_id: int) -> bool:
    """Remove all persisted simple value overrides for ``template_id``."""

    return reset_all_template_value_overrides(template_id)


__all__ = [
    "load_overrides",
    "save_overrides",
    "get_template_entry",
    "set_template_entry",
    "update_placeholder_override",
    "reset_placeholder_override",
    "print_one_time_skip_reminder",
    "update_template_value_override",
    "reset_template_value_override_value",
    "reset_all_template_value_overrides_for_template",
    "list_file_overrides",
    "list_template_value_overrides",
    "reset_file_overrides",
    "reset_file_overrides_with_backup",
    "undo_last_reset_file_overrides",
]
