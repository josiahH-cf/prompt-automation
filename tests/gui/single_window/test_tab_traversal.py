import sys
import types
from pathlib import Path

# Insert src path
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
        self._binds = []  # record bound sequences
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
    def bind(self, seq, func):
        # record the sequence; function not executed in test
        self._binds.append(seq)
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


def _build_collect_module(monkeypatch):
    """Load the collect frame with a stub tkinter capturing binds."""
    real_tk = sys.modules.get("tkinter")
    real_fd = sys.modules.get("tkinter.filedialog")

    stub = types.ModuleType("tkinter")
    # widget classes
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

    import importlib, importlib.util
    module_path = Path(__file__).resolve().parents[3] / "src/prompt_automation/gui/single_window/frames/collect.py"
    spec = importlib.util.spec_from_file_location(
        "prompt_automation.gui.single_window.frames.collect", module_path
    )
    collect = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["prompt_automation.gui.single_window.frames.collect"] = collect
    spec.loader.exec_module(collect)  # type: ignore[attr-defined]

    # restore originals after test via finalizer
    def _restore():
        if real_tk is not None:
            sys.modules["tkinter"] = real_tk
        else:
            sys.modules.pop("tkinter", None)
        if real_fd is not None:
            sys.modules["tkinter.filedialog"] = real_fd
        else:
            sys.modules.pop("tkinter.filedialog", None)
        sys.modules.pop("prompt_automation.gui.single_window.frames.collect", None)
    return collect, _restore


def test_tab_traversal_binds(monkeypatch):
    collect, restore = _build_collect_module(monkeypatch)
    try:
        # Template with multiline, file (override), and single-line entries
        template = {
            "id": 1,
            "placeholders": [
                {"name": "multi", "multiline": True},
                {"name": "fileph", "type": "file", "override": True, "template_id": 1},
                {"name": "single"},
            ],
        }
        app = types.SimpleNamespace(
            root=object(),
            back_to_select=lambda: None,
            advance_to_review=lambda v: None,
            edit_exclusions=lambda tid: None,
        )
        view = collect.build(app, template)
        widgets = view.widgets
        # Multiline text widget should have Tab binds
        multi_w = widgets["multi"]
        assert any(seq == "<Tab>" for seq in getattr(multi_w, "_binds", [])), "Tab not bound for multiline Text"
        # File placeholder path entry
        file_frame = widgets["fileph"]
        path_entry = getattr(file_frame, "entry")
        assert any(seq == "<Tab>" for seq in getattr(path_entry, "_binds", [])), "Tab not bound for file path entry"
        # Single-line entry
        single_w = widgets["single"]
        assert any(seq == "<Tab>" for seq in getattr(single_w, "_binds", [])), "Tab not bound for single-line entry"
        # Shift-Tab present as well
        assert any(seq == "<Shift-Tab>" for seq in getattr(single_w, "_binds", [])), "Shift-Tab not bound"
        # Reset function still available for override file placeholder
        assert "reset" in view.bindings["fileph"], "reset not exposed for override file placeholder"
    finally:
        restore()
