import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from prompt_automation.gui.single_window.frames import select


def _stub_tk():
    """Install a minimal tkinter stub returning previous module."""
    real_tk = sys.modules.get("tkinter")
    stub = types.ModuleType("tkinter")
    sys.modules["tkinter"] = stub
    return real_tk


def _restore_tk(real_tk):
    if real_tk is not None:
        sys.modules["tkinter"] = real_tk
    else:
        sys.modules.pop("tkinter", None)


def test_search_filtering_and_recursive_toggle(monkeypatch):
    real_tk = _stub_tk()

    calls = []
    paths_map = {
        ("", True): [Path("a.json"), Path("b.json")],
        ("foo", True): [Path("foo.json")],
        ("bar", False): [Path("bar.json")],
    }

    def fake_list(search="", recursive=True):
        calls.append((search, recursive))
        return paths_map.get((search, recursive), [])

    monkeypatch.setattr(select, "list_templates", fake_list)
    app = types.SimpleNamespace(root=object(), advance_to_collect=lambda data: None)

    view = select.build(app)
    assert view.state["paths"] == [Path("a.json"), Path("b.json")]
    view.search("foo")
    assert calls[-1] == ("foo", True)
    assert view.state["paths"] == [Path("foo.json")]
    view.toggle_recursive()
    view.search("bar")
    assert calls[-1] == ("bar", False)
    assert view.state["paths"] == [Path("bar.json")]

    _restore_tk(real_tk)


def test_shortcut_resolution(monkeypatch):
    real_tk = _stub_tk()

    monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: [])

    captured = []

    def fake_resolve(key):
        captured.append(key)
        return {"id": 1}

    monkeypatch.setattr(select, "resolve_shortcut", fake_resolve)
    received = []
    app = types.SimpleNamespace(root=object(), advance_to_collect=lambda data: received.append(data))

    view = select.build(app)
    view.activate_shortcut("x")
    assert captured == ["x"]
    assert received == [{"id": 1}]

    _restore_tk(real_tk)


def test_multi_select_combination(monkeypatch):
    real_tk = _stub_tk()

    paths = [Path("a.json"), Path("b.json")]
    monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: paths)
    monkeypatch.setattr(select, "load_template", lambda p: {"template": [p.stem]})

    def fake_merge(templates):
        combined = []
        for tmpl in templates:
            combined.extend(tmpl.get("template", []))
        return {"template": combined}

    monkeypatch.setattr(select, "merge_templates", fake_merge)
    received = []
    app = types.SimpleNamespace(root=object(), advance_to_collect=lambda data: received.append(data))

    view = select.build(app)
    view.select([0, 1])
    combined = view.combine()
    assert combined["template"] == ["a", "b"]
    assert received[-1]["template"] == ["a", "b"]

    _restore_tk(real_tk)


def test_preview_updates(monkeypatch):
    real_tk = _stub_tk()

    paths = [Path("a.json"), Path("b.json")]
    monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: paths)

    def fake_load(path):
        return {"template": [path.stem.upper()]}

    monkeypatch.setattr(select, "load_template", fake_load)

    app = types.SimpleNamespace(root=object(), advance_to_collect=lambda data: None)
    view = select.build(app)

    view.select([0])
    assert view.state["preview"] == "A"

    view.select([1])
    assert view.state["preview"] == "B"

    _restore_tk(real_tk)


def test_preview_error_handling(monkeypatch):
    real_tk = _stub_tk()

    paths = [Path("bad.json")]
    monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: paths)

    def bad_load(path):
        raise ValueError("boom")

    monkeypatch.setattr(select, "load_template", bad_load)

    app = types.SimpleNamespace(root=object(), advance_to_collect=lambda data: None)
    view = select.build(app)

    view.select([0])
    assert "boom" in view.state["preview"]

    _restore_tk(real_tk)

