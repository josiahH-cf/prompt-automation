import pathlib
from typing import Dict, List, Set

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML is required for espanso YAML validation tests")


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_PKG_DIR = REPO_ROOT / "espanso-package"
# Resolve package name dynamically from source manifest
_name = "prompt-automation"
_mf = SRC_PKG_DIR / "_manifest.yml"
if _mf.exists():
    import yaml as _yaml
    try:
        _data = _yaml.safe_load(_mf.read_text()) or {}
        if isinstance(_data.get("name"), str):
            _name = _data["name"]
    except Exception:
        pass
EXT_PKG_BASE = REPO_ROOT / "packages" / _name
LATEST = None
if EXT_PKG_BASE.exists():
    # Prefer a semantic version directory if present, else ignore backups
    ver_dirs = sorted(
        (p for p in EXT_PKG_BASE.iterdir() if p.is_dir() and p.name not in {"_backup"}),
        key=lambda p: p.name,
    )
    # Filter to X.Y.Z style names
    import re as _re
    semver_dirs = [p for p in ver_dirs if _re.match(r"^\d+\.\d+\.\d+$", p.name)]
    if semver_dirs:
        LATEST = semver_dirs[-1]
PKG_DIR = LATEST if LATEST else SRC_PKG_DIR


def _yaml_files() -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    files.append(PKG_DIR / "_manifest.yml")
    files.append(PKG_DIR / "package.yml")
    files.extend(sorted((PKG_DIR / "match").glob("*.yml")))
    return [p for p in files if p.exists()]


def test_manifest_fields_present():
    manifest_path = PKG_DIR / "_manifest.yml"
    assert manifest_path.exists(), "_manifest.yml missing"
    data = yaml.safe_load(manifest_path.read_text())
    assert isinstance(data, dict)
    for field in ("name", "title", "version", "description", "author"):
        assert field in data and str(data[field]).strip(), f"Missing manifest field: {field}"


def test_package_yaml_parses():
    pkg_yaml = PKG_DIR / "package.yml"
    assert pkg_yaml.exists(), "package.yml missing"
    data = yaml.safe_load(pkg_yaml.read_text())
    assert isinstance(data, dict)
    assert data.get("name"), "package.yml must declare a name"


def test_all_match_yamls_parse_and_have_valid_structure():
    match_dir = PKG_DIR / "match"
    assert match_dir.exists(), "match/ directory missing"
    match_files = sorted(match_dir.glob("*.yml"))
    assert match_files, "No match/*.yml files found"

    for f in match_files:
        content = yaml.safe_load(f.read_text())
        assert isinstance(content, dict), f"{f} must be a mapping"
        assert "matches" in content, f"{f} missing 'matches' key"
        matches = content["matches"]
        assert isinstance(matches, list), f"{f} 'matches' must be a list"
        for i, entry in enumerate(matches):
            assert isinstance(entry, dict), f"{f} matches[{i}] must be a mapping"
            # Espanso supports 'trigger' or 'regex'. At least one should exist.
            has_trigger = isinstance(entry.get("trigger"), str) and entry.get("trigger").strip() != ""
            has_regex = isinstance(entry.get("regex"), str) and entry.get("regex").strip() != ""
            assert has_trigger or has_regex, f"{f} matches[{i}] needs 'trigger' or 'regex'"
            # If trigger present, ensure a 'replace' or 'form' or 'vars' exist
            if has_trigger:
                has_replace = isinstance(entry.get("replace"), (str, dict)) and str(entry.get("replace")).strip() != ""
                has_form = isinstance(entry.get("form"), dict)
                has_vars = isinstance(entry.get("vars"), list)
                assert has_replace or has_form or has_vars, (
                    f"{f} matches[{i}] with 'trigger' should define 'replace', 'form' or 'vars'"
                )


def test_no_duplicate_triggers_across_all_match_files():
    match_files = sorted((PKG_DIR / "match").glob("*.yml"))
    triggers: Dict[str, List[str]] = {}
    for f in match_files:
        data = yaml.safe_load(f.read_text())
        for entry in data.get("matches", []) or []:
            t = entry.get("trigger")
            if isinstance(t, str):
                triggers.setdefault(t, []).append(f.name)

    dups = {t: files for t, files in triggers.items() if len(files) > 1}
    assert not dups, f"Duplicate triggers found: {dups}"


def test_trigger_style_conventions():
    """Basic hygiene: triggers should be strings, start with ':', and contain no spaces."""
    match_files = sorted((PKG_DIR / "match").glob("*.yml"))
    bad = []
    for f in match_files:
        data = yaml.safe_load(f.read_text())
        for entry in data.get("matches", []) or []:
            t = entry.get("trigger")
            if isinstance(t, str):
                if not t.startswith(":") or (" " in t):
                    bad.append((f.name, t))
    assert not bad, f"Triggers violate style (start with ':' and no spaces): {bad}"
