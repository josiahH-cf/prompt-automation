import sys, types
from pathlib import Path

# tests/ is one level below repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def _install_headless_tk(monkeypatch):
    """Install a minimal tkinter stub without Canvas to force headless path."""
    stub = types.ModuleType('tkinter')
    # Intentionally do not provide Canvas to trigger headless branch
    stub.Frame = object
    stub.Text = object
    stub.Entry = object
    stub.Scrollbar = object
    stub.Button = object
    stub.Label = object
    stub.StringVar = lambda value='': types.SimpleNamespace(get=lambda: value, set=lambda v: None)
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    # Provide filedialog submodule for variable_form import
    fd = types.ModuleType('tkinter.filedialog')
    fd.askopenfilename = lambda *a, **k: ''
    monkeypatch.setitem(sys.modules, 'tkinter.filedialog', fd)


def test_no_reference_picker_when_placeholder_absent(monkeypatch):
    _install_headless_tk(monkeypatch)
    from prompt_automation.gui.single_window.frames import collect
    template = {
        'id': 1,
        'title': 'T',
        'placeholders': [
            {'name': 'summary', 'label': 'Summary', 'multiline': True},
        ],
    }
    view = collect.build(types.SimpleNamespace(root=None), template)
    # In headless branch, bindings should NOT include global reference UI unless required
    assert '_global_reference' not in view.bindings


def test_reference_picker_present_when_placeholder_exists(monkeypatch):
    _install_headless_tk(monkeypatch)
    from prompt_automation.gui.single_window.frames import collect
    template = {
        'id': 1,
        'title': 'T',
        'placeholders': [
            {'name': 'summary', 'label': 'Summary', 'multiline': True},
            {'name': 'reference_file', 'label': 'Reference File', 'type': 'file'},
        ],
    }
    view = collect.build(types.SimpleNamespace(root=None), template)
    assert '_global_reference' in view.bindings
