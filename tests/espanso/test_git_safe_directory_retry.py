from __future__ import annotations

from pathlib import Path


def test_git_push_retries_after_dubious(monkeypatch, tmp_path: Path) -> None:
    import importlib
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    repo = tmp_path / "r"
    (repo / ".git").mkdir(parents=True)

    calls: list[list[str]] = []

    def fake_run(args, cwd=None, check=False, timeout=None):
        if isinstance(args, list):
            calls.append([str(a) for a in args])
            s = " ".join(args)
            # add
            if s.endswith(" git add -A"):
                return 0, "", ""
            # commit may be skipped (nothing to commit)
            if " git commit -m" in s:
                return 0, "", ""
            # first push fails with dubious, second succeeds
            if " push" in s:
                pushes = [c for c in calls if any(part == "push" for part in c)]
                if len(pushes) == 1:
                    return 1, "", "fatal: detected dubious ownership in repository at '/tmp/test'"
                return 0, "", ""
            # safe.directory config OK
            if args[:4] == ["git", "config", "--global", "--add"] and args[4] == "safe.directory":
                return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(sync, "_run", fake_run)

    sync._git_commit_and_push(repo, branch="main", version="0.0.1")

    flattened = [" ".join(c) for c in calls]
    # Ensure we configured safe.directory and then pushed again
    assert any("git config --global --add safe.directory" in s for s in flattened)
    assert any("git -C" in s and "push origin main" in s for s in flattened)
