from __future__ import annotations

from typing import Any, Dict, Set


def apply_global_placeholders(
    tmpl: Dict[str, Any],
    vars: Dict[str, Any],
    exclude_globals: Set[str],
) -> None:
    """Inject global placeholders into ``vars`` if referenced."""

    gph_all = tmpl.get("global_placeholders", {}) or {}
    if gph_all:
        template_lines = tmpl.get("template", [])
        tmpl_text = "\n".join(template_lines)
        for gk, gv in gph_all.items():
            if gk in exclude_globals:
                continue
            if gk in vars:
                continue
            token = f"{{{{{gk}}}}}"
            if token in tmpl_text:
                if isinstance(gv, str) and not gv.strip():
                    vars[gk] = None
                else:
                    vars[gk] = gv
