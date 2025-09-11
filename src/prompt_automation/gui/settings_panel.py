from __future__ import annotations

import tkinter as tk

from .constants import INFO_CLOSE_SAVE
from ..variables import storage
from ..errorlog import get_logger

_log = get_logger(__name__)


def _refresh_hotkey() -> None:
    """Refresh background hotkey registration best-effort."""
    try:  # pragma: no cover - relies on optional service
        from ..cli.controller import PromptCLI

        PromptCLI()._maybe_register_background_hotkey()
    except Exception as e:  # pragma: no cover - defensive
        try:
            _log.error("hotkey_refresh_failed error=%s", e)
        except Exception:
            pass


def open_settings_panel(root) -> None:  # pragma: no cover - GUI heavy
    """Open settings panel window."""
    win = tk.Toplevel(root)
    win.title("Settings")
    win.resizable(False, False)
    frame = tk.Frame(win, padx=12, pady=8)
    frame.pack(fill="both", expand=True)

    bg_var = tk.BooleanVar(value=storage.get_background_hotkey_enabled())
    esp_var = tk.BooleanVar(value=storage.get_espanso_enabled())

    def _toggle_bg() -> None:
        try:
            storage.set_background_hotkey_enabled(bg_var.get())
            _refresh_hotkey()
        except Exception as e:
            _log.error("toggle_background_hotkey_failed error=%s", e)

    def _toggle_esp() -> None:
        try:
            storage.set_espanso_enabled(esp_var.get())
            _refresh_hotkey()
        except Exception as e:
            _log.error("toggle_espanso_failed error=%s", e)

    tk.Checkbutton(
        frame,
        text="Enable background activation hotkey",
        variable=bg_var,
        command=_toggle_bg,
        anchor="w",
        justify="left",
    ).pack(anchor="w")
    tk.Checkbutton(
        frame,
        text="Enable Espanso integration",
        variable=esp_var,
        command=_toggle_esp,
        anchor="w",
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    tk.Button(frame, text=INFO_CLOSE_SAVE, command=win.destroy).pack(anchor="e", pady=(8, 0))


__all__ = ["open_settings_panel"]
