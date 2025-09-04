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
    stub.TkVersion = "8.6"  # enables hierarchical mode gate in selector
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


def test_hierarchical_root_lists_folders_only(tmp_path, monkeypatch):
    real, tk = _install_tk_hier_stub()
    try:
        root = tmp_path / "styles"
        _write_template(root / "Code" / "01_a.json", 1, "A")
        _write_template(root / "Plans" / "05_p.json", 5, "P")
        (root / "Settings").mkdir(parents=True)
        (root / "Settings" / "settings.json").write_text("{}", encoding="utf-8")

        # Point PROMPTS_DIR to our tmp root and reload config + hierarchy + select
        monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))
        from prompt_automation import config as cfg
        importlib.reload(cfg)
        from prompt_automation.services import hierarchy as hmod
        importlib.reload(hmod)
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)

        # Build GUI view
        app = types.SimpleNamespace(root=_Widget())
        select.build(app)
        items = getattr(app, "_select_listbox")._items
        # Expect only folders at root
        assert any(x.endswith("Code/") for x in items)
        assert any(x.endswith("Plans/") for x in items)
        assert not any(x.endswith(".json") for x in items)
    finally:
        _restore_tk(real)


def test_hierarchical_search_flattens_results(tmp_path, monkeypatch):
    real, tk = _install_tk_hier_stub()
    try:
        root = tmp_path / "styles"
        _write_template(root / "Code" / "01_a.json", 1, "A")
        _write_template(root / "Plans" / "05_p.json", 5, "P")
        monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(root))
        from prompt_automation import config as cfg
        importlib.reload(cfg)
        from prompt_automation.services import hierarchy as hmod
        importlib.reload(hmod)
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)

        app = types.SimpleNamespace(root=_Widget())
        select.build(app)
        # Update query to trigger global search mode and refresh
        entry = getattr(app, "_select_query_entry")
        entry.kw["textvariable"].set("01_")
        # Call the bound key release handler if present
        if "<KeyRelease>" in entry.bound:
            entry.bound["<KeyRelease>"](None)
        items = getattr(app, "_select_listbox")._items
        # Now results should include flat relative path
        assert any(x.endswith("Code/01_a.json") for x in items)
        assert not any(x.endswith("Plans/05_p.json") for x in items)
    finally:
        _restore_tk(real)

