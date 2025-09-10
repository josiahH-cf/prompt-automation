"""Detect orphan prompt-automation executables."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

from .artifacts import Artifact


def _candidate_dirs(platform: str) -> list[Path]:
    home = Path.home()
    if platform.startswith("win"):
        return [home / "Scripts", Path(sys.prefix) / "Scripts"]
    return [home / ".local" / "bin", home / "bin", Path(sys.prefix) / "bin"]


def detect_orphans(platform: str | None = None) -> list[Artifact]:
    """Return orphan executables lacking an importable module.

    Searches common ``bin``/``Scripts`` directories for executables matching
    ``prompt-automation*`` when the ``prompt_automation`` module cannot be
    imported. Each orphan is returned as an :class:`Artifact` with ``kind`` set
    to ``"orphan"``.
    """

    platform = platform or sys.platform

    try:
        if importlib.util.find_spec("prompt_automation") is not None:
            return []
    except Exception:
        pass

    artifacts: list[Artifact] = []
    for directory in _candidate_dirs(platform):
        try:
            if not directory.exists():
                continue
            for path in directory.glob("prompt-automation*"):
                if not path.is_file():
                    continue
                artifacts.append(Artifact(f"orphan-{path.name}", "orphan", path))
        except Exception:
            continue
    return artifacts
