"""Clipboard helper using pyperclip with robust fallbacks."""
from __future__ import annotations

import os
import platform
import shutil
from .utils import safe_run

try:  # Graceful fallback if pyperclip missing at runtime
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover - import guard
    class _PyperclipShim:  # minimal shim used when dependency missing
        def copy(self, _text: str) -> None:
            raise RuntimeError("pyperclip not installed")

    pyperclip = _PyperclipShim()  # type: ignore

from .errorlog import get_logger


_log = get_logger(__name__)


def _is_wsl() -> bool:
    # Check for WSL environment variable first (most reliable)
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    # Only check uname if we're potentially in a Linux environment
    if platform.system() == "Linux":
        rel = platform.uname().release.lower()
        return "microsoft" in rel or "wsl" in rel
    return False


def _copy_system(text: str, os_name: str) -> bool:
    """Attempt system clipboard utilities."""
    try:
        if _is_wsl():
            safe_run(["clip.exe"], input=text.encode(), check=True)
            return True
        if os_name == "Linux":
            if shutil.which("xclip"):
                safe_run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
                return True
            if shutil.which("wl-copy"):
                safe_run(["wl-copy"], input=text.encode(), check=True)
                return True
        elif os_name == "Darwin":
            safe_run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif os_name == "Windows":
            safe_run(["clip"], input=text.encode(), check=True)
            return True
    except Exception as e:  # pragma: no cover - platform specific
        _log.error("system copy failed: %s", e)
    return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard without simulating paste keystroke.

    Returns True on success, False if all strategies failed. Previous callers
    ignored the return value so this is a backward‑compatible enhancement.
    """
    os_name = platform.system()
    copied = False
    try:
        pyperclip.copy(text)
        copied = True
    except Exception as e:  # pragma: no cover - can't easily simulate
        _log.error("pyperclip failed: %s", e)
    if not copied:
        _log.warning("pyperclip failed; attempting system clipboard")
        copied = _copy_system(text, os_name)
    if not copied:
        print("[prompt-automation] Unable to copy text to clipboard. See error log.")
        return False
    return True


def paste_text(text: str) -> None:
    """Copy ``text`` to clipboard and simulate paste."""
    os_name = platform.system()
    copied = False
    try:
        pyperclip.copy(text)
        copied = True
    except Exception as e:  # pragma: no cover - can't easily simulate
        _log.error("pyperclip failed: %s", e)
    if not copied:
        _log.warning("pyperclip failed; attempting system clipboard")
        copied = _copy_system(text, os_name)
    if not copied:
        print("[prompt-automation] Unable to copy text to clipboard. See error log.")
    return

    try:
        if os_name == "Windows":
            try:
                import keyboard  # type: ignore
                keyboard.send("ctrl+v")
            except Exception as e:
                _log.warning("keyboard library failed on Windows: %s", e)
                # Fallback to PowerShell approach
                safe_run(
                    [
                        "powershell.exe",
                        "-Command",
                        "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')",
                    ],
                    check=False,
                )
        elif os_name == "Darwin":
            safe_run(
                ["osascript", "-e", 'tell app "System Events" to keystroke "v" using command down'],
                check=False,
            )
        elif os_name == "Linux" and shutil.which("xdotool"):
            safe_run(["xdotool", "key", "ctrl+v"], check=False)
        elif _is_wsl():
            safe_run(
                [
                    "powershell.exe",
                    "-Command",
                    "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('^v')",
                ],
                check=False,
            )
        else:
            _log.warning("no method to send paste keystroke on %s", os_name)
            print("[prompt-automation] Text copied. Paste manually (Ctrl+V).")
    except Exception as e:  # pragma: no cover - platform specific
        _log.error("sending paste key failed: %s", e)
        print("[prompt-automation] Text copied. Paste manually (Ctrl+V). See error log.")

