"""Loading and rendering prompt templates.

Additions:
    - ``inject_share_flag`` ensures ``metadata.share_this_file_openly`` is always
        present (default ``true``) unless the file resides under a ``prompts/local``
        directory which implicitly makes it private.
    - ``is_shareable`` centralizes share/export eligibility logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Union, Any

from .errorlog import get_logger

_log = get_logger(__name__)


def read_file_safe(path: str) -> str:
    """Return file contents or empty string with logging."""
    p = Path(path).expanduser()
    try:
        if p.suffix.lower() == ".docx":
            try:
                import docx  # type: ignore
                return "\n".join(par.text for par in docx.Document(p).paragraphs)
            except Exception as e:  # pragma: no cover - optional dependency
                _log.error("cannot read Word file %s: %s", path, e)
                return ""
        return p.read_text()
    except Exception as e:
        _log.error("cannot read file %s: %s", path, e)
        return ""


def _coerce_bool(val: Any) -> bool | None:
    """Best-effort coercion of an arbitrary value to a boolean.

    Returns ``None`` if the value is not safely coercible (e.g. list/dict).
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        low = val.strip().lower()
        if low in {"false", "no", "0", "off", "n"}:
            return False
        if low in {"true", "yes", "1", "on", "y"}:
            return True
        return True if low else False
    return None


def inject_share_flag(data: Dict[str, Any], path: Path) -> None:
    """Ensure ``metadata.share_this_file_openly`` exists & normalized.

    Behaviour:
      - If metadata missing, create it.
      - If flag missing, default to ``True`` unless path is under ``prompts/local``.
      - If flag present but not bool, coerce; warn if coercion required.
    """
    meta_obj = data.get("metadata")
    if not isinstance(meta_obj, dict):
        meta_obj = {}
        data["metadata"] = meta_obj
    # Determine if file is within a prompts/local path segment (case-insensitive)
    lowered = [p.lower() for p in path.parts]
    in_local = False
    for i, part in enumerate(lowered):
        if part == "prompts" and i + 1 < len(lowered) and lowered[i + 1] == "local":
            in_local = True
            break
    if "share_this_file_openly" not in meta_obj:
        meta_obj["share_this_file_openly"] = not in_local
    else:
        coerced = _coerce_bool(meta_obj.get("share_this_file_openly"))
        if coerced is None:
            _log.warning(
                "metadata.share_this_file_openly not coercible for %s; defaulting True", path
            )
            coerced = True
        meta_obj["share_this_file_openly"] = coerced


def is_shareable(template: Dict[str, Any], path: Path) -> bool:
    """Return True if template should be considered share/export eligible.

    Precedence order:
      1. Explicit ``metadata.share_this_file_openly`` False => private.
      2. Else if path lives under ``prompts/local`` => private.
      3. Else => shared.
    Missing metadata or flag defaults to shared (handled by ``inject_share_flag``).
    """
    try:
        meta = template.get("metadata", {}) if isinstance(template.get("metadata"), dict) else {}
        if meta.get("share_this_file_openly") is False:
            return False
        lowered = [p.lower() for p in path.parts]
        for i, part in enumerate(lowered):
            if part == "prompts" and i + 1 < len(lowered) and lowered[i + 1] == "local":
                return False
        return True
    except Exception:  # pragma: no cover - defensive
        return True


def load_template(path: Path) -> Dict:
    """Load JSON template file, injecting share flag defaults."""
    path = path.expanduser().resolve()
    if not path.is_file():
        _log.error("template not found: %s", path)
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    try:
        inject_share_flag(data, path)
    except Exception as e:  # pragma: no cover
        _log.warning("failed to inject share flag for %s: %s", path, e)
    return data


def validate_template(data: Dict) -> bool:
    """Basic schema validation (share flag injected lazily at load time)."""
    required = {"id", "title", "style", "template", "placeholders"}
    return required.issubset(data)


def fill_placeholders(
    lines: Iterable[str], vars: Dict[str, Union[str, Sequence[str], None]]
) -> str:
    """Replace ``{{name}}`` placeholders with values.

    ``vars`` may contain either strings or sequences of strings. Sequence
    values (used for dynamic list placeholders) are joined with newlines before
    replacement. ``None`` or empty string values cause the entire line containing
    the placeholder to be removed.
    """

    out: List[str] = []
    for line in lines:
        skip_line = False
        for k, v in vars.items():
            placeholder = f"{{{{{k}}}}}"
            if placeholder not in line:
                continue

            if v is None:
                skip_line = True
                break
            if isinstance(v, (list, tuple)):
                repl = "\n".join(str(item) for item in v)
                if not repl.strip():
                    skip_line = True
                    break
            else:
                repl = str(v)
                if not repl.strip():
                    skip_line = True
                    break
            line = line.replace(placeholder, repl)

        if not skip_line:
            out.append(line)
    return "\n".join(out)


__all__ = [
    "read_file_safe",
    "load_template",
    "validate_template",
    "fill_placeholders",
    "is_shareable",
    "inject_share_flag",
]
