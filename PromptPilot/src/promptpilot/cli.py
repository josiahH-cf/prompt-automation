from . import menus
from .logger import log_usage

def main() -> None:
    template = menus.pick_style()
    if template is None:
        return
    text = menus.render_template(template)
    if text:
        from .paste import paste_text

        paste_text(text)
        log_usage(template)


if __name__ == "__main__":
    main()
