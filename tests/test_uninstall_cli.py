import sys
from pathlib import Path
import json


def _find_repo_root(start: Path) -> Path:
    for d in [start] + list(start.parents):
        if (d / "pyproject.toml").exists():
            return d
    return start.parent


_repo_root = _find_repo_root(Path(__file__).resolve())
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from prompt_automation.cli.controller import PromptCLI
from prompt_automation.uninstall.artifacts import Artifact
from prompt_automation.uninstall import executor


def test_uninstall_cli_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNINSTALL_FEATURE_FLAG", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    art_path = tmp_path / "dummy.txt"
    art_path.write_text("payload")
    artifact = Artifact("dummy", "file", art_path, purge_candidate=True)

    def detector(_platform):
        return [artifact] if art_path.exists() else []

    monkeypatch.setattr(executor, "_DEF_DETECTORS", [detector])
    cli = PromptCLI()

    cli.main(["uninstall", "--purge-data", "--force", "--dry-run", "--json", "--platform", "win32"])
    out1 = capsys.readouterr().out
    data1 = json.loads(out1)
    assert art_path.exists()
    assert data1["removed"][0]["status"] == "planned"

    cli.main(["uninstall", "--purge-data", "--force", "--json", "--platform", "win32"])
    out2 = capsys.readouterr().out
    data2 = json.loads(out2)
    assert not art_path.exists()
    assert data2["removed"][0]["status"] == "removed"

    cli.main(["uninstall", "--purge-data", "--force", "--json", "--platform", "win32"])
    out3 = capsys.readouterr().out
    data3 = json.loads(out3)
    assert data3["removed"] == []
