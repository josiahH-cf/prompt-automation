"""Shared Options menu construction for Prompt Automation GUI.

Centralizes menu item definitions so single-window and legacy selector views
stay in sync. Keeps logic lightweight and defensive (GUI only; failures are
logged but not raised).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

from ..errorlog import get_logger
from .constants import INFO_CLOSE_SAVE
from ..variables import storage as _storage
from ..theme import resolve as _theme_resolve, model as _theme_model, apply as _theme_apply
from ..features import is_hierarchy_enabled as _hierarchy_enabled, set_user_hierarchy_preference as _set_hierarchy
from ..history import list_history as _list_history, is_enabled as _history_enabled

_log = get_logger(__name__)


def configure_options_menu(
    root,
    selector_view_module,
    selector_service,
    *,
    include_global_reference: bool = True,
    include_manage_templates: bool = True,
    extra_items: Callable[[Any, Any], None] | None = None,
) -> Dict[str, Callable[[], None]]:  # pragma: no cover - GUI heavy
    """(Re)build the Options menu and attach to ``root``.

    Returns mapping of accelerator sequences to callables so caller can bind.
    """
    import tkinter as tk

    try:
        menubar = root.nametowidget(root['menu']) if root and root['menu'] else tk.Menu(root)
    except Exception:  # pragma: no cover - best effort
        menubar = tk.Menu(root)

    # Replace entire menubar to avoid duplicate cascades
    new_menubar = tk.Menu(root)
    opt = tk.Menu(new_menubar, tearoff=0)
    accelerators: Dict[str, Callable[[], None]] = {}

    # Manual Espanso sync button (calls same orchestrator as CLI/colon command)
    def _sync_espanso():  # pragma: no cover - GUI side effects
        import threading
        from tkinter import messagebox
        try:
            def _run_sync():
                try:
                    # Use CLI module to reuse argument parsing and env
                    from ..espanso_sync import main as _sync_main
                    # If user configured a repo root in Settings, pass it explicitly
                    # Prefer Settings override; fall back to environment file
                    try:
                        repo_root = _storage.get_setting_espanso_repo_root()
                    except Exception:
                        repo_root = None
                    if not repo_root:
                        try:
                            env_file = Path.home() / ".prompt-automation" / "environment"
                            if env_file.exists():
                                for line in env_file.read_text(encoding="utf-8").splitlines():
                                    if line.startswith("PROMPT_AUTOMATION_REPO="):
                                        repo_root = line.split("=", 1)[1].strip()
                                        break
                        except Exception:
                            pass
                    argv = ["--repo", repo_root] if repo_root else []
                    # Respect env flags; do not hardcode branch or skip-install here
                    _sync_main(argv)
                    messagebox.showinfo("Espanso", "Sync complete. Espanso restarted.")
                except SystemExit as e:
                    code = getattr(e, 'code', 1)
                    if code:
                        messagebox.showerror("Espanso", f"Sync failed (exit {code}). See logs.")
                    else:
                        messagebox.showinfo("Espanso", "Sync complete.")
                except Exception as e:
                    messagebox.showerror("Espanso", f"Sync failed: {e}")
            threading.Thread(target=_run_sync, daemon=True).start()
        except Exception as e:
            _log.error("Espanso sync action failed: %s", e)
    opt.add_command(label="Sync Espanso?", command=_sync_espanso)

    # Reset reference files (with confirmation + undo support)
    def _reset_refs():
        try:
            from tkinter import messagebox
            def _confirm():
                return messagebox.askyesno(
                    "Reset Overrides",
                    "This will clear stored file/skip overrides. You can undo via\n"
                    "Options → Undo last reset. Proceed?",
                )
            changed = selector_service.reset_file_overrides_with_backup(_confirm)
            if changed:
                messagebox.showinfo("Reset", "Overrides cleared. Use Options → Undo last reset to restore.")
            else:
                messagebox.showinfo("Reset", "No changes made.")
        except Exception as e:
            _log.error("Reset refs failed: %s", e)
    opt.add_command(label="Reset reference files", command=_reset_refs, accelerator="Ctrl+Shift+R")
    accelerators['<Control-Shift-R>'] = _reset_refs

    def _undo_reset():
        try:
            from tkinter import messagebox
            if selector_service.undo_last_reset_file_overrides():
                messagebox.showinfo("Undo", "Overrides restored from last reset snapshot.")
            else:
                messagebox.showinfo("Undo", "No reset snapshot available.")
        except Exception as e:
            _log.error("Undo reset failed: %s", e)
    opt.add_command(label="Undo last reset", command=_undo_reset, accelerator="Ctrl+Shift+U")
    accelerators['<Control-Shift-U>'] = _undo_reset

    # Manage overrides
    def _manage_overrides():
        try:
            selector_view_module._manage_overrides(root, selector_service)  # type: ignore[attr-defined]
        except Exception as e:
            _log.error("Manage overrides failed: %s", e)
    opt.add_command(label="Manage overrides", command=_manage_overrides)

    # Edit global exclusions
    def _edit_exclusions():
        try:
            selector_view_module._edit_exclusions(root, selector_service)  # type: ignore[attr-defined]
        except AttributeError:
            _log.warning("_edit_exclusions not available in selector view module")
        except Exception as e:
            _log.error("Edit exclusions failed: %s", e)
    opt.add_command(label="Edit global exclusions", command=_edit_exclusions)
    opt.add_separator()

    # Auto-copy on review toggle (copies rendered output immediately when entering review stage)
    def _toggle_auto_copy():
        try:
            current = _storage.get_setting_auto_copy_review()
            _storage.set_setting_auto_copy_review(not current)
            # If enabling while currently in review, perform immediate copy
            try:
                ctrl = getattr(root, '_controller', None)
                if ctrl and getattr(ctrl, '_stage', None) == 'review' and not current:
                    view = getattr(ctrl, '_current_view', None)
                    if view and hasattr(view, 'copy'):
                        try: view.copy()  # type: ignore[attr-defined]
                        except Exception: pass
                    # Rebuild menu to refresh labels
                    if hasattr(ctrl, '_rebuild_menu'):
                        try: ctrl._rebuild_menu()
                        except Exception: pass
            except Exception:
                pass
        except Exception as e:
            _log.error("toggle auto_copy_review failed: %s", e)
    # Present current state in label for quick visibility
    try:
        if _storage.get_setting_auto_copy_review():
            ac_label = "Disable auto-copy on review"
        else:
            ac_label = "Enable auto-copy on review"
    except Exception:
        ac_label = "Toggle auto-copy on review"
    opt.add_command(label=ac_label, command=_toggle_auto_copy)
    # Per-template toggle appears only when a template is active in review stage (controller injects Stage label afterwards)
    try:
        # Controller sets root._controller with template attr; best-effort introspection
        ctrl = getattr(root, '_controller', None)
        tmpl = getattr(ctrl, 'template', None)
        tid = tmpl.get('id') if isinstance(tmpl, dict) else None
        if tid is not None:
            if _storage.is_auto_copy_enabled_for_template(tid):
                tlabel = 'Disable auto-copy for this template'
            else:
                tlabel = 'Enable auto-copy for this template'
            def _toggle_template():
                try:
                    dis = _storage.is_auto_copy_enabled_for_template(tid)
                    # Passing current state disables if enabled, enables if disabled
                    _storage.set_template_auto_copy_disabled(tid, dis)
                    # If enabling now (previously disabled), perform immediate copy
                    if dis is False:  # it was disabled, now being enabled
                        try:
                            ctrl2 = getattr(root, '_controller', None)
                            view2 = getattr(ctrl2, '_current_view', None)
                            if view2 and hasattr(view2, 'copy'):
                                view2.copy()  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Refresh menu labels
                    ctrl3 = getattr(root, '_controller', None)
                    if ctrl3 and hasattr(ctrl3, '_rebuild_menu'):
                        try: ctrl3._rebuild_menu()
                        except Exception: pass
                except Exception as e:
                    _log.error('toggle per-template auto-copy failed: %s', e)
            opt.add_command(label=tlabel, command=_toggle_template)
    except Exception:
        pass

    # New template wizard
    def _open_wizard():
        try:
            from .new_template_wizard import open_new_template_wizard
            open_new_template_wizard()
        except Exception as e:
            _log.error("Template wizard failed: %s", e)
    opt.add_command(label="New template wizard", command=_open_wizard)

    # Manage templates dialog
    if include_manage_templates:
        def _open_manage_templates():  # pragma: no cover
            import tkinter as tk
            from tkinter import messagebox
            from ..menus import PROMPTS_DIR
            import json
            win = tk.Toplevel(root)
            win.title("Manage Templates")
            win.geometry("760x500")
            win.resizable(True, True)
            cols = ("id","title","rel")
            tree = tk.Treeview(win, columns=cols, show="headings")
            widths = {"id":60, "title":230, "rel":420}
            for c in cols:
                tree.heading(c, text=c.upper()); tree.column(c, width=widths[c], anchor='w')
            vs = tk.Scrollbar(win, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=vs.set)
            tree.pack(side='left', fill='both', expand=True); vs.pack(side='right', fill='y')
            def _load():
                tree.delete(*tree.get_children())
                for p in sorted(PROMPTS_DIR.rglob('*.json')):
                    try: data = json.loads(p.read_text())
                    except Exception: continue
                    tree.insert('', 'end', values=(data.get('id',''), data.get('title', p.stem), str(p.relative_to(PROMPTS_DIR))))
            def _preview(event=None):
                sel = tree.selection();
                if not sel: return
                rel = tree.item(sel[0])['values'][2]
                path = PROMPTS_DIR / rel
                try: raw = path.read_text()
                except Exception as e:
                    messagebox.showerror('Preview', f'Unable: {e}'); return
                pv = tk.Toplevel(win); pv.title(f"Template: {rel}"); pv.geometry('700x600')
                from .fonts import get_display_font
                txt = tk.Text(pv, wrap='word', font=get_display_font(master=pv)); txt.pack(fill='both', expand=True)
                txt.insert('1.0', raw); txt.config(state='disabled')
                pv.bind('<Escape>', lambda e: (pv.destroy(), 'break'))
            def _delete():
                sel = tree.selection();
                if not sel: return
                rel = tree.item(sel[0])['values'][2]
                path = PROMPTS_DIR / rel
                from tkinter import messagebox
                if not messagebox.askyesno('Delete', f'Delete template {rel}?'): return
                try: path.unlink()
                except Exception as e: messagebox.showerror('Delete', f'Failed: {e}'); return
                _load()
            def _new():
                try:
                    from .new_template_wizard import open_new_template_wizard
                    open_new_template_wizard(); _load()
                except Exception as e: messagebox.showerror('Wizard', f'Failed: {e}')
            tree.bind('<Double-1>', _preview)
            btns = tk.Frame(win, pady=6); btns.pack(fill='x')
            tk.Button(btns, text='New', command=_new).pack(side='left')
            tk.Button(btns, text='Delete', command=_delete).pack(side='left', padx=(6,0))
            tk.Button(btns, text='Refresh', command=_load).pack(side='left', padx=(6,0))
            tk.Button(btns, text='Close', command=win.destroy).pack(side='right')
            win.bind('<Escape>', lambda e: (win.destroy(),'break'))
            win.bind('<Control-Return>', lambda e: (win.destroy(),'break'))
            _load()
        opt.add_command(label='Manage templates', command=_open_manage_templates)
        opt.add_separator()

    # Recent history panel (lightweight list with copy)
    def _open_recent_history():  # pragma: no cover - GUI heavy
        import tkinter as tk
        from tkinter import messagebox
        from .error_dialogs import safe_copy_to_clipboard as _safe_copy
        from ..paste import copy_to_clipboard as _legacy_copy
        try:
            if not _history_enabled():
                messagebox.showinfo("Recent history", "History is disabled (see settings or env)")
                return
            entries = _list_history()
            win = tk.Toplevel(root)
            win.title("Recent History")
            win.geometry("900x520")
            win.resizable(True, True)
            import tkinter.ttk as ttk
            cols = ("when", "template", "preview")
            tree = ttk.Treeview(win, columns=cols, show="headings")
            tree.heading("when", text="When (UTC)"); tree.column("when", width=170, anchor='w')
            tree.heading("template", text="Template"); tree.column("template", width=240, anchor='w')
            tree.heading("preview", text="Output Preview"); tree.column("preview", width=440, anchor='w')
            vs = tk.Scrollbar(win, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=vs.set)
            tree.pack(side='top', fill='both', expand=True)
            vs.pack(side='right', fill='y')
            # Preview area
            txt = tk.Text(win, wrap='word', height=10)
            txt.pack(side='bottom', fill='x')
            txt.config(state='disabled')

            def _truncate(s: str, n: int = 85) -> str:
                s = s.replace('\n', ' ').strip()
                return s if len(s) <= n else s[: n - 1] + '…'

            def _load_rows():
                tree.delete(*tree.get_children())
                for e in entries:
                    prev = _truncate((e.get('output') or e.get('rendered') or ''))
                    tree.insert('', 'end', iid=e.get('entry_id'), values=(e.get('ts'), e.get('title') or '', prev))

            def _on_select(event=None):
                sel = tree.selection()
                if not sel:
                    return
                eid = sel[0]
                entry = next((x for x in entries if x.get('entry_id') == eid), None)
                if not entry:
                    return
                try:
                    txt.config(state='normal'); txt.delete('1.0','end')
                    full = entry.get('output') or entry.get('rendered') or ''
                    txt.insert('1.0', full)
                finally:
                    txt.config(state='disabled')

            def _copy_selected():
                sel = tree.selection()
                if not sel:
                    messagebox.showinfo('Copy', 'Select an entry to copy.')
                    return
                eid = sel[0]
                entry = next((x for x in entries if x.get('entry_id') == eid), None)
                if not entry:
                    return
                payload = entry.get('output') or entry.get('rendered') or ''
                if not payload.strip():
                    messagebox.showinfo('Copy', 'Nothing to copy for this entry.')
                    return
                if _safe_copy(payload) or _legacy_copy(payload):
                    messagebox.showinfo('Copy', 'Copied to clipboard.')
                else:
                    messagebox.showerror('Copy', 'Copy failed; see logs.')

            btnbar = tk.Frame(win); btnbar.pack(side='bottom', fill='x')
            tk.Button(btnbar, text='Copy', command=_copy_selected).pack(side='right', padx=6, pady=6)
            tk.Button(btnbar, text='Close', command=win.destroy).pack(side='right', padx=6, pady=6)
            tree.bind('<<TreeviewSelect>>', _on_select)
            _load_rows()
            # Auto-select first row if present
            items = tree.get_children()
            if items:
                tree.selection_set(items[0]); _on_select()
        except Exception as e:
            _log.error('Recent history UI failed: %s', e)

    opt.add_command(label='Recent history', command=_open_recent_history)
    opt.add_separator()

    # Shortcut manager
    def _open_shortcut_manager():
        try:
            selector_view_module._manage_shortcuts(root, selector_service)  # type: ignore[attr-defined]
        except Exception as e:
            _log.error("Shortcut manager failed: %s", e)
            try:
                from tkinter import messagebox
                messagebox.showerror("Shortcut Manager", f"Failed to open: {e}")
            except Exception:
                pass
    opt.add_command(label="Manage shortcuts / renumber", command=_open_shortcut_manager, accelerator="Ctrl+Shift+S")
    accelerators['<Control-Shift-S>'] = _open_shortcut_manager

    # Hierarchical templates status + toggle (mimic theme behavior)
    try:
        current_h = _hierarchy_enabled()
        opt.add_separator()
        opt.add_command(label=f"Hierarchy: {'on' if current_h else 'off'}", state='disabled')
    except Exception:
        pass

    def _toggle_hierarchy_menu():
        try:
            new_state = not _hierarchy_enabled()
            _set_hierarchy(new_state)
            # Surface a visible refresh hook so the label updates
            try:
                ctrl = getattr(root, '_controller', None)
                if ctrl and hasattr(ctrl, '_rebuild_menu'):
                    ctrl._rebuild_menu()
            except Exception:
                pass
        except Exception as e:
            _log.error("Toggle hierarchy failed: %s", e)
    opt.add_command(label="Toggle Hierarchical Templates (Ctrl+Alt+H)", command=_toggle_hierarchy_menu)
    accelerators['<Control-Alt-h>'] = _toggle_hierarchy_menu

    # Theme status + toggle (appears for both selector and stages)
    try:
        resolver = _theme_resolve.ThemeResolver(_theme_resolve.get_registry())
        current_name = resolver.resolve()
        opt.add_separator()
        opt.add_command(label=f"Theme: {current_name}", state='disabled')
    except Exception:
        pass

    # Toggle
    def _toggle_theme_menu():
        try:
            resolver = _theme_resolve.ThemeResolver(_theme_resolve.get_registry())
            new_name = resolver.toggle()
            tokens = _theme_model.get_theme(new_name)
            _theme_apply.apply_to_root(root, tokens, initial=False, enable=_theme_resolve.get_enable_theming())
            # Refresh menu so the Theme: label updates
            try:
                ctrl = getattr(root, '_controller', None)
                if ctrl and hasattr(ctrl, '_rebuild_menu'):
                    ctrl._rebuild_menu()
            except Exception:
                pass
        except Exception as e:
            _log.error("Toggle theme failed: %s", e)
    opt.add_separator()
    opt.add_command(label="Toggle Theme (Ctrl+Alt+D)", command=_toggle_theme_menu)
    accelerators['<Control-Alt-d>'] = _toggle_theme_menu

    # Global reference file manager
    if include_global_reference:
        from .collector.persistence import reset_global_reference_file, get_global_reference_file
        from ..renderer import read_file_safe
        def _open_global_reference_manager():  # pragma: no cover
            import tkinter as tk
            from tkinter import filedialog
            win = tk.Toplevel(root)
            win.title("Global Reference File")
            win.geometry('900x680')
            path_var = tk.StringVar(value=get_global_reference_file() or "")
            top = tk.Frame(win, padx=10, pady=8); top.pack(fill='x')
            tk.Label(top, text='Path:').pack(side='left')
            ent = tk.Entry(top, textvariable=path_var, width=58); ent.pack(side='left', fill='x', expand=True, padx=(4,4))
            def browse():
                fname = filedialog.askopenfilename(parent=win)
                if fname: path_var.set(fname); _render()
            tk.Button(top, text='Browse', command=browse).pack(side='left')
            raw_mode = {'value': False}
            toggle_btn = tk.Button(top, text='Raw', width=5); toggle_btn.pack(side='left', padx=(6,0))
            copy_btn = tk.Button(top, text='Copy', width=6); copy_btn.pack(side='left', padx=(6,0))
            info = tk.Label(top, text=INFO_CLOSE_SAVE, fg='#555'); info.pack(side='left', padx=(12,0))
            frame = tk.Frame(win); frame.pack(fill='both', expand=True)
            txt = tk.Text(frame, wrap='word'); vs = tk.Scrollbar(frame, orient='vertical', command=txt.yview)
            txt.configure(yscrollcommand=vs.set); txt.pack(side='left', fill='both', expand=True); vs.pack(side='right', fill='y')
            SIZE_LIMIT = 200*1024
            def _apply_md(widget, content: str):
                import re
                lines = content.splitlines(); cursor=1; in_code=False; code_start=None
                for ln in lines:
                    idx=f'{cursor}.0'
                    if ln.strip().startswith('```'):
                        if not in_code:
                            in_code=True; code_start=idx
                        else:
                            try: widget.tag_add('codeblock', code_start, f'{cursor}.0 lineend')
                            except Exception: pass
                            in_code=False; code_start=None
                    cursor+=1
                full = widget.get('1.0','end-1c')
                for m in re.finditer(r'\*\*(.+?)\*\*', full): widget.tag_add('bold', f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")
            def _render():
                txt.config(state='normal'); txt.delete('1.0','end')
                p = Path(path_var.get()).expanduser()
                if not p.exists(): txt.insert('1.0', '(No file selected)'); txt.config(state='disabled'); return
                try: content = read_file_safe(str(p)).replace('\r','')
                except Exception: content = '(Error reading file)'
                if len(content.encode('utf-8'))>SIZE_LIMIT:
                    content = '*** File truncated (too large) ***\n\n' + content[:SIZE_LIMIT//2]
                if not raw_mode['value']:
                    new=[]; in_code=False
                    for ln in content.splitlines():
                        if ln.strip().startswith('```'):
                            in_code = not in_code; new.append(ln); continue
                        if not in_code and ln.startswith('- '): ln = '• ' + ln[2:]
                        new.append(ln)
                    content_to_insert='\n'.join(new)
                else:
                    content_to_insert=content
                txt.insert('1.0', content_to_insert)
                if not raw_mode['value']:
                    try: _apply_md(txt, content_to_insert)
                    except Exception: pass
                txt.config(state='disabled')
            def _toggle():
                raw_mode['value'] = not raw_mode['value']; toggle_btn.configure(text=('MD' if raw_mode['value'] else 'Raw')); _render()
            def _copy():
                try: root.clipboard_clear(); root.clipboard_append(txt.get('1.0','end-1c'))
                except Exception: pass
            def _close():
                try:
                    ov = selector_service.load_overrides(); gfiles = ov.setdefault('global_files', {})
                    pv = path_var.get().strip()
                    if pv: gfiles['reference_file'] = pv
                    else: gfiles.pop('reference_file', None)
                    selector_service.save_overrides(ov)
                except Exception: pass
                win.destroy(); return 'break'
            toggle_btn.configure(command=_toggle)
            copy_btn.configure(command=_copy)
            win.bind('<Control-Return>', lambda e: _close())
            win.bind('<Escape>', lambda e: _close())
            win.protocol('WM_DELETE_WINDOW', lambda: _close())
            _render(); ent.focus_set()
        # Wrap global reference manager with visible error surfacing
        def _safe_open_global():
            try:
                _open_global_reference_manager()
            except Exception as e:
                try:
                    from tkinter import messagebox
                    messagebox.showerror('Global Reference', f'Failed: {e}')
                except Exception:
                    pass
        opt.add_command(label='Global reference file', command=_safe_open_global)
        def _reset_global():
            try: reset_global_reference_file()
            except Exception: pass
        opt.add_command(label='Reset global reference file', command=_reset_global)

    if extra_items:
        try:
            extra_items(opt, new_menubar)
        except Exception as e:  # pragma: no cover
            _log.error("extra_items hook failed: %s", e)

    new_menubar.add_cascade(label="Options", menu=opt)
    root.config(menu=new_menubar)
    return accelerators


__all__ = ["configure_options_menu"]
