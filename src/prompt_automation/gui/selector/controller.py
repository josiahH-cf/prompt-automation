"""Controller to open the template selector GUI.

Features:
- Hierarchical browsing (directories & templates) starting at PROMPTS_DIR
- Inline filtering (current directory) AND recursive search (toggle 'Recursive')
- Multi-select with synthetic combined template output (Finish Multi)
- Content-aware search: matches path, title, placeholder names, template body
- Preview window for template contents
- Override management dialogs
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import List, Optional

from .model import create_browser_state, ListingItem, TemplateEntry
from ...variables import (
    reset_file_overrides,
    list_file_overrides,
    reset_single_file_override,
)
from ...errorlog import get_logger

_log = get_logger(__name__)

# --- Preview window -------------------------------------------------------

def _open_preview(parent: tk.Tk, entry: TemplateEntry) -> None:
    try:
        tmpl = entry.data
        preview = tk.Toplevel(parent)
        preview.title(f"Preview: {tmpl.get('title', entry.path.name)}")
        preview.geometry("700x500")
        preview.resizable(True, True)
        text = tk.Text(preview, wrap="word", font=("Consolas", 10))
        text.pack(fill="both", expand=True)
        lines = tmpl.get('template', [])
        text.insert("1.0", "\n".join(lines))
        text.config(state="disabled")
        preview.transient(parent)
        preview.grab_set()
    except Exception as e:
        messagebox.showerror("Preview Error", str(e))

# --- Manage overrides dialog ----------------------------------------------

def _manage_overrides(root: tk.Tk):
    win = tk.Toplevel(root)
    win.title("Manage Overrides")
    win.geometry("580x340")
    frame = tk.Frame(win, padx=12, pady=12)
    frame.pack(fill="both", expand=True)
    hint = tk.Label(
        frame,
        text="Remove an override to re-enable prompting.",
        wraplength=520,
        justify="left",
        fg="#555",
    )
    hint.pack(anchor="w", pady=(0, 6))
    tree = ttk.Treeview(frame, columns=("tid", "name", "data"), show="headings")
    for col, w in ("tid",80), ("name",140), ("data",300):
        tree.heading(col, text=col.capitalize())
        tree.column(col, width=w, anchor="w")
    sb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    for tid, name, info in list_file_overrides():
        import json
        tree.insert("", "end", values=(tid, name, json.dumps(info)))
    btns = tk.Frame(win); btns.pack(pady=8)
    def do_remove():
        sel = tree.selection()
        if not sel: return
        item = tree.item(sel[0])
        tid, name, _ = item['values']
        if reset_single_file_override(int(tid), name):
            tree.delete(sel[0])
    tk.Button(btns, text="Remove Selected", command=do_remove).pack(side="left", padx=4)
    tk.Button(btns, text="Close", command=win.destroy).pack(side="left", padx=4)

# --- Main selector --------------------------------------------------------

def open_template_selector() -> Optional[dict]:
    root = tk.Tk()
    root.title("Select Template - Prompt Automation")
    root.geometry("950x720")
    root.resizable(True, True)
    root.lift(); root.focus_force(); root.attributes("-topmost", True); root.after(120, lambda: root.attributes("-topmost", False))

    browser = create_browser_state()
    browser.build()

    # Menu
    menubar = tk.Menu(root); root.config(menu=menubar)
    opt = tk.Menu(menubar, tearoff=0)
    def do_reset_refs():
        if reset_file_overrides():
            messagebox.showinfo("Reset", "Reference file prompts will reappear.")
        else:
            messagebox.showinfo("Reset", "No overrides found.")
    opt.add_command(label="Reset reference files", command=do_reset_refs, accelerator="Ctrl+Shift+R")
    opt.add_command(label="Manage overrides", command=lambda: _manage_overrides(root))
    menubar.add_cascade(label="Options", menu=opt)
    root.bind("<Control-Shift-R>", lambda e: (do_reset_refs(), "break"))

    # Top controls: search box & multi-select toggle
    top = tk.Frame(root, padx=10, pady=6); top.pack(fill="x")
    tk.Label(top, text="Search:").pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(top, textvariable=search_var, width=42)
    search_entry.pack(side="left", padx=(4,10))
    # Default to recursive search; user can opt-out (non-recursive)
    non_recursive_var = tk.BooleanVar(value=False)
    tk.Checkbutton(top, text="Non-recursive", variable=non_recursive_var).pack(side="left", padx=(0,8))
    multi_var = tk.BooleanVar(value=False)
    tk.Checkbutton(top, text="Multi-select", variable=multi_var).pack(side="left")
    preview_btn = tk.Button(top, text="Preview", state="disabled")
    preview_btn.pack(side="left", padx=6)
    breadcrumb_var = tk.StringVar(value=browser.breadcrumb())
    breadcrumb_lbl = tk.Label(top, textvariable=breadcrumb_var, anchor="w", fg="#555", wraplength=600)
    breadcrumb_lbl.pack(side="left", fill="x", expand=True, padx=(12,0))

    # Listbox
    main_frame = tk.Frame(root, padx=10, pady=6)
    main_frame.pack(fill="both", expand=True)
    listbox = tk.Listbox(main_frame, font=("Arial", 10), selectmode="extended")
    sb = tk.Scrollbar(main_frame, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=sb.set)
    listbox.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    selected_template: Optional[dict] = None
    preview_win: Optional[tk.Toplevel] = None  # for toggle behaviour (Ctrl+P)
    multi_selected: List[dict] = []

    def refresh(display_items: Optional[List[ListingItem]] = None):
        nonlocal selected_template
        items = display_items or browser.items
        listbox.delete(0, "end")
        for it in items:
            listbox.insert("end", it.display)
        if items:
            listbox.selection_set(0)
        selected_template = None
        preview_btn.config(state="disabled")
        breadcrumb_var.set(browser.breadcrumb())

    refresh()

    # Ensure initial keyboard focus lands in the search box for immediate typing
    # (Some WMs ignore early focus requests; schedule a couple of delayed attempts.)
    def _focus_initial():
        try:
            search_entry.focus_set()
            search_entry.focus_force()
            search_entry.select_range(0, 'end')
        except Exception:
            pass
    # Immediate + delayed to cope with window managers / animation
    _focus_initial()
    root.after(80, _focus_initial)
    root.after(200, _focus_initial)

    def current_items() -> List[ListingItem]:
        q = search_var.get().strip()
        if not q:
            return browser.items
        # If non-recursive toggled, restrict to current directory listing
        if non_recursive_var.get():
            return browser.filter(q)
        return browser.search(q)

    def on_search(*_):
        refresh(current_items())
    search_var.trace_add("write", on_search)
    non_recursive_var.trace_add("write", on_search)

    # Quick key: 's' focuses search box and toggles recursion mode
    def focus_search(event=None):
        # Just focus and select text; do not toggle recursion mode
        search_entry.focus_set()
        search_entry.after(10, lambda: search_entry.select_range(0, 'end'))
        return "break"
    root.bind("s", focus_search)
    listbox.bind("s", focus_search)

    def get_selected_item() -> Optional[ListingItem]:
        sel = listbox.curselection()
        if not sel:
            return None
        items = current_items()
        if sel[0] >= len(items):
            return None
        return items[sel[0]]

    def open_or_select():
        nonlocal selected_template, multi_selected
        item = get_selected_item()
        if not item:
            return
        if item.type in {"up", "dir"}:
            browser.enter(item)
            refresh(current_items())
            return
        if item.type == "template" and item.template:
            if multi_var.get():
                # Toggle selection in multi mode
                tmpl_dict = item.template.data
                if tmpl_dict in multi_selected:
                    multi_selected.remove(tmpl_dict)
                else:
                    multi_selected.append(tmpl_dict)
                # Visual hint (prefix with *)
                idx = listbox.curselection()[0]
                disp = item.display
                if disp.startswith("* "):
                    disp = disp[2:]
                else:
                    disp = "* " + disp
                listbox.delete(idx)
                listbox.insert(idx, disp)
                listbox.selection_set(idx)
            else:
                selected_template = item.template.data
                root.destroy()

    def on_preview():
        item = get_selected_item()
        if item and item.type == 'template' and item.template:
            _open_preview(root, item.template)
    preview_btn.config(command=on_preview)

    def on_select_event(event=None):
        open_or_select(); return "break"

    listbox.bind("<Return>", on_select_event)
    listbox.bind("<KP_Enter>", on_select_event)
    listbox.bind("<Double-Button-1>", on_select_event)

    def on_backspace(event):
        if browser.current != browser.root:
            # simulate selecting up
            for it in browser.items:
                if it.type == 'up':
                    browser.enter(it); refresh(current_items()); break
            return "break"
        return None
    listbox.bind("<BackSpace>", on_backspace)

    def on_key_release(event):
        item = get_selected_item()
        if item and item.type=='template':
            preview_btn.config(state="normal")
        else:
            preview_btn.config(state="disabled")
    listbox.bind("<<ListboxSelect>>", on_key_release)
    listbox.bind("<KeyRelease-Up>", on_key_release)
    listbox.bind("<KeyRelease-Down>", on_key_release)

    # --- Keyboard interaction while focus is in the search box -------------
    def _move_selection(delta: int):
        items = current_items()
        if not items:
            return
        sel = listbox.curselection()
        if not sel:
            idx = 0
        else:
            idx = sel[0] + delta
        idx = max(0, min(len(items) - 1, idx))
        listbox.selection_clear(0, 'end')
        listbox.selection_set(idx)
        listbox.see(idx)
        # Trigger preview button state update
        on_key_release(None)

    def _on_search_nav_down(event):
        _move_selection(1)
        return "break"

    def _on_search_nav_up(event):
        _move_selection(-1)
        return "break"

    def _on_search_enter(event):
        # Use current highlighted item
        open_or_select()
        return "break"

    search_entry.bind('<Down>', _on_search_nav_down)
    search_entry.bind('<Up>', _on_search_nav_up)
    search_entry.bind('<Return>', _on_search_enter)
    search_entry.bind('<KP_Enter>', _on_search_enter)

    # Preview toggle (Ctrl+P)
    def toggle_preview(event=None):
        nonlocal preview_win
        item = get_selected_item()
        if not item or item.type != 'template' or not item.template:
            return "break"
        # Close existing preview if open
        if preview_win and preview_win.winfo_exists():
            preview_win.destroy()
            preview_win = None
            return "break"
        # Open new preview window and keep reference
        try:
            tmpl = item.template.data
            preview_win = tk.Toplevel(root)
            preview_win.title(f"Preview: {tmpl.get('title', item.path.name)}")
            preview_win.geometry("700x500")
            preview_win.resizable(True, True)
            txt = tk.Text(preview_win, wrap='word', font=("Consolas", 10))
            txt.pack(fill='both', expand=True)
            lines = tmpl.get('template', [])
            txt.insert('1.0', "\n".join(lines))
            txt.config(state='disabled')
            def _closed(_):
                nonlocal preview_win
                preview_win = None
            preview_win.bind('<Destroy>', _closed)
        except Exception as e:  # pragma: no cover
            messagebox.showerror("Preview Error", str(e))
        return "break"

    root.bind('<Control-p>', toggle_preview)
    listbox.bind('<Control-p>', toggle_preview)
    search_entry.bind('<Control-p>', toggle_preview)

    # Buttons
    btns = tk.Frame(root, pady=6); btns.pack(fill="x")
    def finish_multi():
        nonlocal selected_template
        if multi_selected:
            # wrap multiple templates into a synthetic combined one (concatenate template arrays)
            combined = {
                'id': -1,
                'title': f"Multi ({len(multi_selected)})",
                'style': 'multi',
                'template': sum([t.get('template', []) for t in multi_selected], []),
                'placeholders': [],
            }
            selected_template = combined
            root.destroy()
    tk.Button(btns, text="Open / Select (Enter)", command=open_or_select, padx=18).pack(side="left", padx=(0,8))
    tk.Button(btns, text="Finish Multi", command=finish_multi).pack(side="left", padx=(0,8))
    tk.Button(btns, text="Preview", command=on_preview).pack(side="left", padx=(0,8))
    tk.Button(btns, text="Cancel (Esc)", command=root.destroy).pack(side="left")

    root.bind("<Escape>", lambda e: (root.destroy(), "break"))

    root.mainloop()
    return selected_template

__all__ = ["open_template_selector"]
