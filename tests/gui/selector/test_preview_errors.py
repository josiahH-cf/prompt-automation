import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from prompt_automation.gui.selector.view import preview
from prompt_automation.gui import error_dialogs


def test_open_preview_error_triggers_helper(monkeypatch):
    calls = []
    monkeypatch.setattr(error_dialogs, "show_error", lambda *a, **k: calls.append((a, k)))
    tk_stub = types.ModuleType("tkinter")
    tk_stub.Toplevel = lambda parent: (_ for _ in ()).throw(RuntimeError("boom"))
    monkeypatch.setitem(sys.modules, "tkinter", tk_stub)
    font_stub = types.ModuleType("fonts")
    font_stub.get_display_font = lambda *a, **k: ("Arial", 10)
    monkeypatch.setitem(sys.modules, "prompt_automation.gui.selector.fonts", font_stub)
    entry = types.SimpleNamespace(data={})
    preview.open_preview(object(), entry)
    assert calls and "boom" in calls[0][0][1]
