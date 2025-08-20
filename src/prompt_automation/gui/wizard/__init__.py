"""Wizard package providing GUI and step utilities for template creation."""
from .wizard import open_new_template_wizard
from .steps import (
    SUGGESTED_PLACEHOLDERS,
    next_template_id,
    ensure_style,
    suggest_placeholders,
    generate_template_body,
)

__all__ = [
    "open_new_template_wizard",
    "SUGGESTED_PLACEHOLDERS",
    "next_template_id",
    "ensure_style",
    "suggest_placeholders",
    "generate_template_body",
]
