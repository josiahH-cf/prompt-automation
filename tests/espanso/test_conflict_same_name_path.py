from __future__ import annotations

from pathlib import Path


def test_uninstall_same_name_path_variant(monkeypatch) -> None:
    import importlib
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import prompt_automation.espanso_sync as sync
    importlib.reload(sync)

    # Simulate installed packages output containing the same name with a path source
    def fake_list():
        return [{"name": "prompt-automation", "version": "0.1.0", "source": "path: C:/Users/me/espanso/prompt-automation"}]

    uninstalled: list[str] = []

    def fake_uninstall(name: str) -> None:
        uninstalled.append(name)

    monkeypatch.setattr(sync, "_list_installed_packages", fake_list)
    monkeypatch.setattr(sync, "_uninstall_package", fake_uninstall)

    sync._resolve_conflicts("prompt-automation", repo_url="https://github.com/josiahH-cf/prompt-automation.git", local_path=Path("/tmp/pkgs/prompt-automation/0.0.1"))

    assert uninstalled == ["prompt-automation"], "should uninstall same-named path-based install"

