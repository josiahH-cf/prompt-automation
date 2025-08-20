import json
from pathlib import Path

import prompt_automation.services.template_search as ts
from prompt_automation.shortcuts import save_shortcuts


def _make_template(base: Path, rel: str, title: str = "T") -> Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": 1,
        "title": title,
        "style": "Test",
        "role": "assistant",
        "template": ["hello"],
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


def test_search_and_recursion(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _make_template(tmp_path, "alpha.json", title="Alpha")
    _make_template(tmp_path / "sub", "beta.json", title="Beta")
    _make_template(tmp_path / "sub", "alphabeta.json", title="AlphaBeta")

    all_paths = {p.relative_to(tmp_path) for p in ts.list_templates()}
    assert all_paths == {
        Path("alpha.json"),
        Path("sub/beta.json"),
        Path("sub/alphabeta.json"),
    }

    non_recursive = {p.relative_to(tmp_path) for p in ts.list_templates(recursive=False)}
    assert non_recursive == {Path("alpha.json")}

    search_paths = {p.relative_to(tmp_path) for p in ts.list_templates("alpha")}
    assert search_paths == {Path("alpha.json"), Path("sub/alphabeta.json")}


def test_resolve_shortcut(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    tpl = _make_template(tmp_path, "alpha.json", title="Alpha")
    save_shortcuts({"1": str(tpl.relative_to(tmp_path))})

    data = ts.resolve_shortcut("1")
    assert data and data["title"] == "Alpha"

    assert ts.resolve_shortcut("9") is None

