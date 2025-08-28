"""Theming utilities: registry, resolver, and appliers.

Provides a minimal, accessible dark mode and a future-proof registry for
additional themes. GUI theming is applied via the Tk option database to avoid
heavy dependencies and reduce flicker.
"""
from .model import get_theme, register_theme, list_themes, contrast_ratio
from .resolve import (
    ThemeResolver,
    get_registry,
    get_user_theme_preference,
    set_user_theme_preference,
    get_enable_theming,
    set_enable_theming,
)
from .apply import apply_to_root, format_heading

__all__ = [
    'get_theme',
    'register_theme',
    'list_themes',
    'contrast_ratio',
    'ThemeResolver',
    'get_registry',
    'get_user_theme_preference',
    'set_user_theme_preference',
    'get_enable_theming',
    'set_enable_theming',
    'apply_to_root',
    'format_heading',
]

