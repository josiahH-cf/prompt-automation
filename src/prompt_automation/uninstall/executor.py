"""Uninstall executor orchestrating detection, planning and execution."""

from __future__ import annotations

from pathlib import Path
import json
import logging
import os
import shutil
import sys
from typing import Iterable
from datetime import datetime

from .artifacts import Artifact
from . import detectors, multi_python, orphan
from ..errorlog import get_logger


# Detectors used for core uninstall operations. Optional detectors that remove
# ancillary artifacts are enabled when the ``--all`` flag is provided.
_DEF_DETECTORS: Iterable = (
    detectors.detect_pip_install,
    detectors.detect_editable_repo,
)

# Extended detector set enabled by ``--all``.
_OPT_DETECTORS: Iterable = (
    detectors.detect_espanso_package,
    detectors.detect_systemd_units,
    detectors.detect_desktop_entries,
    detectors.detect_symlink_wrappers,
    detectors.detect_data_dirs,
)

_log = get_logger(__name__)


def _determine_exit_code(removal_failed: bool, arg_error: bool) -> int:
    """Compute the final exit code.

    ``1`` is returned when the user supplied invalid arguments, ``2`` when
    removal failed for one or more artifacts and ``0`` on success.
    """
    if arg_error:
        return 1
    return 2 if removal_failed else 0


def _safe_path(p: Path) -> str:
    """Return path with home directory masked."""
    try:
        home = Path.home().resolve()
        p_resolved = p.resolve()
        if str(p_resolved).startswith(str(home)):
            rel = p_resolved.relative_to(home)
            return f"~/{rel}" if rel.parts else "~"
        return p_resolved.name
    except Exception:
        return p.name


def run(options: "UninstallOptions") -> tuple[int, dict[str, object]]:
    """Run the uninstall routine using provided options.

    Returns a tuple ``(exit_code, results)`` where ``results`` is a dictionary
    grouping processed artifacts into ``removed``, ``skipped`` and ``errors``.
    ``exit_code`` follows the convention used by the CLI: ``0`` for success,
    ``1`` for invalid options and ``2`` when a removal operation failed.
    ``results`` also contains a ``partial`` flag indicating whether any
    artifacts were skipped or failed.
    """

    arg_error = False
    if options.purge_data and options.keep_user_data:
        print("Cannot use --purge-data with --keep-user-data", file=sys.stderr)
        arg_error = True

    platform = options.platform or sys.platform
    if options.verbose:
        _log.setLevel(logging.DEBUG)
    _log.debug("starting uninstall on platform=%s", platform)
    artifacts: list[Artifact] = []
    if not arg_error:
        detector_funcs = list(_DEF_DETECTORS)
        if options.all:
            detector_funcs.extend(_OPT_DETECTORS)
        for func in detector_funcs:
            try:
                detected = func(platform)
                artifacts.extend(detected)
                _log.debug(
                    "detector %s found %d artifacts", func.__name__, len(detected)
                )
            except Exception:
                _log.debug("detector %s failed", func.__name__)
                continue

        if options.keep_user_data or not options.purge_data:
            artifacts = [a for a in artifacts if not a.purge_candidate]

        if options.confirm_orphans or options.remove_orphans:
            try:
                orphan_arts = orphan.detect_orphans(platform)
                artifacts.extend(orphan_arts)
                _log.debug("orphan detector found %d artifacts", len(orphan_arts))
            except Exception:
                _log.debug("orphan detector failed")

    results: dict[str, object] = {
        "removed": [],
        "skipped": [],
        "errors": [],
        "partial": False,
        "pending": [],
    }
    privileged = True
    if os.name != "nt":
        try:
            privileged = os.geteuid() == 0
        except AttributeError:
            privileged = False

    removal_failed = False
    pending_paths: list[Path] = []
    backup_root: Path | None = None
    repo_backup_root: Path | None = None

    if not arg_error:
        for art in artifacts:
            status = "absent"
            backup_path: Path | None = None
            safe = _safe_path(art.path)
            _log.debug("processing %s (%s)", art.id, safe)
            if art.present():
                if art.requires_privilege and not privileged:
                    status = "needs-privilege"
                    removal_failed = True
                    pending_paths.append(art.path)
                    msg = f"{art.id} requires elevated privileges"
                    _log.warning(msg)
                    print(f"[prompt-automation] Warning: {msg}")
                elif options.dry_run:
                    status = "planned"
                    _log.debug("would remove %s", art.id)
                else:
                    proceed = True
                    if art.kind == "orphan":
                        if not (
                            options.force
                            or options.non_interactive
                            or options.remove_orphans
                        ):
                            try:
                                resp = input(
                                    f"Remove orphan {safe}? [y/N]: "
                                ).strip().lower()
                            except EOFError:
                                resp = "n"
                            proceed = resp in ("y", "yes")
                    elif not options.force and not options.non_interactive:
                        try:
                            resp = input(f"Remove {safe}? [y/N]: ").strip().lower()
                        except EOFError:
                            resp = "n"
                        proceed = resp in ("y", "yes")
                    if proceed:
                        if not options.no_backup:
                            if art.repo_protected:
                                if repo_backup_root is None:
                                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                                    repo_backup_root = Path.home() / ".config" / f"prompt-automation.repo-backup.{ts}"
                                try:
                                    repo_backup_root.mkdir(parents=True, exist_ok=True)
                                    backup_path = _backup(art, repo_backup_root)
                                except PermissionError:
                                    msg = "insufficient permissions to back up artifact"
                                    _log.warning("%s: %s", msg, art.id)
                                    print(f"[prompt-automation] Warning: {msg}")
                                    status = "permission-denied"
                                    removal_failed = True
                                    proceed = False
                            elif options.purge_data and art.purge_candidate:
                                if backup_root is None:
                                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                                    backup_root = Path.home() / ".config" / f"prompt-automation.backup.{ts}"
                                try:
                                    backup_root.mkdir(parents=True, exist_ok=True)
                                    backup_path = _backup(art, backup_root)
                                except PermissionError:
                                    msg = "insufficient permissions to back up artifact"
                                    _log.warning("%s: %s", msg, art.id)
                                    print(f"[prompt-automation] Warning: {msg}")
                                    status = "permission-denied"
                                    removal_failed = True
                                    proceed = False
                        if proceed:
                            try:
                                success = _remove(art)
                            except PermissionError:
                                msg = "insufficient permissions to remove artifact"
                                _log.warning("%s: %s", msg, art.id)
                                print(f"[prompt-automation] Warning: {msg}")
                                status = "permission-denied"
                                removal_failed = True
                            else:
                                if not success or art.present():
                                    status = "failed"
                                    removal_failed = True
                                    _log.warning("failed to remove %s", art.id)
                                else:
                                    status = "removed"
                                    _log.debug("removed %s", art.id)
                        else:
                            removal_failed = True
                    if not proceed and status == "absent":
                        status = "skipped"
                        removal_failed = True
                        _log.warning("user skipped %s", art.id)
            entry = {
                "id": art.id,
                "kind": art.kind,
                "path": str(art.path),
                "status": status,
                "backup": str(backup_path) if backup_path else None,
                "interpreter": str(art.interpreter) if getattr(art, "interpreter", None) else None,
            }
            if status in ("removed", "planned"):
                results["removed"].append(entry)
            elif status == "skipped":
                results["skipped"].append(entry)
            elif status in ("failed", "needs-privilege", "permission-denied"):
                results["errors"].append(entry)

    results["pending"] = [str(p) for p in pending_paths]
    results["partial"] = removal_failed

    removed_count = len(results["removed"])
    skipped_count = len(results["skipped"])
    error_count = len(results["errors"])

    if options.json:
        print(json.dumps(results, indent=2))
    else:
        rows: list[tuple[str, str]] = []
        for r in results["removed"]:
            label = "would remove" if r["status"] == "planned" else "removed"
            rows.append((label, _safe_path(Path(r["path"]))))
        for r in results["skipped"]:
            rows.append(("skipped", _safe_path(Path(r["path"]))))
        for r in results["errors"]:
            rows.append((r["status"], _safe_path(Path(r["path"]))))
        if rows:
            width = max(len(a) for a, _ in rows) + 2
            print(f"{'Action':{width}}Path")
            for act, path in rows:
                print(f"{act:{width}}{path}")
        else:
            print("No artifacts to process.")
        print(
            f"\nSummary: removed={removed_count} "
            f"skipped={skipped_count} errors={error_count}"
        )
        if options.dry_run:
            print("DRY RUN: no changes made.")
        if pending_paths and not privileged and options.print_elevated_script:
            _print_elevated_script(pending_paths, platform)

    _log.info(
        "summary removed=%d skipped=%d errors=%d",
        removed_count,
        skipped_count,
        error_count,
    )
    if options.dry_run:
        _log.info("dry run: no changes made")
    exit_code = _determine_exit_code(removal_failed, arg_error)
    return exit_code, results


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
    """Remove the artifact from the filesystem or via interpreter pip."""

    try:
        if artifact.kind == "pip" and artifact.interpreter is not None:
            success, _output = multi_python.uninstall(artifact.interpreter)
            return success
        if artifact.path.is_dir():
            if getattr(artifact, "repo_protected", False):
                return True
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


def _print_elevated_script(paths: list[Path], platform: str) -> None:
    """Emit a script that removes the provided paths with elevated privileges."""
    if platform.startswith("win"):
        for p in paths:
            print(f'Remove-Item -Recurse -Force "{p}"')
    else:
        print("#!/bin/sh")
        for p in paths:
            print(f"rm -rf '{p}'")
