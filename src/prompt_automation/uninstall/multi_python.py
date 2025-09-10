"""Helpers for interacting with multiple Python interpreters during uninstall."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
from typing import Iterable, Tuple, List


def enumerate_pythons() -> list[Path]:
    """Return a list of available Python interpreter executables."""
    seen: set[Path] = set()
    executables: list[Path] = []
    # include current interpreter first
    current = Path(sys.executable).resolve()
    seen.add(current)
    executables.append(current)

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        try:
            for name in os.listdir(directory):
                if not name.startswith("python"):
                    continue
                candidate = Path(directory) / name
                if not candidate.is_file():
                    continue
                try:
                    st = candidate.stat()
                    if not os.access(str(candidate), os.X_OK):
                        continue
                except OSError:
                    continue
                resolved = candidate.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                executables.append(resolved)
        except (OSError, FileNotFoundError):
            continue
    return executables


def uninstall(interpreter: Path) -> tuple[bool, str]:
    """Run pip uninstall for ``prompt-automation`` using the given interpreter.

    Returns a tuple ``(success, output)`` where ``success`` indicates
    whether the command completed successfully and ``output`` contains
    combined stdout/stderr text.
    """
    try:
        proc = subprocess.run(
            [str(interpreter), "-m", "pip", "uninstall", "-y", "prompt-automation"],
            capture_output=True,
            text=True,
        )
        output = proc.stdout + proc.stderr
        return proc.returncode == 0, output
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)
