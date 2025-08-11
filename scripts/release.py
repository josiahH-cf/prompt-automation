#!/usr/bin/env python3
"""Release helper for prompt-automation.

Run from repository root:
    python scripts/release.py [--level patch|minor|major|set <version>] [--tag] [--publish]

Features:
- Bumps version in pyproject.toml
- Moves CHANGELOG 'Unreleased' section entries under new version heading with today's date
- Creates a clean 'Unreleased' placeholder
- Builds sdist and wheel (using `python -m build` if available, else setuptools)
- Optional: git commit + tag
- Optional: publish to PyPI via twine

Safety:
- Aborts if working tree is dirty (unless --allow-dirty)
- Validates semantic version format

Environment variables:
  RELEASE_ALLOW_DIRTY=1  (alternative to --allow-dirty)

"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path
import textwrap

def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(r"^version\s*=\s*['\"](?P<ver>[^'\"]+)['\"]", re.MULTILINE)
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[.-]?([A-Za-z0-9]+))?$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Release helper")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--level", choices=["patch", "minor", "major"], help="Semantic bump level")
    g.add_argument("--set", dest="set_version", help="Explicit version to set")
    p.add_argument("--tag", action="store_true", help="Create a git tag for the release")
    p.add_argument("--publish", action="store_true", help="Upload to PyPI via twine")
    p.add_argument("--allow-dirty", action="store_true", help="Allow dirty working tree")
    p.add_argument("--dry-run", action="store_true", help="Show changes only, no writes")
    return p.parse_args()


def get_current_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = VERSION_RE.search(text)
    if not m:
        print("ERROR: version not found in pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group("ver")


def bump_version(cur: str, level: str) -> str:
    m = SEMVER_RE.match(cur)
    if not m:
        print(f"ERROR: current version '{cur}' is not semantic", file=sys.stderr)
        sys.exit(1)
    major, minor, patch = map(int, m.groups()[:3])
    if level == "patch":
        patch += 1
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "major":
        major += 1
        minor = 0
        patch = 0
    return f"{major}.{minor}.{patch}"


def ensure_clean(allow: bool) -> None:
    if allow or os.environ.get("RELEASE_ALLOW_DIRTY") == "1":
        return
    res = run(["git", "status", "--porcelain"], check=True, capture=True)
    if res.stdout.strip():
        print("ERROR: working tree not clean. Commit or stash changes, or use --allow-dirty.", file=sys.stderr)
        sys.exit(1)


def update_pyproject(new_version: str, dry: bool) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text = VERSION_RE.sub(f"version = \"{new_version}\"", text, count=1)
    if dry:
        print("--- pyproject.toml (preview) ---")
        print(new_text)
    else:
        PYPROJECT.write_text(new_text, encoding="utf-8")


def update_changelog(new_version: str, dry: bool) -> None:
    if not CHANGELOG.exists():
        return
    content = CHANGELOG.read_text(encoding="utf-8")
    lines = content.splitlines()
    try:
        unreleased_idx = next(i for i, l in enumerate(lines) if l.strip().lower() == "## unreleased")
    except StopIteration:
        # Insert Unreleased if missing at top
        header_insert = ["## Unreleased", "- (no changes yet)", ""]
        lines = lines[:1] + [""] + header_insert + lines[1:]
        unreleased_idx = next(i for i, l in enumerate(lines) if l.strip().lower() == "## unreleased")

    # Collect entries until next '## ' or EOF
    collected: list[str] = []
    i = unreleased_idx + 1
    while i < len(lines) and not lines[i].startswith("## "):
        collected.append(lines[i])
        i += 1
    # Trim leading/trailing empties
    while collected and not collected[0].strip():
        collected.pop(0)
    while collected and not collected[-1].strip():
        collected.pop()

    today = dt.date.today().isoformat()
    new_section_header = f"## {new_version} - {today}"
    if not collected:
        collected = ["- (no notable changes)" ]

    insertion_block = [new_section_header] + collected + [""]

    # Replace old range with placeholder
    # Ensure Unreleased placeholder refreshed
    placeholder = ["## Unreleased", "- (no changes yet)", ""]
    new_lines = lines[:unreleased_idx] + placeholder + lines[i:]

    # Find where to insert (after Unreleased placeholder)
    insertion_point = new_lines.index(placeholder[-1]) + 1
    new_lines = new_lines[:insertion_point] + insertion_block + new_lines[insertion_point:]

    new_content = "\n".join(new_lines) + "\n"
    if dry:
        print("--- CHANGELOG.md (preview) ---")
        print(new_content)
    else:
        CHANGELOG.write_text(new_content, encoding="utf-8")


def build_dist(dry: bool) -> None:
    if dry:
        print("(dry-run) Skipping build")
        return
    try:
        run([sys.executable, "-m", "pip", "install", "--upgrade", "build", "twine"], check=True)
        run([sys.executable, "-m", "build"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: build failed: {e}", file=sys.stderr)
        sys.exit(1)


def git_commit_and_tag(new_version: str, do_tag: bool, dry: bool) -> None:
    if dry:
        print("(dry-run) Skipping git commit/tag")
        return
    run(["git", "add", "pyproject.toml", "CHANGELOG.md"], check=True)
    run(["git", "commit", "-m", f"release: v{new_version}"], check=True)
    if do_tag:
        run(["git", "tag", f"v{new_version}"], check=True)


def publish(new_version: str, dry: bool) -> None:
    if dry:
        print("(dry-run) Skipping publish")
        return
    try:
        run([sys.executable, "-m", "twine", "upload", "dist/*"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: publish failed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = parse_args()
    ensure_clean(args.allow_dirty)
    current = get_current_version()

    if args.set_version:
        new_version = args.set_version.strip()
    elif args.level:
        new_version = bump_version(current, args.level)
    else:
        print("Specify either --level or --set", file=sys.stderr)
        sys.exit(1)

    if not SEMVER_RE.match(new_version):
        print(f"ERROR: new version '{new_version}' is not semantic", file=sys.stderr)
        sys.exit(1)

    print(f"Current version: {current}\nNew version: {new_version}")

    update_pyproject(new_version, args.dry_run)
    update_changelog(new_version, args.dry_run)
    build_dist(args.dry_run)
    git_commit_and_tag(new_version, args.tag, args.dry_run)
    if args.publish:
        publish(new_version, args.dry_run)

    print("Release steps complete." + (" (dry run)" if args.dry_run else ""))
    if not args.publish:
        print("Next: git push && git push --tags (if tagged) then optionally run with --publish")

if __name__ == "__main__":  # pragma: no cover
    main()
