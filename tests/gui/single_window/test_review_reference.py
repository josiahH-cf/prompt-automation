import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))


def _install_headless_tk(monkeypatch):
    stub = types.ModuleType('tkinter')
    # Omit Label to trigger headless path
    stub.Frame = object
    stub.Text = object
    stub.Scrollbar = object
    stub.Button = object
    stub.StringVar = lambda value='': types.SimpleNamespace(get=lambda: value, set=lambda v: None)
    stub.Toplevel = object
    monkeypatch.setitem(sys.modules, 'tkinter', stub)
    # messagebox stub used in headless finish
    mb = types.SimpleNamespace(askyesno=lambda *a, **k: False)
    monkeypatch.setitem(sys.modules, 'tkinter.messagebox', mb)
    # filedialog stub required by services.variable_form import path
    fd = types.ModuleType('tkinter.filedialog')
    fd.askopenfilename = lambda *a, **k: ''
    monkeypatch.setitem(sys.modules, 'tkinter.filedialog', fd)


def test_review_exposes_view_reference_headless(monkeypatch, tmp_path):
    _install_headless_tk(monkeypatch)
    from prompt_automation.gui.single_window.frames import review

    # Create a small file and pass its path as reference_file
    ref = tmp_path / 'ref.txt'
    ref.write_text('hello')

    template = {'template': ['X {{a}}']}
    variables = {'a': '1', 'reference_file': str(ref)}
    view = review.build(types.SimpleNamespace(root=None, finish=lambda *_: None, cancel=lambda *_: None), template, variables)

    # Headless path should expose a callable to view the reference; ensure it exists and does not raise
    assert getattr(view, 'view_reference', None) is not None
    view.view_reference()


def test_review_no_view_reference_when_absent(monkeypatch):
    _install_headless_tk(monkeypatch)
    from prompt_automation.gui.single_window.frames import review
    template = {'template': ['X']}
    variables = {'a': '1'}
    view = review.build(types.SimpleNamespace(root=None, finish=lambda *_: None, cancel=lambda *_: None), template, variables)
    assert getattr(view, 'view_reference', None) is None
