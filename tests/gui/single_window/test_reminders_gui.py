import sys
import types
from pathlib import Path

import pytest

# Ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))


class _Var:
    def __init__(self, value=None):
        self.value = value
    def get(self):
        return self.value
    def set(self, v):
        self.value = v


class _Widget:
    def __init__(self, master=None, **kw):
        self.master = master
        self.kw = kw
        self.text = kw.get('text', '')
        self.children = []
    def pack(self, *a, **k):
        pass
    def grid(self, *a, **k):
        pass
    def configure(self, *a, **k):
        pass
    config = configure
    def create_window(self, *a, **k):
        return 1
    def yview(self, *a, **k):
        pass
    def set(self, *a, **k):
        pass
    def bind(self, *a, **k):
        pass
    def bind_all(self, *a, **k):
        pass
    def columnconfigure(self, *a, **k):
        pass
    def rowconfigure(self, *a, **k):
        pass
    def delete(self, *a, **k):
        self.text = ""
    def insert(self, *a, **k):
        pass
    def get(self, *a, **k):
        return self.text
    def focus_set(self):
        pass


@pytest.fixture()
def tk_stub(monkeypatch):
    real_tk = sys.modules.get("tkinter")
    real_fd = sys.modules.get("tkinter.filedialog")

    stub = types.ModuleType("tkinter")
    stub.Frame = _Widget
    stub.Entry = _Widget
    stub.Text = _Widget
    stub.Button = _Widget
    stub.Checkbutton = _Widget
    stub.Label = _Widget
    stub.Scrollbar = _Widget
    stub.Canvas = _Widget
    stub.Toplevel = _Widget
    stub.StringVar = _Var
    stub.BooleanVar = _Var
    stub.Widget = _Widget

    fd_stub = types.ModuleType("filedialog")
    fd_stub.askopenfilename = lambda title=None: "/picked/path"

    monkeypatch.setitem(sys.modules, "tkinter", stub)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fd_stub)
    yield
    if real_tk is not None:
        sys.modules["tkinter"] = real_tk
    else:
        sys.modules.pop("tkinter", None)
    if real_fd is not None:
        sys.modules["tkinter.filedialog"] = real_fd
    else:
        sys.modules.pop("tkinter.filedialog", None)


def test_gui_inline_and_panel(monkeypatch, tk_stub):
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "1")
    from prompt_automation.gui.single_window.frames import collect

    app = types.SimpleNamespace(root=object(), back_to_select=lambda: None, advance_to_review=lambda v: None, edit_exclusions=lambda tid: None)
    template = {
        "id": 1,
        "title": "Demo",
        "reminders": ["Top level one", "Top level two"],
        "global_placeholders": {"reminders": ["Global three"]},
        "placeholders": [
            {"name": "ctx", "label": "Context", "multiline": True, "reminders": ["Under field A", "Under field B"]},
            {"name": "path", "type": "file", "label": "File", "reminders": ["Pick a small file"]},
            {"name": "title", "label": "Title", "reminders": ["Keep it short"]},
        ],
    }
    view = collect.build(app, template)
    # Confirm panel exists
    assert getattr(view, 'reminders_panel', None) is not None
    # Toggle function exists
    assert callable(getattr(view, 'reminders_toggle', None))


def test_gui_flag_off_hides_panel(monkeypatch, tk_stub):
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "0")
    from prompt_automation.gui.single_window.frames import collect

    app = types.SimpleNamespace(root=object(), back_to_select=lambda: None, advance_to_review=lambda v: None, edit_exclusions=lambda tid: None)
    template = {
        "id": 1,
        "title": "Demo",
        "reminders": ["Top level one"],
        "placeholders": [
            {"name": "title", "label": "Title", "reminders": ["Keep it short"]},
        ],
    }
    view = collect.build(app, template)
    # Panel hidden
    assert getattr(view, 'reminders_panel', None) is None
