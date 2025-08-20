"""Template selection frame for single-window mode.

Simplified (not feature-complete) list of available templates discovered under
``PROMPTS_DIR``. Selecting one and pressing Enter or clicking *Next* advances
to the variable collection stage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from ....config import PROMPTS_DIR
from ....renderer import load_template
from ....services.template_search import list_templates, resolve_shortcut
from ....services.multi_select import merge_templates


def build(app) -> Any:  # pragma: no cover - Tk runtime
    import tkinter as tk
    import types

    # Headless test stub: if core widgets missing, return a lightweight object
    if not hasattr(tk, "Listbox"):
        state: Dict[str, Any] = {
            "recursive": True,
            "query": "",
            "paths": list_templates("", True),
            "selected": [],
        }

        def _refresh() -> None:
            state["paths"] = list_templates(state["query"], state["recursive"])

        def search(query: str):
            state["query"] = query
            _refresh()
            return state["paths"]

        def toggle_recursive():
            state["recursive"] = not state["recursive"]
            _refresh()
            return state["recursive"]

        def activate_shortcut(key: str):
            tmpl = resolve_shortcut(str(key))
            if tmpl:
                app.advance_to_collect(tmpl)

        def activate_index(n: int):
            if 1 <= n <= len(state["paths"]):
                tmpl = load_template(state["paths"][n - 1])
                app.advance_to_collect(tmpl)

        def select(indices):
            state["selected"] = [
                load_template(state["paths"][i]) for i in indices if i < len(state["paths"])
            ]

        def combine():
            tmpl = merge_templates(state["selected"])
            if tmpl:
                app.advance_to_collect(tmpl)
            return tmpl

        return types.SimpleNamespace(
            search=search,
            toggle_recursive=toggle_recursive,
            activate_shortcut=activate_shortcut,
            activate_index=activate_index,
            select=select,
            combine=combine,
            state=state,
        )

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Select Template", font=("Arial", 14, "bold")).pack(pady=(12, 4))

    search_bar = tk.Frame(frame)
    search_bar.pack(fill="x", padx=12)
    query = tk.StringVar(value="")
    entry = tk.Entry(search_bar, textvariable=query)
    entry.pack(side="left", fill="x", expand=True)
    recursive_var = tk.BooleanVar(value=True)
    tk.Checkbutton(search_bar, text="Recursive", variable=recursive_var, command=lambda: refresh()).pack(side="right")

    listbox = tk.Listbox(frame, activestyle="dotbox", selectmode="extended")
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 12))

    rel_map: Dict[int, Path] = {}

    def refresh(*_):
        paths = list_templates(query.get(), recursive_var.get())
        listbox.delete(0, "end")
        rel_map.clear()
        for idx, p in enumerate(paths):
            rel = p.relative_to(PROMPTS_DIR)
            listbox.insert("end", str(rel))
            rel_map[idx] = p
        status.set(f"{len(paths)} templates")

    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))

    status = tk.StringVar(value="0 templates")
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

    def combine_action(event=None):
        sel = listbox.curselection()
        if len(sel) < 2:
            status.set("Select at least two templates")
            return "break"
        loaded = [load_template(rel_map[i]) for i in sel]
        tmpl = merge_templates(loaded)
        if tmpl:
            app.advance_to_collect(tmpl)
        else:
            status.set("Failed to combine")
        return "break"

    next_btn = tk.Button(btn_bar, text="Next ▶", command=proceed)
    next_btn.pack(side="right", padx=4)
    tk.Button(btn_bar, text="Combine ▶", command=combine_action).pack(side="right", padx=4)

    entry.bind("<KeyRelease>", refresh)
    listbox.bind("<Return>", proceed)

    def on_key(event):
        key = event.char
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < listbox.size():
                listbox.selection_clear(0, "end")
                listbox.selection_set(idx)
                listbox.activate(idx)
                proceed()
                return "break"
        tmpl = resolve_shortcut(key)
        if tmpl:
            app.advance_to_collect(tmpl)
            return "break"

    frame.bind_all("<Key>", on_key)

    refresh()
    if rel_map:
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_set()


__all__ = ["build"]
