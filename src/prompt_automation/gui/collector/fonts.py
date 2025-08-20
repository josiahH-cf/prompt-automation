"""Compatibility shim re-exporting :func:`get_display_font`.

Legacy code inside ``gui.collector.components`` uses ``from ..fonts import get_display_font``
which resolves to ``prompt_automation.gui.collector.fonts`` (because ``..`` ascends
one level from components to collector). After refactor the actual implementation
lives at ``prompt_automation.gui.fonts`` only, producing
``ModuleNotFoundError: prompt_automation.gui.collector.fonts`` at runtime.

This shim preserves backward compatibility without touching all import sites.
New code should import from ``prompt_automation.gui.fonts`` directly.
"""
from __future__ import annotations

from ..fonts import get_display_font  # re-export underlying helper

__all__ = ["get_display_font"]
