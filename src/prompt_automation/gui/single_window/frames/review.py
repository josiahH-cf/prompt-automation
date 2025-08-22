"""Output review frame used by :class:`SingleWindowApp`.

Renders the template with collected variables and provides copy/finish actions.
During tests a lightweight stand-in object is returned so behaviour can be
verified without a real ``tkinter`` environment.
"""
from __future__ import annotations

from typing import Any, Dict

from ....renderer import fill_placeholders
from ....paste import copy_to_clipboard  # legacy direct copy
from ...error_dialogs import safe_copy_to_clipboard
from ...constants import INSTR_FINISH_COPY_AGAIN, INSTR_FINISH_COPY_CLOSE
from ...file_append import _append_to_files
from ....logger import log_usage


def build(app, template: Dict[str, Any], variables: Dict[str, Any]):  # pragma: no cover - Tk runtime
    """Build review frame and return a small namespace for tests."""
    import tkinter as tk
    from tkinter import messagebox
    import types

    raw_lines = template.get("template") or []
    if not isinstance(raw_lines, list):
        raw_lines = []
    rendered = fill_placeholders(raw_lines, variables)

    has_paths = any(k.endswith("_path") and v for k, v in variables.items())
    needs_append = any(
        k == "append_file" or k.endswith("_append_file") for k in variables
    )

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
            if needs_append and messagebox.askyesno(
                "Append Output", "Append rendered text to file(s)?"
            ):
                _append_to_files(variables, rendered)
            log_usage(template, len(rendered))
            if not safe_copy_to_clipboard(rendered):
                copy_to_clipboard(rendered)
            app.finish(rendered)

        def cancel() -> None:
            app.cancel()

        bindings = {
            "<Control-Return>": finish,
            "<Control-Shift-c>": do_copy,
            "<Escape>": cancel,
        }

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
        )

    # ------------------------------------------------------------------
    # Real tkinter widgets
    # ------------------------------------------------------------------
    frame = tk.Frame(app.root)
    frame.pack(fill="both", expand=True)

    instr_var = tk.StringVar(value=INSTR_FINISH_COPY_CLOSE)
    tk.Label(frame, textvariable=instr_var, anchor="w", fg="#444").pack(
        fill="x", pady=(12, 4), padx=12
    )

    text_frame = tk.Frame(frame)
    text_frame.pack(fill="both", expand=True, padx=12, pady=8)

    text = tk.Text(text_frame, wrap="word")
    scroll = tk.Scrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    text.insert("1.0", rendered)
    text.focus_set()

    status_var = tk.StringVar(value="")
    btn_bar = tk.Frame(frame)
    btn_bar.pack(fill="x", pady=(0, 8))
    tk.Label(btn_bar, textvariable=status_var, anchor="w").pack(side="left", padx=12)

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

    def finish() -> None:
        final_text = text.get("1.0", "end-1c")
        if needs_append and messagebox.askyesno(
            "Append Output", "Append rendered text to file(s)?"
        ):
            _append_to_files(variables, final_text)
        log_usage(template, len(final_text))
        if not safe_copy_to_clipboard(final_text):
            copy_to_clipboard(final_text)
        app.finish(final_text)

    def cancel() -> None:
        app.cancel()

    copy_btn = tk.Button(btn_bar, text="Copy", command=do_copy)
    copy_btn.pack(side="right", padx=4)
    if has_paths:
        copy_paths_btn = tk.Button(btn_bar, text="Copy Paths", command=copy_paths)
        copy_paths_btn.pack(side="right", padx=4)
    else:
        copy_paths_btn = None
    tk.Button(btn_bar, text="Finish", command=finish).pack(side="right", padx=4)
    tk.Button(btn_bar, text="Cancel", command=cancel).pack(side="right", padx=12)

    app.root.bind("<Control-Return>", lambda e: (finish(), "break"))
    app.root.bind("<Control-Shift-c>", lambda e: (do_copy(), "break"))
    app.root.bind("<Escape>", lambda e: (cancel(), "break"))

    # Expose functions so controller can surface in per-stage menu
    return {
        "frame": frame,
        "copy_paths_btn": copy_paths_btn,
        "copy": do_copy,
        "finish": finish,
        "cancel": cancel,
    }


__all__ = ["build"]
