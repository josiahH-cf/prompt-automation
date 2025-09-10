import subprocess
from pathlib import Path
import sys
import json

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

from prompt_automation.uninstall import detectors, executor, multi_python  # noqa: E402
from prompt_automation.uninstall.artifacts import Artifact  # noqa: E402
from prompt_automation.cli.controller import UninstallOptions  # noqa: E402


def test_detect_pip_install_records_interpreters(monkeypatch, tmp_path):
    py1 = tmp_path / "py1"
    py2 = tmp_path / "py2"
    pkg1 = tmp_path / "pkg1"
    pkg2 = tmp_path / "pkg2"
    pkg1.mkdir()
    pkg2.mkdir()
    monkeypatch.setattr(multi_python, "enumerate_pythons", lambda: [py1, py2])

    out1 = json.dumps({"location": str(pkg1), "requires_priv": False})
    out2 = json.dumps({"location": str(pkg2), "requires_priv": True})

    def fake_run(cmd, capture_output=True, text=True):
        if cmd[0] == str(py1):
            return subprocess.CompletedProcess(cmd, 0, stdout=out1, stderr="")
        elif cmd[0] == str(py2):
            return subprocess.CompletedProcess(cmd, 0, stdout=out2, stderr="")
        raise AssertionError("unexpected interpreter")

    monkeypatch.setattr(subprocess, "run", fake_run)
    artifacts = detectors.detect_pip_install()
    assert {a.interpreter for a in artifacts} == {py1, py2}
    assert {a.requires_privilege for a in artifacts} == {False, True}


def test_executor_uninstalls_each_interpreter(monkeypatch, tmp_path):
    py1 = tmp_path / "py1"
    py2 = tmp_path / "py2"
    pkg1 = tmp_path / "pkg1"
    pkg2 = tmp_path / "pkg2"
    pkg1.mkdir()
    pkg2.mkdir()
    art1 = Artifact("pip1", "pip", pkg1, interpreter=py1)
    art2 = Artifact("pip2", "pip", pkg2, interpreter=py2)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _p: [art1, art2]])

    calls = []
    mapping = {py1: pkg1, py2: pkg2}

    def fake_uninstall(interpreter):
        calls.append(interpreter)
        mapping[interpreter].rmdir()
        return True, ""

    monkeypatch.setattr(multi_python, "uninstall", fake_uninstall)
    options = UninstallOptions(force=True)
    code, results = executor.run(options)
    assert code == 0
    assert set(calls) == {py1, py2}
    assert results["partial"] is False
    assert {entry["interpreter"] for entry in results["removed"]} == {str(py1), str(py2)}


def test_executor_reports_failures(monkeypatch, tmp_path):
    py = tmp_path / "py"
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    art = Artifact("pip", "pip", pkg, interpreter=py)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _p: [art]])

    def fail_uninstall(interpreter):
        return False, "boom"

    monkeypatch.setattr(multi_python, "uninstall", fail_uninstall)
    options = UninstallOptions(force=True)
    code, results = executor.run(options)
    assert code == 2
    assert results["errors"][0]["interpreter"] == str(py)
    assert results["errors"][0]["status"] == "failed"
