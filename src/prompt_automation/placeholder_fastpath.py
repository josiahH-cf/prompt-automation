from __future__ import annotations

"""Placeholder fast-path detection utilities.

Expose a small, pure function to determine whether a template is
effectively placeholder-empty (after filtering non-input specs) and
whether the fast-path is disabled by configuration.
"""

from enum import Enum
from typing import Any, Dict, List

from .features import is_placeholder_fastpath_enabled
from .errorlog import get_logger

_log = get_logger(__name__)


class FastPathState(Enum):
    EMPTY = "empty"       # No effective input placeholders; skip allowed
    NON_EMPTY = "non_empty"  # At least one effective input present
    DISABLED = "disabled"    # Kill-switch disables fast-path globally


def _is_effective_input(ph: Dict[str, Any]) -> bool:
    """Return True if placeholder requires user input in the collect stage.

    Filtering rules (should mirror the collect frame classification):
      - Exclude types: reminder, note
      - Exclude link-like placeholders (explicit type 'link' or having 'url'/'href')
      - Exclude entries missing/blank 'name'
      - Heuristic: exclude names starting with 'reminder_' when not marked multiline
    """
    if not isinstance(ph, dict):
        return False
    name = (ph.get("name") or "").strip()
    if not name:
        return False
    ptype = (ph.get("type") or "").strip().lower()
    if ptype in {"reminder", "note"}:
        return False
    if ptype == "link" or ph.get("url") or ph.get("href"):
        return False
    if name.startswith("reminder_") and not ph.get("multiline"):
        return False
    return True


def evaluate_fastpath_state(template: Dict[str, Any]) -> FastPathState:
    """Evaluate tri-state skip decision for a template.

    - If disabled (via env/settings) => DISABLED
    - If placeholders absent/None/not list => EMPTY
    - If list, filter to effective inputs; if zero => EMPTY else NON_EMPTY
    """
    if not is_placeholder_fastpath_enabled():
        return FastPathState.DISABLED
    placeholders = template.get("placeholders") if isinstance(template, dict) else None
    if not isinstance(placeholders, list) or not placeholders:
        return FastPathState.EMPTY
    for ph in placeholders:
        try:
            if _is_effective_input(ph):
                return FastPathState.NON_EMPTY
        except Exception:
            # If a placeholder entry is malformed, ignore it for purposes of input detection
            continue
    return FastPathState.EMPTY


def log_fastpath_activation() -> None:
    """Emit a single debug-level log line for observability (non-sensitive)."""
    try:
        _log.debug("fastpath.placeholder_empty", extra={"activated": True})
    except Exception:
        # Be robust in environments without fully configured logging
        pass


__all__ = [
    "FastPathState",
    "evaluate_fastpath_state",
    "log_fastpath_activation",
]

