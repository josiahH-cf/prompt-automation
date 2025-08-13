import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import prompt_automation.menus as menus


def _base_template():
    return {
        'id': 1,
        'title': 'Test',
        'style': 'Unit',
        'template': ['Hello {{name}}', '', 'Body', '{{extra}}'],
        'placeholders': [
            {'name': 'name', 'default': 'World'},
            {'name': 'extra', 'default': ''},
        ],
        'global_placeholders': {}
    }


def test_default_fallback_applies_when_empty():
    tmpl = _base_template()
    rendered = menus.render_template(tmpl, values={'name': ''})
    assert 'Hello World' in rendered  # default substituted


def test_default_not_used_when_value_present():
    tmpl = _base_template()
    rendered = menus.render_template(tmpl, values={'name': 'Alice'})
    assert 'Hello Alice' in rendered
    assert 'World' not in rendered


def test_reminders_single_string_appended(tmp_path, monkeypatch):
    # Create globals.json with single reminder
    globals_json = tmp_path / 'globals.json'
    globals_json.write_text('{"global_placeholders": {"reminders": "Remember to be concise"}}')
    monkeypatch.setattr(menus, 'PROMPTS_DIR', tmp_path)
    import prompt_automation.variables as vars_mod
    monkeypatch.setattr(vars_mod, 'PROMPTS_DIR', tmp_path)
    tmpl = _base_template()
    rendered = menus.render_template(tmpl, values={'name': ''})
    assert 'Reminders:' in rendered
    assert '> - Remember to be concise' in rendered


def test_reminders_array_appended(tmp_path, monkeypatch):
    globals_json = tmp_path / 'globals.json'
    globals_json.write_text('{"global_placeholders": {"reminders": ["First", "Second"]}}')
    monkeypatch.setattr(menus, 'PROMPTS_DIR', tmp_path)
    import prompt_automation.variables as vars_mod
    monkeypatch.setattr(vars_mod, 'PROMPTS_DIR', tmp_path)
    tmpl = _base_template()
    rendered = menus.render_template(tmpl, values={'name': ''})
    assert '> - First' in rendered and '> - Second' in rendered


def test_no_reminders_when_none(tmp_path, monkeypatch):
    globals_json = tmp_path / 'globals.json'
    globals_json.write_text('{"global_placeholders": {"importance": "normal"}}')
    monkeypatch.setattr(menus, 'PROMPTS_DIR', tmp_path)
    import prompt_automation.variables as vars_mod
    monkeypatch.setattr(vars_mod, 'PROMPTS_DIR', tmp_path)
    tmpl = _base_template()
    rendered = menus.render_template(tmpl, values={'name': ''})
    assert 'Reminders:' not in rendered
