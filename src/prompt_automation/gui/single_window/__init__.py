"""Single-window GUI package."""
from __future__ import annotations

from .controller import SingleWindowApp


def run() -> tuple[None, None]:  # pragma: no cover - thin shim
    """Convenience shim to mirror legacy ``single_window.run`` behavior."""
    app = SingleWindowApp()
    return app.run()


__all__ = ["SingleWindowApp", "run"]
