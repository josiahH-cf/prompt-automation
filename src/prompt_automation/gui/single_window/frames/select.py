"""Template selection frame for single-window mode.

Simplified (not feature-complete) list of available templates discovered under
``PROMPTS_DIR``. Selecting one and pressing Enter or clicking *Next* advances
to the variable collection stage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from ....config import PROMPTS_DIR
from ....renderer import load_template


def _list_templates() -> List[Path]:
    return [p for p in PROMPTS_DIR.rglob("*.json") if p.is_file()]


def build(app) -> None:  # pragma: no cover - Tk runtime
    import tkinter as tk

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Select Template", font=("Arial", 14, "bold")).pack(pady=(12, 4))

    listbox = tk.Listbox(frame, activestyle="dotbox")
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 12))

    paths = _list_templates()
    rel_map: Dict[int, Path] = {}
    for idx, p in enumerate(sorted(paths)):
        rel = p.relative_to(PROMPTS_DIR)
        listbox.insert("end", str(rel))
        rel_map[idx] = p

    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))

    status = tk.StringVar(value=f"{len(paths)} templates")
    tk.Label(btn_bar, textvariable=status, anchor="w").pack(side="left", padx=12)

    def proceed(event=None):
        sel = listbox.curselection()
        if not sel:
            status.set("Select a template first")
            return "break"
        path = rel_map[sel[0]]
        try:
            data = load_template(path)
        except Exception as e:  # pragma: no cover - runtime
            status.set(f"Failed: {e}")
            return "break"
        app.advance_to_collect(data)
        return "break"

    next_btn = tk.Button(btn_bar, text="Next ▶", command=proceed)
    next_btn.pack(side="right", padx=12)

    listbox.bind("<Return>", proceed)
    if paths:
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_set()


__all__ = ["build"]
