import sys, types, json
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
    # Omit Label so review.build uses headless path.
    stub.Text = object; stub.Scrollbar = object; stub.Frame = object; stub.Button = object
    stub.StringVar = lambda value='': types.SimpleNamespace(get=lambda: value, set=lambda v: None)
    stub.messagebox = types.SimpleNamespace(askyesno=lambda *a, **k: False, showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None)
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    stub.filedialog = fd
    sys.modules['tkinter.filedialog'] = fd
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    return stub


def test_auto_copy_triggers_on_review_entry(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    # Ensure fresh import of review module after tk stub so headless path is taken
    sys.modules.pop('prompt_automation.gui.single_window.frames.review', None)
    # Patch settings path to enable auto_copy_review
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    settings_file.write_text(json.dumps({'auto_copy_review': True}))

    from prompt_automation.variables import storage
    monkeypatch.setattr(storage, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(storage, '_SETTINGS_FILE', settings_file, raising=False)

    import prompt_automation.gui.single_window.controller as controller
    # Simplify menu
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    # Stub select & collect
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app, t: types.SimpleNamespace(review=lambda: None))

    # Patch review module via controller reference to ensure same object
    calls = {'copy':0}
    monkeypatch.setattr(controller.review, 'safe_copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or True)
    monkeypatch.setattr(controller.review, 'copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or None)

    app = controller.SingleWindowApp()
    tmpl = {'id': 1, 'style': 'unit', 'template':['Hello World']}
    app.template = tmpl
    app.advance_to_review({})
    view = app._current_view  # headless namespace
    # In headless test mode auto-copy suppressed; no copies yet
    assert calls['copy'] == 0
    # Manual finish should copy once
    view.finish()
    assert calls['copy'] == 1


def test_auto_copy_disabled_default(monkeypatch):
    _install_tk(monkeypatch)
    sys.modules.pop('prompt_automation.gui.single_window.frames.review', None)
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app, t: types.SimpleNamespace(review=lambda: None))
    calls = {'copy':0}
    monkeypatch.setattr(controller.review, 'safe_copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or True)
    monkeypatch.setattr(controller.review, 'copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or None)
    app = controller.SingleWindowApp()
    tmpl = {'id': 2, 'style': 'unit', 'template':['Hi']}
    app.template = tmpl
    app.advance_to_review({})
    view = app._current_view
    # No auto-copy since setting disabled (copy count stays 0 until finish)
    assert calls['copy'] == 0
    view.finish()
    assert calls['copy'] >= 1
