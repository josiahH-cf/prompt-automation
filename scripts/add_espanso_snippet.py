#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as e:
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
SRC_MATCH_DIR = ROOT / "espanso-package" / "match"


def load_yaml(path: Path):
    if not path.exists():
        return {"matches": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must be a YAML mapping at top level")
    data.setdefault("matches", [])
    if not isinstance(data["matches"], list):
        raise SystemExit(f"{path} 'matches' must be a list")
    return data


def collect_all_triggers(match_dir: Path) -> set[str]:
    triggers: set[str] = set()
    for p in match_dir.glob("*.yml"):
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for m in (d.get("matches") or []):
            t = m.get("trigger")
            if isinstance(t, str):
                triggers.add(t)
    return triggers


def main() -> int:
    ap = argparse.ArgumentParser(description="Add a simple espanso snippet to a match file")
    ap.add_argument("--file", required=True, help="match file under espanso-package/match (e.g., base.yml)")
    ap.add_argument("--trigger", required=True, help="trigger starting with ':' (no spaces)")
    ap.add_argument("--replace", required=False, help="replacement text; if omitted, read from stdin")
    ns = ap.parse_args()

    if " " in ns.trigger or not ns.trigger.startswith(":"):
        print("Trigger must start with ':' and contain no spaces", file=sys.stderr)
        return 1

    replace = ns.replace
    if replace is None:
        replace = sys.stdin.read()
    if not replace:
        print("Replace text cannot be empty", file=sys.stderr)
        return 1

    match_dir = SRC_MATCH_DIR
    match_dir.mkdir(parents=True, exist_ok=True)
    path = match_dir / ns.file

    # Duplicate trigger guard (across all files)
    all_triggers = collect_all_triggers(match_dir)
    if ns.trigger in all_triggers:
        print(f"Trigger already exists somewhere: {ns.trigger}", file=sys.stderr)
        return 1

    data = load_yaml(path)
    data["matches"].append({"trigger": ns.trigger, "replace": replace})
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Added snippet to {path}: {ns.trigger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

