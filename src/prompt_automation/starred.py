"""Starred template persistence & helpers.

Stores up to 10 relative template paths in PROMPTS_DIR/Settings/starred.json.
Provides toggle and load/save utilities used by the selector view.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import List

from .config import PROMPTS_DIR

SETTINGS_DIR = PROMPTS_DIR / "Settings"
STARRED_FILE = SETTINGS_DIR / "starred.json"
MAX_STARRED = 10


def load_starred() -> List[str]:
    if not STARRED_FILE.exists():
        return []
    try:
        data = json.loads(STARRED_FILE.read_text())
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
    except Exception:
        return []
    return []


def save_starred(paths: List[str]) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    # enforce uniqueness and limit
    cleaned: List[str] = []
    for p in paths:
        if p not in cleaned:
            cleaned.append(p)
        if len(cleaned) >= MAX_STARRED:
            break
    tmp = STARRED_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(cleaned, indent=2), encoding='utf-8')
    tmp.replace(STARRED_FILE)


def toggle_star(rel_path: str) -> bool:
    """Toggle star for a relative path.

    Returns True if now starred, False if unstarred or could not star due to limit.
    """
    rel_path = str(rel_path)
    stars = load_starred()
    if rel_path in stars:
        stars = [p for p in stars if p != rel_path]
        save_starred(stars)
        return False
    # add new
    if len(stars) >= MAX_STARRED:
        return False  # caller will display message
    stars.append(rel_path)
    save_starred(stars)
    return True

__all__ = [
    "load_starred",
    "save_starred",
    "toggle_star",
    "STARRED_FILE",
    "MAX_STARRED",
]
