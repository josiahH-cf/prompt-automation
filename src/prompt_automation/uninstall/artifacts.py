"""Artifact definitions for the uninstall subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Artifact:
    """Represents a removable component on the filesystem."""

    id: str
    kind: str
    path: Path
    requires_privilege: bool = False
    purge_candidate: bool = False
    repo_protected: bool = False
    interpreter: Path | None = None

    def present(self) -> bool:
        """Return ``True`` if the artifact exists on disk."""
        return self.path.exists()
