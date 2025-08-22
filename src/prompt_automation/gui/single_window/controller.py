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
from ..selector.view.exclusions import edit_exclusions as exclusions_dialog
from ...services import exclusions as exclusions_service
from ...services import overrides as selector_service
from ..selector import view as selector_view_module
from .. import options_menu
from ..error_dialogs import show_error, safe_copy_to_clipboard
from ...shortcuts import load_shortcuts


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

        # Current stage name (select|collect|review) and view object returned
        # by the frame builder (namespace or dict). Kept for per-stage menu
        # dynamic commands.
        self._stage: str | None = None
        self._current_view: Any | None = None

        # Build initial menu (will be rebuilt on each stage swap to ensure
        # per-stage actions are exposed consistently).
        self._bind_accelerators(
            options_menu.configure_options_menu(
                self.root, selector_view_module, selector_service, extra_items=self._stage_extra_items
            )
        )

        # Global shortcut help (F1)
        self.root.bind("<F1>", lambda e: (self._show_shortcuts(), "break"))

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

    # --- Menu / accelerator handling ----------------------------------------
    def _bind_accelerators(self, mapping: Dict[str, Any]) -> None:
        # Unconditional bind (tk replaces existing). Wrap each to return break
        for seq, func in mapping.items():
            self.root.bind(seq, lambda e, f=func: (f(), "break"))
        self._accelerators = mapping

    def _rebuild_menu(self) -> None:
        try:
            mapping = options_menu.configure_options_menu(
                self.root,
                selector_view_module,
                selector_service,
                extra_items=self._stage_extra_items,
            )
        except Exception as e:  # pragma: no cover - defensive
            self._log.error("Menu rebuild failed: %s", e, exc_info=True)
            return
        self._bind_accelerators(mapping)

    # Extra items injected into the Options menu: reflect current stage.
    def _stage_extra_items(self, opt_menu, menubar) -> None:  # pragma: no cover - GUI heavy
        import tkinter as tk
        stage = self._stage or "?"
        # Show a disabled header for clarity
        opt_menu.add_separator()
        opt_menu.add_command(label=f"Stage: {stage}", state="disabled")
        # Stage specific utilities
        try:
            if stage == "collect" and getattr(self, "template", None):
                tid = self.template.get("id") if isinstance(self.template, dict) else None
                if tid is not None:
                    opt_menu.add_command(
                        label="Edit template exclusions",
                        command=lambda tid=tid: self.edit_exclusions(tid),
                    )
                if self._current_view and hasattr(self._current_view, "review"):
                    opt_menu.add_command(
                        label="Review ▶",
                        command=lambda: self._current_view.review(),  # type: ignore[attr-defined]
                    )
            elif stage == "review" and self._current_view:
                # Provide copy / finish commands mirroring toolbar buttons.
                if hasattr(self._current_view, "copy"):
                    opt_menu.add_command(
                        label="Copy (stay)",
                        command=lambda: self._current_view.copy(),  # type: ignore[attr-defined]
                    )
                if hasattr(self._current_view, "finish"):
                    opt_menu.add_command(
                        label="Finish (copy & close)",
                        command=lambda: self._current_view.finish(),  # type: ignore[attr-defined]
                    )
        except Exception as e:
            self._log.error("Stage extra menu items failed: %s", e, exc_info=True)

    def start(self) -> None:
        """Enter stage 1 (template selection)."""
        self._clear_content()
        self._stage = "select"
        try:
            self._current_view = select.build(self)
        except Exception as e:
            self._log.error("Template selection failed: %s", e, exc_info=True)
            show_error("Error", f"Failed to open template selector:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass
        self._rebuild_menu()

    def advance_to_collect(self, template: Dict[str, Any]) -> None:
        self.template = template
        self._clear_content()
        self._stage = "collect"
        try:
            self._current_view = collect.build(self, template)
        except Exception as e:
            self._log.error("Variable collection failed: %s", e, exc_info=True)
            show_error("Error", f"Failed to collect variables:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass
        self._rebuild_menu()

    def back_to_select(self) -> None:
        self.start()

    def advance_to_review(self, variables: Dict[str, Any]) -> None:
        self.variables = variables
        self._clear_content()
        self._stage = "review"
        try:
            self._current_view = review.build(self, self.template, variables)
        except Exception as e:
            self._log.error("Review window failed: %s", e, exc_info=True)
            show_error("Error", f"Failed to open review window:\n{e}")
            raise
        else:
            try:
                self.root.update_idletasks()
                save_geometry(self.root.winfo_geometry())
            except Exception:
                pass
        self._rebuild_menu()

    def edit_exclusions(self, template_id: int) -> None:
        """Open the exclusions editor for ``template_id``."""
        try:
            try:
                exclusions_dialog(self.root, exclusions_service, template_id)
            except TypeError:
                exclusions_dialog(self.root, exclusions_service)  # type: ignore[misc]
        except Exception as e:
            self._log.error("Exclusions editor failed: %s", e, exc_info=True)
            show_error("Error", f"Failed to edit exclusions:\n{e}")

    def _show_shortcuts(self) -> None:
        """Display configured template shortcuts in a simple dialog."""
        from tkinter import messagebox

        mapping = load_shortcuts()
        if not mapping:
            msg = "No shortcuts configured."
        else:
            lines = [f"{k}: {v}" for k, v in sorted(mapping.items())]
            msg = "\n".join(lines)
        messagebox.showinfo("Shortcuts", msg)

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
