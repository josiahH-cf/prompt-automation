"""Uninstall executor orchestrating detection, planning and execution."""

from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import sys
from typing import Iterable
from datetime import datetime

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


def run(options: "UninstallOptions") -> tuple[int, dict[str, object]]:
    """Run the uninstall routine using provided options.

    Returns a tuple ``(exit_code, results)`` where ``results`` is a dictionary
    grouping processed artifacts into ``removed``, ``skipped`` and ``errors``.
    ``exit_code`` follows the convention used by the CLI: ``0`` for success,
    ``1`` for invalid options and ``2`` when a removal operation failed.
    ``results`` also contains a ``partial`` flag indicating whether any
    artifacts were skipped or failed.
    """

    if options.purge_data and options.keep_user_data:
        print("Cannot use --purge-data with --keep-user-data", file=sys.stderr)
        return 1, []

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

    results: dict[str, object] = {
        "removed": [],
        "skipped": [],
        "errors": [],
        "partial": False,
    }
    privileged = True
    if os.name != "nt":
        try:
            privileged = os.geteuid() == 0
        except AttributeError:
            privileged = False

    removal_failed = False
    backup_root: Path | None = None

    for art in artifacts:
        status = "absent"
        backup_path: Path | None = None
        if art.present():
            if art.requires_privilege and not privileged:
                status = "needs-privilege"
                removal_failed = True
            elif options.dry_run:
                status = "planned"
            else:
                proceed = True
                if not options.force and not options.non_interactive:
                    try:
                        resp = input(f"Remove {art.path}? [y/N]: ").strip().lower()
                    except EOFError:
                        resp = "n"
                    proceed = resp in ("y", "yes")
                if proceed:
                    if options.purge_data and art.purge_candidate and not options.no_backup:
                        if backup_root is None:
                            ts = datetime.now().strftime("%Y%m%d%H%M%S")
                            backup_root = Path.home() / ".config" / f"prompt-automation.backup.{ts}"
                        try:
                            backup_root.mkdir(parents=True, exist_ok=True)
                            backup_path = _backup(art, backup_root)
                        except PermissionError:
                            print(f"[prompt-automation] Warning: insufficient permissions to back up {art.path}")
                            status = "permission-denied"
                            removal_failed = True
                            proceed = False
                    if proceed:
                        try:
                            success = _remove(art)
                        except PermissionError:
                            print(f"[prompt-automation] Warning: insufficient permissions to remove {art.path}")
                            status = "permission-denied"
                            removal_failed = True
                        else:
                            if not success or art.present():
                                status = "failed"
                                removal_failed = True
                            else:
                                status = "removed"
                    else:
                        removal_failed = True
                if not proceed and status == "absent":
                    status = "skipped"
                    removal_failed = True
        entry = {
            "id": art.id,
            "kind": art.kind,
            "path": str(art.path),
            "status": status,
            "backup": str(backup_path) if backup_path else None,
        }
        if status in ("removed", "planned"):
            results["removed"].append(entry)
        elif status == "skipped":
            results["skipped"].append(entry)
        elif status in ("failed", "needs-privilege", "permission-denied"):
            results["errors"].append(entry)

    results["partial"] = removal_failed

    if options.json:
        print(json.dumps(results, indent=2))
    else:
        rows: list[tuple[str, str]] = []
        for r in results["removed"]:
            label = "would remove" if r["status"] == "planned" else "removed"
            rows.append((label, r["path"]))
        for r in results["skipped"]:
            rows.append(("skipped", r["path"]))
        for r in results["errors"]:
            rows.append((r["status"], r["path"]))
        if rows:
            width = max(len(a) for a, _ in rows) + 2
            print(f"{'Action':{width}}Path")
            for act, path in rows:
                print(f"{act:{width}}{path}")
        else:
            print("No artifacts to process.")
        print(
            f"\nSummary: removed={len(results['removed'])} "
            f"skipped={len(results['skipped'])} errors={len(results['errors'])}"
        )
        if options.dry_run:
            print("DRY RUN: no changes made.")

    return (2 if removal_failed else 0), results


def _backup(artifact: Artifact, root: Path) -> Path | None:
    """Create a backup copy of the artifact before removal."""
    try:
        target = root / artifact.path.name
        if artifact.path.is_dir():
            shutil.copytree(artifact.path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(artifact.path, target)
        return target
    except PermissionError:
        raise
    except Exception:
        return None


def _remove(artifact: Artifact) -> bool:
    """Remove the artifact from the filesystem.

    Returns ``True`` if the artifact was removed successfully or already
    absent.  ``False`` is returned when a failure occurred.
    """
    try:
        if artifact.path.is_dir():
            shutil.rmtree(artifact.path)
        else:
            artifact.path.unlink()
        return True
    except FileNotFoundError:
        return True
    except PermissionError:
        raise
    except Exception:
        return False
