import os
import pathlib
import shutil
import subprocess
from typing import List

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "todoist_add.ps1"


def _have_pwsh() -> str:
    exe = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
    return exe or ""


pwsh = _have_pwsh()

def _pwsh_runnable() -> bool:
    if not pwsh:
        return False
    try:
        cp = subprocess.run([pwsh, "-NoProfile", "-Command", "Write-Output 1"], capture_output=True, text=True, timeout=5)
        return cp.returncode == 0
    except Exception:
        return False


@pytest.mark.skipif(not _pwsh_runnable(), reason="PowerShell not available or not runnable in sandbox")
def test_dry_run_with_env_token(monkeypatch, tmp_path):
    assert SCRIPT.exists(), "todoist_add.ps1 missing; implement script first"
    # Ensure env takes precedence
    monkeypatch.setenv("TODOIST_API_TOKEN", "ENV_TOKEN_VALUE")
    monkeypatch.setenv("TODOIST_DRY_RUN", "1")

    # Use minimal args: only action required
    args: List[str] = [pwsh, "-NoProfile", "-File", str(SCRIPT), "Feature - Do something — DoD: ", "NRA: ", "-DryRun"]
    cp = subprocess.run(args, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    out = (cp.stdout or "") + (cp.stderr or "")
    # Should not leak the token value
    assert "ENV_TOKEN_VALUE" not in out
    # Should mention dry run
    assert "DRY RUN" in out.upper()


@pytest.mark.skipif(not _pwsh_runnable(), reason="PowerShell not available or not runnable in sandbox")
def test_dry_run_with_repo_secret_file(monkeypatch):
    assert SCRIPT.exists(), "todoist_add.ps1 missing; implement script first"
    # Ensure env is NOT set; create a local secrets file
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.setenv("TODOIST_DRY_RUN", "1")

    secret_path = REPO_ROOT / "local.secrets.psd1"
    try:
        secret_path.write_text("@{ TODOIST_API_TOKEN = 'FILE_TOKEN_VALUE' }\n", encoding="utf-8")
        args: List[str] = [pwsh, "-NoProfile", "-File", str(SCRIPT), "Action only", "", "-DryRun"]
        cp = subprocess.run(args, capture_output=True, text=True)
        assert cp.returncode == 0, cp.stderr
        out = (cp.stdout or "") + (cp.stderr or "")
        assert "FILE_TOKEN_VALUE" not in out, "Token value must never be printed"
        assert "DRY RUN" in out.upper()
    finally:
        if secret_path.exists():
            secret_path.unlink()


@pytest.mark.skipif(not _pwsh_runnable(), reason="PowerShell not available or not runnable in sandbox")
def test_error_when_no_token_available(monkeypatch):
    assert SCRIPT.exists(), "todoist_add.ps1 missing; implement script first"
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.setenv("TODOIST_DRY_RUN", "1")
    # Ensure secrets file does not exist
    secret_path = REPO_ROOT / "local.secrets.psd1"
    if secret_path.exists():
        secret_path.unlink()

    args: List[str] = [pwsh, "-NoProfile", "-File", str(SCRIPT), "Action only", "", "-DryRun"]
    cp = subprocess.run(args, capture_output=True, text=True)
    # Should fail with clear guidance
    assert cp.returncode != 0, "Should fail when no token available"
    out = (cp.stdout or "") + (cp.stderr or "")
    assert "TODOIST_API_TOKEN" in out and "local.secrets.psd1" in out
