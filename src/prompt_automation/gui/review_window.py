"""Final review window for rendered output."""
from __future__ import annotations

from ..menus import render_template
from .. import paste


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

    # Instructions / status area (updated dynamically)
    instructions_var = tk.StringVar()
    instructions_var.set(
        "Edit the prompt below (this text is fully editable & will be copied). "
        "Ctrl+Enter = Finish (copies & closes), Ctrl+Shift+C = Copy without closing, Esc = Cancel"
    )
    instructions = tk.Label(
        main_frame,
        textvariable=instructions_var,
        font=("Arial", 11),
        justify="left",
        anchor="w",
        wraplength=760,
    )
    instructions.pack(fill="x", pady=(0, 8))

    # Text editor
    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    text_widget = tk.Text(text_frame, font=("Consolas", 10), wrap="word")
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)

    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Insert rendered text
    text_widget.insert("1.0", rendered_text)
    text_widget.focus_set()

    # Button frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill="x", pady=(4, 0))

    status_var = tk.StringVar(value="")
    status_label = tk.Label(button_frame, textvariable=status_var, font=("Arial", 9), fg="#2d6a2d")
    status_label.pack(side="right")

    def on_copy_only(event=None):
        text = text_widget.get("1.0", "end-1c")
        try:
            paste.copy_to_clipboard(text)
            status_var.set("Copied to clipboard ✔")
            instructions_var.set(
                "Copied. You can keep editing. Ctrl+Enter = Finish (copies & closes), "
                "Ctrl+Shift+C = Copy again, Esc = Cancel"
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
    copy_btn.pack(side="left", padx=(0, 8))

    confirm_btn = tk.Button(
        button_frame,
        text="Finish (Ctrl+Enter)",
        command=on_confirm,
        font=("Arial", 10),
        padx=18,
    )
    confirm_btn.pack(side="left", padx=(0, 8))

    cancel_btn = tk.Button(
        button_frame,
        text="Cancel (Esc)",
        command=on_cancel,
        font=("Arial", 10),
        padx=18,
    )
    cancel_btn.pack(side="left")

    # Keyboard bindings
    root.bind("<Control-Return>", on_confirm)
    root.bind("<Control-KP_Enter>", on_confirm)
    # Use Shift modifier to disambiguate from standard copy of selected text
    root.bind("<Control-Shift-c>", on_copy_only)
    root.bind("<Escape>", on_cancel)

    root.mainloop()
    return result, var_map


__all__ = ["review_output_gui"]
