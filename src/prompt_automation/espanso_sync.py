"""Espanso sync orchestrator: generate -> validate -> mirror -> install/update -> restart.

Designed to be cross-platform and callable from:
- CLI: `python -m prompt_automation.espanso_sync` or `prompt-automation --espanso-sync`
- Espanso colon command (via a shell var invoking the CLI)

Behavior is environment-agnostic and parameterized via CLI args or env vars:
- PROMPT_AUTOMATION_REPO: repo root (auto-detected if unset)
- PA_AUTO_BUMP: "off"|"patch" (default: patch)
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
from typing import Dict, List, Tuple, Iterable


def _j(status: str, step: str, **extra: object) -> None:
    msg = {"status": status, "step": step, **extra}
    print(json.dumps(msg, ensure_ascii=False))


def _run(cmd: list[str] | str, cwd: Path | None = None, check: bool = False, timeout: float | None = None) -> tuple[int, str, str]:
    if isinstance(cmd, str):
        shell = True
        args: list[str] | str = cmd
    else:
        shell = False
        args = cmd
    try:
        # On Windows, avoid UNC working directories which cause "WinError 2" for PATH tools
        if cwd is None and platform.system() == "Windows":
            try:
                cur = os.getcwd()
                if cur.startswith("\\\\"):
                    user_home = os.environ.get("USERPROFILE") or str(Path.home())
                    cwd = Path(user_home)
            except Exception:
                pass
        proc = subprocess.Popen(
            args, cwd=str(cwd) if cwd else None, shell=shell,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Terminate the process tree and return a timeout code instead of raising
            try:
                proc.kill()
            except Exception:
                pass
            out, err = proc.communicate()
            return 124, out or "", f"timeout after {int(timeout or 0)}s"
    except FileNotFoundError as e:  # common on Windows when PATH differs for GUI apps
        return 127, "", str(e)
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
    # Check Settings/settings.json for an explicit repo root
    try:
        from .config import PROMPTS_DIR  # lightweight import
        settings_path = PROMPTS_DIR / "Settings" / "settings.json"
        if settings_path.exists():
            import json as _json
            payload = _json.loads(settings_path.read_text(encoding="utf-8"))
            repo_path = payload.get("espanso_repo_root") or payload.get("repo_root")
            if isinstance(repo_path, str) and repo_path.strip():
                rp = Path(repo_path).expanduser().resolve()
                if (rp / "espanso-package" / "_manifest.yml").exists():
                    return rp
    except Exception:
        # Non-fatal; continue discovery
        pass
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
    try:
        import yaml
    except ModuleNotFoundError as e:  # pragma: no cover - environment issue
        _j("error", "deps", missing="PyYAML", hint="Install via pipx inject prompt-automation pyyaml or pip install pyyaml")
        raise SystemExit("PyYAML is required: install with 'pipx inject prompt-automation pyyaml' or 'pip install pyyaml'") from e
    mf = repo / "espanso-package" / "_manifest.yml"
    data = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
    name = str(data.get("name") or "prompt-automation")
    version = str(data.get("version") or "0.1.0")
    return name, version


def _validate_yaml(repo: Path) -> None:
    try:
        import yaml
    except ModuleNotFoundError as e:  # pragma: no cover - environment issue
        _j("error", "deps", missing="PyYAML", hint="Install via pipx inject prompt-automation pyyaml or pip install pyyaml")
        raise SystemExit("PyYAML is required: install with 'pipx inject prompt-automation pyyaml' or 'pip install pyyaml'") from e
    pkg_dir = repo / "espanso-package"
    manifest = pkg_dir / "_manifest.yml"
    package_yml = pkg_dir / "package.yml"
    match_dir = pkg_dir / "match"
    problems: List[str] = []

    # Manifest required keys
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    for field in ("name", "title", "version", "description", "author"):
        if not (field in data and str(data[field]).strip()):
            problems.append(f"manifest_missing:{field}")

    # Package.yml present and basic structure
    pdata = yaml.safe_load(package_yml.read_text(encoding="utf-8"))
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
        content = yaml.safe_load(f.read_text(encoding="utf-8"))
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


def _yaml_dump_multiline(data: object) -> str:
    """Dump YAML ensuring multi-line strings use literal block scalars (|).

    We wrap multi-line strings in a dedicated subclass so the representer can
    reliably force style='|', avoiding PyYAML's folded output.
    """
    import yaml

    class LiteralString(str):
        pass

    class LiteralDumper(yaml.SafeDumper):
        pass

    def _represent_literal(dumper: yaml.SafeDumper, value: LiteralString):  # type: ignore[override]
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(value), style='|')

    LiteralDumper.add_representer(LiteralString, _represent_literal)

    def _wrap_multiline(obj: object) -> object:
        if isinstance(obj, str) and '\n' in obj:
            return LiteralString(obj)
        if isinstance(obj, list):
            return [ _wrap_multiline(x) for x in obj ]
        if isinstance(obj, dict):
            return { k: _wrap_multiline(v) for k, v in obj.items() }
        return obj

    wrapped = _wrap_multiline(data)
    return yaml.dump(wrapped, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True)


def _discover_templates(repo: Path) -> List[Path]:
    pkg = repo / "espanso-package"
    tdir = pkg / "templates"
    paths: List[Path] = []
    if tdir.exists():
        paths.extend(sorted(tdir.glob("*.yml")))
    # Also treat match/*.yml.example as templates
    paths.extend(sorted((pkg / "match").glob("*.yml.example")))
    return paths


def _render_templates(repo: Path, templates: Iterable[Path]) -> int:
    """Render templates into match/*.yml. Deduplicate triggers across generated content.

    Returns number of files written/updated.
    """
    try:
        import yaml
    except ModuleNotFoundError as e:  # pragma: no cover - environment issue
        _j("error", "deps", missing="PyYAML", hint="Install via pipx inject prompt-automation pyyaml or pip install pyyaml")
        raise SystemExit("PyYAML is required: install with 'pipx inject prompt-automation pyyaml' or 'pip install pyyaml'") from e

    pkg = repo / "espanso-package"
    match_dir = pkg / "match"
    written = 0
    seen_triggers: set[str] = set()
    for tpl in templates:
        if tpl.parent.name == "templates":
            target = match_dir / tpl.name
        else:
            # *.yml.example in match -> write *.yml next to it
            name = tpl.name[:-len(".example")] if tpl.name.endswith(".example") else tpl.name
            target = tpl.parent / name

        try:
            doc = yaml.safe_load(tpl.read_text(encoding="utf-8")) or {}
        except Exception as e:
            _j("error", "generate", template=str(tpl), error=str(e)[:200])
            raise SystemExit(f"Template parse failed: {tpl}")

        matches = list((doc or {}).get("matches", []) or [])
        if not isinstance(matches, list):
            matches = []

        # filter duplicates across generated set
        filtered: List[dict] = []
        for entry in matches:
            if not isinstance(entry, dict):
                continue
            t = entry.get("trigger")
            if isinstance(t, str) and t in seen_triggers:
                continue
            if isinstance(t, str):
                seen_triggers.add(t)
            filtered.append(entry)

        payload = {"matches": filtered}
        target.write_text(_yaml_dump_multiline(payload), encoding="utf-8")
        written += 1
    return written


def _generate_from_templates(repo: Path) -> None:
    tpls = _discover_templates(repo)
    if not tpls:
        _j("skip", "generate", reason="no_templates")
        return
    n = _render_templates(repo, tpls)
    _j("ok", "generate", files=n)


def _maybe_bump_patch(repo: Path, enable: bool) -> str:
    if not enable:
        return _read_manifest(repo)[1]
    # very small YAML patcher to bump Z in X.Y.Z
    import re
    path = repo / "espanso-package" / "_manifest.yml"
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", txt, flags=re.M)
    if not m:
        return _read_manifest(repo)[1]
    x, y, z = map(int, m.groups())
    new = f"version: {x}.{y}.{z+1}"
    txt = re.sub(r"^version:.*$", new, txt, count=1, flags=re.M)
    path.write_text(txt, encoding="utf-8")
    _j("ok", "bump_version", version=f"{x}.{y}.{z+1}")
    return f"{x}.{y}.{z+1}"


def _mirror(repo: Path, pkg_name: str, version: str) -> Path:
    """Mirror espanso-package into packages/<pkg>/<version> with pruning.

    Policy: keep only two folders under packages/<pkg_name>:
    - The current version directory (just mirrored)
    - A single backup directory "_backup/" containing the previous version snapshot
    Any other historical version directories are deleted to avoid growth.
    """
    import re

    src = repo / "espanso-package"
    base = repo / "packages" / pkg_name
    dst = base / version

    # Ensure destination exists and mirror files
    (dst / "match").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "_manifest.yml", dst / "_manifest.yml")
    if (src / "package.yml").exists():
        shutil.copy2(src / "package.yml", dst / "package.yml")
    for p in sorted((src / "match").glob("*.yml")):
        shutil.copy2(p, dst / "match" / p.name)
    readme = dst / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {pkg_name}\n\nMirrored from espanso-package/ for version {version}.\n",
            encoding="utf-8",
        )
    _j("ok", "mirror", dest=str(dst))

    # Collect existing version directories (semver-like names)
    def _is_ver_dir(d: Path) -> bool:
        return d.is_dir() and re.match(r"^\d+\.\d+\.\d+$", d.name) is not None

    try:
        existing = [d for d in base.iterdir() if _is_ver_dir(d) and d.name != version]
    except FileNotFoundError:
        existing = []

    # Identify the most recent previous version by semantic version sort
    def _semver_key(v: str) -> tuple[int, int, int]:
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v)
        if not m:
            return (0, 0, 0)
        return tuple(map(int, m.groups()))  # type: ignore[return-value]

    prev_dir: Path | None = None
    if existing:
        prev_dir = sorted(existing, key=lambda p: _semver_key(p.name))[-1]

    # Prepare a single backup directory containing the previous version snapshot
    backup_root = base / "_backup"
    try:
        if backup_root.exists():
            shutil.rmtree(backup_root, ignore_errors=True)
        backup_root.mkdir(parents=True, exist_ok=True)
        if prev_dir is not None and prev_dir.exists():
            shutil.copytree(prev_dir, backup_root / prev_dir.name)
            _j("ok", "mirror_backup", previous=str(prev_dir), backup=str(backup_root / prev_dir.name))
    except Exception as e:
        _j("warn", "mirror_backup_failed", error=str(e)[:200])

    # Prune all historical version dirs except the current one
    removed: list[str] = []
    for d in existing:
        try:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d.name)
        except Exception:
            pass
    if removed:
        _j("ok", "mirror_prune", removed=removed)

    return dst


def _prune_local_defaults() -> None:
    """Remove all local match YAMLs so only the package rules apply.

    Deletes every ``*.yml``/``*.yaml`` file under:
    - Linux/macOS: ``~/.config/espanso/match/``
    - Windows: ``%APPDATA%/espanso/match/``
    Safe and idempotent; logs removed paths.
    """
    removed: List[str] = []
    errors: List[str] = []
    created: List[str] = []
    # Try discovering config via espanso path for precise targeting
    cfg_paths: List[Path] = []
    try:
        bin_ = _espanso_bin()
        code_p, out_p, err_p = (1, "", "")
        if bin_:
            code_p, out_p, err_p = _run(bin_ + ["path"], timeout=6)
        if (not bin_) or (code_p != 0 or not out_p):
            if platform.system() == "Windows" and shutil.which("powershell.exe"):
                code_p, out_p, err_p = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "espanso path"], timeout=10)
        if code_p == 0 and out_p:
            # Look for a line containing a path to config (case-insensitive search for 'config')
            for ln in out_p.splitlines():
                if "config" in ln.lower():
                    # extract last path-like token
                    try:
                        import re as _re
                        m = _re.search(r"([A-Za-z]:\\[^\r\n]+|/[^\r\n]+)$", ln.strip())
                        if m:
                            p = Path(m.group(1).strip())
                            if p.exists():
                                cfg_paths.append(p)
                    except Exception:
                        pass
    except Exception:
        pass

    # Linux/macOS style
    try:
        match_dir = Path.home() / ".config" / "espanso" / "match"
        if match_dir.exists():
            for p in list(match_dir.glob("*.yml")) + list(match_dir.glob("*.yaml")):
                try:
                    p.unlink()
                    removed.append(str(p))
                except Exception as e:  # pragma: no cover - best effort
                    errors.append(f"{p}: {str(e)[:120]}")
            # Write disabled sentinel to avoid default regeneration in some builds
            try:
                sentinel = match_dir / "disabled.yml"
                if not sentinel.exists():
                    sentinel.write_text("matches: []\n", encoding="utf-8")
                    created.append(str(sentinel))
            except Exception as e:  # pragma: no cover - best effort
                errors.append(f"sentinel:{match_dir}: {str(e)[:120]}")
    except Exception as e:  # pragma: no cover - best effort
        errors.append(f"home_lookup: {str(e)[:120]}")
    # Windows style (try Python path removal and PowerShell removal for robustness from WSL)
    try:
        appdata = os.environ.get("APPDATA")
        if appdata:
            match_dir = Path(appdata) / "espanso" / "match"
            if match_dir.exists():
                for p in list(match_dir.glob("*.yml")) + list(match_dir.glob("*.yaml")):
                    try:
                        p.unlink()
                        removed.append(str(p))
                    except Exception as e:  # pragma: no cover - best effort
                        errors.append(f"{p}: {str(e)[:120]}")
                # Disabled sentinel
                try:
                    sentinel = match_dir / "disabled.yml"
                    if not sentinel.exists():
                        sentinel.write_text("matches: []\n", encoding="utf-8")
                        created.append(str(sentinel))
                except Exception as e:  # pragma: no cover - best effort
                    errors.append(f"sentinel:{match_dir}: {str(e)[:120]}")
        # Also attempt deletion via PowerShell so WSL can remove Windows-host files
        if shutil.which("powershell.exe"):
            ps = (
                "$ErrorActionPreference='SilentlyContinue'; "
                "if (Test-Path $env:APPDATA/espanso/match) { Remove-Item -Force -Recurse $env:APPDATA/espanso/match/*.yml, $env:APPDATA/espanso/match/*.yaml } "
                "if (Test-Path $env:LOCALAPPDATA/espanso/match) { Remove-Item -Force -Recurse $env:LOCALAPPDATA/espanso/match/*.yml, $env:LOCALAPPDATA/espanso/match/*.yaml }"
            )
            code_ps, out_ps, err_ps = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout=20)
            if code_ps != 0 and (err_ps or out_ps):
                errors.append(f"powershell: {(err_ps or out_ps).strip()[:180]}")
    except Exception as e:  # pragma: no cover - best effort
        errors.append(f"appdata_lookup: {str(e)[:120]}")
    # Also handle paths discovered from 'espanso path'
    for cfg in cfg_paths:
        try:
            md = cfg / "match"
            if md.exists():
                for p in list(md.glob("*.yml")) + list(md.glob("*.yaml")):
                    try:
                        p.unlink()
                        removed.append(str(p))
                    except Exception as e:
                        errors.append(f"{p}: {str(e)[:120]}")
                try:
                    sentinel = md / "disabled.yml"
                    if not sentinel.exists():
                        sentinel.write_text("matches: []\n", encoding="utf-8")
                        created.append(str(sentinel))
                except Exception as e:
                    errors.append(f"sentinel:{md}: {str(e)[:120]}")
        except Exception as e:
            errors.append(f"cfg_scan:{cfg}: {str(e)[:120]}")
    if removed:
        _j("ok", "prune_defaults", removed=removed)
    if created:
        _j("ok", "prune_defaults", created=created)
    if errors:
        _j("warn", "prune_defaults", errors=errors)


def _ensure_undo_backspace_disabled() -> None:
    """Ensure Espanso's backspace-undo is disabled by setting undo_backspace: false.

    Targets config/default.yml under discovered Espanso config directories:
    - Linux/macOS: ~/.config/espanso/config/
    - Windows: %APPDATA%/espanso/config/
    - Any path discovered from `espanso path` that includes a config directory.

    Best-effort and idempotent. Preserves other keys when PyYAML is available;
    otherwise performs a minimal line-level update/append.
    """
    cfg_dirs: List[Path] = []
    # Discover via `espanso path` first (most accurate)
    try:
        bin_ = _espanso_bin()
        code_p, out_p, err_p = (1, "", "")
        if bin_:
            code_p, out_p, err_p = _run(bin_ + ["path"], timeout=6)
        if (not bin_) or (code_p != 0 or not out_p):
            if platform.system() == "Windows" and shutil.which("powershell.exe"):
                code_p, out_p, err_p = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "espanso path"], timeout=10)
        if code_p == 0 and out_p:
            for ln in out_p.splitlines():
                if "config" in ln.lower():
                    try:
                        import re as _re
                        m = _re.search(r"([A-Za-z]:\\[^\r\n]+|/[^\r\n]+)$", ln.strip())
                        if m:
                            p = Path(m.group(1).strip())
                            if p.exists():
                                cfg_dirs.append(p)
                    except Exception:
                        pass
    except Exception:
        pass

    # Add conventional locations
    try:
        cfg_dirs.append(Path.home() / ".config" / "espanso" / "config")
    except Exception:
        pass
    appdata = os.environ.get("APPDATA")
    if appdata:
        cfg_dirs.append(Path(appdata) / "espanso" / "config")

    # Deduplicate while preserving order
    seen: set[str] = set()
    uniq_dirs: List[Path] = []
    for d in cfg_dirs:
        key = str(d.resolve()) if d else ""
        if key and key not in seen:
            seen.add(key)
            uniq_dirs.append(d)

    updated: List[str] = []
    created: List[str] = []
    errors: List[str] = []

    def _write_yaml_setting(path: Path) -> bool:
        try:
            import yaml  # type: ignore
            data: dict = {}
            if path.exists():
                try:
                    data_l = yaml.safe_load(path.read_text(encoding="utf-8"))
                    if isinstance(data_l, dict):
                        data = data_l
                except Exception:
                    # Fall through to overwrite minimally
                    data = {}
            # Set and write
            if data.get("undo_backspace") is False and path.exists():
                return False  # already correct
            data["undo_backspace"] = False
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            return True
        except ModuleNotFoundError:
            # Minimal text update without PyYAML
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    txt = path.read_text(encoding="utf-8")
                    import re as _re
                    if _re.search(r"^\s*undo_backspace\s*:\s*false\s*$", txt, flags=_re.M):
                        return False
                    if _re.search(r"^\s*undo_backspace\s*:\s*true\s*$", txt, flags=_re.M):
                        txt = _re.sub(r"^\s*undo_backspace\s*:\s*true\s*$", "undo_backspace: false", txt, count=1, flags=_re.M)
                        path.write_text(txt, encoding="utf-8")
                        return True
                    # Append setting
                    if not txt.endswith("\n"):
                        txt += "\n"
                    txt += "undo_backspace: false\n"
                    path.write_text(txt, encoding="utf-8")
                    return True
                else:
                    path.write_text("undo_backspace: false\n", encoding="utf-8")
                    return True
            except Exception:
                return False
        except Exception:
            return False

    for cfg in uniq_dirs:
        try:
            dfl = cfg / "default.yml"
            changed = _write_yaml_setting(dfl)
            if changed:
                (updated if dfl.exists() else created).append(str(dfl))
            # Also handle alternative extension if present
            dfl_yaml = cfg / "default.yaml"
            if dfl_yaml.exists():
                changed2 = _write_yaml_setting(dfl_yaml)
                if changed2:
                    updated.append(str(dfl_yaml))
        except Exception as e:  # pragma: no cover - best effort
            errors.append(f"{cfg}: {str(e)[:160]}")

    if updated:
        _j("ok", "undo_backspace", updated=updated)
    if created:
        _j("ok", "undo_backspace", created=created)
    if errors:
        _j("warn", "undo_backspace", errors=errors)

    # Best-effort restart so the setting takes effect immediately
    try:
        bin_ = _espanso_bin()
        if platform.system() == "Windows" and shutil.which("powershell.exe"):
            _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "espanso restart"], timeout=8)
        elif bin_:
            _run(bin_ + ["restart"], timeout=6)
    except Exception:
        pass


def _manifest_homepage(repo: Path) -> str | None:
    try:
        import yaml
        mf = repo / "espanso-package" / "_manifest.yml"
        if mf.exists():
            data = yaml.safe_load(mf.read_text(encoding="utf-8")) or {}
            url = data.get("homepage")
            if isinstance(url, str) and url.strip():
                return url.strip()
    except Exception:
        pass
    return None


def _normalize_git_url(url: str | None) -> str:
    """Normalize a git URL for comparison.

    - lower-case
    - strip trailing "/" and optional ".git"
    - return empty string for None/empty
    """
    if not url:
        return ""
    u = url.strip().lower().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u


def _git_remote(repo: Path) -> str | None:
    # Try git directly
    try:
        code, out, err = _run(["git", "-C", str(repo), "remote", "get-url", "origin"])
        if code == 0 and out.strip():
            return out.strip()
    except Exception:
        pass
    # Try PowerShell git on Windows
    if platform.system() == "Windows" and shutil.which("powershell.exe"):
        try:
            scmd = f"git -C \"{str(repo)}\" remote get-url origin"
            code, out, err = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", scmd])
            if code == 0 and out.strip():
                return out.strip()
        except Exception:
            pass
    # Try parsing .git/config
    try:
        cfg = repo / ".git" / "config"
        if cfg.exists():
            import configparser
            p = configparser.ConfigParser()
            p.read(cfg)
            if p.has_section("remote \"origin\"") and p.has_option("remote \"origin\"", "url"):
                return p.get("remote \"origin\"", "url")
    except Exception:
        pass
    # Fallback to manifest homepage
    hp = _manifest_homepage(repo)
    if hp and hp.startswith("http"):
        # Best-effort: append .git when missing for GitHub URLs
        if hp.endswith(".git"):
            return hp
        if "github.com" in hp:
            return hp + ".git"
        return hp
    return None


def _current_branch(repo: Path) -> str | None:
    """Return the current git branch name, or None when detached/unknown/missing git."""
    try:
        code, out, _ = _run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"])
    except Exception:
        return None
    if code == 0:
        br = (out or "").strip()
        if br and br != "HEAD":
            return br
    return None


def _git_prepare_branch(repo: Path, preferred: str | None) -> str | None:
    """Ensure we are on a usable branch, fetch, and pull --rebase safely.

    - Creates a new branch when detached or preferred missing.
    - Commits a pre-sync snapshot if the working tree is dirty.
    - Pulls with rebase; on failure, tries auto-stash and retries once.
    Returns the active branch or None when not a git repo.
    """
    if not (repo / ".git").exists():
        _j("skip", "git_prepare", reason="not_a_git_repo")
        return None
    def _status_dirty() -> bool:
        code, out, err = _run(["git", "-C", str(repo), "status", "--porcelain"])
        return code == 0 and bool((out or "").strip())
    # Determine branch and switch/create if needed
    current = _current_branch(repo)
    active = current
    if preferred:
        if current != preferred:
            # try checkout preferred; create if missing
            code, _, _ = _run(["git", "-C", str(repo), "rev-parse", "--verify", preferred])
            if code == 0:
                _run(["git", "-C", str(repo), "checkout", preferred])
            else:
                _run(["git", "-C", str(repo), "checkout", "-b", preferred])
            active = preferred
    if active is None:
        import datetime as _dt
        newb = f"espanso-sync-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        _run(["git", "-C", str(repo), "checkout", "-b", newb])
        active = newb
        _j("ok", "git_branch_created", name=newb)
    # Pre-sync snapshot commit if dirty
    if _status_dirty():
        _run(["git", "-C", str(repo), "add", "-A"])  # stage all
        code_c, out_c, err_c = _run(["git", "-C", str(repo), "commit", "-m", "chore(sync): pre-espanso sync snapshot"]) 
        _j("ok" if code_c == 0 else "warn", "git_pre_snapshot_commit", note=(err_c or out_c).strip()[:200])
    # Fetch and rebase/pull
    remote = _git_remote(repo)
    if remote:
        _run(["git", "-C", str(repo), "fetch", "--prune", "origin"], timeout=20)
        code_p, out_p, err_p = _run(["git", "-C", str(repo), "pull", "--rebase", "origin", active], timeout=30)
        if code_p != 0:
            # try auto-stash then retry once
            _j("warn", "git_pull_rebase_failed", error=(err_p or out_p).strip()[:200])
            _run(["git", "-C", str(repo), "stash", "push", "-u", "-m", "espanso-sync-autostash"], timeout=20)
            code_p2, out_p2, err_p2 = _run(["git", "-C", str(repo), "pull", "--rebase", "origin", active], timeout=30)
            if code_p2 == 0:
                _run(["git", "-C", str(repo), "stash", "pop"], timeout=20)
            else:
                _j("warn", "git_pull_stash_failed", error=(err_p2 or out_p2).strip()[:200], hint="There are merges that still need committed; please resolve and re-run sync.")
    return active


def _git_tag_and_push(repo: Path, version: str) -> None:
    """Create and push a tag `espanso-v<version>` if missing."""
    if not (repo / ".git").exists():
        return
    tag = f"espanso-v{version}"
    code_l, out_l, _ = _run(["git", "-C", str(repo), "tag", "-l", tag])
    if code_l == 0 and tag in (out_l or ""):
        _j("skip", "git_tag", reason="exists", tag=tag)
    else:
        code_t, out_t, err_t = _run(["git", "-C", str(repo), "tag", "-a", tag, "-m", f"espanso {version}"])
        _j("ok" if code_t == 0 else "warn", "git_tag", tag=tag, note=(err_t or out_t).strip()[:200])
    # Push tag best-effort
    # Push tag; auto-fix 'dubious ownership' by adding safe.directory and retrying once
    def _do_push_tag() -> tuple[int, str, str]:
        return _run(["git", "-C", str(repo), "push", "origin", tag], timeout=20)

    code_p, out_p, err_p = _do_push_tag()
    if code_p != 0 and ("dubious ownership" in (err_p or "").lower() or "dubious ownership" in (out_p or "").lower()):
        _run(["git", "config", "--global", "--add", "safe.directory", str(repo)])
        _j("warn", "git_tag_push_dubious", action="add_safe_directory", repo=str(repo), tag=tag)
        code_p, out_p, err_p = _do_push_tag()
    _j("ok" if code_p == 0 else "warn", "git_tag_push", tag=tag, note=(err_p or out_p).strip()[:200])


def _git_commit_and_push(repo: Path, branch: str | None, version: str) -> None:
    """Stage, commit, and push espanso changes to origin.

    No-op if not a git repo. Commit may be skipped when tree is clean.
    """
    try:
        if not (repo / ".git").exists():
            _j("skip", "git_commit", reason="not_a_git_repo")
            return
        # Stage all relevant changes
        _run(["git", "-C", str(repo), "add", "-A"], timeout=10)
        # Commit; allow failure if nothing to commit
        code_c, out_c, err_c = _run(
            ["git", "-C", str(repo), "commit", "-m", f"chore(espanso): sync v{version}"], timeout=10
        )
        if code_c == 0:
            _j("ok", "git_commit", version=version)
        else:
            _j("skip", "git_commit", reason=(err_c or out_c).strip()[:200] or "no_changes")
        # Push
        # Attempt push; on 'dubious ownership' add safe.directory and retry once
        def _do_push() -> tuple[int, str, str]:
            if branch:
                return _run(["git", "-C", str(repo), "push", "origin", branch], timeout=20)
            return _run(["git", "-C", str(repo), "push"], timeout=20)

        code_p, out_p, err_p = _do_push()
        if code_p != 0 and ("dubious ownership" in (err_p or "").lower() or "dubious ownership" in (out_p or "").lower()):
            # Configure safe.directory for this repo and retry once
            _run(["git", "config", "--global", "--add", "safe.directory", str(repo)])
            _j("warn", "git_push_dubious", action="add_safe_directory", repo=str(repo))
            code_p, out_p, err_p = _do_push()
        if code_p == 0:
            _j("ok", "git_push", branch=branch or "current")
        else:
            _j("warn", "git_push_failed", branch=branch or "current", error=(err_p or out_p).strip()[:200])
    except Exception as e:  # pragma: no cover - best effort
        _j("warn", "git_push_exception", error=str(e)[:200])


def _espanso_bin() -> list[str] | None:
    # return invocation for espanso appropriate per OS
    if shutil.which("espanso"):
        return ["espanso"]
    return None


def _active_branch(repo: Path, override: str | None) -> str | None:
    if override:
        return override.strip() or None
    env = os.environ.get("PA_GIT_BRANCH")
    if env:
        return env.strip() or None
    return _current_branch(repo)


def _build_git_install_cmds(pkg_name: str, repo_url: str, branch: str | None) -> List[List[str]]:
    """Return a sequence of argument lists to try for git install.

    Includes --external to allow non‑verified repositories (GitHub).
    Uses --git-branch for version selection when provided.
    Tries multiple orderings to satisfy Windows clap parsing.
    """
    base = ["package", "install", pkg_name, "--git", repo_url, "--external"]
    cmds: List[List[str]] = []
    if branch:
        cmds.append([*base, "--git-branch", branch])
    cmds.append(base)
    # Alternative ordering for some Windows builds (options-before-positional)
    alt_base = ["package", "install", "--git", repo_url, "--external", pkg_name]
    if branch:
        cmds.append(["package", "install", "--git", repo_url, "--git-branch", branch, "--external", pkg_name])
    cmds.append(alt_base)
    return cmds


def _list_installed_packages() -> List[Dict[str, str]]:
    """Return installed packages as a list of {name, version, source}.

    Source is a free-form string from espanso (e.g., "git: <url>" or "path: <dir>").
    """
    bin_ = _espanso_bin()
    out = ""
    code = 1
    err = ""
    if bin_:
        code, out, err = _run(bin_ + ["package", "list"], timeout=6)
    # Fall back to PowerShell even when espanso isn't directly invokable
    if (not bin_) or (code != 0 or not out):
        if platform.system() == "Windows" and shutil.which("powershell.exe"):
            ps_cmd = "Set-Location $env:USERPROFILE; espanso package list"
            code, out, err = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], timeout=12)
    if code != 0 or not out:
        return []
    lines = [l.strip() for l in out.splitlines()]
    pkgs: List[Dict[str, str]] = []
    for l in lines:
        # Expected: "- name - version: X (git: URL)" or "- name - version: X (path: DIR)"
        if l.startswith("- ") and " - version:" in l:
            try:
                # naive parse
                head, *tail = l[2:].split(" - version:")
                name = head.strip()
                rest = ":".join(tail).strip()
                version = rest.split()[0]
                src = l[l.find("(") + 1 : l.rfind(")")] if "(" in l and ")" in l else ""
                pkgs.append({"name": name, "version": version, "source": src})
            except Exception:
                continue
    return pkgs


def _uninstall_package(name: str) -> None:
    # Prefer PowerShell on Windows to avoid PATH/CWD edge cases, then fall back to CLI
    if platform.system() == "Windows" and shutil.which("powershell.exe"):
        ps_cmd = f"Set-Location $env:USERPROFILE; espanso package uninstall {name}"
        code_ps, out_ps, err_ps = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], timeout=12)
        _j("ok" if code_ps == 0 else "warn", "uninstall", name=name, via="powershell", code=code_ps, err=(err_ps or out_ps).strip()[:200])
        if code_ps == 0:
            return
    bin_ = _espanso_bin()
    if not bin_:
        return
    code, out, err = _run(bin_ + ["package", "uninstall", name], timeout=10)
    _j("ok" if code == 0 else "warn", "uninstall_cli", name=name, via="cli", code=code, err=(err or out).strip()[:200])


def _resolve_conflicts(pkg_name: str, repo_url: str | None, local_path: Path | None) -> None:
    """Remove conflicting packages installed from the same repo under a different name.

    This helps avoid duplicate triggers when older package names (e.g., 'your-pa')
    were used historically. Best-effort and safe: only removes packages when we
    detect an exact repo URL match, or a known legacy name pointing at this repo.
    """
    pkgs = _list_installed_packages()
    if not pkgs:
        return
    to_uninstall: List[str] = []
    legacy_names = {"your-pa"}
    repo_norm = _normalize_git_url(repo_url)
    for p in pkgs:
        name = p.get("name", "")
        src = p.get("source", "")
        if not name:
            continue
        # If the same-named package is installed from a local path, mark for uninstall
        try:
            src_l = (src or "").lower()
            if name == pkg_name and ("path:" in src_l or (local_path and str(local_path) in src)):
                to_uninstall.append(name)
                continue
        except Exception:
            pass
        # If the same-named package is installed from a different git repo, prefer our remote
        try:
            if name == pkg_name and "git:" in (src or "").lower() and repo_norm:
                src_url = (src_l.split("git:", 1)[1].strip() if 'src_l' in locals() else (src or '').split(':',1)[-1].strip())
                src_norm = _normalize_git_url(src_url)
                if src_norm and repo_norm and not (src_norm == repo_norm or repo_norm in src_norm or src_norm in repo_norm):
                    to_uninstall.append(name)
                    continue
        except Exception:
            pass
        # Same repository under a different package name (normalize URL to compare).
        # Do not target the canonical package name in this alias logic.
        if name == pkg_name:
            # Skip alias checks for canonical name
            pass
        else:
            try:
                src_l = (src or "").lower()
                if "git:" in src_l and repo_norm:
                    src_url = src_l.split("git:", 1)[1].strip()
                    src_norm = _normalize_git_url(src_url)
                    # treat equality or containment as a match to be resilient to protocol diffs
                    if src_norm and (src_norm == repo_norm or repo_norm in src_norm or src_norm in repo_norm):
                        to_uninstall.append(name)
            except Exception:
                pass
        # Known legacy names
        if name in legacy_names:
            to_uninstall.append(name)
        # Path-based installs pointing at our mirrored local path under a different name
        try:
            if local_path and ("path:" in src) and str(local_path) in src and name != pkg_name:
                to_uninstall.append(name)
        except Exception:
            pass
    # Deduplicate and uninstall
    unique = sorted(set(to_uninstall))
    if unique:
        _j("ok", "conflicts", action="uninstall", names=unique)
    for nm in unique:
        _uninstall_package(nm)


def _install_or_update(pkg_name: str, repo_url: str | None, local_path: Path | None, git_branch: str | None) -> None:
    system = platform.system()

    def _direct(cmd: List[str]) -> tuple[int, str, str]:
        bin_ = _espanso_bin()
        if not bin_:
            return (127, "", "espanso not found")
        return _run(bin_ + cmd, timeout=12)

    def _ps(cmd: str) -> tuple[int, str, str]:
        if shutil.which("powershell.exe"):
            return _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], timeout=12)
        return (127, "", "powershell.exe missing")

    # Ensure service is up (best effort in current environment)
    _direct(["service", "register"])  # ignore result
    _direct(["start"])  # ignore result

    # On Windows, enforce Git-only installs; skip local --path due to espanso v2 CLI.
    if system == "Windows" and not repo_url:
        _j("warn", "install_update", reason="windows_git_only_no_repo_url_skip")
        # Best-effort: refresh service/list to surface current state
        if shutil.which("powershell.exe"):
            _ps("espanso restart")
            _ps("espanso package list")
        else:
            _direct(["restart"])
            _direct(["package", "list"])
        _j("ok", "install_update_done", mode="git")
        return

    # Remote-first when a repo URL is available; otherwise allow local path on non-Windows.
    prefer_local = (system != "Windows") and (local_path is not None) and not bool(repo_url)
    mode = "local" if prefer_local else ("git" if repo_url else "local")
    local_ok = False
    # Pre-install pruning of default base files to avoid duplicates
    try:
        _prune_local_defaults()
    except Exception:
        pass
    if prefer_local:
        used_path = local_path
        if platform.system() == "Windows":
            path_str = str(local_path)
            if path_str.startswith("\\\\"):
                base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
                mirror_dir = base / "prompt-automation" / "espanso-mirror" / pkg_name / (local_path.name)
                try:
                    if mirror_dir.exists():
                        shutil.rmtree(mirror_dir, ignore_errors=True)
                    shutil.copytree(local_path, mirror_dir)
                    used_path = mirror_dir
                    _j("ok", "mirror_windows_local", dest=str(mirror_dir))
                except Exception as e:
                    _j("warn", "mirror_windows_local_failed", error=str(e)[:200])

        if platform.system() == "Windows" and shutil.which("powershell.exe"):
            cmds = [
                f"espanso package install --path \"{used_path}\" {pkg_name}",
                f"espanso package install {pkg_name} --path \"{used_path}\"",
            ]
            for scmd in cmds:
                code_try, _, _ = _ps(scmd)
                if code_try == 0:
                    local_ok = True
                    break
            if not local_ok:
                _j("warn", "install_local_fallback", error="powershell install failed for --path in both orderings")
        else:
            attempts = [
                ["package", "install", "--path", str(used_path), pkg_name],
                ["package", "install", pkg_name, "--path", str(used_path)],
            ]
            for a in attempts:
                code_try, _, err_try = _direct(a)
                if code_try == 0:
                    local_ok = True
                    break
            if not local_ok:
                _j("warn", "install_local_fallback", error=(err_try or "install --path failed").strip()[:200])

    if (not local_ok) and prefer_local:
        _direct(["package", "uninstall", pkg_name])
        used_path2 = local_path
        if platform.system() == "Windows" and shutil.which("powershell.exe") and local_path is not None:
            scmds = [
                f"espanso package install --path \"{used_path2}\" {pkg_name}",
                f"espanso package install {pkg_name} --path \"{used_path2}\"",
            ]
            ok = False
            last_err = ""
            for scmd in scmds:
                code_t, _, err_t = _ps(scmd)
                if code_t == 0:
                    ok = True
                    break
                last_err = err_t
            if ok:
                local_ok = True
            else:
                _j("warn", "reinstall_after_uninstall_failed", error=(last_err or "powershell reinstall failed").strip()[:200])
        else:
            code_ext2, _, err_ext2 = _direct(["package", "install", "--path", str(local_path), pkg_name]) if local_path else (1, "", "no local_path")
            if code_ext2 == 0:
                local_ok = True
            else:
                code_path2, _, err_path2 = _direct(["package", "install", pkg_name, "--path", str(local_path)])
                if code_path2 == 0:
                    local_ok = True
                else:
                    _j("warn", "reinstall_after_uninstall_failed", error=(err_ext2 or err_path2).strip()[:200])

    if repo_url and not local_ok:
        mode = "git"
        # Prefer HTTPS over SSH on Windows to avoid interactive auth / timeouts
        repo_for_install = repo_url
        if system == "Windows":
            try:
                ru = (repo_url or "").strip()
                if ru.startswith("git@github.com:"):
                    owner_repo = ru.split(":", 1)[1]
                    if owner_repo.endswith(".git"):
                        owner_repo = owner_repo[:-4]
                    repo_for_install = f"https://github.com/{owner_repo}.git"
                elif ru.startswith("ssh://") and "github.com" in ru:
                    tail = ru.split("github.com", 1)[1].lstrip(":/")
                    if tail.endswith(".git"):
                        tail = tail[:-4]
                    repo_for_install = f"https://github.com/{tail}.git"
            except Exception:
                pass
        cmds = _build_git_install_cmds(pkg_name, repo_for_install, git_branch)
        # If already installed from the same repo, prefer update over reinstall (Windows)
        try:
            if platform.system() == "Windows":
                pkgs = _list_installed_packages()
                repo_norm = (repo_url or "").lower().rstrip("/")
                if repo_norm.endswith(".git"):
                    repo_norm = repo_norm[:-4]
                already = False
                for p in pkgs:
                    if p.get("name") == pkg_name:
                        src = (p.get("source", "") or "").lower()
                        if "git:" in src:
                            src_url = src.split("git:", 1)[1].strip()
                            src_norm = src_url.rstrip("/")
                            if src_norm.endswith(".git"):
                                src_norm = src_norm[:-4]
                            if repo_norm and repo_norm in src_norm:
                                already = True
                                break
                if already:
                    _ps(f"espanso package update {pkg_name}")
                    cmds = []
        except Exception:
            pass

        if system == "Windows":
            last_err = ""
            code = 1
            for c in cmds:
                scmd = "Set-Location $env:USERPROFILE; espanso " + " ".join(c)
                code, out, err = _ps(scmd)
                if code == 0:
                    break
                last_err = err or out
            if code != 0 and (last_err or "").lower().find("already installed") != -1:
                _ps(f"Set-Location $env:USERPROFILE; espanso package update {pkg_name}")
                code = 0
            # Do not fall back to WSL for installs on Windows; it often lacks espanso
            if code != 0:
                _j("warn", "install_update", reason="win_ps_failed_no_wsl_fallback", last_err=(last_err or "").strip()[:200])
        else:
            ok = False
            last_err = ""
            for c in cmds:
                code, _, err = _direct(c)
                if code == 0:
                    ok = True
                    break
                last_err = err
            if not ok:
                _j("warn", "install_update", reason="git_install_failed", last_err=last_err.strip()[:200])
                _direct(["package", "update", pkg_name])

    if platform.system() == "Windows" and shutil.which("powershell.exe"):
        _ps("Set-Location $env:USERPROFILE; espanso restart")
        _ps("Set-Location $env:USERPROFILE; espanso package list")
    else:
        _direct(["restart"])
        _direct(["package", "list"])
    # Post-install prune as well (if a prior restart re-created samples)
    try:
        _prune_local_defaults()
    except Exception:
        pass
    _j("ok", "install_update_done", mode=mode)


def _ensure_version_aligned(pkg_name: str, expected_version: str, repo_url: str | None, local_path: Path | None, git_branch: str | None) -> None:
    """Ensure the installed package version matches the manifest version.

    - If mismatched, attempt update once.
    - If still mismatched, attempt uninstall + reinstall once.
    - If still mismatched, emit a warning and continue.
    """
    def _current_installed() -> tuple[str | None, str | None]:
        try:
            for p in _list_installed_packages():
                if p.get("name") == pkg_name:
                    return p.get("version"), p.get("source")
        except Exception:
            pass
        return None, None

    cur_ver, cur_src = _current_installed()
    if cur_ver == expected_version:
        _j("ok", "version_aligned", name=pkg_name, version=expected_version)
        return

    # Try update once
    try:
        if platform.system() == "Windows" and shutil.which("powershell.exe"):
            _run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"Set-Location $env:USERPROFILE; espanso package update {pkg_name}"
            ], timeout=12)
        else:
            bin_ = _espanso_bin()
            if bin_:
                _run(bin_ + ["package", "update", pkg_name], timeout=12)
    except Exception:
        pass

    cur_ver, cur_src = _current_installed()
    if cur_ver == expected_version:
        _j("ok", "version_aligned_after_update", name=pkg_name, version=expected_version)
        return

    # Uninstall and reinstall once (Git or default path per platform rules)
    try:
        _uninstall_package(pkg_name)
    except Exception:
        pass
    try:
        _install_or_update(pkg_name, repo_url, local_path, git_branch)
    except Exception:
        pass

    cur_ver, cur_src = _current_installed()
    if cur_ver == expected_version:
        _j("ok", "version_aligned_after_reinstall", name=pkg_name, version=expected_version)
        return

    # No further local-path attempts on Windows; warn persists

    _j("warn", "version_mismatch_persists", name=pkg_name, expected=expected_version, installed=cur_ver or "unknown", source=cur_src or "")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="espanso-sync", add_help=True)
    ap.add_argument("--repo", type=Path, default=None, help="Repository root containing espanso-package/")
    ap.add_argument("--auto-bump", choices=["off", "patch"], default=os.environ.get("PA_AUTO_BUMP", "patch"))
    ap.add_argument("--skip-install", action="store_true", default=os.environ.get("PA_SKIP_INSTALL") == "1")
    ap.add_argument("--dry-run", action="store_true", default=os.environ.get("PA_DRY_RUN") == "1")
    ap.add_argument("--git-branch", default=os.environ.get("PA_GIT_BRANCH", ""), help="Branch to install from when using git source (defaults to current branch)")
    args = ap.parse_args(argv)

    _j("start", "sync", os=platform.system())

    repo = _find_repo_root(args.repo)
    _j("ok", "discover_repo", repo=str(repo))

    # Enforce safer defaults early so they apply even on dry-run/skip-install flows
    try:
        _ensure_undo_backspace_disabled()
    except Exception:
        _j("warn", "undo_backspace_apply_failed", note="continuing")

    # Prepare branch & pull latest safely (no-op if not a git repo)
    git_branch = _active_branch(repo, args.git_branch)
    try:
        active_branch = _git_prepare_branch(repo, git_branch)
        if active_branch:
            git_branch = active_branch
    except Exception:
        _j("warn", "git_prepare_failed", note="continuing")

    # Generate from templates then validate
    _generate_from_templates(repo)
    # Validate
    _validate_yaml(repo)

    # Optional bump
    version = _maybe_bump_patch(repo, args.auto_bump == "patch")
    pkg_name, _ = _read_manifest(repo)
    # Mirror
    local_pkg_dir = _mirror(repo, pkg_name, version)
    # Commit and push authoritative state to origin for remote installs
    try:
        _git_commit_and_push(repo, git_branch, version)
    except Exception:
        _j("warn", "git_push_failed", note="continuing with install")
    # Tag and push tag
    try:
        _git_tag_and_push(repo, version)
    except Exception:
        _j("warn", "git_tag_failed", note="continuing")

    if args.dry_run:
        _j("ok", "dry_run", note="skipping install/update")
        return
    # Install/update
    if args.skip_install:
        _j("ok", "skip_install", reason="flag")
        return
    repo_url = _git_remote(repo)
    git_branch = _active_branch(repo, args.git_branch)
    # Remove conflicting package names that point to the same repo to prevent duplicates
    try:
        _resolve_conflicts(pkg_name, repo_url, local_pkg_dir)
    except Exception:
        pass
    _install_or_update(pkg_name, repo_url, local_pkg_dir, git_branch)
    # Enforce single-package convergence: remove any reappearing legacy or same-repo duplicates post-install
    try:
        _resolve_conflicts(pkg_name, repo_url, local_pkg_dir)
    except Exception:
        pass
    # Ensure manifest version alignment (retry once; warn if still mismatched)
    try:
        _ensure_version_aligned(pkg_name, version, repo_url, local_pkg_dir, git_branch)
    except Exception:
        pass
    # Windows-only advisory: if local base.yml exists, it may duplicate triggers.
    try:
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                base_yml = Path(appdata) / "espanso" / "match" / "base.yml"
                if base_yml.exists():
                    _j("warn", "local_base_present", path=str(base_yml), hint="Run scripts/espanso-windows.ps1 -DisableLocalBase to avoid duplicates")
    except Exception:
        pass
    _j("done", "sync")


if __name__ == "__main__":  # pragma: no cover
    main()
