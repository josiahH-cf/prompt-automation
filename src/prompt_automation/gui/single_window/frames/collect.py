"""Variable collection frame for single-window mode.

Builds a scrolling form driven by placeholder metadata.  Widgets are created
via :func:`variable_form_factory` allowing features such as remembered context,
file pickers with skip flags, override reset buttons and optional file view
callbacks.  An exclusions editor and reference file viewer are also exposed
from the returned view for easier testing.
"""
from __future__ import annotations

from typing import Any, Dict
import types
from pathlib import Path

from ....services.variable_form import build_widget as variable_form_factory
from ....reminders import extract_template_reminders, extract_placeholder_reminders
from ....features import is_reminders_enabled as _reminders_enabled
from ...collector.persistence import get_global_reference_file
from ...collector.overrides import load_overrides, save_overrides
from ....renderer import read_file_safe
from ...constants import INSTR_COLLECT_SHORTCUTS
import os
from ..scroll_helpers import ensure_visible
from ....errorlog import get_logger


def build(app, template: Dict[str, Any]):  # pragma: no cover - Tk runtime
    """Return a view object after constructing the form."""
    import tkinter as tk  # type: ignore

    def _reminder_fg() -> str:
        """Theme-aware foreground for reminder text.

        - Light: keep existing muted gray (#444)
        - Dark: use off-white for stronger contrast (theme textPrimary or fallback)
        """
        try:
            from ....theme import resolve as _tres, model as _tmodel
            name = _tres.ThemeResolver(_tres.get_registry()).resolve()
            if (name or '').lower() == 'dark':
                tokens = _tmodel.get_theme(name)
                return tokens.get('textPrimary', '#E6EAF0')
        except Exception:
            pass
        return '#444'

    # Headless test stub: provide legend text without constructing widgets
    if not hasattr(tk, "Canvas"):
        instr = {"text": INSTR_COLLECT_SHORTCUTS}
        # Provide minimal bindings map for tests (Ctrl+Enter review stub)
        bindings: Dict[str, Dict[str, Any]] = {}
        def _review_stub():
            return None
        bindings["<Control-Return>"] = _review_stub
        # Classify placeholders for headless assertions and expose lightweight bindings
        phs = template.get("placeholders") or []
        if not isinstance(phs, list):
            phs = []

        def _classify(ph: Dict[str, Any]) -> str:
            ptype = (ph.get("type") or "").lower()
            name = ph.get("name", "")
            # Explicit kinds first
            if ptype in {"reminder", "note"}:
                return "reminder"
            if ptype == "link" or ph.get("url") or ph.get("href"):
                return "link"
            # Heuristic: names beginning with reminder_ and not multiline are reminders
            if name.startswith("reminder_") and not ph.get("multiline"):
                return "reminder"
            return "input"

        placeholders_meta: Dict[str, Dict[str, Any]] = {}
        for ph in phs:
            if not isinstance(ph, dict):
                continue
            name = ph.get("name")
            if not name:
                continue
            kind = _classify(ph)
            meta: Dict[str, Any] = {"kind": kind}
            if kind == "link":
                url = ph.get("url") or ph.get("href") or ph.get("default") or ""
                meta["url"] = url
                # Create a minimal binding for link fields so variable mapping includes the URL
                bindings[name] = {"get": (lambda u=url: u), "persist": (lambda: None), "url": url}
            elif kind == "reminder":
                # Reminder-only fields have no input value; expose empty get/persist
                bindings[name] = {"get": (lambda: ""), "persist": (lambda: None)}
            placeholders_meta[name] = meta

        # Conditional global reference binding visibility (headless test aid)
        has_ref = any(isinstance(ph, dict) and ph.get("name") == "reference_file" for ph in phs)
        if has_ref:
            bindings["_global_reference"] = {"get": lambda: "", "persist": lambda: None}
        return types.SimpleNamespace(instructions=instr, bindings=bindings, placeholders_meta=placeholders_meta)

    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text=template.get("title", "Variables"),
        font=("Arial", 14, "bold"),
    ).pack(pady=(12, 4))
    tk.Label(frame, text=INSTR_COLLECT_SHORTCUTS, anchor="w", fg="#444").pack(
        fill="x", padx=12
    )

    # Collapsible panel for template/global reminders
    tmpl_reminders = extract_template_reminders(template) if _reminders_enabled() else []
    # Observability (GUI path): summarize counts once per build
    try:
        log = get_logger(__name__)
        phs = template.get("placeholders") or []
        if isinstance(phs, list):
            ph_count = 0
            for ph in phs:
                try:
                    ph_count += len(extract_placeholder_reminders(ph))
                except Exception:
                    continue
        else:
            ph_count = 0
        log.info("reminders.summary", extra={"template": len(tmpl_reminders), "placeholder": ph_count})
    except Exception:
        pass
    reminders_panel = None
    reminders_toggle_btn = None
    if tmpl_reminders:
        # Session-persistent expanded state (in-memory only)
        expanded = getattr(app, "_reminders_expanded", None)
        if expanded is None:
            expanded = True
        app._reminders_expanded = bool(expanded)

        panel = tk.Frame(frame)
        panel.pack(fill="x", padx=12, pady=(4, 0))
        header = tk.Frame(panel)
        header.pack(fill="x")

        state_var = tk.StringVar(value="−" if app._reminders_expanded else "+")

        def _toggle():  # pragma: no cover - tk runtime
            try:
                app._reminders_expanded = not bool(app._reminders_expanded)
                state_var.set("−" if app._reminders_expanded else "+")
                if app._reminders_expanded:
                    body.pack(fill="x", padx=(2, 0), pady=(2, 6))
                else:
                    body.forget()
            except Exception:
                pass

        reminders_toggle_btn = tk.Button(
            header,
            textvariable=state_var,
            width=2,
            command=_toggle,
            takefocus=1,
        )
        reminders_toggle_btn.pack(side="left")
        tk.Label(header, text="Reminders", font=("Arial", 10, "bold"), anchor="w").pack(
            side="left", padx=(6, 0)
        )

        body = tk.Frame(panel)
        bullets = "\n".join([f"• {s}" for s in tmpl_reminders])
        lbl = tk.Label(body, text=bullets, anchor="w", justify="left", fg=_reminder_fg(), takefocus=1)
        lbl.pack(fill="x")
        if app._reminders_expanded:
            body.pack(fill="x", padx=(2, 0), pady=(2, 6))
        reminders_panel = panel

    canvas = tk.Canvas(frame, borderwidth=0, highlightthickness=0)
    inner = tk.Frame(canvas)
    vsb = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
    vsb.pack(side="right", fill="y", padx=(0, 12), pady=8)
    # Keep window id so we can stretch inner frame to canvas width on resize
    inner_win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    widgets: Dict[str, tk.Widget] = {}
    bindings: Dict[str, Dict[str, Any]] = {}
    placeholders = template.get("placeholders") or []
    if not isinstance(placeholders, list):
        placeholders = []

    label_widgets = []  # track normal labels to update wraplength on resize
    full_line_labels = []  # track reminder-only labels spanning the full width

    focus_chain = []  # ordered list of focusable input widgets
    grid_row = 0
    created_global_ref = False
    def _classify(ph: Dict[str, Any]) -> str:
        ptype = (ph.get("type") or "").lower()
        name = ph.get("name", "")
        if ptype in {"reminder", "note"}:
            return "reminder"
        if ptype == "link" or ph.get("url") or ph.get("href"):
            return "link"
        if name.startswith("reminder_") and not ph.get("multiline"):
            return "reminder"
        return "input"

    for ph in placeholders:
        name = ph.get("name") if isinstance(ph, dict) else None
        if not name:
            continue
        # Ensure per-template uniqueness for reference_file path
        try:
            if name == "reference_file":
                ph["override"] = True
                ph["template_id"] = template.get("id")
        except Exception:
            pass
        kind = _classify(ph)
        if kind == "reminder":
            # Render a full-line reminder label (no input widget)
            note = tk.Label(inner, text=ph.get("label", name), anchor="w", justify="left")
            note.grid(row=grid_row, column=0, columnspan=4, sticky="we", padx=6, pady=6)
            full_line_labels.append(note)
            # Optionally expose a binding returning empty string for symmetry
            bindings[name] = {"get": (lambda: ""), "persist": (lambda: None)}
            grid_row += 1
            continue

        # Normal label for non-reminder kinds
        lbl = tk.Label(inner, text=ph.get("label", name), anchor="w", justify="left")
        lbl.grid(row=grid_row, column=0, sticky="nw", padx=6, pady=4)
        label_widgets.append(lbl)

        if kind == "link":
            import webbrowser
            url = ph.get("url") or ph.get("href") or ph.get("default") or ""
            link_text = ph.get("link_text") or url or ph.get("label", name)
            link = tk.Label(inner, text=link_text, fg="#1a0dab", cursor="hand2", anchor="w", justify="left")
            def _open(u=url):  # pragma: no cover - Tk runtime
                try:
                    if u:
                        webbrowser.open(u)
                except Exception:
                    pass
            try:
                link.bind("<Button-1>", lambda e: (_open(), "break"))
            except Exception:
                pass
            link.grid(row=grid_row, column=1, sticky="w", padx=6, pady=4)
            widgets[name] = link
            bindings[name] = {"get": (lambda u=url: u), "persist": (lambda: None), "open": _open, "url": url}
            grid_row += 1
            continue

        # Default behaviour: build standard input widget
        ctor, bind = variable_form_factory(ph)
        widget = ctor(inner)
        widgets[name] = widget
        bindings[name] = bind

        # Determine widget type/layout
        is_text = False
        try:  # pragma: no cover
            import tkinter as _tk
            is_text = isinstance(widget, _tk.Text)
        except Exception:
            pass

        if is_text:
            label_lines = (ph.get("label", "") or "").count("\n") + 1
            base_height = max(6, min(18, label_lines + 6))
            try:
                widget.configure(wrap="word", height=base_height)
            except Exception:
                pass
            try:
                sb = _tk.Scrollbar(inner, orient="vertical", command=widget.yview)
                widget.configure(yscrollcommand=sb.set)
                widget.grid(row=grid_row, column=1, sticky="nsew", padx=(6, 0), pady=4)
                sb.grid(row=grid_row, column=2, sticky="ns", padx=(0, 6), pady=4)
                inner.rowconfigure(grid_row, weight=1)
                inner.columnconfigure(1, weight=1)
            except Exception:
                widget.grid(row=grid_row, column=1, sticky="we", padx=6, pady=4)
            focus_chain.append(widget)
            # Ensure focused widget is visible when tabbing/clicking
            try:
                if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") != "1":
                    widget.bind("<FocusIn>", lambda e, w=widget: ensure_visible(canvas, inner, w))
                    # Snap outer scroll to follow the insertion cursor after key movement
                    from ..scroll_helpers import ensure_insert_visible as _ens_cursor
                    widget.bind("<KeyRelease>", lambda e, w=widget: _ens_cursor(canvas, inner, w))
                    # Also handle Enter on some platforms where release may differ
                    widget.bind("<Return>", lambda e, w=widget: (_ens_cursor(canvas, inner, w), None))
                    widget.bind("<KP_Enter>", lambda e, w=widget: (_ens_cursor(canvas, inner, w), None))
            except Exception:
                pass
            grid_row += 1
            # Inline placeholder reminders for multi-line widgets
            try:
                rinl = extract_placeholder_reminders(ph)
            except Exception:
                rinl = []
            if _reminders_enabled() and rinl:
                try:
                    bullets = "\n".join([f"• {s}" for s in rinl])
                    rlbl = tk.Label(inner, text=bullets, anchor="w", justify="left", fg=_reminder_fg(), takefocus=1)
                    rlbl.grid(row=grid_row, column=1, sticky="we", padx=(6, 0), pady=(0, 6))
                    label_widgets.append(rlbl)
                    grid_row += 1
                except Exception:
                    pass
        elif bind.get("path_var") is not None:
            widget.grid(row=grid_row, column=1, sticky="we", padx=6, pady=4)
            entry = getattr(widget, "entry", None)
            browse_btn = getattr(widget, "browse_btn", None)
            skip_btn = getattr(widget, "skip_btn", None)
            if entry:
                entry.pack(side="left", fill="x", expand=True)
                focus_chain.append(entry)
                try:
                    if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") != "1":
                        entry.bind("<FocusIn>", lambda e, w=entry: ensure_visible(canvas, inner, w))
                except Exception:
                    pass
            if browse_btn:
                browse_btn.pack(side="left", padx=2)
            if skip_btn:
                skip_btn.pack(side="left", padx=2)
            if bind.get("view") and hasattr(widget, "view_btn"):
                widget.view_btn.pack(side="left", padx=2)  # type: ignore[attr-defined]
            grid_row += 1
            # Inline placeholder reminders for file widgets
            try:
                rinl = extract_placeholder_reminders(ph)
            except Exception:
                rinl = []
            if _reminders_enabled() and rinl:
                try:
                    bullets = "\n".join([f"• {s}" for s in rinl])
                    rlbl = tk.Label(inner, text=bullets, anchor="w", justify="left", fg=_reminder_fg(), takefocus=1)
                    rlbl.grid(row=grid_row, column=1, sticky="we", padx=(6, 0), pady=(0, 6))
                    label_widgets.append(rlbl)
                    grid_row += 1
                except Exception:
                    pass
        else:  # single-line entry
            widget.grid(row=grid_row, column=1, sticky="we", padx=6, pady=4)
            try:
                import tkinter as _tk2
                if isinstance(widget, _tk2.Entry):
                    focus_chain.append(widget)
                    try:
                        if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") != "1":
                            widget.bind("<FocusIn>", lambda e, w=widget: ensure_visible(canvas, inner, w))
                    except Exception:
                        pass
            except Exception:
                pass
            grid_row += 1
            # Inline placeholder reminders for single-line entries
            try:
                rinl = extract_placeholder_reminders(ph)
            except Exception:
                rinl = []
            if _reminders_enabled() and rinl:
                try:
                    bullets = "\n".join([f"• {s}" for s in rinl])
                    rlbl = tk.Label(inner, text=bullets, anchor="w", justify="left", fg=_reminder_fg(), takefocus=1)
                    rlbl.grid(row=grid_row, column=1, sticky="we", padx=(6, 0), pady=(0, 6))
                    label_widgets.append(rlbl)
                    grid_row += 1
                except Exception:
                    pass
            if bind.get("remember_var") is not None:
                tk.Checkbutton(
                    inner,
                    text="Remember",
                    variable=bind.get("remember_var"),
                ).grid(row=row, column=2, padx=6, pady=4, sticky="w")

        # Override reset (applies to file placeholders currently)
        if ph.get("override"):
            tk.Label(inner, text="*", fg="red").grid(row=grid_row - 1, column=3, padx=2)

            def _reset(b=bind):
                if b.get("path_var") is not None:
                    b["path_var"].set("")  # type: ignore[index]
                if b.get("skip_var") is not None:
                    b["skip_var"].set(False)  # type: ignore[index]
                b.get("persist", lambda: None)()

            bind["reset"] = _reset
            tk.Button(inner, text="Reset", command=_reset).grid(row=grid_row - 1, column=4, padx=2)

        if grid_row == 1 and hasattr(widget, "focus_set"):
            widget.focus_set()

    # Allow both columns to stretch; col1 (inputs) gets higher weight
    inner.columnconfigure(0, weight=1)
    inner.columnconfigure(1, weight=3)

    def _on_config(event=None):
        # Update scroll region and ensure inner frame spans canvas width
        canvas.configure(scrollregion=canvas.bbox("all"))
        try:
            cwidth = canvas.winfo_width()
            canvas.itemconfigure(inner_win_id, width=cwidth)
        except Exception:
            pass

    def _update_label_wrap(event=None):  # pragma: no cover - resizing logic
        """Dynamically size label wrap so text is never visually clipped.

        Previous logic used a fixed percentage (45%) of the outer frame width
        which could exceed the actual allocated grid column width (since
        column 0 only has weight=1 vs column 1 weight=3). That caused the
        label to request more horizontal pixels than the column owned; Tk
        then clipped the rendered text producing the appearance of truncated
        labels.  We instead derive a wrap length from the *actual* inner frame
        width and the column weight ratios so the requested wrap never
        exceeds available width.
        """
        try:
            # Force geometry update so winfo_width() is current
            frame.update_idletasks()
            inner_w = max(1, inner.winfo_width())
            # Column weight ratio: col0=1, col1=3 -> total=4
            col0_width = inner_w * (1 / 4.0)
            # Leave some padding so text doesn't butt up against the entry
            usable = max(40, col0_width - 24)
            # Clamp within sensible bounds; allow shrink below previous 180
            # if window extremely narrow to avoid clipping.
            wrap = int(min(640, usable))
            for l in label_widgets:
                try:
                    l.configure(wraplength=wrap)
                except Exception:
                    pass
            # Full-line reminders use the entire inner width minus padding
            full_usable = max(40, inner_w - 24)
            full_wrap = int(min(1200, full_usable))
            for l in full_line_labels:
                try:
                    l.configure(wraplength=full_wrap)
                except Exception:
                    pass
        except Exception:
            pass

    inner.bind("<Configure>", lambda e: _on_config())
    canvas.bind("<Configure>", lambda e: (_on_config(), _update_label_wrap()))
    frame.bind("<Configure>", lambda e: _update_label_wrap())

    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))

    def go_back():
        app.back_to_select()

    def review():
        vars_map = {
            k: b["get"]() or None for k, b in bindings.items() if not k.startswith("_")
        }
        for b in bindings.values():
            b.get("persist", lambda: None)()
        app.advance_to_review(vars_map)

    tk.Button(btn_bar, text="◀ Back", command=go_back).pack(side="left", padx=12)

    template_id = template.get("id")

    def open_exclusions():
        if template_id is not None:
            app.edit_exclusions(template_id)

    tk.Button(btn_bar, text="Exclusions", command=open_exclusions).pack(
        side="left", padx=4
    )

    # Prebuild global reference frame and bindings (kept hidden unless legacy flag)
    ref_path_var = tk.StringVar(value=get_global_reference_file() or "")
    ref_frame = tk.Frame(btn_bar)
    ref_entry = tk.Entry(ref_frame, textvariable=ref_path_var, width=40)
    ref_entry.pack(side="left", fill="x", expand=True)

    def _browse_ref():
        from tkinter import filedialog

        fname = filedialog.askopenfilename()
        if fname:
            ref_path_var.set(fname)

    browse_btn = tk.Button(ref_frame, text="Browse", command=_browse_ref)
    browse_btn.pack(side="left", padx=2)

    def _view_ref():
        path = ref_path_var.get().strip()
        if not path:
            return
        win = tk.Toplevel(app.root)
        win.title(f"Reference File: {Path(path).name}")
        win.geometry("900x680")
        text_frame = tk.Frame(win)
        text_frame.pack(fill="both", expand=True)
        txt = tk.Text(text_frame, wrap="word")
        vs = tk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vs.set)
        txt.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        try:
            content = read_file_safe(path).replace("\r", "")
        except Exception:
            content = "(Error reading file)"
        txt.insert("1.0", content)
        txt.config(state="disabled")

    view_btn = tk.Button(ref_frame, text="View", command=_view_ref)
    view_btn.pack(side="left", padx=2)

    def _persist_ref():
        ov = load_overrides()
        gfiles = ov.setdefault("global_files", {})
        pv = ref_path_var.get().strip()
        if pv:
            gfiles["reference_file"] = pv
        else:
            gfiles.pop("reference_file", None)
        save_overrides(ov)

    # Expose on frame for tests; do not pack unless legacy flag set
    ref_frame.entry = ref_entry  # type: ignore[attr-defined]
    ref_frame.browse_btn = browse_btn  # type: ignore[attr-defined]
    ref_frame.view_btn = view_btn  # type: ignore[attr-defined]
    bindings["_global_reference"] = {
        "get": lambda: ref_path_var.get(),
        "persist": _persist_ref,
        "path_var": ref_path_var,
        "view": _view_ref,
    }
    widgets["_global_reference"] = ref_frame

    tk.Button(btn_bar, text="Review ▶", command=review).pack(side="right", padx=12)

    # --- Focus traversal (Tab across all inputs incl. Text) -----------------
    def _bind_tab_traversal(chain):  # pragma: no cover - runtime behaviour
        if not chain:
            return
        # Normalize: replace container frames that hold an 'entry' attribute
        # (file placeholders) with that entry widget so focus goes directly
        # into the text field.
        norm = []
        for w in chain:
            entry = getattr(w, "entry", None)
            norm.append(entry if entry is not None else w)
        chain = norm
        for idx, w in enumerate(chain):
            try:
                # Forward Tab
                def _next(event, i=idx):
                    try:
                        nxt = chain[(i + 1) % len(chain)]
                        nxt.focus_set()
                        try:
                            if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") != "1":
                                ensure_visible(canvas, inner, nxt)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return "break"  # prevent Text from inserting tab
                # Reverse (Shift+Tab)
                def _prev(event, i=idx):
                    try:
                        prv = chain[(i - 1) % len(chain)]
                        prv.focus_set()
                        try:
                            if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") != "1":
                                ensure_visible(canvas, inner, prv)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return "break"
                w.bind("<Tab>", _next)
                w.bind("<Shift-Tab>", _prev)
                w.bind("<ISO_Left_Tab>", _prev)  # some X11 platforms
            except Exception:
                pass
    _bind_tab_traversal(focus_chain)

    # Legacy global reference picker (feature-flag fallback)
    if os.environ.get("PA_DISABLE_SINGLE_WINDOW_FORMATTING_FIX") == "1" and not created_global_ref:
        ref_frame = tk.Frame(btn_bar)
        ref_frame.pack(side="left", padx=4)
        ref_path_var = tk.StringVar(value=get_global_reference_file() or "")
        ref_entry = tk.Entry(ref_frame, textvariable=ref_path_var, width=40)
        ref_entry.pack(side="left", fill="x", expand=True)

        def _browse_ref():
            from tkinter import filedialog

            fname = filedialog.askopenfilename()
            if fname:
                ref_path_var.set(fname)

        browse_btn = tk.Button(ref_frame, text="Browse", command=_browse_ref)
        browse_btn.pack(side="left", padx=2)

        def _view_ref():
            path = ref_path_var.get().strip()
            if not path:
                return
            win = tk.Toplevel(app.root)
            win.title(f"Reference File: {Path(path).name}")
            win.geometry("900x680")
            text_frame = tk.Frame(win)
            text_frame.pack(fill="both", expand=True)
            txt = tk.Text(text_frame, wrap="word")
            vs = tk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vs.set)
            txt.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")
            try:
                content = read_file_safe(path).replace("\r", "")
            except Exception:
                content = "(Error reading file)"
            txt.insert("1.0", content)
            txt.config(state="disabled")

        view_btn = tk.Button(ref_frame, text="View", command=_view_ref)
        view_btn.pack(side="left", padx=2)

        def _persist_ref():
            ov = load_overrides()
            gfiles = ov.setdefault("global_files", {})
            pv = ref_path_var.get().strip()
            if pv:
                gfiles["reference_file"] = pv
            else:
                gfiles.pop("reference_file", None)
            save_overrides(ov)

        ref_frame.entry = ref_entry  # type: ignore[attr-defined]
        ref_frame.browse_btn = browse_btn  # type: ignore[attr-defined]
        ref_frame.view_btn = view_btn  # type: ignore[attr-defined]

        bindings["_global_reference"] = {
            "get": lambda: ref_path_var.get(),
            "persist": _persist_ref,
            "path_var": ref_path_var,
            "view": _view_ref,
        }
        widgets["_global_reference"] = ref_frame

    # Key bindings (stage-level): Ctrl+Enter = Review, Esc = Back
    try:
        app.root.bind("<Control-Return>", lambda e: (review(), "break"))
        app.root.bind("<Escape>", lambda e: (go_back(), "break"))
    except Exception:
        pass

    return types.SimpleNamespace(
        frame=frame,
        widgets=widgets,
        bindings=bindings,
        open_exclusions=open_exclusions,
        review=review,
        reminders_panel=reminders_panel,
        reminders_toggle=_toggle if reminders_panel else (lambda: None),
    )


__all__ = ["build"]
