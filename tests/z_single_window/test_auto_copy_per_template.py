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


def test_per_template_disable(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    # Global auto-copy enabled, template not disabled yet
    settings_file.write_text(json.dumps({'auto_copy_review': True}))

    from prompt_automation.variables import storage
    monkeypatch.setattr(storage, '_SETTINGS_DIR', settings_dir, raising=False)
    monkeypatch.setattr(storage, '_SETTINGS_FILE', settings_file, raising=False)

    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app, t: types.SimpleNamespace(review=lambda: None))
    # Patch review used in controller
    calls = {'copy':0}
    monkeypatch.setattr(controller.review, 'safe_copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or True)
    monkeypatch.setattr(controller.review, 'copy_to_clipboard', lambda text: calls.__setitem__('copy', calls['copy']+1) or None)

    app = controller.SingleWindowApp()
    template = {'id': 42, 'style': 'x', 'template':['abc']}
    app.template = template
    app.advance_to_review({})
    # Headless path skips auto-copy; expect zero until explicit finish
    assert calls['copy'] == 0

    # Now disable for template and re-enter review; should not auto-copy
    storage.set_template_auto_copy_disabled(42, True)
    calls2 = {'copy':0}
    monkeypatch.setattr(controller.review, 'safe_copy_to_clipboard', lambda text: calls2.__setitem__('copy', calls2['copy']+1) or True)
    monkeypatch.setattr(controller.review, 'copy_to_clipboard', lambda text: calls2.__setitem__('copy', calls2['copy']+1) or None)
    # Simulate finishing then starting again
    app.finish('abc')  # cycles back to select
    # Set template again and go to review
    app.template = template
    app.advance_to_review({})
    assert calls2['copy'] == 0

    # Re-enable by removing disable entry
    storage.set_template_auto_copy_disabled(42, False)
    calls3 = {'copy':0}
    monkeypatch.setattr(controller.review, 'safe_copy_to_clipboard', lambda text: calls3.__setitem__('copy', calls3['copy']+1) or True)
    monkeypatch.setattr(controller.review, 'copy_to_clipboard', lambda text: calls3.__setitem__('copy', calls3['copy']+1) or None)
    app.finish('abc')
    app.template = template
    app.advance_to_review({})
    assert calls3['copy'] == 0
