import sys
import types
from pathlib import Path
import importlib

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def _install_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom = "400x300"
            self.bound = {}
            self._menu = None
        def title(self, *a, **k):
            pass
        def geometry(self, g=None):
            if g:
                self._geom = g
            return self._geom
        def minsize(self, *a, **k):
            pass
        def resizable(self, *a, **k):
            pass
        def protocol(self, *a, **k):
            pass
        def update_idletasks(self):
            pass
        def winfo_geometry(self):
            return self._geom
        def winfo_exists(self):
            return True
        def quit(self):
            pass
        def destroy(self):
            pass
        def bind(self, seq, func):
            self.bound[seq] = func
        def config(self, **kw):
            self._menu = kw.get('menu', self._menu)
        def nametowidget(self, name):  # simplistic
            raise KeyError(name)
        def __getitem__(self, item):
            if item == 'menu':
                return self._menu
            raise KeyError(item)
    stub = types.ModuleType("tkinter")
    stub.Tk = DummyTk
    stub.Menu = lambda *a, **k: types.SimpleNamespace(add_cascade=lambda *a, **k: None, add_command=lambda *a, **k: None, add_separator=lambda *a, **k: None)
    stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, askyesno=lambda *a, **k: False, showinfo=lambda *a, **k: None)
    # Provide filedialog submodule expected by variable_form
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    stub.filedialog = fd
    monkeypatch.setitem(sys.modules, "tkinter", stub)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fd)
    return stub


def test_stage_specific_menu(monkeypatch):
    _install_tk(monkeypatch)
    # Import controller fresh
    module = importlib.import_module("prompt_automation.gui.single_window.controller")
    # Capture extra items injections
    injected = []
    real_cfg = module.options_menu.configure_options_menu
    def fake_configure(root, svm, service, **kw):
        accels = real_cfg(root, svm, service, **kw)
        injected.append(root._menu)  # type: ignore[attr-defined]
        return accels
    monkeypatch.setattr(module.options_menu, "configure_options_menu", fake_configure)
    # Stub frames to simple namespaces so stage transitions succeed quickly
    monkeypatch.setattr(module.select, "build", lambda app: types.SimpleNamespace())
    monkeypatch.setattr(module.collect, "build", lambda app, t: types.SimpleNamespace(review=lambda: None))
    monkeypatch.setattr(module.review, "build", lambda app, t, v: types.SimpleNamespace(copy=lambda: None, finish=lambda: None))
    app = module.SingleWindowApp(); app.start()
    # Start → select stage
    assert app._stage == 'select'
    app.advance_to_collect({})
    assert app._stage == 'collect'
    app.advance_to_review({})
    assert app._stage == 'review'
    # Ensure menu was rebuilt at each stage (>=3 times)
    assert len(injected) >= 3


def test_safe_copy_to_clipboard_failure(monkeypatch):
    import prompt_automation.gui.error_dialogs as err
    safe_copy_to_clipboard = err.safe_copy_to_clipboard
    # Force underlying helper to raise so we exercise error path even after
    # refactor to boolean return.
    monkeypatch.setattr(err, '_base_copy', lambda _t: (_ for _ in ()).throw(RuntimeError('boom')))
    # Simulate Tk import success but clipboard failure
    class DummyTk:
        def __init__(self):
            pass
        def withdraw(self):
            pass
        def clipboard_clear(self):
            raise RuntimeError("clipboard unavailable")
        def clipboard_append(self, text):
            pass
        def update_idletasks(self):
            pass
        def destroy(self):
            pass
    tkmod = types.SimpleNamespace(Tk=DummyTk)
    monkeypatch.setitem(sys.modules, 'tkinter', tkmod)
    shown = {}
    def fake_show_error(title, msg):
        shown['title'] = title; shown['msg'] = msg
    monkeypatch.setenv('DISPLAY', ':0')  # ensure Tk path taken
    monkeypatch.setitem(sys.modules, 'tkinter.messagebox', types.SimpleNamespace(showerror=lambda *a, **k: None))
    monkeypatch.setattr(err, 'show_error', fake_show_error)
    ok = safe_copy_to_clipboard('text')
    assert ok is False
    assert shown['title'] == 'Clipboard Error'
