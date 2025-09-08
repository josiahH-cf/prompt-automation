from __future__ import annotations

import json
import os
from pathlib import Path
import importlib


def test_find_repo_root_uses_settings_json(tmp_path, monkeypatch):
    # Create a fake repo with the minimal espanso-package manifest
    repo = tmp_path / "myrepo"
    pkg = repo / "espanso-package"
    (pkg / "match").mkdir(parents=True)
    (pkg / "_manifest.yml").write_text(
        "name: prompt-automation\n"
        "title: 'Prompt-Automation Snippets'\n"
        "version: 0.0.9\n"
        "description: 'Test'\n"
        "author: 'Test'\n",
        encoding="utf-8",
    )
    (pkg / "package.yml").write_text("name: prompt-automation\n", encoding="utf-8")
    (pkg / "match" / "basic.yml").write_text("matches: []\n", encoding="utf-8")

    # Prepare a prompts directory with Settings/settings.json containing espanso_repo_root
    prompts = tmp_path / "prompts" / "styles"
    settings_dir = prompts / "Settings"
    settings_dir.mkdir(parents=True)
    (settings_dir / "settings.json").write_text(
        json.dumps({"espanso_repo_root": str(repo)}),
        encoding="utf-8",
    )

    # Point PROMPT_AUTOMATION_PROMPTS at our temp prompts dir before importing
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(prompts))

    # Import fresh copy so config reads env and espanso_sync sees it
    # Reload order: config first, then espanso_sync
    cfg = importlib.import_module("prompt_automation.config")
    importlib.reload(cfg)  # ensure PROMPTS_DIR honors env var

    sync_mod = importlib.import_module("prompt_automation.espanso_sync")
    importlib.reload(sync_mod)

    # When no repo is explicitly provided and env var is absent, it should use settings.json
    root = sync_mod._find_repo_root(None)  # type: ignore[attr-defined]
    assert Path(root) == repo


def test_run_handles_missing_binary_gracefully():
    import prompt_automation.espanso_sync as sync
    code, out, err = sync._run(["definitely-not-a-real-cmd-xyz-12345"])  # type: ignore[attr-defined]
    # Expect a 127-like status and a useful error string, not an exception
    assert code != 0
    assert isinstance(err, str) and err

