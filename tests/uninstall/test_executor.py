import builtins
from pathlib import Path
import sys

import pytest


def _find_repo_root(start: Path) -> Path:
    for d in [start] + list(start.parents):
        if (d / "pyproject.toml").exists():
            return d
    return start.parent


_repo_root = _find_repo_root(Path(__file__).resolve())
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from prompt_automation.cli.controller import UninstallOptions
from prompt_automation.uninstall import executor, run_uninstall
from prompt_automation.uninstall.artifacts import Artifact
import json


@pytest.fixture(autouse=True)
def clear_detectors(monkeypatch):
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [])


def _make_artifact(tmp_path: Path) -> Artifact:
    path = tmp_path / "dummy.txt"
    path.write_text("data")
    return Artifact("dummy", "file", path)


def test_conflicting_flags_exit_code(monkeypatch):
    options = UninstallOptions(purge_data=True, keep_user_data=True)
    code = run_uninstall(options)
    assert code == 1


def test_confirmation_prompt_interactive(monkeypatch, tmp_path):
    art = _make_artifact(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])
    called = False

    def fake_input(prompt=""):
        nonlocal called
        called = True
        return "n"

    monkeypatch.setattr(builtins, "input", fake_input)
    options = UninstallOptions()
    code, results = executor.run(options)
    assert called is True
    assert art.path.exists()
    assert code == 2
    assert results["skipped"][0]["status"] == "skipped"
    assert results["partial"] is True


@pytest.mark.parametrize("flag", ["force", "non_interactive"])
def test_force_or_non_interactive_skips_prompt(monkeypatch, tmp_path, flag):
    art = _make_artifact(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])
    called = False

    def fake_input(prompt=""):
        nonlocal called
        called = True
        return "y"

    monkeypatch.setattr(builtins, "input", fake_input)
    kwargs = {flag: True}
    options = UninstallOptions(**kwargs)
    code, results = executor.run(options)
    assert called is False
    assert code == 0
    assert not art.path.exists()
    assert results["removed"][0]["status"] == "removed"
    assert results["partial"] is False


def test_failure_sets_exit_code(monkeypatch, tmp_path):
    art = _make_artifact(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])

    def failing_remove(_artifact: Artifact) -> bool:
        return False

    monkeypatch.setattr(executor, "_remove", failing_remove)
    options = UninstallOptions(force=True)
    code, results = executor.run(options)
    assert code == 2
    assert results["errors"][0]["status"] == "failed"
    assert results["partial"] is True
    assert art.path.exists()


def test_idempotent_runs(monkeypatch, tmp_path):
    art = _make_artifact(tmp_path)

    def detector(_platform):
        return [art] if art.path.exists() else []

    monkeypatch.setattr(executor, "_DEF_DETECTORS", [detector])
    options = UninstallOptions(force=True)
    code1, results1 = executor.run(options)
    assert code1 == 0
    assert results1["removed"][0]["status"] == "removed"
    assert results1["partial"] is False
    assert not art.path.exists()

    code2, results2 = executor.run(options)
    assert code2 == 0
    assert results2 == {"removed": [], "skipped": [], "errors": [], "partial": False}


def test_json_output(monkeypatch, tmp_path, capsys):
    art = _make_artifact(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])
    options = UninstallOptions(force=True, json=True, dry_run=True)
    code, results = executor.run(options)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert code == 0
    assert data == results
    assert data["removed"][0]["path"] == str(art.path)
    assert data["removed"][0]["status"] == "planned"
