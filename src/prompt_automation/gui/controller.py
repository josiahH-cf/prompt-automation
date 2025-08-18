"""High level GUI controller."""
from __future__ import annotations

import sys

from .. import logger, update, updater
from ..errorlog import get_logger
from .selector import open_template_selector
from .collector import collect_variables_gui
from .review_window import review_output_gui
from .single_window import SingleWindowApp
from .file_append import _append_to_files


class PromptGUI:
    """Orchestrates the GUI workflow."""

    def __init__(self) -> None:
        self._log = get_logger("prompt_automation.gui")

    def run(self) -> None:
        """Launch the GUI using Tkinter. Falls back to CLI if GUI fails."""
        # Perform background silent pipx upgrade (non-blocking) then existing
        # manifest-based interactive update (retained behaviour)
        try:  # never block GUI startup
            updater.check_for_update()
        except Exception:
            pass
        update.check_and_prompt()
        try:
            import tkinter as tk  # noqa: F401
            from tkinter import ttk, filedialog, messagebox, simpledialog  # noqa: F401
        except Exception as e:
            self._log.warning("Tkinter not available: %s", e)
            print(
                "[prompt-automation] GUI not available, falling back to terminal mode:",
                e,
                file=sys.stderr,
            )
            from .. import cli

            cli.main(["--terminal"])
            return

        try:
            self._log.info("Starting GUI workflow (single-window mode)")
            single_started = False
            try:
                app = SingleWindowApp(); single_started = True
                final_text, var_map = app.run()
                template = app.template if hasattr(app, 'template') else None
                if template and final_text is not None and var_map is not None:
                    _append_to_files(var_map, final_text)
                    logger.log_usage(template, len(final_text))
                    self._log.info("Workflow completed successfully (single-window)")
                else:
                    self._log.info("User cancelled workflow (single-window)")
                return
            except Exception as e_app:
                self._log.error("Single-window path failed: %s -- falling back", e_app, exc_info=True)
                if single_started:
                    # If failure occurred after partial creation, abort entirely
                    return
                template = open_template_selector()
                if template:
                    variables = collect_variables_gui(template)
                    if variables is not None:
                        final_text, var_map = review_output_gui(template, variables)
                        if final_text is not None:
                            _append_to_files(var_map, final_text)
                            logger.log_usage(template, len(final_text))
                return
        except Exception as e:  # pragma: no cover - GUI runtime errors
            self._log.error("GUI workflow failed: %s", e, exc_info=True)
            try:
                import tkinter as tk
                from tkinter import messagebox

                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "Error",
                    f"An error occurred in the GUI:\n\n{e}\n\nCheck logs for details.",
                )
                root.destroy()
            except Exception:
                print(f"[prompt-automation] GUI Error: {e}", file=sys.stderr)
            raise


__all__ = ["PromptGUI"]
