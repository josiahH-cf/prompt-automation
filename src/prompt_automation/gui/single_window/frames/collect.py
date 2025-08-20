"""Variable collection frame for single-window mode.

Builds a scrolling form driven by placeholder metadata.  Widgets are created
via :func:`variable_form_factory` allowing features such as remembered context,
file pickers with skip flags, override reset buttons and optional file view
callbacks.  An exclusions editor and reference file viewer are also exposed
from the returned view for easier testing.
"""
from __future__ import annotations

from typing import Any, Dict
import types

from ....services.variable_form import build_widget as variable_form_factory


def build(app, template: Dict[str, Any]):  # pragma: no cover - Tk runtime
    """Return a view object after constructing the form."""
    import tkinter as tk  # type: ignore

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text=template.get("title", "Variables"),
        font=("Arial", 14, "bold"),
    ).pack(pady=(12, 4))

    canvas = tk.Canvas(frame, borderwidth=0)
    inner = tk.Frame(canvas)
    vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    vsb.pack(side="right", fill="y", padx=(0, 12), pady=8)
    canvas.create_window((0, 0), window=inner, anchor="nw")

    widgets: Dict[str, tk.Widget] = {}
    bindings: Dict[str, Dict[str, Any]] = {}
    placeholders = template.get("placeholders") or []
    if not isinstance(placeholders, list):
        placeholders = []

    for row, ph in enumerate(placeholders):
        name = ph.get("name") if isinstance(ph, dict) else None
        if not name:
            continue
        tk.Label(inner, text=name, anchor="w").grid(
            row=row, column=0, sticky="w", padx=6, pady=4
        )
        ctor, bind = variable_form_factory(ph)
        widget = ctor(inner)
        widgets[name] = widget
        bindings[name] = bind

        if bind.get("path_var") is not None:
            widget.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            entry = getattr(widget, "entry", None)
            browse_btn = getattr(widget, "browse_btn", None)
            skip_btn = getattr(widget, "skip_btn", None)
            if entry:
                entry.pack(side="left", fill="x", expand=True)
            if browse_btn:
                browse_btn.pack(side="left", padx=2)
            if skip_btn:
                skip_btn.pack(side="left", padx=2)
            if bind.get("view") and hasattr(widget, "view_btn"):
                widget.view_btn.pack(side="left", padx=2)  # type: ignore[attr-defined]
        else:
            widget.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            if bind.get("remember_var") is not None:
                tk.Checkbutton(
                    inner,
                    text="Remember",
                    variable=bind.get("remember_var"),
                ).grid(row=row, column=2, padx=6, pady=4, sticky="w")

        if ph.get("override"):
            tk.Label(inner, text="*", fg="red").grid(row=row, column=3, padx=2)

            def _reset(b=bind):
                if b.get("path_var") is not None:
                    b["path_var"].set("")  # type: ignore[index]
                if b.get("skip_var") is not None:
                    b["skip_var"].set(False)  # type: ignore[index]
                b.get("persist", lambda: None)()

            bind["reset"] = _reset
            tk.Button(inner, text="Reset", command=_reset).grid(
                row=row, column=4, padx=2
            )

        if row == 0 and hasattr(widget, "focus_set"):
            widget.focus_set()

    inner.columnconfigure(1, weight=1)

    def _on_config(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner.bind("<Configure>", lambda e: _on_config())

    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))

    def go_back():
        app.back_to_select()

    def review():
        vars_map = {k: b["get"]() or None for k, b in bindings.items()}
        for b in bindings.values():
            b.get("persist", lambda: None)()
        app.advance_to_review(vars_map)

    tk.Button(btn_bar, text="◀ Back", command=go_back).pack(side="left", padx=12)

    template_id = template.get("id")

    def open_exclusions():
        if hasattr(app, "edit_exclusions") and template_id is not None:
            app.edit_exclusions(template_id)

    tk.Button(btn_bar, text="Exclusions", command=open_exclusions).pack(
        side="left", padx=4
    )

    def view_reference():
        if hasattr(app, "view_reference_file"):
            app.view_reference_file()

    tk.Button(btn_bar, text="View Ref", command=view_reference).pack(
        side="left", padx=4
    )

    tk.Button(btn_bar, text="Review ▶", command=review).pack(side="right", padx=12)

    return types.SimpleNamespace(
        frame=frame,
        widgets=widgets,
        bindings=bindings,
        open_exclusions=open_exclusions,
        review=review,
    )


__all__ = ["build"]
