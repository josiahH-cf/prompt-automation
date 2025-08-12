"""Backward-compatible wrapper for legacy template selector import path.

The original implementation grew large; logic now lives in ``gui.selector``.
This module remains to avoid breaking existing imports.
"""
from __future__ import annotations

from .selector import open_template_selector


def select_template_gui():  # pragma: no cover - thin delegator
    return open_template_selector()


__all__ = ["select_template_gui"]
