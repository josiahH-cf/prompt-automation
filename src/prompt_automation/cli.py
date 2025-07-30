"""Command line entrypoint."""
from __future__ import annotations

from pathlib import Path

from . import logger, menus, paste


def main() -> None:
    banner = Path(__file__).with_name("resources").joinpath("banner.txt")
    print(banner.read_text())
    tmpl = menus.pick_style()
    if not tmpl:
        return
    text = menus.render_template(tmpl)
    if text:
        paste.paste_text(text)
        logger.log_usage(tmpl, len(text))


if __name__ == "__main__":
    main()
