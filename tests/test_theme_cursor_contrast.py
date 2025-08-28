from prompt_automation.theme import model as tmodel


def test_dark_mode_cursor_is_white():
    """The text insertion cursor should be high-contrast white in dark mode.

    We validate via a pure function to avoid requiring a Tk root in tests.
    """
    dark = tmodel.get_theme('dark')
    # Function to be implemented in theme.apply; current code lacks it (red first)
    from prompt_automation.theme import apply as tap
    assert hasattr(tap, 'get_cursor_color'), 'missing get_cursor_color API'
    color = tap.get_cursor_color(dark)
    assert color.lower() == '#ffffff'

