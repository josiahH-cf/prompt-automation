"""Espanso sync orchestrator: validate -> mirror -> install/update -> restart.

Designed to be cross-platform and callable from:
- CLI: `python -m prompt_automation.espanso_sync` or `prompt-automation --espanso-sync`
- Espanso colon command (via a shell var invoking the CLI)

Behavior is environment-agnostic and parameterized via CLI args or env vars:
- PROMPT_AUTOMATION_REPO: repo root (auto-detected if unset)
- PA_AUTO_BUMP: "off"|"patch" (default: off)
- PA_SKIP_INSTALL: "1" to skip espanso install/update (default: skip when not running under espanso)
- PA_DRY_RUN: "1" to run validation + mirror only

No secrets are logged; logs are concise JSON lines for each step.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def _j(status: str, step: str, **extra: object) -> None:
    msg = {"status": status, "step": step, **extra}
    print(json.dumps(msg, ensure_ascii=False))


def _run(cmd: list[str] | str, cwd: Path | None = None, check: bool = False) -> tuple[int, str, str]:
    if isinstance(cmd, str):
        shell = True
        args: list[str] | str = cmd
    else:
        shell = False
        args = cmd
    proc = subprocess.Popen(
        args, cwd=str(cwd) if cwd else None, shell=shell,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, args, out, err)
    return proc.returncode, out or "", err or ""


def _find_repo_root(explicit: Path | None) -> Path:
    if explicit and (explicit / "espanso-package" / "_manifest.yml").exists():
        return explicit
    # Check env var
    env = os.environ.get("PROMPT_AUTOMATION_REPO")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "espanso-package" / "_manifest.yml").exists():
            return p
    # Walk up from CWD
    cur = Path.cwd().resolve()
    for d in [cur] + list(cur.parents):
        if (d / "espanso-package" / "_manifest.yml").exists():
            return d
    # Walk up from this file
    here = Path(__file__).resolve()
    for d in [here.parent] + list(here.parents):
        if (d / "espanso-package" / "_manifest.yml").exists():
            return d
    raise SystemExit("Repo root not found. Set PROMPT_AUTOMATION_REPO or run from repo.")


def _read_manifest(repo: Path) -> tuple[str, str]:
    import yaml  # local import to avoid mandatory dependency in unrelated contexts
    mf = repo / "espanso-package" / "_manifest.yml"
    data = yaml.safe_load(mf.read_text()) or {}
    name = str(data.get("name") or "prompt-automation")
    version = str(data.get("version") or "0.1.0")
    return name, version


def _validate_yaml(repo: Path) -> None:
    import yaml
    pkg_dir = repo / "espanso-package"
    manifest = pkg_dir / "_manifest.yml"
    package_yml = pkg_dir / "package.yml"
    match_dir = pkg_dir / "match"
    problems: List[str] = []

    # Manifest required keys
    data = yaml.safe_load(manifest.read_text())
    for field in ("name", "title", "version", "description", "author"):
        if not (field in data and str(data[field]).strip()):
            problems.append(f"manifest_missing:{field}")

    # Package.yml present and basic structure
    pdata = yaml.safe_load(package_yml.read_text())
    if not isinstance(pdata, dict) or not pdata.get("name"):
        problems.append("package_yaml_invalid")

    if not match_dir.exists():
        problems.append("match_dir_missing")
    match_files = sorted(match_dir.glob("*.yml"))
    if not match_files:
        problems.append("no_match_files")

    triggers: Dict[str, List[str]] = {}
    style_violations: List[Tuple[str, str]] = []
    for f in match_files:
        content = yaml.safe_load(f.read_text())
        if not isinstance(content, dict):
            problems.append(f"file_not_mapping:{f.name}")
            continue
        if "matches" not in content or not isinstance(content["matches"], list):
            problems.append(f"matches_invalid:{f.name}")
            continue
        for i, entry in enumerate(content["matches"]):
            if not isinstance(entry, dict):
                problems.append(f"entry_not_mapping:{f.name}:{i}")
                continue
            t = entry.get("trigger")
            r = entry.get("regex")
            has_trigger = isinstance(t, str) and t.strip() != ""
            has_regex = isinstance(r, str) and r.strip() != ""
            if not (has_trigger or has_regex):
                problems.append(f"missing_trigger_or_regex:{f.name}:{i}")
            if has_trigger:
                has_replace = isinstance(entry.get("replace"), (str, dict)) and str(entry.get("replace")).strip() != ""
                has_form = isinstance(entry.get("form"), dict)
                has_vars = isinstance(entry.get("vars"), list)
                if not (has_replace or has_form or has_vars):
                    problems.append(f"trigger_missing_body:{f.name}:{i}")
                # style: start with ':' and no spaces
                if not t.startswith(":") or (" " in t):
                    style_violations.append((f.name, t))
                triggers.setdefault(t, []).append(f.name)

    dups = {t: files for t, files in triggers.items() if isinstance(t, str) and len(files) > 1}
    if dups:
        problems.append(f"duplicate_triggers:{dups}")
    if style_violations:
        problems.append(f"trigger_style:{style_violations}")

    if problems:
        _j("error", "validate", problems=problems)
        raise SystemExit("Validation failed: " + ",".join(problems))
    _j("ok", "validate", files=len(match_files))


def _maybe_bump_patch(repo: Path, enable: bool) -> str:
    if not enable:
        return _read_manifest(repo)[1]
    # very small YAML patcher to bump Z in X.Y.Z
    import re
    path = repo / "espanso-package" / "_manifest.yml"
    txt = path.read_text()
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", txt, flags=re.M)
    if not m:
        return _read_manifest(repo)[1]
    x, y, z = map(int, m.groups())
    new = f"version: {x}.{y}.{z+1}"
    txt = re.sub(r"^version:.*$", new, txt, count=1, flags=re.M)
    path.write_text(txt)
    _j("ok", "bump_version", version=f"{x}.{y}.{z+1}")
    return f"{x}.{y}.{z+1}"


def _mirror(repo: Path, pkg_name: str, version: str) -> Path:
    src = repo / "espanso-package"
    dst = repo / "packages" / pkg_name / version
    (dst / "match").mkdir(parents=True, exist_ok=True)
    # Mirror manifest 1:1
    shutil.copy2(src / "_manifest.yml", dst / "_manifest.yml")
    # Copy package.yml
    if (src / "package.yml").exists():
        shutil.copy2(src / "package.yml", dst / "package.yml")
    # Copy match files
    for p in (src / "match").glob("*.yml"):
        shutil.copy2(p, dst / "match" / p.name)
    # README lightweight
    readme = dst / "README.md"
    if not readme.exists():
        readme.write_text(f"# {pkg_name}\n\nMirrored from espanso-package/ for version {version}.\n", encoding="utf-8")
    _j("ok", "mirror", dest=str(dst))
    return dst


def _git_remote(repo: Path) -> str | None:
    code, out, _ = _run(["git", "-C", str(repo), "remote", "get-url", "origin"])
    url = out.strip()
    return url or None


def _current_branch(repo: Path) -> str | None:
    """Return the current git branch name, or None when detached/unknown."""
    code, out, _ = _run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"])
    if code == 0:
        br = out.strip()
        if br and br != "HEAD":
            return br
    return None


def _espanso_bin() -> list[str] | None:
    # return invocation for espanso appropriate per OS
    if shutil.which("espanso"):
        return ["espanso"]
    return None


def _install_or_update(pkg_name: str, repo_url: str | None, local_path: Path | None, git_branch: str | None) -> None:
    bin_ = _espanso_bin()
    if not bin_:
        _j("warn", "espanso_missing", note="espanso not on PATH; skipping install/update")
        return
    # Ensure service is up (best effort)
    _run(bin_ + ["service", "register"])  # type: ignore[operator]
    _run(bin_ + ["start"])  # type: ignore[operator]

    if repo_url:
        # Prefer git-based workflow
        cmd = bin_ + [
            "package", "install", pkg_name,
            "--git", repo_url,
            "--external",
            "--force",
        ]
        if git_branch:
            cmd += ["--git-branch", git_branch]
        code, _, _ = _run(cmd)  # type: ignore[operator]
        if code != 0:
            _run(bin_ + ["package", "update", pkg_name])  # type: ignore[operator]
    elif local_path:
        # Try local install; espanso may not support --path on all builds, try common flags, then fallback to copy
        code, _, err = _run(bin_ + ["package", "install", pkg_name, "--path", str(local_path)])  # type: ignore[operator]
        if code != 0:
            # try legacy flag name
            code2, _, _ = _run(bin_ + ["package", "install", pkg_name, "--external", str(local_path)])  # type: ignore[operator]
            if code2 != 0:
                _j("warn", "install_local_fallback", error=err.strip()[:200])
    # Restart and show status
    _run(bin_ + ["restart"])  # type: ignore[operator]
    _run(bin_ + ["package", "list"])  # type: ignore[operator]
    _j("ok", "install_update_done", mode="git" if repo_url else "local")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="espanso-sync", add_help=True)
    ap.add_argument("--repo", type=Path, default=None, help="Repository root containing espanso-package/")
    ap.add_argument("--auto-bump", choices=["off", "patch"], default=os.environ.get("PA_AUTO_BUMP", "off"))
    ap.add_argument("--skip-install", action="store_true", default=os.environ.get("PA_SKIP_INSTALL") == "1")
    ap.add_argument("--dry-run", action="store_true", default=os.environ.get("PA_DRY_RUN") == "1")
    ap.add_argument("--git-branch", default=os.environ.get("PA_GIT_BRANCH", ""), help="Branch to install from when using git source (defaults to current branch)")
    args = ap.parse_args(argv)

    _j("start", "sync", os=platform.system())

    repo = _find_repo_root(args.repo)
    _j("ok", "discover_repo", repo=str(repo))

    # Validate
    _validate_yaml(repo)

    # Optional bump
    version = _maybe_bump_patch(repo, args.auto_bump == "patch")
    pkg_name, _ = _read_manifest(repo)
    # Mirror
    local_pkg_dir = _mirror(repo, pkg_name, version)

    if args.dry_run:
        _j("ok", "dry_run", note="skipping install/update")
        return

    # Install/update
    if args.skip_install:
        _j("ok", "skip_install", reason="flag")
        return
    repo_url = _git_remote(repo)
    # Decide which git branch to use for installation
    git_branch = args.git_branch.strip() or _current_branch(repo) or None
    _install_or_update(pkg_name, repo_url, local_pkg_dir, git_branch)
    _j("done", "sync")


if __name__ == "__main__":  # pragma: no cover
    main()

