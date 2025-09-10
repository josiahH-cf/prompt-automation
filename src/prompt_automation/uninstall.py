from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cli.controller import UninstallOptions


def run_uninstall(options: "UninstallOptions") -> None:
    """Placeholder uninstall routine."""
    print(f"Uninstall called with options: {options}")
