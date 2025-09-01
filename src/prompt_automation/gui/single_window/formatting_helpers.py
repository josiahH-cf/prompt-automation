"""Formatting helpers used by the single-window GUI.

This module intentionally contains pure helpers that are easy to unit test
without a running Tk instance. It powers two areas:

- Auto-prefixing for multiline list inputs (existing behaviour)
- Lightweight Markdown prettifying for reference-file previews

The Markdown support here is intentionally minimal but opinionated so that a
raw ``.md`` file reads cleanly inside our viewer without bringing an HTML
engine. We keep the core transformation pure (``format_markdown_plain``) and
leave any Tk-specific styling to the caller.
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


# --- Markdown prettifier ----------------------------------------------------

def _replace_checkboxes(s: str) -> str:
    # Common task list patterns -> unicode symbols
    s2 = s
    s2 = s2.replace("- [ ] ", "☐ ")
    s2 = s2.replace("- [ ]", "☐ ")
    s2 = s2.replace("- [x] ", "☑ ")
    s2 = s2.replace("- [X] ", "☑ ")
    s2 = s2.replace("- [x]", "☑ ")
    s2 = s2.replace("- [X]", "☑ ")
    return s2


def format_markdown_plain(md: str) -> str:
    """Return a tidied, human-friendly plain-text rendering of Markdown.

    Goals:
    - Strip leading ``#`` markers for headings
    - Convert list markers to bullets (``•``) and task lists to checkboxes
    - Preserve code blocks, removing the ``` fences and indenting by 4 spaces
    - Keep blank lines but avoid double fences/markers leaking through

    This does not aim to be a full Markdown parser; it just improves the
    readability of typical notes used as references.
    """
    if not isinstance(md, str) or not md:
        return ""
    lines = md.replace("\r", "").splitlines()
    out: list[str] = []
    in_code = False
    for raw in lines:
        s = raw.rstrip("\n")
        if s.strip().startswith("```"):
            in_code = not in_code
            # On transition, do not emit the fence line
            continue
        if in_code:
            out.append("    " + s)
            continue
        # Horizontal rule variations
        if s.strip() in {"---", "***", "___"}:
            out.append("—" * 24)
            continue
        # Headings (#, ##, ### ...)
        if s.startswith("#"):
            # Remove all leading #'s and single space if present
            text = s.lstrip('#')
            if text.startswith(' '):
                text = text[1:]
            out.append(text)
            continue
        # Task list / bullets
        if s.lstrip().startswith(('- [', '* [', '+ [')):
            # Normalize leading indent then convert checkbox
            indent = len(s) - len(s.lstrip())
            replaced = _replace_checkboxes(s.lstrip())
            out.append(" " * indent + replaced)
            continue
        if s.lstrip().startswith(('- ', '* ', '+ ')):
            indent = len(s) - len(s.lstrip())
            item = s.lstrip()[2:]
            out.append(" " * indent + "• " + item)
            continue
        # Ordered list e.g. "1. Item" or "1) Item"
        ls = s.lstrip()
        if ls[:2].isdigit() or (ls and ls[0].isdigit()):
            # keep as-is but preserve original indent
            out.append(s)
            continue
        # Strong/bold asterisks markers -> keep plain text
        # (we intentionally keep the words and drop markup for plain mode)
        s = s.replace("**", "")
        out.append(_replace_checkboxes(s))
    return "\n".join(out)


__all__.extend(["format_markdown_plain"])

