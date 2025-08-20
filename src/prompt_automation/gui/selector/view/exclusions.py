from __future__ import annotations

"""Dialog to edit template exclusion metadata."""

from typing import TYPE_CHECKING, List
from pathlib import Path

if TYPE_CHECKING:  # pragma: no cover - hints only
    import tkinter as tk


def edit_exclusions(root: "tk.Tk", service) -> None:  # pragma: no cover - GUI dialog
    try:
        import json
        _PD = service.PROMPTS_DIR
    except Exception:
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
    current_path: List[Path] = []

    def _load():
        tid = id_var.get().strip()
        if not tid.isdigit():
            status_var.set("Template id must be numeric")
            return
        target = None
        for p in _PD.rglob("*.json"):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if data.get('id') == int(tid):
                target = (p, data)
                break
        if not target:
            status_var.set("Template not found")
            return
        p, data = target
        current_path.clear(); current_path.append(p)
        meta = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
        raw_ex = meta.get('exclude_globals')
        lines = []
        if isinstance(raw_ex, (list, tuple)):
            lines = [str(x) for x in raw_ex]
        elif isinstance(raw_ex, str):
            if ',' in raw_ex:
                lines = [s.strip() for s in raw_ex.split(',') if s.strip()]
            elif raw_ex.strip():
                lines = [raw_ex.strip()]
        txt.delete('1.0','end')
        if lines:
            txt.insert('1.0', "\n".join(lines))
        status_var.set(f"Loaded {p.name}")

    def _save():
        if not current_path:
            status_var.set("Load a template first")
            return
        p = current_path[0]
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            status_var.set(f"Read error: {e}")
            return
        meta = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
        if not isinstance(meta, dict):
            meta = {}; data['metadata'] = meta
        raw = [l.strip() for l in txt.get('1.0','end-1c').splitlines() if l.strip() and not l.strip().startswith('#')]
        if raw:
            meta['exclude_globals'] = raw
        else:
            meta.pop('exclude_globals', None)
        try:
            p.write_text(json.dumps(data, indent=2))
            status_var.set("Saved")
        except Exception as e:
            status_var.set(f"Write error: {e}")

    tk.Button(topf, text="Load", command=_load).pack(side='left', padx=6)
    tk.Button(topf, text="Save", command=_save).pack(side='left')
    tk.Button(topf, text="Close", command=dlg.destroy).pack(side='right')
    dlg.transient(root); dlg.grab_set(); dlg.focus_set()
