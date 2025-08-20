import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

real_tk = sys.modules.get("tkinter")

# Minimal tkinter stub
stub = types.ModuleType("tkinter")

class DummyWidget:
    def __init__(self, *a, **k):
        pass
    def pack(self, *a, **k):
        pass

class DummyButton(DummyWidget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.kwargs = k

stub.Frame = DummyWidget
stub.Button = DummyButton
sys.modules["tkinter"] = stub

from prompt_automation.gui.single_window.frames import review

# Restore real tkinter after importing review so other tests are unaffected
if real_tk is not None:
    sys.modules["tkinter"] = real_tk
else:
    sys.modules.pop("tkinter", None)


def test_review_frame_path_toggle():
    sys.modules["tkinter"] = stub
    app = types.SimpleNamespace(root=object())
    result = review.build(app, {}, {"file_path": "/tmp/x"})
    assert result["copy_paths_btn"] is not None

    result2 = review.build(app, {}, {"foo": "bar"})
    assert result2["copy_paths_btn"] is None

    if real_tk is not None:
        sys.modules["tkinter"] = real_tk
    else:
        sys.modules.pop("tkinter", None)
