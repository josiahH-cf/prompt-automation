from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))

from prompt_automation.gui.collector.components.formatting import load_file_with_limit


def test_load_file_with_limit_injection(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("hello")

    calls = {}

    def fake_reader(pth):
        calls['called'] = pth
        return "DATA"

    content = load_file_with_limit(str(path), reader=fake_reader, size_limit=100)
    assert content == "DATA"
    assert calls['called'] == str(path)
