"""Update helpers used by the CLI."""
from __future__ import annotations

import sys
from pathlib import Path
from shutil import which

from .. import hotkeys, update
from ..utils import safe_run
from .dependencies import check_dependencies


def perform_update(args) -> None:  # pragma: no cover - user facing
    """Perform update workflow for the CLI."""

    def _find_local_root(start: Path) -> Path | None:
        try:
            for parent in [start] + list(start.parents):
                cfg = parent / "pyproject.toml"
                if cfg.exists():
                    try:
                        text = cfg.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    if (
                        'name = "prompt-automation"' in text
                        or 'name = "prompt_automation"' in text
                    ):
                        if any(part == "site-packages" for part in parent.parts):
                            return None
                        return parent
            return None
        except Exception:
            return None

    local_root = _find_local_root(Path.cwd())
    performed_local = False
    if local_root and local_root.exists():
        print(
            f"[prompt-automation] Detected local project checkout at {local_root}. Performing editable reinstall..."
        )
        try:
            if which("pipx"):
                res = safe_run(
                    ["pipx", "install", "--force", "--editable", str(local_root)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    print(
                        "[prompt-automation] pipx editable install failed; falling back to pip -e ."
                    )
                    safe_run([sys.executable, "-m", "pip", "install", "-e", str(local_root)])
            else:
                safe_run([sys.executable, "-m", "pip", "install", "-e", str(local_root)])
            performed_local = True
            print("[prompt-automation] Local editable reinstall complete.")
        except Exception as e:
            print(f"[prompt-automation] Local reinstall attempt failed: {e}")

    if not performed_local:
        update.check_and_prompt(force=True)
        print("[prompt-automation] Remote manifest update (if any) applied.")

    print("[prompt-automation] Checking dependencies after update...")
    if not check_dependencies(require_fzf=False):
        print("[prompt-automation] Some dependencies may need to be reinstalled.")

    if not hotkeys.ensure_hotkey_dependencies():
        print(
            "[prompt-automation] Warning: Hotkey dependencies missing. Hotkeys may not work properly."
        )

    hotkeys.update_hotkeys()

    print("[prompt-automation] Update complete!")


__all__ = ["perform_update"]

