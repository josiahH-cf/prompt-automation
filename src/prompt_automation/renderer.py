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
from typing import Dict, Iterable, List, Sequence, Union, Any, TYPE_CHECKING
import re

from .errorlog import get_logger

if TYPE_CHECKING:
    from .types import Template

_log = get_logger(__name__)


def read_file_safe(path: str) -> str:
    """Return file contents (best‑effort) or empty string.

    Why rewrite? Previously we relied on ``Path.read_text()`` raising to
    try alternative encodings; on Windows a UTF‑8 file with emoji could be
    decoded as cp1252 *without error*, producing mojibake like ``ðŸ‘—``.
    We now always read bytes first and attempt a deterministic, Unicode‑
    friendly list of decoders in priority order, guaranteeing UTF‑8 wins
    when valid.

    Order rationale:
      1. utf-8 (most common; fast happy path)
      2. utf-8-sig (BOM variants)
      3. utf-16 / utf-16-le / utf-16-be (common exported docs)
      4. cp1252 (legacy Windows fallback)

    If all fail we log and return an empty string. We also perform a simple
    heuristic: if a *later* decoder produced typical UTF‑8 mojibake tokens
    (``\u00f0\u009f`` sequences rendered as ``ðŸ``) but the raw bytes are
    valid UTF‑8, we re-decode with UTF‑8.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return ""
    try:
        if p.suffix.lower() == ".docx":  # optional dependency branch
            try:
                import docx  # type: ignore
                return "\n".join(par.text for par in docx.Document(p).paragraphs)
            except Exception as e:  # pragma: no cover - optional dependency
                _log.error("cannot read Word file %s: %s", path, e)
                return ""
        data = p.read_bytes()
        encodings = ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252")
        last_text: str | None = None
        for enc in encodings:
            try:
                text = data.decode(enc)
                # Quick success for the first (ideal) encodings
                if enc.startswith("utf-8"):
                    return text
                # Save candidate; continue in case utf-8 later would have succeeded (already tried)
                last_text = text
                break
            except Exception:  # pragma: no cover - per-encoding failure
                continue
        if last_text is None:
            # utf-16 variants or cp1252 may have worked; but if not, attempt strict utf-8 once more
            try:
                return data.decode("utf-8")
            except Exception:
                _log.error("cannot decode file %s with fallback set", path)
                return ""
        # Heuristic fix: if mojibake markers present and raw bytes are valid utf-8, prefer utf-8 decode
        if ("ðŸ" in last_text or "â€™" in last_text or "â€“" in last_text):
            try:
                utf8_text = data.decode("utf-8")
                return utf8_text
            except Exception:
                pass
        return last_text
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


def inject_share_flag(data: "Template", path: Path) -> None:
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


def is_shareable(template: "Template", path: Path) -> bool:
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


def load_template(path: Path) -> "Template":
    """Load JSON template file, injecting share flag defaults."""
    path = path.expanduser().resolve()
    if not path.is_file():
        _log.error("template not found: %s", path)
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    try:  # pragma: no cover - simple injection
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

    Features:
      - Multi-line replacements keep indentation when placeholder line only had the token.
      - Sequence values join with newlines.
      - Lines whose placeholders all resolve to empty/whitespace are removed.
      - If a *section header* line (e.g. begins with a dash ``-`` or bullet) is
        immediately followed by a placeholder-only line that is removed due to
        emptiness, the header line is also removed. This prevents empty sections
        caused by tabbing past unused fields.
    """

    # Convert to list for look-ahead logic
    src_lines = list(lines)
    processed: List[str] = []
    skip_indices: set[int] = set()
    placeholder_only_removed: set[int] = set()  # indices of lines removed because only empty placeholders

    for idx, line in enumerate(src_lines):
        if idx in skip_indices:
            continue
        original_line = line
        placeholders_in_line: List[str] = []
        replacement_map: Dict[str, str] = {}
        empty_tokens: set[str] = set()

        for k in vars.keys():
            token = f"{{{{{k}}}}}"
            if token in line:
                placeholders_in_line.append(token)

        if not placeholders_in_line:
            processed.append(line)
            continue

        for token in placeholders_in_line:
            key = token[2:-2]
            v = vars.get(key)
            if v is None:
                empty_tokens.add(token)
                replacement_map[token] = ""
                continue
            if isinstance(v, (list, tuple)):
                repl = "\n".join(str(item) for item in v)
            else:
                repl = str(v)
            if not repl.strip():
                empty_tokens.add(token)
                repl = ""
            if original_line.strip() == token and repl and "\n" in repl:
                indent = original_line[: len(original_line) - len(original_line.lstrip())]
                parts = repl.split("\n")
                if parts:
                    first = parts[0]
                    rest = [indent + p if p.strip() else indent + p for p in parts[1:]]
                    repl = first + ("\n" + "\n".join(rest) if rest else "")
            replacement_map[token] = repl

        non_empty_tokens = [t for t in placeholders_in_line if t not in empty_tokens]
        if not non_empty_tokens:
            residual = original_line
            for t in placeholders_in_line:
                residual = residual.replace(t, "")
            if not residual.strip():
                placeholder_only_removed.add(idx)
                continue

        # Apply replacements
        for token, repl in replacement_map.items():
            line = line.replace(token, repl)
        processed.append(line)

    # Second pass: remove headers preceding removed placeholder-only lines
    final_out: List[str] = []
    i = 0
    total = len(src_lines)
    # Build mapping from original index to whether kept and its processed text
    # Simplify by iterating original indices and referencing processed iteratively
    processed_iter = iter(processed)
    kept_line_by_index: Dict[int, str] = {}
    for idx, line in enumerate(src_lines):
        if idx in placeholder_only_removed:
            continue
        kept_line_by_index[idx] = next(processed_iter)

    idx = 0
    bullet_header_re = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
    while idx < total:
        if idx in placeholder_only_removed:
            idx += 1
            continue
        line = kept_line_by_index[idx]
        if bullet_header_re.match(line) and (idx + 1) in placeholder_only_removed:
            header_indent = len(line) - len(line.lstrip())
            removed_line = src_lines[idx + 1]
            removed_indent = len(removed_line) - len(removed_line.lstrip())
            if removed_indent > header_indent:
                idx += 2
                continue
        final_out.append(line)
        idx += 1

    return "\n".join(final_out)


__all__ = [
    "read_file_safe",
    "load_template",
    "validate_template",
    "fill_placeholders",
    "is_shareable",
    "inject_share_flag",
]
