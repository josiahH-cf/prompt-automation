"""High level variable collection entry points."""
from __future__ import annotations

import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import PROMPTS_DIR
from ..errorlog import get_logger
from ..utils import safe_run
from ..features import is_reminders_enabled as _reminders_enabled
from ..reminders import cli_format_block as _cli_block, extract_placeholder_reminders as _extract_ph_reminders

from .files import _resolve_file_placeholder
from .gui import _gui_file_prompt, _gui_prompt
from .storage import _load_overrides, _save_overrides
from .values import persist_template_values


_log = get_logger(__name__)


def _editor_prompt() -> str | None:
    """Use ``$EDITOR`` as fallback."""
    try:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        editor = os.environ.get(
            "EDITOR", "notepad" if platform.system() == "Windows" else "nano"
        )
        safe_run([editor, path])
        return Path(path).read_text().strip()
    except Exception as e:  # pragma: no cover
        _log.error("editor prompt failed: %s", e)
        return None


def get_variables(
    placeholders: List[Dict],
    initial: Optional[Dict[str, Any]] = None,
    template_id: int | None = None,
    globals_map: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return dict of placeholder values.

    Added: persistent file placeholder handling with skip logic.
    """
    values: Dict[str, Any] = dict(initial or {})
    globals_map = globals_map or {}

    globals_notes: Dict[str, str] = {}
    try:
        gfile = PROMPTS_DIR / "globals.json"
        if gfile.exists():
            gdata = json.loads(gfile.read_text(encoding="utf-8"))
            globals_notes = gdata.get("notes", {}) or {}
    except Exception:
        pass

    persisted_values: Dict[str, Any] = {}
    try:
        if template_id is not None:
            persisted_values = (
                _load_overrides().get("template_values", {}).get(str(template_id), {}) or {}
            )
    except Exception:
        pass

    # CLI reminder header printed once per run (before first CLI prompt)
    _cli_header_printed = False

    for ph in placeholders:
        name = ph["name"]
        ptype = ph.get("type")

        if name not in values and name in persisted_values:
            values[name] = persisted_values[name]

        if "label" not in ph and name in globals_notes:
            note_text = globals_notes.get(name, "")
            if " – " in note_text:
                opt_part, desc_part = note_text.split(" – ", 1)
                if name == "hallucinate" and "|" in opt_part:
                    ph.setdefault("_option_hint_raw", opt_part)
                ph["label"] = desc_part.strip() or note_text.strip()
            else:
                ph["label"] = note_text.strip() or name

        # Ensure human-readable label is always available for downstream
        # fallback and retry logic, even when a pre-supplied value exists.
        label = ph.get("label", name)

    # reference_file now behaves like a normal per-template file placeholder when declared

        if ptype == "file" and template_id is not None:
            path_val = _resolve_file_placeholder(ph, template_id, globals_map)
            values[name] = path_val
            continue

        if name in values and values[name] not in ("", None):
            val: Any = values[name]
        else:
            opts = ph.get("options")
            if name == "hallucinate" and not opts:
                opts = [
                    "(omit)",
                    "Absolutely no hallucination (critical)",
                    "Balanced correctness & breadth (normal)",
                    "Some creative inference allowed (high)",
                    "Maximum creative exploration (low)",
                ]
                ph["_mapped_options"] = True
            multiline = ph.get("multiline", False) or ptype == "list"
            val = None
            if ptype == "file":
                val = _gui_file_prompt(label)
            else:
                val = _gui_prompt(label, opts, multiline)
                if val is None:
                    val = _editor_prompt()
            if val is None:
                _log.info("CLI fallback for %s", label)
                # When using CLI path, print template/global reminders once
                if _reminders_enabled() and not _cli_header_printed:
                    try:
                        tlist = (globals_map or {}).get("__template_reminders") or []
                        if isinstance(tlist, list) and tlist:
                            for line in _cli_block(tlist):
                                print(line)
                            print("")  # spacing
                    except Exception:
                        pass
                    _cli_header_printed = True
                # Print placeholder-level reminders (sanitized, if provided by upstream)
                if _reminders_enabled():
                    try:
                        rinl = ph.get("_reminders_inline") or _extract_ph_reminders(ph) or []
                        if isinstance(rinl, list) and rinl:
                            for line in _cli_block(rinl):
                                # suppress the header line; we want bullets only here
                                if not line.startswith("Reminders:"):
                                    print(line)
                    except Exception:
                        pass
                if opts:
                    print(f"{label} options: {', '.join(opts)}")
                    while True:
                        val = input(f"{label} [{opts[0]}]: ") or opts[0]
                        if val in opts:
                            break
                        print(f"Invalid option. Choose from: {', '.join(opts)}")
                elif ptype == "list" or multiline:
                    print(f"{label} (one per line, blank line to finish):")
                    lines: List[str] = []
                    while True:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                    val = lines
                elif ptype == "file":
                    while True:
                        val = input(f"{label} path: ")
                        if not val:
                            break
                        path = Path(val).expanduser()
                        if path.exists():
                            break
                        print(f"File not found: {path}")
                        retry = input("Try again? [Y/n]: ").lower()
                        if retry in {'n', 'no'}:
                            val = ""
                            break
                elif ptype == "number":
                    while True:
                        val = input(f"{label}: ")
                        try:
                            float(val)
                            break
                        except ValueError:
                            print("Please enter a valid number.")
                else:
                    val = input(f"{label}: ")

        if ptype == "file" and isinstance(val, str) and val and template_id is None:
            while val:
                path = Path(val).expanduser()
                if path.exists():
                    break
                _log.error("file not found: %s", path)
                new_val = _gui_file_prompt(label) or input(
                    f"{label} not found. Enter new path or leave blank to skip: "
                )
                if not new_val:
                    # Treat explicit skip as None (no value) to avoid
                    # downstream confusion between empty and unset.
                    val = None
                    break
                val = new_val

        if ptype == "number":
            try:
                float(val)  # type: ignore[arg-type]
            except Exception:
                val = "0"
        if ptype == "list" and isinstance(val, str):
            val = [l for l in val.splitlines() if l]
        if name == "hallucinate":
            if isinstance(val, str):
                lower = val.lower()
                if "omit" in lower or not lower.strip():
                    val = None
                elif "critical" in lower:
                    val = "critical"
                elif "normal" in lower:
                    val = "normal"
                elif "high" in lower:
                    val = "high"
                elif "low" in lower:
                    val = "low"
            elif val is None:
                val = None
        values[name] = val
    if template_id is not None:
        try:
            persist_template_values(template_id, placeholders, values)
        except Exception as e:  # pragma: no cover
            _log.error("failed to persist template values: %s", e)
    return values
