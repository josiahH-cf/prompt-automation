"""Template selection frame for single-window mode.

Simplified (not feature-complete) list of available templates discovered under
``PROMPTS_DIR``. Selecting one and pressing Enter or clicking *Next* advances
to the variable collection stage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from ....config import PROMPTS_DIR
from ....errorlog import get_logger
from ....renderer import load_template
from ....services.template_search import list_templates, resolve_shortcut
from ....services import multi_select as multi_select_service
from ...constants import INSTR_SELECT_SHORTCUTS


_log = get_logger(__name__)


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
            "preview": "",
        }
        instr = {"text": INSTR_SELECT_SHORTCUTS}

        def _refresh() -> None:
            state["paths"] = list_templates(state["query"], state["recursive"])
            state["preview"] = ""

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

        def _set_preview(path: Path) -> None:
            try:
                tmpl = load_template(path)
                state["preview"] = "\n".join(tmpl.get("template", []))
            except Exception as e:
                state["preview"] = f"Error: {e}"

        def select(indices):
            state["selected"] = []
            if indices:
                idx_paths = [
                    state["paths"][i] for i in indices if i < len(state["paths"])
                ]
                for p in idx_paths:
                    try:
                        state["selected"].append(load_template(p))
                    except Exception:
                        pass
                _set_preview(idx_paths[0])
            else:
                state["preview"] = ""

        def combine():
            tmpl = multi_select_service.merge_templates(state["selected"])
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
            instructions=instr,
        )

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Select Template", font=("Arial", 14, "bold")).pack(pady=(12, 4))
    tk.Label(frame, text=INSTR_SELECT_SHORTCUTS, anchor="w", fg="#444").pack(
        fill="x", padx=12
    )

    search_bar = tk.Frame(frame)
    search_bar.pack(fill="x", padx=12)
    query = tk.StringVar(value="")
    entry = tk.Entry(search_bar, textvariable=query)
    entry.pack(side="left", fill="x", expand=True)
    recursive_var = tk.BooleanVar(value=True)

    main = tk.Frame(frame)
    main.pack(fill="both", expand=True)
    listbox = tk.Listbox(main, activestyle="dotbox", selectmode="extended")
    scrollbar = tk.Scrollbar(main, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    scrollbar.pack(side="left", fill="y", pady=8)

    preview = tk.Text(main, wrap="word", height=10, state="disabled")
    preview.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=8)

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
        update_preview()

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
        tmpl = multi_select_service.merge_templates(loaded)
        if tmpl:
            app.advance_to_collect(tmpl)
        else:
            status.set("Failed to combine")
        return "break"

    next_btn = tk.Button(btn_bar, text="Next ▶", command=proceed)
    next_btn.pack(side="right", padx=4)
    tk.Button(btn_bar, text="Combine ▶", command=combine_action).pack(side="right", padx=4)
    # Moved from search bar: easier tab navigation entry -> listbox without checkbox in between.
    tk.Checkbutton(btn_bar, text="Recursive Search", variable=recursive_var, command=lambda: refresh()).pack(side="right", padx=8)

    entry.bind("<KeyRelease>", refresh)
    listbox.bind("<Return>", proceed)
    listbox.bind("<<ListboxSelect>>", lambda e: update_preview())

    def on_key(event):
        # Only suppress/ignore digits when actively inside a template
        # (collect/review stages). When stage is unknown (e.g., standalone
        # selector usage), allow digits to function normally.
        try:
            st = getattr(app, '_stage', 'select')
            if st in ('collect', 'review'):
                return None
        except Exception:
            pass
        # Normalize key value across platforms. On Windows, numpad digits often
        # arrive with an empty event.char and keysym like "KP_1"; in that case
        # derive the digit so shortcuts and quick-select work consistently.
        key = event.char
        if not key:
            ks = getattr(event, 'keysym', '')
            if ks.startswith('KP_') and len(ks) == 4 and ks[-1].isdigit():
                key = ks[-1]
                try:
                    _log.debug("select.on_key normalized keysym %s -> %s", ks, key)
                except Exception:
                    pass
            elif ks.isdigit():
                key = ks
        # 1. Shortcut mapping (takes precedence over positional index selection)
        tmpl = resolve_shortcut(key)
        if tmpl:
            app.advance_to_collect(tmpl)
            return "break"
        # 2. Fallback: quick-select nth visible template by digit (1..9)
        if key.isdigit() and key != "0":
            idx = int(key) - 1
            if 0 <= idx < listbox.size():
                listbox.selection_clear(0, "end")
                listbox.selection_set(idx)
                listbox.activate(idx)
                proceed()
                return "break"

    frame.bind_all("<Key>", on_key)

    def update_preview():
        sel = listbox.curselection()
        preview.config(state="normal")
        preview.delete("1.0", "end")
        if not sel:
            preview.config(state="disabled")
            return
        path = rel_map.get(sel[0])
        try:
            tmpl = load_template(path)
            lines = tmpl.get("template", [])
            preview.insert("1.0", "\n".join(lines))
        except Exception as e:  # pragma: no cover - runtime
            preview.insert("1.0", f"Error: {e}")
        preview.config(state="disabled")

    refresh()
    # Expose search entry on app for focus preference when snapping back
    try:
        setattr(app, '_select_query_entry', entry)
        setattr(app, '_select_listbox', listbox)
    except Exception:
        pass
    if rel_map:
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_set()
        update_preview()


__all__ = ["build"]
