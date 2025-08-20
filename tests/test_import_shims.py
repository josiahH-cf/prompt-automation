import importlib
import sys
from pathlib import Path

import tkinter
import pytest

# ensure package import from source
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

LEGACY_MODULES = [
    'prompt_automation.hotkeys',
    'prompt_automation.gui.template_selector',
    'prompt_automation.gui.new_template_wizard',
    'prompt_automation.gui.single_window',
    'prompt_automation.gui.collector.prompts',
    'prompt_automation.gui.selector.view',
]


@pytest.mark.parametrize('mod_path', LEGACY_MODULES)
def test_import_shims(mod_path):
    assert tkinter._default_root is None
    module = importlib.import_module(mod_path)
    assert module is not None
    assert tkinter._default_root is None
