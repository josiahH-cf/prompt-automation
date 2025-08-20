import json
from pathlib import Path

import prompt_automation.services.overrides as ov
import prompt_automation.variables.storage as storage
import prompt_automation.variables.values as values



def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_PERSIST_DIR", tmp_path)
    monkeypatch.setattr(storage, "_PERSIST_FILE", tmp_path / "placeholder-overrides.json")
    monkeypatch.setattr(storage, "_SETTINGS_DIR", tmp_path / "Settings")
    monkeypatch.setattr(storage, "_SETTINGS_FILE", tmp_path / "Settings/settings.json")
    # values module holds its own references to these paths
    monkeypatch.setattr(values, "_PERSIST_FILE", storage._PERSIST_FILE)
    monkeypatch.setattr(values, "_SETTINGS_FILE", storage._SETTINGS_FILE)


def test_load_invalid_file(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    storage._PERSIST_FILE.write_text("{invalid json")
    data = ov.load_overrides()
    # Should fall back to empty base structure
    assert data["templates"] == {}
    assert data["template_values"] == {}


def test_update_and_reset_overrides(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    # update placeholder override
    ov.update_placeholder_override(1, "file", path="foo.txt", skip=True)
    data = ov.load_overrides()
    assert data["templates"]["1"]["file"] == {"path": "foo.txt", "skip": True}

    # update template value override
    ov.update_template_value_override(1, "name", "Alice")
    data = ov.load_overrides()
    assert data["template_values"]["1"]["name"] == "Alice"
    # reset template value override
    assert ov.reset_template_value_override_value(1, "name") is True
    data = ov.load_overrides()
    assert data.get("template_values", {}).get("1") is None

    # check bulk reset of value overrides
    ov.update_template_value_override(1, "n1", "v1")
    ov.update_template_value_override(1, "n2", "v2")
    assert ov.reset_all_template_value_overrides_for_template(1) is True
    data = ov.load_overrides()
    assert "1" not in data.get("template_values", {})

    # finally reset placeholder override
    assert ov.reset_placeholder_override(1, "file") is True
    data = ov.load_overrides()
    assert "file" not in data.get("templates", {}).get("1", {})
