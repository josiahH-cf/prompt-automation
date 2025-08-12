"""Dependency checking helpers for the CLI."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from ..utils import safe_run


_log = logging.getLogger("prompt_automation.cli.dependencies")


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
            except Exception as e:  # pragma: no cover - platform specific
                _log.warning("keyboard library unavailable on Windows: %s", e)

    try:
        import pyperclip  # noqa: F401
    except Exception:
        missing.append("pyperclip")

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
    """Return a structured view of dependency availability without installing."""
    import importlib

    status: dict[str, dict[str, str]] = {}

    def _add(name: str, ok: bool, optional: bool = False, detail: str = ""):
        status[name] = {
            "status": "ok" if ok else ("optional-missing" if optional else "missing"),
            "detail": detail,
        }

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
        _add("fzf", shutil.which("fzf") is not None, optional=True, detail="path lookup")

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


__all__ = ["check_dependencies", "dependency_status"]

