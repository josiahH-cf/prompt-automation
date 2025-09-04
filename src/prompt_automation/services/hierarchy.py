from __future__ import annotations

"""Filesystem-backed hierarchical template scanner with caching.

Returns a nested structure of folders and templates under PROMPTS_DIR, with
stable ordering and security checks (no symlinked directories; no traversal).
"""

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from ..config import PROMPTS_DIR
from ..errorlog import get_logger

_log = get_logger(__name__)


@dataclass
class HierarchyNode:
    type: str  # "folder" | "template"
    name: str
    relpath: str
    children: List["HierarchyNode"] = field(default_factory=list)


def _numeric_prefix(name: str) -> Tuple[int, str]:
    m = re.match(r"^(\d+)_", name)
    if m:
        try:
            return int(m.group(1)), name
        except Exception:
            pass
    return (10**9, name)  # large default to sort after numeric prefixes


def _sort_key(node: HierarchyNode) -> Tuple[int, Tuple[int, str]]:
    if node.type == "folder":
        return (0, (0, node.name.lower()))
    # templates after folders; by numeric prefix, then name
    return (1, _numeric_prefix(node.name))


class _Cache:
    def __init__(self, ttl: int = 5):
        self.ttl = ttl
        self._stamp = 0.0
        self._tree: Optional[HierarchyNode] = None
        self._sig: Optional[int] = None

    def get(self) -> Optional[HierarchyNode]:
        if self._tree is None:
            return None
        if (time.time() - self._stamp) > self.ttl:
            return None
        return self._tree

    def set(self, tree: HierarchyNode, sig: int) -> None:
        self._tree = tree
        self._stamp = time.time()
        self._sig = sig

    def invalidate(self) -> None:
        self._tree = None
        self._sig = None
        self._stamp = 0.0


class TemplateHierarchyScanner:
    def __init__(self, root: Path | None = None, cache_ttl: int = 5, time_fn: Callable[[], float] | None = None):
        self.root = (root or PROMPTS_DIR).resolve()
        self.cache = _Cache(cache_ttl)
        self._time = time_fn or (lambda: time.perf_counter())

    def invalidate(self) -> None:
        self.cache.invalidate()

    def _build_signature(self) -> int:
        # Composite signature: sum of mtimes for immediate children. Fast heuristic; not cryptographic.
        sig = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.root):
                # skip Settings/settings.json from signature noise
                filenames = [f for f in filenames if not (f.lower() == "settings.json" and Path(dirpath).endswith("Settings"))]
                for name in dirnames + filenames:
                    try:
                        p = Path(dirpath) / name
                        st = p.lstat()
                        sig ^= int(st.st_mtime_ns) & 0xFFFFFFFF
                    except Exception:
                        continue
        except Exception:
            pass
        return sig

    def _scan_dir(self, base: Path, rel: Path = Path("")) -> HierarchyNode:
        children: List[HierarchyNode] = []
        try:
            with os.scandir(base) as it:
                for entry in it:
                    try:
                        if entry.name.startswith("."):
                            continue
                        p = Path(entry.path)
                        # Reject symlinked directories for safety
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            node = self._scan_dir(p, rel / entry.name)
                            # Skip empty Settings folder noise
                            if node.children or entry.name != "Settings":
                                children.append(node)
                        elif entry.is_file() and entry.name.endswith(".json"):
                            if entry.name.lower() == "settings.json" and rel.name == "Settings":
                                continue
                            node = HierarchyNode(
                                type="template",
                                name=entry.name,
                                relpath=str((rel / entry.name).as_posix()),
                            )
                            children.append(node)
                    except Exception:
                        continue
        except FileNotFoundError:
            pass
        # Sort
        children.sort(key=_sort_key)
        return HierarchyNode(type="folder", name=base.name if rel != Path("") else "", relpath=str(rel.as_posix()), children=children)

    def scan(self) -> HierarchyNode:
        start = self._time()
        cached = self.cache.get()
        if cached is not None:
            try:
                _log.debug("%s", {"event": "hierarchy.scan.cache_hit"})
            except Exception:
                pass
            return cached
        sig = self._build_signature()
        tree = self._scan_dir(self.root)
        self.cache.set(tree, sig)
        end = self._time()
        # Metrics
        def _count(node: HierarchyNode) -> Tuple[int, int]:
            fcnt = 0
            tcnt = 0
            for ch in node.children:
                if ch.type == "folder":
                    c_f, c_t = _count(ch)
                    fcnt += 1 + c_f
                    tcnt += c_t
                else:
                    tcnt += 1
            return fcnt, tcnt

        folders, templates = _count(tree)
        try:
            _log.info(
                "%s",
                {
                    "event": "hierarchy.scan.success",
                    "duration_ms": int((end - start) * 1000),
                    "folder_count": folders,
                    "template_count": templates,
                },
            )
        except Exception:
            pass
        return tree

    def list_flat(self) -> List[Path]:
        # Preserve existing flat behavior, skipping settings.json inside Settings
        results: List[Path] = []
        for p in self.root.rglob("*.json"):
            if p.name.lower() == "settings.json" and p.parent.name == "Settings":
                continue
            results.append(p)
        return sorted(results)


__all__ = ["TemplateHierarchyScanner", "HierarchyNode"]

