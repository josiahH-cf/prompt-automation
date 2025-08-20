import sys
import types
from pathlib import Path
import importlib
import pytest

# insert src path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


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
    def pack(self, *a, **k):
        pass
    def grid(self, *a, **k):
        pass
    def configure(self, *a, **k):
        pass
    config = configure
    def create_window(self, *a, **k):
        pass
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
    def delete(self, *a, **k):
        self.text = ""
    def insert(self, idx, text):
        self.text = text
    def get(self, start=None, end=None):
        if "textvariable" in self.kw:
            return self.kw["textvariable"].get()
        return self.text
    def focus_set(self):
        pass


@pytest.fixture()
def collect_module(monkeypatch):
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

    orig_vf = sys.modules.get("prompt_automation.services.variable_form")
    import importlib.util
    module_path = Path(__file__).resolve().parents[3] / "src/prompt_automation/services/variable_form.py"
    spec = importlib.util.spec_from_file_location(
        "prompt_automation.services.variable_form", module_path
    )
    vf = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["prompt_automation.services.variable_form"] = vf
    spec.loader.exec_module(vf)

    import prompt_automation.gui.single_window.frames.collect as collect
    importlib.reload(collect)

    if orig_vf is not None:
        sys.modules["prompt_automation.services.variable_form"] = orig_vf
    else:
        sys.modules.pop("prompt_automation.services.variable_form", None)

    yield collect, vf

    sys.modules.pop("prompt_automation.gui.single_window.frames.collect", None)
    if real_tk is not None:
        sys.modules["tkinter"] = real_tk
    else:
        sys.modules.pop("tkinter", None)
    if real_fd is not None:
        sys.modules["tkinter.filedialog"] = real_fd
    else:
        sys.modules.pop("tkinter.filedialog", None)


def _setup_storage(monkeypatch, vf, initial):
    storage = {"data": initial, "set": None}
    def fake_load():
        return storage["data"]
    def fake_get(data, tid, name):
        return data.get("templates", {}).get(str(tid), {}).get(name)
    def fake_set(data, tid, name, payload):
        storage["set"] = (tid, name, payload)
        data.setdefault("templates", {}).setdefault(str(tid), {})[name] = payload
    def fake_save(data):
        storage["data"] = data
    monkeypatch.setattr(vf, "_load_overrides", fake_load)
    monkeypatch.setattr(vf, "_get_template_entry", fake_get)
    monkeypatch.setattr(vf, "_set_template_entry", fake_set)
    monkeypatch.setattr(vf, "_save_overrides", fake_save)
    return storage


def _setup_global_storage(monkeypatch, collect, initial):
    storage = {"data": initial}

    def fake_load():
        return storage["data"]

    def fake_save(data):
        storage["data"] = data

    def fake_get():
        return storage["data"].get("global_files", {}).get("reference_file")

    monkeypatch.setattr(collect, "load_overrides", fake_load)
    monkeypatch.setattr(collect, "save_overrides", fake_save)
    monkeypatch.setattr(collect, "get_global_reference_file", fake_get)
    return storage


def test_multiline_remember(monkeypatch, collect_module):
    collect, vf = collect_module
    store = {"value": ""}
    monkeypatch.setattr(vf, "get_remembered_context", lambda: "prev")
    monkeypatch.setattr(vf, "set_remembered_context", lambda v: store.update(value=v))

    app = types.SimpleNamespace(
        root=object(),
        back_to_select=lambda: None,
        advance_to_review=lambda v: None,
        edit_exclusions=lambda tid: None,
    )
    template = {
        "id": 1,
        "placeholders": [{"name": "ctx", "multiline": True, "remember": True}],
    }
    view = collect.build(app, template)
    w = view.widgets["ctx"]
    assert w.get() == "prev"
    w.insert("1.0", "new text")
    bind = view.bindings["ctx"]
    assert bind["get"]() == "new text"
    bind["remember_var"].set(True)
    bind["persist"]()
    assert store["value"] == "new text"


def test_file_picker_skip_and_persistence(monkeypatch, collect_module):
    collect, vf = collect_module
    storage = _setup_storage(monkeypatch, vf, {"templates": {"1": {"fileph": {"path": "/old", "skip": False}}}})
    app = types.SimpleNamespace(
        root=object(),
        back_to_select=lambda: None,
        advance_to_review=lambda v: None,
        edit_exclusions=lambda tid: None,
    )
    template = {
        "id": 1,
        "placeholders": [
            {"name": "fileph", "type": "file", "override": True, "template_id": 1}
        ],
    }
    view = collect.build(app, template)
    bind = view.bindings["fileph"]
    w = view.widgets["fileph"]
    assert bind["path_var"].get() == "/old"
    # simulate browse
    w.browse_btn.kw["command"]()
    assert bind["path_var"].get() == "/picked/path"
    # skip flag
    bind["skip_var"].set(True)
    assert bind["get"]() == ""
    bind["skip_var"].set(False)
    assert bind["get"]() == "/picked/path"
    # persist and rebuild
    bind["persist"]()
    assert storage["set"] == (1, "fileph", {"path": "/picked/path", "skip": False})
    view2 = collect.build(app, template)
    bind2 = view2.bindings["fileph"]
    assert bind2["path_var"].get() == "/picked/path"
    # reset
    bind2["reset"]()
    assert bind2["path_var"].get() == ""
    assert bind2["skip_var"].get() is False


def test_exclusions_access(collect_module):
    collect, _ = collect_module
    called = []
    app = types.SimpleNamespace(
        root=object(),
        back_to_select=lambda: None,
        advance_to_review=lambda v: None,
        edit_exclusions=lambda tid: called.append(tid),
    )
    template = {"id": 42, "placeholders": []}
    view = collect.build(app, template)
    view.open_exclusions()
    assert called == [42]


def test_global_reference_memory(monkeypatch, collect_module):
    collect, vf = collect_module
    storage = _setup_global_storage(monkeypatch, collect, {})

    app = types.SimpleNamespace(
        root=object(),
        back_to_select=lambda: None,
        advance_to_review=lambda v: None,
        edit_exclusions=lambda tid: None,
    )
    template = {"id": 1, "placeholders": []}

    view = collect.build(app, template)
    bind = view.bindings["_global_reference"]
    w = view.widgets["_global_reference"]
    assert bind["path_var"].get() == ""

    # simulate browse
    w.browse_btn.kw["command"]()
    assert bind["path_var"].get() == "/picked/path"

    # persist and rebuild
    bind["persist"]()
    assert storage["data"]["global_files"]["reference_file"] == "/picked/path"

    view2 = collect.build(app, template)
    bind2 = view2.bindings["_global_reference"]
    assert bind2["path_var"].get() == "/picked/path"
