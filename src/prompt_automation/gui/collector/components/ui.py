"""UI helpers for the GUI collector components."""
from __future__ import annotations


def create_window(title: str):
    """Create a visible window.

    Uses ``Toplevel`` if a single-window root is present to avoid spawning
    additional OS windows. Importing of Tk-related modules happens lazily so
    importing this module has no side effects when Tk isn't available.
    """
    import tkinter as tk  # type: ignore

    single_root = None
    try:  # Detect single-window root if running in embedded mode
        from ..selector import view as _sel_view  # type: ignore
        single_root = getattr(_sel_view, "_EMBEDDED_SINGLE_WINDOW_ROOT", None)
    except Exception:  # pragma: no cover - best effort
        single_root = None

    if single_root:
        win = tk.Toplevel(single_root)
    else:
        win = tk.Tk()
    win.title(title)
    return win
