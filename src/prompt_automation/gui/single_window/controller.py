"""Controller for the single-window GUI workflow."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .geometry import load_geometry, save_geometry
from .frames import select, collect, review


class SingleWindowApp:
    """Encapsulates the single window lifecycle."""

    def __init__(self) -> None:
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Prompt Automation")
        self.root.geometry(load_geometry())
        self.root.minsize(960, 640)
        self.root.resizable(True, True)

        self.template: Optional[Dict[str, Any]] = None
        self.variables: Optional[Dict[str, Any]] = None
        self.final_text: Optional[str] = None

        def _on_close() -> None:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            finally:
                self.root.destroy()

        self.root.protocol("WM_DELETE_WINDOW", _on_close)

    def select_template(self) -> Optional[Dict[str, Any]]:
        self.template = select.build(self)
        return self.template

    def collect_variables(self, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.variables = collect.build(self, template)
        return self.variables

    def review_output(self, template: Dict[str, Any], variables: Dict[str, Any]) -> None:
        review.build(self, template, variables)

    def run(self) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            tmpl = self.select_template()
            if tmpl is None:
                self.root.destroy()
                return None, None
            vars_map = self.collect_variables(tmpl) or {}
            self.review_output(tmpl, vars_map)
            self.root.mainloop()
            return self.final_text, self.variables
        finally:
            try:
                if self.root.winfo_exists():
                    save_geometry(self.root.winfo_geometry())
            except Exception:
                pass


__all__ = ["SingleWindowApp"]
