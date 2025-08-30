def test_cli_hotkey_repair_invokes_update(monkeypatch, tmp_path):
    # Ensure home points to tmp to avoid touching real paths
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)

    import prompt_automation.cli.__init__ as cli_mod

    called = {'deps': 0, 'update': 0}

    def _deps_ok():
        called['deps'] += 1
        return True

    def _update():
        called['update'] += 1

    import prompt_automation.hotkeys.base as base
    monkeypatch.setattr(base.HotkeyManager, 'ensure_hotkey_dependencies', staticmethod(_deps_ok))
    monkeypatch.setattr(base.HotkeyManager, 'update_hotkeys', staticmethod(_update))

    cli = cli_mod.PromptCLI()
    cli.main(['--hotkey-repair'])

    assert called['deps'] == 1
    assert called['update'] == 1

