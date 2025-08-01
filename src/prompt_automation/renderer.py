"""Loading and rendering prompt templates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .errorlog import get_logger

_log = get_logger(__name__)


def load_template(path: Path) -> Dict:
    """Load JSON template file with validation."""
    path = path.expanduser().resolve()
    if not path.is_file():
        _log.error("template not found: %s", path)
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_template(data: Dict) -> bool:
    """Basic schema validation used in tests."""
    required = {"id", "title", "style", "template", "placeholders"}
    return required.issubset(data)


def fill_placeholders(lines: Iterable[str], vars: Dict[str, str]) -> str:
    """Replace ``{{name}}`` placeholders with values."""
    out: List[str] = []
    for line in lines:
        for k, v in vars.items():
            line = line.replace(f"{{{{{k}}}}}", v)
        out.append(line)
    return "\n".join(out)
