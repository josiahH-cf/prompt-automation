import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def test_legacy_gui_modules_import_no_side_effect():
    import tkinter
    assert tkinter._default_root is None

    # Legacy module paths should remain importable without creating a root window
    from prompt_automation.gui import single_window, new_template_wizard
    from prompt_automation.gui.collector import prompts
    from prompt_automation.gui.selector import view

    assert single_window is not None
    assert prompts is not None
    assert view is not None
    assert new_template_wizard is not None
    assert tkinter._default_root is None
