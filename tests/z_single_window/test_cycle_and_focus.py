import sys
import types
from pathlib import Path
import importlib
import socket

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _install_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom = "200x100"
            self.bound = {}
            self.lifted = 0
            self.focused = 0
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
        def lift(self):
            self.lifted += 1
        def focus_force(self):
            self.focused += 1
        def attributes(self, *a, **k):
            pass
        def after(self, *a, **k):
            # args: delay, callback
            if len(a) >= 2 and callable(a[1]):
                a[1]()
    stub = types.ModuleType('tkinter')
    stub.Tk = DummyTk
    stub.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    stub.filedialog = types.SimpleNamespace(askopenfilename=lambda *a, **k: '')
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    return stub


def test_finish_cycles_back_to_select(monkeypatch):
    _install_tk(monkeypatch)
    # Minimal widget factory stub used by collect frame
    fake_vf = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))
    sys.modules['prompt_automation.services.variable_form'] = fake_vf
    # Speed up select/collect/review builds with simplified versions
    import prompt_automation.gui.single_window.controller as controller
    cycles = {'select':0, 'collect':0, 'review':0}
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    monkeypatch.setattr(controller.select, 'build', lambda app: cycles.__setitem__('select', cycles['select']+1))
    monkeypatch.setattr(controller.collect, 'build', lambda app, t: cycles.__setitem__('collect', cycles['collect']+1))
    # Review.build returns object with finish() calling app.finish(text)
    def fake_review_build(app, t, v):
        cycles['review'] += 1
        return types.SimpleNamespace(finish=lambda: app.finish('out'), copy=lambda: None, cancel=lambda: None)
    monkeypatch.setattr(controller.review, 'build', fake_review_build)
    app = controller.SingleWindowApp()
    # Explicitly start to simulate normal GUI launch so initial focus occurs
    app.start()
    assert app._stage == 'select'
    app.advance_to_collect({'id':1})
    assert app._stage == 'collect'
    app.advance_to_review({'a':1})
    assert app._stage == 'review'
    # Trigger finish -> should cycle back to select without destroy
    app._current_view.finish()  # type: ignore[attr-defined]
    assert app._stage == 'select'
    # At least two select builds now (initial + cycle)
    assert cycles['select'] >= 2


def test_singleton_focus_inproc(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    # Provide minimal variable_form early so import inside collect works
    fake_vf = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))
    sys.modules['prompt_automation.services.variable_form'] = fake_vf
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    # Count template focus attempts
    def _count_focus(self):
        self.template_focus = getattr(self, 'template_focus', 0) + 1
    monkeypatch.setattr(controller.SingleWindowApp, '_focus_first_template_widget', _count_focus)
    app = controller.SingleWindowApp()
    app.start()
    # Simulate external focus via in-process callback (no sockets required)
    app._focus_and_raise(); app._focus_first_template_widget()
    assert app.root.lifted >= 1 and app.root.focused >= 1
    # Initial start triggers one template focus; simulated focus should add another
    assert getattr(app, 'template_focus', 0) >= 2
    # connect_and_focus_if_running should acknowledge an in-process instance
    from prompt_automation.gui.single_window import singleton
    assert singleton.connect_and_focus_if_running() is True
