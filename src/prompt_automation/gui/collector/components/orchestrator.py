"""GUI prompt construction utilities for variable collection."""
from __future__ import annotations

from pathlib import Path

from .ui import create_window
from .formatting import (
    format_list_input,
    load_file_with_limit,
    truncate_default_hint,
)
from ....renderer import read_file_safe
from ...constants import INSTR_ACCEPT_RESET_REFRESH_CANCEL
from ..persistence import (
    CANCELLED,
    CURRENT_DEFAULTS,
    load_template_value_memory,
    persist_template_values,
    get_remembered_context,
    set_remembered_context,
    get_global_reference_file,
)
from ..overrides import (
    load_overrides,
    get_template_entry,
    save_overrides,
    set_template_entry,
    print_one_time_skip_reminder,
)

# ------------------------- file prompts ------------------------------------

def collect_file_variable_gui(template_id: int, placeholder: dict, globals_map: dict):
    """GUI file selector + viewer with persistence, skip & refresh.

    Workflow:
      - If stored path & exists -> open viewer directly.
      - Else show picker dialog; on choose -> persist then open viewer.
      - Viewer key bindings: Ctrl+Enter accept, Ctrl+R reset (repick), Ctrl+U refresh, Esc cancel.
    Return: path string | "" (skipped) | CANCELLED sentinel.
    """
    import tkinter as tk
    from tkinter import filedialog

    SIZE_LIMIT = 200 * 1024
    name = placeholder["name"]
    label = placeholder.get("label", name)
    overrides = load_overrides()
    entry = get_template_entry(overrides, template_id, name) or {}

    if entry.get("skip"):
        print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    def _persist(pth: str):
        set_template_entry(overrides, template_id, name, {"path": pth, "skip": False})
        save_overrides(overrides)

    def _clear():
        ov = load_overrides()
        tmap = ov.get("templates", {}).get(str(template_id), {})
        if name in tmap:
            tmap.pop(name, None)
            save_overrides(ov)

    def _pick_file(initial: str | None = None) -> str | None:
        root = tk.Tk(); root.withdraw()
        fname = filedialog.askopenfilename(title=label, initialfile=initial or "")
        root.destroy()
        return fname or None

    def _show_viewer(path: str):
        viewer = create_window(f"File: {Path(path).name}")
        viewer.geometry("900x680")
        viewer.resizable(True, True)
        viewer.lift(); viewer.focus_force(); viewer.attributes("-topmost", True); viewer.after(100, lambda: viewer.attributes("-topmost", False))
        action = {"value": "cancel"}

        top = tk.Frame(viewer, padx=14, pady=8)
        top.pack(fill="x")
        instr = tk.Label(top, text=INSTR_ACCEPT_RESET_REFRESH_CANCEL, fg="#444")
        instr.pack(side="left")

        text_frame = tk.Frame(viewer)
        text_frame.pack(fill="both", expand=True)
        from ..fonts import get_display_font
        text = tk.Text(text_frame, wrap="word", font=get_display_font(master=viewer))
        scroll = tk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def render():
            content = load_file_with_limit(path, size_limit=SIZE_LIMIT)
            text.delete("1.0", "end")
            text.insert("1.0", content)

        render()

        def on_accept(event=None):
            action["value"] = "accept"; viewer.destroy(); return "break"
        def on_reset(event=None):
            action["value"] = "reset"; viewer.destroy(); return "break"
        def on_refresh(event=None):
            render(); return "break"
        def on_cancel(event=None):
            action["value"] = "cancel"; viewer.destroy(); return "break"

        viewer.bind("<Control-Return>", on_accept)
        viewer.bind("<Control-r>", on_reset); viewer.bind("<Control-R>", on_reset)
        viewer.bind("<Control-u>", on_refresh); viewer.bind("<Control-U>", on_refresh)
        viewer.bind("<Escape>", on_cancel)
        viewer.mainloop()
        return action["value"]

    path = entry.get("path") if isinstance(entry, dict) else None
    if path and not Path(path).expanduser().exists():
        path = None

    while True:
        if not path:
            picked = _pick_file()
            if not picked:
                return CANCELLED
            path = picked
            _persist(path)
        outcome = _show_viewer(path)
        if outcome == "accept":
            return path
        elif outcome == "reset":
            _clear(); path = None; continue
        else:
            return CANCELLED


# ---------------- per-template reference file (viewer) --------------------

def collect_reference_file_variable_gui(template_id: int, placeholder: dict):
    """File selector + viewer (Ctrl+Enter accept, Ctrl+R reset, Ctrl+U refresh, Esc cancel)
    scoped per *template* (not global). Returns path string, empty string if skipped, or CANCELLED.
    """
    import tkinter as tk
    from tkinter import filedialog

    SIZE_LIMIT = 200 * 1024  # 200KB display truncation only
    name = placeholder["name"]
    label = placeholder.get("label", name)

    overrides = load_overrides()
    entry = get_template_entry(overrides, template_id, name) or {}
    if entry.get("skip"):
        print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    def _pick_file(initial: str | None = None) -> str | None:
        root = tk.Tk(); root.withdraw()
        fname = filedialog.askopenfilename(title=label, initialfile=initial or "")
        root.destroy()
        if fname:
            return fname
        return None

    def _persist(path: str):
        set_template_entry(overrides, template_id, name, {"path": path, "skip": False})
        save_overrides(overrides)

    def _clear():
        # remove persisted path
        ov = load_overrides()
        tmpl = ov.get("templates", {}).get(str(template_id), {})
        if name in tmpl:
            tmpl.pop(name, None)
            save_overrides(ov)

    def _show_viewer(path: str):
        viewer = create_window(f"Reference File: {Path(path).name}")
        viewer.geometry("900x680")
        viewer.resizable(True, True)
        viewer.lift(); viewer.focus_force(); viewer.attributes("-topmost", True); viewer.after(100, lambda: viewer.attributes("-topmost", False))
        action = {"value": "cancel"}

        top = tk.Frame(viewer, padx=14, pady=8)
        top.pack(fill="x")
        instr = tk.Label(top, text=INSTR_ACCEPT_RESET_REFRESH_CANCEL, fg="#444")
        instr.pack(side="left")

        text_frame = tk.Frame(viewer)
        text_frame.pack(fill="both", expand=True)
        from ..fonts import get_display_font
        text = tk.Text(text_frame, wrap="word", font=get_display_font(master=viewer))
        scroll = tk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def render():
            content = load_file_with_limit(path, size_limit=SIZE_LIMIT)
            text.delete("1.0", "end")
            text.insert("1.0", content)

        render()

        def on_accept(event=None):
            action["value"] = "accept"; viewer.destroy(); return "break"
        def on_reset(event=None):
            action["value"] = "reset"; viewer.destroy(); return "break"
        def on_refresh(event=None):
            render(); return "break"
        def on_cancel(event=None):
            action["value"] = "cancel"; viewer.destroy(); return "break"

        viewer.bind("<Control-Return>", on_accept)
        viewer.bind("<Control-r>", on_reset); viewer.bind("<Control-R>", on_reset)
        viewer.bind("<Control-u>", on_refresh); viewer.bind("<Control-U>", on_refresh)
        viewer.bind("<Escape>", on_cancel)
        viewer.mainloop()
        return action["value"]

    # Workflow loop
    path = entry.get("path") if isinstance(entry, dict) else None
    if path and not Path(path).expanduser().exists():
        path = None  # stale path triggers repick

    while True:
        if not path:
            picked = _pick_file()
            if not picked:
                return CANCELLED
            path = picked
            _persist(path)
        outcome = _show_viewer(path)
        if outcome == "accept":
            return path
        elif outcome == "reset":
            _clear()
            path = None
            continue
        else:  # cancel
            return CANCELLED


# ------------------ global reference file prompts ---------------------------

def collect_global_reference_file_gui(placeholder: dict):
    """Interactive global reference file selector + viewer.

    Flow:
      - If no stored path: open file dialog, save selection, then open viewer.
      - If stored path exists: open viewer directly.
      - Viewer keybindings:
          Ctrl+Enter -> accept / continue
          Ctrl+R     -> reset (clear path, re-prompt picker, reopen viewer)
          Esc / Close -> cancel (CANCELLED sentinel)
      - Large files (>200KB) truncated with banner notice.
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox

    label = placeholder.get("label", "Reference File")
    SIZE_LIMIT = 200 * 1024  # 200 KB

    def _clear_global_path():
        from ..persistence import reset_global_reference_file
        reset_global_reference_file()
        try:
            ov = load_overrides()
            for tid, mapping in list(ov.get("templates", {}).items()):
                if isinstance(mapping, dict) and "reference_file" in mapping:
                    mapping.pop("reference_file", None)
            save_overrides(ov)
        except Exception:
            pass

    def _persist_path(path: str):
        ov = load_overrides()
        gfiles = ov.setdefault("global_files", {})
        gfiles["reference_file"] = path
        save_overrides(ov)

    def _pick_file(initial: str | None = None) -> str | None:
        root = tk.Tk(); root.withdraw()
        fname = filedialog.askopenfilename(title=label, initialfile=initial or "")
        root.destroy()
        if fname:
            return fname
        return None

    def _show_viewer(path: str) -> str:
        viewer = create_window(f"Reference File: {Path(path).name}")
        viewer.geometry("900x680")
        viewer.resizable(True, True)
        viewer.lift(); viewer.focus_force(); viewer.attributes("-topmost", True); viewer.after(100, lambda: viewer.attributes("-topmost", False))
        action = {"value": "cancel"}
        top = tk.Frame(viewer, padx=14, pady=8); top.pack(fill="x")
        instr = tk.Label(top, text=INSTR_ACCEPT_RESET_REFRESH_CANCEL, fg="#444")
        instr.pack(side="left")
        # Text area
        text_frame = tk.Frame(viewer); text_frame.pack(fill="both", expand=True)
        from ..fonts import get_display_font
        base_family, base_size = get_display_font(master=viewer)
        text = tk.Text(text_frame, wrap="word", font=(base_family, base_size))
        scroll = tk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        # Tags
        text.tag_configure("h1", font=(base_family, base_size + 6, "bold"))
        text.tag_configure("h2", font=(base_family, base_size + 4, "bold"))
        text.tag_configure("h3", font=(base_family, base_size + 2, "bold"))
        text.tag_configure("bold", font=(base_family, base_size, "bold"))
        text.tag_configure("codeblock", background="#f5f5f5", font=(base_family, base_size))
        text.tag_configure("inlinecode", background="#eee")
        text.tag_configure("hr", foreground="#666")

        def _apply_markdown(text_widget, raw: str):
            lines = raw.splitlines(); cursor = 1; in_code = False; code_start_index = None
            for ln in lines:
                line_index = f"{cursor}.0"
                if ln.strip().startswith("```"):
                    if not in_code:
                        in_code = True; code_start_index = line_index
                    else:
                        try: text_widget.tag_add("codeblock", code_start_index, f"{cursor}.0 lineend")
                        except Exception: pass
                        in_code = False; code_start_index = None
                elif not in_code:
                    if ln.startswith("### "): text_widget.tag_add("h3", line_index, f"{cursor}.0 lineend")
                    elif ln.startswith("## "): text_widget.tag_add("h2", line_index, f"{cursor}.0 lineend")
                    elif ln.startswith("# "): text_widget.tag_add("h1", line_index, f"{cursor}.0 lineend")
                    elif ln.strip() in {"---", "***"}: text_widget.tag_add("hr", line_index, f"{cursor}.0 lineend")
                cursor += 1
            import re
            full = text_widget.get("1.0", "end-1c")
            for m in re.finditer(r"\*\*(.+?)\*\*", full): text_widget.tag_add("bold", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")
            for m in re.finditer(r"`([^`]+?)`", full): text_widget.tag_add("inlinecode", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")

        wants_md = (placeholder.get("render") == "markdown")

        def render(markdown: bool = True):
            content = load_file_with_limit(path, size_limit=SIZE_LIMIT).replace("\r", "")
            if markdown and wants_md:
                new_lines=[]; in_code=False
                for ln in content.splitlines():
                    if ln.strip().startswith("```"):
                        in_code = not in_code; new_lines.append(ln); continue
                    if not in_code and ln.startswith("- "): ln = "• " + ln[2:]
                    new_lines.append(ln)
                content_to_insert = "\n".join(new_lines)
            else:
                content_to_insert = content
            text.delete("1.0", "end"); text.insert("1.0", content_to_insert)
            if markdown and wants_md:
                try: _apply_markdown(text, content_to_insert)
                except Exception: pass

        render()

        def on_accept(event=None): action["value"] = "accept"; viewer.destroy(); return "break"
        def on_reset(event=None): action["value"] = "reset"; viewer.destroy(); return "break"
        def on_refresh(event=None): render(); return "break"
        def on_cancel(event=None): action["value"] = "cancel"; viewer.destroy(); return "break"

        viewer.bind("<Control-Return>", on_accept)
        viewer.bind("<Control-r>", on_reset); viewer.bind("<Control-R>", on_reset)
        viewer.bind("<Escape>", on_cancel); viewer.bind("<Control-u>", on_refresh); viewer.bind("<Control-U>", on_refresh)
        viewer.mainloop(); return action["value"]

    # Main flow
    stored = get_global_reference_file()
    path = stored
    while True:
        if not path:
            picked = _pick_file()
            if not picked:
                return CANCELLED
            path = picked
            _persist_path(path)
        action = _show_viewer(path)
        if action == "accept":
            return path
        elif action == "reset":
            _clear_global_path()
            path = None
        else:
            return CANCELLED


# ------------------ context variable prompt ---------------------------------

def collect_context_variable_gui(label: str):
    """Collect context variable with optional file or remember toggle."""
    import tkinter as tk
    from tkinter import filedialog

    remembered = get_remembered_context()

    root = tk.Tk()
    root.title(f"Input: {label}")
    root.geometry("900x540")
    root.resizable(True, True)
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = CANCELLED
    ctx_file = None
    remember_var = {"value": False}

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    label_widget = tk.Label(main_frame, text=f"{label}:", font=("Arial", 12))
    label_widget.pack(anchor="w", pady=(0, 10))

    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    text_widget = tk.Text(text_frame, font=("Arial", 10), wrap="word")
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    text_widget.focus_set()

    def browse_file():
        filename = filedialog.askopenfilename(parent=root)
        if filename:
            nonlocal ctx_file
            ctx_file = filename

    browse_btn = tk.Button(text_frame, text="Browse Context File", command=browse_file, font=("Arial", 10))
    browse_btn.pack(side="right", padx=(10, 0))

    if remembered:
        text_widget.insert("1.0", remembered)

    remember_chk = tk.Checkbutton(
        main_frame,
        text="Remember for next time",
        command=lambda: remember_var.update({"value": not remember_var["value"]}),
    )
    remember_chk.pack(anchor="w")

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=(8, 0))

    def on_ok(event=None):
        nonlocal result
        result = text_widget.get("1.0", "end-1c")
        root.destroy()
        return "break"

    def on_cancel(event=None):
        nonlocal result
        result = CANCELLED
        root.destroy()
        return "break"

    ok_btn = tk.Button(button_frame, text="OK (Ctrl+Enter)", command=on_ok, font=("Arial", 10), padx=20)
    ok_btn.pack(side="left", padx=(0, 10))
    cancel_btn = tk.Button(button_frame, text="Cancel (Esc)", command=on_cancel, font=("Arial", 10), padx=20)
    cancel_btn.pack(side="left")

    root.bind("<Control-Return>", on_ok)
    root.bind("<Control-KP_Enter>", on_ok)
    root.bind("<Escape>", on_cancel)

    root.mainloop()

    remember_ctx = remember_var["value"]
    return result, ctx_file, remember_ctx


# ------------------ reference file viewer -----------------------------------

def show_reference_file_content(path: str) -> None:
    """Display reference file content in a simple viewer."""
    import tkinter as tk

    root = tk.Tk()
    root.title(f"Reference: {Path(path).name}")
    root.geometry("900x680")
    root.resizable(True, True)
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    main_frame = tk.Frame(root, padx=14, pady=8)
    main_frame.pack(fill="both", expand=True)

    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True)
    from ..fonts import get_display_font
    text = tk.Text(text_frame, wrap="word", font=get_display_font(master=root))
    scroll = tk.Scrollbar(text_frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    content = load_file_with_limit(path)
    text.insert("1.0", content)
    text.config(state="disabled")

    toolbar = tk.Frame(main_frame)
    toolbar.pack(fill="x")

    show_raw = {"value": False}

    def _apply_markdown(text_widget, raw: str):
        lines = raw.splitlines(); cursor = 1
        in_code = False; code_start = None
        for ln in lines:
            idx = f"{cursor}.0"
            if ln.strip().startswith("```"):
                if not in_code:
                    in_code = True; code_start = idx
                else:
                    try: text_widget.tag_add("codeblock", code_start, f"{cursor}.0 lineend")
                    except Exception: pass
                    in_code = False; code_start = None
            elif not in_code:
                if ln.startswith("### "):
                    text_widget.tag_add("h3", idx, f"{cursor}.0 lineend")
                elif ln.startswith("## "):
                    text_widget.tag_add("h2", idx, f"{cursor}.0 lineend")
                elif ln.startswith("# "):
                    text_widget.tag_add("h1", idx, f"{cursor}.0 lineend")
            cursor += 1
        import re
        full = text_widget.get("1.0", "end-1c")
        for m in re.finditer(r"\*\*(.+?)\*\*", full):
            start = f"1.0+{m.start(1)}c"; end = f"1.0+{m.end(1)}c"; text_widget.tag_add("bold", start, end)
        for m in re.finditer(r"`([^`]+?)`", full):
            start = f"1.0+{m.start(1)}c"; end = f"1.0+{m.end(1)}c"; text_widget.tag_add("inlinecode", start, end)

    def render(markdown: bool = True):
        if markdown:
            try:
                text.config(state="normal"); text.delete("1.0", "end"); text.insert("1.0", content)
                _apply_markdown(text, content)
                text.config(state="disabled")
            except Exception:
                text.config(state="normal"); text.delete("1.0", "end"); text.insert("1.0", content); text.config(state="disabled")
        else:
            text.config(state="normal"); text.delete("1.0", "end"); text.insert("1.0", content); text.config(state="disabled")

    def toggle_view():
        show_raw["value"] = not show_raw["value"]
        render(markdown=not show_raw["value"])

    def copy_all():
        try:
            import prompt_automation.paste as paste
            paste.copy_to_clipboard(content)
        except Exception:
            pass

    raw_btn = tk.Button(toolbar, text="Raw View", command=toggle_view)
    raw_btn.pack(side="right")
    copy_btn = tk.Button(toolbar, text="Copy All", command=copy_all)
    copy_btn.pack(side="right", padx=(0, 6))

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=(8, 0))

    def on_close(event=None):  # pragma: no cover - GUI
        root.destroy()
        return "break"

    close_btn = tk.Button(button_frame, text="Close (Esc)", command=on_close, font=("Arial", 10), padx=20)
    close_btn.pack()
    root.bind("<Escape>", on_close)
    root.bind("<Return>", on_close)
    root.mainloop()


# ------------------ variable collection loop --------------------------------

def collect_variables_gui(template):
    """Collect variables for template placeholders (GUI) with persistence."""
    # If running in single-window mode, variable collection is handled there.
    try:
        from ..selector import view as _sv  # type: ignore
        if getattr(_sv, "_EMBEDDED_SINGLE_WINDOW_ROOT", None):
            return {}  # signal no-op to caller in single-window path
    except Exception:
        pass
    placeholders = template.get("placeholders", [])
    if not placeholders:
        return {}

    variables = {}
    template_id = template.get("id", 0)
    globals_map = template.get("global_placeholders", {})

    persisted_simple = load_template_value_memory(template_id) if template_id else {}
    globals_notes = {}
    try:
        search_base = Path(template.get("metadata", {}).get("path", "")).parent if template.get("metadata", {}) else None
        candidates = []
        if search_base:
            candidates.append(search_base / "globals.json")
            candidates.append(Path(search_base).parent / "globals.json")
        for cand in candidates:
            if cand and cand.exists():
                try:
                    globals_notes = (globals_notes or {}).copy()
                    globals_notes.update((__import__('json').loads(cand.read_text()).get('notes', {}) or {}))
                    break
                except Exception:
                    pass
    except Exception:
        pass

    for placeholder in placeholders:
        name = placeholder["name"]
        if "label" in placeholder:
            label = placeholder["label"]
        elif name in globals_notes:
            note_text = globals_notes.get(name, "")
            if " – " in note_text:
                _, desc_part = note_text.split(" – ", 1)
                label = desc_part.strip() or name
            else:
                label = note_text.strip() or name
        else:
            label = name
        ptype = placeholder.get("type", "text")
        options = placeholder.get("options", [])
        multiline = placeholder.get("multiline", False) or ptype == "list"

        if name not in variables and name in persisted_simple:
            variables[name] = persisted_simple[name]

        if name == "reference_file_content":
            path = variables.get("reference_file") or get_global_reference_file()
            p = Path(path).expanduser() if path else None
            if p and p.exists():
                show_reference_file_content(str(p))
                variables[name] = read_file_safe(str(p))
            else:
                variables[name] = ""
            continue

        if name == "context":
            remembered = get_remembered_context()
            value, ctx_path, remember_ctx = collect_context_variable_gui(label)
            if value is CANCELLED:
                return None
            variables[name] = value
            if ctx_path:
                variables["context_append_file"] = ctx_path
            if remember_ctx:
                variables["context_remembered"] = value
                set_remembered_context(value)
            elif remembered and not value.strip():
                variables[name] = remembered
            continue

        if ptype == "file":
            if name == "reference_file":
                value = collect_reference_file_variable_gui(template_id, placeholder)
            else:
                value = collect_file_variable_gui(template_id, placeholder, globals_map)
        else:
            default_val = placeholder.get("default") if isinstance(placeholder, dict) else None
            if isinstance(default_val, str):
                CURRENT_DEFAULTS[name] = default_val
            try:
                value = collect_single_variable(name, label, ptype, options, multiline)
            finally:
                CURRENT_DEFAULTS.pop(name, None)
        if value is CANCELLED:
            return None
        if value is None:
            continue
        variables[name] = value

    if template_id:
        try:
            persist_template_values(template_id, placeholders, variables)
        except Exception:
            pass

    return variables


# ------------------ single variable prompt ----------------------------------

def collect_single_variable(name, label, ptype, options, multiline):
    """Collect a single variable with appropriate input method."""
    import tkinter as tk
    from tkinter import ttk, filedialog

    root = tk.Tk()
    root.title(f"Input: {label}")

    def _initial_geometry():
        if multiline or ptype == "list":
            width = 900
            default_len = len(CURRENT_DEFAULTS.get(name, "") or "")
            if default_len <= 200:
                height = 540
            elif default_len <= 800:
                height = 620
            else:
                height = 720
        else:
            width = 700
            height = 230
        return f"{width}x{height}"
    root.geometry(_initial_geometry())
    root.resizable(True, True)

    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = CANCELLED

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    label_widget = tk.Label(main_frame, text=f"{label}:", font=("Arial", 12))
    label_widget.pack(anchor="w", pady=(0, 10))

    input_widget = None
    default_val = CURRENT_DEFAULTS.get(name)

    if options:
        input_widget = ttk.Combobox(main_frame, values=options, font=("Arial", 10))
        input_widget.pack(fill="x", pady=(0, 10))
        input_widget.set(options[0] if options else "")
        input_widget.focus_set()
    elif ptype == "file":
        file_frame = tk.Frame(main_frame)
        file_frame.pack(fill="x", pady=(0, 10))

        input_widget = tk.Entry(file_frame, font=("Arial", 10))
        input_widget.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def browse_file():
            filename = filedialog.askopenfilename(parent=root)
            if filename:
                input_widget.delete(0, "end")
                input_widget.insert(0, filename)

        browse_btn = tk.Button(
            file_frame,
            text="Browse",
            command=browse_file,
            font=("Arial", 10),
        )
        browse_btn.pack(side="right")

        input_widget.focus_set()
    elif multiline or ptype == "list":
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))

        from ..fonts import get_display_font
        input_widget = tk.Text(text_frame, font=get_display_font(master=root), wrap="word")
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=input_widget.yview)
        input_widget.config(yscrollcommand=scrollbar.set)

        input_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        input_widget.focus_set()
    else:
        input_widget = tk.Entry(main_frame, font=("Arial", 10))
        input_widget.pack(fill="x", pady=(0, 10))
        input_widget.focus_set()

    hint_frame = None
    if isinstance(default_val, str) and default_val.strip():
        full_default = default_val
        display_val, truncated = truncate_default_hint(full_default)
        hint_frame = tk.Frame(main_frame, bg="#f2f2f2", padx=8, pady=4, highlightthickness=1, highlightbackground="#ddd")
        hint_frame.pack(fill="x", pady=(0, 10))
        hint_label = tk.Label(
            hint_frame,
            text=f"Default: {display_val}",
            anchor="w",
            justify="left",
            font=("Arial", 9),
            fg="#333",
            bg="#f2f2f2",
            wraplength=440,
        )
        hint_label.pack(side="left", fill="x", expand=True)
        if truncated:
            def show_full():
                top = tk.Toplevel(root)
                top.title(f"Default value – {label}")
                top.geometry("600x400")
                from ..fonts import get_display_font
                txt = tk.Text(top, wrap="word", font=get_display_font(master=top))
                txt.pack(fill="both", expand=True)
                txt.insert("1.0", full_default)
                txt.config(state="disabled")
                btn = tk.Button(top, text="Close", command=top.destroy)
                btn.pack(pady=6)
                top.transient(root); top.grab_set()
            view_btn = tk.Button(hint_frame, text="[view]", command=show_full, bd=0, fg="#555", bg="#f2f2f2", font=("Arial", 9, "underline"))
            view_btn.pack(side="right")

        if isinstance(input_widget, tk.Text):
            if not input_widget.get("1.0", "end-1c").strip():
                input_widget.insert("1.0", full_default)
        else:
            if not input_widget.get().strip():
                input_widget.insert(0, full_default)

    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill="x")

    def on_ok(skip: bool = False):
        nonlocal result
        if skip:
            result = None
        else:
            if isinstance(input_widget, tk.Text):
                value = input_widget.get("1.0", "end-1c")
                if ptype == "list":
                    result = format_list_input(value)
                else:
                    result = value
            else:
                result = input_widget.get()
        root.destroy()

    def on_cancel():
        nonlocal result
        result = CANCELLED
        root.destroy()

    submit_label = "OK (Ctrl+Enter)" if isinstance(input_widget, tk.Text) else "OK (Enter)"
    ok_btn = tk.Button(button_frame, text=submit_label, command=on_ok, font=("Arial", 10), padx=20)
    ok_btn.pack(side="left", padx=(0, 10))

    cancel_btn = tk.Button(
        button_frame,
        text="Cancel (Esc)",
        command=on_cancel,
        font=("Arial", 10),
        padx=20,
    )
    cancel_btn.pack(side="left")

    def on_enter(event):
        is_ctrl = bool(event.state & 0x4)
        if isinstance(input_widget, tk.Text) and not is_ctrl:
            return None

        if is_ctrl:
            if isinstance(input_widget, tk.Text):
                current = input_widget.get("1.0", "end-1c").strip()
            else:
                current = input_widget.get().strip()
            if not current:
                on_ok(skip=True)
                return "break"
        on_ok()
        return "break"

    def on_escape(event):
        on_cancel()
        return "break"

    root.bind("<Control-Return>", on_enter)
    root.bind("<Control-KP_Enter>", on_enter)
    root.bind("<Escape>", on_escape)

    if not isinstance(input_widget, tk.Text):
        root.bind("<Return>", on_enter)
        root.bind("<KP_Enter>", on_enter)

    root.mainloop()
    return result


__all__ = [
    "collect_file_variable_gui",
    "collect_global_reference_file_gui",
    "collect_context_variable_gui",
    "show_reference_file_content",
    "collect_variables_gui",
    "collect_single_variable",
]
