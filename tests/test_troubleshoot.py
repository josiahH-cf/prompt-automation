import sys

sys.modules.setdefault("pyperclip", type("x", (), {"copy": lambda x: None}))
from prompt_automation import cli


def test_troubleshoot_flag(capsys):
    cli.main(["--troubleshoot"])
    out = capsys.readouterr().out
    assert "Troubleshooting" in out

