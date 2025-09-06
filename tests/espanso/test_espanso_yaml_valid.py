import pathlib
from typing import Dict, List, Set

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML is required for espanso YAML validation tests")


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG_DIR = REPO_ROOT / "espanso-package"


def _yaml_files() -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    # top-level package files
    files.append(PKG_DIR / "_manifest.yml")
    files.append(PKG_DIR / "package.yml")
    # all match files
    files.extend(sorted((PKG_DIR / "match").glob("*.yml")))
    return [p for p in files if p.exists()]


def test_manifest_fields_present():
    manifest_path = PKG_DIR / "_manifest.yml"
    assert manifest_path.exists(), "_manifest.yml missing"
    data = yaml.safe_load(manifest_path.read_text())
    assert isinstance(data, dict)
    for field in ("name", "version", "description", "author"):
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

