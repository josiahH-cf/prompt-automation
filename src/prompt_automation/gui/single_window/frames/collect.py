"""Variable collection frame for single-window mode.

Creates a simple scrolling form of Entry widgets for each placeholder in the
template. Pressing *Review* advances to the review stage.
"""
from __future__ import annotations

from typing import Dict, Any


def build(app, template: Dict[str, Any]) -> None:  # pragma: no cover - Tk runtime
    import tkinter as tk

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text=template.get("title", "Variables"), font=("Arial", 14, "bold")).pack(pady=(12, 4))

    canvas = tk.Canvas(frame, borderwidth=0)
    inner = tk.Frame(canvas)
    vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    vsb.pack(side="right", fill="y", padx=(0, 12), pady=8)
    canvas.create_window((0, 0), window=inner, anchor="nw")

    entries: Dict[str, tk.Entry] = {}
    placeholders = template.get("placeholders") or []
    if not isinstance(placeholders, list):
        placeholders = []
    for row, ph in enumerate(placeholders):
        name = ph.get("name") if isinstance(ph, dict) else None
        if not name:
            continue
        tk.Label(inner, text=name, anchor="w").grid(row=row, column=0, sticky="w", padx=6, pady=4)
        e = tk.Entry(inner, width=80)
        e.grid(row=row, column=1, sticky="we", padx=6, pady=4)
        entries[name] = e
        if row == 0:
            e.focus_set()
    inner.columnconfigure(1, weight=1)

    def _on_config(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>",(lambda e: _on_config()))

    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))

    def go_back():
        app.back_to_select()

    def review():
        vars_map = {k: v.get() or None for k, v in entries.items()}
        app.advance_to_review(vars_map)

    tk.Button(btn_bar, text="◀ Back", command=go_back).pack(side="left", padx=12)
    tk.Button(btn_bar, text="Review ▶", command=review).pack(side="right", padx=12)


__all__ = ["build"]
