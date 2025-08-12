"""Shared append-to-file logic used by GUI and CLI."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..errorlog import get_logger

_log = get_logger(__name__)


def _append_to_files(var_map: dict[str, Any], text: str) -> None:
    """Append ``text`` to any paths specified by append_file placeholders."""
    for key, path in var_map.items():
        if key == "append_file" or key.endswith("_append_file"):
            if not path:
                continue
            try:
                p = Path(path).expanduser()
                with p.open("a", encoding="utf-8") as fh:
                    if key == "context_append_file":
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        fh.write(f"\n\n--- {ts} ---\n{text}\n")
                    else:
                        fh.write(text + "\n")
            except Exception as e:  # pragma: no cover - filesystem
                _log.warning("failed to append to %s: %s", path, e)


__all__ = ["_append_to_files"]
