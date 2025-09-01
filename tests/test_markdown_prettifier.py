from prompt_automation.gui.single_window.formatting_helpers import format_markdown_plain


def test_markdown_plain_prettifier_basic():
    md = (
        "# Heading\n\n"
        "- [ ] unchecked item\n"
        "- [x] done item\n"
        "- bullet item\n\n"
        "```\ncode line\n```\n"
    )
    out = format_markdown_plain(md)
    # Heading hash removed
    assert '# ' not in out
    assert 'Heading' in out
    # Checkbox conversions
    assert '☐ unchecked item' in out
    assert '☑ done item' in out
    # Bullet symbol used
    assert '• bullet item' in out
    # Code fence removed; line indented
    assert 'code line' in out and '```' not in out
    # Horizontal rules become em dashes
    out2 = format_markdown_plain('---')
    assert '—' in out2

