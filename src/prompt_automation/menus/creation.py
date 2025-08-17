from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from ..config import PROMPTS_DIR
from ..renderer import validate_template


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def _check_unique_id(pid: int, exclude: Path | None = None) -> None:
    """Raise ``ValueError`` if ``pid`` already exists in prompts (excluding path)."""
    for p in PROMPTS_DIR.rglob("*.json"):
        if exclude and p.resolve() == exclude.resolve():
            continue
        try:
            data = json.loads(p.read_text())
            if data.get("id") == pid:
                raise ValueError(f"Duplicate id {pid} in {p}")
        except Exception:
            continue


def save_template(data: Dict[str, Any], orig_path: Path | None = None) -> Path:
    """Write ``data`` to disk with validation and backup."""
    if not validate_template(data):
        raise ValueError("invalid template structure")
    _check_unique_id(data["id"], exclude=orig_path)
    dir_path = PROMPTS_DIR / data["style"]
    dir_path.mkdir(parents=True, exist_ok=True)
    fname = f"{int(data['id']):02d}_{_slug(data['title'])}.json"
    path = dir_path / fname
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    if orig_path and orig_path.exists() and orig_path != path:
        shutil.copy2(orig_path, orig_path.with_suffix(orig_path.suffix + ".bak"))
        orig_path.unlink()
    path.write_text(json.dumps(data, indent=2))
    return path


def delete_template(path: Path) -> None:
    """Remove ``path`` after creating a backup."""
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        path.unlink()


def add_style(name: str) -> Path:
    path = PROMPTS_DIR / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def delete_style(name: str) -> None:
    path = PROMPTS_DIR / name
    if any(path.iterdir()):
        raise OSError("style folder not empty")
    path.rmdir()


def ensure_unique_ids(base: Path = PROMPTS_DIR) -> None:
    """Ensure every template has a unique ID."""
    paths = sorted(base.rglob("*.json"))
    used_ids_global: set[int] = set()
    changes: List[str] = []
    problems: List[str] = []

    templates: List[tuple[Path, Dict[str, Any]]] = []
    for path in paths:
        try:
            data = json.loads(path.read_text())
            templates.append((path, data))
        except Exception as e:
            problems.append(f"Unreadable JSON: {path} ({e})")

    def next_free_id() -> int | None:
        for i in range(1, 99):
            if i not in used_ids_global:
                return i
        return None

    for path, data in templates:
        if "template" not in data or data.get("type") == "globals":
            continue
        orig_id = data.get("id")
        if not isinstance(orig_id, int):
            new_id = next_free_id()
            if new_id is None:
                raise ValueError("No free IDs (01-98) remain to assign missing id")
            data["id"] = new_id
            used_ids_global.add(new_id)
            changes.append(f"Assigned missing id {new_id:02d} -> {path}")
        else:
            if orig_id in used_ids_global:
                new_id = next_free_id()
                if new_id is None:
                    raise ValueError(
                        f"Duplicate id {orig_id:02d} in {path} and elsewhere; no free IDs left"
                    )
                data["id"] = new_id
                used_ids_global.add(new_id)
                changes.append(
                    f"Reassigned duplicate id {orig_id:02d} -> {new_id:02d} in {path}"
                )
            else:
                used_ids_global.add(orig_id)

    for path, data in templates:
        if "template" not in data:
            continue
        try:
            pid = data["id"]
            title = data.get("title")
            if not title and path.name.startswith(f"{int(pid):02d}_"):
                expected_name = path.name
            else:
                slug_title = _slug(title or path.stem)
                expected_name = f"{int(pid):02d}_{slug_title}.json"
            if path.name != expected_name:
                new_path = path.with_name(expected_name)
                path.write_text(json.dumps(data, indent=2))
                if new_path.exists() and new_path != path:
                    backup = new_path.with_suffix(new_path.suffix + ".bak")
                    shutil.copy2(new_path, backup)
                if new_path != path:
                    path.rename(new_path)
                    changes.append(f"Renamed {path.name} -> {new_path.name}")
            else:
                path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            problems.append(f"Failed updating {path}: {e}")

    if problems:
        print("[prompt-automation] Issues during ID check:")
        for p in problems:
            print("  -", p)
    if changes:
        print("[prompt-automation] Template ID adjustments:")
        for c in changes:
            print("  -", c)


def create_new_template() -> None:
    style = input("Style: ") or "Misc"
    dir_path = PROMPTS_DIR / style
    dir_path.mkdir(parents=True, exist_ok=True)
    used = {json.loads(p.read_text())["id"] for p in dir_path.glob("*.json")}
    pid = input("Two digit ID (01-98): ")
    while not pid.isdigit() or not (1 <= int(pid) <= 98) or int(pid) in used:
        pid = input("ID taken or invalid, choose another: ")
    title = input("Title: ")
    role = input("Role: ")
    body: List[str] = []
    print("Template lines, end with '.' on its own:")
    while True:
        line = input()
        if line == ".":
            break
        body.append(line)
    placeholders: List[Dict[str, Any]] = []
    print("Placeholder names comma separated (empty to finish):")
    names = input()
    for name in [n.strip() for n in names.split(",") if n.strip()]:
        placeholders.append({"name": name})
    data = {
        "id": int(pid),
        "title": title,
        "style": style,
        "role": role,
        "template": body,
        "placeholders": placeholders,
    }
    fname = f"{int(pid):02d}_{_slug(title)}.json"
    (dir_path / fname).write_text(json.dumps(data, indent=2))
    print(f"Created {fname}")


__all__ = [
    "save_template",
    "delete_template",
    "add_style",
    "delete_style",
    "ensure_unique_ids",
    "create_new_template",
]
