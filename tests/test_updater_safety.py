from __future__ import annotations

import os
from pathlib import Path
import types

import builtins


def test_windows_skips_auto_update_by_default(monkeypatch, tmp_path):
    """On Windows, updater should be a no-op by default (safety)."""
    import prompt_automation.updater as upd

    # Ensure state writes go to a temp file and don't rate-limit unexpectedly
    monkeypatch.setattr(upd, "STATE_PATH", tmp_path / "auto-update.json", raising=False)
    # Force platform to windows
    monkeypatch.setattr(upd, "os", types.SimpleNamespace(environ={}, pathsep=os.pathsep))
    monkeypatch.setattr(upd, "Path", Path)
    monkeypatch.setattr(upd, "time", __import__("time"))

    # Simulate win32 platform
    monkeypatch.setattr(upd, "__name__", upd.__name__, raising=False)
    # Guard: ensure _upgrade_via_pipx is never called
    called = {"upgrade": 0}

    def _no_call():
        called["upgrade"] += 1
        raise AssertionError("_upgrade_via_pipx should not be called on Windows by default")

    monkeypatch.setattr(upd, "_upgrade_via_pipx", _no_call, raising=True)

    # Simulate versions to tempt an upgrade path
    monkeypatch.setattr(upd, "_current_version", lambda: "0.0.0", raising=True)
    monkeypatch.setattr(upd, "_fetch_latest_version", lambda timeout=2.0: "9999.0.0", raising=True)

    # Expose a fake platform flag by injecting sys.platform into module scope
    # We avoid importing sys from module to keep patching simple.
    monkeypatch.setenv("PROMPT_AUTOMATION_TEST_PLATFORM", "win32")
    # The guard in updater consults os.name/platform via os.environ flag; ensure defaults
    upd._PLATFORM = "win32"

    upd.check_for_update()
    assert called["upgrade"] == 0


def test_windows_opt_in_env_is_required(monkeypatch, tmp_path):
    """Windows requires explicit opt-in flag; without it no upgrade occurs."""
    import prompt_automation.updater as upd

    # Ensure a tempting newer version exists but still skip due to default
    monkeypatch.setenv("PROMPT_AUTOMATION_AUTO_UPDATE", "1")
    monkeypatch.setattr(upd, "STATE_PATH", tmp_path / "auto-update.json", raising=False)
    upd._PLATFORM = "win32"

    # Simulate version check and available pipx
    monkeypatch.setattr(upd, "_current_version", lambda: "0.0.0", raising=True)
    monkeypatch.setattr(upd, "_fetch_latest_version", lambda timeout=2.0: "0.0.1", raising=True)
    monkeypatch.setattr(upd, "_should_rate_limit", lambda last: False, raising=True)
    monkeypatch.setattr(upd, "_have_pipx", lambda: True, raising=True)

    # Guard: ensure upgrade is not invoked without opt-in
    called = {"upgrade": 0}

    def _no_upgrade():
        called["upgrade"] += 1

    monkeypatch.setattr(upd, "_upgrade_via_pipx", _no_upgrade, raising=True)

    upd.check_for_update()
    assert called["upgrade"] == 0
