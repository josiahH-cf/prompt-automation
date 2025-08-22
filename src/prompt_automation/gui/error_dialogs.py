"""Central helpers for displaying GUI error dialogs.

Wraps ``tkinter.messagebox.showerror`` to avoid repeated imports across
modules. Failures are ignored so code remains safe in headless test
runs or minimal environments without Tk support.
"""
from __future__ import annotations

# We intentionally DO NOT import tkinter here for clipboard operations anymore.
# Creating a transient Tk root, placing text on the X11 clipboard, and then
# immediately destroying the root can result in the selection being cleared on
# some Linux window managers. Instead we delegate to the core
# ``paste.copy_to_clipboard`` helper (pyperclip + system fallbacks) and only
# surface an error dialog if that raises.
try:  # local import guard to avoid circulars (two dots -> package root)
    from ..paste import copy_to_clipboard as _base_copy  # type: ignore
except Exception:  # pragma: no cover - extremely rare
    def _base_copy(_text: str) -> None:  # type: ignore
        raise RuntimeError("clipboard helper unavailable")


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


def safe_copy_to_clipboard(text: str) -> bool:
    """Attempt to copy text to clipboard; show error dialog on failure.

    Uses the robust project-level copy implementation (pyperclip + platform
    fallbacks). Avoids transient Tk roots which can drop clipboard ownership
    immediately after destruction on X11.
    """
    try:
        ok = _base_copy(text)
        if ok is False:  # explicit failure signal from helper
            raise RuntimeError("clipboard helper returned failure")
        return True
    except Exception as e:  # pragma: no cover - depends on environment
        show_error("Clipboard Error", f"Failed to copy to clipboard:\n{e}")
        return False


__all__ = ["show_error", "safe_copy_to_clipboard"]
