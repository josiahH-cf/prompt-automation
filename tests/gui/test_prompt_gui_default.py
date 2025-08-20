import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import prompt_automation.gui.controller as controller

def _install_tk(monkeypatch):
    stub = types.ModuleType("tkinter")
    class DummyTk:
        def __init__(self):
            pass
        def mainloop(self):
            pass
        def withdraw(self):
            pass
    stub.Tk = DummyTk
    stub.__path__ = []  # mark as package for submodule imports
    monkeypatch.setitem(sys.modules, "tkinter", stub)
    for name in ("ttk", "filedialog", "messagebox", "simpledialog"):
        monkeypatch.setitem(sys.modules, f"tkinter.{name}", types.ModuleType(name))


def _patch_updates(monkeypatch):
    monkeypatch.setattr(controller.updater, "check_for_update", lambda: None)
    monkeypatch.setattr(controller.update, "check_and_prompt", lambda: None)


def test_single_window_is_default(monkeypatch):
    _install_tk(monkeypatch)
    _patch_updates(monkeypatch)
    called = {"single": False, "legacy": False}

    class DummyApp:
        def run(self):
            called["single"] = True
            return None, None

    monkeypatch.setattr(controller.single_window, "SingleWindowApp", DummyApp)
    monkeypatch.setattr(controller, "open_template_selector", lambda: called.__setitem__("legacy", True))

    gui = controller.PromptGUI()
    gui.run()
    assert called["single"] and not called["legacy"]


def test_force_legacy_env(monkeypatch):
    _install_tk(monkeypatch)
    _patch_updates(monkeypatch)
    monkeypatch.setenv("PROMPT_AUTOMATION_FORCE_LEGACY", "1")
    called = {"single": False, "legacy": False}

    class DummyApp:
        def run(self):
            called["single"] = True
            return None, None

    monkeypatch.setattr(controller.single_window, "SingleWindowApp", DummyApp)
    monkeypatch.setattr(controller, "open_template_selector", lambda: called.__setitem__("legacy", True))

    gui = controller.PromptGUI()
    gui.run()
    assert called["legacy"] and not called["single"]
