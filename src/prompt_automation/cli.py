"""Command line entrypoint with dependency checks."""
from __future__ import annotations

import argparse
import logging
import os
import platform
import shutil
from .utils import safe_run
import sys
from pathlib import Path
from typing import Any

from . import logger, menus, paste, update
from . import updater  # lightweight pipx auto-updater
from .variables import reset_file_overrides


LOG_DIR = Path.home() / ".prompt-automation" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cli.log"
_log = logging.getLogger("prompt_automation.cli")
if not _log.handlers:
    _log.setLevel(logging.INFO)
    _log.addHandler(logging.FileHandler(LOG_FILE))


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    if platform.system() == "Linux":
        rel = platform.uname().release.lower()
        return "microsoft" in rel or "wsl" in rel
    return False


def _check_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _run_cmd(cmd: list[str]) -> bool:
    try:
        res = safe_run(cmd, capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def check_dependencies(require_fzf: bool = True) -> bool:
    """Verify required dependencies; attempt install if possible."""
    os_name = platform.system()
    missing: list[str] = []

    if require_fzf and not _check_cmd("fzf"):
        missing.append("fzf")
        if os_name == "Linux":
            if not _check_cmd("zenity"):
                missing.append("zenity")
            if not _check_cmd("xdotool"):
                missing.append("xdotool")
        elif os_name == "Windows":
            try:
                import keyboard  # noqa: F401
            except Exception as e:
                _log.warning("keyboard library unavailable on Windows: %s", e)
                # Don't add to missing - keyboard functionality is optional
                # missing.append("keyboard")

    try:
        import pyperclip  # noqa: F401
    except Exception:
        missing.append("pyperclip")

    # Check for GUI library only if GUI mode might be used
    gui_mode = os.environ.get("PROMPT_AUTOMATION_GUI") != "0"
    if gui_mode:
        try:
            import tkinter  # noqa: F401
            _log.info("Tkinter is available for GUI mode")
        except Exception:
            missing.append("tkinter")

    if _is_wsl():
        if not _check_cmd("clip.exe"):
            _log.warning("WSL clipboard integration missing (clip.exe not found)")
        if not _run_cmd(["powershell.exe", "-Command", ""]):
            _log.warning("WSL unable to run Windows executables")

    if missing:
        msg = "Missing dependencies: " + ", ".join(missing)
        print(f"[prompt-automation] {msg}")
        _log.warning(msg)
        os_name = platform.system()
        for dep in list(missing):
            if dep in ["pyperclip"]:
                _run_cmd([sys.executable, "-m", "pip", "install", dep])
            elif os_name == "Linux" and _check_cmd("apt"):
                if dep == "tkinter":
                    _run_cmd(["sudo", "apt", "install", "-y", "python3-tk"])
                else:
                    _run_cmd(["sudo", "apt", "install", "-y", dep])
            elif os_name == "Darwin" and _check_cmd("brew"):
                if dep != "tkinter":
                    _run_cmd(["brew", "install", dep])
        print("[prompt-automation] Re-run after installing missing dependencies.")
        return False

    return True


def dependency_status(gui_mode: bool) -> dict[str, dict[str, str]]:
    """Return a structured view of dependency availability without installing.

    Each entry maps to a dict with keys:
      status: ok | missing | optional-missing
      detail: short human readable note
    """
    import importlib

    status: dict[str, dict[str, str]] = {}
    def _add(name: str, ok: bool, optional: bool = False, detail: str = ""):
        status[name] = {
            "status": "ok" if ok else ("optional-missing" if optional else "missing"),
            "detail": detail,
        }

    # Core Python module presence
    try:
        importlib.import_module("pyperclip")
        _add("pyperclip", True, detail="available")
    except Exception as e:
        _add("pyperclip", False, detail=str(e))

    if gui_mode:
        try:
            importlib.import_module("tkinter")
            _add("tkinter", True, detail="available")
        except Exception as e:
            _add("tkinter", False, detail=str(e))
    else:
        # CLI mode: prefer fzf but it's optional if user wants simple menu
        _add("fzf", shutil.which("fzf") is not None, optional=True, detail="path lookup")

    # Clipboard tools (optional fallbacks)
    if platform.system() == "Linux":
        _add("xclip", shutil.which("xclip") is not None, optional=True)
        _add("wl-copy", shutil.which("wl-copy") is not None, optional=True)
    elif platform.system() == "Darwin":
        _add("pbcopy", shutil.which("pbcopy") is not None, optional=True)
    elif platform.system() == "Windows":
        _add("clip.exe", shutil.which("clip") is not None, optional=True)
        try:
            importlib.import_module("keyboard")
            _add("keyboard", True, optional=True)
        except Exception as e:
            _add("keyboard", False, optional=True, detail=str(e))

    return status


def main(argv: list[str] | None = None) -> None:
    """Program entry point."""
    # Load environment from config file if it exists
    config_dir = Path.home() / ".prompt-automation"
    env_file = config_dir / "environment"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    
    parser = argparse.ArgumentParser(prog="prompt-automation")
    parser.add_argument("--troubleshoot", action="store_true", help="Show troubleshooting help and paths")
    parser.add_argument("--prompt-dir", type=Path, help="Directory containing prompt templates")
    parser.add_argument("--list", action="store_true", help="List available prompt styles and templates")
    parser.add_argument("--reset-log", action="store_true", help="Clear usage log database")
    parser.add_argument("--reset-file-overrides", action="store_true", help="Clear stored reference file paths & skip flags")
    parser.add_argument("--gui", action="store_true", help="Launch GUI (default)")
    parser.add_argument("--terminal", action="store_true", help="Force terminal mode instead of GUI")
    parser.add_argument("--update", "-u", action="store_true", help="Check for and apply updates")
    parser.add_argument("--self-test", action="store_true", help="Run dependency and template health checks and exit")
    parser.add_argument(
        "--assign-hotkey",
        action="store_true",
        help="Interactively set or change the global GUI hotkey",
    )
    args = parser.parse_args(argv)

    if args.prompt_dir:
        path = args.prompt_dir.expanduser().resolve()
        os.environ["PROMPT_AUTOMATION_PROMPTS"] = str(path)
        _log.info("using custom prompt directory %s", path)

    if args.assign_hotkey:
        from . import hotkeys

        hotkeys.assign_hotkey()
        return

    if args.update:
        from . import hotkeys
        
        # Force update check and installation
        update.check_and_prompt(force=True)
        
        # Ensure dependencies are still met after update
        print("[prompt-automation] Checking dependencies after update...")
        if not check_dependencies(require_fzf=False):  # Check basic deps
            print("[prompt-automation] Some dependencies may need to be reinstalled.")
        
        # Check hotkey-specific dependencies
        if not hotkeys.ensure_hotkey_dependencies():
            print("[prompt-automation] Warning: Hotkey dependencies missing. Hotkeys may not work properly.")
        
        # Update hotkeys to use GUI mode
        hotkeys.update_hotkeys()
        
        print("[prompt-automation] Update complete!")
        return

    try:
        menus.ensure_unique_ids(menus.PROMPTS_DIR)
    except ValueError as e:
        print(f"[prompt-automation] {e}")
        return

    if args.self_test:
        # Gather template metrics
        styles = menus.list_styles()
        template_files = []
        for s in styles:
            for p in menus.list_prompts(s):
                try:
                    data = menus.load_template(p)
                    if isinstance(data, dict) and "template" in data:
                        template_files.append(p)
                except Exception:
                    pass
        gui_mode = not args.terminal and (args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0")
        dep_status = dependency_status(gui_mode)
        missing_critical = [k for k,v in dep_status.items() if v["status"] == "missing"]
        print("=== Self Test Report ===")
        print(f"Styles: {len(styles)} | Templates: {len(template_files)}")
        print("Dependencies:")
        for name, info in sorted(dep_status.items()):
            print(f"  - {name}: {info['status']} {('- ' + info['detail']) if info['detail'] else ''}")
        if missing_critical:
            print("Critical missing dependencies:", ", ".join(missing_critical))
            print("Self test: FAIL")
        else:
            print("Self test: PASS")
        return

    if args.reset_log:
        logger.clear_usage_log()
        print("[prompt-automation] usage log cleared")
        return
    if args.reset_file_overrides:
        if reset_file_overrides():
            print("[prompt-automation] reference file overrides cleared")
        else:
            print("[prompt-automation] no overrides to clear")
        return

    if args.list:
        for style in menus.list_styles():
            print(style)
            for tmpl_path in menus.list_prompts(style):
                print("  ", tmpl_path.name)
        return

    if args.troubleshoot:
        print(
            "Troubleshooting tips:\n- Ensure dependencies are installed.\n- Logs stored at",
            LOG_DIR,
            "\n- Usage DB:",
            logger.DB_PATH,
        )
        return

    gui_mode = not args.terminal and (args.gui or os.environ.get("PROMPT_AUTOMATION_GUI") != "0")

    _log.info("running on %s", platform.platform())
    if not check_dependencies(require_fzf=not gui_mode):
        return
    # Background silent pipx upgrade check (rate-limited)
    try:  # never block startup
        updater.check_for_update()
    except Exception:
        pass
    # Existing manifest-based update system (interactive) retained
    update.check_and_prompt()

    if gui_mode:
        from . import gui

        gui.run()
        return

    # Enhanced CLI workflow
    banner = Path(__file__).with_name("resources").joinpath("banner.txt")
    print(banner.read_text())
    
    # Template selection with improved UX
    tmpl: dict[str, Any] | None = select_template_cli()
    if not tmpl:
        return
        
    # Render with preview option
    text = render_template_cli(tmpl)
    if text:
        # Show preview and confirm
        print("\n" + "="*60)
        print("RENDERED OUTPUT:")
        print("="*60)
        print(text)
        print("="*60)
        
        if input("\nProceed with clipboard copy? [Y/n]: ").lower() not in {'n', 'no'}:
            paste.copy_to_clipboard(text)
            print("\n[prompt-automation] Text copied to clipboard. Press Ctrl+V to paste where needed.")
            logger.log_usage(tmpl, len(text))


def select_template_cli() -> dict[str, Any] | None:
    """Enhanced CLI template selection with better navigation."""
    styles = menus.list_styles()
    if not styles:
        print("No template styles found.")
        return None
    
    # Show styles with numbering and usage frequency
    usage = logger.usage_counts()
    style_freq = {s: sum(c for (pid, st), c in usage.items() if st == s) for s in styles}
    sorted_styles = sorted(styles, key=lambda s: (-style_freq.get(s, 0), s.lower()))
    
    print("\nAvailable Styles:")
    for i, style in enumerate(sorted_styles, 1):
        freq_info = f" ({style_freq[style]} recent)" if style_freq.get(style, 0) > 0 else ""
        print(f"{i:2d}. {style}{freq_info}")
    
    while True:
        try:
            choice = input(f"\nSelect style (1-{len(sorted_styles)}) or press Enter to cancel: ").strip()
            if not choice:
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(sorted_styles):
                selected_style = sorted_styles[int(choice) - 1]
                return pick_prompt_cli(selected_style)
            print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            return None


def pick_prompt_cli(style: str) -> dict[str, Any] | None:
    """Enhanced CLI prompt selection."""
    prompts = menus.list_prompts(style)
    if not prompts:
        print(f"No templates found in style '{style}'.")
        return None
    
    # Show templates with usage frequency
    usage = logger.usage_counts()
    prompt_freq = {p.name: usage.get((p.stem.split("_")[0], style), 0) for p in prompts}
    sorted_prompts = sorted(prompts, key=lambda p: (-prompt_freq.get(p.name, 0), p.name.lower()))
    
    print(f"\nTemplates in '{style}':")
    for i, prompt_path in enumerate(sorted_prompts, 1):
        template = menus.load_template(prompt_path)
        # Show nested relative path (excluding style root) if present
        rel = prompt_path.relative_to(menus.PROMPTS_DIR / style)
        rel_display = str(rel.parent) + "/" if str(rel.parent) != "." else ""
        title = template.get('title', prompt_path.stem)
        freq_info = f" ({prompt_freq[prompt_path.name]} recent)" if prompt_freq.get(prompt_path.name, 0) > 0 else ""
        print(f"{i:2d}. {rel_display}{title}{freq_info}")
        
        # Show placeholder count if any
        if template.get('placeholders'):
            ph_count = len(template['placeholders'])
            print(f"     {ph_count} input(s) required")
    
    while True:
        try:
            choice = input(f"\nSelect template (1-{len(sorted_prompts)}) or press Enter to go back: ").strip()
            if not choice:
                return select_template_cli()  # Go back to style selection
            if choice.isdigit() and 1 <= int(choice) <= len(sorted_prompts):
                return menus.load_template(sorted_prompts[int(choice) - 1])
            print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            return None


def render_template_cli(tmpl: dict[str, Any]) -> str:
    """Enhanced CLI template rendering with better prompts."""
    print(f"\nRendering template: {tmpl.get('title', 'Unknown')}")
    print(f"Style: {tmpl.get('style', 'Unknown')}")
    
    if tmpl.get('placeholders'):
        print(f"\nThis template requires {len(tmpl['placeholders'])} input(s):")
        for ph in tmpl['placeholders']:
            label = ph.get('label', ph['name'])
            ptype = ph.get('type', 'text')
            options = ph.get('options', [])
            multiline = ph.get('multiline', False)
            
            type_info = ptype
            if multiline:
                type_info += ", multiline"
            if options:
                type_info += f", options: {', '.join(options)}"
            
            print(f"  - {label} ({type_info})")
        
        if input("\nProceed with input collection? [Y/n]: ").lower() in {'n', 'no'}:
            return ""
    
    return menus.render_template(tmpl)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # pragma: no cover - entry
        _log.exception("unhandled error")
        print(f"[prompt-automation] Error: {e}. See {LOG_FILE} for details.")

