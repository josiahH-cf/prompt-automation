from __future__ import annotations

from pathlib import Path
from typing import List

from .. import config
from ..renderer import load_template, is_shareable


def list_styles() -> List[str]:
    """List available prompt styles, with error handling for missing directories."""
    try:
        if not config.PROMPTS_DIR.exists():
            print(f"Warning: Prompts directory not found at {config.PROMPTS_DIR}")
            print("Available search locations were:")
            for i, location in enumerate(config.PROMPTS_SEARCH_PATHS, 1):
                exists = "\u2713" if location.exists() else "\u2717"
                print(f"  {i}. {exists} {location}")
            return []
        return [p.name for p in config.PROMPTS_DIR.iterdir() if p.is_dir()]
    except Exception as e:
        print(f"Error listing styles from {config.PROMPTS_DIR}: {e}")
        return []


def list_prompts(style: str, *, shared_only: bool = False) -> List[Path]:
    """Return all ``.json`` prompt templates under a style folder recursively."""
    base = config.PROMPTS_DIR / style
    if not base.exists():
        return []
    paths = sorted(base.rglob("*.json"))
    if not shared_only:
        return paths
    filtered: List[Path] = []
    for p in paths:
        try:
            data = load_template(p)
            if is_shareable(data, p):
                filtered.append(p)
        except Exception:
            continue
    return filtered


__all__ = ["list_styles", "list_prompts"]
