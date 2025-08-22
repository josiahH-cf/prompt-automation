import sys
import types
from pathlib import Path
import importlib

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

def _install_tk(monkeypatch):
    """Install a minimal tkinter stub capturing messagebox calls."""
    calls = []
    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom = "111x222"
            self.bound = {}
            self.menu = None
        def title(self, *a, **k):
            pass
        def geometry(self, g=None):
            if g:
                self._geom = g
            return self._geom
        def minsize(self, *a, **k):
            pass
        def resizable(self, *a, **k):
            pass
        def protocol(self, *a, **k):
            pass
        def update_idletasks(self):
            pass
        def winfo_geometry(self):
            return self._geom
        def winfo_exists(self):
            return True
        def quit(self):
            pass
        def destroy(self):
            pass
        def bind(self, seq, func):
            self.bound[seq] = func
    stub = types.ModuleType("tkinter")
    stub.Tk = DummyTk
    stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: calls.append((a, k)))
    monkeypatch.setitem(sys.modules, "tkinter", stub)
    return stub, calls


def _load_controller(monkeypatch):
    fake_vf = types.SimpleNamespace(build_widget=lambda spec: (lambda m: None, {}))
    orig_vf = sys.modules.get("prompt_automation.services.variable_form")
    sys.modules["prompt_automation.services.variable_form"] = fake_vf
    module = importlib.import_module("prompt_automation.gui.single_window.controller")
    mods = [
        "prompt_automation.gui.single_window.controller",
        "prompt_automation.gui.single_window.frames.select",
        "prompt_automation.gui.single_window.frames.collect",
        "prompt_automation.gui.single_window.frames.review",
        "prompt_automation.gui.single_window.frames",
        "prompt_automation.gui.options_menu",
    ]
    def cleanup():
        for m in mods:
            sys.modules.pop(m, None)
        if orig_vf is not None:
            sys.modules["prompt_automation.services.variable_form"] = orig_vf
        else:
            sys.modules.pop("prompt_automation.services.variable_form", None)
    return module, cleanup


def test_stage_swap_persists_geometry(monkeypatch):
    _install_tk(monkeypatch)
    controller, cleanup = _load_controller(monkeypatch)
    saves = []
    monkeypatch.setattr(controller.options_menu, "configure_options_menu", lambda *a, **k: {})
    monkeypatch.setattr(controller, "save_geometry", lambda g: saves.append(g))
    monkeypatch.setattr(controller.select, "build", lambda app: None)
    monkeypatch.setattr(controller.collect, "build", lambda app, t: None)
    monkeypatch.setattr(controller.review, "build", lambda app, t, v: None)
    try:
        app = controller.SingleWindowApp()
        app.start()
        app.advance_to_collect({})
        app.advance_to_review({})
        app.back_to_select()
        assert len(saves) == 4
    finally:
        cleanup()


def test_service_exception_triggers_dialog_and_log(monkeypatch):
    stub, calls = _install_tk(monkeypatch)
    controller, cleanup = _load_controller(monkeypatch)
    logs = []
    monkeypatch.setattr(controller.options_menu, "configure_options_menu", lambda *a, **k: {})
    class StubLogger:
        def error(self, msg, *args, **kwargs):
            logs.append({"msg": msg, "args": args, "kwargs": kwargs})
    monkeypatch.setattr(controller, "get_logger", lambda name: StubLogger())
    saves = []
    monkeypatch.setattr(controller, "save_geometry", lambda g: saves.append(g))
    monkeypatch.setattr(controller.select, "build", lambda app: None)
    def bad_collect(app, t):
        raise RuntimeError("boom")
    monkeypatch.setattr(controller.collect, "build", bad_collect)
    try:
        app = controller.SingleWindowApp()
        app.start()
        with pytest.raises(RuntimeError):
            app.advance_to_collect({})
        assert calls and "boom" in calls[0][0][1]
        assert logs and logs[0]["kwargs"].get("exc_info")
        assert len(saves) == 1
    finally:
        cleanup()


def test_edit_exclusions_delegates(monkeypatch):
    _install_tk(monkeypatch)
    controller, cleanup = _load_controller(monkeypatch)
    called = []
    monkeypatch.setattr(controller.options_menu, "configure_options_menu", lambda *a, **k: {})

    def fake_dialog(root, service, tid):
        service.load_exclusions(tid)

    monkeypatch.setattr(controller, "exclusions_dialog", fake_dialog)
    fake_service = types.SimpleNamespace(load_exclusions=lambda tid: called.append(tid))
    monkeypatch.setattr(controller, "exclusions_service", fake_service)
    try:
        app = controller.SingleWindowApp()
        app.edit_exclusions(7)
        assert called == [7]
    finally:
        cleanup()


def test_options_menu_accelerators_bound(monkeypatch):
    _install_tk(monkeypatch)
    controller, cleanup = _load_controller(monkeypatch)
    called = []

    def fake_configure(root, *a, **k):
        root.menu = "menubar"
        return {"<Control-x>": lambda: called.append("x")}

    monkeypatch.setattr(controller.options_menu, "configure_options_menu", fake_configure)
    try:
        app = controller.SingleWindowApp()
        assert getattr(app.root, "menu") == "menubar"
        assert "<Control-x>" in app.root.bound
        result = app.root.bound["<Control-x>"](None)
        assert called == ["x"]
        assert result == (None, "break")
    finally:
        cleanup()
