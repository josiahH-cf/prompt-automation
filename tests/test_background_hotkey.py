from __future__ import annotations

from pathlib import Path
import logging

import pytest

from prompt_automation import background_hotkey
from prompt_automation.cli import controller


def _prep_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point Path.home to tmp to isolate settings."""
    monkeypatch.setattr(controller.Path, "home", lambda: tmp_path)


def test_defaults_and_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default combo used and settings persisted for activation."""
    called: dict[str, object] = {}

    class StubService:
        def register_hotkey(self, _id: str, combo: str, callback) -> None:  # noqa: D401
            called["combo"] = combo
            called["callback"] = callback

    # Register with empty settings -> default combo
    assert background_hotkey.ensure_registered({}, StubService()) is True
    assert called["combo"] == background_hotkey.DEFAULT_COMBO

    # Stored settings should be consulted on activation (espanso enabled by default)
    triggered: list[str] = []
    monkeypatch.setattr(
        background_hotkey,
        "trigger_prompt_sequence",
        lambda: triggered.append("trigger"),
        raising=False,
    )
    background_hotkey.on_activate()
    assert triggered == ["trigger"]


def test_registration_invoked_when_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CLI registers background hotkey when feature and setting enabled."""
    _prep_home(monkeypatch, tmp_path)
    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "get_espanso_enabled", lambda: True)
    monkeypatch.setattr(
        controller.storage,
        "_load_settings_payload",
        lambda: {"background_hotkey": {"combo": "Ctrl+Y"}},
    )

    called: dict[str, object] = {}

    def fake_ensure(settings, service):
        called["settings"] = dict(settings)
        called["service"] = service
        return True

    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", fake_ensure)

    controller.PromptCLI()._maybe_register_background_hotkey()

    assert called["service"] is stub_service
    assert called["settings"]["combo"] == "Ctrl+Y"
    assert called["settings"]["espanso_enabled"] is True


def test_callback_path_based_on_espanso_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Activation path depends on espanso_enabled flag."""
    class StubService:
        def register_hotkey(self, *_args) -> None:
            pass

    calls: list[str] = []
    monkeypatch.setattr(
        background_hotkey,
        "trigger_prompt_sequence",
        lambda: calls.append("trigger"),
        raising=False,
    )
    monkeypatch.setattr(
        background_hotkey,
        "run_prompt_sequence_minimal",
        lambda: calls.append("minimal"),
        raising=False,
    )

    background_hotkey.ensure_registered({"espanso_enabled": True}, StubService())
    background_hotkey.on_activate()
    assert calls == ["trigger"]

    calls.clear()
    background_hotkey.ensure_registered({"espanso_enabled": False}, StubService())
    background_hotkey.on_activate()
    assert calls == ["minimal"]


def test_unregistration_on_toggle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Toggling setting off triggers unregistration."""
    _prep_home(monkeypatch, tmp_path)
    stub_service = object()
    monkeypatch.setattr(controller, "global_shortcut_service", stub_service, raising=False)
    monkeypatch.setattr(controller.storage, "get_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller, "is_background_hotkey_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "get_espanso_enabled", lambda: True)
    monkeypatch.setattr(controller.storage, "_load_settings_payload", lambda: {"background_hotkey": {}})

    unreg_calls: list[object] = []

    monkeypatch.setattr(controller.background_hotkey, "ensure_registered", lambda s, svc: True)
    monkeypatch.setattr(controller.background_hotkey, "unregister", lambda svc: unreg_calls.append(svc))

    def fake_set(enabled: bool) -> None:
        controller.storage._notify_boolean_observers("background_hotkey_enabled", enabled)

    monkeypatch.setattr(controller.storage, "set_background_hotkey_enabled", fake_set)

    controller.PromptCLI()._maybe_register_background_hotkey()

    controller.storage.set_background_hotkey_enabled(False)

    assert stub_service in unreg_calls


def test_ensure_registered_respects_env(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    calls: list[str] = []

    class StubService:
        def register_hotkey(self, *_args) -> None:  # pragma: no cover - defensive
            calls.append("registered")

    monkeypatch.setattr(background_hotkey, "is_background_hotkey_enabled", lambda: False)

    caplog.set_level(logging.WARNING, logger="prompt_automation.background_hotkey")
    result = background_hotkey.ensure_registered({}, StubService())

    assert result is False
    assert calls == []
    assert "background_hotkey_env_disabled" in caplog.text
