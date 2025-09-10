"""Uninstall executor orchestrating detection, planning and execution."""

from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import sys
from typing import Iterable

from .artifacts import Artifact
from . import detectors


_DEF_DETECTORS: Iterable = (
    detectors.detect_pip_install,
    detectors.detect_editable_repo,
    detectors.detect_espanso_package,
    detectors.detect_systemd_units,
    detectors.detect_desktop_entries,
    detectors.detect_symlink_wrappers,
    detectors.detect_data_dirs,
)


def run(options: "UninstallOptions") -> list[dict[str, object]]:
    """Run the uninstall routine using provided options."""
    platform = options.platform or sys.platform
    artifacts: list[Artifact] = []
    for func in _DEF_DETECTORS:
        try:
            artifacts.extend(func(platform))
        except Exception:
            # ignore detector failures, continue
            continue

    if options.keep_user_data or not options.purge_data:
        artifacts = [a for a in artifacts if not a.purge_candidate]

    results = []
    privileged = True
    if os.name != "nt":
        try:
            privileged = os.geteuid() == 0
        except AttributeError:
            privileged = False

    for art in artifacts:
        status = "absent"
        backup_path: Path | None = None
        if art.present():
            if art.requires_privilege and not privileged:
                status = "needs-privilege"
            elif options.dry_run:
                status = "planned"
            else:
                backup_path = _backup(art)
                _remove(art)
                status = "removed"
        results.append(
            {
                "id": art.id,
                "kind": art.kind,
                "path": str(art.path),
                "status": status,
                "backup": str(backup_path) if backup_path else None,
            }
        )

    if options.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['kind']:20} {r['path']} -> {r['status']}")
    return results


def _backup(artifact: Artifact) -> Path | None:
    """Create a backup copy of the artifact before removal."""
    backup_root = Path.home() / ".prompt-automation" / "backups"
    try:
        backup_root.mkdir(parents=True, exist_ok=True)
        target = backup_root / artifact.path.name
        if artifact.path.is_dir():
            shutil.copytree(artifact.path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(artifact.path, target)
        return target
    except Exception:
        return None


def _remove(artifact: Artifact) -> None:
    """Remove the artifact from the filesystem."""
    try:
        if artifact.path.is_dir():
            shutil.rmtree(artifact.path)
        else:
            artifact.path.unlink()
    except FileNotFoundError:
        pass
