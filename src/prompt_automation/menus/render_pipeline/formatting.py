from __future__ import annotations

from typing import Any, Dict, List, Sequence, Union


def apply_formatting(vars: Dict[str, Any], placeholders: Sequence[Dict[str, Any]]) -> None:
    """Apply formatting directives like ``list`` and ``checklist``."""

    fmt_map: Dict[str, str] = {}
    for ph in placeholders:
        name = ph.get("name")
        if not name:
            continue
        fmt = ph.get("format") or ph.get("as")
        if isinstance(fmt, str):
            fmt_map[name] = fmt.lower().strip()

    def _normalize_lines(val: Union[str, Sequence[str]]) -> List[str]:
        if isinstance(val, (list, tuple)):
            lines: List[str] = []
            for item in val:
                lines.extend(str(item).splitlines())
            return lines
        else:
            return str(val).splitlines()

    for name, fmt in fmt_map.items():
        raw_val = vars.get(name)
        if not raw_val:
            continue
        lines = _normalize_lines(raw_val)
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue

        def to_bullets(lines: List[str], prefix: str) -> List[str]:
            out: List[str] = []
            for ln in lines:
                if not ln.strip():
                    continue
                if ln.lstrip().startswith(prefix.strip()) and "[" in prefix:
                    out.append(ln)
                else:
                    out.append(f"{prefix}{ln.strip()}")
            return out

        if fmt == "list":
            new_lines = to_bullets(lines, "- ")
        elif fmt == "checklist":
            new_lines = to_bullets(lines, "- [ ] ")
        elif fmt == "auto":
            tokens = ("- ", "* ", "+ ", "- [", "* [")
            if all(any(ln.lstrip().startswith(t) for t in tokens) for ln in lines if ln.strip()):
                new_lines = lines
            else:
                new_lines = to_bullets(lines, "- ")
        else:
            continue
        vars[name] = "\n".join(new_lines)
