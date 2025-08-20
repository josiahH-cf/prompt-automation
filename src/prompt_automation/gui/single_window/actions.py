from __future__ import annotations

from typing import Dict, Any

from ... import paste


def copy_paths(var_map: Dict[str, Any]) -> bool:
    """Copy path variables to clipboard.

    Returns True if any paths were copied."""
    paths = [f"{k}={v}" for k, v in var_map.items() if k.endswith("_path") and v]
    if not paths:
        return False
    data = "\n".join(paths)
    try:
        paste.copy_to_clipboard(data)
    except Exception:  # pragma: no cover - clipboard best effort
        return False
    return True


__all__ = ["copy_paths"]
