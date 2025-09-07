from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _write_minimal_pkg(root: Path, name: str = "prompt-automation", version: str = "0.0.1") -> None:
    pkg = root / "espanso-package"
    (pkg / "match").mkdir(parents=True, exist_ok=True)
    (pkg / "_manifest.yml").write_text(
        f"name: {name}\n"
        f"title: 'Prompt-Automation Snippets'\n"
        f"version: {version}\n"
        f"description: 'Test'\n"
        f"author: 'Test'\n",
        encoding="utf-8",
    )
    (pkg / "package.yml").write_text("name: prompt-automation\ndependencies: []\n", encoding="utf-8")
    (pkg / "match" / "basic.yml").write_text(
        "matches:\n  - trigger: ':t.ok'\n    replace: 'OK'\n",
        encoding="utf-8",
    )


def run_sync(repo: Path, args: list[str]) -> int:
    # Ensure local src is importable without editable install
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from prompt_automation import espanso_sync as sync
    try:
        sync.main(["--repo", str(repo), *args])
        return 0
    except SystemExit as e:  # main may use SystemExit on error
        return int(e.code) if isinstance(e.code, int) else 1


def test_sync_dry_run_validates_and_mirrors(tmp_path: Path) -> None:
    _write_minimal_pkg(tmp_path)
    code = run_sync(tmp_path, ["--dry-run"])  # mirror should proceed; install skipped
    assert code == 0
    # External mirror exists
    ext = tmp_path / "packages" / "prompt-automation" / "0.0.1"
    assert (ext / "_manifest.yml").exists()
    assert (ext / "package.yml").exists()
    assert (ext / "match" / "basic.yml").exists()


def test_sync_duplicate_rejected(tmp_path: Path) -> None:
    _write_minimal_pkg(tmp_path)
    # Add a duplicate trigger across files
    (tmp_path / "espanso-package" / "match" / "b.yml").write_text(
        "matches:\n  - trigger: ':t.ok'\n    replace: 'X'\n",
        encoding="utf-8",
    )
    code = run_sync(tmp_path, ["--dry-run"])  # should fail validation
    assert code != 0


def test_sync_trigger_yaml_present() -> None:
    # Ensure repo ships the :pa.sync trigger match and command references CLI
    repo = Path(__file__).resolve().parents[2]
    sync_yaml = repo / "espanso-package" / "match" / "prompt_automation_sync.yml"
    assert sync_yaml.exists(), "prompt_automation_sync.yml missing"
    txt = sync_yaml.read_text(encoding="utf-8")
    assert ":pa.sync" in txt
    # command should reference prompt-automation CLI for portability
    assert "prompt-automation --espanso-sync" in txt
