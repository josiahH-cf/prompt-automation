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


def _disable_singleton_focus(monkeypatch):
    """Prevent cross-test or external singleton from short-circuiting the GUI path.

    Some environments may have a lingering singleton socket/port file or an
    in-process flag set by earlier tests. The default GUI entry checks
    ``singleton.connect_and_focus_if_running`` first and returns early when it
    reports an existing instance. That would make this test flaky. We patch the
    function to return ``False`` deterministically to exercise the default
    single-window path.
    """
    import prompt_automation.gui.single_window.singleton as singleton_mod
    monkeypatch.setattr(singleton_mod, "connect_and_focus_if_running", lambda: False)


def test_single_window_is_default(monkeypatch):
    _install_tk(monkeypatch)
    _patch_updates(monkeypatch)
    _disable_singleton_focus(monkeypatch)
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
    _disable_singleton_focus(monkeypatch)
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
