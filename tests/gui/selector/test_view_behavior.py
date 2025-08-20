import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

real_tk = sys.modules.get("tkinter")
real_ttk = sys.modules.get("tkinter.ttk")
real_msg = sys.modules.get("tkinter.messagebox")

# Stub out tkinter modules to avoid GUI usage
stub = types.ModuleType("tkinter")
stub.Tk = object
stub.Toplevel = object
stub.Frame = object
stub.Label = object
stub.Entry = object
stub.Button = object
stub.Text = object
stub.Scrollbar = object
stub.BooleanVar = lambda value=False: types.SimpleNamespace(get=lambda: value, set=lambda v: None)
stub.StringVar = lambda value="": types.SimpleNamespace(get=lambda: value, set=lambda v: None)
sys.modules.setdefault("tkinter", stub)

stub_ttk = types.ModuleType("ttk")
stub_ttk.Treeview = object
sys.modules.setdefault("tkinter.ttk", stub_ttk)

stub_msg = types.ModuleType("messagebox")
stub_msg.showerror = lambda *a, **k: None
sys.modules.setdefault("tkinter.messagebox", stub_msg)

from prompt_automation.gui.selector.view import SelectorView

# Restore real tkinter modules after import
if real_tk is not None:
    sys.modules["tkinter"] = real_tk
else:
    sys.modules.pop("tkinter", None)
if real_ttk is not None:
    sys.modules["tkinter.ttk"] = real_ttk
else:
    sys.modules.pop("tkinter.ttk", None)
if real_msg is not None:
    sys.modules["tkinter.messagebox"] = real_msg
else:
    sys.modules.pop("tkinter.messagebox", None)


class DummyService:
    def __init__(self):
        self.calls = []

    def search(self, query: str, recursive: bool = True):
        self.calls.append((query, recursive))
        return []


def test_recursive_toggle_behavior():
    svc = DummyService()
    view = SelectorView(svc)
    view.search("hello")
    view.toggle_recursive()
    view.search("world")
    assert svc.calls == [("hello", True), ("world", False)]


def test_multi_select_concatenation():
    view = SelectorView(DummyService())
    view.select_multi({"template": ["foo"]})
    view.select_multi({"template": ["bar", "baz"]})
    combined = view.finish_multi()
    assert combined["template"] == ["foo", "bar", "baz"]
    assert combined["title"] == "Multi (2)"
    assert combined["style"] == "multi"
