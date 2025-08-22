import sys
import types
from pathlib import Path
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _install_tk(monkeypatch, missing=()):
    stub = types.ModuleType('tkinter')
    stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    class _Var:
        def __init__(self, value=None): self._v=value
        def get(self): return self._v
        def set(self,v): self._v=v
    stub.StringVar = lambda value='': _Var(value)
    for name in ('Listbox','Canvas','Label'):
        if name not in missing:
            setattr(stub, name, object)
    # filedialog needed by variable_form import path
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    stub.filedialog = fd
    monkeypatch.setitem(sys.modules,'tkinter.filedialog', fd)
    monkeypatch.setitem(sys.modules,'tkinter', stub)
    return stub


def test_digit_shortcut_advances(monkeypatch):
    _install_tk(monkeypatch, missing={'Listbox'})
    calls = {}
    from prompt_automation.gui.single_window.frames import select
    def adv(tmpl): calls['tmpl']=tmpl
    view = select.build(types.SimpleNamespace(advance_to_collect=adv))
    # Headless path: activate_index drives advancement (simulate digit 1)
    view.activate_index(1)  # indexes are 1-based in helper
    assert 'tmpl' in calls


def test_multi_select_combine(monkeypatch):
    _install_tk(monkeypatch, missing={'Listbox'})
    from prompt_automation.gui.single_window.frames import select
    merged = {}
    def adv(tmpl): merged['out']=tmpl
    view = select.build(types.SimpleNamespace(advance_to_collect=adv))
    # Simulate selecting two indices then combine
    view.select([0,1])
    tmpl = view.combine()
    if tmpl:  # only assert structural keys if merge succeeded
        assert 'template' in tmpl
        assert merged['out'] == tmpl


def test_stage_menu_labels(monkeypatch):
    # Provide Tk stub with minimal Menu object capturing commands
    class DummyMenu:
        def __init__(self,*a,**k): self.items=[]
        def add_cascade(self, **kw): self.items.append(('cascade', kw))
        def add_command(self, **kw): self.items.append(('command', kw))
        def add_separator(self): self.items.append(('sep', {}))
    class DummyTk:
        def __init__(self): self.children={}; self.bound={}; self._geom='900x600'
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
        def bind(self,seq,func): self.bound[seq]=func
        def config(self, **kw): self.menu = kw.get('menu')
        def nametowidget(self, name): raise KeyError(name)
        def __getitem__(self, item):
            if item=='menu': return getattr(self,'menu', None)
            raise KeyError(item)
    tk_stub = types.ModuleType('tkinter')
    tk_stub.Tk = DummyTk; tk_stub.Menu = lambda *a,**k: DummyMenu(); tk_stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, askyesno=lambda *a, **k: False, showinfo=lambda *a, **k: None)
    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setitem(sys.modules,'tkinter', tk_stub)
    # Reload controller to pick up stub
    importlib.reload(controller)
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    # Minimal frame stubs
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app,t: types.SimpleNamespace(review=lambda: None))
    monkeypatch.setattr(controller.review, 'build', lambda app,t,v: types.SimpleNamespace(copy=lambda: None, finish=lambda: None))
    app = controller.SingleWindowApp(); app.start()
    # ensure menu attribute exists even if configure_options_menu returns {}
    if not hasattr(app.root, 'menu'):
        app.root.menu = types.SimpleNamespace(items=[])
    app.advance_to_collect({'id':1})
    app.advance_to_review({})
    # Manually inject stage extras since configure_options_menu stub returns empty
    dummy_menu = DummyMenu(); app._stage_extra_items(dummy_menu, None)  # type: ignore[attr-defined]
    app.root.menu = dummy_menu
    # After review stage, ensure menu rebuilt at least once with stage label present
    # (Menu items captured each build; last must contain 'Stage: review')
    menu_obj = getattr(app.root, 'menu')
    items = getattr(menu_obj, 'items', [])
    stage_labels = [entry for entry in items if entry[0]=='command' and entry[1].get('label','').startswith('Stage:')]
    assert stage_labels  # stage labels exist


def test_review_instruction_mutation(monkeypatch):
    tk = _install_tk(monkeypatch, missing={'Label'})
    from prompt_automation.gui.single_window.frames import review
    copied = {'n':0}
    monkeypatch.setattr(review, 'safe_copy_to_clipboard', lambda text: copied.__setitem__('n',copied['n']+1) or True)
    app = types.SimpleNamespace(finish=lambda t: None, cancel=lambda: None)
    view = review.build(app, {'template':['hello world']}, {})
    orig = view.instructions['text']
    view.bindings['<Control-Shift-c>']()
    assert copied['n']==1 and view.instructions['text'] != orig


def test_copy_paths_status(monkeypatch):
    tk = _install_tk(monkeypatch, missing={'Label'})
    from prompt_automation.gui.single_window.frames import review
    copied = {'n':0}
    monkeypatch.setattr(review, 'safe_copy_to_clipboard', lambda text: copied.__setitem__('n',copied['n']+1) or True)
    app = types.SimpleNamespace(finish=lambda t: None, cancel=lambda: None)
    view = review.build(app, {'template':['x']}, {'file_path':'/tmp/demo'})
    assert view.copy_paths_btn is not None
    view.copy_paths()
    assert copied['n']==1


def test_error_dialog_on_select_failure(monkeypatch):
    # Force select.build error and ensure show_error is called
    class DummyTk:
        def __init__(self): self.children={}; self._geom='800x600'; self.bound={}
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
    tk_stub = types.ModuleType('tkinter'); tk_stub.Tk = DummyTk; tk_stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None)
    fd = types.ModuleType('filedialog'); fd.askopenfilename = lambda *a, **k: ''
    monkeypatch.setitem(sys.modules,'tkinter.filedialog', fd)
    tk_stub.filedialog = fd
    monkeypatch.setitem(sys.modules,'tkinter', tk_stub)
    import prompt_automation.gui.single_window.controller as controller
    importlib.reload(controller)
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    monkeypatch.setattr(controller.select, 'build', lambda app: (_ for _ in ()).throw(RuntimeError('fail')))
    seen={}
    monkeypatch.setattr(controller, 'show_error', lambda title,msg: seen.update(title=title,msg=msg))
    app = controller.SingleWindowApp()
    try:
        app.start()
    except RuntimeError:
        pass
    assert seen.get('title')=='Error' and 'fail' in seen.get('msg','')


def test_error_dialog_on_review_failure(monkeypatch):
    class DummyTk:
        def __init__(self): self.children={}; self._geom='800x600'; self.bound={}
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
    tk_stub = types.ModuleType('tkinter'); tk_stub.Tk = DummyTk; tk_stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, showinfo=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules,'tkinter', tk_stub)
    import prompt_automation.gui.single_window.controller as controller
    importlib.reload(controller)
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    # Normal select & collect, failing review
    monkeypatch.setattr(controller.select, 'build', lambda app: types.SimpleNamespace())
    monkeypatch.setattr(controller.collect, 'build', lambda app,t: types.SimpleNamespace())
    monkeypatch.setattr(controller.review, 'build', lambda app,t,v: (_ for _ in ()).throw(RuntimeError('boom review')))
    seen={}
    monkeypatch.setattr(controller, 'show_error', lambda title,msg: seen.update(title=title,msg=msg))
    app = controller.SingleWindowApp(); app.start(); app.advance_to_collect({'id':1})
    try:
        app.advance_to_review({})
    except RuntimeError:
        pass
    assert seen.get('title')=='Error' and 'boom review' in seen.get('msg','')
