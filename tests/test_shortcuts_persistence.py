import json
import os
from pathlib import Path

import prompt_automation.shortcuts as sc


def test_template_shortcuts_local_layer_overrides_repo(monkeypatch, tmp_path):
    """Local machine shortcuts should take precedence over repo defaults.

    Current behavior: only reads repo-level `prompts/styles/Settings/template-shortcuts.json`.
    Expected: if a machine-local shortcuts file exists under HOME (~/.prompt-automation),
    it overrides the repo file and survives repo changes.
    """
    # Simulate prompts tree with repo-level shortcuts
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    repo_file = settings_dir / 'template-shortcuts.json'
    repo_file.write_text(json.dumps({'1': 'Code/02_new_feature.json'}))

    # Point PROMPTS_DIR at our temp repo
    monkeypatch.setattr(sc, 'SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(sc, 'SHORTCUT_FILE', repo_file, raising=False)

    # Create a machine-local HOME dir and a local shortcuts file with a different mapping
    home_dir = tmp_path / '.prompt-automation'
    home_dir.mkdir(parents=True)
    local_file = home_dir / 'template-shortcuts.json'
    local_file.write_text(json.dumps({'1': 'Code/03_bug_fix.json', '2': 'Tool/46_create-or-modify-project-structure.json'}))

    # Ensure the library picks up the HOME override path
    from prompt_automation import config as cfg
    monkeypatch.setenv(cfg.ENV_HOME, str(home_dir))
    # Force re-evaluation of HOME_DIR inside shortcuts via config
    import importlib; importlib.reload(cfg)
    importlib.reload(sc)

    # Under desired behavior, local overrides win. Today this will FAIL (red),
    # because sc.load_shortcuts() ignores the local layer and only returns repo mapping.
    mapping = sc.load_shortcuts()
    assert mapping.get('1') == 'Code/03_bug_fix.json'
    assert mapping.get('2') == 'Tool/46_create-or-modify-project-structure.json'

