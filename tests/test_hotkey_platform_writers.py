from pathlib import Path
import types


def test_linux_writer_generates_espanso_yaml(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.linux as lnx
    # Make home point to tmp so writer uses this path
    monkeypatch.setattr(lnx, 'Path', type('P', (Path,), {}))
    # monkeypatch Path.home to return tmp_path
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    # Stub subprocess.run so no real command is executed
    import subprocess
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: types.SimpleNamespace(returncode=0))

    lnx._update_linux('ctrl+shift+j')
    yaml_path = tmp_path / '.config' / 'espanso' / 'match' / 'prompt-automation.yml'
    assert yaml_path.exists()
    content = yaml_path.read_text()
    assert '<ctrl>+<shift>+j' in content
    assert 'prompt-automation --focus' in content


def test_windows_writer_generates_ahk(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.windows as win
    # Point APPDATA to tmp
    monkeypatch.setenv('APPDATA', str(tmp_path))
    # Stub popen
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: None)

    win._update_windows('ctrl+shift+j')
    startup = Path(tmp_path) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
    script = startup / 'prompt-automation.ahk'
    assert script.exists()
    text = script.read_text()
    assert '^+j' in text  # AHK mapping for ctrl+shift+j
    assert 'prompt-automation --focus' in text


def test_windows_writer_no_shell_chain_operators(monkeypatch, tmp_path):
    """Reproduction: current Windows writer incorrectly embeds shell '||' operators which AHK does not interpret.

    This causes the hotkey script to attempt to run an invalid command literal
    (e.g. "prompt-automation --focus || prompt-automation --gui") instead of
    falling back to the second command, preventing the app from launching when
    pressing Ctrl+Shift+J.
    """
    import prompt_automation.hotkeys.windows as win
    monkeypatch.setenv('APPDATA', str(tmp_path))
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: None)

    win._update_windows('ctrl+shift+j')
    startup = Path(tmp_path) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
    script = startup / 'prompt-automation.ahk'
    text = script.read_text()
    # Failing assertion (pre-fix): script currently contains '||'
    assert '||' not in text, 'AHK script should not contain shell chaining operators; they break fallback logic'


def test_macos_writer_generates_applescript(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.macos as mac
    # monkeypatch Path.home
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    mac._update_macos('ctrl+shift+j')
    script = tmp_path / 'Library' / 'Application Scripts' / 'prompt-automation' / 'macos.applescript'
    assert script.exists()
    content = script.read_text()
    assert 'prompt-automation --focus' in content


def test_windows_writer_normalizes_modifier_order():
    import prompt_automation.hotkeys.windows as win
    a = win._to_ahk('ctrl+shift+j')
    b = win._to_ahk('shift+ctrl+j')
    assert a == b == '^+j'


def test_windows_writer_rebind_overwrites(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.windows as win
    monkeypatch.setenv('APPDATA', str(tmp_path))
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: None)

    win._update_windows('ctrl+shift+j')
    startup = Path(tmp_path) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
    script = startup / 'prompt-automation.ahk'
    text1 = script.read_text()
    assert '^+j' in text1

    win._update_windows('ctrl+shift+k')
    text2 = script.read_text()
    assert '^+k' in text2
    assert '^+j' not in text2
    assert '||' not in text2


def test_cli_focus_emits_handler_logs(monkeypatch, tmp_path):
    # Route logs to tmp home
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    monkeypatch.setenv('PROMPT_AUTOMATION_DEBUG', '1')
    # Ensure a fresh logger configuration for file output
    import logging
    log = logging.getLogger('prompt_automation.cli')
    for h in list(log.handlers):
        log.removeHandler(h)

    # Avoid dependency checks and update calls
    import prompt_automation.cli.__init__ as cli_mod
    cli_mod.check_dependencies = lambda require_fzf=True: True  # type: ignore
    cli_mod.updater.check_for_update = lambda: None  # type: ignore
    cli_mod.manifest_update.check_and_prompt = lambda: None  # type: ignore
    cli_mod.ensure_unique_ids = lambda _: None  # type: ignore

    # Stub singleton fast-focus to succeed
    import prompt_automation.gui.single_window.singleton as singleton_mod
    # Use monkeypatch to avoid leaking this stub across tests
    monkeypatch.setattr(
        singleton_mod,
        'connect_and_focus_if_running',
        lambda: True,  # type: ignore
    )

    # Invoke CLI with --focus which should attempt focus and return
    cli = cli_mod.PromptCLI()
    cli.main(['--focus'])

    log_file = tmp_path / '.prompt-automation' / 'logs' / 'cli.log'
    assert log_file.exists()
    logs = log_file.read_text()
    assert 'hotkey_event_received' in logs
    assert 'hotkey_handler_invoked action=focus_app' in logs
