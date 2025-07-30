from promptpilot.renderer import fill_placeholders


def test_fill_placeholders():
    lines = ["Hello {{NAME}}"]
    result = fill_placeholders(lines, {"NAME": "World"})
    assert result == "Hello World"
