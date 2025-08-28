from __future__ import annotations

import os
import sys
from typing import Dict


def apply_to_root(root, theme: Dict[str, str], *, initial: bool = False, enable: bool = True) -> int:
    """Apply theme tokens to a Tk root via option database.

    Returns the number of applied options. Light theme is treated as a no-op to
    avoid perturbing existing visuals.
    """
    if not enable:
        return 0
    name = theme.get('name', 'light')
    if name == 'light':
        return 0
    if not hasattr(root, 'option_add'):
        return 0
    # Map semantic tokens to Tk option database keys.
    mapping = [
        ('*background', theme['background']),
        ('*foreground', theme['textPrimary']),
        ('*activeForeground', theme['textPrimary']),
        ('*activeBackground', theme['surface']),
        ('*selectBackground', theme['selectionBackground']),
        ('*selectForeground', theme['selectionForeground']),
        ('*highlightColor', theme['focusOutline']),
        # Insertion cursor (caret) color; include multiple patterns for cross-platform Tk variants
        ('*insertbackground', get_cursor_color(theme)),  # common lowercase option name
        ('*insertBackground', get_cursor_color(theme)),  # resource name form used by option database
        ('*Text.insertBackground', get_cursor_color(theme)),  # widget-specific override (Text)
        ('*Entry.insertBackground', get_cursor_color(theme)),  # widget-specific override (Entry)
        # Insertion cursor width for better visibility on dark backgrounds
        ('*insertWidth', '2'),
        ('*Text.insertWidth', '2'),
        ('*Entry.insertWidth', '2'),
        ('*troughColor', theme['surfaceAlt']),
    ]
    count = 0
    for key, val in mapping:
        try:
            root.option_add(key, val)
            count += 1
        except Exception:
            # best effort; continue
            pass
    return count


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join([c * 2 for c in h])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def format_heading(text: str, theme: Dict[str, str], *, force_tty: bool | None = None, no_color_env: bool | None = None) -> str:
    """Return heading string with theme-aware ANSI color when appropriate.

    Applies color only when output is a TTY and NO_COLOR is not set. The
    optional parameters allow tests to override detection.
    """
    name = theme.get('name', 'light')
    if force_tty is None:
        try:
            force_tty = sys.stdout.isatty()
        except Exception:
            force_tty = False
    if no_color_env is None:
        no_color_env = bool(os.environ.get('NO_COLOR'))
    if not force_tty or no_color_env or name == 'light':
        return text
    r, g, b = _hex_to_rgb(theme.get('accentPrimary', '#5AA9E6'))
    return f"\033[1;38;2;{r};{g};{b}m{text}\033[0m"


def get_cursor_color(theme: Dict[str, str]) -> str:
    """Return high-contrast insertion cursor color for the given theme.

    Policy: for dark themes use white ``#FFFFFF`` for maximum contrast.
    For all others fall back to the primary text color.
    """
    try:
        name = (theme.get('name') or '').lower()
        if name == 'dark':
            return '#FFFFFF'
        return theme.get('textPrimary', '#000000')
    except Exception:
        return '#FFFFFF'
