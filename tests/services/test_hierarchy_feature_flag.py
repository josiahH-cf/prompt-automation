import json
import importlib
from pathlib import Path

import os


def test_hierarchy_default_true_without_env_or_settings(tmp_path, monkeypatch):
    # Prepare a temp prompts dir with no settings
    root = tmp_path / "styles"
    (root / "Code").mkdir(parents=True)
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    # Reload config and features to pick up the new root
    from prompt_automation import config as cfg
    importlib.reload(cfg)
    from prompt_automation import features as feat
    importlib.reload(feat)

    assert feat.is_hierarchy_enabled() is True


def test_hierarchy_env_overrides(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    root.mkdir(parents=True)
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    from prompt_automation import config as cfg
    importlib.reload(cfg)
    from prompt_automation import features as feat
    importlib.reload(feat)

    monkeypatch.setenv("PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES", "0")
    importlib.reload(feat)
    assert feat.is_hierarchy_enabled() is False

    monkeypatch.setenv("PROMPT_AUTOMATION_HIERARCHICAL_TEMPLATES", "1")
    importlib.reload(feat)
    assert feat.is_hierarchy_enabled() is True


def test_hierarchy_settings_toggle_persistence(tmp_path, monkeypatch):
    root = tmp_path / "styles"
    (root / "Settings").mkdir(parents=True)
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))

    from prompt_automation import config as cfg
    importlib.reload(cfg)
    from prompt_automation import features as feat
    importlib.reload(feat)

    # Persist off
    feat.set_user_hierarchy_preference(False)
    importlib.reload(feat)
    assert feat.is_hierarchy_enabled() is False

    # Persist on
    feat.set_user_hierarchy_preference(True)
    importlib.reload(feat)
    assert feat.is_hierarchy_enabled() is True

