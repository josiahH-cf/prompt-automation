"""CLI package providing the :class:`PromptCLI` entry point.

This shim now re-exports PromptCLI from controller.py to keep file size small.
"""
from __future__ import annotations

from .controller import PromptCLI  # noqa: F401
# Backwards-compat re-exports used by tests and scripts that patch these
# directly off the package module.
from .dependencies import check_dependencies, dependency_status  # noqa: F401
from .. import updater  # noqa: F401
from .. import update as update  # noqa: F401
from ..update import check_and_prompt as _check_and_prompt  # noqa: F401
from ..menus import ensure_unique_ids  # noqa: F401

# Back-compat aliases used in tests
manifest_update = update  # type: ignore

__all__ = [
    "PromptCLI",
    "check_dependencies",
    "dependency_status",
    "updater",
    "update",
    "manifest_update",
    "ensure_unique_ids",
]
