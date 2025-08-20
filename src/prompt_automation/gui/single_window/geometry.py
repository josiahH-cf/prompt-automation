from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from ...config import HOME_DIR

SETTINGS_PATH: Final[Path] = HOME_DIR / "gui-settings.json"
DEFAULT_GEOMETRY: Final[str] = "1280x860"


def load_geometry() -> str:
    """Load persisted window geometry.

    Returns default geometry if the settings file is missing or corrupt."""
    try:
        if SETTINGS_PATH.exists():
            data = json.loads(SETTINGS_PATH.read_text())
            geom = data.get("geometry")
            if isinstance(geom, str) and "x" in geom:
                return geom
    except Exception:  # pragma: no cover - best effort
        pass
    return DEFAULT_GEOMETRY


def save_geometry(geometry: str) -> None:
    """Persist the window geometry to the settings file."""
    try:  # pragma: no cover - best effort persistence
        current = {}
        if SETTINGS_PATH.exists():
            try:
                current = json.loads(SETTINGS_PATH.read_text()) or {}
            except Exception:
                current = {}
        current["geometry"] = geometry
        SETTINGS_PATH.write_text(json.dumps(current, indent=2))
    except Exception:
        pass


__all__ = ["load_geometry", "save_geometry", "SETTINGS_PATH", "DEFAULT_GEOMETRY"]
