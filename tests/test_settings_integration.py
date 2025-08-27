import json
from pathlib import Path
from prompt_automation.variables import storage
from prompt_automation.hotkeys.base import HotkeyManager


def test_settings_global_reference_file_merges(monkeypatch, tmp_path):
    # Patch settings + overrides paths
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    overrides_file = tmp_path / 'placeholder-overrides.json'
    monkeypatch.setattr(storage, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(storage, '_SETTINGS_FILE', settings_file, raising=False)
    monkeypatch.setattr(storage, '_PERSIST_FILE', overrides_file, raising=False)

    # Write settings with global_files.reference_file
    ref = tmp_path / 'ref.txt'
    ref.write_text('hello')
    settings_file.write_text(json.dumps({'global_files': {'reference_file': str(ref)}}))

    from prompt_automation.variables.files import get_global_reference_file
    # Should pick up from settings even though overrides file absent
    assert get_global_reference_file() == str(ref)


def test_settings_hotkey_default(monkeypatch, tmp_path):
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    settings_file.write_text(json.dumps({'hotkey': 'alt+shift+p'}))

    from prompt_automation.variables import storage as st
    monkeypatch.setattr(st, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(st, '_SETTINGS_FILE', settings_file, raising=False)

    # Ensure no local hotkey file exists
    monkeypatch.setattr('prompt_automation.hotkeys.base.HOTKEY_FILE', tmp_path / 'hotkey.json', raising=False)

    hk = HotkeyManager.get_current_hotkey()
    assert hk == 'alt+shift+p'
