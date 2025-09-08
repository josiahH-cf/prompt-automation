from __future__ import annotations

from pathlib import Path
import sys


def _write_minimal_pkg(root: Path, name: str = "prompt-automation", version: str = "0.0.2") -> None:
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
        "matches:\n  - trigger: ':t.cli'\n    replace: 'OK'\n",
        encoding="utf-8",
    )


def test_cli_espanso_sync_entry_skips_install_and_mirrors(tmp_path: Path, monkeypatch) -> None:
    # Prepare temp repo and environment
    _write_minimal_pkg(tmp_path)
    monkeypatch.setenv("PROMPT_AUTOMATION_REPO", str(tmp_path))
    monkeypatch.setenv("PA_SKIP_INSTALL", "1")

    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # Call the real CLI entry
    from prompt_automation.cli import cli as cli_mod
    cli_mod.main(["--espanso-sync", "--espanso-skip-install"])  # should not raise

    # Validate mirror exists (auto-bumped patch version)
    ext = tmp_path / "packages" / "prompt-automation" / "0.0.3"
    assert (ext / "_manifest.yml").exists()
    assert (ext / "package.yml").exists()
    assert (ext / "match" / "basic.yml").exists()

