from __future__ import annotations

"""Helpers for building hierarchical list items for the selector UI.

Keeps UI module concise by encapsulating tree traversal and item shaping.
"""

from pathlib import Path
from typing import Dict, List, Tuple

from ... import config
from ...services.hierarchy import HierarchyNode


def find_node_for(tree: HierarchyNode, rel: str) -> HierarchyNode:
    if not rel:
        return tree
    parts = [p for p in Path(rel).parts if p]
    node = tree
    for name in parts:
        found = None
        for ch in node.children:
            if ch.type == "folder" and ch.name == name:
                found = ch
                break
        if found is None:
            return node
        node = found
    return node


def build_browse_items(node: HierarchyNode, cwd_rel: str, expanded: set[str]) -> List[Tuple[str, Dict]]:
    """Return display rows (text, meta) for the current node.

    Rules:
    - Show folders first (indent relative to cwd).
    - If a folder is in expanded set, show its immediate children (folders and templates) indented +1.
    - Do not show templates at the root (cwd) level to reduce clutter; only inside expanded folders or when navigated into the folder (handled by caller by setting cwd_rel).
    """
    rows: List[Tuple[str, Dict]] = []

    def _indent(level: int) -> str:
        return "  " * max(level, 0)

    # Level 0: children of cwd
    for ch in node.children:
        if ch.type != "folder":
            continue
        disp = f"{ch.name}/"
        rows.append((disp, {"type": "folder", "rel": str(Path(cwd_rel) / ch.name), "indent": 0}))
        rel = str(Path(cwd_rel) / ch.name)
        if rel in expanded:
            # Show level-1 children: folders then templates
            for sub in ch.children:
                if sub.type != "folder":
                    continue
                rows.append((f"{_indent(1)}{sub.name}/", {"type": "folder", "rel": str(Path(rel) / sub.name), "indent": 1}))
            for sub in ch.children:
                if sub.type != "template":
                    continue
                name = Path(sub.relpath).name
                rows.append((f"{_indent(1)}{name}", {"type": "template", "path": (config.PROMPTS_DIR / sub.relpath), "indent": 1}))

    # Show templates only when cwd is not root (the caller may build those separately)
    if cwd_rel:
        for ch in node.children:
            if ch.type == "template":
                name = Path(ch.relpath).name
                rows.append((name, {"type": "template", "path": (config.PROMPTS_DIR / ch.relpath), "indent": 0}))

    return rows


def flatten_matches(paths: List[Path], query: str) -> List[Tuple[str, Dict]]:
    q = query.strip().lower()
    rows: List[Tuple[str, Dict]] = []
    if not q:
        return rows
    for p in paths:
        rel = p.relative_to(config.PROMPTS_DIR)
        if q in str(rel).lower():
            rows.append((str(rel), {"type": "template", "path": p, "indent": 0}))
    return rows


__all__ = ["find_node_for", "build_browse_items", "flatten_matches"]
