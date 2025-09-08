from __future__ import annotations

from pathlib import Path
from typing import List


def test_resolve_conflicts_uninstalls_legacy_package(monkeypatch):
    import importlib
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    calls: List[List[str]] = []

    def fake_bin():
        return ["espanso"]

    def fake_run(args, cwd=None, check=False, timeout=None):
        if isinstance(args, list) and args[:2] == ["espanso", "package"] and args[2] == "list":
            out = """
Installed packages:

- your-pa - version: 0.1.0 (git: https://github.com/josiahH-cf/prompt-automation)
- prompt-automation - version: 0.1.0 (git: https://github.com/josiahH-cf/prompt-automation.git)
"""
            return 0, out, ""
        calls.append([str(a) for a in args])
        return 0, "", ""

    monkeypatch.setattr(sync, "_espanso_bin", fake_bin)
    monkeypatch.setattr(sync, "_run", fake_run)

    sync._resolve_conflicts("prompt-automation", "https://github.com/josiahH-cf/prompt-automation.git", None)

    flat = [" ".join(c) for c in calls]
    assert any("package uninstall your-pa" in s for s in flat)


def test_resolve_conflicts_uninstalls_same_repo_alias(monkeypatch):
    import importlib
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    calls: List[List[str]] = []

    def fake_bin():
        return ["espanso"]

    # Output uses two package names pointing to the same repo URL, one with .git and one without
    listing = """
Installed packages:

- pa-snippets - version: 0.1.0 (git: https://github.com/josiahH-cf/prompt-automation)
- prompt-automation - version: 0.1.0 (git: https://github.com/josiahH-cf/prompt-automation.git)
"""

    def fake_run(args, cwd=None, check=False, timeout=None):
        if isinstance(args, list) and args[:3] == ["espanso", "package", "list"]:
            return 0, listing, ""
        # record everything else
        calls.append([str(a) for a in args])
        return 0, "", ""

    monkeypatch.setattr(sync, "_espanso_bin", fake_bin)
    monkeypatch.setattr(sync, "_run", fake_run)

    # repo_url includes .git; should match alias without .git
    sync._resolve_conflicts(
        "prompt-automation",
        "https://github.com/josiahH-cf/prompt-automation.git",
        None,
    )

    flat = [" ".join(c) for c in calls]
    assert any("package uninstall pa-snippets" in s for s in flat)


def test_resolve_conflicts_idempotent(monkeypatch):
    import importlib
    import sys
    from pathlib import Path
    here = Path(__file__).resolve()
    repo_root = None
    for d in [here.parent] + list(here.parents):
        if (d / "src" / "prompt_automation").exists():
            repo_root = d
            break
    assert repo_root is not None
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    # Simulate installed packages where an alias points to the same repo as the canonical name
    state = [{
        "name": "alias-older",
        "version": "0.1.0",
        "source": "git: https://github.com/josiahH-cf/prompt-automation",
    }, {
        "name": "prompt-automation",
        "version": "0.1.0",
        "source": "git: https://github.com/josiahH-cf/prompt-automation.git",
    }]

    def fake_list():
        # Return a shallow copy to simulate espanso output
        return list(state)

    uninstalled = []

    def fake_uninstall(name: str):
        uninstalled.append(name)
        # Remove from state to simulate successful uninstall
        nonlocal state
        state = [p for p in state if p["name"] != name]

    monkeypatch.setattr(sync, "_list_installed_packages", fake_list)
    monkeypatch.setattr(sync, "_uninstall_package", fake_uninstall)

    # First run should uninstall the alias
    sync._resolve_conflicts("prompt-automation", "https://github.com/josiahH-cf/prompt-automation.git", None)
    assert uninstalled == ["alias-older"]

    # Second run is idempotent: nothing more to uninstall
    sync._resolve_conflicts("prompt-automation", "https://github.com/josiahH-cf/prompt-automation.git", None)
    assert uninstalled == ["alias-older"]
