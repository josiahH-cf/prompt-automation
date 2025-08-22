"""Central helpers for displaying GUI error dialogs.

Wraps ``tkinter.messagebox.showerror`` to avoid repeated imports across
modules. Failures are ignored so code remains safe in headless test
runs or minimal environments without Tk support.
"""
from __future__ import annotations


def show_error(title: str, message: str) -> None:
    """Best-effort wrapper around ``messagebox.showerror``."""
    try:
        from tkinter import messagebox
    except Exception:
        return
    try:
        messagebox.showerror(title, message)
    except Exception:
        # Error dialogs should never raise further exceptions; simply
        # swallow any issues so callers don't need additional guards.
        pass


__all__ = ["show_error"]
