"""Menu system with fzf and prompt_toolkit fallback."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import logger
from .renderer import fill_placeholders, load_template
from .variables import get_variables

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "styles"


def _run_picker(items: List[str], title: str) -> Optional[str]:
    """Return selected item using ``fzf`` or simple input."""
    try:
        res = subprocess.run(
            ["fzf", "--prompt", f"{title}> "],
            input="\n".join(items),
            text=True,
            capture_output=True,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    # fallback
    print(title)
    for i, it in enumerate(items, 1):
        print(f"{i}. {it}")
    sel = input("Select: ")
    if sel.isdigit() and 1 <= int(sel) <= len(items):
        return items[int(sel) - 1]
    return None


def _freq_sorted(names: List[str], freq: Dict[str, int]) -> List[str]:
    return sorted(names, key=lambda n: (-freq.get(n, 0), n.lower()))


def list_styles() -> List[str]:
    return [p.name for p in PROMPTS_DIR.iterdir() if p.is_dir()]


def list_prompts(style: str) -> List[Path]:
    return sorted((PROMPTS_DIR / style).glob("*.json"))


def pick_style() -> Optional[Dict[str, Any]]:
    usage = logger.usage_counts()
    style_freq = {s: sum(c for (pid, st), c in usage.items() if st == s) for s in list_styles()}
    styles = _freq_sorted(list_styles(), style_freq)
    styles.append("99 Create new template")
    sel = _run_picker(styles, "Style")
    if not sel:
        return None
    if sel.startswith("99") or sel.startswith("Create"):
        create_new_template()
        return None
    return pick_prompt(sel)


def pick_prompt(style: str) -> Optional[Dict[str, Any]]:
    usage = logger.usage_counts()
    prompts = list_prompts(style)
    freq = {p.name: usage.get((p.stem.split("_")[0], style), 0) for p in prompts}
    ordered = _freq_sorted([p.name for p in prompts], freq)
    sel = _run_picker(ordered, f"{style} prompt")
    if not sel:
        return None
    path = (PROMPTS_DIR / style / sel)
    return load_template(path)


def render_template(tmpl: Dict[str, Any]) -> str:
    vars = get_variables(tmpl.get("placeholders", []))
    return fill_placeholders(tmpl["template"], vars)


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


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
    body = []
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

