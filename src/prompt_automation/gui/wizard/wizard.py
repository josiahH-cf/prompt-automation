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
from typing import List, Dict, Any

from ...config import PROMPTS_DIR
from ...renderer import fill_placeholders
from ..fonts import get_display_font
from .steps import SUGGESTED_PLACEHOLDERS, next_template_id

# Legacy helper retained for any external import; now a no-op.
def _slug(text: str) -> str:  # pragma: no cover - legacy shim
    return text




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

    # --- Placeholder Builder -------------------------------------------------
    builder_label = tk.Label(main, text="Placeholders", font=("Arial", 10, "bold"))
    builder_label.pack(anchor="w")
    builder = tk.Frame(main)
    builder.pack(fill="x", pady=(0, 6))

    ph_name_var = tk.StringVar()
    ph_type_var = tk.StringVar(value="text")
    ph_format_var = tk.StringVar(value="")
    ph_default_var = tk.StringVar()
    ph_multiline_var = tk.BooleanVar(value=False)
    ph_persist_var = tk.BooleanVar(value=False)
    ph_override_var = tk.BooleanVar(value=False)
    ph_remove_var = tk.StringVar()  # comma separated phrases
    ph_options_var = tk.StringVar()  # comma separated for 'options' type

    def build_labeled(parent, text, widget):
        row = tk.Frame(parent)
        tk.Label(row, text=text, width=12, anchor="w").pack(side="left")
        widget.pack(side="left", fill="x", expand=True)
        row.pack(fill="x", pady=1)

    build_labeled(builder, "Name", tk.Entry(builder, textvariable=ph_name_var))
    type_combo = ttk.Combobox(builder, textvariable=ph_type_var, values=["text","list","file","number","options"], width=12, state="readonly")
    build_labeled(builder, "Type", type_combo)
    fmt_combo = ttk.Combobox(builder, textvariable=ph_format_var, values=["","list","checklist","auto"], width=12, state="readonly")
    build_labeled(builder, "Format", fmt_combo)
    build_labeled(builder, "Default", tk.Entry(builder, textvariable=ph_default_var))
    build_labeled(builder, "Options", tk.Entry(builder, textvariable=ph_options_var))
    build_labeled(builder, "Remove If Empty", tk.Entry(builder, textvariable=ph_remove_var))

    flags = tk.Frame(builder)
    tk.Checkbutton(flags, text="Multiline", variable=ph_multiline_var).pack(side="left")
    tk.Checkbutton(flags, text="Persist", variable=ph_persist_var).pack(side="left")
    tk.Checkbutton(flags, text="Override(File)", variable=ph_override_var).pack(side="left")
    flags.pack(anchor="w", pady=(2,3))

    # Placeholder list (treeview)
    columns = ("type","default","format","flags")
    ph_tree = ttk.Treeview(main, columns=columns, show="headings", height=6)
    for col in columns:
        ph_tree.heading(col, text=col.capitalize())
        ph_tree.column(col, width=110, stretch=True)
    ph_tree.pack(fill="x", pady=(0,4))

    ph_objects: List[Dict[str, Any]] = []

    def refresh_tree():
        for i in ph_tree.get_children():
            ph_tree.delete(i)
        for ph in ph_objects:
            flags_txt = "+".join([
                f for f, cond in [("M", ph.get("multiline")), ("P", ph.get("persist")), ("O", ph.get("override"))] if cond
            ])
            ph_tree.insert("", "end", iid=ph["name"], values=(ph.get("type","text"), str(ph.get("default",""))[:20], ph.get("format",""), flags_txt))

    def clear_form():
        ph_name_var.set("")
        ph_type_var.set("text")
        ph_format_var.set("")
        ph_default_var.set("")
        ph_multiline_var.set(False)
        ph_persist_var.set(False)
        ph_override_var.set(False)
        ph_remove_var.set("")
        ph_options_var.set("")

    def add_or_update_placeholder():
        name = ph_name_var.get().strip()
        if not name:
            messagebox.showerror("Validation", "Placeholder name required")
            return
        # Basic schema
        ph: Dict[str, Any] = {"name": name}
        ptype = ph_type_var.get().strip() or "text"
        if ptype != "text":
            ph["type"] = ptype
        if ph_format_var.get().strip():
            ph["format"] = ph_format_var.get().strip()
        if ph_default_var.get().strip():
            # list formatting: if list type and comma present -> split; else string
            if ptype == "list" and "\n" in ph_default_var.get():
                ph["default"] = [l for l in ph_default_var.get().splitlines() if l.strip()]
            else:
                ph["default"] = ph_default_var.get()
        if ph_multiline_var.get():
            ph["multiline"] = True
        if ph_persist_var.get():
            ph["persist"] = True
        if ph_override_var.get() and ptype == "file":
            ph["override"] = True
        if ph_remove_var.get().strip():
            phrases = [p.strip() for p in ph_remove_var.get().split(",") if p.strip()]
            if phrases:
                ph["remove_if_empty"] = phrases if len(phrases) > 1 else phrases[0]
        if ptype == "options" and ph_options_var.get().strip():
            opts = [o.strip() for o in ph_options_var.get().split(",") if o.strip()]
            if opts:
                ph["options"] = opts
        # Replace existing by name or append
        for i, existing in enumerate(ph_objects):
            if existing["name"] == name:
                ph_objects[i] = ph
                break
        else:
            ph_objects.append(ph)
        refresh_tree()
        update_preview()
        clear_form()

    def on_tree_select(event):  # populate form for edit
        sel = ph_tree.selection()
        if not sel:
            return
        name = sel[0]
        for ph in ph_objects:
            if ph["name"] == name:
                ph_name_var.set(ph["name"])
                ph_type_var.set(ph.get("type","text"))
                ph_format_var.set(ph.get("format",""))
                dval = ph.get("default")
                if isinstance(dval, list):
                    ph_default_var.set("\n".join(dval))
                elif dval is not None:
                    ph_default_var.set(str(dval))
                else:
                    ph_default_var.set("")
                ph_multiline_var.set(bool(ph.get("multiline")))
                ph_persist_var.set(bool(ph.get("persist")))
                ph_override_var.set(bool(ph.get("override")))
                rem = ph.get("remove_if_empty")
                if isinstance(rem, list):
                    ph_remove_var.set(", ".join(rem))
                elif isinstance(rem, str):
                    ph_remove_var.set(rem)
                else:
                    ph_remove_var.set("")
                if ph.get("type") == "options" and isinstance(ph.get("options"), list):
                    ph_options_var.set(",".join(ph.get("options")))
                else:
                    ph_options_var.set("")
                break

    ph_tree.bind("<<TreeviewSelect>>", on_tree_select)

    btns_row = tk.Frame(main)
    tk.Button(btns_row, text="Add / Update", command=add_or_update_placeholder).pack(side="left")
    def delete_sel():
        sel = ph_tree.selection()
        if not sel:
            return
        name = sel[0]
        for i, ph in enumerate(ph_objects):
            if ph["name"] == name:
                ph_objects.pop(i)
                break
        refresh_tree(); update_preview()
    tk.Button(btns_row, text="Delete", command=delete_sel).pack(side="left", padx=(6,0))
    def move(offset: int):
        sel = ph_tree.selection()
        if not sel:
            return
        name = sel[0]
        for i, ph in enumerate(ph_objects):
            if ph["name"] == name:
                ni = i + offset
                if 0 <= ni < len(ph_objects):
                    ph_objects[i], ph_objects[ni] = ph_objects[ni], ph_objects[i]
                    refresh_tree()
                    ph_tree.selection_set(ph["name"])
                break
        update_preview()
    tk.Button(btns_row, text="Up", command=lambda: move(-1)).pack(side="left", padx=(6,0))
    tk.Button(btns_row, text="Down", command=lambda: move(1)).pack(side="left", padx=(4,0))
    tk.Button(btns_row, text="Clear Form", command=clear_form).pack(side="left", padx=(10,0))
    btns_row.pack(anchor="w", pady=(2,6))

    # Seed with suggested placeholders (without defaults beyond blanks)
    for name in SUGGESTED_PLACEHOLDERS:
        ph_objects.append({"name": name, "multiline": name in {"context","instructions","inputs","constraints","output_format","quality_checks","follow_ups"}})
    refresh_tree()

    # Body editor & preview side-by-side
    body_frame = tk.Frame(main)
    body_frame.pack(fill="both", expand=True)
    body_left = tk.Frame(body_frame)
    body_left.pack(side="left", fill="both", expand=True)
    tk.Label(body_left, text="Template Body (one line per entry)", font=("Arial", 10, "bold")).pack(anchor="w")
    body_text = tk.Text(body_left, height=14, font=get_display_font(master=root))
    body_text.pack(fill="both", expand=True)
    body_text.insert("1.0", "# Compose your template lines here. Use {{placeholder_name}} tokens.\n")

    # Preview
    preview_frame = tk.Frame(body_frame, padx=8)
    preview_frame.pack(side="left", fill="both", expand=True)
    tk.Label(preview_frame, text="Live Preview", font=("Arial", 10, "bold")).pack(anchor="w")
    preview_text = tk.Text(preview_frame, height=14, font=get_display_font(master=root), state="disabled")
    preview_text.pack(fill="both", expand=True)

    def compute_preview() -> str:
        lines = body_text.get("1.0", "end-1c").splitlines()
        # Build value map from defaults
        var_map: Dict[str, Any] = {}
        for ph in ph_objects:
            d = ph.get("default")
            if isinstance(d, list):
                var_map[ph["name"]] = d
            elif isinstance(d, str):
                var_map[ph["name"]] = d
            else:
                var_map[ph["name"]] = ""  # empty
        try:
            rendered = fill_placeholders(lines, var_map)
        except Exception as e:
            rendered = f"<error rendering: {e}>"
        return rendered

    def update_preview():
        text = compute_preview()
        preview_text.configure(state="normal")
        preview_text.delete("1.0", "end")
        preview_text.insert("1.0", text)
        preview_text.configure(state="disabled")

    tk.Button(preview_frame, text="Refresh Preview", command=update_preview).pack(anchor="w", pady=(4,2))
    update_preview()

    # Private checkbox & metadata/global exclusions
    opts_frame = tk.Frame(main)
    opts_frame.pack(fill="x", pady=(4,2))
    tk.Checkbutton(opts_frame, text="Private (store under prompts/local)", variable=private_var).pack(side="left")
    share_var = tk.BooleanVar(value=True)
    tk.Checkbutton(opts_frame, text="Shareable", variable=share_var).pack(side="left", padx=(12,0))

    # Global placeholder exclusion checkboxes
    exclude_frame = tk.Frame(main)
    exclude_frame.pack(fill="x", pady=(2,4))
    tk.Label(exclude_frame, text="Include Globals:", font=("Arial",9,"bold")).pack(anchor="w")
    global_keys: List[str] = []
    gfile = PROMPTS_DIR / "globals.json"
    if gfile.exists():
        try:
            gdata = json.loads(gfile.read_text())
            gph = gdata.get("global_placeholders") or {}
            if isinstance(gph, dict):
                global_keys = sorted([k for k in gph.keys() if isinstance(k, str)])
        except Exception:
            global_keys = []
    global_vars: Dict[str, tk.BooleanVar] = {}
    if global_keys:
        row = tk.Frame(exclude_frame)
        row.pack(fill="x")
        for k in global_keys:
            var = tk.BooleanVar(value=True)
            global_vars[k] = var
            tk.Checkbutton(row, text=k, variable=var).pack(side="left", padx=2)
    else:
        tk.Label(exclude_frame, text="(no globals detected)").pack(anchor="w")

    status_var = tk.StringVar()
    tk.Label(main, textvariable=status_var, fg="#2c662d", anchor="w").pack(fill="x", pady=(4, 2))

    btns = tk.Frame(main); btns.pack(fill="x", pady=(8,0))

    def build_skeleton(phs: List[str]) -> List[str]:
        # Provide a minimal scaffold only if body still default.
        lines: List[str] = []
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
        pid = next_template_id(base_style_dir)
        # If user left the single starter line, build skeleton automatically
        raw_body_lines = [l for l in body_text.get("1.0", "end-1c").splitlines()]
        if len(raw_body_lines) <= 2 and raw_body_lines[0].startswith("# Compose your template"):
            body = build_skeleton([p["name"] for p in ph_objects]) or []
        else:
            body = raw_body_lines
        data = {
            "schema": 1,
            "id": pid,
            "title": title,
            "style": style_name,
            "role": "assistant",  # no automatic role placeholder
            # Order: placeholders then template for workflow preference
            "placeholders": ph_objects,
            "template": body,
            "global_placeholders": {},
            "metadata": {
                # 'path' deprecated: keep empty string to signal no sync-to-title renaming.
                "path": "",
                "tags": [],
                "version": 1,
                "render": "markdown",
                "share_this_file_openly": share_var.get() and not private_var.get(),
            },
        }
        # Exclusions: any global key checkbox that is unchecked
        excluded = [k for k, var in global_vars.items() if not var.get()]
        if excluded:
            data["metadata"]["exclude_globals"] = excluded
        pad_width = 2 if pid < 100 else len(str(pid))
        fname = f"{pid:0{pad_width}d}.json"
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

