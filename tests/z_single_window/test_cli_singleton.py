import sys
import types
from pathlib import Path
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


def _install_tk(monkeypatch):
    class DummyTk:
        def __init__(self):
            self.children = {}
        def title(self,*a,**k): pass
        def geometry(self,*a,**k): return '100x100'
        def minsize(self,*a,**k): pass
        def resizable(self,*a,**k): pass
        def protocol(self,*a,**k): pass
        def update_idletasks(self): pass
        def winfo_geometry(self): return '100x100'
        def winfo_exists(self): return True
        def quit(self): pass
        def destroy(self): pass
        def bind(self, *a, **k): pass
        def lift(self): pass
        def focus_force(self): pass
        def attributes(self, *a, **k): pass
        def after(self,*a,**k): pass
        def mainloop(self): pass
    tkmod = types.ModuleType('tkinter')
    tkmod.Tk = DummyTk
    tkmod.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    tkmod.filedialog = types.SimpleNamespace(askopenfilename=lambda *a, **k: '')
    tkmod.ttk = types.SimpleNamespace()
    tkmod.simpledialog = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'tkinter', tkmod)
    return tkmod


def _stub_env(monkeypatch, tmp_path):
    monkeypatch.setenv('PROMPT_AUTOMATION_SINGLETON_SOCKET', str(tmp_path / 'gui.sock'))


def test_cli_focuses_existing_instance(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    _stub_env(monkeypatch, tmp_path)
    # Provide minimal variable_form factory early
    sys.modules['prompt_automation.services.variable_form'] = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))

    # Import controller to create first instance
    import prompt_automation.gui.single_window.controller as sw_controller
    monkeypatch.setattr(sw_controller.options_menu, 'configure_options_menu', lambda *a, **k: {})
    app = sw_controller.SingleWindowApp()  # starts server
    app.start()

    # Count instantiations attempted during second run
    created = {'count': 0}
    import prompt_automation.gui.controller as gui_controller
    class Sentinal:
        def __init__(self):
            created['count'] += 1
        def run(self):
            return None, None
    monkeypatch.setattr(gui_controller.single_window, 'SingleWindowApp', Sentinal)

    # Patch heavy operations in CLI
    import prompt_automation.cli as cli_pkg
    monkeypatch.setattr(cli_pkg.PromptCLI, 'check_dependencies', staticmethod(lambda require_fzf=True: True))
    monkeypatch.setitem(cli_pkg.__dict__, 'check_dependencies', lambda require_fzf=True: True)
    monkeypatch.setattr(cli_pkg.updater, 'check_for_update', lambda: None, raising=False)
    monkeypatch.setattr(cli_pkg.update, 'check_and_prompt', lambda: None, raising=False)
    # Patch ensure_unique_ids invoked during CLI flow
    monkeypatch.setattr(cli_pkg, 'ensure_unique_ids', lambda *a, **k: None)

    # Run CLI with --gui (simulating hotkey launch)
    cli = cli_pkg.PromptCLI()
    cli.main(['--gui'])

    # Ensure no new instance created (focus path returned early)
    assert created['count'] == 0

    # Also test --focus explicit flag (should focus and not create)
    cli2 = cli_pkg.PromptCLI()
    cli2.main(['--focus'])
    assert created['count'] == 0


def test_cli_launches_instance_when_none_running(monkeypatch, tmp_path):
    _install_tk(monkeypatch)
    _stub_env(monkeypatch, tmp_path)
    sys.modules['prompt_automation.services.variable_form'] = types.SimpleNamespace(build_widget=lambda spec: (lambda parent: types.SimpleNamespace(focus_set=lambda: None), {'get': lambda: ''}))

    import prompt_automation.gui.single_window.controller as sw_controller
    monkeypatch.setattr(sw_controller.options_menu, 'configure_options_menu', lambda *a, **k: {})

    # Ensure no existing server by not instantiating first app
    created = {'count': 0}
    import prompt_automation.gui.controller as gui_controller
    base_cls = gui_controller.single_window.SingleWindowApp
    class Tracker(base_cls):  # type: ignore
        def __init__(self):
            created['count'] += 1
            super().__init__()
        def run(self):
            # Avoid blocking loop
            self.start()
            return None, None
    monkeypatch.setattr(gui_controller.single_window, 'SingleWindowApp', Tracker)

    # Patch CLI heavy ops
    import prompt_automation.cli as cli_pkg
    monkeypatch.setattr(cli_pkg.PromptCLI, 'check_dependencies', staticmethod(lambda require_fzf=True: True))
    monkeypatch.setitem(cli_pkg.__dict__, 'check_dependencies', lambda require_fzf=True: True)
    monkeypatch.setattr(cli_pkg.updater, 'check_for_update', lambda: None, raising=False)
    monkeypatch.setattr(cli_pkg.update, 'check_and_prompt', lambda: None, raising=False)
    monkeypatch.setattr(cli_pkg, 'ensure_unique_ids', lambda *a, **k: None)

    cli = cli_pkg.PromptCLI()
    cli.main(['--gui'])
    assert created['count'] == 1
