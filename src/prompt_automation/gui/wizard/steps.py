"""Utility helpers for the template creation wizard.

These functions are intentionally UI-agnostic so they can be unit tested
independently from the Tk based interface.  They mirror a subset of the
logic that used to live in ``new_template_wizard.py``.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable, List

from ...config import PROMPTS_DIR

# Public constants -----------------------------------------------------------
SUGGESTED_PLACEHOLDERS = [
    # 'role' intentionally omitted – no longer auto-included
    "objective",
    "context",
    "instructions",
    "inputs",
    "constraints",
    "output_format",
    "quality_checks",
    "follow_ups",
]


def next_template_id(style_root: Path) -> int:
    """Return the next available positive integer id within ``style_root``.

    The function scans all ``*.json`` files under ``style_root`` looking for an
    ``id`` field.  If none are found the id ``1`` is returned; otherwise the
    maximum id plus one.
    """
    used: set[int] = set()
    if style_root.exists():
        for p in style_root.rglob("*.json"):
            try:
                data = json.loads(p.read_text())
                if (
                    data.get("style") == style_root.name
                    and isinstance(data.get("id"), int)
                    and data["id"] > 0
                ):
                    used.add(int(data["id"]))
            except Exception:
                continue
    return max(used) + 1 if used else 1


def ensure_style(style: str, private: bool = False, base_dir: Path | None = None) -> Path:
    """Create (if necessary) and return the directory for ``style``.

    ``base_dir`` defaults to :data:`PROMPTS_DIR`.  When ``private`` is ``True``
    the style is created under ``base_dir.parent / 'local'``; otherwise under
    ``base_dir`` directly.
    """
    root = base_dir or PROMPTS_DIR
    target_root = root.parent / "local" if private else root
    path = target_root / style
    path.mkdir(parents=True, exist_ok=True)
    return path


def suggest_placeholders(existing: Iterable[str] | None = None) -> List[str]:
    """Return placeholder suggestions not already present.

    ``existing`` is compared case-insensitively.
    """
    existing_set = {e.lower() for e in (existing or [])}
    return [p for p in SUGGESTED_PLACEHOLDERS if p.lower() not in existing_set]


def generate_template_body(placeholders: Iterable[str]) -> str:
    """Return a deterministic body skeleton for ``placeholders``.

    The body simply maps each placeholder name to a ``{{placeholder}}`` token
    separated by newlines.  The order of ``placeholders`` is preserved and the
    function is pure, so repeated calls yield identical results.
    """
    return "\n".join(f"{name}: {{{{{name}}}}}" for name in placeholders)


__all__ = [
    "SUGGESTED_PLACEHOLDERS",
    "next_template_id",
    "ensure_style",
    "suggest_placeholders",
    "generate_template_body",
]
