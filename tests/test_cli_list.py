import sys
sys.modules.setdefault("pyperclip", type("x", (), {"copy": lambda *a: None}))
from prompt_automation import cli  # noqa: E402

def test_list_flag(capsys):
    cli.main(["--list"])
    out = capsys.readouterr().out
    assert "Utility" in out

