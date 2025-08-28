"""Helpers for multiline list auto-formatting in single-window GUI.

This module contains pure functions that are unit-testable without Tk.
Runtime event bindings in the widgets call into these helpers.
"""
from __future__ import annotations

from typing import Literal

FormatType = Literal["bullet", "checklist"]


def next_line_prefix(prev_line: str, fmt: FormatType) -> str:
    """Return the prefix to insert on the next line based on ``prev_line``.

    Inputs:
    - prev_line: The full text of the line where Enter was pressed.
    - fmt: Either "bullet" or "checklist".

    Output:
    - The string to insert after the newline (e.g., "- " or "- [ ] "), or
      an empty string if no auto-prefix should be inserted.

    Rules:
    - bullet: If the previous line starts with "- " and has non-empty content
      after the dash, return "- ". If the previous line is just the prefix
      ("- ") or empty/whitespace, return "".
    - checklist: If the previous line starts with "- [ ] " and has non-empty
      content after the marker, return "- [ ] ". If only the prefix ("- [ ] ")
      is present or the line is blank, return "".
    """
    s = prev_line.rstrip("\n\r")
    stripped = s.strip()

    if fmt == "bullet":
        # No insertion if line is blank or only a dash prefix
        if stripped == "" or stripped == "-" or stripped == "-":
            return ""
        if stripped.startswith("- "):
            # When content exists beyond the dash, continue the list
            return "- "
        return ""

    # checklist
    # Allow minor variations like "- [ ]" without trailing space
    if stripped == "" or stripped in {"- [ ]", "- [ ]"}:
        return ""
    if stripped.startswith("- [ ") or stripped.startswith("- [ ]"):
        # Normalize to standard prefix with trailing space
        return "- [ ] "
    return ""


__all__ = ["next_line_prefix"]

