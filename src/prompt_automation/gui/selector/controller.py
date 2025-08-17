"""High-level orchestration between selector view and service."""
from __future__ import annotations
from typing import Optional

from . import view, service


def open_template_selector() -> Optional[dict]:
    """Open the template selector GUI and return chosen template data."""
    return view.open_template_selector(service)


__all__ = ["open_template_selector"]
