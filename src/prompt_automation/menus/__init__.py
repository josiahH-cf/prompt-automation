"""Menu system with fzf and prompt_toolkit fallback."""
from __future__ import annotations

import json
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ..config import PROMPTS_DIR, PROMPTS_SEARCH_PATHS
from ..renderer import (
    fill_placeholders,
    load_template,
    validate_template,
    read_file_safe,
    is_shareable,
)
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


# --- Rendering -------------------------------------------------------------

def render_template(
    tmpl: Dict[str, Any],
    values: Dict[str, Any] | None = None,
    *,
    return_vars: bool = False,
) -> str | tuple[str, Dict[str, Any]]:
    """Render ``tmpl`` using provided ``values`` for placeholders."""

    placeholders = tmpl.get("placeholders", [])
    template_id = tmpl.get("id")

    meta = tmpl.get("metadata") if isinstance(tmpl.get("metadata"), dict) else {}
    exclude_globals: set[str] = set()
    try:
        raw_ex = meta.get("exclude_globals")
        if isinstance(raw_ex, (list, tuple)):
            exclude_globals = {str(x).strip() for x in raw_ex if str(x).strip()}
        elif isinstance(raw_ex, str):
            exclude_globals = {s.strip() for s in raw_ex.split(",") if s.strip()}
    except Exception:
        exclude_globals = set()

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
        raw_vars = get_variables(
            placeholders, template_id=template_id, globals_map=globals_map
        )
    else:
        raw_vars = dict(values)
    vars = dict(raw_vars)

    context_path = raw_vars.get("context_append_file") or raw_vars.get("context_file")
    if not context_path:
        candidate = raw_vars.get("context")
        if isinstance(candidate, str) and Path(candidate).expanduser().is_file():
            context_path = candidate
    if context_path:
        vars["context"] = read_file_safe(str(context_path))
        raw_vars["context_append_file"] = str(context_path)

    # --- File placeholder handling (multi-file support) ------------------
    ref_path_global = get_global_reference_file()
    template_lines_all = tmpl.get("template", []) or []
    tmpl_text_all = "\n".join(template_lines_all)
    declared_reference_placeholder = any(ph.get("name") == "reference_file" for ph in placeholders)

    for ph in placeholders:
        if ph.get("type") != "file":
            continue
        name = ph.get("name")
        if not name:
            continue
        path = raw_vars.get(name)
        # For canonical reference_file placeholder: fallback to global *only if blank*
        if name == "reference_file" and (not path) and ref_path_global:
            path = ref_path_global
            raw_vars[name] = path  # record effective path for caller if they requested return_vars
        content = read_file_safe(path) if path else ""
        vars[name] = content
        # Optional path token lazily injected only if referenced (saves clutter in vars)
        if f"{{{{{name}_path}}}}" in tmpl_text_all:
            vars[f"{name}_path"] = path or ""
        # Legacy alias only for canonical name
        if name == "reference_file":
            vars["reference_file_content"] = content

    # Global fallback when template did NOT declare reference_file placeholder at all.
    # If the template references either {{reference_file}} or {{reference_file_content}} tokens
    # inject the global file content (and path token if requested) without a placeholder definition.
    if not declared_reference_placeholder and ref_path_global:
        try:
            needs_ref = ("{{reference_file}}" in tmpl_text_all) or ("{{reference_file_content}}" in tmpl_text_all)
            if needs_ref:
                content = read_file_safe(ref_path_global)
                if "{{reference_file}}" in tmpl_text_all and "reference_file" not in vars:
                    vars["reference_file"] = content
                if "reference_file_content" not in vars and "{{reference_file_content}}" in tmpl_text_all:
                    vars["reference_file_content"] = content
                if "{{reference_file_path}}" in tmpl_text_all and "reference_file_path" not in vars:
                    vars["reference_file_path"] = ref_path_global
        except Exception:
            pass

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
                or (isinstance(cur, (list, tuple)) and not any(str(x).strip() for x in cur))
            )
            if is_empty:
                vars[name] = default_val

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

    fmt_map: dict[str, str] = {}
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

    rendered = fill_placeholders(tmpl["template"], vars)

    try:
        for ph in placeholders:
            name = ph.get("name")
            if not name:
                continue
            val = vars.get(name)
            if val is not None and str(val).strip():
                continue
            phrases = ph.get("remove_if_empty") or ph.get("remove_if_empty_phrases")
            if not phrases:
                continue
            if isinstance(phrases, str):
                phrases = [phrases]
            for phrase in phrases:
                if not isinstance(phrase, str) or not phrase.strip():
                    continue
                pattern = re.compile(rf"(\s|^){re.escape(phrase.strip())}(?=\s*[.,;:!?])", re.IGNORECASE)
                rendered = pattern.sub(lambda m: m.group(1) if m.group(1).isspace() else "", rendered)
                pattern2 = re.compile(rf"(\s|^){re.escape(phrase.strip())}\s+", re.IGNORECASE)
                rendered = pattern2.sub(lambda m: m.group(1) if m.group(1).isspace() else "", rendered)

        meta = tmpl.get("metadata", {}) if isinstance(tmpl.get("metadata"), dict) else {}
        trim_blanks_flag = meta.get("trim_blanks")
        if trim_blanks_flag is None:
            try:
                gfile = PROMPTS_DIR / "globals.json"
                if gfile.exists():
                    gdata = json.loads(gfile.read_text())
                    trim_blanks_flag = (
                        gdata.get("render_settings", {}).get("trim_blanks")
                        or gdata.get("global_settings", {}).get("trim_blanks")
                        or gdata.get("trim_blanks")
                    )
            except Exception:
                trim_blanks_flag = None
        if trim_blanks_flag is None:
            env_val = os.environ.get("PROMPT_AUTOMATION_TRIM_BLANKS")
            if env_val is not None:
                if env_val.lower() in {"0", "false", "no", "off"}:
                    trim_blanks_flag = False
                else:
                    trim_blanks_flag = True
        if trim_blanks_flag is None:
            trim_blanks_flag = True
        if trim_blanks_flag:
            rendered = "\n".join([ln.rstrip() for ln in rendered.splitlines()]).strip()
    except Exception:
        pass

    gph = tmpl.get("global_placeholders")
    try:
        reminders = gph.get("reminders") if isinstance(gph, dict) else None
        if reminders:
            if isinstance(reminders, str):
                reminders_list = [reminders]
            elif isinstance(reminders, list):
                reminders_list = [str(r) for r in reminders if str(r).strip()]
            else:
                reminders_list = []
            reminders_list = [r for r in reminders_list if r.strip()]
            if reminders_list:
                rendered += "\n\nReminders:\n" + "\n".join(f"> - {r}" for r in reminders_list)
                appended_reminders = True
            else:
                appended_reminders = False
        else:
            appended_reminders = False
        td_val = gph.get("think_deeply") if isinstance(gph, dict) else None
        if isinstance(td_val, str) and td_val.strip():
            token = "{{think_deeply}}"
            if token not in "\n".join(tmpl.get("template", [])) and td_val.strip() not in rendered:
                if "think_deeply" not in exclude_globals:
                    if not rendered.endswith("\n"):
                        rendered += "\n"
                    if appended_reminders:
                        rendered += "\n"
                    rendered += td_val.strip()
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
