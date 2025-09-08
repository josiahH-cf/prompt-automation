from __future__ import annotations

from pathlib import Path
from typing import List


def test_clean_env_lists_and_removes(tmp_path, monkeypatch):
    # Create fake local match dir with base.yml and other.yml
    match_dir = tmp_path / '.config' / 'espanso' / 'match'
    match_dir.mkdir(parents=True)
    (match_dir / 'base.yml').write_text('matches: []\n')
    (match_dir / 'other.yml').write_text('matches: []\n')

    # Simulate this path as user's home
    monkeypatch.setenv('HOME', str(tmp_path))

    # Mock espanso binaries
    import prompt_automation.cli.espanso_cmds as cmd
    monkeypatch.setattr(cmd, '_espanso_bin', lambda: None)

    # list_only mode prints files (not asserted here, just ensure no error)
    cmd.clean_env(list_only=True)

    # default (non-deep) should remove only base.yml and create backup dir
    cmd.clean_env(deep=False, list_only=False)
    assert not (match_dir / 'base.yml').exists()
    assert (match_dir / 'other.yml').exists()
    # deep should remove all and create a backup
    cmd.clean_env(deep=True, list_only=False)
    assert not (match_dir / 'other.yml').exists()

