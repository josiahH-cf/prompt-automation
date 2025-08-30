import re
from typing import Dict, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

try:
    import dateparser
except Exception:
    dateparser = None


PRIORITY_KEYWORDS = {
    "p1": ["asap", "urgent", "blocker", "today"],
    "p2": ["soon", "this week"],
}


RE_CAPTURE = re.compile(
    r"(?i)^(?P<outcome>.*?)(?:\s+(?P<priority>p[1-4]))?(?:\s+due:\s*(?P<due>[^\n]+?))?(?:\s+ac:\s*(?P<ac>.+))?$")


def _infer_priority_from_outcome(outcome: str) -> Optional[str]:
    o = outcome.lower()
    for p, kws in PRIORITY_KEYWORDS.items():
        for kw in kws:
            if kw in o:
                return p
    return None


def _strip_priority_keywords(outcome: str) -> str:
    o = outcome
    for kws in PRIORITY_KEYWORDS.values():
        for kw in kws:
            # remove standalone keyword tokens and excess whitespace
            o = re.sub(r"\b" + re.escape(kw) + r"\b", "", o, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", o).strip()


def _ensure_leading_verb(title: str, default_verb: str = "Draft") -> str:
    stripped = title.strip()
    if not stripped:
        # Nothing to work with; return placeholder title for downstream logic
        return f"{default_verb} task"
    # Heuristic: consider word is a verb if it is lowercased or common verb forms
    first_word = stripped.split(" ", 1)[0]
    if not first_word:
        return f"{default_verb} task"
    # crude check: if first word ends with 'e' or is one of common verbs, accept; otherwise prepend
    verbs = {
        "draft",
        "decide",
        "fix",
        "create",
        "send",
        "ship",
        "update",
        "email",
        "review",
        "prepare",
        "schedule",
        "implement",
        "triage",
        "test",
        "run",
        "analyze",
        "deploy",
        "merge",
        "close",
        "resolve",
        "investigate",
    }
    if first_word.lower() in verbs:
        return stripped
    # If the first word is imperative-like (starts with uppercase verb) we still accept
    if first_word[0].isupper() and first_word.lower() in verbs:
        return stripped
    # Otherwise prepend default verb
    return f"{default_verb} {stripped}"


def _resolve_due(due_str: Optional[str], settings_tz: Optional[str] = None) -> Optional[str]:
    if not due_str:
        return None
    raw = due_str.strip()
    if dateparser is None:
        return raw

    settings = {"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": True}
    if settings_tz:
        settings["TIMEZONE"] = settings_tz

    dt = dateparser.parse(raw, settings=settings)
    if not dt:
        return raw

    # Ensure timezone-aware datetime; convert to requested timezone if provided
    try:
        if settings_tz:
            tz = ZoneInfo(settings_tz)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                dt = dt.astimezone(tz)
        else:
            # normalize to system local tz if possible
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    except Exception:
        # if zoneinfo fails, fall back to naive dt
        pass

    now = datetime.now(dt.tzinfo) if dt.tzinfo is not None else datetime.now()
    date_only = dt.date()
    today = now.date()

    time_part = dt.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")

    # If the user gave a relative token like 'today' or 'friday', prefer to show that
    low = raw.lower()
    for token in ("today", "tomorrow", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday"):
        if token in low:
            # preserve weekday token and time if present
            if token in ("today", "tomorrow"):
                return f"{token} {time_part}" if dt.time() != datetime.min.time() else token
            return f"{token.capitalize()} {time_part}" if dt.time() != datetime.min.time() else token.capitalize()

    # If date is today
    if date_only == today:
        return f"today {time_part}" if dt.time() != datetime.min.time() else "today"

    # If within next 7 days, show weekday name
    if 0 <= (date_only - today).days < 7:
        weekday = dt.strftime("%A")
        return f"{weekday} {time_part}" if dt.time() != datetime.min.time() else weekday

    # Otherwise show month day and time (e.g., Sep 2 9:00 AM)
    return dt.strftime("%b %d %I:%M %p").replace(" 0", " ")


def parse_capture(capture: str, timezone: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Parse a single-line capture per the JSON logic and return structured outputs.

    Spec (current):
    - Defaults: priority p3, no due.
    - Inference: keyword -> p1/p2.
    - Due backfill (display & raw): p1 -> today, p2 -> end of week ("end of week").
    - Acceptance scaffold inserted when ac: segment missing.
    - Always show priority bracket (including default p3) for consistency.
    Returns dict with keys: title, priority, due_display, acceptance_final, raw_due.
    """
    m = RE_CAPTURE.match(capture.strip())
    outcome = capture.strip()
    priority = None
    priority_explicit = False  # user typed p[1-4] or keyword implied
    due = None
    ac = None
    if m:
        outcome = (m.group("outcome") or "").strip()
        priority = (m.group("priority") or None)
        if priority:
            priority_explicit = True
        due = (m.group("due") or None)
        ac = (m.group("ac") or None)

    # infer priority if missing
    if not priority:
        inferred = _infer_priority_from_outcome(outcome)
        if inferred:
            priority = inferred
            priority_explicit = True
        else:
            priority = "p3"
    # if explicit priority present, keep as-is

    # Backfill due per spec (if none provided explicitly)
    if not due:
        if priority == "p1":
            due = "today"
        elif priority == "p2":
            due = "end of week"

    # normalize title: strip keywords used for inference
    title = _strip_priority_keywords(outcome)
    title = title.strip()
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Ensure leading verb
    title = _ensure_leading_verb(title, default_verb="Draft")

    # resolve due into display string if possible
    resolved_due = _resolve_due(due, settings_tz=timezone) if due else None
    due_display = f" — due: {resolved_due}" if resolved_due else ""

    # acceptance
    if ac and ac.strip():
        acceptance_final = ac.strip()
    else:
        acceptance_final = ""  # omit acceptance section when not specified

    return {
        "title": title,
        "priority": priority,
        "due_display": due_display,
        "acceptance_final": acceptance_final,
        "raw_due": due,
    }
