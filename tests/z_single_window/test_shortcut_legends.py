"""Ensure single-window frames expose shortcut legends.

Adds src path like other tests so running file directly works without
PYTHONPATH modifications.
"""
import sys
import types
from pathlib import Path

# Ensure local src is importable when test executed in isolation
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def _install_tk(monkeypatch, missing=()):
    """Install a minimal tkinter stub with optional missing widgets."""
    stub = types.ModuleType("tkinter")
    stub.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: False)

    class _Var:
        def __init__(self, value=None):
            self._v = value

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    stub.Variable = _Var
    stub.StringVar = lambda value=None: _Var(value)
    stub.BooleanVar = lambda value=False: _Var(value)
    stub.filedialog = types.SimpleNamespace(askopenfilename=lambda *a, **k: "")

    for name in ("Listbox", "Canvas", "Label"):
        if name not in missing:
            setattr(stub, name, object)

    monkeypatch.setitem(sys.modules, "tkinter", stub)
    return stub


def test_select_legend_includes_digits(monkeypatch):
    _install_tk(monkeypatch, missing={"Listbox"})
    from prompt_automation.gui.single_window.frames import select

    app = types.SimpleNamespace(advance_to_collect=lambda tmpl: None)
    view = select.build(app)
    assert "digits" in view.instructions["text"]


def test_collect_legend_includes_ctrl_s(monkeypatch):
    _install_tk(monkeypatch, missing={"Canvas"})
    from prompt_automation.gui.single_window.frames import collect

    app = types.SimpleNamespace(
        back_to_select=lambda: None, advance_to_review=lambda v: None
    )
    view = collect.build(app, {"placeholders": []})
    text = view.instructions["text"]
    assert "Ctrl+Enter" in text and "Ctrl+S" in text


def test_review_legend_includes_ctrl_shift_c(monkeypatch):
    _install_tk(monkeypatch, missing={"Label"})
    from prompt_automation.gui.single_window.frames import review

    app = types.SimpleNamespace(finish=lambda t: None, cancel=lambda: None)
    view = review.build(app, {"template": []}, {})
    assert "Ctrl+Shift+C" in view.instructions["text"]

