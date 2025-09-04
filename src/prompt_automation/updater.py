"""Lightweight PyPI auto-update helper.

Checks PyPI for a newer released version of ``prompt-automation`` and if
found attempts to upgrade the local installation using ``pipx upgrade``.

Behaviour is controlled by environment variable
``PROMPT_AUTOMATION_AUTO_UPDATE`` (default ``1`` = enabled). Set to ``0``
to disable the check. A small state file stores the timestamp of the
last check to rate‑limit network calls to once per 24 hours.

All failures are silent; the main application should never be blocked
by update logic. The operation intentionally avoids additional third
party dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from pathlib import Path
from typing import Optional
from urllib import request, error
import sys

from .utils import safe_run

try:  # Python >=3.8
    from importlib import metadata as importlib_metadata
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore

PYPI_URL = "https://pypi.org/pypi/prompt-automation/json"
STATE_PATH = Path.home() / ".prompt-automation" / "auto-update.json"
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

RATE_LIMIT_SECONDS = 60 * 60 * 24  # 24h

# Platform flag (indirectly patchable in tests)
_PLATFORM = sys.platform


@dataclass
class UpdateState:
    last_check: float = 0.0
    last_version: str = ""

    @classmethod
    def load(cls) -> "UpdateState":
        try:
            data = json.loads(STATE_PATH.read_text())
            return cls(**data)
        except Exception:
            return cls()

    def save(self) -> None:
        try:
            STATE_PATH.write_text(json.dumps(self.__dict__))
        except Exception:
            pass


def _current_version() -> str:
    try:
        return importlib_metadata.version("prompt-automation")
    except Exception:  # pragma: no cover
        return "0"


def _fetch_latest_version(timeout: float = 2.0) -> Optional[str]:
    try:
        with request.urlopen(PYPI_URL, timeout=timeout) as resp:  # pragma: no cover - network
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except error.URLError:
        return None
    except Exception:
        return None


def _should_rate_limit(last_check: float) -> bool:
    return (time.time() - last_check) < RATE_LIMIT_SECONDS


def _is_newer(remote: str, local: str) -> bool:
    def parse(v: str):
        return [int(p) if p.isdigit() else p for p in v.replace("-", ".").split(".")]
    try:
        return parse(remote) > parse(local)
    except Exception:
        return remote != local


def _have_pipx() -> bool:
    from shutil import which
    return which("pipx") is not None


def _upgrade_via_pipx() -> None:
    """Attempt to upgrade via pipx with resilient fallbacks.

    Problem: On Windows + WSL workflows the provided install script may copy the
    project to a temporary directory (e.g. %TEMP%/prompt-automation-install) and
    run ``pipx install <that-temp-path>``. After installation the temp folder is
    deleted. ``pipx upgrade`` later attempts to resolve the *original* local
    path spec (now missing) and emits:

        "Unable to parse package spec: C:\\Users\\...\\Temp\\prompt-automation-install"

    This function detects that failure mode and transparently falls back to a
    clean forced install from PyPI (resetting the spec to the package name) so
    subsequent upgrades work normally. All failures remain silent by design.
    Set ``PROMPT_AUTOMATION_DISABLE_PIPX_FALLBACK=1`` to disable the fallback.
    """
    if os.environ.get("PROMPT_AUTOMATION_DISABLE_PIPX_FALLBACK") == "1":  # pragma: no cover - opt out
        try:
            safe_run(["pipx", "upgrade", "prompt-automation"], capture_output=True, timeout=30)
        except Exception:
            pass
        return

    try:
        res = safe_run(
            ["pipx", "upgrade", "prompt-automation"], capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0:
            return
        combined = (res.stdout or "") + "\n" + (res.stderr or "")
        if "Unable to parse package spec" in combined or "parse package spec" in combined:
            # Fallback: reinstall from PyPI (forces spec to canonical name)
            try:
                safe_run(
                    ["pipx", "install", "--force", "prompt-automation"],
                    capture_output=True,
                    timeout=60,
                )
            except Exception:
                # Final fallback: user install via pip (no pipx) so they at least get newer code
                try:
                    safe_run(
                        ["python", "-m", "pip", "install", "--upgrade", "--user", "prompt-automation"],
                        capture_output=True,
                        timeout=60,
                    )
                except Exception:
                    pass
    except Exception:
        # Silent by design
        pass


def check_for_update() -> None:
    # Global opt-out
    if os.environ.get("PROMPT_AUTOMATION_AUTO_UPDATE", "1") == "0":
        return

    # Safety default on Windows: skip implicit pipx upgrades unless explicitly opted in.
    # This avoids breaking pipx shims when installed from temporary/local specs
    # (a common pattern on Windows when installing from a WSL path via PowerShell).
    if _PLATFORM.startswith("win") and os.environ.get(
        "PROMPT_AUTOMATION_WINDOWS_ALLOW_PIPX_UPDATE", "0"
    ) != "1":
        return

    state = UpdateState.load()
    if _should_rate_limit(state.last_check):
        return

    local_version = _current_version()
    latest = _fetch_latest_version()
    state.last_check = time.time()
    if latest:
        state.last_version = latest
    state.save()

    if not latest or not _is_newer(latest, local_version):
        return

    if _have_pipx():
        _upgrade_via_pipx()


__all__ = ["check_for_update"]
