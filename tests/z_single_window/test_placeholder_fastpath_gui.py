import sys, types
from pathlib import Path

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
        def after(self, *a, **k): pass
        def focus_force(self): pass
        def lift(self): pass
        def attributes(self,*a,**k): pass
        def __getitem__(self, item):
            if item=='menu': return self._menu
            raise KeyError(item)
    stub = types.ModuleType('tkinter')
    stub.Tk = DummyTk
    stub.Menu = lambda *a, **k: types.SimpleNamespace(add_cascade=lambda *a, **k: None, add_command=lambda *a, **k: None, add_separator=lambda *a, **k: None)
    # Omit Label so review.build uses headless path (deterministic in tests)
    stub.Text = object; stub.Scrollbar = object; stub.Frame = object; stub.Button = object
    stub.StringVar = lambda value='': types.SimpleNamespace(get=lambda: value, set=lambda v: None)
    stub.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: False, showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None)
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    stub.filedialog = fd
    sys.modules['tkinter.filedialog'] = fd
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    return stub


def test_gui_fastpath_skips_collect(monkeypatch):
    _install_tk(monkeypatch)
    # Fresh import of controller to bind tk stub
    import prompt_automation.gui.single_window.controller as controller
    # No-op menu
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    calls = {'collect': 0, 'review': 0, 'debug': []}
    # Track collect.build invocations
    orig_collect_build = controller.collect.build
    def spy_collect(*a, **k):
        calls['collect'] += 1
        return orig_collect_build(*a, **k)
    monkeypatch.setattr(controller.collect, 'build', spy_collect)
    # Track review.build
    orig_review_build = controller.review.build
    def spy_review(*a, **k):
        calls['review'] += 1
        return orig_review_build(*a, **k)
    monkeypatch.setattr(controller.review, 'build', spy_review)
    # Capture debug logs
    class StubLog:
        def debug(self, msg, **kw):
            calls['debug'].append((msg, kw))
        def info(self, *a, **k): pass
        def error(self, *a, **k): pass
    app = controller.SingleWindowApp()
    app._log = StubLog()

    tmpl = {'id': 1, 'style': 'unit', 'title': 't', 'template':['Hello World'], 'placeholders': []}
    app.advance_to_collect(tmpl)

    assert calls['collect'] == 0, 'collect.should not be built on fast-path'
    assert calls['review'] == 1, 'review.should be built exactly once on fast-path'
    assert app._stage == 'review'
    # Ensure a debug-level line was emitted (non-sensitive)
    assert any('fastpath' in (m or '') for (m, _) in calls['debug'])


def test_gui_fastpath_disabled(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    # Wire settings to disable fast-path
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    (settings_dir / 'settings.json').write_text('{"disable_placeholder_fastpath": true}')
    from prompt_automation import features
    # PROMPTS_DIR points at the styles folder (parent of Settings)
    monkeypatch.setattr(features, 'PROMPTS_DIR', settings_dir.parent, raising=False)

    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    calls = {'collect': 0, 'review': 0}
    orig_collect_build = controller.collect.build
    def spy_collect(*a, **k):
        calls['collect'] += 1
        return orig_collect_build(*a, **k)
    monkeypatch.setattr(controller.collect, 'build', spy_collect)
    orig_review_build = controller.review.build
    def spy_review(*a, **k):
        calls['review'] += 1
        return orig_review_build(*a, **k)
    monkeypatch.setattr(controller.review, 'build', spy_review)

    app = controller.SingleWindowApp()
    tmpl = {'id': 2, 'style': 'unit', 'title': 't', 'template':['Hi'], 'placeholders': []}
    app.advance_to_collect(tmpl)

    assert calls['collect'] == 1, 'collect.should be built when fast-path disabled'
    assert calls['review'] == 0
    assert app._stage == 'collect'


def test_gui_fastpath_keeps_non_empty_flow(monkeypatch):
    _install_tk(monkeypatch)
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    calls = {'collect': 0, 'review': 0}
    orig_collect_build = controller.collect.build
    def spy_collect(*a, **k):
        calls['collect'] += 1
        return orig_collect_build(*a, **k)
    monkeypatch.setattr(controller.collect, 'build', spy_collect)
    orig_review_build = controller.review.build
    def spy_review(*a, **k):
        calls['review'] += 1
        return orig_review_build(*a, **k)
    monkeypatch.setattr(controller.review, 'build', spy_review)

    app = controller.SingleWindowApp()
    tmpl = {'id': 3, 'style': 'unit', 'title':'t', 'template':['Hi {{n}}'], 'placeholders': [{'name': 'n'}]}
    app.advance_to_collect(tmpl)

    assert calls['collect'] == 1, 'collect.should be built for non-empty templates'
    assert calls['review'] == 0
    assert app._stage == 'collect'
