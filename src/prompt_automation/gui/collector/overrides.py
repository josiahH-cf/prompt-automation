"""File override helpers for GUI collection.

Historically these functions lived in this module; they now proxy to the
shared :mod:`prompt_automation.services.overrides` helpers so that
non-GUI components can reuse the same behaviour.
"""
from __future__ import annotations

from ...services.overrides import (
    load_overrides,
    get_template_entry,
    save_overrides,
    set_template_entry,
    print_one_time_skip_reminder,
)


__all__ = [
    "load_overrides",
    "get_template_entry",
    "save_overrides",
    "set_template_entry",
    "print_one_time_skip_reminder",
]
