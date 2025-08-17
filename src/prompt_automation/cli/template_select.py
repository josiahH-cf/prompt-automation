"""Template selection helpers for the CLI."""
from __future__ import annotations

from typing import Any

from .. import logger
from ..menus import list_styles, list_prompts, load_template, PROMPTS_DIR


def select_template_cli() -> dict[str, Any] | None:
    """Enhanced CLI template selection with better navigation."""
    styles = list_styles()
    if not styles:
        print("No template styles found.")
        return None

    usage = logger.usage_counts()
    style_freq = {
        s: sum(c for (pid, st), c in usage.items() if st == s) for s in styles
    }
    sorted_styles = sorted(styles, key=lambda s: (-style_freq.get(s, 0), s.lower()))

    print("\nAvailable Styles:")
    for i, style in enumerate(sorted_styles, 1):
        freq_info = f" ({style_freq[style]} recent)" if style_freq.get(style, 0) > 0 else ""
        print(f"{i:2d}. {style}{freq_info}")

    while True:
        try:
            choice = input(
                f"\nSelect style (1-{len(sorted_styles)}) or press Enter to cancel: "
            ).strip()
            if not choice:
                return None
            if choice.isdigit() and 1 <= int(choice) <= len(sorted_styles):
                selected_style = sorted_styles[int(choice) - 1]
                return pick_prompt_cli(selected_style)
            print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            return None


def pick_prompt_cli(style: str) -> dict[str, Any] | None:
    """Enhanced CLI prompt selection."""
    prompts = list_prompts(style)
    if not prompts:
        print(f"No templates found in style '{style}'.")
        return None

    usage = logger.usage_counts()
    prompt_freq = {
        p.name: usage.get((p.stem.split("_")[0], style), 0) for p in prompts
    }
    sorted_prompts = sorted(
        prompts, key=lambda p: (-prompt_freq.get(p.name, 0), p.name.lower())
    )

    print(f"\nTemplates in '{style}':")
    for i, prompt_path in enumerate(sorted_prompts, 1):
        template = load_template(prompt_path)
        rel = prompt_path.relative_to(PROMPTS_DIR / style)
        rel_display = str(rel.parent) + "/" if str(rel.parent) != "." else ""
        title = template.get("title", prompt_path.stem)
        freq_info = (
            f" ({prompt_freq[prompt_path.name]} recent)"
            if prompt_freq.get(prompt_path.name, 0) > 0
            else ""
        )
        print(f"{i:2d}. {rel_display}{title}{freq_info}")

        if template.get("placeholders"):
            ph_count = len(template["placeholders"])
            print(f"     {ph_count} input(s) required")

    while True:
        try:
            choice = input(
                f"\nSelect template (1-{len(sorted_prompts)}) or press Enter to go back: "
            ).strip()
            if not choice:
                return select_template_cli()
            if choice.isdigit() and 1 <= int(choice) <= len(sorted_prompts):
                return load_template(sorted_prompts[int(choice) - 1])
            print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            return None


__all__ = ["select_template_cli", "pick_prompt_cli"]

