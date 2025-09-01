from pathlib import Path


def test_cli_repeated_runs_terminal_mode(monkeypatch, tmp_path):
    # Avoid touching the real home directory
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    # Disable any background update checks
    monkeypatch.setenv('PROMPT_AUTOMATION_AUTO_UPDATE', '0')

    # Import CLI and call the light-weight --version path twice.
    import prompt_automation.cli.__init__ as cli_mod

    cli = cli_mod.PromptCLI()
    cli.main(['--version'])
    # Second run should work identically
    cli.main(['--version'])

