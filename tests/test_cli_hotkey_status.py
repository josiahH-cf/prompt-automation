import sys
from pathlib import Path


def test_hotkey_status_linux(monkeypatch, capsys, tmp_path):
    # Make platform Linux and HOME to tmp
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    # Seed an espanso yaml so status reports OK
    yml = tmp_path / '.config' / 'espanso' / 'match' / 'prompt-automation.yml'
    yml.parent.mkdir(parents=True, exist_ok=True)
    yml.write_text('matches: []')
    # Ensure hotkey manager returns a value
    import prompt_automation.hotkeys.base as base
    monkeypatch.setattr(base.HotkeyManager, 'get_current_hotkey', staticmethod(lambda: 'ctrl+shift+j'))

    # Invoke CLI
    import prompt_automation.cli as cli
    cli.PromptCLI().main(['--hotkey-status'])
    out = capsys.readouterr().out
    assert 'Current hotkey' in out and 'Espanso YAML: OK' in out

