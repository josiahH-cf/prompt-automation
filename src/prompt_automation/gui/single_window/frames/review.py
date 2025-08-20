"""Output review frame used by :class:`SingleWindowApp`."""
from __future__ import annotations

from typing import Dict, Any

from .. import actions


def build(app, template: Dict[str, Any], variables: Dict[str, Any]):  # pragma: no cover - UI wiring
    """Build the review frame widgets.

    The function returns a dictionary containing references to key widgets so
    tests can inspect their presence without requiring a real GUI backend."""
    import tkinter as tk

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    btns = tk.Frame(frame)
    btns.pack(fill="x")

    copy_btn = None
    if any(k.endswith("_path") for k in variables):
        copy_btn = tk.Button(btns, text="Copy Paths", command=lambda: actions.copy_paths(variables))
        copy_btn.pack(side="left")

    return {"frame": frame, "copy_paths_btn": copy_btn}


__all__ = ["build"]
