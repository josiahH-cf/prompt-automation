import sys, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def test_select_stage_focuses_listbox_and_type_redirects(monkeypatch):
    # Minimal tkinter root stub
    class Root:
        def __init__(self):
            self.children={}
            self.bound={}
            self._geom='100x100'
        def title(self,*a,**k): pass
        def geometry(self,g=None): return self._geom
        def minsize(self,*a,**k): pass
        def resizable(self,*a,**k): pass
        def protocol(self,*a,**k): pass
        def update_idletasks(self): pass
        def winfo_geometry(self): return self._geom
        def winfo_exists(self): return True
        def bind(self, seq, func): self.bound[seq]=func
        def after(self, delay, cb): cb()
        def lift(self): pass
        def focus_force(self): pass
        def attributes(self,*a,**k): pass
    tk = types.ModuleType('tkinter')
    tk.Tk = Root
    tk.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None)
    tk.filedialog = types.SimpleNamespace(askopenfilename=lambda *a, **k: '')
    monkeypatch.setitem(sys.modules,'tkinter', tk)

    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu,'configure_options_menu',lambda *a,**k: {})

    class MockWidget:
        def __init__(self): self.focused=0; self.text=''
        def focus_set(self): self.focused+=1
        def insert(self, where, ch): self.text+=ch
        def event_generate(self,*a,**k): pass
    class MockList(MockWidget): pass
    entry = MockWidget(); lst=MockList()

    def fake_build(app):
        app._select_query_entry = entry
        app._select_listbox = lst
        return types.SimpleNamespace()

    monkeypatch.setattr(controller.select,'build',fake_build)

    app = controller.SingleWindowApp(); app.start()
    assert lst.focused>=1
    class E: char='a'
    handler = app.root.bound.get('<Key>')
    assert handler is not None
    handler(E())
    assert entry.focused>=1 and 'a' in entry.text
