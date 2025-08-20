"""Template selection frame placeholder."""
from __future__ import annotations

from typing import Optional, Dict, Any


def build(app) -> Optional[Dict[str, Any]]:  # pragma: no cover - simple placeholder
    """Return a dummy template selection.

    The full selector UI is outside the scope of unit tests; this function acts
    as a stand-in so that :class:`SingleWindowApp` can be instantiated without
    launching complex UI logic."""
    return {}


__all__ = ["build"]
