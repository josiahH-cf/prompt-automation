"""Command line entrypoint with dependency checks."""
from __future__ import annotations

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import logger, menus, paste


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
    rel = platform.uname().release.lower()
    return "microsoft" in rel or "wsl" in rel


def _check_cmd(name: str) -> bool:
    return shutil.which(name) is not None


def _run_cmd(cmd: list[str]) -> bool:
    try:
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def check_dependencies() -> bool:
    """Verify required dependencies; attempt install if possible."""
    os_name = platform.system()
    missing: list[str] = []

    if not _check_cmd("fzf"):
        missing.append("fzf")
    if os_name == "Linux":
        if not _check_cmd("zenity"):
            missing.append("zenity")
        if not _check_cmd("xdotool"):
            missing.append("xdotool")
    elif os_name == "Windows":
        try:
            import keyboard  # noqa: F401
        except Exception:
            missing.append("keyboard")

    try:
        import pyperclip  # noqa: F401
    except Exception:
        missing.append("pyperclip")

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
            if dep in {"pyperclip", "keyboard"}:
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
    parser = argparse.ArgumentParser(prog="prompt-automation")
    parser.add_argument("--troubleshoot", action="store_true", help="Show troubleshooting help")
    args = parser.parse_args(argv)

    if args.troubleshoot:
        print("Troubleshooting tips:\n- Ensure dependencies are installed.\n- Logs stored at", LOG_DIR)
        return

    _log.info("running on %s", platform.platform())
    if not check_dependencies():
        return
    banner = Path(__file__).with_name("resources").joinpath("banner.txt")
    print(banner.read_text())
    tmpl = menus.pick_style()
    if not tmpl:
        return
    text = menus.render_template(tmpl)
    if text:
        paste.paste_text(text)
        logger.log_usage(tmpl, len(text))


if __name__ == "__main__":
    main()

