import subprocess
from typing import Any


def _sanitize_arg(arg: str) -> str:
    """Basic arg sanitizer removing newlines and command separators."""
    bad_chars = ['\n', '\r', ';', '&', '|']
    for ch in bad_chars:
        arg = arg.replace(ch, ' ')
    return arg


def safe_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Run subprocess with simple argument sanitization."""
    clean = [_sanitize_arg(str(c)) for c in cmd]
    return subprocess.run(clean, **kwargs)
