from __future__ import annotations

from pathlib import Path


def test_espanso_script_has_sync_alias():
    repo = Path(__file__).resolve().parents[2]
    path = repo / 'scripts' / 'espanso.sh'
    text = path.read_text(encoding='utf-8')
    assert '\n  sync)' in text or '\nsync)' in text, 'sync alias missing in scripts/espanso.sh'
    # Ensure it invokes the orchestrator via CLI or python -m fallback
    assert '--espanso-sync' in text or 'prompt_automation.espanso_sync' in text

