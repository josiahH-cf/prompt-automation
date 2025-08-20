import sys
import types
from pathlib import Path

# insert src path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# --- stub tkinter modules ---------------------------------------------------
real_tk = sys.modules.get("tkinter")
real_fd = sys.modules.get("tkinter.filedialog")

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
        self.text = ""
    def insert(self, idx, text):
        self.text = text
    def get(self, start=None, end=None):
        if "textvariable" in self.kw:
            return self.kw["textvariable"].get()
        return self.text

stub = types.ModuleType("tkinter")
stub.Frame = _Widget
stub.Entry = _Widget
stub.Text = _Widget
stub.Button = _Widget
stub.Checkbutton = _Widget
stub.StringVar = _Var
stub.BooleanVar = _Var
sys.modules["tkinter"] = stub

fd_stub = types.ModuleType("filedialog")
fd_stub.askopenfilename = lambda title=None, initialfile="": "/chosen/path"
sys.modules["tkinter.filedialog"] = fd_stub

# ensure module uses the stub regardless of previous imports
sys.modules.pop("prompt_automation.services.variable_form", None)
from prompt_automation.services.variable_form import build_widget
import prompt_automation.services.variable_form as vf

# restore real tkinter modules after import
if real_tk is not None:
    sys.modules["tkinter"] = real_tk
else:
    sys.modules.pop("tkinter", None)
if real_fd is not None:
    sys.modules["tkinter.filedialog"] = real_fd
else:
    sys.modules.pop("tkinter.filedialog", None)


# ---------------------------------------------------------------------------
# helpers for patching storage layer


def _setup_storage(monkeypatch, stored):
    def fake_load():
        return stored
    def fake_get(data, tid, name):
        return data.get("templates", {}).get(str(tid), {}).get(name)
    recorded = {"set": None, "save": None}
    def fake_set(data, tid, name, payload):
        recorded["set"] = (tid, name, payload)
    def fake_save(data):
        recorded["save"] = data
    monkeypatch.setattr(vf, "_load_overrides", fake_load)
    monkeypatch.setattr(vf, "_get_template_entry", fake_get)
    monkeypatch.setattr(vf, "_set_template_entry", fake_set)
    monkeypatch.setattr(vf, "_save_overrides", fake_save)
    return recorded


# ---------------------------------------------------------------------------

def test_text_single_line():
    ctor, bind = build_widget({"name": "title"})
    widget = ctor(None)
    assert isinstance(widget, _Widget)
    bind_obj = types.SimpleNamespace(**bind)
    # simulate user input
    widget.kw["textvariable"].set("hello")
    assert bind_obj.get() == "hello"


def test_text_multiline_remember(monkeypatch):
    store = {"value": "old"}
    monkeypatch.setattr(vf, "get_remembered_context", lambda: store["value"])
    monkeypatch.setattr(vf, "set_remembered_context", lambda v: store.update(value=v))
    ctor, bind = build_widget({"name": "context", "multiline": True, "remember": True})
    widget = ctor(None)
    assert widget.get() == "old"
    widget.insert("1.0", "new text")
    bind["remember_var"].set(True)
    bind["persist"]()
    assert store["value"] == "new text"


def test_file_widget(monkeypatch):
    stored = {"templates": {"1": {"fileph": {"path": "/remembered", "skip": False}}}}
    calls = _setup_storage(monkeypatch, stored)

    viewed = {}
    def viewer(path):
        viewed["path"] = path

    ctor, bind = build_widget({
        "name": "fileph",
        "type": "file",
        "override": True,
        "template_id": 1,
        "on_view": viewer,
    })
    ctor(None)
    assert bind["path_var"].get() == "/remembered"
    bind["view"]()
    assert viewed["path"] == "/remembered"
    bind["path_var"].set("/new/path")
    bind["skip_var"].set(True)
    bind["persist"]()
    assert calls["set"] == (1, "fileph", {"path": "/new/path", "skip": True})
    assert bind["get"]() == ""
    bind["skip_var"].set(False)
    assert bind["get"]() == "/new/path"
