from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))

from prompt_automation.gui.collector.components import formatting


def test_format_list_input():
    raw = "foo\nbar\n\n baz \n"
    assert formatting.format_list_input(raw) == ["foo", "bar", "baz"]


def test_truncate_default_hint():
    default = "line1\n" + "a" * 170
    display, truncated = formatting.truncate_default_hint(default, limit=50)
    assert truncated is True
    assert display.endswith("…")
    assert "\n" not in display
    assert len(display) <= 51
