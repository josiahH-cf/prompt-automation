import sys, types
from pathlib import Path

# Ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


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


def test_headless_classifies_reminder_and_link(monkeypatch):
    _install_headless_tk(monkeypatch)
    from prompt_automation.gui.single_window.frames import collect

    template = {
        'id': 99,
        'title': 'Demo',
        'placeholders': [
            # Reminder-only via heuristic (name prefix)
            {'name': 'reminder_open', 'label': 'Open personal email, Todoist, and this app in a view'},
            # Link placeholder (explicit)
            {'name': 'help_link', 'label': 'Review Guide', 'type': 'link', 'url': 'https://example.com/review'},
            # Regular input
            {'name': 'summary', 'label': 'Summary', 'multiline': True},
        ],
    }
    view = collect.build(types.SimpleNamespace(root=None), template)

    # Headless meta describes field kinds
    meta = getattr(view, 'placeholders_meta', {})
    assert meta.get('reminder_open', {}).get('kind') == 'reminder'
    assert meta.get('help_link', {}).get('kind') == 'link'
    assert meta.get('summary', {}).get('kind', 'input') == 'input'

    # Link binding should resolve to the configured URL
    assert 'help_link' in view.bindings
    assert callable(view.bindings['help_link']['get'])
    assert view.bindings['help_link']['get']() == 'https://example.com/review'

    # Reminder binding returns empty string (no input value)
    assert 'reminder_open' in view.bindings
    assert view.bindings['reminder_open']['get']() == ''

