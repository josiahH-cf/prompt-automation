from __future__ import annotations

import os
from pathlib import Path
import sys

# Ensure repository sources are importable without installing the package
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _call_helper() -> None:
    # Import inside to avoid side effects during collection
    from prompt_automation.espanso_sync import _ensure_undo_backspace_disabled

    _ensure_undo_backspace_disabled()


def test_creates_default_with_undo_backspace_false(tmp_path: Path, monkeypatch) -> None:
    # Point HOME to temp so Linux location ~/.config/espanso/config is used
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg_dir = tmp_path / ".config" / "espanso" / "config"
    assert not (cfg_dir / "default.yml").exists()

    _call_helper()

    text = (cfg_dir / "default.yml").read_text(encoding="utf-8")
    assert "undo_backspace: false" in text


def test_patches_existing_true_to_false(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg_dir = tmp_path / ".config" / "espanso" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "default.yml").write_text("undo_backspace: true\nother: keep\n", encoding="utf-8")

    _call_helper()

    text = (cfg_dir / "default.yml").read_text(encoding="utf-8")
    # Ensure it's flipped to false and other keys remain
    assert "undo_backspace: false" in text
    assert "other: keep" in text
