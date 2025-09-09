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

    # Helper to present a log window with filter and copy controls
    def _present_log_window(log_text: str, ok: bool):  # pragma: no cover - GUI
        try:
            import tkinter as tk
            from tkinter import scrolledtext
            import json as _json2
            # Prepare filtered view (warn/error only) by parsing JSON lines
            lines = log_text.splitlines()
            header = lines[0] if lines else ""
            json_lines = lines[1:]
            filtered = []
            for ln in json_lines:
                try:
                    o = _json2.loads(ln)
                    s = str(o.get('status', '')).lower()
                    if s in ('warn', 'error'):
                        filtered.append(ln)
                except Exception:
                    # Non-JSON lines are omitted in filtered view
                    pass
            full_text = log_text
            filtered_text = (header + "\n\n" + "\n".join(filtered)) if filtered else full_text
            win = tk.Toplevel(root)
            win.title("Espanso Sync Log" + (" — OK" if ok else " — Issues"))
            win.geometry("720x480")
            # Controls frame
            top = tk.Frame(win)
            top.pack(fill='x')
            show_all_var = tk.BooleanVar(value=False)
            def _toggle():
                try:
                    txt.configure(state='normal')
                    txt.delete('1.0', 'end')
                    txt.insert('1.0', full_text if show_all_var.get() else filtered_text)
                    txt.mark_set("insert", "1.0")
                    txt.configure(state='disabled')
                except Exception:
                    pass
            cb = tk.Checkbutton(top, text='Show all logs', variable=show_all_var, command=_toggle)
            cb.pack(side='left', padx=6, pady=4)
            def _copy():
                try:
                    win.clipboard_clear()
                    win.clipboard_append(full_text if show_all_var.get() else filtered_text)
                except Exception:
                    pass
            copy_btn = tk.Button(top, text='Copy', command=_copy)
            copy_btn.pack(side='left', padx=6)
            # Log area
            txt = scrolledtext.ScrolledText(win, wrap='none')
            txt.pack(fill='both', expand=True)
            try:
                txt.insert('1.0', filtered_text)
                txt.mark_set("insert", "1.0")
                txt.configure(state='disabled')
            except Exception:
                pass
            # Close button
            btn = tk.Button(win, text=INFO_CLOSE_SAVE, command=win.destroy)
            btn.pack(side='bottom')
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Espanso", f"Sync finished, but log window failed: {e}")

    # Manual Espanso sync button (calls same orchestrator as CLI/colon command)
    def _sync_espanso():  # pragma: no cover - GUI side effects
        import threading
        import io
        import json as _json
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox
        try:

            def _run_sync():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                try:
                    from ..espanso_sync import main as _sync_main
                    from .. import espanso_sync as _esp
                    # Resolve repo root if configured
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
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        _sync_main(argv)
                    # Parse JSON lines to compute summary
                    warn_cnt = 0; err_cnt = 0
                    last_step = ""
                    for line in buf_out.getvalue().splitlines():
                        try:
                            o = _json.loads(line)
                            s = str(o.get('status', '')).lower()
                            if s == 'warn': warn_cnt += 1
                            if s == 'error': err_cnt += 1
                            if 'step' in o: last_step = str(o['step'])
                        except Exception:
                            continue
                    ok = (err_cnt == 0)
                    header = f"Summary: {'OK' if ok else 'Issues'} | warnings={warn_cnt} errors={err_cnt} last_step={last_step}\n\n"
                    log_text = header + buf_out.getvalue()
                except SystemExit as e:
                    code = getattr(e, 'code', 1)
                    log_text = f"Summary: Exit {code} (SystemExit)\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                except Exception as e:
                    log_text = f"Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    # Present log in UI thread
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        # Fallback to messagebox if scheduling fails
                        messagebox.showinfo("Espanso", log_text[:2000])
                # Windows-only advisory if local base.yml exists (can cause duplicates)
                try:
                    import platform, os
                    from pathlib import Path as _P
                    if platform.system() == "Windows":
                        appdata = os.environ.get("APPDATA")
                        if appdata:
                            by = _P(appdata) / "espanso" / "match" / "base.yml"
                            if by.exists():
                                messagebox.showwarning("Espanso",
                                    f"Local base.yml detected at:\n{by}\n\nIt may cause duplicate triggers.\nUse: scripts/espanso-windows.ps1 -DisableLocalBase")
                except Exception:
                    pass
            threading.Thread(target=_run_sync, daemon=True).start()
        except Exception as e:
            _log.error("Espanso sync action failed: %s", e)
    # Group all Espanso actions into a submenu to declutter the main menu
    esp_menu = tk.Menu(opt, tearoff=0)
    # Allow configuring a default HTTPS repo URL used by installers
    def _set_default_repo_url():  # pragma: no cover - GUI
        from tkinter import simpledialog, messagebox
        try:
            from ..variables import storage as _stg
            cur = _stg.get_setting_espanso_repo_url() or "https://github.com/<owner>/<repo>.git"
            url = simpledialog.askstring("Espanso Repo URL", "Default HTTPS Git URL for installs:", initialvalue=cur, parent=root)
            if url is None:
                return
            url = url.strip()
            if not url:
                _stg.set_setting_espanso_repo_url(None)
                messagebox.showinfo("Espanso", "Cleared default repo URL.")
                return
            _stg.set_setting_espanso_repo_url(url)
            messagebox.showinfo("Espanso", f"Saved default repo URL:\n{url}")
        except Exception as e:
            _log.error("set default repo url failed: %s", e)
    esp_menu.add_command(label="Set Default Repo URL...", command=_set_default_repo_url)
    esp_menu.add_separator()
    esp_menu.add_command(label="Sync Espanso?", command=_sync_espanso)

    # Deep Clean + Sync (Windows-friendly): backs up and removes all local user matches then syncs
    def _deep_clean_and_sync():  # pragma: no cover - GUI side effects
        import threading
        import io
        from contextlib import redirect_stdout, redirect_stderr
        import json as _json
        from tkinter import messagebox
        try:
            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                try:
                    # Deep clean
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        from ..cli.espanso_cmds import clean_env
                        clean_env(deep=True, list_only=False)
                    # Sync (reuse repo detection as in _sync_espanso)
                    from ..espanso_sync import main as _sync_main
                    # Optional repo root override
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
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        _sync_main(argv)
                    # Evaluate summary from sync portion
                    warn_cnt = 0; err_cnt = 0; last_step = ""
                    for ln in buf_out.getvalue().splitlines():
                        try:
                            o = _json.loads(ln)
                            s = str(o.get('status', '')).lower()
                            if s == 'warn': warn_cnt += 1
                            if s == 'error': err_cnt += 1
                            if 'step' in o: last_step = str(o['step'])
                        except Exception:
                            continue
                    ok = (err_cnt == 0)
                    header = f"Deep Clean + Sync Summary: {'OK' if ok else 'Issues'} | warnings={warn_cnt} errors={err_cnt} last_step={last_step}\n\n"
                    log_text = header + buf_out.getvalue()
                except SystemExit as e:
                    code = getattr(e, 'code', 1)
                    log_text = f"Deep Clean + Sync Summary: Exit {code} (SystemExit)\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                except Exception as e:
                    log_text = f"Deep Clean + Sync Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Deep clean + sync failed: %s", e)
    esp_menu.add_command(label="Deep Clean + Sync (Windows)", command=_deep_clean_and_sync)

    # Install from current git branch with elevation on Windows (admin)
    def _install_from_current_branch_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        import json as _json
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox
        from pathlib import Path as _P
        import tempfile
        try:
            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                try:
                    # Discover repo, remote, branch
                    from .. import espanso_sync as _esp
                    repo = None
                    try:
                        repo = _esp._find_repo_root(None)
                    except SystemExit:
                        repo = None
                    # Prefer explicit URL from settings, then derive from git
                    from ..variables import storage as _stg
                    repo_url = _stg.get_setting_espanso_repo_url() or (_esp._git_remote(repo) if repo else None)
                    branch = _esp._active_branch(repo or _P.cwd(), None)
                    if not branch:
                        branch = "main"
                    # Prefer HTTPS on Windows
                    if repo_url and repo_url.startswith("git@github.com:"):
                        owner_repo = repo_url.split(":", 1)[1]
                        if owner_repo.endswith(".git"):
                            owner_repo = owner_repo[:-4]
                        repo_url = f"https://github.com/{owner_repo}.git"
                    elif repo_url and repo_url.startswith("ssh://") and "github.com" in repo_url:
                        tail = repo_url.split("github.com", 1)[1].lstrip(":/")
                        if tail.endswith(".git"):
                            tail = tail[:-4]
                        repo_url = f"https://github.com/{tail}.git"

                    # Windows elevated path
                    import platform
                    import shutil as _sh
                    if platform.system() == "Windows" and _sh.which("powershell.exe") and repo_url:
                        # Write a log to a temp file so we can present output
                        log_path = _P(tempfile.gettempdir()) / "espanso_install_branch.log"
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; Set-Location $env:USERPROFILE; "
                            f"$log=\"{str(log_path)}\"; "
                            "function W([string]$t){ Add-Content -Path $log -Encoding UTF8 $t }; "
                            "W('BEGIN'); try { W((espanso path | Out-String)) } catch {}; "
                            f"$o=(espanso package install prompt-automation --git {repo_url} --git-branch {branch} --external) 2>&1 | Out-String; W($o); "
                            "if (($LASTEXITCODE -ne 0) -or ($o -match 'already installed' -or $o -match 'unable to install')) { "
                            "  try { espanso package update prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  try { espanso package uninstall prompt-automation | Out-String | % { W($_) } } catch {}; "
                            f"  $o2=(espanso package install prompt-automation --git {repo_url} --git-branch {branch} --external) 2>&1 | Out-String; W($o2); "
                            "} "
                            "espanso restart | Out-String | % { W($_) }; "
                            "espanso package list | Out-String | % { W($_) }; "
                            "W('END')"
                        )
                        # Try non-admin first; fallback to elevation only if needed
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            code_na, out_na, err_na = _esp._run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command", ps], timeout=120)
                            if code_na != 0:
                                cmd = [
                                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                                    f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                                ]
                                _esp._run(cmd, timeout=150)
                        # Read back log
                        try:
                            log_text = log_path.read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        # Basic summary
                        ok = ("package installed" in log_text.lower() or "already installed" in log_text.lower())
                        header = f"Install from Branch Summary: {'OK' if ok else 'Issues'} | branch={branch}\n\n"
                        log_text = header + log_text
                        root.after(0, _present_log_window, log_text, ok)
                        return

                    # Non-Windows or fallback: try internal installer directly
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        _esp._install_or_update("prompt-automation", repo_url, None, branch)
                    ok = True
                    log_text = "Install from Branch Summary: OK\n\n" + buf_out.getvalue()
                except Exception as e:
                    log_text = f"Install from Branch Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Install from branch (admin) failed: %s", e)
    esp_menu.add_command(label="Install from Current Branch (Admin)", command=_install_from_current_branch_admin)

    # Install from specific tag (Admin prompt), useful when the GitHub provider expects a versioned tag
    def _install_from_tag_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        import json as _json
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox, simpledialog
        from pathlib import Path as _P
        import tempfile
        try:
            # Ask for tag name
            default_tag = None
            try:
                from .. import espanso_sync as _esp
                repo = _esp._find_repo_root(None)
                _, ver = _esp._read_manifest(repo)
                default_tag = f"espanso-v{ver}"
            except Exception:
                default_tag = "espanso-v0.1.0"
            tag = simpledialog.askstring("Install from Tag", "Enter tag to install (e.g., espanso-v0.1.23):", initialvalue=default_tag, parent=root)
            if not tag:
                return

            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                log_text = ""
                try:
                    from .. import espanso_sync as _esp
                    repo = None
                    try:
                        repo = _esp._find_repo_root(None)
                    except SystemExit:
                        repo = None
                    from ..variables import storage as _stg
                    repo_url = _stg.get_setting_espanso_repo_url() or (_esp._git_remote(repo) if repo else None)
                    # Prefer HTTPS on Windows
                    if repo_url and repo_url.startswith("git@github.com:"):
                        owner_repo = repo_url.split(":", 1)[1]
                        if owner_repo.endswith(".git"):
                            owner_repo = owner_repo[:-4]
                        repo_url = f"https://github.com/{owner_repo}.git"
                    elif repo_url and repo_url.startswith("ssh://") and "github.com" in repo_url:
                        tail = repo_url.split("github.com", 1)[1].lstrip(":/")
                        if tail.endswith(".git"):
                            tail = tail[:-4]
                        repo_url = f"https://github.com/{tail}.git"

                    import platform, shutil as _sh
                    if platform.system() == "Windows" and _sh.which("powershell.exe") and repo_url:
                        log_path = _P(tempfile.gettempdir()) / "espanso_install_tag.log"
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; Set-Location $env:USERPROFILE; "
                            f"$log=\"{str(log_path)}\"; "
                            "function W([string]$t){ Add-Content -Path $log -Encoding UTF8 $t }; "
                            f"$o=(espanso package install prompt-automation --git {repo_url} --git-branch {tag} --external) 2>&1 | Out-String; W($o); "
                            "if (($LASTEXITCODE -ne 0) -or ($o -match 'already installed' -or $o -match 'unable to install')) { "
                            "  try { espanso package update prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  try { espanso package uninstall prompt-automation | Out-String | % { W($_) } } catch {}; "
                            f"  $o2=(espanso package install prompt-automation --git {repo_url} --git-branch {tag} --external) 2>&1 | Out-String; W($o2); "
                            "} "
                            "espanso restart | Out-String | % { W($_) }; "
                            "espanso package list | Out-String | % { W($_) }; "
                            "W('DONE')"
                        )
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            code_na, out_na, err_na = _esp._run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command", ps], timeout=120)
                            if code_na != 0:
                                cmd = [
                                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                                    f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                                ]
                                _esp._run(cmd, timeout=150)
                        try:
                            log_text = _P(log_path).read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        ok = ("package installed" in log_text.lower() or "already installed" in log_text.lower())
                        header = f"Install from Tag Summary: {'OK' if ok else 'Issues'} | tag={tag}\n\n"
                        log_text = header + log_text
                    else:
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            _esp._install_or_update("prompt-automation", repo_url, None, tag)
                        ok = True
                        log_text = "Install from Tag Summary: OK\n\n" + buf_out.getvalue()
                except Exception as e:
                    log_text = f"Install from Tag Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Install from tag (admin) failed: %s", e)
    esp_menu.add_command(label="Install from Tag (Admin)...", command=_install_from_tag_admin)

    # Install from a custom branch name (Admin prompt)
    def _install_from_branch_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        import json as _json
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox, simpledialog
        from pathlib import Path as _P
        import tempfile
        try:
            # Default to current active branch if available
            default_branch = "main"
            try:
                from .. import espanso_sync as _esp
                repo = _esp._find_repo_root(None)
                b = _esp._active_branch(repo, None)
                if b:
                    default_branch = b
            except Exception:
                pass
            branch = simpledialog.askstring("Install from Branch", "Enter branch to install:", initialvalue=default_branch, parent=root)
            if not branch:
                return

            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                log_text = ""
                try:
                    from .. import espanso_sync as _esp
                    repo = None
                    try:
                        repo = _esp._find_repo_root(None)
                    except SystemExit:
                        repo = None
                    from ..variables import storage as _stg
                    repo_url = _stg.get_setting_espanso_repo_url() or (_esp._git_remote(repo) if repo else None)
                    if repo_url and repo_url.startswith("git@github.com:"):
                        owner_repo = repo_url.split(":", 1)[1]
                        if owner_repo.endswith(".git"):
                            owner_repo = owner_repo[:-4]
                        repo_url = f"https://github.com/{owner_repo}.git"
                    elif repo_url and repo_url.startswith("ssh://") and "github.com" in repo_url:
                        tail = repo_url.split("github.com", 1)[1].lstrip(":/")
                        if tail.endswith(".git"):
                            tail = tail[:-4]
                        repo_url = f"https://github.com/{tail}.git"

                    import platform, shutil as _sh
                    if platform.system() == "Windows" and _sh.which("powershell.exe") and repo_url:
                        log_path = _P(tempfile.gettempdir()) / "espanso_install_branch_input.log"
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; Set-Location $env:USERPROFILE; "
                            f"$log=\"{str(log_path)}\"; "
                            "function W([string]$t){ Add-Content -Path $log -Encoding UTF8 $t }; "
                            f"$o=(espanso package install prompt-automation --git {repo_url} --git-branch {branch} --external) 2>&1 | Out-String; W($o); "
                            "if (($LASTEXITCODE -ne 0) -or ($o -match 'already installed' -or $o -match 'unable to install')) { "
                            "  try { espanso package update prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  try { espanso package uninstall prompt-automation | Out-String | % { W($_) } } catch {}; "
                            f"  $o2=(espanso package install prompt-automation --git {repo_url} --git-branch {branch} --external) 2>&1 | Out-String; W($o2); "
                            "} "
                            "espanso restart | Out-String | % { W($_) }; "
                            "espanso package list | Out-String | % { W($_) }; "
                            "W('DONE')"
                        )
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            code_na, out_na, err_na = _esp._run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command", ps], timeout=120)
                            if code_na != 0:
                                cmd = [
                                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                                    f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                                ]
                                _esp._run(cmd, timeout=150)
                        try:
                            log_text = _P(log_path).read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        ok = ("package installed" in log_text.lower() or "already installed" in log_text.lower())
                        header = f"Install from Branch Summary: {'OK' if ok else 'Issues'} | branch={branch}\n\n"
                        log_text = header + log_text
                    else:
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            _esp._install_or_update("prompt-automation", repo_url, None, branch)
                        ok = True
                        log_text = "Install from Branch Summary: OK\n\n" + buf_out.getvalue()
                except Exception as e:
                    log_text = f"Install from Branch Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Install from branch (custom, admin) failed: %s", e)
    esp_menu.add_command(label="Install from Branch (Admin)...", command=_install_from_branch_admin)

    # Install from custom Git URL + branch (Admin)
    def _install_from_url_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox, simpledialog
        try:
            from .. import espanso_sync as _esp
            # Suggest current repo remote (HTTPS normalized) and branch
            repo = None
            try:
                repo = _esp._find_repo_root(None)
            except SystemExit:
                repo = None
            url = _esp._git_remote(repo) if repo else "https://github.com/<owner>/<repo>.git"
            if url and url.startswith("git@github.com:"):
                owner_repo = url.split(":", 1)[1]
                if owner_repo.endswith(".git"):
                    owner_repo = owner_repo[:-4]
                url = f"https://github.com/{owner_repo}.git"
            elif url and url.startswith("ssh://") and "github.com" in url:
                tail = url.split("github.com", 1)[1].lstrip(":/")
                if tail.endswith(".git"):
                    tail = tail[:-4]
                url = f"https://github.com/{tail}.git"
            branch = _esp._active_branch(repo, None) or "main"

            chosen_url = simpledialog.askstring("Install from URL", "Git URL (HTTPS):", initialvalue=url, parent=root)
            if not chosen_url:
                return
            chosen_branch = simpledialog.askstring("Install from URL", "Branch or tag:", initialvalue=branch, parent=root)
            if not chosen_branch:
                return

            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                log_text = ""
                try:
                    import platform, shutil as _sh, tempfile
                    from pathlib import Path as _P
                    if platform.system() == "Windows" and _sh.which("powershell.exe"):
                        log_path = _P(tempfile.gettempdir()) / "espanso_install_url.log"
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; Set-Location $env:USERPROFILE; "
                            f"$log=\"{str(log_path)}\"; "
                            "function W([string]$t){ Add-Content -Path $log -Encoding UTF8 $t }; "
                            f"$o=(espanso package install prompt-automation --git {chosen_url} --git-branch {chosen_branch} --external) 2>&1 | Out-String; W($o); "
                            "if (($LASTEXITCODE -ne 0) -or ($o -match 'already installed' -or $o -match 'unable to install')) { "
                            "  try { espanso package update prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  try { espanso package uninstall prompt-automation | Out-String | % { W($_) } } catch {}; "
                            f"  $o2=(espanso package install prompt-automation --git {chosen_url} --git-branch {chosen_branch} --external) 2>&1 | Out-String; W($o2); "
                            "} "
                            "espanso restart | Out-String | % { W($_) }; "
                            "espanso package list | Out-String | % { W($_) }; "
                            "W('DONE')"
                        )
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            code_na, out_na, err_na = _esp._run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command", ps], timeout=120)
                            if code_na != 0:
                                _esp._run([
                                    "powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command",
                                    f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                                ], timeout=150)
                        try:
                            log_text = _P(log_path).read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        ok = ("package installed" in log_text.lower() or "already installed" in log_text.lower())
                        header = f"Install from URL Summary: {'OK' if ok else 'Issues'} | branch_or_tag={chosen_branch}\n\n"
                        log_text = header + log_text
                    else:
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            _esp._install_or_update("prompt-automation", chosen_url, None, chosen_branch)
                        ok = True
                        log_text = "Install from URL Summary: OK\n\n" + buf_out.getvalue()
                except Exception as e:
                    log_text = f"Install from URL Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Install from URL (admin) failed: %s", e)
    esp_menu.add_command(label="Install from URL (Admin)...", command=_install_from_url_admin)

    # Publish release tag (Admin) and open GitHub releases page
    def _publish_release_tag_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox, simpledialog
        try:
            from .. import espanso_sync as _esp
            repo = None
            try:
                repo = _esp._find_repo_root(None)
            except SystemExit:
                messagebox.showerror("Publish", "Repo not found; open the app from the repo")
                return
            # Default tag based on manifest
            _, ver = _esp._read_manifest(repo)
            default_tag = f"espanso-v{ver}"
            tag = simpledialog.askstring("Publish Tag", "Tag to create/push (e.g., espanso-v0.1.23):", initialvalue=default_tag, parent=root)
            if not tag:
                return

            def _run():
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                log_text = ""
                try:
                    import platform, shutil as _sh, tempfile, webbrowser
                    from pathlib import Path as _P
                    # Prefer URL from settings; fall back to git remote
                    from ..variables import storage as _stg
                    set_url = _stg.get_setting_espanso_repo_url()
                    web = set_url or (_esp._git_remote(repo) or "")
                    # Normalize web URL for release page
                    if web.startswith("git@github.com:"):
                        owner_repo = web.split(":", 1)[1]
                        if owner_repo.endswith(".git"):
                            owner_repo = owner_repo[:-4]
                        web = f"https://github.com/{owner_repo}"
                    elif web.startswith("ssh://") and "github.com" in web:
                        tail = web.split("github.com", 1)[1].lstrip(":/")
                        if tail.endswith(".git"):
                            tail = tail[:-4]
                        web = f"https://github.com/{tail}"
                    if web.endswith(".git"):
                        web = web[:-4]

                    if platform.system() == "Windows" and _sh.which("powershell.exe"):
                        log_path = _P(tempfile.gettempdir()) / "espanso_publish_tag.log"
                        # Build PS with safe.directory retry
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; "
                            f"$log=\"{str(log_path)}\"; function W([string]$t){{ Add-Content -Path $log -Encoding UTF8 $t }}; "
                            f"$repo=\"{str(repo)}\"; $tag=\"{tag}\"; "
                            "try { W((git -C $repo status --porcelain | Out-String)) } catch {}; "
                            "try { git -C $repo tag -a $tag -m $tag 2>&1 | Out-String | % { W($_) } } catch {}; "
                            "try { git -C $repo push origin $tag 2>&1 | Out-String | % { W($_) } } catch {}; "
                            "if ((Get-Content $log) -match 'dubious ownership') { git config --global --add safe.directory $repo; git -C $repo push origin $tag 2>&1 | Out-String | % { W($_) } }; "
                            "W('DONE')"
                        )
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            code_na, out_na, err_na = _esp._run([
                                "powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command", ps
                            ], timeout=120)
                            if code_na != 0:
                                _esp._run([
                                    "powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command",
                                    f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                                ], timeout=150)
                        try:
                            log_text = _P(log_path).read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        ok = ("[new tag]" in log_text.lower() or "up to date" in log_text.lower() or "done" in log_text.lower())
                        header = f"Publish Tag Summary: {'OK' if ok else 'Issues'} | tag={tag}\n\n"
                        log_text = header + log_text
                        # Open releases page for tag
                        if web:
                            try: webbrowser.open(f"{web}/releases/new?tag={tag}")
                            except Exception: pass
                    else:
                        # Non-Windows simple path
                        out = []
                        def _W(s: str): out.append(s)
                        _esp._run(["git","-C",str(repo),"tag","-a",tag,"-m",tag])
                        _esp._run(["git","-C",str(repo),"push","origin",tag])
                        for l in out: pass
                        ok = True
                        log_text = f"Publish Tag Summary: OK | tag={tag}\n"
                        if web:
                            try: webbrowser.open(f"{web}/releases/new?tag={tag}")
                            except Exception: pass
                except Exception as e:
                    log_text = f"Publish Tag Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Publish release tag (admin) failed: %s", e)
    esp_menu.add_command(label="Publish Release + Tag (Admin)", command=_publish_release_tag_admin)

    # Publish current manifest version tag and install it (Admin, one-click)
    def _publish_and_install_admin():  # pragma: no cover - GUI side effects
        import threading
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from tkinter import messagebox
        try:
            from .. import espanso_sync as _esp
            repo = None
            try:
                repo = _esp._find_repo_root(None)
            except SystemExit:
                messagebox.showerror("Publish + Install", "Repo not found; open the app from the repo")
                return
            # Determine version and tag
            _, ver = _esp._read_manifest(repo)
            tag = f"espanso-v{ver}"
            # Normalize remote to HTTPS for Windows
            remote = _esp._git_remote(repo) or ""
            if remote.startswith("git@github.com:"):
                owner_repo = remote.split(":", 1)[1]
                if owner_repo.endswith(".git"):
                    owner_repo = owner_repo[:-4]
                remote_https = f"https://github.com/{owner_repo}.git"
            elif remote.startswith("ssh://") and "github.com" in remote:
                tail = remote.split("github.com", 1)[1].lstrip(":/")
                if tail.endswith(".git"):
                    tail = tail[:-4]
                remote_https = f"https://github.com/{tail}.git"
            else:
                remote_https = remote or ""
            # If remote URL is still unknown, prompt the user
            if not remote_https or "github.com/" not in remote_https:
                from tkinter import simpledialog
                entered = simpledialog.askstring(
                    "Publish + Install",
                    "Enter HTTPS Git URL (e.g., https://github.com/<owner>/<repo>.git):",
                    parent=root,
                )
                if not entered:
                    messagebox.showerror("Publish + Install", "Aborted: missing repository URL")
                    return
                remote_https = entered.strip()

            def _run():
                import platform, shutil as _sh, tempfile
                from pathlib import Path as _P
                buf_out, buf_err = io.StringIO(), io.StringIO()
                ok = False
                log_text = ""
                try:
                    if platform.system() == "Windows" and _sh.which("powershell.exe"):
                        log_path = _P(tempfile.gettempdir()) / "espanso_publish_install.log"
                        # PowerShell script to set location, tag, push (with safe.directory retry), install, restart, list
                        ps = (
                            "$ErrorActionPreference='SilentlyContinue'; Set-Location $env:USERPROFILE; "
                            f"$log=\"{str(log_path)}\"; function W([string]$t){{ Add-Content -Path $log -Encoding UTF8 $t }}; "
                            f"$repo=\"{str(repo)}\"; $tag=\"{tag}\"; $url=\"{remote_https}\"; "
                            # Git tag and push
                            "try { git -C $repo tag -a $tag -m $tag 2>&1 | Out-String | % { W($_) } } catch {}; "
                            "try { git -C $repo push origin $tag 2>&1 | Out-String | % { W($_) } } catch {}; "
                            # Dubious ownership recovery
                            "if ((Get-Content $log) -match 'dubious ownership') { git config --global --add safe.directory $repo; git -C $repo push origin $tag 2>&1 | Out-String | % { W($_) } }; "
                            # Install that tag with retry logic
                            "$o=(espanso package install prompt-automation --git $url --git-branch $tag --external) 2>&1 | Out-String; W($o); "
                            "if (($LASTEXITCODE -ne 0) -or ($o -match 'already installed' -or $o -match 'unable to install')) { "
                            "  try { espanso package update prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  try { espanso package uninstall prompt-automation | Out-String | % { W($_) } } catch {}; "
                            "  $o2=(espanso package install prompt-automation --git $url --git-branch $tag --external) 2>&1 | Out-String; W($o2); "
                            "} "
                            "espanso restart | Out-String | % { W($_) }; "
                            "espanso package list | Out-String | % { W($_) }; "
                            "W('DONE')"
                        )
                        cmd = [
                            "powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command",
                            f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','{ps.replace("'","''")}' -Verb RunAs -Wait"
                        ]
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            _esp._run(cmd, timeout=150)
                        try:
                            log_text = _P(log_path).read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            log_text = buf_out.getvalue()
                        low = log_text.lower()
                        ok = ("package installed" in low or "already installed" in low) and (tag.lower() in low)
                        header = f"Publish + Install Summary: {'OK' if ok else 'Issues'} | tag={tag}\n\n"
                        log_text = header + log_text
                    else:
                        # Non-Windows fallback: do best-effort tagging + install via internal functions
                        with redirect_stdout(buf_out), redirect_stderr(buf_err):
                            _esp._run(["git","-C",str(repo),"tag","-a",tag,"-m",tag])
                            _esp._run(["git","-C",str(repo),"push","origin",tag])
                            _esp._uninstall_package("prompt-automation")
                            _esp._install_or_update("prompt-automation", remote_https, None, tag)
                        ok = True
                        log_text = f"Publish + Install Summary: OK | tag={tag}\n\n" + buf_out.getvalue()
                except Exception as e:
                    log_text = f"Publish + Install Summary: Exception: {e}\n\n" + buf_out.getvalue() + ("\n[stderr]\n" + buf_err.getvalue() if buf_err.getvalue() else "")
                finally:
                    try:
                        root.after(0, _present_log_window, log_text, ok)
                    except Exception:
                        messagebox.showinfo("Espanso", log_text[:2000])
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            _log.error("Publish + Install (admin) failed: %s", e)
    esp_menu.add_command(label="Publish + Install (Admin)", command=_publish_and_install_admin)
    opt.add_cascade(label="Espanso", menu=esp_menu)

    # Help menu with concise workflow and guide
    help_menu = tk.Menu(new_menubar, tearoff=0)

    def _open_remote_first_guide():  # pragma: no cover - GUI heavy
        import tkinter as tk
        from tkinter import scrolledtext, messagebox
        try:
            # Try to locate the local docs file from repo
            from .. import espanso_sync as _esp
            guide = None
            try:
                repo = _esp._find_repo_root(None)
                p = repo / 'docs' / 'ESPANSO_REMOTE_FIRST.md'
                if p.exists():
                    guide = p
            except Exception:
                guide = None
            content = None
            if guide is not None:
                try:
                    content = guide.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    content = None
            if content is None:
                content = (
                    "Remote-first guide not found locally.\n\n"
                    "Summary:\n"
                    "1) Options → Espanso → Set Default Repo URL… (HTTPS)\n"
                    "2) Options → Espanso → Deep Clean + Sync (Windows)\n"
                    "3) Verify via 'espanso package list'\n"
                )
            win = tk.Toplevel(root)
            win.title("Remote-First Guide")
            win.geometry("780x560")
            txt = scrolledtext.ScrolledText(win, wrap='word')
            txt.pack(fill='both', expand=True)
            try:
                txt.insert('1.0', content)
                txt.configure(state='disabled')
            except Exception:
                pass
            tk.Button(win, text=INFO_CLOSE_SAVE, command=win.destroy).pack(side='bottom')
        except Exception as e:
            try:
                messagebox.showerror('Help', f'Unable to open guide: {e}')
            except Exception:
                pass

    def _quick_sync_steps():  # pragma: no cover - GUI heavy
        import tkinter as tk
        from tkinter import messagebox
        steps = (
            "Quick Sync Workflow\n\n"
            "1) Options → Espanso → Set Default Repo URL… (HTTPS)\n"
            "2) Options → Espanso → Deep Clean + Sync (Windows)\n"
            "3) (if you get errors) Options → Espanso → Publish and Install (should make remote version available)\n"
            "3) Verify:\n"
            "   - espanso package list\n"
            "   - Should show 'prompt-automation' with your GitHub https URL\n"
            "   - No user match files except disabled.yml under %APPDATA%\\espanso\\match\n\n"
            "Tip: Use Install from Tag/Branch/URL to bypass Releases when needed."
        )
        try:
            win = tk.Toplevel(root)
            win.title('Quick Sync')
            win.geometry('560x360')
            txt = tk.Text(win, wrap='word')
            txt.pack(fill='both', expand=True)
            try:
                txt.insert('1.0', steps)
                txt.configure(state='disabled')
            except Exception:
                pass
            def _copy():
                try:
                    root.clipboard_clear(); root.clipboard_append(steps)
                except Exception: pass
            bar = tk.Frame(win); bar.pack(fill='x')
            tk.Button(bar, text='Copy', command=_copy).pack(side='left')
            tk.Button(bar, text=INFO_CLOSE_SAVE, command=win.destroy).pack(side='right')
        except Exception:
            try:
                messagebox.showinfo('Quick Sync', steps)
            except Exception:
                pass

    help_menu.add_command(label='Quick Sync Steps', command=_quick_sync_steps)
    help_menu.add_command(label='Open Remote-First Guide', command=_open_remote_first_guide)
    new_menubar.add_cascade(label='Help', menu=help_menu)

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
