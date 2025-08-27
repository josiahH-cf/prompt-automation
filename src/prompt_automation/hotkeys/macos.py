from __future__ import annotations

from pathlib import Path


def _update_macos(hotkey: str) -> None:  # pragma: no cover - macOS specific
    script_dir = Path.home() / "Library" / "Application Scripts" / "prompt-automation"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "macos.applescript"

    applescript_content = (
        'on run\n'
        '    try\n'
    '        do shell script "prompt-automation --focus || prompt-automation --gui &"\n'
        '    on error\n'
        '        try\n'
        '            do shell script "prompt-automation --terminal &"\n'
        '        on error\n'
        '            display dialog "prompt-automation failed to start. Please check installation." buttons {"OK"} default button "OK"\n'
        '        end try\n'
        '    end try\n'
        'end run\n'
    )
    script_path.write_text(applescript_content)
    print(
        "[prompt-automation] macOS hotkey updated. Assign the new hotkey via System Preferences > Keyboard > Shortcuts."
    )
