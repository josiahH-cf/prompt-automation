import subprocess
from typing import Any

from .errorlog import get_logger

_log = get_logger(__name__)


def _sanitize_arg(arg: str) -> str:
    """Basic arg sanitizer removing newlines and command separators."""
    bad_chars = ['\n', '\r', ';', '&', '|']
    for ch in bad_chars:
        arg = arg.replace(ch, ' ')
    return arg


def safe_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run subprocess with simple argument sanitization."""
    clean = [_sanitize_arg(str(c)) for c in cmd]
    try:
        return subprocess.run(clean, **kwargs)
    except Exception as e:  # pragma: no cover - depends on platform
        _log.error("command failed: %s", e)
        raise
