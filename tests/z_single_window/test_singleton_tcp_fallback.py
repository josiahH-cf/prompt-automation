import sys, types, socket, os, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _stub_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children={}
            self._geom='100x100'
            self.focused=0
        def title(self,*a,**k): pass
        def geometry(self,g=None): return self._geom
        def minsize(self,*a,**k): pass
        def resizable(self,*a,**k): pass
        def protocol(self,*a,**k): pass
        def update_idletasks(self): pass
        def winfo_geometry(self): return self._geom
        def winfo_exists(self): return True
        def quit(self): pass
        def destroy(self): pass
        def bind(self,*a,**k): pass
        def lift(self): pass
        def focus_force(self): self.focused += 1
        def attributes(self,*a,**k): pass
        def after(self,*a,**k): pass
    tk = types.ModuleType('tkinter')
    tk.Tk = DummyTk
    tk.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    monkeypatch.setitem(sys.modules, 'tkinter', tk)
    return tk


def test_tcp_fallback_focus_inproc(monkeypatch, tmp_path):
    _stub_tk(monkeypatch)
    # Force TCP fallback even if AF_UNIX available (no sockets used in this test)
    monkeypatch.setenv('PROMPT_AUTOMATION_SINGLETON_FORCE_TCP', '1')
    monkeypatch.setenv('PROMPT_AUTOMATION_SINGLETON_SOCKET', str(tmp_path / 'dummy.sock'))
    # Provide variable_form stub
    sys.modules['prompt_automation.services.variable_form'] = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    app = controller.SingleWindowApp()
    # Simulate focus event directly (server callback normally does this)
    app._focus_and_raise(); app._focus_first_template_widget()
    assert app.root.focused >= 1
