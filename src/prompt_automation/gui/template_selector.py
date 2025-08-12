"""Template selection stage for the GUI workflow."""
from __future__ import annotations

import json

from .. import menus
from ..variables import (
    reset_file_overrides,
    list_file_overrides,
    reset_single_file_override,
)
from ..errorlog import get_logger

_log = get_logger(__name__)


def select_template_gui():
    """Template selection window - fully keyboard navigable."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("Select Template - Prompt Automation")
    root.geometry("600x400")
    root.resizable(False, False)

    # menu for additional actions
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    def on_reset_refs():
        if reset_file_overrides():
            messagebox.showinfo(
                "Reset reference files",
                "Reference file prompts will reappear.",
            )
        else:
            messagebox.showinfo(
                "Reset reference files",
                "No reference file overrides found.",
            )

    options_menu = tk.Menu(menubar, tearoff=0)
    options_menu.add_command(
        label="Reset reference files",
        command=on_reset_refs,
        accelerator="Ctrl+Shift+R",
    )

    def on_manage_overrides():
        import tkinter as tk
        from tkinter import messagebox

        win = tk.Toplevel(root)
        win.title("Manage Overrides")
        win.geometry("550x300")
        frame = tk.Frame(win, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        hint = tk.Label(
            frame,
            text="Remove an override to re-enable prompting. Entries mirror settings.json (two-way sync).",
            wraplength=520,
            justify="left",
            fg="#555",
        )
        hint.pack(anchor="w", pady=(0, 6))
        from tkinter import ttk

        tree = ttk.Treeview(frame, columns=("tid", "name", "data"), show="headings")
        tree.heading("tid", text="Template")
        tree.heading("name", text="Placeholder")
        tree.heading("data", text="Info")
        tree.column("tid", width=80, anchor="center")
        tree.column("name", width=130, anchor="w")
        tree.column("data", width=300, anchor="w")
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for tid, name, info in list_file_overrides():
            tree.insert("", "end", values=(tid, name, json.dumps(info)))
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=8)

        def do_remove():
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])
            tid, name, _ = item["values"]
            if reset_single_file_override(int(tid), name):
                tree.delete(sel[0])
            else:
                messagebox.showinfo("Override", "Nothing to remove")

        rm_btn = tk.Button(btn_frame, text="Remove Selected", command=do_remove)
        rm_btn.pack(side="left", padx=4)

        def do_close():
            win.destroy()

        close_btn = tk.Button(btn_frame, text="Close", command=do_close)
        close_btn.pack(side="left", padx=4)

    options_menu.add_command(label="Manage overrides", command=on_manage_overrides)
    menubar.add_cascade(label="Options", menu=options_menu)

    root.bind("<Control-Shift-R>", lambda e: (on_reset_refs(), "break"))

    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    selected_template = None

    # Create main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    # Instructions
    instructions = tk.Label(
        main_frame,
        text="Select a template using arrow keys, then press Enter:",
        font=("Arial", 12),
    )
    instructions.pack(pady=(0, 10))

    # Get all templates organized by style
    styles = [s for s in menus.list_styles() if s.lower() != "settings"]
    template_items = []

    for style in styles:
        prompts = menus.list_prompts(style)
        for prompt_path in prompts:
            # Skip settings.json explicitly
            if prompt_path.name.lower() == "settings.json":
                continue
            try:
                template = menus.load_template(prompt_path)
                # Validate schema; skip if missing required keys
                if not menus.validate_template(template):
                    continue
                title = template.get("title", prompt_path.stem)
                rel = prompt_path.relative_to(menus.PROMPTS_DIR / style)
                prefix = (str(rel.parent) + "/") if str(rel.parent) != "." else ""
                template_items.append(
                    {
                        "display": f"{style}: {prefix}{title}",
                        "template": template,
                        "path": prompt_path,
                    }
                )
            except Exception as e:  # pragma: no cover - template errors
                _log.error("Failed to load template %s: %s", prompt_path, e)

    if not template_items:
        messagebox.showerror("Error", "No templates found!")
        root.destroy()
        return None

    # Create listbox for templates
    listbox_frame = tk.Frame(main_frame)
    listbox_frame.pack(fill="both", expand=True, pady=(0, 10))

    listbox = tk.Listbox(listbox_frame, font=("Arial", 10))
    scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Populate listbox
    for item in template_items:
        listbox.insert("end", item["display"])

    # Select first item by default
    if template_items:
        listbox.selection_set(0)
        listbox.focus_set()

    # Button frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill="x")

    def on_select():
        nonlocal selected_template
        selection = listbox.curselection()
        if selection:
            selected_template = template_items[selection[0]]["template"]
            root.destroy()

    def on_cancel():
        root.destroy()

    select_btn = tk.Button(
        button_frame,
        text="Select (Enter)",
        command=on_select,
        font=("Arial", 10),
        padx=20,
    )
    select_btn.pack(side="left", padx=(0, 10))

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
        on_select()
        return "break"

    def on_escape(event):
        on_cancel()
        return "break"

    def on_double_click(event):
        on_select()
        return "break"

    root.bind("<Return>", on_enter)
    root.bind("<KP_Enter>", on_enter)
    root.bind("<Escape>", on_escape)
    listbox.bind("<Double-Button-1>", on_double_click)
    listbox.bind("<Return>", on_enter)
    listbox.bind("<KP_Enter>", on_enter)

    # Tab navigation
    def on_tab(event):
        if event.widget == listbox:
            select_btn.focus_set()
        elif event.widget == select_btn:
            cancel_btn.focus_set()
        elif event.widget == cancel_btn:
            listbox.focus_set()
        return "break"

    def on_shift_tab(event):
        if event.widget == listbox:
            cancel_btn.focus_set()
        elif event.widget == select_btn:
            listbox.focus_set()
        elif event.widget == cancel_btn:
            select_btn.focus_set()
        return "break"

    listbox.bind("<Tab>", on_tab)
    select_btn.bind("<Tab>", on_tab)
    cancel_btn.bind("<Tab>", on_tab)
    listbox.bind("<Shift-Tab>", on_shift_tab)
    select_btn.bind("<Shift-Tab>", on_shift_tab)
    cancel_btn.bind("<Shift-Tab>", on_shift_tab)

    root.mainloop()
    return selected_template


__all__ = ["select_template_gui"]
