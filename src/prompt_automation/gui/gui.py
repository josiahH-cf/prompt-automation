"""Lightweight wrapper used as the GUI entry point."""
from __future__ import annotations

from .controller import PromptGUI


def run() -> None:  # pragma: no cover - GUI entry
    """Entry point for ``prompt-automation`` GUI."""
    PromptGUI().run()


__all__ = ["run"]
