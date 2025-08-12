"""Simple GUI front-end for prompt selection and rendering using Tkinter."""
from __future__ import annotations

import sys
from pathlib import Path

from . import logger, menus, paste, update
from . import updater  # silent pipx auto-updater (rate-limited)
from .errorlog import get_logger
from .renderer import read_file_safe
from .variables import (
    _get_template_entry,
    _load_overrides,
    _print_one_time_skip_reminder,
    _save_overrides,
    _set_template_entry,
    reset_file_overrides,
)


_log = get_logger(__name__)


# sentinel object to signal user cancellation during input collection
CANCELLED = object()


def run() -> None:
    """Launch the GUI using Tkinter. Falls back to CLI if GUI fails."""
    # Perform background silent pipx upgrade (non-blocking) then existing
    # manifest-based interactive update (retained behaviour)
    try:  # never block GUI startup
        updater.check_for_update()
    except Exception:
        pass
    update.check_and_prompt()
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox, simpledialog
    except Exception as e:
        _log.warning("Tkinter not available: %s", e)
        print(
            "[prompt-automation] GUI not available, falling back to terminal mode:",
            e,
            file=sys.stderr,
        )
        from . import cli

        cli.main(["--terminal"])
        return

    try:
        # Start the simplified template selection workflow
        _log.info("Starting GUI workflow")
        template = select_template_gui()
        if template:
            _log.info("Template selected: %s", template.get('title', 'Unknown'))
            # Collect variables for the template
            variables = collect_variables_gui(template)
            if variables is not None:
                _log.info(
                    "Variables collected: %d placeholders",
                    len(template.get("placeholders", [])),
                )
                # Render and review the output
                final_text = review_output_gui(template, variables)
                if final_text is not None:
                    _log.info("Final text confirmed, length: %d", len(final_text))
                    logger.log_usage(template, len(final_text))
                    _log.info("Workflow completed successfully")
                else:
                    _log.info("User cancelled at review stage")
            else:
                _log.info("User cancelled during variable collection")
        else:
            _log.info("User cancelled template selection")
    except Exception as e:
        _log.error("GUI workflow failed: %s", e, exc_info=True)
        # Show error to user
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"An error occurred in the GUI:\n\n{e}\n\nCheck logs for details.")
            root.destroy()
        except:
            print(f"[prompt-automation] GUI Error: {e}", file=sys.stderr)
        raise


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
    menubar.add_cascade(label="Options", menu=options_menu)

    root.bind("<Control-Shift-R>", lambda e: (on_reset_refs(), "break"))
    
    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    
    selected_template = None
    
    # Create main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Instructions
    instructions = tk.Label(main_frame, text="Select a template using arrow keys, then press Enter:", 
                           font=("Arial", 12))
    instructions.pack(pady=(0, 10))
    
    # Get all templates organized by style
    styles = menus.list_styles()
    template_items = []
    
    for style in styles:
        prompts = menus.list_prompts(style)
        for prompt_path in prompts:
            try:
                template = menus.load_template(prompt_path)
                title = template.get('title', prompt_path.stem)
                # Relative subfolder display (exclude style root)
                rel = prompt_path.relative_to(menus.PROMPTS_DIR / style)
                prefix = (str(rel.parent) + '/') if str(rel.parent) != '.' else ''
                template_items.append({
                    'display': f"{style}: {prefix}{title}",
                    'template': template,
                    'path': prompt_path
                })
            except Exception as e:
                _log.error(f"Failed to load template {prompt_path}: {e}")
    
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
        listbox.insert("end", item['display'])
    
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
            selected_template = template_items[selection[0]]['template']
            root.destroy()
    
    def on_cancel():
        root.destroy()
    
    select_btn = tk.Button(button_frame, text="Select (Enter)", command=on_select, 
                          font=("Arial", 10), padx=20)
    select_btn.pack(side="left", padx=(0, 10))
    
    cancel_btn = tk.Button(button_frame, text="Cancel (Esc)", command=on_cancel, 
                          font=("Arial", 10), padx=20)
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
    
    root.bind('<Return>', on_enter)
    root.bind('<KP_Enter>', on_enter)
    root.bind('<Escape>', on_escape)
    listbox.bind('<Double-Button-1>', on_double_click)
    listbox.bind('<Return>', on_enter)
    listbox.bind('<KP_Enter>', on_enter)
    
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
    
    listbox.bind('<Tab>', on_tab)
    select_btn.bind('<Tab>', on_tab)
    cancel_btn.bind('<Tab>', on_tab)
    listbox.bind('<Shift-Tab>', on_shift_tab)
    select_btn.bind('<Shift-Tab>', on_shift_tab)
    cancel_btn.bind('<Shift-Tab>', on_shift_tab)
    
    root.mainloop()
    return selected_template


def collect_file_variable_gui(template_id: int, placeholder: dict, globals_map: dict):
    """GUI file selector with persistence and skip support."""
    import tkinter as tk
    from tkinter import filedialog

    name = placeholder["name"]
    label = placeholder.get("label", name)
    skip_local_flag = f"{name}_skip_template"
    skip_local = globals_map.get(skip_local_flag) == "yes" or placeholder.get("default") == "skip"

    overrides = _load_overrides()
    entry = _get_template_entry(overrides, template_id, name) or {}

    if entry.get("skip") or skip_local:
        _print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    global_skip = globals_map.get("reference_file_skip") == "yes"
    if global_skip and not entry:
        _set_template_entry(overrides, template_id, name, {"skip": True})
        _save_overrides(overrides)
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
    root.geometry("500x150")
    root.resizable(False, False)
    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

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

    root.bind('<Return>', lambda e: (on_ok(), "break"))
    root.bind('<KP_Enter>', lambda e: (on_ok(), "break"))
    root.bind('<Escape>', lambda e: (on_cancel(), "break"))

    root.mainloop()
    return result


def show_reference_file_content(path: str) -> None:
    """Display the contents of ``path`` in a read-only Tk window."""
    import tkinter as tk

    text = read_file_safe(path)

    root = tk.Tk()
    root.title(f"Reference File: {Path(path).name}")
    root.geometry("800x600")
    root.resizable(True, True)

    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)

    text_frame = tk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, pady=(0, 10))

    text_widget = tk.Text(text_frame, font=("Consolas", 10), wrap="word")
    scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    text_widget.insert("1.0", text)
    text_widget.config(state="disabled")

    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=(10, 0))

    def on_close(event=None):
        root.destroy()
        return "break"

    close_btn = tk.Button(button_frame, text="Close (Esc)", command=on_close,
                          font=("Arial", 10), padx=20)
    close_btn.pack()

    root.bind('<Escape>', on_close)
    root.bind('<Return>', on_close)

    root.mainloop()


def collect_variables_gui(template):
    """Collect variables for template placeholders - fully keyboard driven."""
    placeholders = template.get('placeholders', [])
    if not placeholders:
        return {}

    variables = {}
    template_id = template.get("id", 0)
    globals_map = template.get("global_placeholders", {})

    for placeholder in placeholders:
        name = placeholder["name"]
        label = placeholder.get("label", name)
        ptype = placeholder.get("type", "text")
        options = placeholder.get("options", [])
        multiline = placeholder.get("multiline", False) or ptype == "list"

        if name == "reference_file_content":
            path = variables.get("reference_file")
            p = Path(path).expanduser() if path else None
            if p and p.exists():
                show_reference_file_content(str(p))
                variables[name] = read_file_safe(str(p))
            else:
                variables[name] = ""
            continue

        if ptype == "file":
            value = collect_file_variable_gui(template_id, placeholder, globals_map)
        else:
            value = collect_single_variable(name, label, ptype, options, multiline)
        if value is CANCELLED:  # User cancelled entire workflow
            return None
        variables[name] = value

    return variables


def collect_single_variable(name, label, ptype, options, multiline):
    """Collect a single variable with appropriate input method."""
    import tkinter as tk
    from tkinter import ttk, filedialog

    root = tk.Tk()
    root.title(f"Input: {label}")
    root.geometry("500x300" if multiline else "500x150")
    root.resizable(False, False)

    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    result = CANCELLED
    
    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Label
    label_widget = tk.Label(main_frame, text=f"{label}:", font=("Arial", 12))
    label_widget.pack(anchor="w", pady=(0, 10))
    
    # Input widget based on type
    input_widget = None
    
    if options:
        # Dropdown for options
        input_widget = ttk.Combobox(main_frame, values=options, font=("Arial", 10))
        input_widget.pack(fill="x", pady=(0, 10))
        input_widget.set(options[0] if options else "")
        input_widget.focus_set()
        
    elif ptype == 'file':
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
        
        browse_btn = tk.Button(file_frame, text="Browse", command=browse_file, 
                              font=("Arial", 10))
        browse_btn.pack(side="right")
        
        input_widget.focus_set()
        
    elif multiline or ptype == 'list':
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
    
    # Button frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill="x")
    
    def on_ok(skip: bool = False):
        nonlocal result
        if skip:
            result = None
        elif isinstance(input_widget, tk.Text):
            value = input_widget.get("1.0", "end-1c")
            if ptype == "list":
                result = [line.strip() for line in value.splitlines() if line.strip()]
            else:
                result = value
        else:
            result = input_widget.get()
        root.destroy()

    def on_cancel():
        nonlocal result
        result = CANCELLED
        root.destroy()
    
    ok_btn = tk.Button(button_frame, text="OK (Enter)", command=on_ok, 
                      font=("Arial", 10), padx=20)
    ok_btn.pack(side="left", padx=(0, 10))
    
    cancel_btn = tk.Button(button_frame, text="Cancel (Esc)", command=on_cancel, 
                          font=("Arial", 10), padx=20)
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
    
    root.bind('<Control-Return>', on_enter)
    root.bind('<Control-KP_Enter>', on_enter)
    root.bind('<Escape>', on_escape)
    
    # For non-text widgets, regular Enter also submits
    if not isinstance(input_widget, tk.Text):
        root.bind('<Return>', on_enter)
        root.bind('<KP_Enter>', on_enter)
    
    root.mainloop()
    return result


def review_output_gui(template, variables):
    """Review and edit the rendered output."""
    import tkinter as tk
    from tkinter import messagebox
    
    # Render the template
    rendered_text = menus.render_template(template, variables)
    
    root = tk.Tk()
    root.title("Review Output - Prompt Automation")
    root.geometry("800x600")
    root.resizable(True, True)
    
    # Bring to foreground and focus
    root.lift()
    root.focus_force()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    
    result = None
    
    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Instructions / status area (updated dynamically)
    instructions_var = tk.StringVar()
    instructions_var.set(
        "Edit the prompt below. Ctrl+Enter = Finish (copies & closes), "
        "Ctrl+Shift+C = Copy without closing, Esc = Cancel"
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
    root.bind('<Control-Return>', on_confirm)
    root.bind('<Control-KP_Enter>', on_confirm)
    # Use Shift modifier to disambiguate from standard copy of selected text
    root.bind('<Control-Shift-c>', on_copy_only)
    root.bind('<Escape>', on_cancel)
    
    root.mainloop()
    return result

