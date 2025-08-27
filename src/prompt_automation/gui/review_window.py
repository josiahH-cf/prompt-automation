"""Final review window for rendered output."""
from __future__ import annotations

from ..menus import render_template
from .. import paste
from ..variables.storage import is_auto_copy_enabled_for_template, get_setting_auto_copy_review  # type: ignore
from .constants import INSTR_FINISH_COPY_CLOSE, INSTR_FINISH_COPY_AGAIN


def review_output_gui(template, variables):
    """Review and edit the rendered output.

    Returns a tuple ``(final_text, var_map)`` where ``final_text`` is ``None``
    if the user cancels. ``var_map`` contains the raw variable inputs collected
    for the template, enabling append-to-file behaviour after confirmation.
    """
    import tkinter as tk
    from tkinter import messagebox

    # Render the template
    rendered_text, var_map = render_template(
        template, variables, return_vars=True
    )

    root = tk.Tk()
    root.title("Review Output - Prompt Automation")
    root.geometry("800x600")
    root.resizable(True, True)

    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    result = None

    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    main_frame.rowconfigure(2, weight=1)
    main_frame.columnconfigure(0, weight=1)

    # Instructions / status area (updated dynamically)
    instructions_var = tk.StringVar()
    instructions_var.set(
        "Edit the prompt below (this text is fully editable & will be copied). "
        + INSTR_FINISH_COPY_CLOSE
    )
    instructions = tk.Label(main_frame, textvariable=instructions_var, font=("Arial", 11), justify="left", anchor="w")
    instructions.grid(row=0, column=0, sticky="we", pady=(0,8))

    # Text editor
    text_frame = tk.Frame(main_frame)
    text_frame.grid(row=2, column=0, sticky="nsew", pady=(0,10))
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)

    from .fonts import get_display_font
    text_widget = tk.Text(text_frame, font=get_display_font(master=root), wrap="word")
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)

    text_widget.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Insert rendered text
    text_widget.insert("1.0", rendered_text)
    text_widget.focus_set()

    # --- Auto-copy feature (global + per-template) -------------------------
    try:  # best effort, never raise
        tid = None
        try:
            tid = template.get("id") if isinstance(template, dict) else None
        except Exception:
            tid = None
        if is_auto_copy_enabled_for_template(tid):
            did = False
            try:
                paste.copy_to_clipboard(rendered_text); did = True
            except Exception:
                pass
            if did:
                status_var.set("Copied to clipboard ✔")
                instructions_var.set(
                    "Copied automatically. You can keep editing. " + INSTR_FINISH_COPY_AGAIN
                )
    except Exception:
        pass

    # Button frame
    button_frame = tk.Frame(main_frame)
    button_frame.grid(row=3, column=0, sticky="we", pady=(4,0))
    button_frame.columnconfigure(10, weight=1)

    status_var = tk.StringVar(value="")
    status_label = tk.Label(button_frame, textvariable=status_var, font=("Arial", 9), fg="#2d6a2d")
    status_label.grid(row=0, column=10, sticky="e")

    def on_copy_only(event=None):
        text = text_widget.get("1.0", "end-1c")
        try:
            paste.copy_to_clipboard(text)
            status_var.set("Copied to clipboard ✔")
            instructions_var.set(
                "Copied. You can keep editing. " + INSTR_FINISH_COPY_AGAIN
            )
            # Clear status after a delay
            root.after(4000, lambda: status_var.set(""))
        except Exception as e:  # pragma: no cover - clipboard runtime
            status_var.set("Copy failed – see logs")
            messagebox.showerror("Clipboard Error", f"Unable to copy to clipboard:\n{e}")
        return "break"

    def on_confirm(event=None):
        nonlocal result
        result = text_widget.get("1.0", "end-1c")
        # Perform a final copy so user always leaves with clipboard populated
        try:
            paste.copy_to_clipboard(result)
        except Exception:
            pass
        root.destroy()
        return "break"

    def on_cancel(event=None):
        nonlocal result
        result = None
        root.destroy()
        return "break"

    copy_btn = tk.Button(
        button_frame,
        text="Copy (Ctrl+Shift+C)",
        command=on_copy_only,
        font=("Arial", 10),
        padx=16,
    )
    copy_btn.grid(row=0, column=0, padx=(0,8), sticky="w")

    confirm_btn = tk.Button(
        button_frame,
        text="Finish (Ctrl+Enter)",
        command=on_confirm,
        font=("Arial", 10),
        padx=18,
    )
    confirm_btn.grid(row=0, column=1, padx=(0,8), sticky="w")

    cancel_btn = tk.Button(
        button_frame,
        text="Cancel (Esc)",
        command=on_cancel,
        font=("Arial", 10),
        padx=18,
    )
    cancel_btn.grid(row=0, column=2, sticky="w")

    # Responsive wraplength adjustments
    def _on_resize(event=None):  # pragma: no cover - GUI runtime
        try:
            wrap = max(360, root.winfo_width() - 120)
            instructions.configure(wraplength=wrap)
        except Exception:
            pass
    root.bind("<Configure>", lambda e: _on_resize())
    _on_resize()

    # Keyboard bindings
    root.bind("<Control-Return>", on_confirm)
    root.bind("<Control-KP_Enter>", on_confirm)
    # Use Shift modifier to disambiguate from standard copy of selected text
    root.bind("<Control-Shift-c>", on_copy_only)
    root.bind("<Escape>", on_cancel)

    root.mainloop()
    return result, var_map


__all__ = ["review_output_gui"]
