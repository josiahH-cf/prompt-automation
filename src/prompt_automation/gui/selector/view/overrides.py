from __future__ import annotations

"""Override management dialog for the selector GUI."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hints only
    import tkinter as tk


def manage_overrides(root: "tk.Tk", service) -> None:
    """Unified manager for file & simple value overrides with inline editing."""
    import tkinter as tk
    from tkinter import ttk
    import json

    win = tk.Toplevel(root)
    win.title("Manage Overrides")
    win.geometry("760x420")
    frame = tk.Frame(win, padx=12, pady=12)
    frame.pack(fill="both", expand=True)
    hint = tk.Label(
        frame,
        text="Double‑click a row to edit value (simple overrides). Delete removes. File overrides show path/skip.",
        wraplength=720,
        justify="left",
        fg="#555",
    )
    hint.pack(anchor="w", pady=(0, 6))
    cols = ("kind","tid","name","data")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    widths = {"kind":80, "tid":60, "name":160, "data":360}
    for c in cols:
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=widths[c], anchor="w")
    sb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def _refresh():
        tree.delete(*tree.get_children())
        for tid, name, info in service.list_file_overrides():
            tree.insert("", "end", values=("file", tid, name, json.dumps(info)))
        for tid, name, val in service.list_template_value_overrides():
            if isinstance(val, list):
                display = ", ".join(str(v) for v in val[:5]) + (" …" if len(val) > 5 else "")
            else:
                display = str(val)
            tree.insert("", "end", values=("value", tid, name, display))
    _refresh()

    def _edit(event=None):
        sel = tree.selection()
        if not sel:
            return
        item = tree.item(sel[0]); kind, tid, name, data = item['values']
        if kind != 'value':
            return  # only simple values editable
        dlg = tk.Toplevel(win)
        dlg.title(f"Edit Override: {tid}/{name}")
        tk.Label(dlg, text=f"Template {tid} – {name}").pack(padx=10,pady=(10,4))
        txt = tk.Text(dlg, width=60, height=6, wrap='word')
        txt.pack(padx=10, pady=4)
        txt.insert('1.0', data)
        def _ok():
            val = txt.get('1.0','end-1c').strip()
            service.set_template_value_override(int(tid), name, val)
            _refresh(); dlg.destroy()
        tk.Button(dlg, text='Save', command=_ok).pack(side='left', padx=10, pady=8)
        tk.Button(dlg, text='Cancel', command=dlg.destroy).pack(side='left', padx=4, pady=8)
        dlg.transient(win); dlg.grab_set(); txt.focus_set()
        dlg.bind('<Escape>', lambda e: (dlg.destroy(),'break'))
        dlg.bind('<Return>', lambda e: (_ok(),'break'))
    tree.bind('<Double-1>', _edit)

    btns = tk.Frame(win); btns.pack(pady=8)
    def do_remove():
        sel = tree.selection()
        if not sel:
            return
        item = tree.item(sel[0]); kind, tid, name, _ = item['values']
        removed = False
        if kind == 'file':
            removed = service.reset_single_file_override(int(tid), name)
        else:
            removed = service.reset_template_value_override(int(tid), name)
        if removed:
            tree.delete(sel[0])
    tk.Button(btns, text="Remove Selected", command=do_remove).pack(side="left", padx=4)
    tk.Button(btns, text="Close", command=win.destroy).pack(side="left", padx=4)
