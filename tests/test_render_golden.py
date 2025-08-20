import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import prompt_automation.menus as menus
import prompt_automation.variables as vars_mod


def test_render_pipeline_golden(tmp_path, monkeypatch):
    """Full render snapshot covering defaults, reminders, multi-file placeholders,
    list formatting, phrase removal and trimming."""
    # Set up globals with reminders and think_deeply auto append
    gdata = {
        'global_placeholders': {
            'think_deeply': 'THINK',
            'reminders': ['Remember A', 'Remember B'],
        }
    }
    (tmp_path / 'globals.json').write_text(json.dumps(gdata))

    # Route prompts dir to temp and change cwd so relative file paths resolve
    monkeypatch.setattr(menus, 'PROMPTS_DIR', tmp_path)
    monkeypatch.setattr(vars_mod, 'PROMPTS_DIR', tmp_path)
    monkeypatch.chdir(tmp_path)

    # File placeholders
    (tmp_path / 'ref.txt').write_text('REF CONTENT')
    (tmp_path / 'sec.txt').write_text('SEC CONTENT')

    tmpl = {
        'id': 1,
        'title': 'Golden',
        'style': 'Unit',
        'template': [
            'Hello {{name}}',
            '',
            'Tasks:',
            '{{tasks}}',
            '',
            'Optional: {{optional_line}}',
            'Reference file path: {{reference_file_path}}',
            'Reference file content: {{reference_file}}',
            'Secondary path: {{secondary_file_path}}',
            'Secondary content: {{secondary_file}}',
        ],
        'placeholders': [
            {'name': 'name', 'default': 'World'},
            {'name': 'tasks', 'format': 'checklist'},
            {'name': 'reference_file', 'type': 'file'},
            {'name': 'secondary_file', 'type': 'file'},
            {'name': 'optional_line', 'remove_if_empty': 'Optional:'},
        ],
        'global_placeholders': {},
    }

    rendered = menus.render_template(
        tmpl,
        values={
            'tasks': ['task one', 'task two'],
            'reference_file': 'ref.txt',
            'secondary_file': 'sec.txt',
            'optional_line': '',
        },
    )

    expected = """Hello World

Tasks:
- [ ] task one
- [ ] task two

Reference file path: ref.txt
Reference file content: REF CONTENT
Secondary path: sec.txt
Secondary content: SEC CONTENT

Reminders:
> - Remember A
> - Remember B

THINK"""
    assert rendered == expected
