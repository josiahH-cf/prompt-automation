from __future__ import annotations

"""Preview window helpers for the selector GUI."""

from typing import TYPE_CHECKING

from ..model import TemplateEntry

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    import tkinter as tk


def open_preview(parent: "tk.Tk", entry: TemplateEntry) -> None:
    """Display a read-only preview of a template."""
    import tkinter as tk
    from ..fonts import get_display_font
    from ...error_dialogs import show_error

    try:
        tmpl = entry.data
        preview = tk.Toplevel(parent)
        preview.title(f"Preview: {tmpl.get('title', entry.path.name)}")
        preview.geometry("700x500")
        preview.resizable(True, True)
        text = tk.Text(preview, wrap="word", font=get_display_font(master=parent))
        text.pack(fill="both", expand=True)
        lines = tmpl.get('template', [])
        text.insert("1.0", "\n".join(lines))
        text.config(state="disabled")
        preview.transient(parent)
        preview.grab_set()
    except Exception as e:  # pragma: no cover - GUI error path
        show_error("Preview Error", str(e))
