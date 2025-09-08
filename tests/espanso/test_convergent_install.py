from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


def _mk_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    pkg = repo / "espanso-package"
    (pkg / "match").mkdir(parents=True)
    (pkg / "_manifest.yml").write_text(
        "name: prompt-automation\n"
        "title: 'Prompt-Automation Snippets'\n"
        "version: 1.2.3\n"
        "description: 'Test'\n"
        "author: 'Test'\n",
        encoding="utf-8",
    )
    (pkg / "package.yml").write_text("name: prompt-automation\n", encoding="utf-8")
    (pkg / "match" / "basic.yml").write_text("matches: []\n", encoding="utf-8")
    return repo


def test_install_prefers_local_external(monkeypatch, tmp_path):
    import importlib
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    repo = _mk_repo(tmp_path)
    pkg_name, version = "prompt-automation", "1.2.3"
    local_pkg = repo / "packages" / pkg_name / version
    (local_pkg / "match").mkdir(parents=True)

    calls: List[List[str]] = []

    def fake_bin():
        return ["espanso"]

    def fake_run(args, cwd=None, check=False, timeout=None):
        # record
        if isinstance(args, list):
            calls.append([str(a) for a in args])
        # Success by default
        class R:  # pragma: no cover - structure only
            pass
        return 0, "ok", ""

    monkeypatch.setattr(sync, "_espanso_bin", fake_bin)
    monkeypatch.setattr(sync, "_run", fake_run)

    sync._install_or_update(pkg_name, repo_url=None, local_path=local_pkg, git_branch=None)

    flat = [" ".join(c) for c in calls]
    # Ensure we attempted a local install via --path or --external and did not attempt git
    assert any("package install" in s and ("--path" in s or "--external" in s) for s in flat)
    assert not any("package install" in s and "--git" in s for s in flat)


def test_remote_first_when_git_available(monkeypatch, tmp_path):
    import importlib
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    repo = _mk_repo(tmp_path)
    pkg_name, version = "prompt-automation", "1.2.3"
    local_pkg = repo / "packages" / pkg_name / version
    (local_pkg / "match").mkdir(parents=True)

    calls: List[List[str]] = []

    # Simulate: git install attempt -> already installed -> update -> restart/list
    outcomes: List[Tuple[str, int]] = [
        ("--git", 1),  # initial install returns non-zero with already-installed
        ("update", 0),
        ("restart", 0),
        ("package list", 0),
    ]

    def fake_bin():
        return ["espanso"]

    def fake_run(args, cwd=None, check=False, timeout=None):
        if isinstance(args, list):
            s = " ".join(args)
            calls.append([str(a) for a in args])
            # find next outcome matching this type
            if "package install" in s and "--git" in s:
                rc = next((rc for typ, rc in outcomes if typ == "--git"), 0)
                for i, (typ, _rc) in enumerate(outcomes):
                    if typ == "--git":
                        outcomes.pop(i)
                        break
                # Simulate 'already installed' err text to trigger update
                return rc, "", "unable to install package: package prompt-automation is already installed"
            if "package update" in s:
                rc = next((rc for typ, rc in outcomes if typ == "update"), 0)
                for i, (typ, _rc) in enumerate(outcomes):
                    if typ == "update":
                        outcomes.pop(i)
                        break
                return rc, "", ""
            if "restart" in s:
                rc = next((rc for typ, rc in outcomes if typ == "restart"), 0)
                for i, (typ, _rc) in enumerate(outcomes):
                    if typ == "restart":
                        outcomes.pop(i)
                        break
                return rc, "", ""
            if "package list" in s:
                rc = next((rc for typ, rc in outcomes if typ == "package list"), 0)
                for i, (typ, _rc) in enumerate(outcomes):
                    if typ == "package list":
                        outcomes.pop(i)
                        break
                return rc, "", ""
        return 0, "", ""

    monkeypatch.setattr(sync, "_espanso_bin", fake_bin)
    monkeypatch.setattr(sync, "_run", fake_run)

    sync._install_or_update(pkg_name, repo_url="https://example.com/repo.git", local_path=local_pkg, git_branch="main")

    flat = [" ".join(c) for c in calls]
    # Ensure we attempted a git install
    assert any("package install" in s and "--git" in s for s in flat)
    # Ensure no local --path attempts when repo_url is provided
    assert not any("package install" in s and "--path" in s for s in flat)
