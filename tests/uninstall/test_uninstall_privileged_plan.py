import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for d in [start] + list(start.parents):
        if (d / "pyproject.toml").exists():
            return d
    return start.parent


_repo_root = _find_repo_root(Path(__file__).resolve())
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from prompt_automation.uninstall import executor
from prompt_automation.uninstall.artifacts import Artifact
from prompt_automation.cli.controller import UninstallOptions


def _make_priv_art(tmp_path: Path) -> Artifact:
    path = tmp_path / "sysfile.txt"
    path.write_text("data")
    return Artifact("sysfile", "file", path, requires_privilege=True)


def test_print_script_posix(monkeypatch, tmp_path, capsys):
    art = _make_priv_art(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])
    monkeypatch.setattr(executor.os, "geteuid", lambda: 1000)
    opts = UninstallOptions(force=True, print_elevated_script=True)
    code, results = executor.run(opts)
    out = capsys.readouterr().out
    assert code == 2
    assert results["pending"] == [str(art.path)]
    assert f"rm -rf '{art.path}'" in out


def test_print_script_windows(monkeypatch, tmp_path, capsys):
    art = _make_priv_art(tmp_path)
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [lambda _platform: [art]])
    monkeypatch.setattr(executor.os, "geteuid", lambda: 1000)
    opts = UninstallOptions(force=True, print_elevated_script=True, platform="win32")
    code, results = executor.run(opts)
    out = capsys.readouterr().out
    assert code == 2
    assert results["pending"] == [str(art.path)]
    assert f'Remove-Item -Recurse -Force "{art.path}"' in out
