"""Override and logging maintenance commands for CLI split out for size."""
from __future__ import annotations

import json
from typing import Iterable

from .. import logger
from ..variables import (
    reset_file_overrides,
    reset_single_file_override,
    list_file_overrides,
)


def clear_usage_log() -> None:
    logger.clear_usage_log()
    print("[prompt-automation] usage log cleared")


def clear_all_overrides() -> None:
    if reset_file_overrides():
        print("[prompt-automation] reference file overrides cleared")
    else:
        print("[prompt-automation] no overrides to clear")


def clear_one_override(tid: str, name: str) -> None:
    if not tid.isdigit():
        print("[prompt-automation] TEMPLATE_ID must be an integer")
        return
    removed = reset_single_file_override(int(tid), name)
    if removed:
        print(f"[prompt-automation] override removed for template {tid} placeholder '{name}'")
    else:
        print(f"[prompt-automation] no override found for template {tid} placeholder '{name}'")


def show_overrides() -> None:
    rows = list_file_overrides()
    if not rows:
        print("[prompt-automation] no overrides present")
    else:
        print("TemplateID | Placeholder | Data")
        for tid, name, info in rows:
            print(f"{tid:>9} | {name:<12} | {json.dumps(info)}")


__all__ = [
    "clear_usage_log",
    "clear_all_overrides",
    "clear_one_override",
    "show_overrides",
]

