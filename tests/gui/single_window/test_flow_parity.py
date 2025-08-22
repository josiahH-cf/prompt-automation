import sys
import types
from pathlib import Path

import pytest


# ensure src package on path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def _install_tk(monkeypatch):
    """Install a minimal tkinter stub used by SingleWindowApp."""

    class DummyTk:
        def __init__(self):
            self.children = {}
            self._geom = "200x100"

        def title(self, *_a, **_k):
            pass

        def geometry(self, g=None):
            if g:
                self._geom = g
            return self._geom

        def minsize(self, *_a, **_k):
            pass

        def resizable(self, *_a, **_k):
            pass

        def protocol(self, *_a, **_k):
            pass

        def update_idletasks(self):
            pass

        def winfo_geometry(self):
            return self._geom

        def winfo_exists(self):
            return True

        def destroy(self):
            pass

        def quit(self):
            pass

        def mainloop(self):
            pass

    stub = types.ModuleType("tkinter")
    stub.Tk = DummyTk
    stub.messagebox = types.SimpleNamespace(showerror=lambda *a, **k: None, askyesno=lambda *a, **k: False)
    monkeypatch.setitem(sys.modules, "tkinter", stub)
    return stub


def test_single_window_output_matches_legacy(monkeypatch):
    """Final rendered output should match legacy render_template result."""

    _install_tk(monkeypatch)

    fake_vf = types.SimpleNamespace(build_widget=lambda spec: (lambda m: None, {}))
    monkeypatch.setitem(sys.modules, "prompt_automation.services.variable_form", fake_vf)
    import prompt_automation.gui.single_window.controller as controller
    from prompt_automation.gui.single_window.frames import review as review_frame
    from prompt_automation.menus import render_template
    from prompt_automation.renderer import fill_placeholders

    # avoid file system interactions
    monkeypatch.setattr(controller, "load_geometry", lambda: "100x100")
    monkeypatch.setattr(controller, "save_geometry", lambda g: None)
    monkeypatch.setattr(controller.options_menu, "configure_options_menu", lambda *a, **k: {})
    monkeypatch.setattr(review_frame, "log_usage", lambda *a, **k: None)
    monkeypatch.setattr(review_frame, "_append_to_files", lambda *a, **k: None)

    template = {
        "id": 1,
        "template": ["Hello {{name}}"],
        "placeholders": [{"name": "name"}],
    }
    variables = {"name": "World"}

    legacy_out, legacy_vars = render_template(template, variables, return_vars=True)

    # auto-advance through stages
    monkeypatch.setattr(controller.select, "build", lambda app: app.advance_to_collect(template))
    monkeypatch.setattr(controller.collect, "build", lambda app, tmpl: app.advance_to_review(variables))

    def _review(app, tmpl, vars):
        # compute final text using same fill_placeholders as real review frame
        text = fill_placeholders(tmpl["template"], vars)
        app.finish(text)
        return types.SimpleNamespace()

    monkeypatch.setattr(controller.review, "build", _review)

    app = controller.SingleWindowApp()
    final_text, var_map = app.run()

    assert final_text == legacy_out
    assert var_map == legacy_vars


def test_single_window_cancel_flow(monkeypatch):
    """Cancellation should return ``(None, None)`` without errors."""

    _install_tk(monkeypatch)

    fake_vf = types.SimpleNamespace(build_widget=lambda spec: (lambda m: None, {}))
    monkeypatch.setitem(sys.modules, "prompt_automation.services.variable_form", fake_vf)
    import prompt_automation.gui.single_window.controller as controller

    monkeypatch.setattr(controller, "load_geometry", lambda: "100x100")
    monkeypatch.setattr(controller, "save_geometry", lambda g: None)
    monkeypatch.setattr(controller.options_menu, "configure_options_menu", lambda *a, **k: {})

    template = {"id": 1, "template": [], "placeholders": []}
    variables = {}

    monkeypatch.setattr(controller.select, "build", lambda app: app.advance_to_collect(template))
    monkeypatch.setattr(controller.collect, "build", lambda app, tmpl: app.advance_to_review(variables))
    monkeypatch.setattr(controller.review, "build", lambda app, t, v: app.cancel())

    app = controller.SingleWindowApp()
    final_text, var_map = app.run()

    assert final_text is None and var_map is None

