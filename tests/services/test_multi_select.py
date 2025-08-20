import json
from pathlib import Path

import prompt_automation.services.multi_select as ms
import prompt_automation.services.template_search as ts
from prompt_automation.shortcuts import save_shortcuts
from prompt_automation.menus import render_template


def _make_template(base: Path, rel: str, lines: list[str]) -> Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": sum(rel.encode()),
        "title": rel,
        "style": "Test",
        "template": lines,
        "placeholders": [],
    }
    path.write_text(json.dumps(data))
    return path


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("prompt_automation.config.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("prompt_automation.shortcuts.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(
        "prompt_automation.shortcuts.SETTINGS_DIR", tmp_path / "Settings"
    )
    monkeypatch.setattr(
        "prompt_automation.shortcuts.SHORTCUT_FILE",
        tmp_path / "Settings/template-shortcuts.json",
    )
    # ensure multi_select uses patched resolver
    monkeypatch.setattr(ms, "resolve_shortcut", ts.resolve_shortcut)


def test_merge_paths_order_and_dedup(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    t1 = _make_template(tmp_path, "a.json", ["A"])
    t2 = _make_template(tmp_path, "b.json", ["B", "C"])
    merged = ms.merge_paths([t1, t2])
    assert merged["template"] == ["A", "B", "C"]
    # duplicate paths ignored and order preserved
    merged_dup = ms.merge_paths([t2, t1, t2])
    assert merged_dup["template"] == ["B", "C", "A"]


def test_merge_templates_duplicates():
    t1 = {"id": 1, "template": ["X"]}
    t2 = {"id": 2, "template": ["Y"]}
    merged = ms.merge_templates([t1, t1, t2])
    assert merged["template"] == ["X", "Y"]
    assert merged["title"] == "Multi (2)"
    assert merged["style"] == "multi"
    assert merged["id"] == -1


def test_merge_shortcut_keys(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    t1 = _make_template(tmp_path, "alpha.json", ["Alpha"])
    t2 = _make_template(tmp_path, "beta.json", ["Beta"])
    save_shortcuts({
        "1": str(t1.relative_to(tmp_path)),
        "2": str(t2.relative_to(tmp_path)),
    })
    merged = ms.merge_shortcuts(["1", "2", "1"])
    assert merged["template"] == ["Alpha", "Beta"]


def test_merged_render_matches_sequential():
    t1 = {
        "id": 1,
        "title": "A",
        "style": "Test",
        "template": ["Hello {{x}}"],
        "placeholders": [{"name": "x"}],
    }
    t2 = {
        "id": 2,
        "title": "B",
        "style": "Test",
        "template": ["Bye {{y}}"],
        "placeholders": [{"name": "y"}],
    }
    legacy = "\n".join(
        [
            render_template(t1, {"x": "one"}),
            render_template(t2, {"y": "two"}),
        ]
    )
    combined = ms.merge_templates([t1, t2])
    merged = render_template(combined, {"x": "one", "y": "two"})
    assert merged == legacy
