from __future__ import annotations

from pathlib import Path
import sys


def test_build_git_install_cmds_branch_variants():
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / 'src'
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    cmds = sync._build_git_install_cmds('prompt-automation', 'https://example/repo.git', 'dev')
    # First attempt should use --ref dev; include base fallback too
    flat = [' '.join(c) for c in cmds]
    assert any(' --git-branch dev' in s for s in flat)
    # One of the generated commands should be a package install
    assert any('package install' in s for s in flat)


def test_active_branch_override_env(monkeypatch, tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / 'src'
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    # Override has priority
    assert sync._active_branch(tmp_path, 'feature/x') == 'feature/x'
    # Env fallback
    monkeypatch.setenv('PA_GIT_BRANCH', 'release/y')
    assert sync._active_branch(tmp_path, None) == 'release/y'
