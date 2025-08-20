from __future__ import annotations

from typing import Any, Dict, Sequence

from ...renderer import read_file_safe


def apply_file_placeholders(
    tmpl: Dict[str, Any],
    raw_vars: Dict[str, Any],
    vars: Dict[str, Any],
    placeholders: Sequence[Dict[str, Any]],
) -> None:
    """Populate file placeholder contents into ``vars``.

    This mutates ``tmpl`` and the provided dictionaries in-place.
    """

    from .. import get_global_reference_file

    ref_path_global = get_global_reference_file()
    template_lines_all = tmpl.get("template", []) or []
    tmpl_text_all = "\n".join(template_lines_all)
    declared_reference_placeholder = any(
        ph.get("name") == "reference_file" for ph in placeholders
    )

    for ph in placeholders:
        if ph.get("type") != "file":
            continue
        name = ph.get("name")
        if not name:
            continue
        path = raw_vars.get(name)
        if name == "reference_file" and (not path) and ref_path_global:
            path = ref_path_global
            raw_vars[name] = path
        content = read_file_safe(path) if path else ""
        vars[name] = content
        if f"{{{{{name}_path}}}}" in tmpl_text_all:
            vars[f"{name}_path"] = path or ""
        if name == "reference_file":
            vars["reference_file_content"] = content

    if not declared_reference_placeholder and ref_path_global:
        try:
            needs_ref = (
                "{{reference_file}}" in tmpl_text_all
                or "{{reference_file_content}}" in tmpl_text_all
            )
            if needs_ref:
                content = read_file_safe(ref_path_global)
                if "{{reference_file}}" in tmpl_text_all and "reference_file" not in vars:
                    vars["reference_file"] = content
                if (
                    "reference_file_content" not in vars
                    and "{{reference_file_content}}" in tmpl_text_all
                ):
                    vars["reference_file_content"] = content
                if (
                    "{{reference_file_path}}" in tmpl_text_all
                    and "reference_file_path" not in vars
                ):
                    vars["reference_file_path"] = ref_path_global
        except Exception:
            pass
