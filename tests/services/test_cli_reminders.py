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
    # Also patch the names imported into core so it doesn't invoke OS dialogs
    monkeypatch.setattr(core_mod, "_gui_prompt", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(core_mod, "_gui_file_prompt", lambda *a, **k: None, raising=False)

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


def test_cli_no_reminders_silent_output_no_blank_lines(monkeypatch, capsys):
    """No-reminders scenario: ensure absolutely no header/bullets or stray blanks.

    - Reminders feature enabled, but no template/global or placeholder reminders.
    - CLI path executes (GUI/editor stubs return None).
    - Captured stdout must contain:
        * No lines starting with "Reminders:" or " - ".
        * No extra blank line attributable to reminders path (empty stdout here).
    """
    # Enable reminders feature flag
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "1")

    # Force CLI path
    import prompt_automation.variables.gui as vgui
    monkeypatch.setattr(vgui, "_gui_prompt", lambda *a, **k: None)
    monkeypatch.setattr(vgui, "_gui_file_prompt", lambda *a, **k: None)
    monkeypatch.setattr(core_mod, "_gui_prompt", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(core_mod, "_gui_file_prompt", lambda *a, **k: None, raising=False)

    # No reminders at template/global or placeholder level
    placeholders = [
        {"name": "first", "label": "First"},
        {"name": "second", "label": "Second"},
    ]
    globals_map = {}

    # Simulate user input for two prompts; do not print prompt text
    seq = iter(["one", "two"])
    monkeypatch.setattr(__import__("builtins"), "input", lambda *a, **k: next(seq))

    # Ensure editor fallback does not intercept CLI path
    monkeypatch.setattr(core_mod, "_editor_prompt", lambda: None)

    values = get_variables(placeholders, template_id=None, globals_map=globals_map)
    assert values["first"] == "one"
    assert values["second"] == "two"

    out = capsys.readouterr().out
    # No headers or bullets at all
    assert "Reminders:" not in out
    assert " - " not in out
    # No stray newlines attributable to reminders path
    assert out == "" or not out.startswith("\n")


def test_cli_reminders_overlap_header_once_inline_dedup_and_ordering(monkeypatch, capsys):
    """Overlap scenario: single header printed; inline dedup; header before first prompt.

    Template/global reminders: [alpha, zeta].
    Placeholders: first[alpha, beta], second[alpha, gamma].
    Expectations:
      - Exactly one "Reminders:" header block.
      - Header contains bullets for alpha and zeta.
      - Inline prints bullets only for non-overlapping: beta and gamma.
      - "Reminders:" header text never appears inline (count == 1).
      - Header appears before the first placeholder prompt label.
    """
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "1")

    # Force CLI path
    import prompt_automation.variables.gui as vgui
    monkeypatch.setattr(vgui, "_gui_prompt", lambda *a, **k: None)
    monkeypatch.setattr(vgui, "_gui_file_prompt", lambda *a, **k: None)
    monkeypatch.setattr(core_mod, "_gui_prompt", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(core_mod, "_gui_file_prompt", lambda *a, **k: None, raising=False)

    # Print the prompt text like real input() to assert ordering
    seq = iter(["one", "two"])

    def _fake_input(prompt: str = "") -> str:  # mimic input() writing prompt
        if prompt:
            print(prompt, end="")
        return next(seq)

    monkeypatch.setattr(__import__("builtins"), "input", _fake_input)

    # Ensure editor fallback does not intercept CLI path
    monkeypatch.setattr(core_mod, "_editor_prompt", lambda: None)

    # Build a minimal template that flows through menus.render_template, which
    # attaches _reminders_inline (deduped) and injects template reminders into globals.
    tmpl = {
        "id": 123,
        "template": "Hello {{first}} and {{second}}",
        "reminders": ["alpha", "zeta"],  # header items
        "placeholders": [
            {"name": "first", "label": "First", "reminders": ["alpha", "beta"]},
            {"name": "second", "label": "Second", "reminders": ["alpha", "gamma"]},
        ],
    }

    from prompt_automation.menus import render_template

    rendered, vars_out = render_template(tmpl, return_vars=True)
    assert vars_out.get("first") == "one"
    assert vars_out.get("second") == "two"
    assert isinstance(rendered, str)

    out = capsys.readouterr().out

    # Exactly one header block
    assert out.count("Reminders:") == 1

    # Header items appear as bullets under that single block
    assert out.count(" - alpha") == 1  # only under header (deduped inline)
    assert out.count(" - zeta") == 1

    # Inline bullets include only non-overlapping items
    assert out.count(" - beta") == 1
    assert out.count(" - gamma") == 1

    # Ordering: header appears before the first prompt label
    first_prompt_idx = out.find("First: ")
    header_idx = out.find("Reminders:")
    assert header_idx != -1 and first_prompt_idx != -1 and header_idx < first_prompt_idx
