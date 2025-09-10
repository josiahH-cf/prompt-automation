from __future__ import annotations

import os
import platform
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from ..errorlog import get_logger
from ..variables.storage import get_boolean_setting

_log = get_logger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _which(cmd: str) -> Optional[str]:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = Path(p) / cmd
        if cand.exists() and os.access(cand, os.X_OK):
            return str(cand)
    return None


def _detect_powershell() -> Optional[str]:
    # Prefer Windows PowerShell when on Windows, else pwsh if available
    if os.name == "nt":
        return _which("powershell.exe") or "powershell"
    return _which("pwsh")


def _script_path_from_repo() -> Optional[Path]:
    # Try PROMPT_AUTOMATION_REPO, else walk up from this file
    repo = os.environ.get("PROMPT_AUTOMATION_REPO")
    if repo:
        p = Path(repo).expanduser().resolve() / "scripts" / "todoist_add.ps1"
        if p.exists():
            return p
    here = Path(__file__).resolve()
    for up in [here.parent.parent.parent.parent, here.parent.parent.parent]:
        # src/prompt_automation/services/ -> repo root is 3 levels up from src
        # But guard with presence of scripts/todoist_add.ps1
        cand = up / "scripts" / "todoist_add.ps1"
        if cand.exists():
            return cand
    return None


def build_summary_and_note(action: str, type_: str | None, dod: str | None, nra: str | None) -> Tuple[str, Optional[str]]:
    # Assemble Summary: "[type] - [action] — DoD: [dod]" with omissions
    action = (action or "").strip()
    type_ = (type_ or "").strip()
    dod = (dod or "").strip()
    nra = (nra or "").strip()

    parts = []
    if type_:
        parts.append(type_)
    if action:
        if parts:
            parts.append("- "+action)
        else:
            parts.append(action)
    summary = " ".join(parts).strip()
    if dod:
        if summary:
            summary = f"{summary} — DoD: {dod}"
        else:
            summary = f"DoD: {dod}"

    note = f"NRA: {nra}" if nra else None
    return summary, note


def send_to_todoist(summary: str, note: Optional[str]) -> Tuple[bool, str]:
    """Invoke the repo PowerShell script to create a Todoist task.

    Returns (ok, message). Never logs secrets; only token source is logged by the script.
    Honors env flags:
      - SEND_TODOIST_AFTER_RENDER: default off
      - TODOIST_DRY_RUN: when true, script runs with -DryRun
      - NTSK_DISABLE: kill-switch honored by the script
      - TODOIST_TOKEN_ENV: optional override of token env var name
    """
    # In dev/test runs, default to disabled unless explicitly enabled via env
    if os.environ.get("PROMPT_AUTOMATION_DEV") == "1" and os.environ.get("SEND_TODOIST_AFTER_RENDER") is None:
        return True, "disabled"
    # Gate by env first; if off, also check user setting key 'send_todoist_after_render'
    if not (_bool_env("SEND_TODOIST_AFTER_RENDER", default=False) or get_boolean_setting("send_todoist_after_render", False)):
        return True, "disabled"

    # Non-blocking skip if PowerShell unavailable
    ps = _detect_powershell()
    if not ps:
        _log.warning("todoist.post_action powershell_unavailable platform=%s", platform.platform())
        return True, "powershell_missing"

    script = _script_path_from_repo()
    if not script or not script.exists():
        _log.warning("todoist.post_action script_missing")
        return False, "script_missing"

    args = [ps, "-NoProfile"]
    # On Windows PowerShell, ExecutionPolicy bypass to be safe
    if os.name == "nt":
        args += ["-ExecutionPolicy", "Bypass"]
    args += ["-File", str(script), summary]
    if note is not None:
        args.append(note)
    # Dry-run may be enabled via env or persisted settings
    dry_run = _bool_env("TODOIST_DRY_RUN", default=False) or get_boolean_setting("todoist_dry_run", False)
    if dry_run:
        args.append("-DryRun")

    start = time.perf_counter()
    try:
        # Structured logs without content duplication; script already logs content
        _log.info("todoist.post_action start", extra={"dry_run": dry_run})
    except Exception:
        pass
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        ok = proc.returncode == 0
        msg = proc.stdout.strip() or proc.stderr.strip()
        try:
            _log.info(
                "todoist.post_action end",
                extra={"ok": ok, "status": proc.returncode, "duration_ms": int((time.perf_counter() - start) * 1000)},
            )
        except Exception:
            pass
        return ok, msg[:500]
    except subprocess.TimeoutExpired:
        try:
            _log.warning("todoist.post_action timeout")
        except Exception:
            pass
        return False, "timeout"
    except Exception as e:
        try:
            _log.error("todoist.post_action error %s", e)
        except Exception:
            pass
        return False, str(e)


__all__ = ["send_to_todoist", "build_summary_and_note"]
