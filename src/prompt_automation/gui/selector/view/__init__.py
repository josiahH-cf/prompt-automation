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

# ---------------------------------------------------------------------------
# Backwards compatibility shims expected by options_menu.configure_options_menu
# These lightweight implementations are only invoked in GUI environments; they
# fail silently (logged) if tkinter unavailable. Keeping them here avoids
# circular imports with legacy controller code that previously provided them.

def _manage_shortcuts(root, service):  # pragma: no cover - GUI heavy
    try:
        import tkinter as tk  # type: ignore
        from tkinter import ttk, messagebox  # ttk provides Treeview
        from ....shortcuts import load_shortcuts, save_shortcuts, renumber_templates
    except Exception:
        # silently abort if GUI not available
        return

    win = tk.Toplevel(root)
    win.title("Shortcut Manager")
    win.geometry("620x420")
    frame = tk.Frame(win, padx=10, pady=10)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="Configure digit -> template shortcuts (double click digit to edit)").pack(anchor="w")

    shortcuts = load_shortcuts()

    # Fallback to simple listbox if ttk.Treeview missing
    has_tree = hasattr(ttk, "Treeview")
    tree = None
    listbox = None
    if has_tree:
        cols = ("digit", "template")
        tree = ttk.Treeview(frame, columns=cols, show="headings")  # type: ignore
        tree.heading("digit", text="Digit")
        tree.heading("template", text="Template (relative path)")
        tree.column("digit", width=60, anchor="center")
        tree.column("template", width=440, anchor="w")
        vs = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side="left", fill="both", expand=True, pady=(6,4))
        vs.pack(side="right", fill="y", pady=(6,4))
    else:  # pragma: no cover - unlikely path
        listbox = tk.Listbox(frame)
        listbox.pack(fill="both", expand=True, pady=(6,4))

    def _refresh():
        ordered = sorted(shortcuts.items(), key=lambda kv: (len(kv[0]), kv[0]))
        if tree:
            tree.delete(*tree.get_children())  # type: ignore
            for d, path in ordered:
                tree.insert("", "end", values=(d, path))  # type: ignore
        elif listbox:
            listbox.delete(0, 'end')
            for d, path in ordered:
                listbox.insert('end', f"{d}: {path}")
    _refresh()

    def _edit(event=None):
        if tree:
            sel = tree.selection()  # type: ignore
            if not sel:
                return
            item = tree.item(sel[0])  # type: ignore
            digit, path = item["values"]
        else:
            cur = listbox.curselection() if listbox else []
            if not cur:
                return
            line = listbox.get(cur[0])  # type: ignore
            digit, path = line.split(':',1)
            path = path.strip()
        dlg = tk.Toplevel(win)
        dlg.title(f"Edit Shortcut {digit}")
        body = tk.Frame(dlg); body.pack(fill='both', expand=True, padx=8, pady=8)
        tk.Label(body, text=f"Digit {digit}").pack(anchor='w')
        var = tk.StringVar(value=path)
        entry_row = tk.Frame(body); entry_row.pack(fill='x', pady=(6,4))
        ent = tk.Entry(entry_row, textvariable=var, width=50)
        ent.pack(side='left', fill='x', expand=True)

        # Guided picker: list available templates with id/title/rel
        picker = tk.Listbox(body, height=8)
        try:
            from ....shortcuts import build_shortcut_options, update_shortcut_digit
            options = build_shortcut_options()
        except Exception:
            options = []
            update_shortcut_digit = None  # type: ignore
        labels = [o.get('label','') for o in options]
        for lab in labels:
            picker.insert('end', lab)
        def _apply_pick(event=None):
            sel = picker.curselection()
            if not sel:
                return
            rel = options[sel[0]].get('rel','')
            var.set(rel)
        picker.bind('<Double-1>', _apply_pick)
        picker.pack(fill='both', expand=True, pady=(6,2))

        info = tk.Label(body, text='Tip: Double-click a template above to select. Overwrites will ask to confirm.', fg='#555')
        info.pack(anchor='w', pady=(2,6))

        def _ok():
            new = var.get().strip()
            if new:
                def _confirm_overwrite(d, old, newp):
                    try:
                        return messagebox.askyesno('Overwrite', f'Replace mapping for digit {d}?\n\n{old}\n→ {newp}')
                    except Exception:
                        return True
                if update_shortcut_digit:
                    updated = update_shortcut_digit(shortcuts, str(digit), new, confirm_cb=_confirm_overwrite)  # type: ignore[arg-type]
                else:
                    updated = dict(shortcuts); updated[str(digit)] = new
                shortcuts.clear(); shortcuts.update(updated)
                save_shortcuts(shortcuts)
                _refresh()
            dlg.destroy()
        from tkinter import messagebox
        btns = tk.Frame(dlg); btns.pack(fill='x', pady=(6,6))
        tk.Button(btns, text="Save", command=_ok).pack(side="left", padx=8)
        tk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="left", padx=4)
        ent.focus_set()
        dlg.bind('<Return>', lambda e: (_ok(),'break'))
        dlg.bind('<Escape>', lambda e: (dlg.destroy(),'break'))
    if tree:
        tree.bind('<Double-1>', _edit)  # type: ignore
    elif listbox:
        listbox.bind('<Double-1>', _edit)  # type: ignore

    def _add():
        for i in range(1,10):
            if str(i) not in shortcuts:
                shortcuts[str(i)] = ''
                break
        save_shortcuts(shortcuts); _refresh()

    def _remove():
        if tree:
            sel = tree.selection()  # type: ignore
            if not sel:
                return
            digit = tree.item(sel[0])["values"][0]  # type: ignore
        else:
            sel = listbox.curselection() if listbox else []
            if not sel:
                return
            digit = listbox.get(sel[0]).split(':',1)[0]  # type: ignore
        if digit in shortcuts:
            shortcuts.pop(str(digit), None)
            save_shortcuts(shortcuts); _refresh()

    def _renumber():
        try:
            updated, applied = renumber_templates(shortcuts)
            shortcuts.clear(); shortcuts.update(updated)
            _refresh()
            messagebox.showinfo("Renumber", f"Applied IDs: {len(applied)}")
        except Exception as e:
            messagebox.showerror("Renumber", f"Failed: {e}")

    btns = tk.Frame(win); btns.pack(fill='x', pady=(4,2))
    tk.Button(btns, text="Add", command=_add).pack(side='left')
    tk.Button(btns, text="Remove", command=_remove).pack(side='left', padx=(6,0))
    tk.Button(btns, text="Renumber", command=_renumber).pack(side='left', padx=(6,0))
    tk.Button(btns, text="Close", command=win.destroy).pack(side='right')
    win.bind('<Escape>', lambda e: (win.destroy(),'break'))



__all__ = ["open_template_selector", "SelectorView"]
