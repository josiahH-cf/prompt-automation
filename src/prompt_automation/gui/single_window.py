"""Single-window GUI workflow implementation.

Provides a persistent root window that is reused across
template selection -> variable collection -> review stages.

Goals:
 - Fixed, larger default geometry (persisted across runs)
 - Text widgets wrap and scroll instead of spawning new windows
 - Avoid creating/destroying root (prevents OS snap resets)

This co-exists with legacy multi-window functions; controller chooses this
path by default. If any fatal error occurs it can fall back to legacy path.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict, Optional

from ..config import HOME_DIR
from ..errorlog import get_logger
from ..renderer import read_file_safe
from .. import paste
from .fonts import get_display_font
from .selector import view as selector_view, service as selector_service
from .collector.persistence import reset_global_reference_file, get_global_reference_file
from .options_menu import configure_options_menu

_log = get_logger(__name__)

SETTINGS_PATH = HOME_DIR / "gui-settings.json"
DEFAULT_GEOMETRY = "1280x860"  # width x height (fixed; user can resize, we'll persist)


def _load_geometry() -> str:
    try:
        if SETTINGS_PATH.exists():
            data = json.loads(SETTINGS_PATH.read_text())
            geom = data.get("geometry")
            if isinstance(geom, str) and "x" in geom:
                return geom
    except Exception:  # pragma: no cover - best effort
        pass
    return DEFAULT_GEOMETRY


def _save_geometry(geometry: str) -> None:
    try:  # pragma: no cover - best effort persistence
        current = {}
        if SETTINGS_PATH.exists():
            try:
                current = json.loads(SETTINGS_PATH.read_text()) or {}
            except Exception:
                current = {}
        current["geometry"] = geometry
        SETTINGS_PATH.write_text(json.dumps(current, indent=2))
    except Exception:
        pass


class SingleWindowApp:
    """Encapsulates the single window lifecycle."""

    def __init__(self) -> None:
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Prompt Automation")
        self.root.geometry(_load_geometry())
        self.root.minsize(960, 640)
        self.root.resizable(True, True)
        # Focus & raise
        self.root.lift(); self.root.focus_force(); self.root.attributes("-topmost", True); self.root.after(120, lambda: self.root.attributes("-topmost", False))
        self.stage_frame: Optional[tk.Frame] = None
        self.template: Optional[dict] = None
        self.variables: Optional[Dict[str, Any]] = None
        self.final_text: Optional[str] = None
        # Provide global reference so that embedded selector logic can reuse root if needed
        selector_view._EMBEDDED_SINGLE_WINDOW_ROOT = self.root  # type: ignore[attr-defined]

        # Save geometry on close
        def _on_close():
            try:
                self.root.update_idletasks()
                _save_geometry(self.root.winfo_geometry())
            finally:
                self.root.destroy()
        self.root.protocol("WM_DELETE_WINDOW", _on_close)

        # Menu bar (Options -> Manage Shortcuts) for numeric key assignment parity
        try:
            accels = configure_options_menu(
                self.root,
                selector_view_module=selector_view,
                selector_service=selector_service,
                include_global_reference=True,
                include_manage_templates=True,
            )
            for seq, fn in accels.items():
                self.root.bind(seq, lambda e, f=fn: (f(), 'break'))
        except Exception as e:  # pragma: no cover
            _log.error("Options menu init failed: %s", e)

    # ----------------------------- utility ---------------------------------
    def _swap_stage(self):
        import tkinter as tk
        if self.stage_frame is not None:
            try:
                self.stage_frame.destroy()
            except Exception:
                pass
        self.stage_frame = tk.Frame(self.root, padx=14, pady=12)
        self.stage_frame.pack(fill="both", expand=True)
        return self.stage_frame

    # ----------------------- Stage 1: Template select ----------------------
    def select_template(self) -> Optional[dict]:
        """Embed existing selector view in single root.

        We wrap core list UI inside our stage frame and intercept completion
        instead of destroying root.
        """
        import tkinter as tk

        frame = self._swap_stage()
        hdr = tk.Label(frame, text="Select a template", font=("Arial", 14, "bold"))
        hdr.pack(anchor="w", pady=(0, 8))

        try:
            tmpl = selector_view.open_template_selector(selector_service, embedded=True, parent=frame)  # type: ignore[arg-type]
        except TypeError:
            _log.warning("Embedded selector not available; falling back.")
            tmpl = selector_view.open_template_selector(selector_service)
        # Multi-select preview stage
        if tmpl and tmpl.get('style') == 'multi' and isinstance(tmpl.get('template'), list):
            import tkinter as tk
            preview_frame = self._swap_stage()
            tk.Label(preview_frame, text=f"Multi-Template Preview ({len(tmpl.get('template'))} lines)", font=("Arial",14,"bold")).pack(pady=(0,6))
            txt_frame = tk.Frame(preview_frame); txt_frame.pack(fill='both', expand=True)
            txt = tk.Text(txt_frame, wrap='word', font=get_display_font(master=self.root))
            vs = tk.Scrollbar(txt_frame, orient='vertical', command=txt.yview)
            txt.configure(yscrollcommand=vs.set)
            txt.pack(side='left', fill='both', expand=True); vs.pack(side='right', fill='y')
            txt.insert('1.0', "\n".join(tmpl.get('template'))); txt.config(state='disabled')
            btns = tk.Frame(preview_frame, pady=6); btns.pack(fill='x')
            def _proceed(): self.template = tmpl; self.collect_variables(tmpl)
            def _back(): self.template=None; self.select_template()
            tk.Button(btns, text='Continue', command=_proceed, padx=16).pack(side='left')
            tk.Button(btns, text='Back', command=_back, padx=16).pack(side='left', padx=(6,0))
            return tmpl
        self.template = tmpl
        return tmpl

    # -------------------- Stage 2: Variable collection ---------------------
    def collect_variables(self, template: dict) -> Optional[Dict[str, Any]]:
        import tkinter as tk
        from .collector.persistence import (
            load_template_value_memory,
            persist_template_values,
            get_remembered_context,
            set_remembered_context,
            get_global_reference_file,
        )
        from .collector.prompts import (
            collect_file_variable_gui,
            collect_reference_file_variable_gui,
            CANCELLED,
        )
        from .collector.overrides import (
            load_overrides,
            get_template_entry,
            set_template_entry,
            save_overrides,
            print_one_time_skip_reminder,
        )

        frame = self._swap_stage()
        placeholders = template.get("placeholders", [])
        if not placeholders:
            self.variables = {}
            return {}
        template_id = template.get("id", 0)
        persisted_simple = load_template_value_memory(template_id) if template_id else {}

        vars_map: Dict[str, Any] = {}
        index = 0
        total = len(placeholders)

        title_var = tk.StringVar()
        title_lbl = tk.Label(
            frame,
            textvariable=title_var,
            font=("Arial", 13, "bold"),
            anchor="center",
            justify="center",
            wraplength=self.root.winfo_width() - 60 if self.root.winfo_width() > 200 else 1100,
        )
        title_lbl.pack(fill="x", pady=(0, 6))

        # Bind once to adjust wraplength & keep centered when window snaps / resizes
        if not hasattr(self, "_title_wrap_bound"):
            def _adjust_title_wrap(event):
                try:
                    usable = max(event.width - 60, 300)
                    title_lbl.configure(wraplength=usable)
                except Exception:
                    pass
            self.root.bind("<Configure>", _adjust_title_wrap, add="+")
            self._title_wrap_bound = True
        progress_var = tk.StringVar()
        tk.Label(frame, textvariable=progress_var, font=("Arial", 10), fg="#555", anchor="w").pack(fill="x", pady=(0, 10))

        input_container = tk.Frame(frame)
        input_container.pack(fill="both", expand=True)

        hint_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=hint_var, font=("Arial", 9), fg="#555", anchor="w", justify="left", wraplength=1100).pack(fill="x", pady=(0, 6))

        btn_row = tk.Frame(frame); btn_row.pack(fill="x")

        def _advance():
            nonlocal index
            index += 1
            if index >= total:
                try:
                    persist_template_values(template_id, placeholders, vars_map)
                except Exception:
                    pass
                self.variables = vars_map
                self.review_output(template, vars_map)
            else:
                _render_placeholder()

        def _cancel():
            self.variables = None
            self.final_text = None
            self.root.destroy()

        def _render_placeholder():
            nonlocal index
            for w in input_container.winfo_children():
                w.destroy()
            if index >= total:
                return
            ph = placeholders[index]
            name = ph["name"]
            label = ph.get("label", name)
            ptype = ph.get("type", "text")
            multiline = ph.get("multiline", False) or ptype == "list"
            options = ph.get("options", [])
            # Add two newlines after template title for clearer separation from field label
            title_var.set(f"{template.get('title','Template')}\n\n{label}")
            progress_var.set(f"{index+1} / {total}")
            default_val = ph.get("default")
            if name in persisted_simple and name not in vars_map:
                vars_map[name] = persisted_simple[name]

            # File placeholders delegate to legacy handlers (which respect skip logic)
            if name == "reference_file" and ptype == "file":
                # Inline viewer/selector instead of popup
                overrides = load_overrides()
                entry = get_template_entry(overrides, template_id, name) or {}
                if entry.get("skip"):
                    print_one_time_skip_reminder(overrides, template_id, name)
                    vars_map[name] = ""; _advance(); return

                stored_path = entry.get("path") if isinstance(entry, dict) else None
                if stored_path and not Path(stored_path).expanduser().exists():
                    stored_path = None

                path_frame = tk.Frame(input_container); path_frame.pack(fill="x", pady=(0,4))
                tk.Label(path_frame, text="Reference File Path:", anchor="w").pack(side="left")
                path_var = tk.StringVar(value=stored_path or "")
                path_entry = tk.Entry(path_frame, textvariable=path_var, font=("Arial",10))
                path_entry.pack(side="left", fill="x", expand=True, padx=(6,6))

                from tkinter import filedialog
                def browse():
                    fname = filedialog.askopenfilename(parent=self.root)
                    if fname:
                        path_var.set(fname); _render_preview()
                tk.Button(path_frame, text="Browse", command=browse).pack(side="left")
                def reset_path():
                    path_var.set(""); _render_preview(clear=True)
                tk.Button(path_frame, text="Reset", command=reset_path).pack(side="left", padx=(4,0))
                def refresh():
                    _render_preview()
                tk.Button(path_frame, text="Refresh", command=refresh).pack(side="left", padx=(4,0))

                # Viewer area
                view_frame = tk.Frame(input_container)
                view_frame.pack(fill="both", expand=True, pady=(4,4))
                txt = tk.Text(view_frame, wrap="word", font=get_display_font(master=self.root))
                vs = tk.Scrollbar(view_frame, orient="vertical", command=txt.yview)
                txt.configure(yscrollcommand=vs.set)
                txt.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")

                # Markdown-ish tagging similar to legacy when placeholder render==markdown
                wants_md = (ph.get("render") == "markdown")
                base_family, base_size = get_display_font(master=self.root)
                try:
                    txt.tag_configure("h1", font=(base_family, base_size+6, "bold"))
                    txt.tag_configure("h2", font=(base_family, base_size+4, "bold"))
                    txt.tag_configure("h3", font=(base_family, base_size+2, "bold"))
                    txt.tag_configure("bold", font=(base_family, base_size, "bold"))
                    txt.tag_configure("codeblock", background="#f5f5f5", font=(base_family, base_size))
                    txt.tag_configure("inlinecode", background="#eee")
                    txt.tag_configure("hr", foreground="#666")
                except Exception:
                    pass

                def _apply_markdown(text_widget, raw: str):
                    lines = raw.splitlines(); cursor = 1; in_code = False; code_start_index=None
                    for ln in lines:
                        line_index = f"{cursor}.0"
                        if ln.strip().startswith("```"):
                            if not in_code:
                                in_code = True; code_start_index = line_index
                            else:
                                try: text_widget.tag_add("codeblock", code_start_index, f"{cursor}.0 lineend")
                                except Exception: pass
                                in_code = False; code_start_index=None
                        elif not in_code:
                            if ln.startswith("### "): text_widget.tag_add("h3", line_index, f"{cursor}.0 lineend")
                            elif ln.startswith("## "): text_widget.tag_add("h2", line_index, f"{cursor}.0 lineend")
                            elif ln.startswith("# "): text_widget.tag_add("h1", line_index, f"{cursor}.0 lineend")
                            elif ln.strip() in {"---","***"}: text_widget.tag_add("hr", line_index, f"{cursor}.0 lineend")
                        cursor += 1
                    import re
                    full = text_widget.get("1.0","end-1c")
                    for m in re.finditer(r"\\*\\*(.+?)\\*\\*", full):
                        text_widget.tag_add("bold", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")
                    for m in re.finditer(r"`([^`]+?)`", full):
                        text_widget.tag_add("inlinecode", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")

                SIZE_LIMIT = 200 * 1024
                def _render_preview(clear: bool=False):
                    txt.config(state="normal")
                    txt.delete("1.0","end")
                    if clear:
                        txt.config(state="disabled"); return
                    path_val = Path(path_var.get()).expanduser()
                    if not path_val.exists():
                        txt.insert("1.0", "(No file selected)"); txt.config(state="disabled"); return
                    try:
                        content = read_file_safe(str(path_val)).replace("\r", "")
                    except Exception:
                        content = "(Error reading file)"
                    if len(content.encode("utf-8")) > SIZE_LIMIT:
                        banner = "*** File truncated (too large) ***\n\n"; content = banner + content[: SIZE_LIMIT // 2]
                    if wants_md:
                        new_lines=[]; in_code=False
                        for ln in content.splitlines():
                            if ln.strip().startswith("```"):
                                in_code = not in_code; new_lines.append(ln); continue
                            if not in_code and ln.startswith("- "): ln = "• " + ln[2:]
                            new_lines.append(ln)
                        content_to_insert = "\n".join(new_lines)
                    else:
                        content_to_insert = content
                    txt.insert("1.0", content_to_insert)
                    if wants_md:
                        try: _apply_markdown(txt, content_to_insert)
                        except Exception: pass
                    txt.config(state="disabled")

                _render_preview()

                def _persist(path: str):
                    set_template_entry(overrides, template_id, name, {"path": path, "skip": False}); save_overrides(overrides)
                def _clear():
                    ov = load_overrides(); tmpl = ov.get("templates", {}).get(str(template_id), {})
                    if name in tmpl: tmpl.pop(name, None); save_overrides(ov)

                def _accept():
                    pv = path_var.get().strip()
                    if pv:
                        _persist(pv); vars_map[name] = pv
                    _advance()
                def _skip_inline():
                    _advance()
                def _reset_inline():
                    reset_path(); _clear()
                def _refresh_inline():
                    _render_preview()

                controls = tk.Frame(input_container); controls.pack(anchor="w", pady=(4,2))
                tk.Button(controls, text="Next", command=_accept, padx=14).pack(side="left")
                tk.Button(controls, text="Skip", command=_skip_inline, padx=10).pack(side="left", padx=(6,0))
                tk.Button(controls, text="Reset", command=_reset_inline, padx=10).pack(side="left", padx=(6,0))
                tk.Button(controls, text="Refresh", command=_refresh_inline, padx=10).pack(side="left", padx=(6,0))
                def _copy_view():
                    try:
                        self.root.clipboard_clear(); self.root.clipboard_append(txt.get('1.0','end-1c'))
                    except Exception: pass
                tk.Button(controls, text="Copy", command=_copy_view, padx=10).pack(side="left", padx=(6,0))

                # Keybindings
                for seq, fn in {
                    "<Control-Return>": _accept,
                    "<Control-s>": _skip_inline,
                    "<Control-r>": _reset_inline,
                    "<Control-R>": _reset_inline,
                    "<Control-u>": _refresh_inline,
                    "<Control-U>": _refresh_inline,
                }.items():
                    self.root.bind(seq, lambda e, f=fn: (f(), "break"))
                path_entry.bind("<Return>", lambda e: (_accept(), "break"))
                path_entry.focus_set(); self.root.after(50, path_entry.focus_set)
                hint_var.set("Reference file inline viewer: Ctrl+Enter=Next, Ctrl+R=Reset, Ctrl+U=Refresh, Ctrl+S=Skip, Esc=Cancel")
                return
            # Unified inline file placeholder handler (reference_file + others)
            if ptype == "file":
                is_reference = (name == "reference_file")
                overrides = load_overrides()
                entry = get_template_entry(overrides, template_id, name) or {}
                if entry.get("skip") and is_reference:
                    print_one_time_skip_reminder(overrides, template_id, name)
                    vars_map[name] = ""; _advance(); return

                stored_path = entry.get("path") if isinstance(entry, dict) else None
                if stored_path and not Path(stored_path).expanduser().exists():
                    stored_path = None

                path_frame = tk.Frame(input_container); path_frame.pack(fill="x", pady=(0,4))
                tk.Label(path_frame, text=("Reference File Path:" if is_reference else f"File: {label}"), anchor="w").pack(side="left")
                path_var = tk.StringVar(value=stored_path or "")
                path_entry = tk.Entry(path_frame, textvariable=path_var, font=("Arial",10))
                path_entry.pack(side="left", fill="x", expand=True, padx=(6,6))
                from tkinter import filedialog
                def browse():
                    fname = filedialog.askopenfilename(parent=self.root)
                    if fname: path_var.set(fname); _render_preview()
                tk.Button(path_frame, text="Browse", command=browse).pack(side="left")
                def reset_path():
                    path_var.set(""); _render_preview(clear=True); _clear()
                tk.Button(path_frame, text="Reset", command=reset_path).pack(side="left", padx=(4,0))
                def refresh(): _render_preview()
                tk.Button(path_frame, text="Refresh", command=refresh).pack(side="left", padx=(4,0))
                skip_future_var = tk.BooleanVar(value=bool(entry.get("skip")))
                if is_reference:
                    tk.Checkbutton(path_frame, text="Skip future", variable=skip_future_var).pack(side="left", padx=(8,0))

                view_frame = tk.Frame(input_container)
                view_frame.pack(fill="both", expand=True, pady=(4,4))
                txt = tk.Text(view_frame, wrap="word", font=get_display_font(master=self.root))
                vs = tk.Scrollbar(view_frame, orient="vertical", command=txt.yview)
                txt.configure(yscrollcommand=vs.set)
                txt.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
                wants_md = (ph.get("render") == "markdown") and is_reference
                base_family, base_size = get_display_font(master=self.root)
                try:
                    for tag, inc, weight in [("h1",6,"bold"),("h2",4,"bold"),("h3",2,"bold")]:
                        txt.tag_configure(tag, font=(base_family, base_size+inc, weight))
                    txt.tag_configure("bold", font=(base_family, base_size, "bold"))
                    txt.tag_configure("codeblock", background="#f5f5f5", font=(base_family, base_size))
                    txt.tag_configure("inlinecode", background="#eee")
                    txt.tag_configure("hr", foreground="#666")
                except Exception: pass
                raw_mode = {"value": False}
                toggle_btn = None
                if wants_md:
                    toggle_btn = tk.Button(path_frame, text="Raw", width=5)
                    toggle_btn.pack(side="left", padx=(6,0))
                def _apply_markdown(text_widget, raw: str):
                    lines = raw.splitlines(); cursor = 1; in_code = False; code_start_index=None
                    for ln in lines:
                        line_index = f"{cursor}.0"
                        if ln.strip().startswith("```"):
                            if not in_code:
                                in_code = True; code_start_index = line_index
                            else:
                                try: text_widget.tag_add("codeblock", code_start_index, f"{cursor}.0 lineend")
                                except Exception: pass
                                in_code = False; code_start_index=None
                        elif not in_code:
                            if ln.startswith("### "): text_widget.tag_add("h3", line_index, f"{cursor}.0 lineend")
                            elif ln.startswith("## "): text_widget.tag_add("h2", line_index, f"{cursor}.0 lineend")
                            elif ln.startswith("# "): text_widget.tag_add("h1", line_index, f"{cursor}.0 lineend")
                            elif ln.strip() in {"---","***"}: text_widget.tag_add("hr", line_index, f"{cursor}.0 lineend")
                        cursor += 1
                    import re
                    full = text_widget.get("1.0","end-1c")
                    for m in re.finditer(r"\\*\\*(.+?)\\*\\*", full): text_widget.tag_add("bold", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")
                    for m in re.finditer(r"`([^`]+?)`", full): text_widget.tag_add("inlinecode", f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")
                SIZE_LIMIT = 200 * 1024
                def _render_preview(clear: bool=False):
                    # retain scroll position
                    try: y = txt.yview()
                    except Exception: y = (0,1)
                    txt.config(state="normal"); txt.delete("1.0","end")
                    if clear:
                        txt.insert("1.0","(No file selected)"); txt.config(state="disabled"); return
                    path_val = Path(path_var.get()).expanduser()
                    if not path_val.exists():
                        txt.insert("1.0","(No file selected)"); txt.config(state="disabled"); return
                    try: content = read_file_safe(str(path_val)).replace("\r", "")
                    except Exception: content = "(Error reading file)"
                    banner = "*** File truncated (too large) ***\n\n"
                    if len(content.encode("utf-8")) > SIZE_LIMIT:
                        content = banner + content[: SIZE_LIMIT // 2]
                    if wants_md and not raw_mode["value"]:
                        new_lines=[]; in_code=False
                        for ln in content.splitlines():
                            if ln.strip().startswith("```"):
                                in_code = not in_code; new_lines.append(ln); continue
                            if not in_code and ln.startswith("- "): ln = "• " + ln[2:]
                            new_lines.append(ln)
                        content_to_insert = "\n".join(new_lines)
                    else:
                        content_to_insert = content
                    txt.insert("1.0", content_to_insert)
                    if wants_md and not raw_mode["value"]:
                        try: _apply_markdown(txt, content_to_insert)
                        except Exception: pass
                    txt.config(state="disabled")
                    # restore scroll
                    try: txt.yview_moveto(y[0])
                    except Exception: pass
                def _toggle_mode():
                    raw_mode["value"] = not raw_mode["value"]
                    if toggle_btn:
                        toggle_btn.configure(text=("MD" if raw_mode["value"] else "Raw"))
                    _render_preview()
                if toggle_btn: toggle_btn.configure(command=_toggle_mode)
                _render_preview()
                def _persist(path: str, skip: bool=False):
                    set_template_entry(overrides, template_id, name, {"path": path, "skip": bool(skip)})
                    save_overrides(overrides)
                def _clear():
                    ov = load_overrides(); tmpl = ov.get("templates", {}).get(str(template_id), {})
                    if name in tmpl: tmpl.pop(name, None); save_overrides(ov)
                def _accept():
                    pv = path_var.get().strip()
                    if pv and Path(pv).expanduser().exists():
                        _persist(pv, skip_future_var.get() if is_reference else False)
                        vars_map[name] = pv
                    elif is_reference and skip_future_var.get():
                        _persist("", True); vars_map[name] = ""
                    _advance()
                def _skip_inline(): _advance()
                def _reset_inline(): reset_path()
                def _refresh_inline(): _render_preview()
                controls = tk.Frame(input_container); controls.pack(anchor="w", pady=(4,2))
                tk.Button(controls, text="Next", command=_accept, padx=14).pack(side="left")
                tk.Button(controls, text="Skip", command=_skip_inline, padx=10).pack(side="left", padx=(6,0))
                tk.Button(controls, text="Reset", command=_reset_inline, padx=10).pack(side="left", padx=(6,0))
                tk.Button(controls, text="Refresh", command=_refresh_inline, padx=10).pack(side="left", padx=(6,0))
                # Keybindings
                for seq, fn in {
                    "<Control-Return>": _accept,
                    "<Control-s>": _skip_inline,
                    "<Control-r>": _reset_inline,
                    "<Control-R>": _reset_inline,
                    "<Control-u>": _refresh_inline,
                    "<Control-U>": _refresh_inline,
                }.items():
                    self.root.bind(seq, lambda e, f=fn: (f(), "break"))
                path_entry.bind("<Return>", lambda e: (_accept(), "break"))
                path_entry.focus_set(); self.root.after(50, path_entry.focus_set)
                hint_var.set(("Reference file inline viewer: Ctrl+Enter=Next, Ctrl+R=Reset, Ctrl+U=Refresh, Ctrl+S=Skip, Esc=Cancel" if is_reference else "File viewer: Ctrl+Enter=Next, Ctrl+R=Reset, Ctrl+U=Refresh, Ctrl+S=Skip, Esc=Cancel"))
                return

            if name == "reference_file_content":
                path = vars_map.get("reference_file") or get_global_reference_file()
                p = Path(path).expanduser() if path else None
                if p and p.exists():
                    try:
                        vars_map[name] = read_file_safe(str(p))
                    except Exception:
                        vars_map[name] = ""
                else:
                    vars_map[name] = ""
                _advance(); return

            if name == "context":
                remembered = get_remembered_context()
                from ..gui.fonts import get_display_font as _gdf  # type: ignore
                txt_frame = tk.Frame(input_container); txt_frame.pack(fill="both", expand=True)
                txt = tk.Text(txt_frame, wrap="word", font=_gdf(master=self.root))
                vs = tk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
                txt.configure(yscrollcommand=vs.set)
                txt.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
                if remembered and not vars_map.get(name):
                    txt.insert("1.0", remembered)
                elif default_val:
                    txt.insert("1.0", default_val)
                hint_var.set("Multiline context: Enter=new line; Ctrl+Enter=Save; Esc=Cancel")
                def _save_ctx():
                    vars_map[name] = txt.get("1.0","end-1c")
                    if vars_map[name].strip():
                        try: set_remembered_context(vars_map[name])
                        except Exception: pass
                    _advance()
                tk.Button(input_container, text="Save Context", command=_save_ctx, padx=18).pack(anchor="w", pady=6)
                txt.bind("<Control-Return>", lambda e: (_save_ctx(), "break"))
                txt.focus_set(); return

            # Generic inputs (with default hint panel)
            widget = None
            if options:
                from tkinter import ttk
                widget = ttk.Combobox(input_container, values=options, font=("Arial", 10))
                widget.pack(fill="x", pady=(0,8))
                widget.set(vars_map.get(name) or (options[0] if options else ""))
                hint_var.set("Select option; Enter=Next; Ctrl+S=Skip; Esc=Cancel")
                # Focus combo box so user can immediately type
                try: widget.focus_set()
                except Exception: pass
            elif multiline or ptype == "list":
                txt_frame = tk.Frame(input_container); txt_frame.pack(fill="both", expand=True)
                widget = tk.Text(txt_frame, wrap="word", font=get_display_font(master=self.root))
                vs = tk.Scrollbar(txt_frame, orient="vertical", command=widget.yview)
                widget.configure(yscrollcommand=vs.set)
                widget.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
                if vars_map.get(name):
                    widget.insert("1.0", vars_map[name] if isinstance(vars_map[name], str) else "\n".join(vars_map[name]))
                elif default_val:
                    widget.insert("1.0", default_val)
                hint_var.set("Multiline: Enter=new line; Ctrl+Enter=Next; Ctrl+S=Skip; Esc=Cancel")
                try: widget.focus_set()
                except Exception: pass
            else:
                entry = tk.Entry(input_container, font=("Arial", 10))
                entry.pack(fill="x", pady=(0,8))
                if vars_map.get(name): entry.insert(0, vars_map[name])
                elif default_val: entry.insert(0, default_val)
                widget = entry
                hint_var.set("Enter=Next; Ctrl+S=Skip; Esc=Cancel")
                try: widget.focus_set()
                except Exception: pass

            # Default value hint panel if explicit default provided and not already visible for multiline
            if isinstance(default_val, str) and default_val.strip():
                full_default = default_val
                truncated = False
                display_val = full_default.replace("\n", " ")
                if len(display_val) > 160:
                    display_val = display_val[:160].rstrip() + "…"; truncated = True
                hint_box = tk.Frame(input_container, bg="#f2f2f2", padx=6, pady=4, highlightthickness=1, highlightbackground="#ddd")
                hint_box.pack(fill="x", pady=(0,8))
                lbl = tk.Label(hint_box, text=f"Default: {display_val}", bg="#f2f2f2", fg="#333", anchor="w", justify="left", font=("Arial",9), wraplength=640)
                lbl.pack(side="left", fill="x", expand=True)
                if truncated:
                    def _show_full():
                        top = tk.Toplevel(self.root); top.title("Full Default Value"); top.geometry("600x400")
                        txtw = tk.Text(top, wrap="word", font=get_display_font(master=top))
                        txtw.pack(fill="both", expand=True); txtw.insert("1.0", full_default); txtw.config(state="disabled")
                        btn = tk.Button(top, text="Close", command=top.destroy); btn.pack(pady=6)
                        top.bind("<Escape>", lambda e: (top.destroy(), "break"))
                    view_btn = tk.Button(hint_box, text="[view]", bd=0, fg="#555", bg="#f2f2f2", command=_show_full, font=("Arial",9,"underline"))
                    view_btn.pack(side="right")

            def _save_current():
                ph_local = placeholders[index]
                nm = ph_local["name"]
                ptype_local = ph_local.get("type","text")
                if options:
                    val = widget.get()  # type: ignore
                elif isinstance(widget, tk.Text):
                    raw = widget.get("1.0","end-1c")
                    if ptype_local == "list":
                        val = [l.strip() for l in raw.splitlines() if l.strip()]
                    else:
                        val = raw
                else:
                    val = widget.get()  # type: ignore
                vars_map[nm] = val
                _advance()

            def _skip():
                _advance()

            btns_inner = tk.Frame(input_container); btns_inner.pack(anchor="w", pady=4)
            tk.Button(btns_inner, text="Next", command=_save_current, padx=16).pack(side="left")
            tk.Button(btns_inner, text="Skip", command=_skip, padx=12).pack(side="left", padx=(6,0))

            if isinstance(widget, tk.Text):
                widget.bind("<Control-Return>", lambda e: (_save_current(), "break"))
                widget.bind("<Control-s>", lambda e: (_skip(), "break"))
            else:
                widget.bind("<Return>", lambda e: (_save_current(), "break"))
                widget.bind("<Control-s>", lambda e: (_skip(), "break"))

            # Reinforce focus after idle so it isn't stolen by buttons
            if widget is not None:
                try:
                    self.root.after(50, lambda w=widget: w.focus_set())
                except Exception:
                    pass

        tk.Button(btn_row, text="Cancel (Esc)", command=_cancel, padx=14).pack(side="left")
        def _change_template():
            # Restart at template selection without destroying root
            self.template = None; self.variables = None; self.final_text = None
            new = self.select_template()
            if new:
                self.collect_variables(new)
        tk.Button(btn_row, text="Change Template", command=_change_template, padx=14).pack(side="left", padx=(8,0))
        self.root.bind("<Escape>", lambda e: (_cancel(), "break"))

        _render_placeholder()
        return vars_map

    # ----------------------- Stage 3: Review Output ------------------------
    def review_output(self, template: dict, variables: Dict[str, Any]):  # type: ignore[override]
        import tkinter as tk
        from ..menus import render_template
        from .. import paste

        frame = self._swap_stage()
        rendered_text, var_map = render_template(template, variables, return_vars=True)
        self.variables = var_map

        tk.Label(frame, text="Review Output", font=("Arial", 14, "bold"), anchor="center", justify="center").pack(fill="x", pady=(0, 8))
        instr = tk.Label(frame, text="Edit below. Ctrl+Enter = Finish & Paste, Ctrl+Shift+C = Copy (stay), Esc = Cancel", anchor="center", justify="center", fg="#444", wraplength=1200)
        instr.pack(fill="x", pady=(0, 6))

        text_frame = tk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        text_widget = tk.Text(text_frame, wrap="word", font=get_display_font(master=self.root))
        vs = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=vs.set)
        text_widget.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        text_widget.insert("1.0", rendered_text)
        text_widget.focus_set()

        status_var = tk.StringVar(value="")
        status = tk.Label(frame, textvariable=status_var, font=("Arial", 9), fg="#2d6a2d")
        status.pack(fill="x", pady=(4, 4))

        btns = tk.Frame(frame)
        btns.pack(fill="x")

        def do_copy():
            txt = text_widget.get("1.0", "end-1c")
            try:
                paste.copy_to_clipboard(txt)
                status_var.set("Copied ✔ (Ctrl+Enter to finish & paste)")
                self.root.after(3500, lambda: status_var.set(""))
            except Exception:
                status_var.set("Copy failed – see logs")

        def do_finish():
            self.final_text = text_widget.get("1.0", "end-1c")
            try:
                paste.paste_text(self.final_text)
            except Exception:
                try:
                    paste.copy_to_clipboard(self.final_text)
                except Exception:
                    pass
            try:
                self.root.update_idletasks(); _save_geometry(self.root.winfo_geometry())
            except Exception:
                pass
            self.root.destroy()

        def do_cancel():
            self.final_text = None
            self.root.destroy()

        tk.Button(btns, text="Copy (Ctrl+Shift+C)", command=do_copy, padx=18).pack(side="left", padx=(0, 8))
        def copy_paths():
            paths = [f"{k}={v}" for k,v in var_map.items() if k.endswith('_path') and v]
            if not paths: return
            data = "\n".join(paths)
            try:
                paste.copy_to_clipboard(data)
                status_var.set("Paths copied")
                self.root.after(2500, lambda: status_var.set(""))
            except Exception:
                status_var.set("Copy paths failed")
        if any(k.endswith('_path') for k in var_map):
            tk.Button(btns, text="Copy Paths", command=copy_paths, padx=14).pack(side="left", padx=(0,8))
        append_targets = [v for k,v in var_map.items() if (k == 'append_file' or k.endswith('_append_file')) and v]
        if append_targets:
            def _preview_appends():
                import tkinter as tk
                from ..renderer import read_file_safe
                win = tk.Toplevel(self.root); win.title('Append Targets'); win.geometry('820x520')
                note = tk.Label(win, text='Existing file content (read-only). Output will be appended when finishing.', fg='#444')
                note.pack(anchor='w', padx=8, pady=(6,4))
                container = tk.Frame(win); container.pack(fill='both', expand=True)
                list_frame = tk.Frame(container, padx=6, pady=4); list_frame.pack(side='left', fill='y')
                lb = tk.Listbox(list_frame, height=8)
                for p in append_targets: lb.insert('end', p)
                lb.pack(side='left', fill='y')
                txt_frame = tk.Frame(container); txt_frame.pack(side='left', fill='both', expand=True)
                txt_prev = tk.Text(txt_frame, wrap='word', font=get_display_font(master=win))
                sb_prev = tk.Scrollbar(txt_frame, orient='vertical', command=txt_prev.yview)
                txt_prev.configure(yscrollcommand=sb_prev.set)
                txt_prev.pack(side='left', fill='both', expand=True); sb_prev.pack(side='right', fill='y')
                SIZE_LIMIT=100*1024
                def _load(idx):
                    pth = lb.get(idx)
                    txt_prev.config(state='normal'); txt_prev.delete('1.0','end')
                    from pathlib import Path as _P
                    path_obj = _P(pth).expanduser()
                    if not path_obj.exists(): txt_prev.insert('1.0','(File not found)'); txt_prev.config(state='disabled'); return
                    try: content = read_file_safe(str(path_obj))
                    except Exception: content='(Read error)'
                    if len(content.encode('utf-8'))>SIZE_LIMIT:
                        content = '*** Truncated preview ***\n\n' + content[:SIZE_LIMIT//2]
                    txt_prev.insert('1.0', content); txt_prev.config(state='disabled')
                def _on_sel(event=None):
                    sel = lb.curselection();
                    if sel: _load(sel[0])
                lb.bind('<<ListboxSelect>>', _on_sel)
                if append_targets: lb.selection_set(0); _load(0)
                win.bind('<Escape>', lambda e: (win.destroy(),'break'))
            tk.Button(btns, text='Preview Append Targets', command=_preview_appends, padx=14).pack(side='left', padx=(0,8))
        tk.Button(btns, text="Finish & Paste (Ctrl+Enter)", command=do_finish, padx=18).pack(side="left", padx=(0, 8))
        def _change_template_review():
            # Capture geometry then restart selection
            self.final_text = None
            self.template = None
            self.variables = None
            self.select_template()
            if self.template:
                self.collect_variables(self.template)
            else:
                self.root.destroy()
        tk.Button(btns, text="Change Template", command=_change_template_review, padx=18).pack(side="left", padx=(0,8))
        tk.Button(btns, text="Cancel (Esc)", command=do_cancel, padx=18).pack(side="left")

        # Clear previous stage bindings that may hijack Ctrl+Enter / Esc
        for seq in ["<Control-Return>", "<Control-KP_Enter>", "<Control-Shift-c>", "<Escape>"]:
            try:
                self.root.unbind(seq)
            except Exception:
                pass
        self.root.bind("<Control-Return>", lambda e: (do_finish(), "break"))
        self.root.bind("<Control-KP_Enter>", lambda e: (do_finish(), "break"))
        self.root.bind("<Control-Shift-c>", lambda e: (do_copy(), "break"))
        self.root.bind("<Escape>", lambda e: (do_cancel(), "break"))

    def run(self) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        try:
            tmpl = self.select_template()
            if not tmpl:
                self.root.destroy(); return None, None
            self.collect_variables(tmpl)
            self.root.mainloop()  # blocks until review finishes
            return self.final_text, self.variables
        finally:
            try:
                if self.root.winfo_exists():
                    _save_geometry(self.root.winfo_geometry())
            except Exception:
                pass


__all__ = ["SingleWindowApp"]
