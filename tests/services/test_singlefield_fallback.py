import json
from prompt_automation.menus import render_template

def test_singlefield_fallback_substitution():
    tmpl = json.load(open('src/prompt_automation/prompts/styles/Code/01_todoist_task.json'))
    # Intentionally pass capture with trailing spaces to simulate user input edge
    rendered = render_template(tmpl, {'capture': 'Budget review Q4  '})
    assert '{{title}}' not in rendered
    assert 'Budget review Q4' in rendered or 'Draft budget review Q4' in rendered
    # No scaffold when AC absent
    assert 'Acceptance Criteria' not in rendered
    # Default p3 priority bracket present
    assert ' [p3]' in rendered