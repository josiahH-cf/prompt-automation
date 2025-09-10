import sys
from pathlib import Path

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
from prompt_automation.uninstall import executor
from prompt_automation.uninstall.artifacts import Artifact


def _make_artifact(tmp_path: Path, name: str) -> Artifact:
    path = tmp_path / f"{name}.txt"
    path.write_text("data")
    return Artifact(name, "file", path)


def test_all_flag_adds_optional_detectors(monkeypatch, tmp_path):
    base = _make_artifact(tmp_path, "base")
    extra = _make_artifact(tmp_path, "extra")
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _p: [base]])
    monkeypatch.setattr(executor, "_OPT_DETECTORS", [lambda _p: [extra]])

    # Without --all, optional detector should not run
    opts = UninstallOptions(force=True)
    code, results = executor.run(opts)
    assert code == 0
    assert not base.path.exists()
    assert extra.path.exists()
    assert {r["id"] for r in results["removed"]} == {"base"}

    # With --all, optional detector is included
    base2 = _make_artifact(tmp_path, "base2")
    extra2 = _make_artifact(tmp_path, "extra2")
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _p: [base2]])
    monkeypatch.setattr(executor, "_OPT_DETECTORS", [lambda _p: [extra2]])

    opts_all = UninstallOptions(force=True, all=True)
    code2, results2 = executor.run(opts_all)
    assert code2 == 0
    assert not base2.path.exists()
    assert not extra2.path.exists()
    assert {r["id"] for r in results2["removed"]} == {"base2", "extra2"}
