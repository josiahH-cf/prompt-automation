"""GUI wizard to create a new prompt template (folders + JSON skeleton).

Provides an interactive window (no dependency on existing templates) that lets
the user:
  - Choose (or create) a style (top-level folder under PROMPTS_DIR)
  - Optionally pick / create nested subfolders inside the style
  - Enter template title
  - Enter placeholders (one per line) or accept suggested defaults
  - Choose private (store under prompts/local) vs shared (prompts/styles)
  - Provide optional template body override or auto-generate structured body

Writes a valid JSON template file with the next free ID (01-98) in that style.
"""
from __future__ import annotations

from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

from ..config import PROMPTS_DIR


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-") or "template"


def _next_id(style_root: Path) -> int:
    used: set[int] = set()
    for p in style_root.rglob("*.json"):
        try:
            data = json.loads(p.read_text())
            if data.get("style") == style_root.name and isinstance(data.get("id"), int):
                used.add(int(data["id"]))
        except Exception:
            continue
    for i in range(1, 99):
        if i not in used:
            return i
    raise ValueError("No free ID 01-98 remaining in this style")


SUGGESTED_PLACEHOLDERS = [
    "role",
    "objective",
    "context",
    "instructions",
    "inputs",
    "constraints",
    "output_format",
    "quality_checks",
    "follow_ups",
]


def open_new_template_wizard():  # pragma: no cover - GUI logic
    root = tk.Toplevel()
    root.title("New Template Wizard")
    root.geometry("780x640")
    root.resizable(True, True)
    root.lift(); root.focus_force(); root.attributes('-topmost', True); root.after(150, lambda: root.attributes('-topmost', False))

    main = tk.Frame(root, padx=16, pady=14)
    main.pack(fill="both", expand=True)

    # Shared vs private
    private_var = tk.BooleanVar(value=False)

    # Style selection
    tk.Label(main, text="Style (top-level):", font=("Arial", 11, "bold")).pack(anchor="w")
    styles = sorted([p.name for p in PROMPTS_DIR.iterdir() if p.is_dir() and p.name not in {"Settings"}])
    style_var = tk.StringVar(value=styles[0] if styles else "Misc")
    style_combo = ttk.Combobox(main, textvariable=style_var, values=styles, width=28)
    style_combo.pack(fill="x", pady=(0, 8))

    # Subfolder selection / creation inside style
    tk.Label(main, text="Subfolder (optional, can be nested e.g. Sub/Feature):", font=("Arial", 10)).pack(anchor="w")
    subfolder_var = tk.StringVar()
    sub_entry = tk.Entry(main, textvariable=subfolder_var)
    sub_entry.pack(fill="x", pady=(0, 8))

    def browse_dir():
        base_style_path = (PROMPTS_DIR if not private_var.get() else PROMPTS_DIR.parent / "local") / style_var.get()
        base_style_path.mkdir(parents=True, exist_ok=True)
        chosen = filedialog.askdirectory(parent=root, initialdir=str(base_style_path), title="Select / Create Subfolder")
        if chosen:
            try:
                rel = Path(chosen).resolve().relative_to(base_style_path.resolve())
                if str(rel) != ".":
                    subfolder_var.set(str(rel))
                else:
                    subfolder_var.set("")
            except Exception:
                pass

    tk.Button(main, text="Browse Subfolder", command=browse_dir).pack(anchor="w", pady=(0, 8))

    # Title
    tk.Label(main, text="Template Title:", font=("Arial", 11, "bold")).pack(anchor="w")
    title_var = tk.StringVar()
    title_entry = tk.Entry(main, textvariable=title_var)
    title_entry.pack(fill="x", pady=(0, 8))

    # Placeholders
    tk.Label(main, text="Placeholders (one per line):", font=("Arial", 10, "bold")).pack(anchor="w")
    ph_frame = tk.Frame(main)
    ph_frame.pack(fill="both", expand=True)
    ph_text = tk.Text(ph_frame, height=8, font=("Consolas", 10))
    ph_text.pack(fill="both", expand=True)
    ph_text.insert("1.0", "\n".join(SUGGESTED_PLACEHOLDERS))

    # Body override
    body_override_var = tk.BooleanVar(value=True)
    tk.Checkbutton(main, text="Generate skeleton body (uncheck to supply custom body below)", variable=body_override_var).pack(anchor="w", pady=(6, 2))
    body_text = tk.Text(main, height=10, font=("Consolas", 10))
    body_text.pack(fill="both", expand=True)
    body_text.insert("1.0", "# Custom body here (ignored if skeleton generation checked)")

    # Private checkbox
    tk.Checkbutton(main, text="Private (store under prompts/local instead of prompts/styles)", variable=private_var).pack(anchor="w", pady=(6, 2))

    status_var = tk.StringVar()
    tk.Label(main, textvariable=status_var, fg="#2c662d", anchor="w").pack(fill="x", pady=(4, 2))

    btns = tk.Frame(main); btns.pack(fill="x", pady=(8,0))

    def build_skeleton(phs: List[str]) -> List[str]:
        lines: List[str] = []
        # Role section if role placeholder present
        if "role" in phs:
            lines.append("{{role}}")
            lines.append("")
        mapping = [
            ("objective", "## Objective"),
            ("context", "## Context"),
            ("instructions", "## Instructions"),
            ("inputs", "## Inputs"),
            ("constraints", "## Constraints"),
            ("output_format", "## Output Format"),
            ("quality_checks", "## Quality Checks"),
            ("follow_ups", "## Follow-ups"),
        ]
        for name, heading in mapping:
            if name in phs:
                lines.append(heading)
                lines.append(f"{{{{{name}}}}}")
                lines.append("")
        if lines and lines[-1] == "":
            lines.pop()
        return lines

    def do_create():
        title = title_var.get().strip()
        if not title:
            messagebox.showerror("Validation", "Title required")
            return
        style_name = style_var.get().strip() or "Misc"
        shared_root = PROMPTS_DIR
        private_root = PROMPTS_DIR.parent / "local"
        target_root = private_root if private_var.get() else shared_root
        base_style_dir = target_root / style_name
        sub_rel = subfolder_var.get().strip()
        final_dir = base_style_dir / sub_rel if sub_rel else base_style_dir
        try:
            # Ensure the 'local' folder exists if private is checked
            if private_var.get():
                private_root.mkdir(parents=True, exist_ok=True)
            final_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create directory: {e}")
            return
        pid = _next_id(base_style_dir)
        raw_phs = [l.strip() for l in ph_text.get("1.0", "end-1c").splitlines() if l.strip()]
        # Always ensure role first if present
        ph_objects = []
        for name in raw_phs:
            ph_objects.append({"name": name, "multiline": name in {"context","instructions","inputs","constraints","output_format","quality_checks","follow_ups"}})
        # Add defaults for important placeholders
        for ph in ph_objects:
            if ph["name"] == "role":
                ph["default"] = "assistant"
            else:
                ph.setdefault("default", "")
        if body_override_var.get():
            body = build_skeleton([p["name"] for p in ph_objects])
        else:
            body = [l for l in body_text.get("1.0", "end-1c").splitlines()]
        data = {
            "schema": 1,
            "id": pid,
            "title": title,
            "style": style_name,
            "role": "{{role}}" if any(p["name"] == "role" for p in ph_objects) else "assistant",
            "template": body,
            "placeholders": ph_objects,
            "global_placeholders": {},
            "metadata": {
                "path": f"{style_name}/{_slug(title)}.json",
                "tags": [],
                "version": 1,
                "render": "markdown",
                # Will be normalized again by loader; set tentative flag
                "share_this_file_openly": not private_var.get(),
            },
        }
        fname = f"{pid:02d}_{_slug(title)}.json"
        fpath = final_dir / fname
        try:
            if fpath.exists():
                messagebox.showerror("Exists", f"File already exists: {fpath}")
                return
            fpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
            status_var.set(f"Created {fpath}")
            messagebox.showinfo("Created", f"New template written to:\n{fpath}")
            root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write template: {e}")

    tk.Button(btns, text="Create", command=do_create, padx=18).pack(side="left")
    tk.Button(btns, text="Cancel", command=root.destroy, padx=18).pack(side="left", padx=(8,0))

    title_entry.focus_set()
    root.bind('<Return>', lambda e: (do_create(), 'break'))
    root.bind('<Escape>', lambda e: (root.destroy(), 'break'))
    root.mainloop()


__all__ = ["open_new_template_wizard"]
