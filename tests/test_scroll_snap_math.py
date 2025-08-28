import sys
from pathlib import Path

# tests/ is one level below repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def test_compute_scroll_adjustment_scrolls_down_when_below():
    from prompt_automation.gui.single_window.scroll_helpers import compute_scroll_adjustment
    # Widget is below current view (100..300), widget spans 320..360
    new_top = compute_scroll_adjustment(widget_top=320, widget_bottom=360, view_top=100, view_bottom=300)
    assert new_top is not None
    assert new_top >= 320 and new_top <= 360  # top-align or minimal scroll to show


def test_compute_scroll_adjustment_scrolls_up_when_above():
    from prompt_automation.gui.single_window.scroll_helpers import compute_scroll_adjustment
    # Widget is above current view (200..400), widget spans 120..160
    new_top = compute_scroll_adjustment(widget_top=120, widget_bottom=160, view_top=200, view_bottom=400)
    assert new_top is not None
    assert new_top <= 120


def test_compute_scroll_adjustment_none_when_visible():
    from prompt_automation.gui.single_window.scroll_helpers import compute_scroll_adjustment
    # Widget (240..260) fully visible in (200..400)
    assert compute_scroll_adjustment(240, 260, 200, 400) is None


def test_compute_scroll_adjustment_large_widget_top_align():
    from prompt_automation.gui.single_window.scroll_helpers import compute_scroll_adjustment
    # Widget taller than viewport: 100..500; viewport 200..350
    # Align to top (100) is acceptable minimal strategy
    new_top = compute_scroll_adjustment(100, 500, 200, 350)
    assert new_top in (100, 350) or (new_top is not None and 100 <= new_top <= 350)
