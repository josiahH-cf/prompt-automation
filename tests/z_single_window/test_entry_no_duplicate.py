import types
import sys


def test_no_double_insertion_when_entry_has_focus(monkeypatch):
    # Tk root stub with focus tracking
    class Root:
        def __init__(self):
            self.children = {}
            self.bound = {}
            self._geom = '100x100'
            self._focus = None
        def title(self,*a,**k): pass
        def geometry(self,g=None): return self._geom
        def minsize(self,*a,**k): pass
        def resizable(self,*a,**k): pass
        def protocol(self,*a,**k): pass
        def update_idletasks(self): pass
        def winfo_geometry(self): return self._geom
        def winfo_exists(self): return True
        def bind(self, seq, func): self.bound[seq] = func
        def after(self, delay, cb): cb()
        def lift(self): pass
        def focus_force(self): pass
        def attributes(self,*a,**k): pass
        def focus_get(self): return self._focus

    tk = types.ModuleType('tkinter')
    tk.Tk = Root
    tk.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None)
    tk.filedialog = types.SimpleNamespace(askopenfilename=lambda *a, **k: '')
    monkeypatch.setitem(sys.modules, 'tkinter', tk)

    import prompt_automation.gui.single_window.controller as controller
    monkeypatch.setattr(controller.options_menu, 'configure_options_menu', lambda *a, **k: {})

    class MockWidget:
        def __init__(self, root):
            self._root = root
            self.focused = 0
            self.text = ''
        def focus_set(self):
            self.focused += 1
            self._root._focus = self
        def insert(self, where, ch):
            self.text += ch
        def event_generate(self, *a, **k):
            pass

    class MockList(MockWidget):
        pass

    # Prepare mocks wired into controller
    root_ref = None
    entry = MockWidget(None)
    lst = MockList(None)

    def fake_build(app):
        # Update root for widgets now that app.root exists
        nonlocal root_ref, entry, lst
        root_ref = app.root
        entry._root = root_ref
        lst._root = root_ref
        app._select_query_entry = entry
        app._select_listbox = lst
        return types.SimpleNamespace()

    monkeypatch.setattr(controller.select, 'build', fake_build)

    app = controller.SingleWindowApp(); app.start()
    handler = app.root.bound.get('<Key>')
    assert handler is not None

    # When entry has focus, our handler should not duplicate insertion
    entry.focus_set()
    # Simulate default Tk insertion
    entry.insert('end', 'a')
    before = entry.text
    handler(types.SimpleNamespace(char='a'))
    assert entry.text == before  # no duplicate

    # When listbox has focus, the handler should move focus and insert once
    entry.text = ''
    lst.focus_set()
    handler(types.SimpleNamespace(char='b'))
    assert entry.text == 'b' and entry.focused >= 1

