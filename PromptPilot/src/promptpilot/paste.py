"""Clipboard helper using pyperclip and keyboard."""
import os
import platform
import subprocess

import pyperclip


def paste_text(text: str) -> None:
    """Copy ``text`` to clipboard and simulate paste."""
    pyperclip.copy(text)
    os_name = platform.system()
    try:
        if os_name == "Windows":
            import keyboard
            keyboard.send("ctrl+v")
        elif os_name == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell app "System Events" to keystroke "v" using command down'],
                check=False,
            )
        else:
            subprocess.run(["xdotool", "key", "ctrl+v"], check=False)
    except Exception:
        pass
