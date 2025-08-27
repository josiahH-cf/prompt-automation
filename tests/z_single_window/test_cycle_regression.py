import sys, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _install_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom='100x100'
            self.bound = {}
            self.after_calls = []
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
        def bind(self, seq, func): self.bound[seq]=func
        def lift(self): pass
        def focus_force(self): pass
        def attributes(self,*a,**k): pass
        def after(self, delay, cb): self.after_calls.append(cb); cb()
    tk = types.ModuleType('tkinter'); tk.Tk = DummyTk; tk.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    monkeypatch.setitem(sys.modules,'tkinter',tk)
    return tk


def test_cycle_finish_returns_to_select_without_freeze(monkeypatch):
    _install_tk(monkeypatch)
    # stub variable_form before import
    sys.modules['prompt_automation.services.variable_form'] = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu,'configure_options_menu',lambda *a,**k: {})
    events = []
    # simplify frame builders
    monkeypatch.setattr(controller.select,'build',lambda app: events.append('select'))
    monkeypatch.setattr(controller.collect,'build',lambda app,t: events.append('collect'))
    def fake_review(app,t,v):
        events.append('review')
        return types.SimpleNamespace(finish=lambda: app.finish('x'))
    monkeypatch.setattr(controller.review,'build',fake_review)
    app = controller.SingleWindowApp(); app.start()
    app.advance_to_collect({'id':1}); app.advance_to_review({'a':1})
    # Call finish (cycles asynchronously via after stub executing immediately)
    app._current_view.finish()  # type: ignore[attr-defined]
    # Expect order includes second 'select'
    assert events.count('select') == 2
    # Invoke collect path again to ensure bindings still work (no freeze simulated)
    app.advance_to_collect({'id':2})
    assert events.count('collect') >= 2
