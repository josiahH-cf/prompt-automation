import sys
import types
import json
from pathlib import Path
import importlib


class _Var:
    def __init__(self, value=None):
        self._v = value
    def get(self):
        return self._v
    def set(self, v):
        self._v = v


class _Widget:
    def __init__(self, master=None, **kw):
        self.master = master
        self.kw = kw
        self.text = ""
        self.bound = {}
    def pack(self, *a, **k):
        pass
    def configure(self, *a, **k):
        pass
    config = configure
    def yview(self, *a, **k):
        pass
    def set(self, *a, **k):
        pass
    def bind(self, seq, func):
        self.bound[seq] = func
    def bind_all(self, *a, **k):
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


class _Listbox(_Widget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._items = []
        self._selected = []
        self._active = None
    def insert(self, idx, text):
        self._items.append(text)
    def delete(self, start, end=None):
        self._items = []
        self._selected = []
        self._active = None
    def size(self):
        return len(self._items)
    def curselection(self):
        return tuple(self._selected)
    def selection_clear(self, start, end):
        self._selected = []
    def selection_set(self, idx):
        self._selected = [idx]
    def activate(self, idx):
        self._active = idx


def _install_tk_hier_stub():
    real = sys.modules.get("tkinter")
    stub = types.ModuleType("tkinter")
    stub.TkVersion = "8.6"
    stub.Frame = _Widget
    stub.Entry = _Widget
    stub.Text = _Widget
    stub.Button = _Widget
    stub.Checkbutton = _Widget
    stub.Label = _Widget
    stub.Scrollbar = _Widget
    stub.Listbox = _Listbox
    stub.StringVar = _Var
    stub.BooleanVar = _Var
    sys.modules["tkinter"] = stub
    sys.modules["tkinter.filedialog"] = types.ModuleType("filedialog")
    return real, stub


def _restore_tk(real):
    if real is not None:
        sys.modules["tkinter"] = real
    else:
        sys.modules.pop("tkinter", None)


def _write_template(path: Path, id_val: int, title: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "id": id_val,
            "title": title,
            "style": path.parent.name,
            "template": ["{{title}}"],
            "placeholders": [{"name": "capture"}],
        }),
        encoding="utf-8",
    )


def test_ctrl_enter_toggles_folder_dropdown_and_enter_opens_template(tmp_path, monkeypatch):
    real, tk = _install_tk_hier_stub()
    try:
        root = tmp_path / "styles"
        _write_template(root / "Code" / "01_a.json", 1, "A")
        _write_template(root / "Plans" / "05_p.json", 5, "P")
        monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))
        monkeypatch.setenv("PROMPT_AUTOMATION_HOME", str(tmp_path / ".home"))
        # Reload config and selector path dependencies
        from prompt_automation import config as cfg
        importlib.reload(cfg)
        from prompt_automation.gui.single_window import geometry
        importlib.reload(geometry)
        from prompt_automation.gui.single_window import selector_state
        importlib.reload(selector_state)
        from prompt_automation.services import hierarchy as hmod
        importlib.reload(hmod)
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)

        received = []
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data))
        select.build(app)
        lb = getattr(app, "_select_listbox")
        items = lb._items
        # Find Code/ row
        code_idx = next(i for i, t in enumerate(items) if t.endswith("Code/"))
        lb.selection_clear(0, "end"); lb.selection_set(code_idx)
        # Toggle expansion via Ctrl+Enter
        assert "<Control-Return>" in lb.bound
        lb.bound["<Control-Return>"](None)
        items = lb._items
        assert any(t.strip().endswith("01_a.json") for t in items)
        # Select the template and press Enter
        tmpl_idx = next(i for i, t in enumerate(items) if t.strip().endswith("01_a.json"))
        lb.selection_clear(0, "end"); lb.selection_set(tmpl_idx)
        assert "<Return>" in lb.bound
        lb.bound["<Return>"](None)
        assert received and received[0].get("id") == 1
        # Toggle again to collapse
        lb.selection_clear(0, "end"); lb.selection_set(code_idx)
        lb.bound["<Control-Return>"](None)
        items = lb._items
        assert not any(t.strip().endswith("01_a.json") for t in items)
    finally:
        _restore_tk(real)
