from __future__ import annotations

from pathlib import Path


def test_prune_local_defaults_attempts_deletion(monkeypatch, tmp_path: Path):
    import importlib
    import sys
    # Ensure module path
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    # Seed Linux-style base files
    lin_match = tmp_path / ".config" / "espanso" / "match"
    lin_match.mkdir(parents=True)
    (lin_match / "base.yml").write_text("matches: []\n", encoding="utf-8")
    (lin_match / "base.yaml").write_text("matches: []\n", encoding="utf-8")
    monkeypatch.setattr(sync.Path, "home", lambda: tmp_path)

    # Seed Windows-style base files
    appdata = tmp_path / "AppData" / "Roaming"
    win_match = appdata / "espanso" / "match"
    win_match.mkdir(parents=True)
    (win_match / "base.yml").write_text("matches: []\n", encoding="utf-8")
    (win_match / "base.yaml").write_text("matches: []\n", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(appdata))

    events = []

    def fake_j(status: str, step: str, **extra):
        events.append((status, step, extra))

    monkeypatch.setattr(sync, "_j", fake_j)

    sync._prune_local_defaults()

    # Both linux and windows defaults should be removed
    assert not (lin_match / "base.yml").exists()
    assert not (lin_match / "base.yaml").exists()
    assert not (win_match / "base.yml").exists()
    assert not (win_match / "base.yaml").exists()
    # Should log at least one prune event and create a disabled sentinel
    assert any(step == "prune_defaults" for _, step, _ in events)
    created = []
    for _, step, extra in events:
        if step == "prune_defaults" and "created" in extra:
            created.extend(extra["created"])  # type: ignore[index]
    assert any("disabled.yml" in p for p in created)
