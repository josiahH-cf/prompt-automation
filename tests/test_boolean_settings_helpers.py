import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prompt_automation.variables import storage


def _prepare_settings(monkeypatch, tmp_path):
    settings_dir = tmp_path / "prompts" / "styles" / "Settings"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "settings.json"
    monkeypatch.setattr(storage, "_SETTINGS_DIR", settings_dir, raising=False)
    monkeypatch.setattr(storage, "_SETTINGS_FILE", settings_file, raising=False)
    return settings_file


def test_background_hotkey_setting_round_trip(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)

    # Default should be True when unset
    assert storage.get_background_hotkey_enabled() is True

    storage.set_background_hotkey_enabled(False)
    assert storage.get_background_hotkey_enabled() is False


def test_espanso_enabled_round_trip(monkeypatch, tmp_path):
    _prepare_settings(monkeypatch, tmp_path)

    assert storage.get_espanso_enabled() is True

    storage.set_espanso_enabled(False)
    assert storage.get_espanso_enabled() is False

