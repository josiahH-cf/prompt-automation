from __future__ import annotations

from pathlib import Path
import sys


def _write_repo_with_templates(root: Path) -> None:
    # minimal manifest + package
    (root / 'espanso-package' / 'match').mkdir(parents=True, exist_ok=True)
    (root / 'espanso-package' / 'templates').mkdir(parents=True, exist_ok=True)
    (root / 'espanso-package' / '_manifest.yml').write_text(
        """name: prompt-automation
title: 'Prompt-Automation Snippets'
version: 0.9.1
description: 'Test'
author: 'Test'
""",
        encoding='utf-8',
    )
    (root / 'espanso-package' / 'package.yml').write_text("name: prompt-automation\ndependencies: []\n", encoding='utf-8')

    # Template with multi-line replace
    (root / 'espanso-package' / 'templates' / 'gen.yml').write_text(
        """matches:
  - trigger: ':t.gen'
    replace: "Line1\\nLine2"
""",
        encoding='utf-8',
    )
    # Duplicate trigger across templates should be deduplicated in generation across generated set
    (root / 'espanso-package' / 'templates' / 'gen2.yml').write_text(
        """matches:
  - trigger: ':t.gen'
    replace: 'Second'
  - trigger: ':t.ok'
    replace: 'OK'
""",
        encoding='utf-8',
    )


def test_generation_writes_match_files_with_block_scalars_and_mirror(tmp_path: Path) -> None:
    _write_repo_with_templates(tmp_path)
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / 'src'
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    # Run orchestrator in dry-run (should still generate + mirror)
    from prompt_automation.espanso_sync import main as sync_main
    sync_main(["--repo", str(tmp_path), "--dry-run"])  # should not raise

    # Generated files present
    gen = (tmp_path / 'espanso-package' / 'match' / 'gen.yml').read_text(encoding='utf-8')
    # Expect block scalar for multi-line string (allow chomp modifier)
    assert ('|\n' in gen or '|-\n' in gen) and 'Line1' in gen and 'Line2' in gen
    # Dedup across generated set: only one ':t.gen' entry should survive
    import yaml
    data = yaml.safe_load((tmp_path / 'espanso-package' / 'match' / 'gen2.yml').read_text())
    triggers = [m.get('trigger') for m in data.get('matches', [])]
    assert ':t.gen' not in triggers  # duplicate removed in second file
    assert ':t.ok' in triggers

    # Mirrored external layout exists and matches version and triggers (auto-bumped)
    ext = tmp_path / 'packages' / 'prompt-automation' / '0.9.2'
    assert (ext / '_manifest.yml').exists()
    # Basic parity: triggers present in external mirror
    e2 = yaml.safe_load((ext / 'match' / 'gen2.yml').read_text())
    ext_triggers = [m.get('trigger') for m in e2.get('matches', [])]
    assert set(ext_triggers) == set(triggers)
