import os
import platform

import pyperclip


def paste_text(text: str) -> None:
    pyperclip.copy(text)
    os_name = platform.system()
    if os_name == "Windows":
        try:
            import keyboard

            keyboard.send("ctrl+v")
        except Exception:
            pass
    elif os_name == "Darwin":
        os.system(
            'osascript -e "tell application \"System Events\" to keystroke \"v\" using command down"'
        )
    else:
        os.system("xdotool key ctrl+v")
