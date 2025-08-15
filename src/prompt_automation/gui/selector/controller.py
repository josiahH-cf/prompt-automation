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

from .model import create_browser_state, ListingItem, TemplateEntry, BrowserState
from ...variables import (
    reset_file_overrides,
    list_file_overrides,
    reset_single_file_override,
    list_template_value_overrides,
    reset_template_value_override,
    set_template_value_override,
)
from ..new_template_wizard import open_new_template_wizard
from ...shortcuts import load_shortcuts, save_shortcuts, renumber_templates, SHORTCUT_FILE
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
    """Unified manager for file & simple value overrides with inline editing."""
    win = tk.Toplevel(root)
    win.title("Manage Overrides")
    win.geometry("760x420")
    frame = tk.Frame(win, padx=12, pady=12)
    frame.pack(fill="both", expand=True)
    hint = tk.Label(
        frame,
        text="Double‑click a row to edit value (simple overrides). Delete removes. File overrides show path/skip.",
        wraplength=720,
        justify="left",
        fg="#555",
    )
    hint.pack(anchor="w", pady=(0, 6))
    cols = ("kind","tid","name","data")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    widths = {"kind":80, "tid":60, "name":160, "data":360}
    for c in cols:
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=widths[c], anchor="w")
    sb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    import json
    def _refresh():
        tree.delete(*tree.get_children())
        for tid, name, info in list_file_overrides():
            tree.insert("", "end", values=("file", tid, name, json.dumps(info)))
        for tid, name, val in list_template_value_overrides():
            # show scalar/list succinctly
            if isinstance(val, list):
                display = ", ".join(str(v) for v in val[:5]) + (" …" if len(val) > 5 else "")
            else:
                display = str(val)
            tree.insert("", "end", values=("value", tid, name, display))
    _refresh()

    def _edit(event=None):
        sel = tree.selection()
        if not sel: return
        item = tree.item(sel[0]); kind, tid, name, data = item['values']
        if kind != 'value':
            return  # only simple values editable
        dlg = tk.Toplevel(win)
        dlg.title(f"Edit Override: {tid}/{name}")
        tk.Label(dlg, text=f"Template {tid} – {name}").pack(padx=10,pady=(10,4))
        txt = tk.Text(dlg, width=60, height=6, wrap='word')
        txt.pack(padx=10, pady=4)
        txt.insert('1.0', data)
        def _ok():
            val = txt.get('1.0','end-1c').strip()
            set_template_value_override(int(tid), name, val)
            _refresh(); dlg.destroy()
        tk.Button(dlg, text='Save', command=_ok).pack(side='left', padx=10, pady=8)
        tk.Button(dlg, text='Cancel', command=dlg.destroy).pack(side='left', padx=4, pady=8)
        dlg.transient(win); dlg.grab_set(); txt.focus_set()
        dlg.bind('<Escape>', lambda e: (dlg.destroy(),'break'))
        dlg.bind('<Return>', lambda e: (_ok(),'break'))
    tree.bind('<Double-1>', _edit)

    btns = tk.Frame(win); btns.pack(pady=8)
    def do_remove():
        sel = tree.selection()
        if not sel: return
        item = tree.item(sel[0]); kind, tid, name, _ = item['values']
        removed = False
        if kind == 'file':
            removed = reset_single_file_override(int(tid), name)
        else:
            removed = reset_template_value_override(int(tid), name)
        if removed:
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


    # Build two browsers: one for shared (PROMPTS_DIR), and optionally one for local/private
    browser = create_browser_state()
    browser.build()
    # Try to build local/private browser if exists
    from ...config import PROMPTS_DIR as _PD
    local_dir = _PD.parent / "local"
    local_browser: Optional[BrowserState] = None
    try:
        if local_dir.exists() and local_dir.is_dir():
            local_browser = BrowserState(local_dir)
            local_browser.build()
    except Exception:
        local_browser = None

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
    def _edit_exclusions():
        try:
            import json
            from ...config import PROMPTS_DIR as _PD
        except Exception:
            return
        dlg = tk.Toplevel(root)
        dlg.title("Edit Global Exclusions (exclude_globals)")
        dlg.geometry("640x400")
        tk.Label(dlg, text="Enter template ID (numeric) or browse to load its metadata.").pack(anchor='w', padx=10, pady=(10,4))
        topf = tk.Frame(dlg); topf.pack(fill='x', padx=10)
        id_var = tk.StringVar()
        tk.Entry(topf, textvariable=id_var, width=10).pack(side='left')
        status_var = tk.StringVar(value="")
        tk.Label(dlg, textvariable=status_var, fg="#555").pack(anchor='w', padx=10, pady=(4,4))
        txt = tk.Text(dlg, wrap='word')
        txt.pack(fill='both', expand=True, padx=10, pady=6)
        txt.insert('1.0', "# Enter one global key per line to exclude for this template\n")
        current_path: list[Path] = []
        def _load():
            tid = id_var.get().strip()
            if not tid.isdigit():
                status_var.set("Template id must be numeric")
                return
            # search for file with matching id
            target = None
            for p in _PD.rglob("*.json"):
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    continue
                if data.get('id') == int(tid):
                    target = (p, data); break
            if not target:
                status_var.set("Template not found")
                return
            p, data = target
            current_path.clear(); current_path.append(p)
            meta = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
            raw_ex = meta.get('exclude_globals')
            lines = []
            if isinstance(raw_ex, (list, tuple)):
                lines = [str(x) for x in raw_ex]
            elif isinstance(raw_ex, str):
                if ',' in raw_ex:
                    lines = [s.strip() for s in raw_ex.split(',') if s.strip()]
                elif raw_ex.strip():
                    lines = [raw_ex.strip()]
            txt.delete('1.0','end')
            if lines:
                txt.insert('1.0', "\n".join(lines))
            status_var.set(f"Loaded {p.name}")
        def _save():
            if not current_path:
                status_var.set("Load a template first")
                return
            p = current_path[0]
            try:
                data = json.loads(p.read_text())
            except Exception as e:
                status_var.set(f"Read error: {e}")
                return
            meta = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
            if not isinstance(meta, dict):
                meta = {}; data['metadata'] = meta
            raw = [l.strip() for l in txt.get('1.0','end-1c').splitlines() if l.strip() and not l.strip().startswith('#')]
            if raw:
                meta['exclude_globals'] = raw
            else:
                meta.pop('exclude_globals', None)
            try:
                p.write_text(json.dumps(data, indent=2))
                status_var.set("Saved")
            except Exception as e:
                status_var.set(f"Write error: {e}")
        tk.Button(topf, text="Load", command=_load).pack(side='left', padx=6)
        tk.Button(topf, text="Save", command=_save).pack(side='left')
        tk.Button(topf, text="Close", command=dlg.destroy).pack(side='right')
        dlg.transient(root); dlg.grab_set(); dlg.focus_set()
    opt.add_command(label="Edit global exclusions", command=_edit_exclusions)
    opt.add_separator()
    opt.add_command(label="New template wizard", command=lambda: open_new_template_wizard())
    opt.add_separator()
    def _open_shortcuts_manager():
        _manage_shortcuts(root)
    opt.add_command(label="Manage shortcuts / renumber", command=_open_shortcuts_manager)
    menubar.add_cascade(label="Options", menu=opt)
    root.bind("<Control-Shift-R>", lambda e: (do_reset_refs(), "break"))
    root.bind("<Control-Shift-S>", lambda e: (_open_shortcuts_manager(), "break"))

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

    # Track which domain is active ('shared' or 'local')
    active_domain = 'shared'
    # flat_items holds ListingItem objects (may include headers/back) for display
    flat_items: List[ListingItem] = []

    def refresh(display_items: Optional[List[ListingItem]] = None):
        """Rebuild listbox based on active domain.

        Shared domain: show current shared directory. If at shared root and local exists,
        append a header then the top-level local styles (only root of local domain).
        Local domain: show only local browser items. Provide a '[..] Shared Root' back item
        when at local root to return to shared domain.
        """
        nonlocal selected_template, flat_items, active_domain
        listbox.delete(0, 'end')
        flat_items = []
        if active_domain == 'shared':
            base_items = display_items if display_items is not None else browser.items
            if base_items:
                flat_items.extend(base_items)
            if local_browser and browser.current == browser.root:
                header = ListingItem(type='header', display='--- Local (Private) * ---')
                flat_items.append(header)
                for it in local_browser.items:
                    if it.type == 'up':
                        continue
                    marker = ListingItem(type=it.type, path=it.path, template=it.template,
                                         display=(f"* {it.display}" if it.type == 'template' else it.display))
                    setattr(marker, 'origin', 'local')
                    flat_items.append(marker)
        else:  # local domain
            if local_browser:
                if local_browser.current == local_browser.root:
                    back = ListingItem(type='back', display='[..] Shared Root')
                    flat_items.append(back)
                for it in local_browser.items:
                    if local_browser.current == local_browser.root and it.type == 'up':
                        continue
                    marker = ListingItem(type=it.type, path=it.path, template=it.template,
                                         display=(f"* {it.display}" if it.type == 'template' else it.display))
                    setattr(marker, 'origin', 'local')
                    flat_items.append(marker)
        if not flat_items:
            flat_items.append(ListingItem(type='empty', display='<empty>'))
        for it in flat_items:
            listbox.insert('end', it.display)
        for idx, it in enumerate(flat_items):
            if it.type not in {'header','empty'}:
                listbox.selection_set(idx); listbox.see(idx); break
        selected_template = None
        preview_btn.config(state='disabled')
        if active_domain == 'shared':
            breadcrumb_var.set(browser.breadcrumb())
        else:
            if local_browser:
                if local_browser.current == local_browser.root:
                    breadcrumb_var.set('Local')
                else:
                    breadcrumb_var.set(f"Local/{local_browser.current.relative_to(local_browser.root)}")
            else:
                breadcrumb_var.set('Local')

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
        """Return items for the active domain (without any headers/back)."""
        q = search_var.get().strip()
        if active_domain == 'local' and local_browser:
            if not q:
                return local_browser.items
            if non_recursive_var.get():
                return local_browser.filter(q)
            return local_browser.search(q)
        # Shared domain
        if not q:
            return browser.items
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
        idx = sel[0]
        if idx < 0 or idx >= len(flat_items):
            return None
        it = flat_items[idx]
        if it.type in {'header','empty'}:
            return None
        return it

    def open_or_select():
        nonlocal selected_template, multi_selected, active_domain
        item = get_selected_item()
        if not item:
            return
        origin = getattr(item, 'origin', active_domain)
        # Back navigation
        if item.type == 'back':
            active_domain = 'shared'
            refresh(current_items()); return
        if item.type in {'up','dir'}:
            if origin == 'local' and local_browser:
                # Switch to local domain if coming from shared root listing
                if active_domain != 'local':
                    active_domain = 'local'
                # Navigate inside local
                # Find corresponding listing item in local_browser to use enter logic
                if item.type == 'up':
                    for it2 in local_browser.items:
                        if it2.type == 'up':
                            local_browser.enter(it2); break
                else:
                    # directory
                    for it2 in local_browser.items:
                        if it2.path == item.path:
                            local_browser.enter(it2); break
                refresh(current_items()); return
            else:
                # Shared domain navigation
                active_domain = 'shared'
                # Similar search within browser items
                if item.type == 'up':
                    for it2 in browser.items:
                        if it2.type == 'up':
                            browser.enter(it2); break
                else:
                    for it2 in browser.items:
                        if it2.path == item.path:
                            browser.enter(it2); break
                refresh(current_items()); return
        if item.type == 'template' and item.template:
            if multi_var.get():
                tmpl_dict = item.template.data
                if tmpl_dict in multi_selected:
                    multi_selected.remove(tmpl_dict)
                else:
                    multi_selected.append(tmpl_dict)
                idx = listbox.curselection()[0]
                disp = item.display
                if disp.startswith('* '):
                    disp = disp[2:]
                else:
                    disp = '* ' + disp
                listbox.delete(idx); listbox.insert(idx, disp); listbox.selection_set(idx)
            else:
                selected_template = item.template.data; root.destroy()

    # --- Shortcut key handling (numeric keys mapped to specific templates) ---
    _shortcut_mapping = load_shortcuts()  # key -> relative path from PROMPTS_DIR/style? actually store relative to PROMPTS_DIR root

    def _resolve_shortcut(key: str):
        rel = _shortcut_mapping.get(key)
        if not rel:
            return None
        # Path may include style folder already
        try:
            from ...config import PROMPTS_DIR as _PD
            p = _PD / rel
            if p.exists():
                from ...renderer import load_template as _LT
                return _LT(p)
        except Exception:
            return None
        return None

    def _on_digit(event):
        if event.char and event.char.isdigit():
            tmpl = _resolve_shortcut(event.char)
            if tmpl:
                nonlocal selected_template
                selected_template = tmpl
                root.destroy()
                return "break"
        return None
    # Bind 0-9 keys globally (without modifiers) when focus is in list or search
    for d in "0123456789":
        root.bind(d, _on_digit)
        listbox.bind(d, _on_digit)
        search_entry.bind(d, _on_digit)

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
        nonlocal active_domain
        if active_domain == 'local' and local_browser:
            if local_browser.current != local_browser.root:
                for it in local_browser.items:
                    if it.type == 'up':
                        local_browser.enter(it); refresh(current_items()); break
                return 'break'
            else:
                active_domain = 'shared'; refresh(current_items()); return 'break'
        if browser.current != browser.root:
            for it in browser.items:
                if it.type == 'up':
                    browser.enter(it); refresh(current_items()); break
            return 'break'
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
        size = len(flat_items)
        if size == 0:
            return
        sel = listbox.curselection()
        if not sel:
            idx = 0 if delta >= 0 else size - 1
        else:
            idx = sel[0] + delta
        idx = max(0, min(size - 1, idx))
        # Skip headers
        step = 1 if delta >= 0 else -1
        while 0 <= idx < size and flat_items[idx].type == 'header':
            idx += step
        idx = max(0, min(size - 1, idx))
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

# --- Shortcuts manager dialog ----------------------------------------------

def _manage_shortcuts(root: tk.Tk):  # pragma: no cover - GUI only
    win = tk.Toplevel(root)
    win.title("Manage Template Shortcuts")
    win.geometry("700x420")
    win.resizable(True, True)
    frame = tk.Frame(win, padx=12, pady=12); frame.pack(fill="both", expand=True)
    hint = tk.Label(frame, text="Assign single-digit keys to frequently used templates. Double-click a row to set/edit key. Use Renumber to rename files so IDs match chosen digits.", wraplength=660, justify="left", fg="#444")
    hint.pack(anchor="w", pady=(0,8))
    cols = ("key","rel","title","id")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    widths = {"key":60, "rel":300, "title":200, "id":60}
    for c in cols:
        tree.heading(c, text=c.upper())
        tree.column(c, width=widths[c], anchor="w")
    vsb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")

    mapping = load_shortcuts()  # key -> rel path

    # Gather templates for listing
    from ...config import PROMPTS_DIR as _PD
    from ...renderer import load_template as _LT
    templates: list[tuple[str, Path, dict]] = []  # (rel, path, data)
    for p in sorted(_PD.rglob("*.json")):
        try:
            data = _LT(p)
            if "template" in data:
                rel = str(p.relative_to(_PD))
                templates.append((rel, p, data))
        except Exception:
            continue

    def _refresh_tree():
        tree.delete(*tree.get_children())
        for rel, path, data in templates:
            key = next((k for k,v in mapping.items() if v == rel), "")
            tree.insert("", "end", values=(key, rel, data.get("title",""), data.get("id","")))
    _refresh_tree()

    def _edit_key(event=None):
        sel = tree.selection()
        if not sel: return
        item = tree.item(sel[0])
        cur_key, rel, *_ = item["values"]
        def _apply(new_key: str):
            new_key = new_key.strip()
            # Remove existing mapping for this rel or key
            for k in list(mapping.keys()):
                if mapping[k] == rel or k == new_key:
                    mapping.pop(k, None)
            if new_key:
                mapping[new_key] = rel
            save_shortcuts(mapping)
            _refresh_tree()
        # Simple prompt dialog
        dlg = tk.Toplevel(win); dlg.title("Set Key")
        tk.Label(dlg, text=f"Template: {rel}\nCurrent key: {cur_key or '(none)'}\nEnter new single-digit key (blank to clear):").pack(padx=12,pady=12)
        var = tk.StringVar(value=cur_key)
        ent = tk.Entry(dlg, textvariable=var); ent.pack(padx=12, pady=(0,12))
        def _ok():
            val = var.get()
            if val and (len(val)!=1 or not val.isdigit()):
                messagebox.showerror("Validation", "Key must be a single digit 0-9 or blank")
                return
            _apply(val)
            dlg.destroy()
        tk.Button(dlg, text="OK", command=_ok).pack(side="left", padx=12, pady=8)
        tk.Button(dlg, text="Cancel", command=dlg.destroy).pack(side="left", padx=4, pady=8)
        ent.focus_set(); ent.select_range(0,'end')
        dlg.bind('<Return>', lambda e: (_ok(), 'break'))
        dlg.bind('<Escape>', lambda e: (dlg.destroy(), 'break'))
        dlg.transient(win); dlg.grab_set()

    tree.bind('<Double-1>', _edit_key)

    btns = tk.Frame(frame); btns.pack(fill="x", pady=8)
    def _do_delete():
        sel = tree.selection();
        if not sel: return
        item = tree.item(sel[0]); cur_key, rel, *_ = item['values']
        # remove mapping
        for k in list(mapping.keys()):
            if mapping[k] == rel:
                mapping.pop(k, None)
        save_shortcuts(mapping); _refresh_tree()
    def _do_renumber():
        # Apply renumbering according to numeric shortcut keys
        try:
            renumber_templates(mapping)
            messagebox.showinfo("Renumber", "Renumbering complete. Close and reopen selector to see changes.")
        except Exception as e:
            messagebox.showerror("Renumber", f"Failed: {e}")
    tk.Button(btns, text="Edit Key", command=_edit_key).pack(side="left", padx=4)
    tk.Button(btns, text="Clear Key", command=_do_delete).pack(side="left", padx=4)
    tk.Button(btns, text="Renumber", command=_do_renumber).pack(side="left", padx=10)
    tk.Button(btns, text="Close", command=win.destroy).pack(side="right", padx=4)

    win.bind('<Escape>', lambda e: (win.destroy(), 'break'))
    win.transient(root); win.grab_set()
    win.focus_set()

__all__ = ["open_template_selector"]
