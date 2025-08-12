"""Utility to configure the default system hotkey."""

from prompt_automation import hotkeys


def configure_hotkey(combo: str = "ctrl+shift+j") -> None:
    """Update the system hotkey mapping.

    Parameters
    ----------
    combo: str
        Key combination to register.
    """
    hotkeys.update_system_hotkey(combo)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure system hotkey")
    parser.add_argument("--hotkey", default="ctrl+shift+j", help="Key combo to register")
    args = parser.parse_args()
    configure_hotkey(args.hotkey)
    print("Global hotkey configured successfully")
