from __future__ import annotations

"""Helpers to detect developer mode installs.

Dev mode should disable self-update behaviours so local edits are
immediately effective, especially when installed in editable mode
(`pip install -e .` or `pipx install --editable PATH`).
"""

from pathlib import Path
import os


def is_dev_mode() -> bool:
    """Best-effort detection of a developer install.

    Signals considered:
    - ``PROMPT_AUTOMATION_DEV=1`` explicitly enables dev mode.
    - Package path resides in a source tree with a ``.git`` ancestor.
    - PEP 610 direct_url metadata indicates an editable install.
    """
    if os.environ.get("PROMPT_AUTOMATION_DEV") == "1":
        return True

    # Heuristic: imported package path is within a git repo source tree
    try:
        from . import __file__ as pkg_file  # type: ignore

        p = Path(pkg_file).resolve()
        for parent in [p] + list(p.parents):
            if (parent / ".git").exists():
                # Running out of a git checkout (e.g. src/ prompt-automation)
                return True
    except Exception:
        pass

    # PEP 610 direct_url.json may exist and mark editable installs
    try:
        from importlib import metadata as importlib_metadata

        dist = importlib_metadata.distribution("prompt-automation")
        direct_url = None
        try:
            direct_url = dist.read_text("direct_url.json")
        except Exception:
            direct_url = None
        if direct_url:
            import json

            data = json.loads(direct_url)
            dir_info = data.get("dir_info") or {}
            if dir_info.get("editable"):
                return True
            # Local path installs also imply development workflow
            if data.get("url", "").startswith("file:"):
                return True
    except Exception:
        pass

    return False


__all__ = ["is_dev_mode"]

