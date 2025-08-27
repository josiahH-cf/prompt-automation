from __future__ import annotations

import subprocess
from pathlib import Path


def _to_espanso(hotkey: str) -> str:
    parts = hotkey.lower().split("+")
    mods, key = parts[:-1], parts[-1]
    if mods:
        return "+".join(f"<{m}>" for m in mods) + "+" + key
    return key


def _update_linux(hotkey: str) -> None:
    trigger = _to_espanso(hotkey)
    match_dir = Path.home() / ".config" / "espanso" / "match"
    match_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = match_dir / "prompt-automation.yml"

    yaml_content = (
        f"matches:\n"
        f"  - trigger: \"{trigger}\"\n"
        f"    run: |\n"
        f"      # Focus existing window if present; else launch GUI; fallback terminal\n"
        f"      prompt-automation --focus || prompt-automation --gui || prompt-automation --terminal\n"
        f"    propagate: false\n"
    )
    yaml_path.write_text(yaml_content)

    try:  # pragma: no cover - external tool
        subprocess.run(
            ["espanso", "restart"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
