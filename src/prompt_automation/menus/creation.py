from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

from ..config import PROMPTS_DIR
from ..renderer import validate_template

if TYPE_CHECKING:
    from ..types import Template, Placeholder

# NOTE: Slug logic removed. Filenames are now stable once created. We keep a
# tiny helper for backwards compatibility if any external code imported it.
def _slug(text: str) -> str:  # pragma: no cover - legacy shim
    return text


def _check_unique_id(pid: int, exclude: Path | None = None) -> None:
    """Raise ``ValueError`` if ``pid`` already exists (excluding provided path).

    ID range is no longer restricted to 01-98; any positive int is accepted.
    """
    if not isinstance(pid, int) or pid <= 0:
        raise ValueError("Template 'id' must be a positive integer")
    for p in PROMPTS_DIR.rglob("*.json"):
        if exclude and p.resolve() == (exclude.resolve()):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("id") == pid:
                raise ValueError(f"Duplicate id {pid} in {p}")
        except Exception:
            continue


def save_template(data: "Template", orig_path: Path | None = None) -> Path:
    """Persist ``data`` without automatic renaming based on title.

    Rules now:
      - On create (no ``orig_path``): filename = ``<id>.json`` (zero padded to
        at least 2 digits for legacy sort friendliness) under style directory.
      - On update (``orig_path`` provided): reuse the existing filename even if
        ``title`` changed.
    """
    if not validate_template(data):
        raise ValueError("invalid template structure")
    _check_unique_id(data["id"], exclude=orig_path)
    dir_path = PROMPTS_DIR / data["style"]
    dir_path.mkdir(parents=True, exist_ok=True)
    if orig_path and orig_path.exists():
        path = orig_path
    else:
        pid = int(data["id"])
        # Preserve at least two digits for readability; allow growth past 99.
        pad_width = 2 if pid < 100 else len(str(pid))
        fname = f"{pid:0{pad_width}d}.json"
        path = dir_path / fname
    if path.exists() and (not orig_path or orig_path == path):
        # Backup existing when overwriting.
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
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
    """Ensure every template has a unique positive integer ID.

    Behaviour change: No file renaming occurs. Only assigns IDs to files
    missing an integer ``id`` or resolves duplicates by assigning the next
    free integer greater than the current max.
    """
    paths = sorted(base.rglob("*.json"))
    templates: List[tuple[Path, "Template"]] = []
    problems: List[str] = []
    used: set[int] = set()

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            templates.append((path, data))
            if isinstance(data.get("id"), int) and data["id"] > 0:
                if data["id"] in used:
                    # mark duplicate; will fix later
                    pass
                used.add(int(data["id"]))
        except Exception as e:
            problems.append(f"Unreadable JSON: {path} ({e})")

    if used:
        next_id = max(used) + 1
    else:
        next_id = 1

    changes: List[str] = []
    seen: set[int] = set()
    for path, data in templates:
        if "template" not in data:
            continue
        cur = data.get("id")
        if not isinstance(cur, int) or cur <= 0 or cur in seen:
            data["id"] = next_id
            changes.append(f"Assigned id {next_id} -> {path}")
            seen.add(next_id)
            next_id += 1
            try:
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception as e:
                problems.append(f"Failed writing updated id for {path}: {e}")
        else:
            seen.add(cur)

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
    used = {json.loads(p.read_text(encoding="utf-8"))["id"] for p in dir_path.glob("*.json")}
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
    placeholders: List["Placeholder"] = []
    print("Placeholder names comma separated (empty to finish):")
    names = input()
    for name in [n.strip() for n in names.split(",") if n.strip()]:
        placeholders.append({"name": name})
    data: "Template" = {
        "id": int(pid),
        "title": title,
        "style": style,
        "role": role,
        "template": body,
        "placeholders": placeholders,
    }
    # New creation now uses plain id-based filename only.
    pad_width = 2 if int(pid) < 100 else len(str(int(pid)))
    fname = f"{int(pid):0{pad_width}d}.json"
    (dir_path / fname).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Created {fname}")


__all__ = [
    "save_template",
    "delete_template",
    "add_style",
    "delete_style",
    "ensure_unique_ids",
    "create_new_template",
]
