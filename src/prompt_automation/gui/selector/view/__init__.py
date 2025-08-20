"""Legacy selector *view* layer public API.

Historically the controller invoked ``view.open_template_selector(service)``
where *service* is the ``prompt_automation.gui.selector.service`` module (used
for dependency injection / easier testing). During refactor this function was
temporarily replaced by a shim that proxied back to the controller, breaking
the expected signature (the controller's function takes no parameters). That
caused the runtime error: ``open_template_selector() takes 0 positional args``.

We restore compatibility by re‑implementing a lightweight template picker UI
that accepts the service module argument. This is intentionally minimal but
functional for the legacy multi-window mode retained as a fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def open_template_selector(service_module) -> Optional[dict]:  # pragma: no cover - GUI runtime
    """Open a simple blocking template selection dialog.

    Parameters
    ----------
    service_module: module
        The injected ``service`` module providing ``PROMPTS_DIR`` and
        ``load_template_by_relative`` (mirrors original design).
    """
    try:
        import tkinter as tk
    except Exception:
        return None

    prompts_dir: Path = getattr(service_module, "PROMPTS_DIR")
    loader = getattr(service_module, "load_template_by_relative")

    root = tk.Tk()
    root.title("Select Template - Prompt Automation")
    root.geometry("600x420")
    root.resizable(True, True)

    tk.Label(root, text="Templates", font=("Arial", 13, "bold")).pack(pady=(10, 4))

    listbox = tk.Listbox(root, activestyle="dotbox")
    scrollbar = tk.Scrollbar(root, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=8)

    rel_paths: list[str] = []
    for p in sorted(prompts_dir.rglob("*.json")):
        try:
            rel = p.relative_to(prompts_dir)
        except Exception:
            continue
        rel_paths.append(str(rel))
        listbox.insert("end", str(rel))

    selection: dict | None = None

    status_var = tk.StringVar(value=f"{len(rel_paths)} templates")
    status_label = tk.Label(root, textvariable=status_var, anchor="w")
    status_label.pack(fill="x", padx=12)

    def choose(event=None):
        nonlocal selection
        cur = listbox.curselection()
        if not cur:
            status_var.set("Select a template")
            return "break"
        rel = rel_paths[cur[0]]
        selection = loader(rel)
        root.destroy()
        return "break"

    def cancel():
        root.destroy()

    btn_bar = tk.Frame(root)
    btn_bar.pack(fill="x", pady=(0, 10))
    tk.Button(btn_bar, text="Cancel", command=cancel).pack(side="right", padx=6)
    tk.Button(btn_bar, text="Open", command=choose).pack(side="right", padx=6)

    listbox.bind("<Return>", choose)
    if rel_paths:
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_set()

    root.mainloop()
    return selection


def __getattr__(name):  # pragma: no cover - dynamic export
    if name == "SelectorView":
        from .orchestrator import SelectorView
        return SelectorView
    raise AttributeError(name)


__all__ = ["open_template_selector", "SelectorView"]
