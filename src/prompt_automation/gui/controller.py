"""High level GUI controller.

Recent refactor introduced an experimental *single-window* workflow implemented
in :mod:`prompt_automation.gui.single_window`. The current single-window
implementation intentionally uses placeholder frame builders (see
``single_window/frames/*.py``) that do **not** create real widgets yet. This
results in a blank / empty window (only a bare Tk root) exactly like the user
reported.

To avoid shipping a non-functional GUI we gate the experimental path behind the
environment variable ``PROMPT_AUTOMATION_SINGLE_WINDOW=1`` and fall back to the
fully functional legacy multi-step GUI (template selector -> variable
collection -> review window) by default.

Set ``PROMPT_AUTOMATION_SINGLE_WINDOW=1`` to re-enable the new flow while it is
under development.
"""
from __future__ import annotations

import os
import sys

from .. import logger, update, updater
from ..errorlog import get_logger
from .selector import open_template_selector
from .collector import collect_variables_gui
from .review_window import review_output_gui
from . import single_window
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
            if os.environ.get("PROMPT_AUTOMATION_SINGLE_WINDOW") == "1":
                # --- Experimental single-window path ---------------------------------
                self._log.info("Starting GUI workflow (EXPERIMENTAL single-window mode)")
                single_started = False
                try:
                    app = single_window.SingleWindowApp(); single_started = True
                    final_text, var_map = app.run()
                    template = getattr(app, "template", None)
                    if template and final_text is not None and var_map is not None:
                        _append_to_files(var_map, final_text)
                        logger.log_usage(template, len(final_text))
                        self._log.info("Workflow completed successfully (single-window)")
                    else:
                        self._log.info("User cancelled workflow (single-window)")
                    return
                except Exception as e_app:  # pragma: no cover - runtime GUI path
                    self._log.error(
                        "Single-window path failed: %s -- falling back to legacy GUI", e_app,
                        exc_info=True,
                    )
                    if single_started:
                        # If failure occurred after partial creation, abort entirely
                        return
                    # Fall through to legacy flow below

            # --- Legacy multi-window flow (default) ----------------------------------
            self._log.info("Starting GUI workflow (legacy multi-window mode)")
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
