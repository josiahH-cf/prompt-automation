from __future__ import annotations

"""Lightweight helpers for parsing and presenting template reminders.

Reminders are read-only instructional strings that may appear:
- At the template root under key "reminders": ["..."]
- Under individual placeholder objects as key "reminders": ["..."]
- Optionally under globals.json -> global_placeholders.reminders: ["..."]

Utilities in this module sanitize inputs, enforce soft limits, deduplicate
merged sources, and provide CLI-friendly formatting. Rendering in GUI/CLI is
gated by the feature flag resolved via ``features.is_reminders_enabled``.
"""

from typing import Any, Dict, Iterable, List, Tuple

from .features import is_reminders_enabled as _flag_enabled


# Soft limits (UI-focused; defensive for extremely large inputs)
REMINDER_LEN_MAX = 500
REMINDER_MAX = 25


def _sanitize_text(s: Any) -> str:
    """Return a safe, trimmed string for display.

    - Coerces to string
    - Strips leading/trailing whitespace
    - Replaces control characters except common whitespace
    - Truncates to REMINDER_LEN_MAX with ellipsis
    """
    # Treat None as empty (ignored)
    if s is None:
        return ""
    try:
        text = str(s)
    except Exception:
        text = ""
    text = text.replace("\r", " ")
    # Keep newlines; drop other control chars
    text = "".join(ch if (ch.isprintable() or ch in "\n\t ") else " " for ch in text)
    text = text.strip()
    if not text:
        return ""
    if len(text) > REMINDER_LEN_MAX:
        return text[: REMINDER_LEN_MAX - 1].rstrip() + "\u2026"  # ellipsis
    return text


def _collect_list(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for item in raw:
        t = _sanitize_text(item)
        if t:
            out.append(t)
        if len(out) >= REMINDER_MAX:
            break
    return out


def extract_template_reminders(template: Dict[str, Any]) -> List[str]:
    """Return merged template + global reminders for this template.

    - If feature flag disabled, returns []
    - Merges template.reminders + template.global_placeholders.reminders
    - Deduplicates while preserving order
    """
    if not _flag_enabled():
        return []
    merged: List[str] = []
    seen = set()
    # Template-level
    for s in _collect_list(template.get("reminders")):
        if s not in seen:
            merged.append(s)
            seen.add(s)
    # Global-level (if present on loaded template)
    gp = template.get("global_placeholders") or {}
    if isinstance(gp, dict):
        for s in _collect_list(gp.get("reminders")):
            if s not in seen:
                merged.append(s)
                seen.add(s)
    return merged


def extract_placeholder_reminders(ph: Dict[str, Any]) -> List[str]:
    """Return sanitized placeholder-level reminders for a placeholder dict."""
    if not _flag_enabled():
        return []
    return _collect_list(ph.get("reminders"))


def partition_placeholder_reminders(
    placeholders: Iterable[Dict[str, Any]],
    template_reminders: Iterable[str] | None = None,
) -> Dict[str, List[str]]:
    """Return mapping: placeholder name -> reminders (deduped against template).

    Only placeholders that have an explicit reminders list are included.
    """
    tset = set(template_reminders or [])
    out: Dict[str, List[str]] = {}
    for ph in placeholders or []:
        if not isinstance(ph, dict):
            continue
        name = ph.get("name")
        if not name:
            continue
        items = extract_placeholder_reminders(ph)
        if not items:
            continue
        # Dedup against template/global reminders
        filt = [s for s in items if s not in tset]
        if filt:
            out[name] = filt
    return out


def cli_format_block(reminders: List[str]) -> List[str]:
    """Return printable lines for CLI presentation.

    Example:
        Reminders:
         - item 1
         - item 2
    """
    if not reminders:
        return []
    lines = ["Reminders:"]
    for s in reminders:
        lines.append(f" - {s}")
    return lines


__all__ = [
    "REMINDER_LEN_MAX",
    "REMINDER_MAX",
    "extract_template_reminders",
    "extract_placeholder_reminders",
    "partition_placeholder_reminders",
    "cli_format_block",
]
