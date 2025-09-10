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

from prompt_automation.uninstall import detectors


def test_linux_data_dir_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".config/prompt-automation").mkdir(parents=True)
    (tmp_path / ".cache/prompt-automation").mkdir(parents=True)
    (tmp_path / ".local/state/prompt-automation").mkdir(parents=True)
    (tmp_path / ".config/prompt-automation/logs").mkdir(parents=True)
    arts = detectors.detect_data_dirs(platform="linux")
    assert {a.id for a in arts} == {"config-dir", "cache-dir", "state-dir", "log-dir"}


def test_darwin_data_dir_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    base = tmp_path / "Library"
    (base / "Application Support/prompt-automation").mkdir(parents=True)
    (base / "Caches/prompt-automation").mkdir(parents=True)
    (base / "Application Support/prompt-automation/state").mkdir(parents=True)
    (base / "Logs/prompt-automation").mkdir(parents=True)
    arts = detectors.detect_data_dirs(platform="darwin")
    assert {a.id for a in arts} == {"config-dir", "cache-dir", "state-dir", "log-dir"}


def test_windows_data_dir_detection(monkeypatch, tmp_path):
    home = tmp_path
    monkeypatch.setattr(Path, "home", lambda: home)
    appdata = home / "AppData" / "Roaming"
    local = home / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    (appdata / "prompt-automation").mkdir(parents=True)
    (local / "prompt-automation/cache").mkdir(parents=True)
    (local / "prompt-automation/state").mkdir(parents=True)
    (local / "prompt-automation/logs").mkdir(parents=True)
    arts = detectors.detect_data_dirs(platform="win32")
    assert {a.id for a in arts} == {"config-dir", "cache-dir", "state-dir", "log-dir"}
