from __future__ import annotations

"""Dialog to edit template exclusion metadata."""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # pragma: no cover - hints only
    import tkinter as tk


def edit_exclusions(root: "tk.Tk", service) -> None:  # pragma: no cover - GUI dialog
    if not hasattr(service, "load_exclusions"):
        return

    import tkinter as tk

    dlg = tk.Toplevel(root)
    dlg.title("Edit Global Exclusions (exclude_globals)")
    dlg.geometry("640x400")
    tk.Label(dlg, text="Enter template ID (numeric) or browse to load its metadata.").pack(anchor='w', padx=10, pady=(10,4))
    topf = tk.Frame(dlg); topf.pack(fill='x', padx=10)
    id_var = tk.StringVar()
    tk.Entry(topf, textvariable=id_var, width=10).pack(side='left')
    status_var = tk.StringVar(value="")
    tk.Label(dlg, textvariable=status_var, fg="#555").pack(anchor='w', padx=10, pady=(4,4))
    txt = tk.Text(dlg, wrap='word')
    txt.pack(fill='both', expand=True, padx=10, pady=6)
    txt.insert('1.0', "# Enter one global key per line to exclude for this template\n")
    current_id: List[int] = []

    def _load():
        tid = id_var.get().strip()
        if not tid.isdigit():
            status_var.set("Template id must be numeric")
            return
        exclusions = service.load_exclusions(int(tid))
        if exclusions is None:
            status_var.set("Template not found")
            return
        current_id.clear(); current_id.append(int(tid))
        txt.delete('1.0','end')
        if exclusions:
            txt.insert('1.0', "\n".join(exclusions))
        status_var.set(f"Loaded {tid}")

    def _save():
        if not current_id:
            status_var.set("Load a template first")
            return
        raw = [
            l.strip()
            for l in txt.get('1.0','end-1c').splitlines()
            if l.strip() and not l.strip().startswith('#')
        ]
        ok = service.set_exclusions(current_id[0], raw)
        status_var.set("Saved" if ok else "Write error")

    tk.Button(topf, text="Load", command=_load).pack(side='left', padx=6)
    tk.Button(topf, text="Save", command=_save).pack(side='left')
    tk.Button(topf, text="Close", command=dlg.destroy).pack(side='right')
    dlg.transient(root); dlg.grab_set(); dlg.focus_set()
