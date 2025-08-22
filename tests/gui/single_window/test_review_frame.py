import sys
import types
from pathlib import Path
import importlib
import pytest

# add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


@pytest.fixture()
def review_module(monkeypatch):
    """Provide the review module with a minimal tkinter stub."""
    real_tk = sys.modules.get("tkinter")
    stub = types.ModuleType("tkinter")
    stub.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: True)
    monkeypatch.setitem(sys.modules, "tkinter", stub)

    base = Path(__file__).resolve().parents[3] / "src/prompt_automation"
    pkg_gui = types.ModuleType("prompt_automation.gui")
    pkg_gui.__path__ = [str(base / "gui")]
    monkeypatch.setitem(sys.modules, "prompt_automation.gui", pkg_gui)
    pkg_sw = types.ModuleType("prompt_automation.gui.single_window")
    pkg_sw.__path__ = [str(base / "gui" / "single_window")]
    monkeypatch.setitem(sys.modules, "prompt_automation.gui.single_window", pkg_sw)
    pkg_frames = types.ModuleType("prompt_automation.gui.single_window.frames")
    pkg_frames.__path__ = [str(base / "gui" / "single_window" / "frames")]
    monkeypatch.setitem(sys.modules, "prompt_automation.gui.single_window.frames", pkg_frames)

    module_path = base / "gui" / "single_window" / "frames" / "review.py"
    spec = importlib.util.spec_from_file_location(
        "prompt_automation.gui.single_window.frames.review", module_path
    )
    review = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = review
    spec.loader.exec_module(review)

    yield review, stub

    if real_tk is not None:
        sys.modules["tkinter"] = real_tk
    else:
        sys.modules.pop("tkinter", None)
    for mod in [
        "prompt_automation.gui",
        "prompt_automation.gui.single_window",
        "prompt_automation.gui.single_window.frames",
        spec.name,
        "prompt_automation.services.variable_form",
    ]:
        sys.modules.pop(mod, None)


def _simple_app():
    return types.SimpleNamespace(root=object(), finish=lambda t: None, cancel=lambda: None)


def test_copy_paths_visibility(review_module):
    review, _ = review_module
    app = _simple_app()
    view = review.build(app, {}, {"file_path": "/tmp/x"})
    assert view.copy_paths_btn is not None
    view2 = review.build(app, {}, {"foo": "bar"})
    assert view2.copy_paths_btn is None


def test_append_confirmation_flow(monkeypatch, review_module):
    review, tkstub = review_module
    app = _simple_app()
    template = {"template": ["hi"]}
    variables = {"append_file": "/tmp/file"}
    calls = {}
    monkeypatch.setattr(review, "_append_to_files", lambda vm, text: calls.update(vm=vm, text=text))
    monkeypatch.setattr(review, "log_usage", lambda t, l: None)
    # confirm append
    tkstub.messagebox.askyesno = lambda *a, **k: True
    view = review.build(app, template, variables)
    view.finish()
    assert calls["vm"] == variables and calls["text"] == "hi"
    # decline append
    calls.clear()
    tkstub.messagebox.askyesno = lambda *a, **k: False
    view = review.build(app, template, variables)
    view.finish()
    assert calls == {}


def test_usage_logging_invocation(monkeypatch, review_module):
    review, tkstub = review_module
    app = _simple_app()
    template = {"id": 1, "style": "test", "template": ["hello"]}
    captured = {}
    monkeypatch.setattr(review, "log_usage", lambda tmpl, length: captured.update(tmpl=tmpl, length=length))
    tkstub.messagebox.askyesno = lambda *a, **k: False
    view = review.build(app, template, {})
    view.finish()
    assert captured == {"tmpl": template, "length": len("hello")}


def test_shortcut_keys(monkeypatch, review_module):
    review, tkstub = review_module
    finished = {}
    cancelled = {}
    copied = {}
    app = types.SimpleNamespace(
        root=object(),
        finish=lambda text: finished.update(text=text),
        cancel=lambda: cancelled.setdefault("called", True),
    )
    template = {"template": ["bye"]}
    monkeypatch.setattr(review, "log_usage", lambda *a, **k: None)
    monkeypatch.setattr(review, "_append_to_files", lambda *a, **k: None)
    tkstub.messagebox.askyesno = lambda *a, **k: False
    monkeypatch.setattr(review, "copy_to_clipboard", lambda txt: copied.setdefault("text", txt))
    view = review.build(app, template, {})
    assert {"<Control-Return>", "<Control-Shift-c>", "<Escape>"} <= set(view.bindings)
    view.bindings["<Control-Shift-c>"]()
    assert copied["text"] == "bye"
    view.bindings["<Control-Return>"]()
    assert finished["text"] == "bye"
    view.bindings["<Escape>"]()
    assert cancelled["called"]


def test_finish_copies_to_clipboard(monkeypatch, review_module):
    review, tkstub = review_module
    events = []
    app = types.SimpleNamespace(
        root=object(),
        finish=lambda text: events.append(("finish", text)),
        cancel=lambda: None,
    )
    template = {"template": ["hi"]}
    monkeypatch.setattr(review, "log_usage", lambda *a, **k: None)
    monkeypatch.setattr(review, "_append_to_files", lambda *a, **k: None)
    tkstub.messagebox.askyesno = lambda *a, **k: False
    monkeypatch.setattr(
        review, "copy_to_clipboard", lambda txt: events.append(("copy", txt))
    )
    view = review.build(app, template, {})
    view.finish()
    assert events == [("copy", "hi"), ("finish", "hi")]
