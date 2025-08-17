"""Session state and persistence helpers for GUI variable collection."""
from __future__ import annotations

from ...variables import (
    load_template_value_memory,
    persist_template_values,
    get_remembered_context,
    set_remembered_context,
    get_global_reference_file,
    reset_global_reference_file,
)


# sentinel object to signal user cancellation during input collection
CANCELLED = object()

# Internal mapping used to convey default values into collect_single_variable
CURRENT_DEFAULTS: dict[str, str] = {}

__all__ = [
    "CANCELLED",
    "CURRENT_DEFAULTS",
    "load_template_value_memory",
    "persist_template_values",
    "get_remembered_context",
    "set_remembered_context",
    "get_global_reference_file",
    "reset_global_reference_file",
]
