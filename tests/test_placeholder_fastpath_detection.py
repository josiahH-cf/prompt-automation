import sys
from pathlib import Path

# ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import time
import types
import os


def test_fastpath_absent_and_empty(monkeypatch):
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    # Absent placeholders
    t1 = {"id": 1, "title": "T", "style": "S", "template": ["Hello"]}
    assert evaluate_fastpath_state(t1) == FastPathState.EMPTY
    # None placeholders
    t2 = {"id": 2, "title": "T", "style": "S", "template": ["Hello"], "placeholders": None}
    assert evaluate_fastpath_state(t2) == FastPathState.EMPTY
    # Empty list
    t3 = {"id": 3, "title": "T", "style": "S", "template": ["Hello"], "placeholders": []}
    assert evaluate_fastpath_state(t3) == FastPathState.EMPTY


def test_fastpath_invalid_specs_filtered(monkeypatch):
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    t = {
        "id": 1,
        "title": "X",
        "style": "S",
        "template": ["Hi"],
        "placeholders": [
            {},  # invalid
            {"name": ""},  # blank
            {"name": "reminder_tip", "label": "Tip"},  # heuristic reminder
            {"name": "note1", "type": "note"},  # note
            {"name": "lnk", "type": "link", "url": "https://example.com"},  # link
        ],
    }
    assert evaluate_fastpath_state(t) == FastPathState.EMPTY


def test_fastpath_detects_non_empty(monkeypatch):
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    t = {
        "id": 5,
        "title": "X",
        "style": "S",
        "template": ["Hi {{name}}"],
        "placeholders": [{"name": "name"}],
    }
    assert evaluate_fastpath_state(t) == FastPathState.NON_EMPTY


def test_fastpath_killswitch_env(monkeypatch):
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    monkeypatch.setenv('PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH', '1')
    t = {"template": ["X"], "placeholders": []}
    assert evaluate_fastpath_state(t) == FastPathState.DISABLED


def test_fastpath_killswitch_settings(monkeypatch, tmp_path):
    # Clear env influence
    monkeypatch.delenv('PROMPT_AUTOMATION_DISABLE_PLACEHOLDER_FASTPATH', raising=False)
    settings_dir = tmp_path / 'prompts' / 'styles' / 'Settings'
    settings_dir.mkdir(parents=True)
    settings_file = settings_dir / 'settings.json'
    settings_file.write_text('{"disable_placeholder_fastpath": true}')
    from prompt_automation import features
    # PROMPTS_DIR points at the styles folder
    monkeypatch.setattr(features, 'PROMPTS_DIR', settings_dir.parent, raising=False)
    # Import after patch to ensure path resolution uses tmp settings
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    t = {"template": ["X"], "placeholders": []}
    assert evaluate_fastpath_state(t) == FastPathState.DISABLED


def test_fastpath_eval_perf_small_overhead():
    from prompt_automation.placeholder_fastpath import evaluate_fastpath_state, FastPathState
    t = {"template": ["x"], "placeholders": []}
    # Warm-up
    for _ in range(100):
        evaluate_fastpath_state(t)
    # Measure 2000 iterations; ensure under a small budget. Allow a modest
    # cushion to avoid flakiness on slower or sandboxed environments.
    start = time.perf_counter()
    for _ in range(2000):
        evaluate_fastpath_state(t)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert elapsed_ms < 75.0, f"fast-path eval took {elapsed_ms:.2f}ms (>75ms)"
