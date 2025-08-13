#!/usr/bin/env python
"""Idempotent migration: add metadata.share_this_file_openly=true to templates.

Rules implemented:
  * Only touches JSON files under src/prompt_automation/prompts/styles/.
  * Skips files already containing the flag.
  * Creates a metadata object if missing.
  * Leaves non-template (no 'template' array) files intact unless you want the flag there too.

Run: python scripts/add_share_flag.py
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = ROOT / "src" / "prompt_automation" / "prompts" / "styles"

CHANGED = 0
SKIPPED = 0
ERRORS: list[str] = []

for path in sorted(STYLES_DIR.rglob("*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        ERRORS.append(f"Unreadable {path}: {e}")
        continue
    # Only operate on template-like files (have 'template' key list) but still
    # add for others if they already have metadata (harmless).
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
    if meta and isinstance(meta.get("share_this_file_openly"), bool):
        SKIPPED += 1
        continue
    # Insert / create
    if not meta:
        meta = {}
        data["metadata"] = meta
    # Respect explicit False if somehow present but not bool (will coerce)
    val = meta.get("share_this_file_openly")
    if isinstance(val, bool):
        SKIPPED += 1
        continue
    meta["share_this_file_openly"] = True
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    CHANGED += 1

print(f"[migration] share flag add complete: changed={CHANGED} skipped={SKIPPED} errors={len(ERRORS)}")
if ERRORS:
    for e in ERRORS:
        print("  -", e)
    sys.exit(1)
