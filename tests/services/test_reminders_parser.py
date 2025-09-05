import os
import sys
from pathlib import Path

# Ensure src on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from prompt_automation.reminders import (
    extract_template_reminders,
    extract_placeholder_reminders,
    partition_placeholder_reminders,
)


def test_template_and_global_merge_and_dedup(monkeypatch):
    tmpl = {
        "reminders": ["A", "B", "A", "", None],
        "global_placeholders": {"reminders": ["B", "C", "  "]},
    }
    merged = extract_template_reminders(tmpl)
    # Order preserved, duplicates removed, blanks dropped
    assert merged == ["A", "B", "C"]


def test_placeholder_reminders_and_partition(monkeypatch):
    placeholders = [
        {"name": "a", "reminders": ["one", "two", "one"]},
        {"name": "b", "reminders": ["two", "three"]},
        {"name": "c"},
    ]
    tlist = ["zero", "one"]
    part = partition_placeholder_reminders(placeholders, tlist)
    # "one" removed due to dedup against template list
    assert part["a"] == ["two"]
    assert part["b"] == ["two", "three"]
    assert "c" not in part


def test_feature_flag_disables_all(monkeypatch):
    monkeypatch.setenv("PROMPT_AUTOMATION_REMINDERS", "0")
    try:
        tmpl = {"reminders": ["x"], "global_placeholders": {"reminders": ["y"]}}
        assert extract_template_reminders(tmpl) == []
        assert extract_placeholder_reminders({"reminders": ["z"]}) == []
        assert partition_placeholder_reminders([{"name": "a", "reminders": ["z"]}], ["z"]) == {}
    finally:
        monkeypatch.delenv("PROMPT_AUTOMATION_REMINDERS", raising=False)

