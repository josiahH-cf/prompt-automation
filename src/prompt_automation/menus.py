"""Menu system with fzf and prompt_toolkit fallback."""
from __future__ import annotations

import json
from .utils import safe_run
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import logger
from .renderer import fill_placeholders, load_template, validate_template, read_file_safe
from .variables import get_variables

# Try to find prompts directory in multiple locations
def _find_prompts_dir():
    # Environment variable override
    env_path = os.environ.get("PROMPT_AUTOMATION_PROMPTS")
    if env_path:
        env_prompts = Path(env_path)
        if env_prompts.exists():
            return env_prompts
    
    # List of potential locations in order of preference
    locations = [
        # Development structure (3 levels up from this file)
        Path(__file__).resolve().parent.parent.parent / "prompts" / "styles",
        
        # Packaged installation - data files location
        Path(__file__).resolve().parent / "prompts" / "styles",
        
        # Alternative package location (in site-packages)
        Path(__file__).resolve().parent.parent / "prompts" / "styles",
        
        # pipx virtual environment location
        Path(__file__).resolve().parent.parent.parent / "Lib" / "prompts" / "styles",
        
        # User's home directory
        Path.home() / ".prompt-automation" / "prompts" / "styles",
        Path.home() / ".local" / "share" / "prompt-automation" / "prompts" / "styles",
        
        # System-wide locations
        Path("/usr/local/share/prompt-automation/prompts/styles"),
        Path("C:/ProgramData/prompt-automation/prompts/styles"),  # Windows system-wide
    ]
    
    # Try each location
    for location in locations:
        if location.exists() and location.is_dir():
            return location
    
    # If none exist, return the development location as fallback
    return locations[0]

DEFAULT_PROMPTS_DIR = _find_prompts_dir()
PROMPTS_DIR = Path(os.environ.get("PROMPT_AUTOMATION_PROMPTS", DEFAULT_PROMPTS_DIR))


def _run_picker(items: List[str], title: str) -> Optional[str]:
    """Return selected item using ``fzf`` or simple input."""
    try:
        res = safe_run(
            ["fzf", "--prompt", f"{title}> "],
            input="\n".join(it.replace("\n", " ") for it in items),
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
    """List available prompt styles, with error handling for missing directories."""
    try:
        if not PROMPTS_DIR.exists():
            print(f"Warning: Prompts directory not found at {PROMPTS_DIR}")
            print("Available search locations were:")
            for i, location in enumerate([
                Path(__file__).resolve().parent.parent.parent / "prompts" / "styles",
                Path(__file__).resolve().parent / "prompts" / "styles",
                Path(__file__).resolve().parent.parent / "prompts" / "styles",
                Path.home() / ".prompt-automation" / "prompts" / "styles",
            ], 1):
                exists = "✓" if location.exists() else "✗"
                print(f"  {i}. {exists} {location}")
            return []
        
        return [p.name for p in PROMPTS_DIR.iterdir() if p.is_dir()]
    except Exception as e:
        print(f"Error listing styles from {PROMPTS_DIR}: {e}")
        return []


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


def render_template(tmpl: Dict[str, Any], values: Dict[str, Any] | None = None) -> str:
    """Render ``tmpl`` using provided ``values`` for placeholders.

    If ``values`` is ``None`` any missing variables will be collected via
    :func:`variables.get_variables` which falls back to GUI/CLI prompts.
    """

    vars = get_variables(tmpl.get("placeholders", []), initial=values)
    for ph in tmpl.get("placeholders", []):
        if ph.get("type") == "file":
            name = ph["name"]
            path = vars.get(name)
            if path:
                vars[name] = read_file_safe(path)
            else:
                vars[name] = ""
    return fill_placeholders(tmpl["template"], vars)


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def _check_unique_id(pid: int, exclude: Path | None = None) -> None:
    """Raise ``ValueError`` if ``pid`` already exists in prompts (excluding path)."""
    for p in PROMPTS_DIR.rglob("*.json"):
        if exclude and p.resolve() == exclude.resolve():
            continue
        try:
            data = json.loads(p.read_text())
            if data.get("id") == pid:
                raise ValueError(f"Duplicate id {pid} in {p}")
        except Exception:
            continue


def save_template(data: Dict[str, Any], orig_path: Path | None = None) -> Path:
    """Write ``data`` to disk with validation and backup."""
    if not validate_template(data):
        raise ValueError("invalid template structure")
    _check_unique_id(data["id"], exclude=orig_path)
    dir_path = PROMPTS_DIR / data["style"]
    dir_path.mkdir(parents=True, exist_ok=True)
    fname = f"{int(data['id']):02d}_{_slug(data['title'])}.json"
    path = dir_path / fname
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    if orig_path and orig_path.exists() and orig_path != path:
        shutil.copy2(orig_path, orig_path.with_suffix(orig_path.suffix + ".bak"))
        orig_path.unlink()
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
    """Raise ``ValueError`` if duplicate template IDs are found."""
    seen: Dict[int, Path] = {}
    for path in base.rglob("*.json"):
        data = json.loads(path.read_text())
        pid = data["id"]
        if pid in seen:
            raise ValueError(f"Duplicate id {pid} in {path} and {seen[pid]}")
        seen[pid] = path


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


