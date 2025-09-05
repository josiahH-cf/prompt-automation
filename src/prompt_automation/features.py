from __future__ import annotations

"""Feature flags and configuration toggles.

Currently supports:
  - hierarchical_templates: enable hierarchical template browsing in UI/CLI.
  - reminders: enable read-only reminders parsing and rendering.

Resolution order for hierarchical_templates (mimics theme behavior):
  1. Environment variable PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES
     - truthy: "1", "true", "yes", "on"
     - falsy:  "0", "false", "no", "off"
  2. Settings file under PROMPTS_DIR/Settings/settings.json key "hierarchical_templates"
  3. Default: True (auto-enabled unless explicitly off)
"""

import json
import os
from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR
from .errorlog import get_logger

_log = get_logger(__name__)


def _coerce_bool(val: Any) -> bool | None:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
    return None


def is_hierarchy_enabled() -> bool:
    env = os.environ.get("PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return coerced
    try:
        settings = PROMPTS_DIR / "Settings" / "settings.json"
        if settings.exists():
            data = json.loads(settings.read_text())
            v = data.get("hierarchical_templates")
            coerced = _coerce_bool(v)
            if coerced is not None:
                return coerced
    except Exception as e:  # pragma: no cover - permissive
        try:
            _log.debug("feature_flag_read_failed error=%s", e)
        except Exception:
            pass
    # Default to enabled unless explicitly disabled
    return True


def set_user_hierarchy_preference(enabled: bool) -> None:
    """Persist the hierarchical_templates preference in settings.json.

    Creates the Settings directory/file if missing and preserves other keys.
    """
    try:
        settings_dir = PROMPTS_DIR / "Settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings_path = settings_dir / "settings.json"
        data: dict[str, Any] = {}
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text())
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}
        data["hierarchical_templates"] = bool(enabled)
        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:  # pragma: no cover - defensive
        try:
            _log.error("failed_to_persist_hierarchy_preference error=%s", e)
        except Exception:
            pass


__all__ = ["is_hierarchy_enabled", "set_user_hierarchy_preference"]
 
def is_reminders_enabled() -> bool:
    """Resolve reminders feature flag.

    Resolution order:
      1. Env PROMPT_AUTOMATION_REMINDERS (1/true/on vs 0/false/off)
      2. Settings Settings/settings.json key "reminders_enabled"
      3. Default: True (enabled)
    """
    env = os.environ.get("PROMPT_AUTOMATION_REMINDERS")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return coerced
    try:
        settings = PROMPTS_DIR / "Settings" / "settings.json"
        if settings.exists():
            data = json.loads(settings.read_text())
            v = data.get("reminders_enabled")
            coerced = _coerce_bool(v)
            if coerced is not None:
                return coerced
    except Exception as e:  # pragma: no cover - permissive
        try:
            _log.debug("reminders_flag_read_failed error=%s", e)
        except Exception:
            pass
    return True


__all__.append("is_reminders_enabled")


def is_reminders_timing_enabled() -> bool:
    """Dev-only flag to log reminder parsing timing.

    Env: PROMPT_AUTOMATION_REMINDERS_TIMING (1/true/on vs 0/false/off)
    Settings: Settings/settings.json key "reminders_timing"
    Default: False
    """
    env = os.environ.get("PROMPT_AUTOMATION_REMINDERS_TIMING")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return coerced
    try:
        settings = PROMPTS_DIR / "Settings" / "settings.json"
        if settings.exists():
            data = json.loads(settings.read_text())
            v = data.get("reminders_timing")
            coerced = _coerce_bool(v)
            if coerced is not None:
                return coerced
    except Exception:
        pass
    return False


__all__.append("is_reminders_timing_enabled")


# --- Placeholder fast-path (auto-skip collect stage) ------------------------
def is_placeholder_fastpath_enabled() -> bool:
    """Return True if the placeholder-empty fast-path is enabled.

    Resolution order (env overrides settings):
      1. Env PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH
         - truthy (1/true/on)  => disabled (return False)
         - falsy  (0/false/off)=> enabled  (return True)
      2. Settings Settings/settings.json key "disable_placeholder_fastpath"
         - truthy => disabled (False)
         - falsy  => enabled  (True)
      3. Default: enabled (True)
    """
    env = os.environ.get("PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return not coerced
    try:
        settings = PROMPTS_DIR / "Settings" / "settings.json"
        if settings.exists():
            data = json.loads(settings.read_text())
            v = data.get("disable_placeholder_fastpath")
            coerced = _coerce_bool(v)
            if coerced is not None:
                return not coerced
    except Exception:
        pass
    return True


__all__.append("is_placeholder_fastpath_enabled")
