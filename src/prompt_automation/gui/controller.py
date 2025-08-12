"""High level GUI controller."""
from __future__ import annotations

import sys

from .. import logger, update, updater
from ..errorlog import get_logger
from .selector import open_template_selector
from .variable_collector import collect_variables_gui
from .review_window import review_output_gui
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
            self._log.info("Starting GUI workflow")
            template = open_template_selector()
            if template:
                self._log.info("Template selected: %s", template.get("title", "Unknown"))
                variables = collect_variables_gui(template)
                if variables is not None:
                    self._log.info(
                        "Variables collected: %d placeholders",
                        len(template.get("placeholders", [])),
                    )
                    final_text, var_map = review_output_gui(template, variables)
                    if final_text is not None:
                        self._log.info(
                            "Final text confirmed, length: %d", len(final_text)
                        )
                        _append_to_files(var_map, final_text)
                        logger.log_usage(template, len(final_text))
                        self._log.info("Workflow completed successfully")
                    else:
                        self._log.info("User cancelled at review stage")
                else:
                    self._log.info("User cancelled during variable collection")
            else:
                self._log.info("User cancelled template selection")
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
