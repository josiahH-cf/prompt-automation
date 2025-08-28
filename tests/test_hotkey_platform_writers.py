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


def test_macos_writer_generates_applescript(monkeypatch, tmp_path):
    import prompt_automation.hotkeys.macos as mac
    # monkeypatch Path.home
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    mac._update_macos('ctrl+shift+j')
    script = tmp_path / 'Library' / 'Application Scripts' / 'prompt-automation' / 'macos.applescript'
    assert script.exists()
    content = script.read_text()
    assert 'prompt-automation --focus' in content

