"""Single-window GUI package."""
from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .controller import SingleWindowApp as _SWA


def _load() -> "_SWA":
    from .controller import SingleWindowApp as _App

    return _App


def run() -> Tuple[None, None]:  # pragma: no cover - thin shim
    """Convenience shim to mirror legacy ``single_window.run`` behavior."""
    app = _load()()
    return app.run()


__all__ = ["SingleWindowApp", "run"]


def __getattr__(name: str):  # pragma: no cover - simple proxy
    if name == "SingleWindowApp":
        return _load()
    raise AttributeError(name)
