"""Input collection utilities for the GUI workflow."""
from __future__ import annotations

from pathlib import Path

from ..renderer import read_file_safe
from ..variables import (
    _get_template_entry,
    _load_overrides,
    _print_one_time_skip_reminder,
    _save_overrides,
    _set_template_entry,
    load_template_value_memory,
    persist_template_values,
    get_remembered_context,
    set_remembered_context,
    get_global_reference_file,
    reset_global_reference_file,
)

# sentinel object to signal user cancellation during input collection
CANCELLED = object()

# Internal mapping used to convey default values into collect_single_variable
CURRENT_DEFAULTS: dict[str, str] = {}


def collect_file_variable_gui(template_id: int, placeholder: dict, globals_map: dict):
    """GUI file selector with persistence and skip support."""
    import tkinter as tk
    from tkinter import filedialog

    name = placeholder["name"]
    label = placeholder.get("label", name)
    # No longer support template/global skip flags via globals.json; only persisted user skip

    overrides = _load_overrides()
    entry = _get_template_entry(overrides, template_id, name) or {}

    if entry.get("skip"):
        _print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    path_str = entry.get("path")
    if path_str:
        p = Path(path_str).expanduser()
        if p.exists():
            return str(p)
        # remove stale path so user is prompted again
        overrides.get("templates", {}).get(str(template_id), {}).pop(name, None)
        _save_overrides(overrides)

    root = tk.Tk()
    root.title(f"File: {label}")
    # Larger default & allow resize/maximize
    root.geometry("640x180")
    root.resizable(True, True)
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = CANCELLED

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    path_var = tk.StringVar()
    entry_widget = tk.Entry(main_frame, textvariable=path_var, font=("Arial", 10))
    entry_widget.pack(side="left", fill="x", expand=True, padx=(0, 10))
    entry_widget.focus_set()

    def browse_file():
        filename = filedialog.askopenfilename(parent=root, title=label)
        if filename:
            path_var.set(filename)

    browse_btn = tk.Button(main_frame, text="Browse", command=browse_file, font=("Arial", 10))
    browse_btn.pack(side="right")

    button_frame = tk.Frame(root)
    button_frame.pack(pady=(10, 0))

    def on_ok():
        nonlocal result
        p = Path(path_var.get()).expanduser()
        if p.exists():
            _set_template_entry(overrides, template_id, name, {"path": str(p), "skip": False})
            _save_overrides(overrides)
            result = str(p)
        else:
            result = ""
        root.destroy()

    def on_skip():
        nonlocal result
        _set_template_entry(overrides, template_id, name, {"skip": True})
        _save_overrides(overrides)
        _print_one_time_skip_reminder(overrides, template_id, name)
        result = ""
        root.destroy()

    def on_cancel():
        nonlocal result
        result = CANCELLED
        root.destroy()

    ok_btn = tk.Button(button_frame, text="OK (Enter)", command=on_ok, font=("Arial", 10), padx=20)
    ok_btn.pack(side="left", padx=(0, 10))

    skip_btn = tk.Button(button_frame, text="Skip", command=on_skip, font=("Arial", 10), padx=20)
    skip_btn.pack(side="left", padx=(0, 10))

    cancel_btn = tk.Button(button_frame, text="Cancel (Esc)", command=on_cancel, font=("Arial", 10), padx=20)
    cancel_btn.pack(side="left")

    root.bind("<Return>", lambda e: (on_ok(), "break"))
    root.bind("<KP_Enter>", lambda e: (on_ok(), "break"))
    root.bind("<Escape>", lambda e: (on_cancel(), "break"))

    root.mainloop()
    return result


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
    from ..renderer import read_file_safe

    label = placeholder.get("label", "Reference File")
    SIZE_LIMIT = 200 * 1024  # 200 KB

    def _clear_global_path():
        reset_global_reference_file()
        try:
            ov = _load_overrides()
            for tid, mapping in list(ov.get("templates", {}).items()):
                if isinstance(mapping, dict) and "reference_file" in mapping:
                    mapping.pop("reference_file", None)
            _save_overrides(ov)
        except Exception:
            pass

    def _persist_path(path: str):
        ov = _load_overrides()
        gfiles = ov.setdefault("global_files", {})
        gfiles["reference_file"] = path
        _save_overrides(ov)

    def _pick_file(initial: str | None = None) -> str | None:
        root = tk.Tk(); root.withdraw()
        fname = filedialog.askopenfilename(title=label, initialfile=initial or "")
        root.destroy()
        if fname:
            return fname
        return None

    def _show_viewer(path: str) -> str:
        # returns 'accept' | 'reset' | 'cancel'
        viewer = tk.Tk()
        viewer.title(f"Reference File: {Path(path).name}")
        viewer.geometry("900x680")
        viewer.resizable(True, True)
        viewer.lift(); viewer.focus_force(); viewer.attributes("-topmost", True); viewer.after(100, lambda: viewer.attributes("-topmost", False))

        action = {"value": "cancel"}

        # Toolbar/instructions
        top = tk.Frame(viewer, padx=14, pady=8)
        top.pack(fill="x")
        instr = tk.Label(top, text="Ctrl+Enter = Continue   |   Ctrl+R = Reset   |   Ctrl+U = Refresh   |   Esc = Cancel", fg="#444")
        instr.pack(side="left")

        # Text area
        text_frame = tk.Frame(viewer)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, wrap="word", font=("Consolas", 10))
        scroll = tk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        # Markdown tag styles
        text.tag_configure("h1", font=("Consolas", 16, "bold"))
        text.tag_configure("h2", font=("Consolas", 14, "bold"))
        text.tag_configure("h3", font=("Consolas", 12, "bold"))
        text.tag_configure("bold", font=("Consolas", 10, "bold"))
        text.tag_configure("codeblock", background="#f5f5f5", font=("Consolas", 10))
        text.tag_configure("inlinecode", background="#eee")
        text.tag_configure("hr", foreground="#666")

        def _render(reload: bool = True):
            # load & render content
            try:
                raw_bytes = Path(path).read_bytes() if reload else b""
            except Exception:
                raw_bytes = b""
            truncated = len(raw_bytes) > SIZE_LIMIT
            display_bytes = raw_bytes[:SIZE_LIMIT] if truncated else raw_bytes
            try:
                content = display_bytes.decode("utf-8", errors="replace")
            except Exception:
                content = read_file_safe(path)
            banner = ""
            if truncated:
                banner = f"[Truncated to {SIZE_LIMIT//1024}KB of {len(raw_bytes)//1024}KB. Press Ctrl+R to pick a different file if needed.]\n\n"
            render_flag = str(placeholder.get("render", "")).lower() in {"md", "markdown"}
            is_markdown = render_flag or (Path(path).suffix.lower() in {".md", ".markdown"} or any(l.startswith("#") for l in content.splitlines()[:20]))
            text.config(state="normal")
            text.delete("1.0", "end")
            if banner:
                text.insert("1.0", banner)
            if not is_markdown:
                text.insert("end", content)
                text.config(state="disabled")
                return
            import re as _re
            in_code = False
            for line in content.splitlines():
                if line.strip().startswith("```"):
                    if not in_code:
                        in_code = True; text.insert("end", "\n")
                    else:
                        in_code = False
                    continue
                if in_code:
                    start = text.index("end-1c"); text.insert("end", line + "\n"); text.tag_add("codeblock", start, text.index("end-1c")); continue
                if _re.match(r"^---+$", line.strip()):
                    start = text.index("end-1c"); text.insert("end", "\n" + line.strip() + "\n"); text.tag_add("hr", start, text.index("end-1c")); continue
                m = _re.match(r"^(#{1,6})\s+(.*)$", line)
                if m:
                    hashes, content_line = m.groups(); lvl = min(len(hashes), 3)
                    start = text.index("end-1c"); text.insert("end", content_line + "\n"); text.tag_add(f"h{lvl}", start, text.index("end-1c")); continue
                pos_before = text.index("end-1c")
                working = line; cursor = 0; bold_pattern = _re.compile(r"\*\*(.+?)\*\*")
                while True:
                    bm = bold_pattern.search(working, cursor)
                    if not bm:
                        text.insert("end", working[cursor:] + "\n"); break
                    text.insert("end", working[cursor:bm.start()])
                    bold_start = text.index("end-1c"); text.insert("end", bm.group(1)); bold_end = text.index("end-1c"); text.tag_add("bold", bold_start, bold_end)
                    cursor = bm.end()
                    if cursor >= len(working):
                        text.insert("end", "\n"); break
                # Inline code replacements
                line_start_idx = pos_before; line_end_idx = text.index("end-2c lineend"); line_text = text.get(line_start_idx, line_end_idx)
                for s, e in reversed([(m.start(), m.end()) for m in _re.finditer(r"`([^`]+)`", line_text)]):
                    inner = _re.match(r"`([^`]+)`", line_text[s:e]).group(1)
                    abs_start = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + s}"; abs_end = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + e}"
                    text.delete(abs_start, abs_end); text.insert(abs_start, inner)
                    new_end_idx = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + s + len(inner)}"; text.tag_add("inlinecode", abs_start, new_end_idx)
            text.config(state="disabled")

        _render()

        def _refresh(event=None):
            y = text.yview()
            _render()
            try: text.yview_moveto(y[0])
            except Exception: pass
            return "break"

        def _accept(event=None):
            action["value"] = "accept"; viewer.destroy(); return "break"
        def _reset(event=None):
            action["value"] = "reset"; viewer.destroy(); return "break"
        def _cancel(event=None):
            action["value"] = "cancel"; viewer.destroy(); return "break"

        viewer.bind("<Control-Return>", _accept)
        viewer.bind("<Control-KP_Enter>", _accept)
        viewer.bind("<Escape>", _cancel)
        viewer.bind("<Control-r>", _reset)
        viewer.bind("<Control-u>", _refresh)
        viewer.protocol("WM_DELETE_WINDOW", lambda: _cancel())
        viewer.mainloop()
        return action["value"]

    # Main loop
    current = get_global_reference_file()
    if current and not Path(current).expanduser().exists():
        _clear_global_path()
        current = None

    while True:
        if not current:
            picked = _pick_file()
            if not picked:
                return CANCELLED
            current = str(Path(picked).expanduser())
            _persist_path(current)
        action = _show_viewer(current)
        if action == "accept":
            return current
        if action == "reset":
            _clear_global_path()
            current = None
            continue  # loop re-picks and reopens viewer
        if action == "cancel":
            return CANCELLED


def collect_context_variable_gui(label: str):
    """Collect context text with optional file loading and remember toggle.

    Returns (value, selected_path, remember_flag). If user cancels, value is CANCELLED.
    Submission uses Ctrl+Enter (Enter inserts newline) to match multiline convention.
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.title(f"Context: {label}")
    root.geometry("700x500")
    root.resizable(True, True)
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = CANCELLED
    selected_path = ""
    remember_flag = False
    # Fetch any previously remembered context
    try:
        remembered_context = get_remembered_context()
    except Exception:
        remembered_context = None

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    text_widget = tk.Text(text_frame, font=("Consolas", 10), wrap="word")
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    path_frame = tk.Frame(main_frame)
    path_frame.pack(fill="x", pady=(0, 10))

    path_var = tk.StringVar()
    path_entry = tk.Entry(path_frame, textvariable=path_var, font=("Arial", 10))
    path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def browse_file():
        nonlocal selected_path
        filename = filedialog.askopenfilename(parent=root, title=label)
        if filename:
            selected_path = filename
            path_var.set(filename)
            content = read_file_safe(filename)
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", content)

    browse_btn = tk.Button(path_frame, text="Browse", command=browse_file, font=("Arial", 10))
    browse_btn.pack(side="right")

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=(10, 0), fill="x")

    remember_var = tk.BooleanVar(value=bool(remembered_context))
    remember_chk = tk.Checkbutton(button_frame, text="Remember for session", variable=remember_var)
    remember_chk.pack(side="left", padx=(0, 12))

    def clear_remembered():
        nonlocal remembered_context
        set_remembered_context(None)
        remembered_context = None
        remember_var.set(False)
        # Only clear text if it exactly matches previous remembered value (avoid erasing user edits)
        try:
            current = text_widget.get("1.0", "end-1c")
            if current.strip() == (remembered_context or "").strip():
                text_widget.delete("1.0", "end")
        except Exception:
            pass
        clear_btn.config(state="disabled")

    clear_btn = tk.Button(button_frame, text="Clear Remembered", command=clear_remembered,
                          font=("Arial", 9))
    clear_btn.pack(side="left")
    if not remembered_context:
        clear_btn.config(state="disabled")

    def on_ok():
        nonlocal result, selected_path, remember_flag
        result = text_widget.get("1.0", "end-1c")
        if path_var.get():
            selected_path = path_var.get()
        remember_flag = bool(remember_var.get())
        root.destroy()

    def on_cancel():
        nonlocal result
        result = CANCELLED
        root.destroy()

    ok_btn = tk.Button(button_frame, text="OK (Ctrl+Enter)", command=on_ok, font=("Arial", 10), padx=20)
    ok_btn.pack(side="left", padx=(0, 10))

    cancel_btn = tk.Button(button_frame, text="Cancel (Esc)", command=on_cancel, font=("Arial", 10), padx=20)
    cancel_btn.pack(side="left")

    root.bind("<Control-Return>", lambda e: (on_ok(), "break"))
    root.bind("<Control-KP_Enter>", lambda e: (on_ok(), "break"))
    root.bind("<Escape>", lambda e: (on_cancel(), "break"))

    # Prefill with remembered context if present and editor is blank
    if remembered_context and not text_widget.get("1.0", "end-1c").strip():
        text_widget.insert("1.0", remembered_context)

    root.mainloop()
    return result, selected_path, remember_flag


def show_reference_file_content(path: str) -> None:
    """Display the contents of ``path`` in a read-only Tk window with light Markdown rendering."""
    import tkinter as tk
    import re

    raw_text = read_file_safe(path)

    root = tk.Tk()
    root.title(f"Reference File: {Path(path).name}")
    root.geometry("900x650")
    root.resizable(True, True)

    root.lift(); root.focus_force(); root.attributes("-topmost", True); root.after(100, lambda: root.attributes("-topmost", False))

    main_frame = tk.Frame(root, padx=16, pady=12)
    main_frame.pack(fill="both", expand=True)

    # Toolbar
    toolbar = tk.Frame(main_frame)
    toolbar.pack(fill="x", pady=(0, 6))
    info_lbl = tk.Label(
        toolbar,
        text="Formatted preview (basic Markdown). Toggle raw to see original.",
        fg="#555",
    )
    info_lbl.pack(side="left")

    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True)

    text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 10))
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Tag styles
    text_widget.tag_configure("h1", font=("Consolas", 15, "bold"))
    text_widget.tag_configure("h2", font=("Consolas", 13, "bold"))
    text_widget.tag_configure("h3", font=("Consolas", 12, "bold"))
    text_widget.tag_configure("bold", font=("Consolas", 10, "bold"))
    text_widget.tag_configure("codeblock", background="#f5f5f5", font=("Consolas", 10))
    text_widget.tag_configure("inlinecode", background="#eee")
    text_widget.tag_configure("hr", foreground="#666")

    is_markdown = Path(path).suffix.lower() in {".md", ".markdown"} or any(
        l.startswith("#") for l in raw_text.splitlines()[:20]
    )
    show_raw = {"value": False}

    def render(markdown: bool):
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        if not markdown:
            text_widget.insert("1.0", raw_text)
            text_widget.config(state="disabled")
            return
        in_code = False
        for line in raw_text.splitlines():
            if line.strip().startswith("```"):
                if not in_code:
                    in_code = True
                    text_widget.insert("end", "\n")
                else:
                    in_code = False
                continue
            if in_code:
                start = text_widget.index("end-1c")
                text_widget.insert("end", line + "\n")
                text_widget.tag_add("codeblock", start, text_widget.index("end-1c"))
                continue
            # Horizontal rule
            if re.match(r"^---+$", line.strip()):
                start = text_widget.index("end-1c")
                text_widget.insert("end", "\n" + line.strip() + "\n")
                text_widget.tag_add("hr", start, text_widget.index("end-1c"))
                continue
            # Headings
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                hashes, content = m.groups()
                lvl = min(len(hashes), 3)
                start = text_widget.index("end-1c")
                text_widget.insert("end", content + "\n")
                tag = f"h{lvl}"
                text_widget.tag_add(tag, start, text_widget.index("end-1c"))
                continue
            # Bold **text**
            pos_before = text_widget.index("end-1c")
            working = line
            cursor = 0
            bold_pattern = re.compile(r"\*\*(.+?)\*\*")
            while True:
                bm = bold_pattern.search(working, cursor)
                if not bm:
                    text_widget.insert("end", working[cursor:] + "\n")
                    break
                # text before bold
                text_widget.insert("end", working[cursor:bm.start()])
                bold_start = text_widget.index("end-1c")
                text_widget.insert("end", bm.group(1))
                bold_end = text_widget.index("end-1c")
                text_widget.tag_add("bold", bold_start, bold_end)
                cursor = bm.end()
                if cursor >= len(working):
                    text_widget.insert("end", "\n")
                    break
            # Inline code `code`
            # After insertion, scan the just inserted line region for backticks
            line_start_idx = pos_before
            line_end_idx = text_widget.index("end-2c lineend")
            line_text = text_widget.get(line_start_idx, line_end_idx)
            inline_positions = [
                (m.start(), m.end()) for m in re.finditer(r"`([^`]+)`", line_text)
            ]
            # Adjust tags; remove backticks visually by replacing them
            for s, e in reversed(inline_positions):
                # Replace with inner content
                inner = re.match(r"`([^`]+)`", line_text[s:e]).group(1)
                abs_start = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + s}"
                abs_end = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + e}"
                text_widget.delete(abs_start, abs_end)
                text_widget.insert(abs_start, inner)
                # Compute new end after replacement
                new_end_idx = f"{line_start_idx.split('.')[0]}.{int(line_start_idx.split('.')[1]) + s + len(inner)}"
                text_widget.tag_add("inlinecode", abs_start, new_end_idx)
        text_widget.config(state="disabled")

    def toggle_view():
        show_raw["value"] = not show_raw["value"]
        raw_btn.config(text="Raw View" if not show_raw["value"] else "Formatted View")
        render(markdown=is_markdown and not show_raw["value"])

    def copy_all():
        try:
            import prompt_automation.paste as paste

            paste.copy_to_clipboard(raw_text)
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


def collect_variables_gui(template):
    """Collect variables for template placeholders (GUI) with persistence.

    Mirrors CLI variable collection enhancements: persistent simple values, global note labels,
    and friendly hallucinate dropdown.
    """
    placeholders = template.get("placeholders", [])
    if not placeholders:
        return {}

    variables = {}
    template_id = template.get("id", 0)
    globals_map = template.get("global_placeholders", {})

    # Load persisted simple values (non-file) & global notes for labels
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

        # Pre-populate with persisted value if available
        if name not in variables and name in persisted_simple:
            variables[name] = persisted_simple[name]

        if name == "reference_file_content":
            # Backward compatibility: content auto-derived from global reference file
            path = variables.get("reference_file") or get_global_reference_file()
            p = Path(path).expanduser() if path else None
            if p and p.exists():
                show_reference_file_content(str(p))
                variables[name] = read_file_safe(str(p))
            else:
                variables[name] = ""
            continue

        if name == "context":
            # If there is a remembered context and user has not yet supplied one, prefill it
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
                # If user left it blank but a remembered context exists, reuse remembered
                variables[name] = remembered
            continue

        if ptype == "file":
            if name == "reference_file":
                value = collect_global_reference_file_gui(placeholder)
            else:
                value = collect_file_variable_gui(template_id, placeholder, globals_map)
        else:
            default_val = placeholder.get("default") if isinstance(placeholder, dict) else None
            if isinstance(default_val, str):
                CURRENT_DEFAULTS[name] = default_val
            try:
                if name == "hallucinate" and not options:
                    options = [
                        "(omit)",
                        "Absolutely no hallucination (critical)",
                        "Balanced correctness & breadth (normal)",
                        "Some creative inference allowed (high)",
                        "Maximum creative exploration (low)",
                    ]
                value = collect_single_variable(name, label, ptype, options, multiline)
            finally:
                CURRENT_DEFAULTS.pop(name, None)
        if value is CANCELLED:
            return None
        if name == "hallucinate" and isinstance(value, str):
            low = value.lower()
            if "omit" in low or not low.strip():
                value = None
            elif "critical" in low:
                value = "critical"
            elif "normal" in low:
                value = "normal"
            elif "high" in low:
                value = "high"
            elif "low" in low:
                value = "low"
        variables[name] = value

    # Persist simple values (non-file, scalar/list) for future sessions
    try:
        if template_id:
            persist_template_values(template_id, placeholders, variables)
    except Exception:
        pass

    return variables


def collect_single_variable(name, label, ptype, options, multiline):
    """Collect a single variable with appropriate input method."""
    import tkinter as tk
    from tkinter import ttk, filedialog

    root = tk.Tk()
    root.title(f"Input: {label}")
    # Dynamic sizing: larger defaults & adapt height to expected content
    def _initial_geometry():
        # Heuristics: multiline/list get big window; single-line moderate
        if multiline or ptype == "list":
            # Base width/height
            width = 900
            # Estimate height from default length
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

    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = CANCELLED

    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    # Label
    label_widget = tk.Label(main_frame, text=f"{label}:", font=("Arial", 12))
    label_widget.pack(anchor="w", pady=(0, 10))

    # Input widget based on type
    input_widget = None

    # Determine default from options/placeholder global? (Feature A)
    # For GUI collection we expect caller to supply placeholder meta separately; in this
    # function we cannot access the placeholder dict directly, so we look for a
    # convention: an option string starting with 'DEFAULT::' is NOT used. Instead we rely
    # on a hidden attribute attached by caller. Simpler: we allow the caller to set a
    # global dict _CURRENT_PLACEHOLDER_DEFAULT prior to invocation. Fallback: no default.
    default_val = CURRENT_DEFAULTS.get(name)

    if options:
        # Dropdown for options
        input_widget = ttk.Combobox(main_frame, values=options, font=("Arial", 10))
        input_widget.pack(fill="x", pady=(0, 10))
        input_widget.set(options[0] if options else "")
        input_widget.focus_set()

    elif ptype == "file":
        # File input with browse button
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
        # Multi-line text input
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))

        input_widget = tk.Text(text_frame, font=("Arial", 10), wrap="word")
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=input_widget.yview)
        input_widget.config(yscrollcommand=scrollbar.set)

        input_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        input_widget.focus_set()

    else:
        # Single-line text input
        input_widget = tk.Entry(main_frame, font=("Arial", 10))
        input_widget.pack(fill="x", pady=(0, 10))
        input_widget.focus_set()

    # Default hint footer (Feature A) - only if non-empty string default
    hint_frame = None
    if isinstance(default_val, str) and default_val.strip():
        full_default = default_val
        truncated = False
        display_val = full_default
        if len(display_val) > 160 or "\n" in display_val:
            display_val = (display_val.replace("\n", " "))[:160].rstrip() + "…"
            truncated = True
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
                txt = tk.Text(top, wrap="word", font=("Consolas", 10))
                txt.pack(fill="both", expand=True)
                txt.insert("1.0", full_default)
                txt.config(state="disabled")
                btn = tk.Button(top, text="Close", command=top.destroy)
                btn.pack(pady=6)
                top.transient(root); top.grab_set()
            view_btn = tk.Button(hint_frame, text="[view]", command=show_full, bd=0, fg="#555", bg="#f2f2f2", font=("Arial", 9, "underline"))
            view_btn.pack(side="right")

        # Pre-fill input with default (existing behaviour) only if currently blank
        if isinstance(input_widget, tk.Text):
            if not input_widget.get("1.0", "end-1c").strip():
                input_widget.insert("1.0", full_default)
        else:
            if not input_widget.get().strip():
                input_widget.insert(0, full_default)

    # Button frame
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
                    result = [line.strip() for line in value.splitlines() if line.strip()]
                else:
                    result = value
            else:
                result = input_widget.get()
        # Keep raw empty string if user cleared it; fallback applied later
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

    # Keyboard bindings
    def on_enter(event):
        # For multi-line text, Ctrl+Enter submits, Enter adds new line
        is_ctrl = bool(event.state & 0x4)
        if isinstance(input_widget, tk.Text) and not is_ctrl:
            return None  # Allow normal Enter behavior in text widget

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

    # For non-text widgets, regular Enter also submits
    if not isinstance(input_widget, tk.Text):
        root.bind("<Return>", on_enter)
        root.bind("<KP_Enter>", on_enter)

    root.mainloop()
    return result


__all__ = [
    "CANCELLED",
    "collect_file_variable_gui",
    "collect_context_variable_gui",
    "show_reference_file_content",
    "collect_variables_gui",
    "collect_single_variable",
]
