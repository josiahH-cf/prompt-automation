import json
import types
from pathlib import Path

import prompt_automation.hotkeys.base as base


def test_update_hotkeys_creates_default_and_calls_platform(monkeypatch, tmp_path):
    # Ensure hotkey file is absent and points to tmp
    monkeypatch.setattr(base, 'CONFIG_DIR', tmp_path, raising=False)
    hotkey_file = tmp_path / 'hotkey.json'
    monkeypatch.setattr(base, 'HOTKEY_FILE', hotkey_file, raising=False)

    called = {'hotkey': None}
    monkeypatch.setattr(base.HotkeyManager, 'update_system_hotkey', classmethod(lambda cls, hk: called.__setitem__('hotkey', hk)))

    base.HotkeyManager.update_hotkeys()

    # default hotkey applied and persisted
    assert called['hotkey'] == 'ctrl+shift+j'
    assert hotkey_file.exists()
    data = json.loads(hotkey_file.read_text())
    assert data.get('hotkey') == 'ctrl+shift+j'


def test_assign_hotkey_persists_and_sets_env(monkeypatch, tmp_path):
    # Simulate user input path by monkeypatching capture_hotkey
    monkeypatch.setattr(base.HotkeyManager, 'capture_hotkey', staticmethod(lambda: 'alt+shift+p'))
    monkeypatch.setattr(base, 'CONFIG_DIR', tmp_path, raising=False)
    monkeypatch.setattr(base, 'HOTKEY_FILE', tmp_path / 'hotkey.json', raising=False)
    # Stub platform-specific updater
    monkeypatch.setattr(base.HotkeyManager, 'update_system_hotkey', staticmethod(lambda hk: None))

    base.HotkeyManager.assign_hotkey()

    # Files written
    cfg = json.loads((tmp_path / 'hotkey.json').read_text())
    assert cfg.get('hotkey') == 'alt+shift+p'
    env_file = tmp_path / 'environment'
    assert env_file.exists()
    assert 'PROMPT_AUTOMATION_GUI=1' in env_file.read_text()

