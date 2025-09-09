import pathlib
from typing import Any, Dict

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML required for espanso tests")


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE_YML = REPO_ROOT / "espanso-package" / "match" / "base.yml"


def _load_base_yaml() -> Dict[str, Any]:
    assert BASE_YML.exists(), f"Missing {BASE_YML}"
    return yaml.safe_load(BASE_YML.read_text(encoding="utf-8"))


def test_ntsk_command_uses_repo_script_and_not_appdata():
    data = _load_base_yaml()
    matches = data.get("matches") or []
    ntsk = next((m for m in matches if m.get("trigger") == ":ntsk"), None)
    assert ntsk is not None, ":ntsk match not found in base.yml"

    # Find the vars entry with the shell command
    vars_list = ntsk.get("vars") or []
    shell_var = next((v for v in vars_list if v.get("name") == "create_todoist_task_ntsk"), None)
    assert shell_var is not None, "create_todoist_task_ntsk var missing"
    cmd = ((shell_var.get("params") or {}).get("cmd") or "").strip()
    assert cmd, "cmd string missing for :ntsk"

    # Must not reference legacy APPDATA script path
    assert "%APPDATA%\\espanso\\scripts\\todoist_add.ps1" not in cmd, "should not use APPDATA path"

    # Must invoke powershell and use -File against repo-resident script
    assert "powershell" in cmd.lower(), "should invoke powershell"
    assert "-File" in cmd, "should use -File for final invocation"
    assert "scripts\\todoist_add.ps1" in cmd or "scripts/todoist_add.ps1" in cmd, "should point to repo script"

    # Should use a bridging strategy: env/WSL detection or a stable UNC path
    assert (
        "PROMPT_AUTOMATION_REPO" in cmd or "wslpath" in cmd or "wsl.exe" in cmd or "\\\\wsl.localhost\\" in cmd
    ), "should handle WSL/Windows path bridging"

