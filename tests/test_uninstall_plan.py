import sys
from pathlib import Path
import os


def _find_repo_root(start: Path) -> Path:
    for d in [start] + list(start.parents):
        if (d / "pyproject.toml").exists():
            return d
    return start.parent


_repo_root = _find_repo_root(Path(__file__).resolve())
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from prompt_automation.uninstall import detectors, executor
from prompt_automation.uninstall.artifacts import Artifact
from prompt_automation.cli.controller import UninstallOptions


def test_artifact_detection_and_platforms(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    (tmp_path / ".config/prompt-automation").mkdir(parents=True)
    (tmp_path / ".cache/prompt-automation").mkdir(parents=True)
    (tmp_path / ".config/prompt-automation/logs").mkdir(parents=True)
    (tmp_path / ".local/state/prompt-automation").mkdir(parents=True)
    data_arts = detectors.detect_data_dirs(platform="linux")
    assert {a.id for a in data_arts} == {"config-dir", "cache-dir", "state-dir", "log-dir"}
    assert all(a.purge_candidate for a in data_arts)

    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    (scripts / "prompt-automation.exe").touch()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    win_arts = detectors.detect_symlink_wrappers(platform="win32")
    assert win_arts and win_arts[0].id == "windows-wrapper"

    (tmp_path / ".config/systemd/user").mkdir(parents=True)
    (tmp_path / ".config/systemd/user/prompt-automation.service").touch()
    system_unit = Path("/etc/systemd/system/prompt-automation.service")
    system_unit.parent.mkdir(parents=True, exist_ok=True)
    system_unit.touch()
    try:
        sysd_arts = detectors.detect_systemd_units(platform="linux")
        assert {a.id for a in sysd_arts} == {"systemd-user", "systemd-system"}
    finally:
        try:
            system_unit.unlink()
        except FileNotFoundError:
            pass


def test_action_ordering(tmp_path, monkeypatch):
    a_path = tmp_path / "a.txt"
    b_path = tmp_path / "b.txt"
    a_path.write_text("a")
    b_path.write_text("b")
    art_a = Artifact("a", "file", a_path)
    art_b = Artifact("b", "file", b_path)

    def det_a(_platform):
        return [art_a]

    def det_b(_platform):
        return [art_b]

    monkeypatch.setattr(executor, "_DEF_DETECTORS", [det_a, det_b])
    opts = UninstallOptions(force=True)
    code, results = executor.run(opts)
    assert code == 0
    assert [r["id"] for r in results["removed"]] == ["a", "b"]
    assert not a_path.exists() and not b_path.exists()
