"""Utility to switch between terminal and GUI modes."""
from __future__ import annotations

import argparse
from pathlib import Path


CONFIG_DIR = Path.home() / ".prompt-automation"
ENV_FILE = CONFIG_DIR / "environment"


def set_mode(mode: str) -> None:
    """Set the default mode for prompt-automation."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if mode == "gui":
        ENV_FILE.write_text("PROMPT_AUTOMATION_GUI=1\n")
        print("[prompt-automation] Default mode set to GUI")
    elif mode == "terminal":
        if ENV_FILE.exists():
            content = ENV_FILE.read_text()
            lines = [line for line in content.splitlines() 
                    if not line.startswith("PROMPT_AUTOMATION_GUI")]
            ENV_FILE.write_text("\n".join(lines) + "\n" if lines else "")
        print("[prompt-automation] Default mode set to terminal")
    else:
        raise ValueError(f"Invalid mode: {mode}. Use 'gui' or 'terminal'")


def get_current_mode() -> str:
    """Get the current default mode."""
    if ENV_FILE.exists():
        content = ENV_FILE.read_text()
        for line in content.splitlines():
            if line.startswith("PROMPT_AUTOMATION_GUI="):
                return "gui"
    return "terminal"


def main() -> None:
    """CLI entry point for mode switching."""
    parser = argparse.ArgumentParser(
        prog="prompt-automation-mode",
        description="Switch between terminal and GUI modes for prompt-automation"
    )
    parser.add_argument(
        "mode",
        choices=["gui", "terminal", "status"],
        help="Mode to set or 'status' to check current mode"
    )
    
    args = parser.parse_args()
    
    if args.mode == "status":
        current = get_current_mode()
        print(f"Current default mode: {current}")
    else:
        set_mode(args.mode)


if __name__ == "__main__":
    main()
