"""Template rendering helpers for the CLI."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .. import menus


def _append_to_files(var_map: dict[str, Any], text: str) -> None:
    """Append ``text`` to any paths specified by append_file placeholders."""
    for key, path in var_map.items():
        if key == "append_file" or key.endswith("_append_file"):
            if not path:
                continue
            try:
                p = Path(path).expanduser()
                with p.open("a", encoding="utf-8") as fh:
                    if key == "context_append_file":
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        fh.write(f"\n\n--- {ts} ---\n{text}\n")
                    else:
                        fh.write(text + "\n")
            except Exception as e:
                # Log failure silently to avoid cluttering CLI output
                import logging

                logging.getLogger("prompt_automation.cli").warning(
                    "failed to append to %s: %s", path, e
                )


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

    return menus.render_template(tmpl, return_vars=True)


__all__ = ["render_template_cli", "_append_to_files"]

