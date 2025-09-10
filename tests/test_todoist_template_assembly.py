from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from prompt_automation.services.todoist_action import build_summary_and_note, send_to_todoist


def test_summary_and_note_omissions():
    s, n = build_summary_and_note(action="Ship login fix", type_="bug", dod="passes CI", nra="merge")
    assert s == "bug - Ship login fix — DoD: passes CI"
    assert n == "NRA: merge"

    s, n = build_summary_and_note(action="Write docs", type_="", dod="", nra=None)
    assert s == "Write docs"
    assert n is None

    s, n = build_summary_and_note(action="Refactor", type_=None, dod="improve clarity", nra="")
    assert s == "Refactor — DoD: improve clarity"
    assert n is None


def test_post_action_disabled_by_default(monkeypatch, tmp_path):
    # Ensure packaged Settings/settings.json doesn't flip the default on
    monkeypatch.setenv("PROMPT_AUTOMATION_PROMPTS", str(tmp_path))
    monkeypatch.delenv("SEND_TODOIST_AFTER_RENDER", raising=False)
    ok, msg = send_to_todoist("Task", None)
    assert ok and msg == "disabled"


def test_post_action_pwsh_unavailable(monkeypatch):
    monkeypatch.setenv("SEND_TODOIST_AFTER_RENDER", "1")
    # Force detector to fail
    monkeypatch.setenv("PATH", "")
    ok, msg = send_to_todoist("Task", None)
    assert ok and msg == "powershell_missing"


def test_post_action_dry_run(monkeypatch, tmp_path):
    monkeypatch.setenv("SEND_TODOIST_AFTER_RENDER", "1")
    monkeypatch.setenv("TODOIST_DRY_RUN", "1")

    # Provide a fake pwsh and a wrapper to echo argv
    fake_pwsh = tmp_path / ("pwsh.exe" if os.name == "nt" else "pwsh")
    fake_pwsh.write_text("#!/bin/sh\necho DRYRUN\nexit 0\n")
    fake_pwsh.chmod(0o755)

    # Put fake pwsh first on PATH
    monkeypatch.setenv("PATH", str(tmp_path))

    # Point to real script path so arguments shape is exercised
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("PROMPT_AUTOMATION_REPO", str(repo_root))

    ok, msg = send_to_todoist("Hello", "NRA: test")
    assert ok
