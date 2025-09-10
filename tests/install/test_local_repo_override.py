import os
import json
import subprocess
from pathlib import Path


def _seed_defaults(home: Path):
    cfg = home / '.prompt-automation'
    cfg.mkdir(parents=True, exist_ok=True)
    hotkey = cfg / 'hotkey.json'
    if not hotkey.exists():
        hotkey.write_text('{"hotkey": "ctrl+shift+j"}')
    env = cfg / 'environment'
    if not env.exists():
        env.write_text('PROMPT_AUTOMATION_GUI=1\nPROMPT_AUTOMATION_AUTO_UPDATE=1\nPROMPT_AUTOMATION_MANIFEST_AUTO=1\n')


def _make_repo(path: Path, msg: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / 'pa_main.py').write_text(f"print('{msg}')\n")
    return path


def _install_repo(repo: Path, bin_dir: Path):
    bin_dir.mkdir(parents=True, exist_ok=True)
    src = repo / 'pa_main.py'
    dest = bin_dir / 'prompt-automation'
    dest.write_text(f"#!/usr/bin/env python3\n{src.read_text()}")
    dest.chmod(0o755)


def test_reinstall_preserves_user_config(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    monkeypatch.setattr(Path, 'home', lambda: home)

    bin_dir = tmp_path / 'bin'
    monkeypatch.setenv('PATH', str(bin_dir) + os.pathsep + os.environ['PATH'])

    repo1 = _make_repo(tmp_path / 'repo1', 'v1')
    _seed_defaults(home)
    _install_repo(repo1, bin_dir)
    out1 = subprocess.check_output(['prompt-automation'], text=True).strip()
    assert out1 == 'v1'

    hotkey_file = home / '.prompt-automation' / 'hotkey.json'
    env_file = home / '.prompt-automation' / 'environment'
    hotkey_file.write_text('{"hotkey": "custom"}')
    env_file.write_text('CUSTOM_ENV=1\n')

    repo2 = _make_repo(tmp_path / 'repo2', 'v2')
    _seed_defaults(home)
    _install_repo(repo2, bin_dir)
    out2 = subprocess.check_output(['prompt-automation'], text=True).strip()
    assert out2 == 'v2'

    cfg = json.loads(hotkey_file.read_text())
    assert cfg['hotkey'] == 'custom'
    assert 'CUSTOM_ENV=1' in env_file.read_text()
