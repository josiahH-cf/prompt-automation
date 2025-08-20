"""Controller for the single-window GUI workflow.

The original refactor introduced placeholder frame builders which produced a
blank window. This controller now orchestrates three in-window stages:

1. Template selection
2. Variable collection
3. Output review / finish

Each stage swaps a single content frame inside ``root``. The public ``run``
method blocks via ``mainloop`` until the workflow finishes or is cancelled.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ...errorlog import get_logger
from .geometry import load_geometry, save_geometry
from .frames import select, collect, review


class SingleWindowApp:
    """Encapsulates the single window lifecycle."""

    def __init__(self) -> None:
        import tkinter as tk

        self._log = get_logger("prompt_automation.gui.single_window")

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

    # --- Stage orchestration -------------------------------------------------
    def _clear_content(self) -> None:
        for child in list(self.root.children.values()):
            try:
                child.destroy()
            except Exception:
                pass

    def start(self) -> None:
        """Enter stage 1 (template selection)."""
        self._clear_content()
        try:
            select.build(self)
        except Exception as e:
            self._log.error("Template selection failed: %s", e, exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Error", f"Failed to open template selector:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass

    def advance_to_collect(self, template: Dict[str, Any]) -> None:
        self.template = template
        self._clear_content()
        try:
            collect.build(self, template)
        except Exception as e:
            self._log.error("Variable collection failed: %s", e, exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Error", f"Failed to collect variables:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass

    def back_to_select(self) -> None:
        self.start()

    def advance_to_review(self, variables: Dict[str, Any]) -> None:
        self.variables = variables
        self._clear_content()
        try:
            review.build(self, self.template, variables)
        except Exception as e:
            self._log.error("Review window failed: %s", e, exc_info=True)
            from tkinter import messagebox

            messagebox.showerror("Error", f"Failed to open review window:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass

    def finish(self, final_text: str) -> None:
        self.final_text = final_text
        try:
            self.root.quit()
        finally:
            self.root.destroy()

    def cancel(self) -> None:
        self.final_text = None
        self.variables = None
        try:
            self.root.quit()
        finally:
            self.root.destroy()

    def run(self) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            self.start()
            self.root.mainloop()
            return self.final_text, self.variables
        finally:  # persistence best effort
            try:
                if self.root.winfo_exists():
                    save_geometry(self.root.winfo_geometry())
            except Exception:
                pass


__all__ = ["SingleWindowApp"]
