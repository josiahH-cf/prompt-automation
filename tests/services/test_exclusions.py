import json
from pathlib import Path

import prompt_automation.services.exclusions as ex


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setattr(ex, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("prompt_automation.config.PROMPTS_DIR", tmp_path)


def _make_template(base: Path, tid: int, exclusions=None) -> Path:
    data = {
        "id": tid,
        "title": "T",
        "style": "S",
        "role": "assistant",
        "template": ["hi"],
        "placeholders": [],
        "metadata": {},
    }
    if exclusions is not None:
        data["metadata"]["exclude_globals"] = exclusions
    path = base / f"{tid}.json"
    path.write_text(json.dumps(data))
    return path


def test_modify_exclusions(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _make_template(tmp_path, 1, ["foo"])

    assert ex.load_exclusions(1) == ["foo"]

    assert ex.add_exclusion(1, "bar") is True
    assert set(ex.load_exclusions(1)) == {"foo", "bar"}

    assert ex.remove_exclusion(1, "foo") is True
    assert ex.load_exclusions(1) == ["bar"]

    assert ex.reset_exclusions(1) is True
    assert ex.load_exclusions(1) == []

