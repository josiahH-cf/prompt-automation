import logging

from prompt_automation.cli import controller


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

    assert called["args"][0] == {"combo": "Ctrl+X"}
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

