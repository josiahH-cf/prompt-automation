"""GUI package providing the :class:`PromptGUI` entry point.

Exports:
	- PromptGUI: High-level GUI workflow controller.
	- run(): Convenience function used by the CLI to start the GUI.

The project previously had an empty top-level module ``gui.py`` which
shadowed this package, causing ``AttributeError: module 'prompt_automation.gui' has no attribute 'run'``.
That file has been removed; ``run`` is now exposed here to keep the CLI
call ``from .. import gui; gui.run()`` working.
"""
from __future__ import annotations

from .controller import PromptGUI  # noqa: F401
from .gui import run  # re-export wrapper function
from . import constants

__all__ = ["PromptGUI", "run", "constants"]
