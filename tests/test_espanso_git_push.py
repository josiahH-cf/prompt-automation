from __future__ import annotations

from pathlib import Path


def test_commit_and_push_called(monkeypatch, tmp_path: Path):
    import importlib
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # sentinel to be treated as a git repo

    calls = []

    def fake_run(args, cwd=None, check=False, timeout=None):
        calls.append([str(a) for a in (args if isinstance(args, list) else [args])])
        s = " ".join(calls[-1])
        if " git add -A" in s:
            return 0, "", ""
        if " git commit -m" in s:
            # simulate clean tree (nothing to commit)
            return 1, "", "nothing to commit"
        if " git push" in s:
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(sync, "_run", fake_run)

    sync._git_commit_and_push(repo, "dev", "1.2.3")

    flat = [" ".join(c) for c in calls]
    assert any(f"git -C {repo} add -A" in s for s in flat)
    assert any("git -C" in s and "commit -m" in s and "1.2.3" in s for s in flat)
    assert any(f"git -C {repo} push origin dev" in s for s in flat)

