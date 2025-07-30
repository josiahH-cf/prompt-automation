from pathlib import Path

def test_install_script_contains_hotkey():
    data = Path('scripts/install.sh').read_text()
    assert 'espanso restart' in data
    ps = Path('scripts/install.ps1').read_text()
    assert 'AutoHotkey' in ps

