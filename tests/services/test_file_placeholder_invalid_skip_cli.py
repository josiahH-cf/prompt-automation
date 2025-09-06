import builtins
from pathlib import Path

import pytest


def test_invalid_presupplied_file_path_with_no_template_triggers_single_cli_skip(monkeypatch, tmp_path):
    # Arrange: invalid pre-supplied path and no template binding (template_id=None)
    missing = tmp_path / "does_not_exist.txt"
    assert not missing.exists()

    # Force GUI file chooser to return no selection so CLI fallback is used
    import prompt_automation.variables.core as core_mod
    monkeypatch.setattr(core_mod, "_gui_file_prompt", lambda *a, **k: None)

    # Count how many times CLI input is requested; simulate immediate skip (empty input)
    calls = {"count": 0}

    def _input_stub(*args, **kwargs):
        calls["count"] += 1
        # At most one CLI prompt in this scenario
        if calls["count"] > 1:
            raise AssertionError("CLI was prompted more than once for invalid file path")
        return ""  # user chooses to skip

    monkeypatch.setattr(builtins, "input", _input_stub)

    placeholders = [{"name": "ref", "type": "file", "label": "Ref File"}]

    # Act: collect variables with an invalid pre-supplied path
    values = core_mod.get_variables(placeholders, initial={"ref": str(missing)}, template_id=None)

    # Assert: no crash, single CLI prompt, and value is None (skip)
    assert calls["count"] == 1
    assert values["ref"] is None

