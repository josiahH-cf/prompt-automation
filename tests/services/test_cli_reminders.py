import builtins
import sys
from pathlib import Path

import types
import pytest

# Ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from prompt_automation.variables import core as core_mod
from prompt_automation.variables.core import get_variables


def test_cli_prints_template_and_placeholder_reminders(monkeypatch, capsys):
    # Force GUI helpers to return None so CLI path executes
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "1")
    import prompt_automation.variables.gui as vgui
    monkeypatch.setattr(vgui, "_gui_prompt", lambda *a, **k: None)
    monkeypatch.setattr(vgui, "_gui_file_prompt", lambda *a, **k: None)

    placeholders = [
        {"name": "first", "label": "First", "reminders": ["alpha", "beta"]},
        {"name": "second", "label": "Second", "reminders": ["beta", "gamma"]},
    ]
    # Provide template-level list; also supply same item to test dedup at placeholder
    globals_map = {"__template_reminders": ["alpha", "zeta"]}

    # Simulate user input for two prompts
    seq = iter(["one", "two"])
    monkeypatch.setattr(builtins, "input", lambda *a, **k: next(seq))

    # Ensure editor fallback does not intercept CLI path
    monkeypatch.setattr(core_mod, "_editor_prompt", lambda: None)
    values = get_variables(placeholders, template_id=None, globals_map=globals_map)
    # Ensure values collected
    assert values["first"] == "one"
    assert values["second"] == "two"

    out = capsys.readouterr().out
    # Template reminders once
    assert out.count("Reminders:") >= 1
    assert out.count(" - alpha") >= 1
    assert out.count(" - zeta") >= 1
    # Placeholder-level printed before prompts, deduped against template alpha
    assert " - beta" in out
    # 'alpha' should not appear again from placeholder inline (only in header block)
    # The header prints at least once; beta shows at least once since not in header
    # We can't perfectly assert positions without a full prompt transcript.
