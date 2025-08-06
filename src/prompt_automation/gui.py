"""Simple GUI front-end for prompt selection and rendering using Tkinter."""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict

from . import logger, menus, paste, update
from .errorlog import get_logger


_log = get_logger(__name__)


def run() -> None:
    """Launch the GUI using Tkinter. Falls back to CLI if GUI fails."""
    update.check_and_prompt()
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox, simpledialog
    except Exception as e:
        _log.warning("Tkinter not available: %s", e)
        print(
            "[prompt-automation] GUI not available, falling back to terminal mode:",
            e,
            file=sys.stderr,
        )
        from . import cli

        cli.main(["--terminal"])
        return

    def build_placeholder_widgets(frame: tk.Frame, tmpl: dict):
        widgets: dict[str, tk.Widget] = {}
        file_keys: set[str] = set()
        for idx, ph in enumerate(tmpl.get("placeholders", [])):
            label = ph.get("label", ph["name"])
            key = ph["name"]
            ptype = ph.get("type")
            tk.Label(frame, text=label).grid(row=idx, column=0, sticky="w")
            if ph.get("options"):
                cb = ttk.Combobox(frame, values=ph["options"], width=30)
                cb.grid(row=idx, column=1, sticky="ew")
                widgets[key] = cb
            elif ptype == "file":
                entry = tk.Entry(frame, width=30)
                entry.grid(row=idx, column=1, sticky="ew")

                def browse(e=entry):
                    path = filedialog.askopenfilename()
                    if path:
                        e.delete(0, "end")
                        e.insert(0, path)

                tk.Button(frame, text="Browse", command=browse).grid(row=idx, column=2)

                def clear(e=entry):
                    e.delete(0, "end")

                tk.Button(frame, text="Clear", command=clear).grid(row=idx, column=3)
                widgets[key] = entry
                file_keys.add(key)
            elif ptype == "list" or ph.get("multiline"):
                txt = tk.Text(frame, width=30, height=3)
                txt.grid(row=idx, column=1, sticky="ew")
                widgets[key] = txt
            else:
                entry = tk.Entry(frame, width=30)
                entry.grid(row=idx, column=1, sticky="ew")
                widgets[key] = entry
        return widgets, file_keys

    def validate_file_inputs(widgets: dict[str, tk.Widget], tmpl: dict):
        invalid: list[str] = []
        for ph in tmpl.get("placeholders", []):
            if ph.get("type") == "file":
                key = ph["name"]
                w = widgets.get(key)
                path = w.get()
                if path and not Path(path).expanduser().is_file():
                    w.config(bg="#ffdddd")
                    invalid.append(key)
                else:
                    w.config(bg="white")
        return invalid

    def prompt_missing_file(widget: tk.Entry, key: str, path: str):
        res = messagebox.askyesnocancel(
            "File not found",
            f"File not found:\n{path}\nYes = Browse, No = Skip, Cancel = Remove",
        )
        if res is True:
            new_path = filedialog.askopenfilename()
            if new_path:
                widget.delete(0, "end")
                widget.insert(0, new_path)
                _log.info("updated file placeholder %s to %s", key, new_path)
                return new_path, False
        elif res is None:
            widget.delete(0, "end")
            _log.info("removed file placeholder %s", key)
            return "", False
        _log.info("skipped missing file %s for %s", path, key)
        return path, True

    def edit_template_window(root: tk.Tk, data=None, path=None):
        if data is None:
            data = {"id": "", "title": "", "style": "", "role": "", "template": [], "placeholders": []}
        win = tk.Toplevel(root)
        win.title("Template")
        win.grab_set()
        tk.Label(win, text="ID").grid(row=0, column=0, sticky="w")
        id_var = tk.StringVar(value=str(data.get("id", "")))
        tk.Entry(win, textvariable=id_var).grid(row=0, column=1, sticky="ew")
        tk.Label(win, text="Title").grid(row=1, column=0, sticky="w")
        title_var = tk.StringVar(value=data.get("title", ""))
        tk.Entry(win, textvariable=title_var).grid(row=1, column=1, sticky="ew")
        tk.Label(win, text="Style").grid(row=2, column=0, sticky="w")
        style_var = tk.StringVar(value=data.get("style", ""))
        tk.Entry(win, textvariable=style_var).grid(row=2, column=1, sticky="ew")
        tk.Label(win, text="Role").grid(row=3, column=0, sticky="w")
        role_var = tk.StringVar(value=data.get("role", ""))
        tk.Entry(win, textvariable=role_var).grid(row=3, column=1, sticky="ew")
        tk.Label(win, text="Template").grid(row=4, column=0, sticky="nw")
        template_text = tk.Text(win, width=60, height=10)
        template_text.insert("1.0", "\n".join(data.get("template", [])))
        template_text.grid(row=4, column=1, sticky="ew")
        tk.Label(win, text="Placeholders (JSON)").grid(row=5, column=0, sticky="nw")
        placeholders_text = tk.Text(win, width=60, height=10)
        placeholders_text.insert("1.0", json.dumps(data.get("placeholders", []), indent=2))
        placeholders_text.grid(row=5, column=1, sticky="ew")
        result = {"path": None}

        def on_save():
            try:
                tpl = {
                    "id": int(id_var.get()),
                    "title": title_var.get(),
                    "style": style_var.get(),
                    "role": role_var.get(),
                    "template": [l for l in template_text.get("1.0", "end-1c").splitlines()],
                    "placeholders": json.loads(placeholders_text.get("1.0", "end-1c") or "[]"),
                }
                result["path"] = menus.save_template(tpl, orig_path=path)
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error saving template: {e}")

        tk.Button(win, text="Save", command=on_save).grid(row=6, column=0, pady=5)
        tk.Button(win, text="Cancel", command=win.destroy).grid(row=6, column=1, pady=5)
        win.wait_window()
        return result["path"]

    root = tk.Tk()
    root.title("Prompt Automation")

    styles = menus.list_styles()
    templates_cache: Dict[str, list[str]] = {}
    current_tmpl = None
    current_path = None
    widgets: dict[str, tk.Widget] = {}
    file_keys: set[str] = set()

    top_frame = tk.Frame(root)
    top_frame.pack(padx=5, pady=5, fill="x")

    tk.Label(top_frame, text="Style").grid(row=0, column=0, sticky="w")
    style_filter_var = tk.StringVar()
    style_filter_entry = tk.Entry(top_frame, textvariable=style_filter_var)
    style_filter_entry.grid(row=0, column=1, sticky="ew")
    new_style_btn = tk.Button(top_frame, text="New Style")
    new_style_btn.grid(row=0, column=2, padx=2)
    del_style_btn = tk.Button(top_frame, text="Del Style")
    del_style_btn.grid(row=0, column=3, padx=2)

    main_frame = tk.Frame(root)
    main_frame.pack(padx=5, pady=5)

    style_listbox = tk.Listbox(main_frame, height=10)
    style_listbox.grid(row=0, column=0, sticky="ns")
    for s in styles:
        style_listbox.insert("end", s)

    tmpl_frame = tk.Frame(main_frame)
    tmpl_frame.grid(row=0, column=1, padx=5)

    tk.Label(tmpl_frame, text="Template").grid(row=0, column=0, sticky="w")
    template_filter_var = tk.StringVar()
    template_filter_entry = tk.Entry(tmpl_frame, textvariable=template_filter_var)
    template_filter_entry.grid(row=0, column=1, sticky="ew")
    new_template_btn = tk.Button(tmpl_frame, text="New")
    new_template_btn.grid(row=0, column=2, padx=2)
    edit_template_btn = tk.Button(tmpl_frame, text="Edit")
    edit_template_btn.grid(row=0, column=3, padx=2)
    del_template_btn = tk.Button(tmpl_frame, text="Del")
    del_template_btn.grid(row=0, column=4, padx=2)

    template_listbox = tk.Listbox(tmpl_frame, height=10, width=30)
    template_listbox.grid(row=1, column=0, columnspan=5, pady=2, sticky="nsew")

    ph_frame = tk.Frame(root)
    ph_frame.pack(padx=5, pady=5, fill="x")

    btn_frame = tk.Frame(root)
    btn_frame.pack(padx=5, pady=5)
    render_btn = tk.Button(btn_frame, text="Render")
    render_btn.grid(row=0, column=0, padx=2)
    paste_btn = tk.Button(btn_frame, text="Paste")
    paste_btn.grid(row=0, column=1, padx=2)
    tk.Button(btn_frame, text="Exit", command=root.destroy).grid(row=0, column=2, padx=2)

    output_text = tk.Text(root, width=80, height=20)
    output_text.pack(padx=5, pady=5)

    def refresh_styles():
        style_listbox.delete(0, "end")
        for s in styles:
            style_listbox.insert("end", s)

    def on_style_filter(*args):
        query = style_filter_var.get().lower()
        filtered = [s for s in styles if query in s.lower()]
        style_listbox.delete(0, "end")
        for s in filtered:
            style_listbox.insert("end", s)

    style_filter_var.trace_add("write", on_style_filter)

    def new_style():
        nonlocal styles
        name = simpledialog.askstring("New style name", "New style name:", parent=root)
        if name:
            menus.add_style(name)
            styles = menus.list_styles()
            refresh_styles()

    def del_style():
        nonlocal styles
        sel = style_listbox.curselection()
        if sel:
            style = style_listbox.get(sel[0])
            if messagebox.askokcancel("Delete style", f"Delete style {style}?"):
                try:
                    menus.delete_style(style)
                    styles = menus.list_styles()
                    refresh_styles()
                    template_listbox.delete(0, "end")
                except Exception as e:
                    messagebox.showerror("Error", f"Cannot delete style: {e}")

    new_style_btn.config(command=new_style)
    del_style_btn.config(command=del_style)

    def on_style_select(event):
        sel = style_listbox.curselection()
        if sel:
            style = style_listbox.get(sel[0])
            templates = [p.name for p in menus.list_prompts(style)]
            templates_cache[style] = templates
            template_listbox.delete(0, "end")
            for t in templates:
                template_listbox.insert("end", t)
            template_filter_var.set("")

    style_listbox.bind("<<ListboxSelect>>", on_style_select)

    def on_template_filter(*args):
        sel = style_listbox.curselection()
        if sel:
            style = style_listbox.get(sel[0])
            templates = templates_cache.get(style) or [p.name for p in menus.list_prompts(style)]
            query = template_filter_var.get().lower()
            filtered = [t for t in templates if query in t.lower()]
            template_listbox.delete(0, "end")
            for t in filtered:
                template_listbox.insert("end", t)

    template_filter_var.trace_add("write", on_template_filter)

    def on_template_select(event):
        nonlocal current_tmpl, current_path, widgets, file_keys
        sel = template_listbox.curselection()
        style_sel = style_listbox.curselection()
        if style_sel and sel:
            style = style_listbox.get(style_sel[0])
            tmpl_name = template_listbox.get(sel[0])
            current_path = menus.PROMPTS_DIR / style / tmpl_name
            current_tmpl = menus.load_template(current_path)
            for w in ph_frame.winfo_children():
                w.destroy()
            widgets, file_keys = build_placeholder_widgets(ph_frame, current_tmpl)

    template_listbox.bind("<<ListboxSelect>>", on_template_select)

    def new_template():
        nonlocal styles
        sel = style_listbox.curselection()
        data = {"style": style_listbox.get(sel[0])} if sel else None
        path = edit_template_window(root, data)
        if path:
            styles = menus.list_styles()
            refresh_styles()
            style = path.parent.name
            templates = [p.name for p in menus.list_prompts(style)]
            templates_cache[style] = templates
            if sel and style_listbox.get(sel[0]) == style:
                template_listbox.delete(0, "end")
                for t in templates:
                    template_listbox.insert("end", t)

    def edit_template():
        nonlocal current_tmpl, current_path, widgets, file_keys, styles
        if current_tmpl and current_path:
            path = edit_template_window(root, current_tmpl, current_path)
            if path:
                current_path = path
                current_tmpl = menus.load_template(path)
                styles = menus.list_styles()
                refresh_styles()
                style = path.parent.name
                templates = [p.name for p in menus.list_prompts(style)]
                templates_cache[style] = templates
                template_listbox.delete(0, "end")
                for t in templates:
                    template_listbox.insert("end", t)
                for w in ph_frame.winfo_children():
                    w.destroy()
                widgets, file_keys = build_placeholder_widgets(ph_frame, current_tmpl)

    def del_template():
        nonlocal current_tmpl, current_path, widgets, file_keys
        if current_path:
            if messagebox.askokcancel("Delete", f"Delete {current_path.name}?"):
                menus.delete_template(current_path)
                current_path = None
                current_tmpl = None
                sel = style_listbox.curselection()
                if sel:
                    style = style_listbox.get(sel[0])
                    templates = [p.name for p in menus.list_prompts(style)]
                    templates_cache[style] = templates
                    template_listbox.delete(0, "end")
                    for t in templates:
                        template_listbox.insert("end", t)
                for w in ph_frame.winfo_children():
                    w.destroy()
                output_text.delete("1.0", "end")
                widgets = {}
                file_keys = set()

    new_template_btn.config(command=new_template)
    edit_template_btn.config(command=edit_template)
    del_template_btn.config(command=del_template)

    def render():
        if not current_tmpl:
            return
        skip_keys = set()
        invalid = validate_file_inputs(widgets, current_tmpl)
        for key in invalid:
            widget = widgets[key]
            path = widget.get()
            new_path, skip = prompt_missing_file(widget, key, path)
            if skip:
                skip_keys.add(key)
        ph_vals = {}
        for ph in current_tmpl.get("placeholders", []):
            key = ph["name"]
            widget = widgets.get(key)
            if isinstance(widget, tk.Text):
                val = widget.get("1.0", "end-1c")
                if ph.get("type") == "list":
                    val = [v for v in val.splitlines() if v]
            else:
                val = widget.get()
            if key in skip_keys:
                val = ""
            ph_vals[key] = val
        text = menus.render_template(current_tmpl, ph_vals)
        output_text.delete("1.0", "end")
        output_text.insert("1.0", text)

    def paste_output():
        text = output_text.get("1.0", "end-1c")
        if not text and current_tmpl:
            render()
            text = output_text.get("1.0", "end-1c")
        if text:
            paste.paste_text(text)
            if current_tmpl:
                logger.log_usage(current_tmpl, len(text))

    def on_return(event):
        text = output_text.get("1.0", "end-1c")
        if text:
            paste.paste_text(text)
            if current_tmpl:
                logger.log_usage(current_tmpl, len(text))

    render_btn.config(command=render)
    paste_btn.config(command=paste_output)
    output_text.bind("<Return>", on_return)

    root.mainloop()

