import re
from prompt_automation.prompts import parser_singlefield as ps


def _strip_time_markup(s: str) -> str:
    # helper to normalize due_display for assertions when dateparser present/absent
    return re.sub(r"\s+", " ", s).strip()


def test_explicit_priority_due_ac():
    inp = "Email the board with Q3 forecast p1 due: today 4pm ac: Include revenue, burn, runway"
    out = ps.parse_capture(inp)
    assert out["title"].startswith("Email the board")
    assert out["priority"] == "p1"
    assert out["raw_due"] is not None
    assert "Include revenue" in out["acceptance_final"]
    # Scaffold replaced by user AC so should not just be scaffold lines
    assert "Given" not in out["acceptance_final"]


def test_keyword_inference_p1_backfill():
    inp = "Ship hotfix for login timeout asap"
    out = ps.parse_capture(inp)
    assert out["priority"] == "p1"
    # raw_due backfilled to today
    assert out["raw_due"] == "today"
    # acceptance omitted now
    assert out["acceptance_final"] == ""


def test_explicit_p2_with_due():
    inp = "Draft customer update for launch p2 due: next Tue 9am"
    out = ps.parse_capture(inp)
    assert out["priority"] == "p2"
    assert out["raw_due"] is not None
    assert out["acceptance_final"] == ""


def test_default_priority_no_due():
    inp = "Decide vendor for analytics"
    out = ps.parse_capture(inp)
    assert out["priority"] == "p3"
    assert out["raw_due"] is None
    assert out["acceptance_final"] == ""


def test_normalization_prepends_verb():
    inp = "Budget review Q4"
    out = ps.parse_capture(inp)
    # should have a verb prepended (we chose 'Draft')
    assert out["title"].lower().startswith("draft ")
    assert out["priority"] == "p3"
    assert out["acceptance_final"] == ""
