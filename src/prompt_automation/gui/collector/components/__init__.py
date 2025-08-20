"""Subcomponents for GUI prompt collection."""

from .formatting import (
    load_file_with_limit,
    format_list_input,
    truncate_default_hint,
)
from .orchestrator import (
    collect_file_variable_gui,
    collect_reference_file_variable_gui,
    collect_global_reference_file_gui,
    collect_context_variable_gui,
    show_reference_file_content,
    collect_variables_gui,
    collect_single_variable,
)
from .ui import create_window

__all__ = [
    "load_file_with_limit",
    "format_list_input",
    "truncate_default_hint",
    "collect_file_variable_gui",
    "collect_reference_file_variable_gui",
    "collect_global_reference_file_gui",
    "collect_context_variable_gui",
    "show_reference_file_content",
    "collect_variables_gui",
    "collect_single_variable",
    "create_window",
]
