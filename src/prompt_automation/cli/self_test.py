"""Self-test command split out of the main controller."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..menus import list_styles, list_prompts, load_template
from .dependencies import dependency_status


def run_self_test(gui_mode_hint: bool | None = None) -> None:
    styles = list_styles()
    template_files: list[Path] = []
    for s in styles:
        for p in list_prompts(s):
            try:
                data = load_template(p)
                if isinstance(data, dict) and "template" in data:
                    template_files.append(p)
            except Exception:
                pass
    gui_mode = bool(gui_mode_hint) if gui_mode_hint is not None else (
        os.environ.get("PROMPT_AUTOMATION_GUI") != "0"
    )
    dep_status = dependency_status(gui_mode)
    missing_critical = [
        k for k, v in dep_status.items() if v["status"] == "missing"
    ]
    print("=== Self Test Report ===")
    print(f"Styles: {len(styles)} | Templates: {len(template_files)}")
    print("Dependencies:")
    for name, info in sorted(dep_status.items()):
        detail = info["detail"]
        print(
            f"  - {name}: {info['status']} {('- ' + detail) if detail else ''}"
        )
    if missing_critical:
        print("Critical missing dependencies:", ", ".join(missing_critical))
        print("Self test: FAIL")
    else:
        print("Self test: PASS")


__all__ = ["run_self_test"]

