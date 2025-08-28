"""Variable collection and persistence helpers."""
from ..config import PROMPTS_DIR
from .core import get_variables
from .files import (
    get_global_reference_file,
    reset_global_reference_file,
    _print_one_time_skip_reminder,
)
from .values import (
    load_template_value_memory,
    persist_template_values,
    list_template_value_overrides,
    reset_template_value_override,
    reset_all_template_value_overrides,
    set_template_value_override,
    reset_file_overrides,
    reset_single_file_override,
    list_file_overrides,
    reset_file_overrides_with_backup,
    undo_last_reset_file_overrides,
)
from .storage import (
    get_remembered_context,
    set_remembered_context,
    get_template_global_overrides,
    ensure_template_global_snapshot,
    apply_template_global_overrides,
    _load_overrides,
    _save_overrides,
    _get_template_entry,
    _set_template_entry,
)

__all__ = [
    "PROMPTS_DIR",
    "get_variables",
    "get_global_reference_file",
    "reset_global_reference_file",
    "load_template_value_memory",
    "persist_template_values",
    "list_template_value_overrides",
    "reset_template_value_override",
    "reset_all_template_value_overrides",
    "set_template_value_override",
    "reset_file_overrides",
    "reset_single_file_override",
    "list_file_overrides",
    "reset_file_overrides_with_backup",
    "undo_last_reset_file_overrides",
    "get_remembered_context",
    "set_remembered_context",
    "get_template_global_overrides",
    "ensure_template_global_snapshot",
    "apply_template_global_overrides",
    "_load_overrides",
    "_save_overrides",
    "_get_template_entry",
    "_set_template_entry",
    "_print_one_time_skip_reminder",
]
