"""Hierarchical template selection widgets and controller.

This package historically exposed ``open_template_selector`` directly at the
package root. The refactor split controller and view layers causing circular
imports during test collection. We now provide a lightweight proxy that lazily
loads the controller when first invoked to avoid import cycles.
"""
from __future__ import annotations

from typing import Any, Optional


def open_template_selector(*args: Any, **kwargs: Any) -> Optional[dict]:  # pragma: no cover - thin proxy
	from .controller import open_template_selector as _impl
	return _impl(*args, **kwargs)


__all__ = ["open_template_selector"]
