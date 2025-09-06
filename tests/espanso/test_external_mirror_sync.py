import pathlib
import re
from typing import Dict, List, Tuple

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML required for espanso tests")


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_PKG_DIR = REPO_ROOT / "espanso-package"
EXT_PKGS_BASE = REPO_ROOT / "packages"


def _semver_key(v: str) -> Tuple[int, int, int]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v)
    if not m:
        return (0, 0, 0)
    return tuple(map(int, m.groups()))  # type: ignore[return-value]


def _read_yaml(path: pathlib.Path):
    return yaml.safe_load(path.read_text())


def _collect_triggers(match_dir: pathlib.Path) -> Dict[str, List[str]]:
    triggers: Dict[str, List[str]] = {}
    for p in sorted(match_dir.glob("*.yml")):
        data = _read_yaml(p)
        for entry in (data or {}).get("matches", []) or []:
            t = entry.get("trigger")
            if isinstance(t, str):
                triggers.setdefault(t, []).append(p.name)
    return triggers


def test_external_layout_mirrors_source_if_present():
    # Skip gracefully if external layout not present
    if not EXT_PKGS_BASE.exists():
        pytest.skip("packages/ not present; external layout mirror is optional")

    # Require espanso-package to exist
    assert SRC_PKG_DIR.exists(), "espanso-package missing"

    # Determine package name from manifest
    manifest_path = SRC_PKG_DIR / "_manifest.yml"
    assert manifest_path.exists(), "espanso-package/_manifest.yml missing"
    msrc = _read_yaml(manifest_path)
    pkg_name = msrc.get("name", "prompt-automation")

    ext_base = EXT_PKGS_BASE / pkg_name
    if not ext_base.exists():
        pytest.skip(f"packages/{pkg_name} not present; run sync runbook to generate")

    # Find latest semver dir
    versions = [d.name for d in ext_base.iterdir() if d.is_dir() and re.match(r"^\d+\.\d+\.\d+$", d.name)]
    assert versions, f"No version directories found under packages/{pkg_name}"
    latest = sorted(versions, key=_semver_key)[-1]
    ext_dir = ext_base / latest

    # Manifest parity
    mext = _read_yaml(ext_dir / "_manifest.yml")
    assert mext.get("name") == msrc.get("name")
    # Version should match source manifest version
    assert mext.get("version") == msrc.get("version"), "External version should match source manifest version"

    # Match files parity (triggers, not byte-for-byte)
    src_triggers = _collect_triggers(SRC_PKG_DIR / "match")
    ext_triggers = _collect_triggers(ext_dir / "match")
    assert set(src_triggers.keys()) == set(ext_triggers.keys()), "Triggers differ between source and external layout"


def test_no_duplicate_triggers_in_external_if_present():
    if not EXT_PKGS_BASE.exists():
        pytest.skip("packages/ not present; external layout mirror is optional")

    # Determine any one package
    names = [d.name for d in EXT_PKGS_BASE.iterdir() if d.is_dir()]
    if not names:
        pytest.skip("No packages present under packages/")

    for name in names:
        base = EXT_PKGS_BASE / name
        versions = [d.name for d in base.iterdir() if d.is_dir() and re.match(r"^\d+\.\d+\.\d+$", d.name)]
        if not versions:
            continue
        latest = sorted(versions, key=_semver_key)[-1]
        match_dir = base / latest / "match"
        triggers = _collect_triggers(match_dir)
        dups = {t: files for t, files in triggers.items() if len(files) > 1}
        assert not dups, f"Duplicate triggers in external package {name}@{latest}: {dups}"
