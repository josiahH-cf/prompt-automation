"""File placeholder handling and global reference helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple, List

from ..errorlog import get_logger

from .gui import _gui_file_prompt
from .storage import (
    _get_template_entry,
    _load_overrides,
    _normalize_reference_path,
    _PERSIST_FILE,
    _save_overrides,
    _set_template_entry,
)


_log = get_logger(__name__)


def _print_one_time_skip_reminder(data: dict, template_id: int, name: str) -> None:
    """Notify user once when a file placeholder is permanently skipped."""
    key = f"{template_id}:{name}"
    reminders = data.setdefault("reminders", {})
    if reminders.get(key):
        return
    reminders[key] = True
    _log.info(
        "Reference file '%s' skipped for template %s. Remove entry in %s to re-enable.",
        name,
        template_id,
        _PERSIST_FILE,
    )
    try:
        import tkinter as tk  # type: ignore
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Reference file skipped",
            f"Reference file ‘{name}’ skipped. Use 'Reset reference files' to re-enable prompts.",
        )
        root.destroy()
    except Exception:
        print(
            f"Reference file ‘{name}’ skipped. Use 'Reset reference files' to re-enable prompts."
        )
    _save_overrides(data)


def _resolve_file_placeholder(ph: Dict[str, Any], template_id: int, globals_map: Dict[str, Any]) -> str:
    name = ph["name"]
    persist_override = bool(ph.get("override") is True)
    if not persist_override:
        label = ph.get("label", name)
        chosen = _gui_file_prompt(label) or input(f"File for {label} (leave blank to skip): ").strip()
        if chosen and Path(chosen).expanduser().exists():
            return str(Path(chosen).expanduser())
        return ""

    overrides = _load_overrides()
    entry = _get_template_entry(overrides, template_id, name) or {}

    if entry.get("skip"):
        _print_one_time_skip_reminder(overrides, template_id, name)
        return ""

    path_str = entry.get("path")
    if path_str:
        p = Path(path_str).expanduser()
        if p.exists():
            return str(p)

    label = ph.get("label", name)
    chosen = _gui_file_prompt(label)
    if not chosen:
        while True:
            choice = input(
                f"No file selected for {label}. (c)hoose again, (s)kip, (p)ermanent skip: "
            ).lower().strip() or "c"
            if choice in {"c", "choose"}:
                chosen = _gui_file_prompt(label) or input(
                    f"Enter path for {label} (blank to cancel): "
                )
                if chosen and Path(chosen).expanduser().exists():
                    break
                if not chosen:
                    continue
            elif choice in {"s", "skip"}:
                return ""
            elif choice in {"p", "perm", "permanent"}:
                _set_template_entry(overrides, template_id, name, {"skip": True})
                _save_overrides(overrides)
                _print_one_time_skip_reminder(overrides, template_id, name)
                return ""
        # fallthrough
    if chosen and Path(chosen).expanduser().exists():
        _set_template_entry(
            overrides,
            template_id,
            name,
            {"path": str(Path(chosen).expanduser()), "skip": False},
        )
        _save_overrides(overrides)
        return str(Path(chosen).expanduser())
    return ""


def get_global_reference_file() -> str | None:
    try:
        data = _load_overrides()
        path = data.get("global_files", {}).get("reference_file")
        if path:
            norm = _normalize_reference_path(path)
            p = Path(norm).expanduser()
            if p.exists():
                if norm != path:
                    try:
                        raw = _load_overrides()
                        raw.setdefault("global_files", {})["reference_file"] = norm
                        _save_overrides(raw)
                    except Exception:
                        pass
                return str(p)
    except Exception:
        pass
    return None


def reset_global_reference_file() -> bool:
    try:
        data = _load_overrides()
        gfiles = data.get("global_files", {})
        if "reference_file" in gfiles:
            gfiles.pop("reference_file", None)
            _save_overrides(data)
            return True
    except Exception:
        pass
    return False
