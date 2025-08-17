"""Menu system with fzf and prompt_toolkit fallback.

Feature additions:
    - Feature A (Default fallback): When rendering, if a placeholder has a
        non-empty default string and the collected value is empty / whitespace /
        empty list, we substitute the default at assembly time (leaving raw_vars
        untouched for audit).
    - Feature B (Global reminders): If a top-level ``globals.json`` defines
        ``global_placeholders.reminders`` (string or list) and the template (or its
        own ``global_placeholders``) does not already override ``reminders`` then the
        value is merged in. After rendering, any reminders are appended as a
        blockquote list at the end of the composed prompt.
"""
from __future__ import annotations

import json
import re
import os
from .utils import safe_run
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Sequence

from . import logger
from .config import PROMPTS_DIR, PROMPTS_SEARCH_PATHS
from .renderer import (
        fill_placeholders,
        load_template,
        validate_template,
        read_file_safe,
        is_shareable,
)
from .variables import (
    get_variables,
    ensure_template_global_snapshot,
    apply_template_global_overrides,
    get_global_reference_file,
)


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
            for i, location in enumerate(PROMPTS_SEARCH_PATHS, 1):
                exists = "✓" if location.exists() else "✗"
                print(f"  {i}. {exists} {location}")
            return []
        return [p.name for p in PROMPTS_DIR.iterdir() if p.is_dir()]
    except Exception as e:
        print(f"Error listing styles from {PROMPTS_DIR}: {e}")
        return []


def list_prompts(style: str, *, shared_only: bool = False) -> List[Path]:
    """Return all ``.json`` prompt templates under a style folder recursively.

    Previously only files directly inside the style directory were returned, so
    nested folders (e.g. ``Code/Code-Cleanup``) were ignored. We now recurse so
    deeper organizational subfolders are supported transparently.
    """
    base = PROMPTS_DIR / style
    if not base.exists():
        return []
    paths = sorted(base.rglob("*.json"))
    if not shared_only:
        return paths
    filtered: List[Path] = []
    for p in paths:
        try:
            data = load_template(p)
            if is_shareable(data, p):
                filtered.append(p)
        except Exception:
            continue
    return filtered


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
    # Use relative paths (support nested folders) for uniqueness & display
    rel_map = {str(p.relative_to(PROMPTS_DIR / style)): p for p in prompts}
    # Frequency based only on template ID extracted from filename stem
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


def render_template(
    tmpl: Dict[str, Any],
    values: Dict[str, Any] | None = None,
    *,
    return_vars: bool = False,
) -> str | tuple[str, Dict[str, Any]]:
    """Render ``tmpl`` using provided ``values`` for placeholders.

    If ``values`` is ``None`` any missing variables will be collected via
    :func:`variables.get_variables` which falls back to GUI/CLI prompts. When
    ``values`` is supplied it is used as-is, allowing ``None`` entries to skip
    placeholders.

    When ``return_vars`` is ``True`` the function returns a tuple of the final
    rendered text and the raw variable map collected prior to any file content
    substitutions. This allows callers to inspect file paths (e.g. for
    append-to-file behaviour) while preserving existing rendering behaviour.
    """

    placeholders = tmpl.get("placeholders", [])
    template_id = tmpl.get("id")

    # Read exclusion list for global placeholders from metadata.exclude_globals
    meta = tmpl.get("metadata") if isinstance(tmpl.get("metadata"), dict) else {}
    exclude_globals: set[str] = set()
    try:  # robust parsing (list or comma-separated string)
        raw_ex = meta.get("exclude_globals")
        if isinstance(raw_ex, (list, tuple)):
            exclude_globals = {str(x).strip() for x in raw_ex if str(x).strip()}
        elif isinstance(raw_ex, str):
            exclude_globals = {s.strip() for s in raw_ex.split(",") if s.strip()}
    except Exception:
        exclude_globals = set()

    # Merge global placeholders from root globals.json.
    # Previous behaviour only merged 'reminders'. We now merge *all* keys, letting
    # template-level global_placeholders override root. This powers auto-injection
    # (e.g. {{think_deeply}}, {{hallucinate}}) without needing each template to
    # repeat static values. Reminders keep prior semantics (template override wins).
    try:  # non-fatal best-effort
        globals_file = PROMPTS_DIR / "globals.json"
        if globals_file.exists():
            gdata = json.loads(globals_file.read_text())
            gph_all = gdata.get("global_placeholders", {}) or {}
            if gph_all:
                tgt = tmpl.setdefault("global_placeholders", {})
                for k, v in gph_all.items():
                    if k not in tgt:  # template overrides win
                        tgt[k] = v
        else:
            # No globals file in active PROMPTS_DIR; do not fall back to any other location.
            pass
    except Exception:
        pass
    # Template globals after merging root globals (above)
    globals_map = tmpl.get("global_placeholders", {}) or {}
    # Remove excluded keys pre-snapshot so they never persist
    if exclude_globals:
        for k in list(globals_map.keys()):
            if k in exclude_globals:
                globals_map.pop(k, None)
    # Create a one-time snapshot for this template so repeated runs stay stable
    if isinstance(template_id, int):
        # Create snapshot only if one doesn't exist; then merge (snapshot only supplies
        # keys that did not already appear in template's current globals_map).
        ensure_template_global_snapshot(template_id, globals_map)
        snap_merged = apply_template_global_overrides(template_id, {})
        # Only fill missing keys to avoid overriding updated root/test-provided globals.
        # Additionally: do NOT resurrect a 'reminders' key from an older snapshot if the
        # current merged globals (root + template) do not define it. This prevents cross-
        # test leakage where a prior run captured reminders, and a later run (without
        # reminders defined) would unexpectedly append them.
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

    # Optional context file injection
    context_path = raw_vars.get("context_append_file") or raw_vars.get("context_file")
    if not context_path:
        candidate = raw_vars.get("context")
        if isinstance(candidate, str) and Path(candidate).expanduser().is_file():
            context_path = candidate
    if context_path:
        vars["context"] = read_file_safe(str(context_path))
        raw_vars["context_append_file"] = str(context_path)

    # Handle file placeholders including consolidated global reference_file
    ref_path_global = get_global_reference_file()
    for ph in placeholders:
        if ph.get("type") != "file":
            continue
        name = ph["name"]
        path = raw_vars.get(name)
        if name == "reference_file":
            # Fallback to global persisted path if not supplied in raw_vars
            if not path and ref_path_global:
                path = ref_path_global
                raw_vars[name] = path
            content = read_file_safe(path) if path else ""
            # Provide both legacy content var and direct injection if template uses {{reference_file_content}}
            vars["reference_file_content"] = content
        else:
            vars[name] = read_file_safe(path) if path else ""

    # Feature A: default fallback for effectively empty user input
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

    # Auto-inject global placeholder values if referenced in template body but
    # not already collected. This avoids having to list them in 'placeholders'.
    gph_all = tmpl.get("global_placeholders", {}) or {}
    if gph_all:
        # Build set of tokens in template once for efficiency
        template_lines = tmpl.get("template", [])
        tmpl_text = "\n".join(template_lines)
        for gk, gv in gph_all.items():
            if gk in exclude_globals:
                continue
            if gk in vars:
                continue  # user / placeholder value has precedence
            token = f"{{{{{gk}}}}}"
            if token in tmpl_text:
                # Basic heuristics: blank global value => treat as None so line removed
                if isinstance(gv, str) and not gv.strip():
                    vars[gk] = None  # line removed by fill_placeholders
                else:
                    vars[gk] = gv

    # Pre-format variables based on optional formatting hints.
    # A placeholder may supply a 'format' or 'as' key with values:
    #   - 'list': treat multi-line user input or sequence as bullet list (- item)
    #   - 'checklist': bullet list with unchecked markdown checkboxes (- [ ] item)
    #   - 'auto': if every non-empty line looks like a task prefix (*,-,number,[ ]) leave as-is, else convert to bullets
    fmt_map: dict[str, str] = {}
    for ph in placeholders:
        name = ph.get("name")
        if not name:
            continue
        fmt = ph.get("format") or ph.get("as")  # allow alias 'as'
        if isinstance(fmt, str):
            fmt_map[name] = fmt.lower().strip()

    def _normalize_lines(val: Union[str, Sequence[str]]) -> list[str]:
        if isinstance(val, (list, tuple)):
            lines: list[str] = []
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
        # Strip trailing/leading blank lines logically
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue
        def to_bullets(lines: list[str], prefix: str) -> list[str]:
            out: list[str] = []
            for ln in lines:
                if not ln.strip():
                    continue
                if ln.lstrip().startswith(prefix.strip()) and '[' in prefix:  # already checkbox maybe
                    out.append(ln)
                else:
                    out.append(f"{prefix}{ln.strip()}")
            return out
        if fmt == "list":
            new_lines = to_bullets(lines, "- ")
        elif fmt == "checklist":
            new_lines = to_bullets(lines, "- [ ] ")
        elif fmt == "auto":
            # Heuristic: if all lines already start with bullet/list token keep; else bulletize
            tokens = ("- ", "* ", "+ ", "- [", "* [")
            if all(any(ln.lstrip().startswith(t) for t in tokens) for ln in lines if ln.strip()):
                new_lines = lines
            else:
                new_lines = to_bullets(lines, "- ")
        else:
            continue
        vars[name] = "\n".join(new_lines)

    rendered = fill_placeholders(tmpl["template"], vars)

    # Post-render cleanup: phrase removal for empty placeholders + whitespace trimming
    try:
        # Remove inline phrases tied to empty placeholders
        for ph in placeholders:
            name = ph.get("name")
            if not name:
                continue
            val = vars.get(name)
            if val is not None and str(val).strip():
                continue  # has content
            phrases = ph.get("remove_if_empty") or ph.get("remove_if_empty_phrases")
            if not phrases:
                continue
            if isinstance(phrases, str):
                phrases = [phrases]
            for phrase in phrases:
                if not isinstance(phrase, str) or not phrase.strip():
                    continue
                # Pattern: optional leading space/start, phrase, optional trailing space before punctuation
                pattern = re.compile(rf"(\s|^){re.escape(phrase.strip())}(?=\s*[.,;:!?])", re.IGNORECASE)
                rendered = pattern.sub(lambda m: m.group(1) if m.group(1).isspace() else "", rendered)
                # Also remove occurrences not followed by punctuation but trailing spaces
                pattern2 = re.compile(rf"(\s|^){re.escape(phrase.strip())}\s+", re.IGNORECASE)
                rendered = pattern2.sub(lambda m: m.group(1) if m.group(1).isspace() else "", rendered)

        meta = tmpl.get("metadata", {}) if isinstance(tmpl.get("metadata"), dict) else {}
        # Global trim_blanks resolution order: metadata > globals.json(render_settings/trim_blanks) > env var > default True
        trim_blanks_flag = meta.get("trim_blanks")
        if trim_blanks_flag is None:
            try:
                gfile = PROMPTS_DIR / "globals.json"
                if gfile.exists():
                    gdata = json.loads(gfile.read_text())
                    # Accept several possible key locations
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
                if env_val.lower() in {"0","false","no","off"}:
                    trim_blanks_flag = False
                else:
                    trim_blanks_flag = True
        if trim_blanks_flag is None:
            trim_blanks_flag = True

        if trim_blanks_flag:
            # Collapse multiple spaces
            rendered = re.sub(r"[ \t]{2,}", " ", rendered)
            # Remove spaces before punctuation
            rendered = re.sub(r"\s+([.,;:!?])", r"\1", rendered)
            # Collapse >2 blank lines to max 1
            rendered = re.sub(r"\n{3,}", "\n\n", rendered)
            # Strip trailing spaces per line
            rendered = "\n".join(l.rstrip() for l in rendered.splitlines())
            # Final trim newline
            rendered = rendered.strip() + "\n"
    except Exception:
        pass

    # Reminders block (blockquote markdown) + optional think_deeply append after block
    try:
        gph = globals_map or {}
        # Only act on reminders if key explicitly present and truthy; prevents
        # unrelated globals (importance etc.) from causing default repo reminders.
        if "reminders" in gph and "reminders" not in exclude_globals:
            raw_rem = gph.get("reminders")
        else:
            raw_rem = None
        reminders: list[str] = []
        if isinstance(raw_rem, str):
            raw_list = [raw_rem]
        elif isinstance(raw_rem, (list, tuple)):
            raw_list = list(raw_rem)
        else:
            raw_list = []
        for item in raw_list:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if not cleaned:
                continue
            if len(cleaned) > 500:
                cleaned = cleaned[:500].rstrip() + "…"
            reminders.append(cleaned)
        appended_reminders = False
        if reminders:
            block_lines = ["> Reminders:"] + [f"> - {r}" for r in reminders]
            if not rendered.endswith("\n"):
                rendered += "\n"
            if not rendered.endswith("\n\n"):
                rendered += "\n"
            rendered += "\n".join(block_lines)
            appended_reminders = True
        # Append think_deeply directive if not explicitly tokenized or already present.
        td_val = gph.get("think_deeply") if isinstance(gph, dict) else None
        if isinstance(td_val, str) and td_val.strip():
            token = "{{think_deeply}}"
            # Only add if token absent from original template AND value not already in rendered
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
    """Ensure every template has a unique ID.

    Behaviour improvements over the previous implementation:
    - Missing ``id`` fields are auto-assigned the next free ID (01-98) per style
      (falling back to global pool) instead of raising a raw ``KeyError``.
    - Duplicate IDs are resolved by reassigning *later* files to a new ID.
    - Files are renamed to keep the ``NN_`` prefix in sync with their ID.
    - A concise summary of any fixes is printed so the user can review changes.

    Any unrecoverable issues (e.g. ID pool exhausted) still raise ``ValueError``.
    """

    # Collect template file paths first to have deterministic ordering (path sort)
    paths = sorted(base.rglob("*.json"))
    used_ids_global: set[int] = set()
    changes: List[str] = []
    problems: List[str] = []

    # Pre-load all data (skip unreadable files silently but note them)
    templates: List[tuple[Path, Dict[str, Any]]] = []
    for path in paths:
        try:
            data = json.loads(path.read_text())
            templates.append((path, data))
        except Exception as e:
            problems.append(f"Unreadable JSON: {path} ({e})")

    # Helper to generate next free ID within allowed range (1-98)
    def next_free_id() -> int | None:
        for i in range(1, 99):
            if i not in used_ids_global:
                return i
        return None

    for path, data in templates:
        # Ignore non-template global/config files
        if "template" not in data or data.get("type") == "globals":
            continue
        orig_id = data.get("id")
        if not isinstance(orig_id, int):
            new_id = next_free_id()
            if new_id is None:
                raise ValueError("No free IDs (01-98) remain to assign missing id")
            data["id"] = new_id
            used_ids_global.add(new_id)
            changes.append(f"Assigned missing id {new_id:02d} -> {path}")
        else:
            if orig_id in used_ids_global:
                # Duplicate – assign new id
                new_id = next_free_id()
                if new_id is None:
                    raise ValueError(
                        f"Duplicate id {orig_id:02d} in {path} and elsewhere; no free IDs left"
                    )
                data["id"] = new_id
                used_ids_global.add(new_id)
                changes.append(
                    f"Reassigned duplicate id {orig_id:02d} -> {new_id:02d} in {path}"
                )
            else:
                used_ids_global.add(orig_id)

    # Persist any modified templates (id changed or added); rename files if needed
    for path, data in templates:
        # Skip non-template config/variable files (no 'template' field)
        if "template" not in data:
            continue
        # Determine expected file prefix based on id + slug(title)
        try:
            pid = data["id"]
            title = data.get("title")
            # If no title and filename already starts with NN_ assume it's intentional (e.g. globals)
            if not title and path.name.startswith(f"{int(pid):02d}_"):
                expected_name = path.name  # keep as-is
            else:
                slug_title = _slug(title or path.stem)
                expected_name = f"{int(pid):02d}_{slug_title}.json"
            if path.name != expected_name:
                new_path = path.with_name(expected_name)
                # Write to new path then remove/backup old
                path.write_text(json.dumps(data, indent=2))  # ensure current path has updated data
                if new_path.exists() and new_path != path:
                    # Backup existing conflicting file
                    backup = new_path.with_suffix(new_path.suffix + ".bak")
                    shutil.copy2(new_path, backup)
                if new_path != path:
                    path.rename(new_path)
                    changes.append(f"Renamed {path.name} -> {new_path.name}")
            else:
                # Only write if id was changed (detect by reading file again?)
                # Simpler: always rewrite – small cost, ensures consistency
                path.write_text(json.dumps(data, indent=2))
        except Exception as e:  # pragma: no cover - defensive
            problems.append(f"Failed updating {path}: {e}")

    if problems:
        print("[prompt-automation] Issues during ID check:")
        for p in problems:
            print("  -", p)
    if changes:
        print("[prompt-automation] Template ID adjustments:")
        for c in changes:
            print("  -", c)
    # If no changes and no problems, remain silent for fast startup


def create_new_template() -> None:
    style = input("Style: ") or "Misc"
    dir_path = PROMPTS_DIR / style
    dir_path.mkdir(parents=True, exist_ok=True)
    used = {json.loads(p.read_text())['id'] for p in dir_path.glob("*.json")}
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


