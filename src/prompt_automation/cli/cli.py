"""Lightweight wrapper used as the console entry point."""
from __future__ import annotations

from . import PromptCLI


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - CLI entry
    """Entry point for ``prompt-automation`` script."""
    PromptCLI().main(argv)


__all__ = ["main"]

