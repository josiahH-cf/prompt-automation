from __future__ import annotations

"""Background hotkey registration helpers."""

from typing import Any
import time

from .errorlog import get_logger
from .features import is_background_hotkey_enabled

try:  # pragma: no cover - optional dependency
    from . import metrics as _metrics
except Exception:  # pragma: no cover - defensive
    _metrics = None

HOTKEY_ID = "prompt_automation.activate"
DEFAULT_COMBO = "Ctrl+Shift+3"

_log = get_logger(__name__)


_settings_ref: Any | None = None


def ensure_registered(settings: Any, shortcut_service: Any) -> bool:
    """Register the background hotkey with ``shortcut_service``.

    Parameters
    ----------
    settings:
        Mapping-like object containing configuration. The ``combo`` or ``hotkey``
        value, if present, overrides :data:`DEFAULT_COMBO`.
    shortcut_service:
        Object exposing ``register_hotkey(id, combo, callback)``. The callback
        will be invoked when the hotkey is triggered.
    """
    global _settings_ref
    _settings_ref = settings

    if not is_background_hotkey_enabled():
        try:
            _log.warning("background_hotkey_env_disabled")
        except Exception:
            pass
        return False

    combo = DEFAULT_COMBO
    try:
        if isinstance(settings, dict):
            combo = settings.get("combo") or settings.get("hotkey") or DEFAULT_COMBO
        else:  # attribute style access
            combo = getattr(settings, "combo", None) or getattr(settings, "hotkey", None) or DEFAULT_COMBO
    except Exception:
        combo = DEFAULT_COMBO

    try:
        shortcut_service.register_hotkey(HOTKEY_ID, combo, on_activate)
        _log.info("background_hotkey_registered id=%s combo=%s", HOTKEY_ID, combo)
        return True
    except Exception as e:  # pragma: no cover - defensive
        try:
            _log.error("background_hotkey_register_failed id=%s combo=%s error=%s", HOTKEY_ID, combo, e)
        except Exception:
            pass
        return False


def unregister(shortcut_service: Any) -> None:
    """Remove the background hotkey from ``shortcut_service``."""
    try:
        shortcut_service.unregister_hotkey(HOTKEY_ID)
        _log.info("background_hotkey_unregistered id=%s", HOTKEY_ID)
    except Exception as e:  # pragma: no cover - defensive
        try:
            _log.error("background_hotkey_unregister_failed id=%s error=%s", HOTKEY_ID, e)
        except Exception:
            pass


def on_activate() -> None:
    """Handle hotkey activation.

    Chooses between ``trigger_prompt_sequence`` and
    ``run_prompt_sequence_minimal`` depending on ``settings.activateMinimal``.
    These callables are expected to be present in the import scope when the
    hotkey fires. Errors are logged but otherwise swallowed to avoid crashing
    background handlers.
    """
    settings = _settings_ref or {}
    minimal = False
    espanso_enabled = True
    try:
        if isinstance(settings, dict):
            minimal = bool(settings.get("activateMinimal"))
            espanso_enabled = bool(settings.get("espanso_enabled", True))
        else:
            minimal = bool(getattr(settings, "activateMinimal", False))
            espanso_enabled = bool(getattr(settings, "espanso_enabled", True))
    except Exception:
        minimal = False
        espanso_enabled = True
    if not espanso_enabled:
        minimal = True

    start = time.perf_counter()
    _log.info("background_hotkey_invoked minimal=%s", minimal)
    if _metrics is not None:
        try:  # pragma: no cover - optional metrics
            _metrics.counter("background_hotkey.invocations").inc()
        except Exception:  # pragma: no cover - defensive
            pass

    try:
        if minimal:
            run_prompt_sequence_minimal()  # type: ignore[name-defined]
        else:
            trigger_prompt_sequence()  # type: ignore[name-defined]
    except Exception as e:  # pragma: no cover - defensive
        if _metrics is not None:
            try:  # pragma: no cover - optional metrics
                _metrics.counter("background_hotkey.failures").inc()
            except Exception:  # pragma: no cover - defensive
                pass
        try:
            _log.error("background_hotkey_activation_failed minimal=%s error=%s", minimal, e)
        except Exception:
            pass
    finally:
        try:
            duration_ms = int((time.perf_counter() - start) * 1000)
            _log.info(
                "background_hotkey_completed minimal=%s duration_ms=%s",
                minimal,
                duration_ms,
            )
        except Exception:  # pragma: no cover - defensive
            pass
