from __future__ import annotations

from pathlib import Path


def test_options_menu_contains_sync_label():
    repo_root = Path(__file__).resolve().parents[2]
    text = (repo_root / 'src' / 'prompt_automation' / 'gui' / 'options_menu.py').read_text(encoding='utf-8')
    assert 'Sync Espanso?' in text

