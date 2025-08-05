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
        gui_available = False
        try:
            # Try FreeSimpleGUI first (open source), then PySimpleGUI (commercial)
            try:
                import FreeSimpleGUI  # noqa: F401
                gui_available = True
                _log.info("FreeSimpleGUI is available for GUI mode")
            except ImportError:
                try:
                    import PySimpleGUI  # noqa: F401
                    gui_available = True
                    _log.info("PySimpleGUI is available for GUI mode")
                except ImportError:
                    pass
        except Exception as e:
            _log.warning("Error checking GUI libraries: %s", e)
        
        if not gui_available:
            missing.append("FreeSimpleGUI or PySimpleGUI")

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
            if dep == "FreeSimpleGUI or PySimpleGUI":
                # Try to install FreeSimpleGUI first, then PySimpleGUI as fallback
                if not _run_cmd([sys.executable, "-m", "pip", "install", "FreeSimpleGUI"]):
                    _run_cmd([sys.executable, "-m", "pip", "install", "PySimpleGUI"])
            elif dep in ["pyperclip"]:
                _run_cmd([sys.executable, "-m", "pip", "install", dep])
            elif os_name == "Linux" and _check_cmd("apt"):
                _run_cmd(["sudo", "apt", "install", "-y", dep])
            elif os_name == "Darwin" and _check_cmd("brew"):
                _run_cmd(["brew", "install", dep])
        print("[prompt-automation] Re-run after installing missing dependencies.")
        return False

    return True


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
    parser.add_argument("--gui", action="store_true", help="Launch GUI (default)")
    parser.add_argument("--terminal", action="store_true", help="Force terminal mode instead of GUI")
    parser.add_argument("--update", "-u", action="store_true", help="Check for and apply updates")
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

    if args.reset_log:
        logger.clear_usage_log()
        print("[prompt-automation] usage log cleared")
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
    # Check for updates on startup unless explicitly running update
    update.check_and_prompt()

    if gui_mode:
        from . import gui

        gui.run()
        return

    banner = Path(__file__).with_name("resources").joinpath("banner.txt")
    print(banner.read_text())
    tmpl: dict[str, Any] | None = menus.pick_style()
    if not tmpl:
        return
    text = menus.render_template(tmpl)
    if text:
        # In terminal mode, only copy to clipboard - don't auto-paste
        # to avoid pasting into the terminal where the app is running
        paste.copy_to_clipboard(text)
        print("\n[prompt-automation] Text copied to clipboard. Press Ctrl+V to paste where needed.")
        logger.log_usage(tmpl, len(text))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # pragma: no cover - entry
        _log.exception("unhandled error")
        print(f"[prompt-automation] Error: {e}. See {LOG_FILE} for details.")

