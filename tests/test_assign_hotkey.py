import json
import sys

sys.modules.setdefault("pyperclip", type("x", (), {"copy": lambda *a: None}))
from prompt_automation import cli, hotkeys


def test_assign_hotkey_creates_config(tmp_path, monkeypatch):
    monkeypatch.setattr(hotkeys, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(hotkeys, "HOTKEY_FILE", tmp_path / "hotkey.json")
    monkeypatch.setattr(hotkeys, "capture_hotkey", lambda: "ctrl+shift+k")
    monkeypatch.setattr(hotkeys, "update_system_hotkey", lambda hotkey: None)
    cli.main(["--assign-hotkey"])
    data = json.loads((tmp_path / "hotkey.json").read_text())
    assert data["hotkey"] == "ctrl+shift+k"
