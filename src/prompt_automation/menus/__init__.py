"""Menu system with fzf and prompt_toolkit fallback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from ..config import PROMPTS_DIR, PROMPTS_SEARCH_PATHS
from ..services.exclusions import parse_exclusions
from ..renderer import (
    fill_placeholders,
    load_template,
    validate_template,
    read_file_safe,
    is_shareable,
)

if TYPE_CHECKING:
    from ..types import Template
from ..variables import (
    get_variables,
    ensure_template_global_snapshot,
    apply_template_global_overrides,
    get_global_reference_file,
)

from .listing import list_styles, list_prompts
from .creation import (
    save_template,
    delete_template,
    add_style,
    delete_style,
    ensure_unique_ids,
    create_new_template,
)
from .picker import pick_style, pick_prompt

from .render_pipeline import (
    apply_defaults,
    apply_file_placeholders,
    apply_formatting,
    apply_global_placeholders,
    apply_markdown_rendering,
    apply_post_render,
)
from .. import parser_singlefield
from ..reminders import (
    extract_template_reminders,
    partition_placeholder_reminders,
)
from ..features import is_reminders_enabled as _reminders_enabled, is_reminders_timing_enabled as _rem_timing
from ..errorlog import get_logger

_log = get_logger(__name__)


# --- Rendering -------------------------------------------------------------

def render_template(
    tmpl: "Template",
    values: Dict[str, Any] | None = None,
    *,
    return_vars: bool = False,
) -> str | tuple[str, Dict[str, Any]]:
    """Render ``tmpl`` using provided ``values`` for placeholders."""

    placeholders = tmpl.get("placeholders", [])
    template_id = tmpl.get("id")

    meta = tmpl.get("metadata") if isinstance(tmpl.get("metadata"), dict) else {}
    exclude_globals: set[str] = parse_exclusions(meta.get("exclude_globals"))

    try:
        globals_file = PROMPTS_DIR / "globals.json"
        if globals_file.exists():
            gdata = json.loads(globals_file.read_text())
            gph_all = gdata.get("global_placeholders", {}) or {}
            if gph_all:
                tgt = tmpl.setdefault("global_placeholders", {})
                for k, v in gph_all.items():
                    if k not in tgt:
                        tgt[k] = v
    except Exception:
        pass
    globals_map = tmpl.get("global_placeholders", {}) or {}
    if exclude_globals:
        for k in list(globals_map.keys()):
            if k in exclude_globals:
                globals_map.pop(k, None)
    if isinstance(template_id, int):
        ensure_template_global_snapshot(template_id, globals_map)
        snap_merged = apply_template_global_overrides(template_id, {})
        for k, v in snap_merged.items():
            if k in exclude_globals:
                continue
            if k == "reminders" and k not in globals_map:
                continue
            globals_map.setdefault(k, v)
        tmpl["global_placeholders"] = globals_map
    if values is None:
        # Compute reminders (non-invasive): attach a private key for CLI flow,
        # and pass template/global reminders via globals_map under a reserved key.
        if _reminders_enabled():
            try:
                import time
                t0 = time.perf_counter() if _rem_timing() else None
                tmpl_rem = extract_template_reminders(tmpl)
                ph_map = partition_placeholder_reminders(placeholders, tmpl_rem)
                # Attach sanitized per-placeholder reminders for CLI presentation
                for ph in placeholders:
                    if isinstance(ph, dict) and ph.get("name") in ph_map:
                        ph.setdefault("_reminders_inline", ph_map[ph["name"]])
                # Inject template reminders into globals map for CLI printing
                if tmpl_rem:
                    globals_map = dict(globals_map)
                    globals_map["__template_reminders"] = tmpl_rem
                # Observability: log counts without content
                try:
                    _log.info(
                        "reminders.summary",
                        extra={
                            "template": len(tmpl_rem),
                            "placeholder": sum(len(v) for v in ph_map.values()),
                        },
                    )
                    if t0 is not None:
                        dt_ms = int((time.perf_counter() - t0) * 1000)
                        _log.info("reminders.timing_ms", extra={"duration_ms": dt_ms})
                except Exception:
                    pass
            except Exception:
                pass
        raw_vars = get_variables(
            placeholders, template_id=template_id, globals_map=globals_map
        )
    else:
        raw_vars = dict(values)

    # If this template includes a single-field capture and a logic block, parse it
    try:
        if (
            isinstance(placeholders, list)
            and len(placeholders) == 1
            and placeholders[0].get("name") == "capture"
            and isinstance(tmpl.get("logic"), dict)
        ):
            capture_val = raw_vars.get("capture") or ""
            tz = tmpl.get("logic", {}).get("timezone")
            parsed = parser_singlefield.parse_capture(capture_val, timezone=tz)
            # Update raw_vars with parsed outputs so downstream pipeline sees them
            raw_vars.update(parsed)
    except Exception:
        pass

    vars = dict(raw_vars)

    context_path = raw_vars.get("context_append_file") or raw_vars.get("context_file")
    if not context_path:
        candidate = raw_vars.get("context")
        if isinstance(candidate, str) and Path(candidate).expanduser().is_file():
            context_path = candidate
    if context_path:
        vars["context"] = read_file_safe(str(context_path))
        raw_vars["context_append_file"] = str(context_path)

    apply_file_placeholders(tmpl, raw_vars, vars, placeholders)
    apply_defaults(raw_vars, vars, placeholders)
    apply_global_placeholders(tmpl, vars, exclude_globals)
    apply_formatting(vars, placeholders)
    # Convert markdown placeholders (e.g., reference_file) into sanitized HTML and wrappers
    try:
        apply_markdown_rendering(tmpl, vars, placeholders)
    except Exception:
        pass

    rendered = fill_placeholders(tmpl["template"], vars)
    rendered = apply_post_render(rendered, tmpl, placeholders, vars, exclude_globals)

    # Fallback: if logic-driven tokens still present, attempt late parse & substitution
    if (
        isinstance(tmpl.get("logic"), dict)
        and isinstance(placeholders, list)
        and len(placeholders) == 1
        and placeholders[0].get("name") == "capture"
    and ("{{title}}" in rendered or "{{priority}}" in rendered or "{{due_display}}" in rendered or "{{acceptance_final}}" in rendered)
    ):
        try:
            capture_val = raw_vars.get("capture") or ""
            tz = tmpl.get("logic", {}).get("timezone")
            parsed_late = parser_singlefield.parse_capture(capture_val, timezone=tz)
            repl_map = {
                "{{title}}": parsed_late.get("title", ""),
                "{{priority}}": parsed_late.get("priority", ""),
                "{{due_display}}": parsed_late.get("due_display", ""),
                "{{acceptance_final}}": parsed_late.get("acceptance_final", ""),
            }
            for token, val in repl_map.items():
                rendered = rendered.replace(token, val)
        except Exception:
            pass

    if return_vars:
        return rendered, raw_vars
    return rendered


__all__ = [
    "list_styles",
    "list_prompts",
    "pick_style",
    "pick_prompt",
    "render_template",
    "save_template",
    "delete_template",
    "add_style",
    "delete_style",
    "ensure_unique_ids",
    "create_new_template",
    "PROMPTS_DIR",
    "PROMPTS_SEARCH_PATHS",
    "load_template",
]
