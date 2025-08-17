"""Font selection helpers for GUI text widgets.

Select a font with improved Unicode / emoji coverage so rendered output
(reference file contents or plain template text) shows emoji, dashes and
other symbols instead of tofu boxes. We keep this light-weight and safe
for headless test environments.
"""
from __future__ import annotations

import sys
from typing import Sequence, Tuple


def _platform_font_candidates() -> Sequence[str]:
    plat = sys.platform
    if plat.startswith("win"):
        return [
            "Segoe UI Emoji",  # includes color emoji
            "Segoe UI",
            "Consolas",
            "Arial",
        ]
    if plat == "darwin":  # macOS
        return [
            "Apple Color Emoji",
            "SF Pro Text",
            "Menlo",
            "Helvetica",
            "Arial",
        ]
    # Linux / other
    return [
        "Noto Color Emoji",
        "Noto Sans",
        "DejaVu Sans",
        "DejaVu Sans Mono",
        "Liberation Sans",
        "Monospace",
    ]


def get_display_font(size: int = 10, master=None) -> Tuple[str, int]:
    """Return a (family, size) tuple for a Text widget.

    If *master* is provided (a Tk widget/root) we try to pick the first
    candidate actually installed. Errors are ignored so this still works
    in headless test runs.
    """
    candidates = _platform_font_candidates()
    if master is not None:
        try:
            fams = {f.lower() for f in master.tk.splitlist(master.tk.call("font", "families"))}
            for fam in candidates:
                if fam.lower() in fams:
                    return fam, size
        except Exception:
            pass
    return candidates[0], size


__all__ = ["get_display_font"]
