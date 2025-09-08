from __future__ import annotations

"""Utility commands for managing the local Espanso environment.

Provides a cross-platform cleanup that:
 - Lists or backs up/removes local match files (Windows/macOS/Linux paths)
 - Uninstalls legacy/conflicting packages installed from the same repo
 - Optionally performs a deep cleanup of all local match files
"""

import os
import platform
import shutil
import time
from pathlib import Path
from typing import List

from ..espanso_sync import (
    _espanso_bin,
    _run,
    _resolve_conflicts,
    _find_repo_root,
    _git_remote,
    _read_manifest,
)


def _match_dir_candidates() -> List[Path]:
    home = Path.home()
    system = platform.system()
    candidates: List[Path] = []
    # Linux/WSL
    candidates.append(home / ".config" / "espanso" / "match")
    # macOS
    candidates.append(home / "Library" / "Application Support" / "espanso" / "match")
    # Windows
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "espanso" / "match")
    # Deduplicate while preserving order
    seen = set()
    uniq: List[Path] = []
    for c in candidates:
        p = c.resolve()
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


def _list_local_matches() -> List[Path]:
    files: List[Path] = []
    for d in _match_dir_candidates():
        if d.exists():
            files.extend(sorted(d.glob("*.yml")))
    return files


def _backup_and_remove(files: List[Path]) -> Path | None:
    if not files:
        return None
    # Use the first file's parent as the backup base
    base_dir = files[0].parent
    ts = str(int(time.time()))
    backup_dir = base_dir / f"backup.{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        try:
            shutil.copy2(f, backup_dir / f.name)
            f.unlink(missing_ok=True)
        except Exception:
            pass
    return backup_dir


def clean_env(*, deep: bool = False, list_only: bool = False) -> None:
    """Reset local espanso state safely across OSes.

    - Lists local match files when list_only=True.
    - When deep=False, only targets base.yml/base.yaml for removal with backup.
    - When deep=True, backs up and removes all local match/*.yml.
    - Removes legacy/conflicting packages installed from the same repo (best effort).
    - Restarts espanso when available.
    """
    files = _list_local_matches()
    if list_only:
        print("Local match files:")
        for f in files:
            print(" -", f)
        # Also print installed packages for quick visibility
        bin_ = _espanso_bin()
        if bin_:
            _run(bin_ + ["package", "list"], timeout=10)
        return

    targets: List[Path] = []
    if deep:
        targets = files
    else:
        for f in files:
            if f.name.lower() in {"base.yml", "base.yaml"}:
                targets.append(f)

    backup_dir = _backup_and_remove(targets)
    if backup_dir:
        print(f"[espanso-clean] Backed up {len(targets)} file(s) to {backup_dir} and removed originals")
    else:
        print("[espanso-clean] No local files removed")

    # Remove conflicting packages pointing at the same repo
    repo_root = None
    repo_url = None
    pkg_name = "prompt-automation"
    try:
        repo_root = _find_repo_root(None)
        repo_url = _git_remote(repo_root)
        pkg_name, _ = _read_manifest(repo_root)
    except SystemExit:
        # Not fatal if repo not found; still remove legacy packages by URL when available
        pass
    try:
        _resolve_conflicts(pkg_name, repo_url, None)
    except Exception:
        pass

    # Restart espanso (best effort)
    try:
        bin_ = _espanso_bin()
        if bin_:
            _run(bin_ + ["restart"], timeout=8)
            _run(bin_ + ["package", "list"], timeout=10)
    except Exception:
        pass

