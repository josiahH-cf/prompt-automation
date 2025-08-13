import json
from pathlib import Path
from prompt_automation.menus import render_template
from prompt_automation.config import PROMPTS_DIR


def test_global_auto_injection(tmp_path, monkeypatch):
    # Fake prompts dir
    gdir = tmp_path
    monkeypatch.setattr('prompt_automation.menus.PROMPTS_DIR', gdir)
    monkeypatch.setattr('prompt_automation.variables.PROMPTS_DIR', gdir)
    # Write globals
    (gdir / 'globals.json').write_text(json.dumps({
        'type': 'globals',
        'global_placeholders': {
            'think_deeply': 'think deeply about this',
            'hallucinate': 'high',
            'reminders': ['Check facts']
        }
    }))
    # Template that uses hallucinate token but not think_deeply token
    tmpl_path = gdir / 'Style'
    tmpl_path.mkdir()
    tdata = {
        'id': 1,
        'title': 'Test',
        'style': 'Style',
        'template': ['Risk level: {{hallucinate}}'],
        'placeholders': []
    }
    # Render
    rendered = render_template(tdata)
    assert 'Risk level:' in rendered
    assert 'high' in rendered  # hallucinate auto injected
    assert 'think deeply about this' in rendered  # appended at end since token absent
    assert '> - Check facts' in rendered  # reminder block
