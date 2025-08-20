import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from prompt_automation.gui.single_window import geometry


def test_geometry_round_trip(tmp_path, monkeypatch):
    tmp_file = tmp_path / "settings.json"
    monkeypatch.setattr(geometry, "SETTINGS_PATH", tmp_file)
    geometry.save_geometry("111x222")
    assert geometry.load_geometry() == "111x222"
