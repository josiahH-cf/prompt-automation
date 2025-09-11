from prompt_automation.cli import controller

def _prep(monkeypatch, tmp_path):
    monkeypatch.setattr(controller.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(controller, "ensure_unique_ids", lambda *a, **k: None)
    monkeypatch.setattr(controller, "list_styles", lambda: [])
    monkeypatch.setattr(controller, "list_prompts", lambda style: [])


def test_disable_background_hotkey_triggers_unregistration(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {"combo": "Ctrl+X"}})
    monkeypatch.setattr(controller.storage, "get_espanso_enabled", lambda: True)

    reg_calls = []
    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", lambda s, svc: reg_calls.append(dict(s)))
    unreg_calls = []
    monkeypatch.setattr(controller.background_hotkey, "unregister", lambda svc: unreg_calls.append(svc))

    def fake_set(enabled: bool):
        controller.storage._notify_boolean_observers("background_hotkey_enabled", enabled)
    monkeypatch.setattr(controller.storage, "set_background_hotkey_enabled", fake_set)

    cli = controller.PromptCLI()
    cli.main(["--disable-background-hotkey", "--list"])

    assert stub_service in unreg_calls
    assert any(call.get("espanso_enabled") is True for call in reg_calls)


def test_enable_espanso_triggers_reregistration(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {"combo": "Ctrl+X"}})
    monkeypatch.setattr(controller.storage, "get_espanso_enabled", lambda: False)

    reg_calls = []
    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", lambda s, svc: reg_calls.append(dict(s)))
    monkeypatch.setattr(controller.background_hotkey, "unregister", lambda svc: None)

    def fake_set(enabled: bool):
        controller.storage._notify_boolean_observers("espanso_enabled", enabled)
    monkeypatch.setattr(controller.storage, "set_espanso_enabled", fake_set)

    cli = controller.PromptCLI()
    cli.main(["--enable-espanso", "--list"])

    assert any(call.get("espanso_enabled") is False for call in reg_calls)
    assert any(call.get("espanso_enabled") is True for call in reg_calls)
