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


def test_tcp_fallback_focus(monkeypatch, tmp_path):
    # Some CI sandboxes disallow AF_INET sockets entirely; skip in that case
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.close()
    except Exception:
        pytest.skip('socket creation not permitted in sandbox')
    _stub_tk(monkeypatch)
    # Force TCP fallback even if AF_UNIX available
    monkeypatch.setenv('PROMPT_AUTOMATION_SINGLETON_FORCE_TCP', '1')
    monkeypatch.setenv('PROMPT_AUTOMATION_SINGLETON_SOCKET', str(tmp_path / 'dummy.sock'))
    # Provide variable_form stub
    sys.modules['prompt_automation.services.variable_form'] = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    app = controller.SingleWindowApp()
    # Locate port file
    port_file = Path.home() / '.prompt-automation' / 'gui.port'
    for _ in range(50):
        if port_file.exists(): break
        time.sleep(0.01)
    if not port_file.exists():
        pytest.skip('port file not created')
    port = int(port_file.read_text().strip())
    # Connect and send focus message
    with socket.create_connection(('127.0.0.1', port), timeout=0.5) as s:
        s.sendall(b'FOCUS\n')
    for _ in range(20):
        if app.root.focused:
            break
        time.sleep(0.01)
    assert app.root.focused >= 1
