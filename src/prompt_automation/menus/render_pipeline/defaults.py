from __future__ import annotations

from typing import Any, Dict, Sequence


def apply_defaults(
    raw_vars: Dict[str, Any],
    vars: Dict[str, Any],
    placeholders: Sequence[Dict[str, Any]],
) -> None:
    """Apply default values for placeholders if values are missing."""

    for ph in placeholders:
        name = ph.get("name")
        if not name:
            continue
        default_val = ph.get("default")
        if isinstance(default_val, str) and default_val.strip():
            cur = raw_vars.get(name)
            is_empty = (
                cur is None
                or (isinstance(cur, str) and not cur.strip())
                or (
                    isinstance(cur, (list, tuple))
                    and not any(str(x).strip() for x in cur)
                )
            )
            if is_empty:
                vars[name] = default_val
