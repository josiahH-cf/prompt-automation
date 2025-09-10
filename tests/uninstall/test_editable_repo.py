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

import pytest

from prompt_automation.cli.controller import UninstallOptions
from prompt_automation.uninstall import executor, detectors


def _setup_editable(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()
    egg = site / "prompt_automation.egg-link"
    egg.write_text(str(_repo_root))
    info = site / "prompt_automation.egg-info"
    info.mkdir()
    entry = info / "entry_points.txt"
    entry.write_text("data")
    return site, egg, entry


def test_editable_repo_preserved_and_backed_up(monkeypatch, tmp_path):
    site, egg, entry = _setup_editable(tmp_path)
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [detectors.detect_editable_repo])
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    options = UninstallOptions(force=True)
    code, results = executor.run(options)
    assert code == 0
    assert _repo_root.exists()
    assert not egg.exists()
    assert not entry.exists()
    backups = list((tmp_path / ".config").glob("prompt-automation.repo-backup.*"))
    assert backups
    backup_files = {p.name for p in backups[0].iterdir()}
    assert egg.name in backup_files
    assert entry.name in backup_files
    for item in results["removed"]:
        assert item["backup"] is not None


def test_editable_repo_no_backup_flag(monkeypatch, tmp_path):
    site, egg, entry = _setup_editable(tmp_path)
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.setattr(executor, "_DEF_DETECTORS", [detectors.detect_editable_repo])
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    options = UninstallOptions(force=True, no_backup=True)
    code, results = executor.run(options)
    assert code == 0
    backups = list((tmp_path / ".config").glob("prompt-automation.repo-backup.*"))
    assert not backups
    for item in results["removed"]:
        assert item["backup"] is None
    assert _repo_root.exists()
    assert not egg.exists()
    assert not entry.exists()
