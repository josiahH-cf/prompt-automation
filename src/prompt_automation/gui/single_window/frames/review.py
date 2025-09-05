"""Output review frame used by :class:`SingleWindowApp`.

Renders the template with collected variables and provides copy/finish actions.
During tests a lightweight stand-in object is returned so behaviour can be
verified without a real ``tkinter`` environment.
"""
from __future__ import annotations

from typing import Any, Dict
import os

from ....renderer import fill_placeholders, read_file_safe
from ..formatting_helpers import format_markdown_plain
from ....paste import copy_to_clipboard  # legacy direct copy
from ...error_dialogs import safe_copy_to_clipboard
from ....variables.storage import get_setting_auto_copy_review, is_auto_copy_enabled_for_template
from ...constants import INSTR_FINISH_COPY_AGAIN, INSTR_FINISH_COPY_CLOSE
from ...file_append import _append_to_files
from ....logger import log_usage


def build(app, template: Dict[str, Any], variables: Dict[str, Any]):  # pragma: no cover - Tk runtime
    """Build review frame and return a small namespace for tests."""
    import tkinter as tk
    # message dialogs imported lazily only in GUI path to keep headless tests simple
    import types

    raw_lines = template.get("template") or []
    if not isinstance(raw_lines, list):
        raw_lines = []
    rendered = fill_placeholders(raw_lines, variables)

    has_paths = any(k.endswith("_path") and v for k, v in variables.items())
    needs_append = any(
        k == "append_file" or k.endswith("_append_file") for k in variables
    )

    # Determine if reference file is present in variables
    ref_path = None
    try:
        val = variables.get("reference_file")
        if isinstance(val, str) and val.strip():
            ref_path = val.strip()
    except Exception:
        ref_path = None

    # ------------------------------------------------------------------
    # Headless test environment: tkinter stub without Label class
    # ------------------------------------------------------------------
    if not hasattr(tk, "Label"):
        status = {"text": ""}
        instr = {"text": INSTR_FINISH_COPY_CLOSE}

        def _set_status(msg: str) -> None:
            status["text"] = msg

        def do_copy() -> None:
            # Attempt resilient copy first; fallback to legacy util
            if not safe_copy_to_clipboard(rendered):
                copy_to_clipboard(rendered)
            _set_status("Copied ✔")
            instr["text"] = INSTR_FINISH_COPY_AGAIN

        def copy_paths() -> None:
            if not has_paths:
                return
            paths = [str(v) for k, v in variables.items() if k.endswith("_path") and v]
            if not safe_copy_to_clipboard("\n".join(paths)):
                copy_to_clipboard("\n".join(paths))
            _set_status("Paths Copied ✔")

        def finish() -> None:
            # In headless tests, respect a stubbed tkinter.messagebox if provided
            if needs_append:
                try:
                    import tkinter as _tk  # type: ignore
                    mb = getattr(_tk, 'messagebox', None)
                    do_append = bool(mb.askyesno("Append Output", "Append rendered text to file(s)?")) if mb else False
                except Exception:
                    do_append = False
                if do_append:
                    _append_to_files(variables, rendered)
            log_usage(template, len(rendered))
            # Record in recent history (ignore errors)
            try:
                from ....history import record_history
                record_history(template, rendered_text=rendered, final_output=rendered)
            except Exception:
                pass
            if not safe_copy_to_clipboard(rendered):
                copy_to_clipboard(rendered)
            app.finish(rendered)

        def view_reference() -> str | None:
            # Headless viewer: return prettified plain text for assertions
            try:
                if not ref_path:
                    return None
                raw = read_file_safe(ref_path)
                return format_markdown_plain(raw)
            except Exception:
                return None

        def cancel() -> None:
            app.cancel()

        bindings = {
            "<Control-Return>": finish,
            "<Control-Shift-c>": do_copy,
            "<Escape>": cancel,
        }

    # Auto-copy skipped in headless test path to maintain deterministic copy counts in tests.

        return types.SimpleNamespace(
            frame=object(),
            copy_paths_btn=object() if has_paths else None,
            instructions=instr,
            status=status,
            copy=do_copy,
            copy_paths=copy_paths,
            finish=finish,
            cancel=cancel,
            bindings=bindings,
            view_reference=view_reference if ref_path else None,
        )

    # ------------------------------------------------------------------
    # Real tkinter widgets
    # ------------------------------------------------------------------
    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)
    frame.rowconfigure(1, weight=1)  # text area expands
    frame.columnconfigure(0, weight=1)

    instr_var = tk.StringVar(value=INSTR_FINISH_COPY_CLOSE)
    instr_lbl = tk.Label(frame, textvariable=instr_var, anchor="w", fg="#444", justify="left")
    instr_lbl.grid(row=0, column=0, sticky="we", pady=(12,4), padx=12)

    text_frame = tk.Frame(frame)
    text_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    text = tk.Text(text_frame, wrap="word", undo=True)
    scroll = tk.Scrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    text.insert("1.0", rendered)
    text.focus_set()

    status_var = tk.StringVar(value="")
    btn_bar = tk.Frame(frame)
    btn_bar.grid(row=2, column=0, sticky="we", pady=(0,8))
    btn_bar.columnconfigure(0, weight=1)
    tk.Label(btn_bar, textvariable=status_var, anchor="w").grid(row=0, column=0, sticky="w", padx=12)

    def _set_status(msg: str) -> None:
        status_var.set(msg)
        app.root.after(3000, lambda: status_var.set(""))

    def do_copy() -> None:
        content = text.get("1.0", "end-1c")
        if not safe_copy_to_clipboard(content):
            copy_to_clipboard(content)
        _set_status("Copied ✔")
        instr_var.set(INSTR_FINISH_COPY_AGAIN)

    def copy_paths() -> None:
        paths = [str(v) for k, v in variables.items() if k.endswith("_path") and v]
        if paths:
            payload = "\n".join(paths)
            if not safe_copy_to_clipboard(payload):
                copy_to_clipboard(payload)
            _set_status("Paths Copied ✔")

    def _open_reference() -> None:
        # Show reference file content in a simple viewer window
        try:
            if not ref_path:
                return
            win = tk.Toplevel(app.root)
            from pathlib import Path as _P
            try: win.title(f"Reference File: {_P(ref_path).name}")
            except Exception: win.title("Reference File")
            win.geometry("900x680")
            text_frame = tk.Frame(win)
            text_frame.pack(fill="both", expand=True)
            txt = tk.Text(text_frame, wrap="word")
            vs = tk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vs.set)
            txt.pack(side="left", fill="both", expand=True)
            vs.pack(side="right", fill="y")
            try:
                raw = read_file_safe(ref_path).replace("\r", "")
            except Exception:
                raw = "(Error reading file)"
            # Prettify markdown for readability; fall back to raw on error
            try:
                content = format_markdown_plain(raw)
            except Exception:
                content = raw
            # Basic emphasis: configure a slightly nicer font for display
            try:
                from ..fonts import get_display_font
                txt.configure(font=get_display_font(master=app.root))
            except Exception:
                pass
            txt.insert("1.0", content)
            txt.config(state="disabled")
        except Exception:
            pass

    def finish() -> None:
        final_text = text.get("1.0", "end-1c")
        if needs_append:
            try:
                from tkinter import messagebox  # type: ignore
                do_append = messagebox.askyesno("Append Output", "Append rendered text to file(s)?")
            except Exception:
                do_append = False
            if do_append:
                _append_to_files(variables, final_text)
        log_usage(template, len(final_text))
        # Record in recent history (ignore errors)
        try:
            from ....history import record_history
            record_history(template, rendered_text=final_text, final_output=final_text)
        except Exception:
            pass
        if not safe_copy_to_clipboard(final_text):
            copy_to_clipboard(final_text)
        app.finish(final_text)

    def cancel() -> None:
        app.cancel()

    copy_btn = tk.Button(btn_bar, text="Copy", command=do_copy)
    copy_btn.grid(row=0, column=99, sticky="e", padx=4)
    if has_paths:
        copy_paths_btn = tk.Button(btn_bar, text="Copy Paths", command=copy_paths)
        copy_paths_btn.grid(row=0, column=98, sticky="e", padx=4)
    else:
        copy_paths_btn = None
    if ref_path:
        view_ref_btn = tk.Button(btn_bar, text="View Reference", command=_open_reference)
        view_ref_btn.grid(row=0, column=97, sticky="e", padx=4)
    tk.Button(btn_bar, text="Finish", command=finish).grid(row=0, column=96, sticky="e", padx=4)
    tk.Button(btn_bar, text="Cancel", command=cancel).grid(row=0, column=95, sticky="e", padx=12)

    # Responsive adjustments (instruction wraplength)
    def _on_resize(event=None):  # pragma: no cover - GUI behaviour
        try:
            wrap = max(300, frame.winfo_width() - 200)
            instr_lbl.configure(wraplength=wrap)
        except Exception:
            pass
    frame.bind("<Configure>", lambda e: _on_resize())
    _on_resize()

    app.root.bind("<Control-Return>", lambda e: (finish(), "break"))
    app.root.bind("<Control-Shift-c>", lambda e: (do_copy(), "break"))
    app.root.bind("<Escape>", lambda e: (cancel(), "break"))

    # Perform auto-copy immediately if setting enabled
    try:
        if is_auto_copy_enabled_for_template(template.get("id")):
            content_initial = text.get("1.0", "end-1c")
            if content_initial.strip():
                copied = safe_copy_to_clipboard(content_initial)
                if not copied:
                    try: copy_to_clipboard(content_initial); copied = True
                    except Exception: copied = False
                if copied:
                    _set_status("Copied ✔")
                    instr_var.set(INSTR_FINISH_COPY_AGAIN)
    except Exception:
        pass

    # If reference file present, auto-open once after layout unless disabled
    try:
        if ref_path:
            auto_open = os.environ.get("PA_REVIEW_AUTO_OPEN_REFERENCE", "1") != "0"
            if auto_open:
                app.root.after(80, _open_reference)
    except Exception:
        pass

    # Expose functions so controller can surface in per-stage menu
    return {
        "frame": frame,
        "copy_paths_btn": copy_paths_btn,
        "copy": do_copy,
        "finish": finish,
        "cancel": cancel,
    }


__all__ = ["build"]
