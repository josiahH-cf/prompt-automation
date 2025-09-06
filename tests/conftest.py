"""Global pytest configuration to ensure deterministic, non-interactive tests.

Why: Some environments run the test suite outside a git checkout or with
PROMPT_AUTOMATION_UPDATE_URL set. In those cases the CLI can attempt
networked self-update checks (pipx or manifest) which may block or
slow down tests. We explicitly enable dev mode and disable auto-update
for the duration of each test to avoid any network or interactive prompts.
"""

from __future__ import annotations

import os
import pytest


@pytest.fixture(autouse=True)
def _isolate_updates(monkeypatch: pytest.MonkeyPatch):
    # Force dev mode so CLI skips updater + manifest checks
    monkeypatch.setenv("PROMPT_AUTOMATION_DEV", "1")
    # Belt-and-suspenders: also disable pipx auto-update helper
    monkeypatch.setenv("PROMPT_AUTOMATION_AUTO_UPDATE", "0")
    # And ensure manifest updater has no remote configured
    monkeypatch.delenv("PROMPT_AUTOMATION_UPDATE_URL", raising=False)
    # Keep environment otherwise intact for other tests
    yield

