import json
from pathlib import Path
from prompt_automation.menus import render_template


def test_singlefield_render_replaces_tokens(tmp_path):
    # Copy template into temp prompts dir to simulate normal loading if needed
    source = Path('src/prompt_automation/prompts/styles/Code/01_todoist_task.json')
    tmpl = json.loads(source.read_text())
    rendered = render_template(tmpl, {'capture': 'Email the board with Q3 forecast p1 due: today 4pm ac: Include revenue'})
    assert '{{title}}' not in rendered
    assert '{{priority}}' not in rendered
    assert 'Email the board with Q3 forecast' in rendered
    assert 'Include revenue' in rendered
    assert ' [p1]' in rendered  # explicit priority rendered


def test_singlefield_render_omits_optional_fields():
    source = Path('src/prompt_automation/prompts/styles/Code/01_todoist_task.json')
    tmpl = json.loads(source.read_text())
    rendered = render_template(tmpl, {'capture': 'Decide vendor shortlist p2'})
    # explicit p2 shows
    assert ' [p2]' in rendered
    # due backfilled (end of week wording may resolve to something like 'Friday')
    assert 'due:' in rendered
    # acceptance omitted
    assert 'Acceptance Criteria' not in rendered
    assert 'Decide vendor shortlist' in rendered


def test_singlefield_render_omits_priority_block_for_default():
    source = Path('src/prompt_automation/prompts/styles/Code/01_todoist_task.json')
    tmpl = json.loads(source.read_text())
    rendered = render_template(tmpl, {'capture': 'Draft release notes outline'})
    # Default p3 still shown
    assert ' [p3]' in rendered
    # acceptance omitted
    assert 'Acceptance Criteria' not in rendered
    assert 'release notes outline' in rendered