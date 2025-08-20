"""Pure formatting helpers for GUI collector components."""
from __future__ import annotations

from typing import Callable

from ....renderer import read_file_safe

SIZE_LIMIT = 200 * 1024


def load_file_with_limit(
    path: str,
    reader: Callable[[str], str] = read_file_safe,
    *,
    size_limit: int = SIZE_LIMIT,
) -> str:
    """Load file content using *reader*, truncating large files.

    Parameters
    ----------
    path:
        File path to read.
    reader:
        Callable used to read the file. Defaults to :func:`read_file_safe`.
    size_limit:
        Maximum number of bytes to display before truncation notice is added.
    """
    content = reader(path)
    if len(content.encode("utf-8")) > size_limit:
        banner = "*** File truncated (display only) ***\n\n"
        content = banner + content[: size_limit // 2]
    return content


def format_list_input(raw: str) -> list[str]:
    """Convert a multiline string into a list of stripped items."""
    return [line.strip() for line in raw.splitlines() if line.strip()]


def truncate_default_hint(default: str, limit: int = 160) -> tuple[str, bool]:
    """Truncate default hint for display.

    Returns the possibly truncated value and whether truncation occurred.
    """
    display = default.replace("\n", " ")
    truncated = False
    if len(display) > limit:
        display = display[:limit].rstrip() + "…"
        truncated = True
    return display, truncated
