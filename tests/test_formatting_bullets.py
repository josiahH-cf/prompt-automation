import sys
from pathlib import Path

# tests/ is one level below repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def test_next_line_prefix_bullet_basic():
    # Expect '- ' inserted after a non-empty bullet line
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("- Do thing", "bullet") == "- "


def test_next_line_prefix_bullet_blank_line_no_prefix():
    # Two consecutive Enters on an empty bullet should not keep inserting dashes
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("- ", "bullet") == ""


def test_next_line_prefix_checklist():
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("- [ ] Task", "checklist") == "- [ ] "


def test_next_line_prefix_non_list_no_prefix():
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("Hello world", "bullet") == ""
    assert next_line_prefix("Hello world", "checklist") == ""


def test_next_line_prefix_indented_bullet():
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("    - Do thing", "bullet") == "- "


def test_next_line_prefix_checklist_without_trailing_space_normalizes():
    from prompt_automation.gui.single_window.formatting_helpers import next_line_prefix
    assert next_line_prefix("- [ ]Task", "checklist") == "- [ ] "
