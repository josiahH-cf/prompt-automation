import json
from pathlib import Path
from typing import Any, Dict, Optional

from .renderer import fill_placeholders, load_template
from .variables import get_variables

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "styles"


def list_styles() -> Dict[str, Path]:
    return {p.name: p for p in PROMPTS_DIR.iterdir() if p.is_dir()}


def pick_style() -> Optional[Dict[str, Any]]:
    styles = list(list_styles().keys())
    styles.sort()
    styles.append("99 Create new prompt")
    print("Select style:")
    for idx, name in enumerate(styles, 1):
        print(f"{idx}. {name}")
    choice = input("Enter choice: ")
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(styles):
        return None
    if int(choice) == len(styles):
        create_new_template()
        return None
    style = styles[int(choice) - 1]
    return pick_prompt(style)


def pick_prompt(style: str) -> Optional[Dict[str, Any]]:
    dir_path = PROMPTS_DIR / style
    templates = sorted(dir_path.glob("*.json"))
    if not templates:
        return None
    print("Select prompt:")
    for idx, path in enumerate(templates, 1):
        data = json.loads(path.read_text())
        print(f"{idx}. {data['id']:02d} {data['title']}")
    choice = input("Enter choice: ")
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(templates):
        return None
    tmpl = load_template(templates[int(choice) - 1])
    return tmpl


def render_template(template: Dict[str, Any]) -> str:
    vars = get_variables(template["placeholders"])
    return fill_placeholders(template["template"], vars)


def create_new_template() -> None:
    styles = list_styles()
    print("Existing styles:", ", ".join(styles))
    style = input("Style name: ") or "Misc"
    dir_path = PROMPTS_DIR / style
    dir_path.mkdir(parents=True, exist_ok=True)
    used_ids = {json.loads(p.read_text())["id"] for p in dir_path.glob("*.json")}
    prompt_id = int(input("Prompt ID: "))
    while prompt_id in used_ids:
        prompt_id = int(input("ID in use. Choose another: "))
    title = input("Short title: ")
    lines = []
    print("Enter prompt text, end with a single '.' line:")
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    template = {
        "id": prompt_id,
        "title": title,
        "style": style,
        "role": "",
        "template": lines,
        "placeholders": [],
    }
    path = dir_path / f"{prompt_id:02d}_{title}.json"
    path.write_text(json.dumps(template, indent=2))
    print(f"Created {path}")
