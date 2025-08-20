import importlib
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))


def test_import_without_tk():
    sys.modules.pop('prompt_automation.gui.collector.components.orchestrator', None)

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name.startswith('tkinter'):
            raise AssertionError('tkinter imported at module level')
        return real_import(name, *args, **kwargs)

    with mock.patch('builtins.__import__', side_effect=fake_import):
        importlib.import_module('prompt_automation.gui.collector.components.orchestrator')
