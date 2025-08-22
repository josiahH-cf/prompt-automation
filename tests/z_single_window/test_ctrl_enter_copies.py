import sys
import types
from pathlib import Path
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _install_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom = '800x600'
            self.bound = {}
            self._menu=None
        def title(self,*a,**k): pass
        def geometry(self,g=None):
            if g: self._geom=g
            return self._geom
        def minsize(self,*a,**k): pass
        def resizable(self,*a,**k): pass
        def protocol(self,*a,**k): pass
        def update_idletasks(self): pass
        def winfo_geometry(self): return self._geom
        def winfo_exists(self): return True
        def quit(self): pass
        def destroy(self): pass
        def bind(self, seq, func): self.bound[seq]=func
        def config(self, **kw): self._menu = kw.get('menu', self._menu)
        def nametowidget(self, name): raise KeyError(name)
        def __getitem__(self, item):
            if item=='menu': return self._menu
            raise KeyError(item)
    stub = types.ModuleType('tkinter')
    stub.Tk = DummyTk
    stub.Menu = lambda *a, **k: types.SimpleNamespace(add_cascade=lambda *a, **k: None, add_command=lambda *a, **k: None, add_separator=lambda *a, **k: None)
    # Omit Label so review.build uses headless (non-widget) path.
    stub.Text = object; stub.Scrollbar = object; stub.Frame = object; stub.Button = object
    stub.StringVar = lambda value='': types.SimpleNamespace(get=lambda: value, set=lambda v: None)
    stub.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: False, showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None)
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    stub.filedialog = fd
    sys.modules['tkinter.filedialog'] = fd
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    return stub


def test_ctrl_enter_triggers_copy(monkeypatch):
    _install_tk(monkeypatch)
    # Fresh import of controller & review frame
    import prompt_automation.gui.single_window.controller as controller
    # Prevent options menu complexity
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    # Stub select & collect -> directly advance to review with template
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app, t: types.SimpleNamespace(review=lambda: None))
    import prompt_automation.gui.single_window.frames.review as review_mod
    calls = {'copy':0}
    # Patch safe copy so we can verify it is used during finish
    monkeypatch.setattr(review_mod, 'safe_copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or True)
    app = controller.SingleWindowApp()
    tmpl = {'id': 1, 'style': 'unit', 'template':['Hello']}
    app.template = tmpl  # normally set during advance_to_collect
    vars_map={}
    app.advance_to_review(vars_map)
    # In headless stub, bindings exposed on view instead of root
    view = app._current_view  # type: ignore
    assert '<Control-Return>' in view.bindings
    view.bindings['<Control-Return>']()
    # finish() should have copied exactly once
    assert calls['copy'] == 1
