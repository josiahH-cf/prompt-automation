import importlib
import sys

import pytest

from prompt_automation.cli.controller import PromptCLI


def test_import_guard(monkeypatch, capsys):
    monkeypatch.setenv("UNINSTALL_FEATURE_FLAG", "0")
    sys.modules.pop("prompt_automation.uninstall", None)
    with pytest.raises(SystemExit) as excinfo:
        importlib.import_module("prompt_automation.uninstall")
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "Uninstall feature disabled" in err
    sys.modules.pop("prompt_automation.uninstall", None)


def test_cli_guard(monkeypatch, capsys):
    monkeypatch.setenv("UNINSTALL_FEATURE_FLAG", "0")
    cli = PromptCLI()
    code = cli.main(["uninstall"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Uninstall feature disabled" in out
