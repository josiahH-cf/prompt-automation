"""Variable collection frame placeholder."""
from __future__ import annotations

from typing import Dict, Any, Optional


def build(app, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:  # pragma: no cover - placeholder
    """Collect variables for the provided template.

    In this simplified test-friendly version we simply return an empty mapping."""
    return {}


__all__ = ["build"]
