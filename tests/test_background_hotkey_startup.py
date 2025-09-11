import logging

from prompt_automation.cli import controller
from prompt_automation import background_hotkey


def _prepare_settings(monkeypatch, tmp_path):
    settings_dir = tmp_path / "prompts" / "styles" / "Settings"
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / "settings.json"
    monkeypatch.setattr(controller.storage, "_SETTINGS_DIR", settings_dir, raising=False)
    monkeypatch.setattr(controller.storage, "_SETTINGS_FILE", settings_file, raising=False)
    settings_file.write_text("{}", encoding="utf-8")
    return settings_file


def _prep_home(monkeypatch, tmp_path):
    monkeypatch.setattr(controller.Path, "home", lambda: tmp_path)


def test_background_hotkey_registered(monkeypatch, tmp_path):
    _prep_home(monkeypatch, tmp_path)

    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {"combo": "Ctrl+X"}})

    called = {}

    def fake_ensure(settings, service):
        called["args"] = (settings, service)
        return True

    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", fake_ensure)

    controller.PromptCLI()._maybe_register_background_hotkey()

    assert called["args"][0]["combo"] == "Ctrl+X"
    assert called["args"][0]["espanso_enabled"] is True
    assert called["args"][1] is stub_service


def test_background_hotkey_errors_logged(monkeypatch, tmp_path, caplog):
    _prep_home(monkeypatch, tmp_path)

    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {}})

    def boom(settings, service):  # noqa: ARG001
        raise RuntimeError("nope")

    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", boom)

    caplog.set_level(logging.ERROR, logger="prompt_automation.cli")
    controller.PromptCLI()._maybe_register_background_hotkey()

    assert "background_hotkey_init_failed" in caplog.text


def test_env_disables_background_hotkey(monkeypatch, tmp_path, caplog):
    _prep_home(monkeypatch, tmp_path)

    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: False)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {}})

    called: dict[str, bool] = {}
    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", lambda s, svc: called.__setitem__("called", True))

    caplog.set_level(logging.WARNING, logger="prompt_automation.cli")
    controller.PromptCLI()._maybe_register_background_hotkey()

    assert "background_hotkey_env_disabled" in caplog.text
    assert "called" not in called


def test_settings_observer_reacts(monkeypatch, tmp_path):
    _prep_home(monkeypatch, tmp_path)
    _prepare_settings(monkeypatch, tmp_path)

    class StubService:
        def register_hotkey(self, *args, **kwargs):
            pass

        def unregister_hotkey(self, *args, **kwargs):
            pass

    stub_service = StubService()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)

    reg_calls: list[dict] = []
    unreg_calls: list[bool] = []

    def fake_reg(settings, service):
        reg_calls.append(dict(settings))
        return True

    def fake_unreg(service):
        unreg_calls.append(True)

    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", fake_reg)
    monkeypatch.setattr(controller.background_hotkey, "unregister", fake_unreg)

    cli = controller.PromptCLI()
    cli._maybe_register_background_hotkey()

    controller.storage.set_background_hotkey_enabled(False)
    controller.storage.set_background_hotkey_enabled(True)
    controller.storage.set_espanso_enabled(False)
    controller.storage.set_espanso_enabled(True)

    assert reg_calls[0].get("espanso_enabled") is True
    assert any(rc.get("espanso_enabled") is False for rc in reg_calls)
    assert len(unreg_calls) >= 1


def test_on_activate_respects_espanso(monkeypatch):
    class StubService:
        def register_hotkey(self, *args, **kwargs):
            pass

    calls: list[str] = []

    monkeypatch.setattr(background_hotkey, "trigger_prompt_sequence", lambda: calls.append("trigger"), raising=False)
    monkeypatch.setattr(background_hotkey, "run_prompt_sequence_minimal", lambda: calls.append("minimal"), raising=False)

    background_hotkey.ensure_registered({"espanso_enabled": True}, StubService())
    background_hotkey.on_activate()
    assert calls == ["trigger"]

    calls.clear()
    background_hotkey.ensure_registered({"espanso_enabled": False}, StubService())
    background_hotkey.on_activate()
    assert calls == ["minimal"]

