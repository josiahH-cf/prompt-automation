import sys
from pathlib import Path
_here = Path(__file__).resolve()
for parent in _here.parents:
    candidate = parent / 'src' / 'prompt_automation'
    if candidate.is_dir():
        sys.path.insert(0, str(parent / 'src'))
        break
from prompt_automation.renderer import fill_placeholders

def test_line_with_only_empty_placeholder_removed():
    lines = ["Intro", "{{a}}", "Outro"]
    out = fill_placeholders(lines, {"a": ""})
    assert out.splitlines() == ["Intro", "Outro"], out


def test_line_with_multiple_all_empty_placeholders_removed():
    lines = ["Before", "  {{a}} {{b}}  ", "After"]
    out = fill_placeholders(lines, {"a": None, "b": "  "})
    assert out.splitlines() == ["Before", "After"], out


def test_line_mixed_text_not_removed_when_placeholder_empty():
    lines = ["Value: {{a}}"]
    out = fill_placeholders(lines, {"a": ""})
    # Line retained but token gone
    assert out == "Value: ", out


def test_indented_multiline_expansion_and_empty_skip():
    lines = ["- Header", "  {{body}}", "- Next", "  {{next_body}}"]
    body_text = "Item1\nItem2"
    out = fill_placeholders(lines, {"body": body_text, "next_body": ""})
    parts = out.splitlines()
    # Second block header/body removed (empty body)
    assert "- Next" not in parts
    # Multiline indentation preserved for first body
    assert parts[1] == "  Item1"
    assert parts[2] == "  Item2"


def test_header_removed_when_body_empty_first_section():
    lines = ["- Header1", "  {{body1}}", "- Header2", "  {{body2}}"]
    out = fill_placeholders(lines, {"body1": "", "body2": "Value"})
    parts = out.splitlines()
    assert "- Header1" not in parts  # removed because its body empty
    assert "- Header2" in parts
    assert parts[-1] == "  Value"


def test_alt_bullet_styles_removed_when_body_empty():
    lines = ["* StarHeader", "  {{a}}", "• DotHeader", "  {{b}}", "1. NumHeader", "  {{c}}", "2) NumParen", "  {{d}}"]
    out = fill_placeholders(lines, {"a": "", "b": "", "c": "", "d": ""})
    assert "* StarHeader" not in out
    assert "• DotHeader" not in out
    assert "1. NumHeader" not in out
    assert "2) NumParen" not in out


def test_whitespace_only_replacement_treated_as_empty():
    lines = ["{{a}}", "End"]
    out = fill_placeholders(lines, {"a": "   \t  "})
    assert out.splitlines() == ["End"], out
