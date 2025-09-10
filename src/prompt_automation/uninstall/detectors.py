"""Artifact detectors for the uninstall routine."""

from __future__ import annotations

from pathlib import Path
import sys
import os
import importlib.metadata
import site

from .artifacts import Artifact


def _platform_value(platform: str | None) -> str:
    return platform or sys.platform


def detect_pip_install(platform: str | None = None) -> list[Artifact]:
    """Detect package installation location via ``pip``."""
    _platform_value(platform)  # placeholder to satisfy signature
    artifacts: list[Artifact] = []
    try:
        dist = importlib.metadata.distribution("prompt-automation")
        location = Path(dist.locate_file(""))
        try:
            requires_priv = location.is_relative_to(Path(sys.prefix)) and not location.is_relative_to(Path(site.USER_SITE))
        except Exception:
            requires_priv = str(location).startswith(sys.prefix) and not str(location).startswith(site.USER_SITE)
        artifacts.append(Artifact("pip-install", "pip", location, requires_privilege=requires_priv))
    except importlib.metadata.PackageNotFoundError:
        pass
    return [a for a in artifacts if a.present()]


def detect_editable_repo(platform: str | None = None) -> list[Artifact]:
    """Detect editable install metadata without targeting the repo itself."""

    arts: list[Artifact] = []
    repo_root = Path(__file__).resolve().parents[3]
    if not (repo_root / ".git").exists():
        return arts

    candidates: list[Path] = []
    for p_str in sys.path:
        base = Path(p_str)
        # Pip may use either hyphen or underscore naming conventions
        candidates.append(base / "prompt_automation.egg-link")
        candidates.append(base / "prompt-automation.egg-link")
        for info_dir in ["prompt_automation.egg-info", "prompt_automation.dist-info"]:
            candidates.append(base / info_dir / "entry_points.txt")

    for path in candidates:
        if path.exists():
            arts.append(
                Artifact(
                    "editable-metadata",
                    "repo",
                    path,
                    repo_protected=True,
                )
            )

    return arts


def detect_espanso_package(platform: str | None = None) -> list[Artifact]:
    """Detect installed espanso package."""
    platform = _platform_value(platform)
    if platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / "espanso" / "match" / "packages" / "prompt-automation"
    else:
        base = Path.home() / ".local" / "share" / "espanso" / "match" / "packages" / "prompt-automation"
    art = Artifact("espanso-package", "espanso", base, purge_candidate=True)
    return [art] if art.present() else []


def detect_systemd_units(platform: str | None = None) -> list[Artifact]:
    """Detect systemd unit files."""
    platform = _platform_value(platform)
    arts: list[Artifact] = []
    if platform.startswith("linux"):
        user_unit = Path.home() / ".config" / "systemd" / "user" / "prompt-automation.service"
        system_unit = Path("/etc/systemd/system/prompt-automation.service")
        arts.append(Artifact("systemd-user", "systemd", user_unit))
        arts.append(Artifact("systemd-system", "systemd", system_unit, requires_privilege=True))
    return [a for a in arts if a.present()]


def detect_desktop_entries(platform: str | None = None) -> list[Artifact]:
    """Detect desktop or autostart entries."""
    platform = _platform_value(platform)
    arts: list[Artifact] = []
    if platform.startswith("linux"):
        autostart = Path.home() / ".config" / "autostart" / "prompt-automation.desktop"
        desktop = Path.home() / ".local" / "share" / "applications" / "prompt-automation.desktop"
        arts.append(Artifact("autostart-entry", "desktop", autostart))
        arts.append(Artifact("desktop-entry", "desktop", desktop))
    return [a for a in arts if a.present()]


def detect_symlink_wrappers(platform: str | None = None) -> list[Artifact]:
    """Detect wrapper scripts or symlinks placed on PATH."""
    platform = _platform_value(platform)
    arts: list[Artifact] = []
    if platform.startswith(("linux", "darwin")):
        user_bin = Path.home() / "bin" / "prompt-automation"
        system_bin = Path("/usr/local/bin/prompt-automation")
        arts.append(Artifact("user-wrapper", "symlink", user_bin))
        arts.append(Artifact("system-wrapper", "symlink", system_bin, requires_privilege=True))
    elif platform.startswith("win"):
        scripts = Path(os.environ.get("USERPROFILE", Path.home())) / "Scripts"
        arts.append(Artifact("windows-wrapper", "symlink", scripts / "prompt-automation.exe"))
    return [a for a in arts if a.present()]


def detect_data_dirs(platform: str | None = None) -> list[Artifact]:
    """Detect configuration and cache directories."""
    _platform_value(platform)
    home = Path.home()
    # Follow the XDG base directory specification for config and cache data
    config_dir = home / ".config" / "prompt-automation"
    cache_dir = home / ".cache" / "prompt-automation"
    log_dir = config_dir / "logs"
    arts = [
        Artifact("config-dir", "data", config_dir, purge_candidate=True),
        Artifact("cache-dir", "data", cache_dir, purge_candidate=True),
        Artifact("log-dir", "data", log_dir, purge_candidate=True),
    ]
    return [a for a in arts if a.present()]
