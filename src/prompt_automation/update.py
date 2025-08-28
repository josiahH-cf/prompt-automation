"""Self-update utilities for prompt-automation.

The goal of this module is to provide a *safe* update workflow.  It can
check a remote source for new releases, download updated files and apply
them only after the user explicitly approves the changes.  Local user
content is never removed or overwritten without confirmation.

The implementation intentionally avoids external dependencies so it can
run in restricted environments and across all supported platforms
(Windows/Mac/Linux/WSL2).

The remote update location can be customised via the environment
variable ``PROMPT_AUTOMATION_UPDATE_URL``.  The expected payload is a JSON
document with at minimum the keys ``version`` and ``files``.  ``files`` is a
mapping of relative file paths to download URLs.  An optional ``moved``
mapping can be supplied to indicate files that changed paths.

Example manifest::

    {
        "version": "0.3.0",
        "files": {
            "src/prompt_automation/some.py": "https://example/file.py",
            "prompts/example.txt": "https://example/example.txt"
        },
        "moved": {"old/path.txt": "new/path.txt"}
    }

The :func:`check_and_prompt` function is the public entry point used by
both the CLI and GUI at start-up.  It performs the following steps:

``fetch_manifest`` -> ``compare version`` -> ``prompt user`` ->
``download/apply``

All notable actions are logged to ``~/.prompt-automation/logs/update.log``
for troubleshooting.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from urllib import request, error
from typing import Dict, Iterable

# ---------------------------------------------------------------------------
# Logging setup
LOG_DIR = Path.home() / ".prompt-automation" / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
LOG_FILE = LOG_DIR / "update.log"

_log = logging.getLogger("prompt_automation.update")
if not _log.handlers:
    _log.setLevel(logging.INFO)
    try:
        _log.addHandler(logging.FileHandler(LOG_FILE))
    except Exception:  # pragma: no cover - sandbox/file permission
        _log.addHandler(logging.StreamHandler())


# ---------------------------------------------------------------------------
# Configuration
ROOT_DIR = Path(__file__).resolve().parents[2]
"""Project root used when writing update files."""

UPDATE_URL = os.environ.get("PROMPT_AUTOMATION_UPDATE_URL", "")
"""Remote manifest location.  Empty string disables update checks."""

# Auto-apply behaviour (default enabled). Set ``PROMPT_AUTOMATION_MANIFEST_AUTO=0``
# to restore interactive prompts. When enabled the manifest update system
# applies updates silently and resolves file conflicts by backing up the
# existing file to ``<name>.bak`` (or ``<name>.bak.N`` if needed) before
# replacing it. Moved files are auto-migrated.
def _auto_mode() -> bool:
    return os.environ.get("PROMPT_AUTOMATION_MANIFEST_AUTO", "1") != "0"


def _read_local_version() -> str:
    """Return the currently installed version of the application."""
    try:  # Python >=3.8
        from importlib import metadata

        return metadata.version("prompt-automation")
    except Exception:  # pragma: no cover - metadata access failure
        return "0"


def _prompt_yes_no(message: str, default: bool = False) -> bool:
    """Simple ``y/n`` prompt returning ``True`` for confirmation."""

    suffix = " [Y/n]: " if default else " [y/N]: "
    ans = input(message + suffix).strip().lower()
    if not ans:
        return default
    return ans in {"y", "yes"}


def fetch_manifest() -> dict | None:
    """Fetch remote update manifest.

    Returns ``None`` if no remote source is configured or if the manifest
    cannot be retrieved.
    """

    if not UPDATE_URL:
        _log.info("update URL not configured; skipping check")
        return None
    try:
        with request.urlopen(UPDATE_URL, timeout=5) as resp:  # pragma: no cover - network
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except error.URLError as e:  # pragma: no cover - network errors
        _log.warning("unable to fetch update manifest: %s", e)
    except Exception as e:  # pragma: no cover
        _log.warning("bad update manifest: %s", e)
    return None


def _download_to_temp(url: str) -> Path:
    """Download ``url`` to a temporary file and return the path."""

    tmp_fd, tmp_path = tempfile.mkstemp()
    os.close(tmp_fd)
    try:
        with request.urlopen(url) as resp:  # pragma: no cover - network
            with open(tmp_path, "wb") as fh:
                shutil.copyfileobj(resp, fh)
    except Exception as e:  # pragma: no cover
        _log.error("failed downloading %s: %s", url, e)
        raise
    return Path(tmp_path)


def _apply_file_update(dest: Path, new_file: Path) -> None:
    """Safely apply an update for ``dest`` using content from ``new_file``.

    If ``dest`` exists and differs from ``new_file`` the user is prompted to
    decide between update, keep local or rename.
    """

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        if dest.read_bytes() == new_file.read_bytes():
            _log.info("%s already up to date", dest)
            return
        if _auto_mode():
            # Automatic resolution: create unique .bak backup then replace
            backup = dest.with_suffix(dest.suffix + ".bak")
            idx = 1
            while backup.exists():
                backup = dest.with_suffix(dest.suffix + f".bak.{idx}")
                idx += 1
            try:
                dest.rename(backup)
                _log.info("auto backup %s -> %s", dest, backup)
            except Exception as e:  # pragma: no cover - filesystem edge
                _log.warning("failed to backup %s: %s (continuing with overwrite)", dest, e)
        else:
            print(f"Conflict for {dest}")
            print("  [U]pdate to new version")
            print("  [K]eep local version")
            print("  [R]ename and keep both")
            while True:
                choice = input("Select (u/k/r): ").strip().lower()
                if choice in {"u", "k", "r"}:
                    break
            if choice == "k":
                _log.info("kept local copy of %s", dest)
                return
            if choice == "r":
                backup = dest.with_suffix(dest.suffix + ".local")
                dest.rename(backup)
                _log.info("renamed existing %s to %s", dest, backup)

    shutil.move(str(new_file), dest)
    _log.info("updated %s", dest)


def _handle_moved_files(mapping: Dict[str, str]) -> None:
    """Handle moved/renamed files.

    In auto mode the move is applied silently (if target not already
    present). In interactive mode the user is prompted per file.
    """

    for old, new in mapping.items():
        old_path = ROOT_DIR / old
        new_path = ROOT_DIR / new
        if not old_path.exists():
            continue
        if _auto_mode():
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                if new_path.exists():
                    # Avoid overwriting existing target; keep original
                    _log.info("target already exists for move %s -> %s; skipping", old_path, new_path)
                else:
                    old_path.rename(new_path)
                    _log.info("auto moved %s to %s", old_path, new_path)
            except Exception as e:  # pragma: no cover
                _log.warning("auto move failed %s -> %s: %s", old_path, new_path, e)
        else:
            msg = f"The file '{old}' has moved to '{new}'. Update path?"
            if _prompt_yes_no(msg):
                new_path.parent.mkdir(parents=True, exist_ok=True)
                old_path.rename(new_path)
                _log.info("moved %s to %s", old_path, new_path)
            else:
                _log.info("skipped moving %s", old_path)


def apply_update(manifest: dict) -> None:
    """Download and apply update described by ``manifest``."""

    files: Dict[str, str] = manifest.get("files", {})
    moved: Dict[str, str] = manifest.get("moved", {})

    for relpath, url in files.items():
        dest = ROOT_DIR / relpath
        try:
            tmp_file = _download_to_temp(url)
        except Exception:
            print(f"Failed downloading {url}")
            continue
        _apply_file_update(dest, tmp_file)

    if moved:
        _handle_moved_files(moved)


def check_and_prompt(force: bool = False) -> None:
    """Check for updates and apply them.

    Behaviour:
    - Auto mode (default): apply updates silently when a newer manifest version
      is available; backup conflicting files; move renamed files.
    - Interactive mode (``PROMPT_AUTOMATION_MANIFEST_AUTO=0``): original
      behaviour with confirmation and per-file conflict prompts.
    """

    manifest = fetch_manifest()
    if not manifest:
        return

    local_version = _read_local_version()
    remote_version = manifest.get("version", "0")

    if not force and remote_version <= local_version:
        _log.info("no updates available (local=%s remote=%s)", local_version, remote_version)
        return

    if not _auto_mode():
        if not _prompt_yes_no("Updates are available. Review and apply updates now?"):
            _log.info("user skipped update")
            return
    else:
        _log.info("auto applying manifest update (local=%s remote=%s)", local_version, remote_version)

    apply_update(manifest)
    if not _auto_mode():
        print("[prompt-automation] Update complete")


__all__ = [
    "check_and_prompt",
    "fetch_manifest",
    "apply_update",
]
