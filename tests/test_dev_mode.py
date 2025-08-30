import types
from pathlib import Path


def test_is_dev_mode_by_env(monkeypatch):
    import prompt_automation.dev as dev
    monkeypatch.setenv('PROMPT_AUTOMATION_DEV', '1')
    assert dev.is_dev_mode() is True


def test_cli_skips_updates_in_dev(monkeypatch, tmp_path):
    # Route logs to tmp home and mark dev mode
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    monkeypatch.setenv('PROMPT_AUTOMATION_DEV', '1')

    # Track calls
    called = {'pip_updater': False, 'manifest_update': False}

    import prompt_automation.cli.__init__ as cli_mod

    def _check_for_update():
        called['pip_updater'] = True

    def _manifest_update():
        called['manifest_update'] = True

    monkeypatch.setattr(cli_mod.updater, 'check_for_update', _check_for_update)
    monkeypatch.setattr(cli_mod.manifest_update, 'check_and_prompt', _manifest_update)

    # Stub singleton fast-focus to succeed
    import prompt_automation.gui.single_window.singleton as singleton_mod
    monkeypatch.setattr(singleton_mod, 'connect_and_focus_if_running', lambda: True)

    cli = cli_mod.PromptCLI()
    cli.main(['--focus'])

    assert called['pip_updater'] is False
    assert called['manifest_update'] is False


def test_windows_ahk_includes_py_launcher(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.windows as win
    monkeypatch.setenv('APPDATA', str(tmp_path))
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: None)

    win._update_windows('ctrl+shift+j')
    startup = Path(tmp_path) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
    script = startup / 'prompt-automation.ahk'
    text = script.read_text()
    assert 'py -m prompt_automation --focus' in text
    assert 'py -m prompt_automation --gui' in text
    assert 'py -m prompt_automation --terminal' in text

