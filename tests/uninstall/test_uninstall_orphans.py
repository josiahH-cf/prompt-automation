import builtins
import importlib.util
from pathlib import Path
import sys

import pytest

# Helpers to locate repo root and ensure src on sys.path

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
from prompt_automation.uninstall import executor, orphan


@pytest.fixture(autouse=True)
def clear_detectors(monkeypatch):
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [])
    monkeypatch.setattr(executor, "_OPT_DETECTORS", [])


def _make_orphan(tmp_path: Path) -> Path:
    bin_dir = tmp_path / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    script = bin_dir / "prompt-automation"
    script.write_text("echo")
    return script


def test_detect_orphans(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    script = _make_orphan(tmp_path)
    arts = orphan.detect_orphans("linux")
    assert [a.path for a in arts] == [script]


def test_confirmation_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    script = _make_orphan(tmp_path)
    called = False

    def fake_input(prompt=""):
        nonlocal called
        called = True
        return "n"

    monkeypatch.setattr(builtins, "input", fake_input)
    options = UninstallOptions(confirm_orphans=True)
    code, results = executor.run(options)
    assert called is True
    assert script.exists()
    assert code == 2
    assert results["skipped"][0]["kind"] == "orphan"
    assert results["partial"] is True


def test_remove_orphans_flag(monkeypatch, tmp_path):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    script = _make_orphan(tmp_path)
    called = False

    def fake_input(prompt=""):
        nonlocal called
        called = True
        return "n"

    monkeypatch.setattr(builtins, "input", fake_input)
    options = UninstallOptions(remove_orphans=True)
    code, results = executor.run(options)
    assert called is False
    assert not script.exists()
    assert code == 0
    assert results["removed"][0]["kind"] == "orphan"
