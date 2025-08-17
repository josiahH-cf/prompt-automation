"""Template rendering helpers for the CLI."""
from __future__ import annotations

from typing import Any

from ..menus import render_template
from ..gui.file_append import _append_to_files


def render_template_cli(tmpl: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Enhanced CLI template rendering with better prompts."""
    print(f"\nRendering template: {tmpl.get('title', 'Unknown')}")
    print(f"Style: {tmpl.get('style', 'Unknown')}")

    if tmpl.get("placeholders"):
        print(f"\nThis template requires {len(tmpl['placeholders'])} input(s):")
        for ph in tmpl["placeholders"]:
            label = ph.get("label", ph["name"])
            ptype = ph.get("type", "text")
            options = ph.get("options", [])
            multiline = ph.get("multiline", False)

            type_info = ptype
            if multiline:
                type_info += ", multiline"
            if options:
                type_info += f", options: {', '.join(options)}"

            print(f"  - {label} ({type_info})")

        if input("\nProceed with input collection? [Y/n]: ").lower() in {"n", "no"}:
            return None

    return render_template(tmpl, return_vars=True)


__all__ = ["render_template_cli", "_append_to_files"]

