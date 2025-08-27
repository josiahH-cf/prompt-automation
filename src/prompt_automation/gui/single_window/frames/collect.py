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
from ...collector.persistence import get_global_reference_file
from ...collector.overrides import load_overrides, save_overrides
from ....renderer import read_file_safe
from ...constants import INSTR_COLLECT_SHORTCUTS


def build(app, template: Dict[str, Any]):  # pragma: no cover - Tk runtime
    """Return a view object after constructing the form."""
    import tkinter as tk  # type: ignore

    # Headless test stub: provide legend text without constructing widgets
    if not hasattr(tk, "Canvas"):
        instr = {"text": INSTR_COLLECT_SHORTCUTS}
        # Provide minimal bindings map for tests (Ctrl+Enter review stub)
        bindings = {}
        def _review_stub():
            return None
        bindings["<Control-Return>"] = _review_stub
        return types.SimpleNamespace(instructions=instr, bindings=bindings)

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

    label_widgets = []  # track to update wraplength on resize

    focus_chain = []  # ordered list of focusable input widgets
    for row, ph in enumerate(placeholders):
        name = ph.get("name") if isinstance(ph, dict) else None
        if not name:
            continue
        lbl = tk.Label(inner, text=ph.get("label", name), anchor="w", justify="left")
        lbl.grid(row=row, column=0, sticky="nw", padx=6, pady=4)
        label_widgets.append(lbl)

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
                widget.grid(row=row, column=1, sticky="nsew", padx=(6, 0), pady=4)
                sb.grid(row=row, column=2, sticky="ns", padx=(0, 6), pady=4)
                inner.rowconfigure(row, weight=1)
                inner.columnconfigure(1, weight=1)
            except Exception:
                widget.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            focus_chain.append(widget)
        elif bind.get("path_var") is not None:
            widget.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            entry = getattr(widget, "entry", None)
            browse_btn = getattr(widget, "browse_btn", None)
            skip_btn = getattr(widget, "skip_btn", None)
            if entry:
                entry.pack(side="left", fill="x", expand=True)
                focus_chain.append(entry)
            if browse_btn:
                browse_btn.pack(side="left", padx=2)
            if skip_btn:
                skip_btn.pack(side="left", padx=2)
            if bind.get("view") and hasattr(widget, "view_btn"):
                widget.view_btn.pack(side="left", padx=2)  # type: ignore[attr-defined]
        else:  # single-line entry
            widget.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            try:
                import tkinter as _tk2
                if isinstance(widget, _tk2.Entry):
                    focus_chain.append(widget)
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
            tk.Label(inner, text="*", fg="red").grid(row=row, column=3, padx=2)

            def _reset(b=bind):
                if b.get("path_var") is not None:
                    b["path_var"].set("")  # type: ignore[index]
                if b.get("skip_var") is not None:
                    b["skip_var"].set(False)  # type: ignore[index]
                b.get("persist", lambda: None)()

            bind["reset"] = _reset
            tk.Button(inner, text="Reset", command=_reset).grid(row=row, column=4, padx=2)

        if row == 0 and hasattr(widget, "focus_set"):
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

    # --- Global reference file picker ------------------------------------
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
                    except Exception:
                        pass
                    return "break"  # prevent Text from inserting tab
                # Reverse (Shift+Tab)
                def _prev(event, i=idx):
                    try:
                        prv = chain[(i - 1) % len(chain)]
                        prv.focus_set()
                    except Exception:
                        pass
                    return "break"
                w.bind("<Tab>", _next)
                w.bind("<Shift-Tab>", _prev)
                w.bind("<ISO_Left_Tab>", _prev)  # some X11 platforms
            except Exception:
                pass
    _bind_tab_traversal(focus_chain)

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
    )


__all__ = ["build"]
