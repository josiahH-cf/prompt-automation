import sys
import types
from pathlib import Path

import importlib

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


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
    def pack(self, *a, **k):
        pass
    def configure(self, *a, **k):
        pass
    config = configure
    def yview(self, *a, **k):
        pass
    def set(self, *a, **k):
        pass
    def bind(self, *a, **k):
        pass
    def bind_all(self, *a, **k):
        # Store global binding for retrieval in test
        seq, func = a[0], a[1]
        import sys as _sys
        tkmod = _sys.modules.get("tkinter")
        if tkmod:
            setattr(tkmod, "GLOBAL_BINDINGS", getattr(tkmod, "GLOBAL_BINDINGS", {}))
            tkmod.GLOBAL_BINDINGS[seq] = func
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


def _install_tk_stub():
    real = sys.modules.get("tkinter")
    stub = types.ModuleType("tkinter")
    # Widgets used by select.build GUI path
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
    # Provide storage for global key bindings
    stub.GLOBAL_BINDINGS = {}
    sys.modules["tkinter"] = stub
    # Also provide filedialog submodule expected by variable_form imports
    fd_stub = types.ModuleType("filedialog")
    fd_stub.askopenfilename = lambda *a, **k: ""
    sys.modules["tkinter.filedialog"] = fd_stub
    return real, stub


def _restore_tk(real):
    if real is not None:
        sys.modules["tkinter"] = real
    else:
        sys.modules.pop("tkinter", None)


def test_windows_numpad_digit_triggers_selection(monkeypatch):
    real_tk, tk = _install_tk_stub()
    try:
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)

        # Ensure relative_to(PROMPTS_DIR) works with simple relative Paths
        monkeypatch.setattr(select, "PROMPTS_DIR", Path("."))
        # Provide two templates and a loader
        monkeypatch.setattr(
            select,
            "list_templates",
            lambda search="", recursive=True: [Path("a.json"), Path("b.json")],
        )
        monkeypatch.setattr(select, "load_template", lambda p: {"id": 1, "template": [p.stem]})
        # No shortcut mapping resolution in this test
        monkeypatch.setattr(select, "resolve_shortcut", lambda k: None)

        received = []
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data), _stage='select')

        # Build GUI view (uses our Tk stub) and fetch bound on_key
        select.build(app)
        on_key = tk.GLOBAL_BINDINGS.get("<Key>")
        assert callable(on_key), "on_key handler was not bound"

        # Simulate Windows numpad event with empty char but KP_1 keysym
        event = types.SimpleNamespace(char="", keysym="KP_1")
        out = on_key(event)
        # Before fix, handler returns None and does not advance; after fix it should return "break"
        assert received, "Expected selection to advance for KP_1 event"
        assert out == "break"
    finally:
        _restore_tk(real_tk)


def test_toprow_digit_with_empty_char_still_works(monkeypatch):
    real_tk, tk = _install_tk_stub()
    try:
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)
        monkeypatch.setattr(select, "PROMPTS_DIR", Path("."))
        monkeypatch.setattr(
            select,
            "list_templates",
            lambda search="", recursive=True: [Path("a.json"), Path("b.json")],
        )
        monkeypatch.setattr(select, "load_template", lambda p: {"id": 1})
        monkeypatch.setattr(select, "resolve_shortcut", lambda k: None)
        received = []
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data), _stage='select')
        select.build(app)
        on_key = tk.GLOBAL_BINDINGS.get("<Key>")
        # Simulate top-row '1' where event.char happens to be empty
        out = on_key(types.SimpleNamespace(char="", keysym="1"))
        assert received, "Expected advancement for keysym '1'"
        assert out == "break"
    finally:
        _restore_tk(real_tk)


def test_out_of_range_digit_does_not_advance(monkeypatch):
    real_tk, tk = _install_tk_stub()
    try:
        import prompt_automation.gui.single_window.frames.select as select
        importlib.reload(select)
        monkeypatch.setattr(select, "PROMPTS_DIR", Path("."))
        monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: [Path("a.json")])
        monkeypatch.setattr(select, "load_template", lambda p: {"id": 1})
        monkeypatch.setattr(select, "resolve_shortcut", lambda k: None)
        received = []
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data), _stage='select')
        select.build(app)
        on_key = tk.GLOBAL_BINDINGS.get("<Key>")
        # Only 1 item; press '9' should do nothing and not swallow
        out = on_key(types.SimpleNamespace(char="", keysym="9"))
        assert not received, "Should not advance for out-of-range digit"
        assert out is None, "Un-handled key should not be swallowed"
    finally:
        _restore_tk(real_tk)


def test_digits_are_ignored_outside_select_stage(monkeypatch):
    real_tk, tk = _install_tk_stub()
    try:
        import prompt_automation.gui.single_window.frames.select as select
        import importlib
        importlib.reload(select)
        monkeypatch.setattr(select, "PROMPTS_DIR", Path("."))
        monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: [Path("a.json")])
        monkeypatch.setattr(select, "load_template", lambda p: {"id": 1})
        monkeypatch.setattr(select, "resolve_shortcut", lambda k: None)
        received = []
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data))
        select.build(app)
        on_key = tk.GLOBAL_BINDINGS.get("<Key>")
        # Simulate stage switch to 'collect' as controller would
        setattr(app, "_stage", "collect")
        out = on_key(types.SimpleNamespace(char="", keysym="KP_1"))
        assert not received, "Digit should not activate in collect stage"
        assert out is None, "Handler should not swallow keys in collect stage"
    finally:
        _restore_tk(real_tk)


def test_digits_work_when_stage_unknown(monkeypatch):
    real_tk, tk = _install_tk_stub()
    try:
        import prompt_automation.gui.single_window.frames.select as select
        import importlib
        importlib.reload(select)
        monkeypatch.setattr(select, "PROMPTS_DIR", Path("."))
        monkeypatch.setattr(select, "list_templates", lambda search="", recursive=True: [Path("a.json")])
        monkeypatch.setattr(select, "load_template", lambda p: {"id": 1})
        monkeypatch.setattr(select, "resolve_shortcut", lambda k: None)
        received = []
        # No _stage attribute on app (simulate legacy/standalone usage)
        app = types.SimpleNamespace(root=_Widget(), advance_to_collect=lambda data: received.append(data))
        select.build(app)
        on_key = tk.GLOBAL_BINDINGS.get("<Key>")
        out = on_key(types.SimpleNamespace(char="", keysym="1"))
        assert received, "Digits should work when stage is unknown"
        assert out == "break"
    finally:
        _restore_tk(real_tk)
