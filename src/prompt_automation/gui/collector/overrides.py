"""File override helpers for GUI collection."""
from __future__ import annotations

from ...variables import (
    _load_overrides,
    _get_template_entry,
    _save_overrides,
    _set_template_entry,
    _print_one_time_skip_reminder,
)


def load_overrides():
    return _load_overrides()


def get_template_entry(overrides, template_id, name):
    return _get_template_entry(overrides, template_id, name)


def save_overrides(overrides) -> None:
    _save_overrides(overrides)


def set_template_entry(overrides, template_id, name, entry) -> None:
    _set_template_entry(overrides, template_id, name, entry)


def print_one_time_skip_reminder(overrides, template_id, name) -> None:
    _print_one_time_skip_reminder(overrides, template_id, name)


__all__ = [
    "load_overrides",
    "get_template_entry",
    "save_overrides",
    "set_template_entry",
    "print_one_time_skip_reminder",
]
