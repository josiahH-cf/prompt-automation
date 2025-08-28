from __future__ import annotations

from typing import Optional

from ..errorlog import get_logger
from .model import ThemeRegistry, get_registry as _model_registry
from ..variables import storage as _storage


_log = get_logger(__name__)


def get_user_theme_preference() -> Optional[str]:
    try:
        val = _storage.get_setting_theme()
        return val
    except Exception:
        return None


def set_user_theme_preference(name: str) -> None:
    try:
        _storage.set_setting_theme(name)
    except Exception:
        pass


def get_enable_theming() -> bool:
    try:
        return _storage.get_setting_enable_theming()
    except Exception:
        return True


def set_enable_theming(enabled: bool) -> None:
    try:
        _storage.set_setting_enable_theming(bool(enabled))
    except Exception:
        pass


def get_registry() -> ThemeRegistry:
    return _model_registry()


class ThemeResolver:
    """Resolve active theme with precedence and allow runtime toggle.

    Precedence: CLI override > session override (toggle) > persisted > default(light).
    If theming is disabled via config, the resolved theme is always 'light'.
    """

    def __init__(self, registry: ThemeRegistry) -> None:
        self._registry = registry
        self._session: Optional[str] = None
        self._toggles: int = 0

    def _sanitize(self, name: Optional[str]) -> Optional[str]:
        if not name or not isinstance(name, str):
            return None
        return name if self._registry.has(name) else None

    def resolve(self, cli_override: Optional[str] = None) -> str:
        if not get_enable_theming():
            return 'light'
        src = 'default'
        # Allow environment-provided override if explicit param is None
        if cli_override is None:
            import os as _os
            cli_override = _os.environ.get('PROMPT_AUTOMATION_THEME')
        name = self._sanitize(cli_override)
        if name:
            src = 'cli'
        if not name and self._session:
            name = self._sanitize(self._session)
            if name:
                src = 'session'
        if not name:
            name = self._sanitize(get_user_theme_preference())
            if name:
                src = 'persisted'
        if not name:
            name = 'light'
        _log.info('theme.resolve name=%s source=%s', name, src)
        return name

    def toggle(self) -> str:
        if not get_enable_theming():
            # keep light enforced
            return 'light'
        current = self._sanitize(get_user_theme_preference()) or 'light'
        new = 'dark' if current != 'dark' else 'light'
        if not self._registry.has(new):
            new = 'light'
        self._session = new
        self._toggles += 1
        try:
            set_user_theme_preference(new)
        except Exception:
            pass
        _log.info('theme.switch %s->%s', current, new)
        return new

    def get_toggle_count(self) -> int:
        return self._toggles

    def set_session_override(self, name: Optional[str]) -> None:
        self._session = self._sanitize(name)
