import json
from pathlib import Path

from prompt_automation.gui.single_window.frames import review as review_frame


class _DummyApp:
    def finish(self, *_):
        pass

    def cancel(self, *_):
        pass


def test_headless_reference_viewer_prettifies(tmp_path, monkeypatch):
    # Ensure we take the headless path used in other tests by stubbing tkinter
    import sys, types
    tk_stub = types.SimpleNamespace()  # lacks Label attribute
    # Replace tkinter with a stub for this test so build() takes the headless path
    monkeypatch.setitem(sys.modules, 'tkinter', tk_stub)

    md = tmp_path / 'ref.md'
    md.write_text('# Title\n\n- [ ] todo\n- item\n')

    tmpl = {
        'schema': 1,
        'id': 99,
        'title': 't',
        'style': 'unit',
        'template': ['{{reference_file}}'],
        'placeholders': [
            {'name': 'reference_file', 'type': 'file', 'label': 'Ref', 'render': 'markdown'}
        ],
        'metadata': {'path': 'unit/test.json'}
    }

    app = _DummyApp()
    ns = review_frame.build(app, tmpl, {'reference_file': str(md)})
    # view_reference should be present and return prettified text
    assert getattr(ns, 'view_reference') is not None
    content = ns.view_reference()
    assert isinstance(content, str)
    assert 'Title' in content and '• item' in content and '☐ todo' in content
