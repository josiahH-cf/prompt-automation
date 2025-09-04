from __future__ import annotations

"""Filesystem CRUD operations for hierarchical templates under PROMPTS_DIR.

All operations are sandboxed to the configured root and validated for safety.
"""

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..config import PROMPTS_DIR
from ..errorlog import get_logger

_log = get_logger(__name__)

FOLDER_NAME_REGEX = re.compile(r"^[A-Za-z0-9._-]+$")


class HierarchyError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass
class TemplateFSService:
    root: Path = PROMPTS_DIR
    on_change: Optional[Callable[[], None]] = None

    def _resolve_safe(self, rel: str) -> Path:
        if ".." in rel.split("/"):
            raise HierarchyError("E_UNSAFE_PATH", "Path traversal detected")
        rp = (self.root / rel).resolve()
        try:
            rp.relative_to(self.root.resolve())
        except Exception:
            raise HierarchyError("E_UNSAFE_PATH", "Resolved path outside root")
        return rp

    def _validate_folder_name(self, name: str) -> None:
        if not FOLDER_NAME_REGEX.match(name):
            raise HierarchyError("E_INVALID_NAME", f"Invalid folder name: {name}")

    def _validate_template_name(self, filename: str) -> None:
        if not filename.endswith(".json"):
            raise HierarchyError("E_INVALID_NAME", "Template file must end with .json")
        stem = Path(filename).stem
        if not FOLDER_NAME_REGEX.match(stem):
            raise HierarchyError("E_INVALID_NAME", f"Invalid template name: {stem}")

    def _emit(self, event: str, **fields):
        payload = {"event": event}
        payload.update(fields)
        try:
            _log.info("%s", payload)
        except Exception:
            pass

    # Folder ops
    def create_folder(self, rel: str) -> Path:
        path = self._resolve_safe(rel)
        self._validate_folder_name(path.name)
        if path.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Folder exists: {rel}")
        path.mkdir(parents=True, exist_ok=False)
        self._emit("hierarchy.crud.success", op="create_folder", path=str(rel))
        if self.on_change:
            self.on_change()
        return path

    def rename_folder(self, rel: str, new_name: str) -> Path:
        src = self._resolve_safe(rel)
        if not src.is_dir():
            raise HierarchyError("E_NOT_FOUND", f"Folder not found: {rel}")
        self._validate_folder_name(new_name)
        dst = src.with_name(new_name)
        if dst.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Target exists: {dst.relative_to(self.root)}")
        src.rename(dst)
        self._emit("hierarchy.crud.success", op="rename_folder", path=str(rel), new=str(dst.relative_to(self.root)))
        if self.on_change:
            self.on_change()
        return dst

    def move_folder(self, src_rel: str, dst_parent_rel: str) -> Path:
        src = self._resolve_safe(src_rel)
        dst_parent = self._resolve_safe(dst_parent_rel)
        if not src.is_dir():
            raise HierarchyError("E_NOT_FOUND", f"Folder not found: {src_rel}")
        if not dst_parent.is_dir():
            raise HierarchyError("E_NOT_FOUND", f"Destination not a folder: {dst_parent_rel}")
        dst = dst_parent / src.name
        if dst.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Target exists: {dst.relative_to(self.root)}")
        shutil.move(str(src), str(dst))
        self._emit("hierarchy.crud.success", op="move_folder", src=str(src_rel), dst=str(dst.relative_to(self.root)))
        if self.on_change:
            self.on_change()
        return dst

    def delete_folder(self, rel: str, recursive: bool = False) -> None:
        path = self._resolve_safe(rel)
        if not path.exists() or not path.is_dir():
            raise HierarchyError("E_NOT_FOUND", f"Folder not found: {rel}")
        if any(path.iterdir()) and not recursive:
            raise HierarchyError("E_NOT_EMPTY", f"Folder not empty: {rel}")
        shutil.rmtree(path)
        self._emit("hierarchy.crud.success", op="delete_folder", path=str(rel))
        if self.on_change:
            self.on_change()

    # Template ops
    def create_template(self, rel: str, payload: dict | None = None) -> Path:
        path = self._resolve_safe(rel)
        self._validate_template_name(path.name)
        if path.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Template exists: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = payload or {"id": 0, "title": "Untitled", "style": path.parent.name, "template": [], "placeholders": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._emit("hierarchy.crud.success", op="create_template", path=str(rel))
        if self.on_change:
            self.on_change()
        return path

    def rename_template(self, rel: str, new_name: str) -> Path:
        src = self._resolve_safe(rel)
        if not src.exists() or not src.is_file():
            raise HierarchyError("E_NOT_FOUND", f"Template not found: {rel}")
        self._validate_template_name(new_name)
        dst = src.with_name(new_name)
        if dst.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Target exists: {dst.relative_to(self.root)}")
        src.rename(dst)
        self._emit("hierarchy.crud.success", op="rename_template", path=str(rel), new=str(dst.relative_to(self.root)))
        if self.on_change:
            self.on_change()
        return dst

    def move_template(self, src_rel: str, dst_rel: str) -> Path:
        src = self._resolve_safe(src_rel)
        dst = self._resolve_safe(dst_rel)
        if not src.exists() or not src.is_file():
            raise HierarchyError("E_NOT_FOUND", f"Template not found: {src_rel}")
        if not dst.name.endswith(".json"):
            raise HierarchyError("E_INVALID_NAME", "Destination must be a .json path")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Target exists: {dst_rel}")
        shutil.move(str(src), str(dst))
        self._emit("hierarchy.crud.success", op="move_template", src=str(src_rel), dst=str(dst_rel))
        if self.on_change:
            self.on_change()
        return dst

    def duplicate_template(self, src_rel: str, dst_rel: str | None = None) -> Path:
        src = self._resolve_safe(src_rel)
        if not src.exists() or not src.is_file():
            raise HierarchyError("E_NOT_FOUND", f"Template not found: {src_rel}")
        if dst_rel is None:
            dst_rel = str(Path(src_rel).with_stem(Path(src_rel).stem + "_copy"))
        dst = self._resolve_safe(dst_rel)
        self._validate_template_name(dst.name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise HierarchyError("E_NAME_EXISTS", f"Target exists: {dst_rel}")
        shutil.copy2(src, dst)
        self._emit("hierarchy.crud.success", op="duplicate_template", src=str(src_rel), dst=str(dst_rel))
        if self.on_change:
            self.on_change()
        return dst

    def delete_template(self, rel: str) -> None:
        path = self._resolve_safe(rel)
        if not path.exists() or not path.is_file():
            raise HierarchyError("E_NOT_FOUND", f"Template not found: {rel}")
        path.unlink()
        self._emit("hierarchy.crud.success", op="delete_template", path=str(rel))
        if self.on_change:
            self.on_change()


__all__ = ["TemplateFSService", "HierarchyError", "FOLDER_NAME_REGEX"]

