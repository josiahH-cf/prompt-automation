"""Uninstall helpers for prompt_automation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .executor import run

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from ..cli.controller import UninstallOptions


def run_uninstall(options: "UninstallOptions") -> int:
    """Entry point for the uninstall routine.

    Returns the exit code from :func:`executor.run`. Any unexpected
    exception results in an exit code greater than ``2``.
    """
    try:
        code, _ = run(options)
        return code
    except Exception:
        return 3


__all__ = ["run_uninstall"]
