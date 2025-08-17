from __future__ import annotations

from typing import Any, Dict, List, Optional

from .. import logger
from ..utils import safe_run
from ..config import PROMPTS_DIR
from ..renderer import load_template

from .listing import list_styles, list_prompts
from .creation import create_new_template


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
    print(title)
    for i, it in enumerate(items, 1):
        print(f"{i}. {it}")
    sel = input("Select: ")
    if sel.isdigit() and 1 <= int(sel) <= len(items):
        return items[int(sel) - 1]
    return None


def _freq_sorted(names: List[str], freq: Dict[str, int]) -> List[str]:
    return sorted(names, key=lambda n: (-freq.get(n, 0), n.lower()))


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
    rel_map = {str(p.relative_to(PROMPTS_DIR / style)): p for p in prompts}
    freq = {
        rel: usage.get((orig.stem.split("_")[0], style), 0)
        for rel, orig in rel_map.items()
    }
    ordered = _freq_sorted(list(rel_map.keys()), freq)
    sel = _run_picker(ordered, f"{style} prompt")
    if not sel:
        return None
    path = rel_map[sel]
    return load_template(path)


__all__ = ["pick_style", "pick_prompt"]
