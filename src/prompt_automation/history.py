"""Recent template execution history (lightweight, privacy-aware, persistent).

Features:
- Persist up to HISTORY_LIMIT entries (newest first) to HOME_DIR/recent-history.json.
- Atomic writes (tmp + rename). Defensive load; quarantine corrupt file.
- Redaction hook for sensitive patterns from env or settings.
- Feature flags via env/settings: enable/disable and purge-on-disable.

Environment variables (optional):
- PROMPT_AUTOMATION_HISTORY: "1/true/on" enables, "0/false/off" disables. Default: enabled.
- PROMPT_AUTOMATION_HISTORY_PURGE_ON_DISABLE: same coercion; default: disabled.
- PROMPT_AUTOMATION_HISTORY_REDACTION_PATTERNS: JSON array or comma-separated list of regexes.

Settings keys (PROMPTS_DIR/Settings/settings.json):
- recent_history_enabled: bool (overridden by env if set)
- recent_history_purge_on_disable: bool
- recent_history_redaction_patterns: list[str]

Data shape (schema_version=1):
{
  "schema_version": 1,
  "limit": 5,
  "entries": [
    {
      "entry_id": "<uuid4>",
      "template_id": 123,
      "title": "...",
      "ts": "2025-01-01T00:00:00Z",
      "rendered": "...",  # pre post-render if available; else equals output
      "output": "..."      # final resolved output (post-render)
    }
  ]
}
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import HOME_DIR, PROMPTS_DIR
from .errorlog import get_logger

_log = get_logger(__name__)

SCHEMA_VERSION = 1
DEFAULT_LIMIT = 5


def _coerce_bool(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
    return None


def _settings_path() -> Path:
    return PROMPTS_DIR / "Settings" / "settings.json"


def _load_settings_payload() -> Dict[str, Any]:
    p = _settings_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    except Exception:  # pragma: no cover - defensive
        return {}


def is_enabled() -> bool:
    env = os.environ.get("PROMPT_AUTOMATION_HISTORY")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return coerced
    try:
        pay = _load_settings_payload()
        val = pay.get("recent_history_enabled")
        coerced = _coerce_bool(val)
        if coerced is not None:
            return coerced
    except Exception:
        pass
    return True


def purge_on_disable() -> bool:
    env = os.environ.get("PROMPT_AUTOMATION_HISTORY_PURGE_ON_DISABLE")
    coerced = _coerce_bool(env) if env is not None else None
    if coerced is not None:
        return coerced
    try:
        pay = _load_settings_payload()
        val = pay.get("recent_history_purge_on_disable")
        coerced = _coerce_bool(val)
        if coerced is not None:
            return coerced
    except Exception:
        pass
    return False


def _redaction_patterns() -> List[re.Pattern[str]]:
    patterns: List[str] = []
    # Env may be JSON array or comma-separated
    raw = os.environ.get("PROMPT_AUTOMATION_HISTORY_REDACTION_PATTERNS")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                patterns.extend([str(x) for x in data if isinstance(x, str)])
        except Exception:
            patterns.extend([s.strip() for s in raw.split(",") if s.strip()])
    try:
        pay = _load_settings_payload()
        lst = pay.get("recent_history_redaction_patterns")
        if isinstance(lst, list):
            patterns.extend([str(x) for x in lst if isinstance(x, str)])
    except Exception:
        pass
    compiled: List[re.Pattern[str]] = []
    for s in patterns:
        try:
            compiled.append(re.compile(s))
        except re.error:
            try:
                _log.info("history.redaction_pattern_invalid", extra={"pattern": s})
            except Exception:
                pass
    return compiled


def _apply_redaction(text: str) -> str:
    if not text:
        return text
    try:
        redacted = text
        for pat in _redaction_patterns():
            redacted = pat.sub("[REDACTED]", redacted)
        return redacted
    except Exception:
        return text


@dataclass
class HistoryEntry:
    entry_id: str
    template_id: int | str | None
    title: str | None
    ts: str  # ISO-8601 UTC
    rendered: str
    output: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "template_id": self.template_id,
            "title": self.title,
            "ts": self.ts,
            "rendered": self.rendered,
            "output": self.output,
        }


class RecentHistoryStore:
    """JSON-backed recent history with rotation and redaction."""

    def __init__(self, path: Path | None = None, *, limit: int = DEFAULT_LIMIT) -> None:
        self.path = path or (HOME_DIR / "recent-history.json")
        self.limit = int(limit) if limit and int(limit) > 0 else DEFAULT_LIMIT
        self._entries: List[HistoryEntry] = []
        self._loaded = False
        # Pre-create directory
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # --- Persistence --------------------------------------------------------
    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            self._entries = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid root type")
            if int(data.get("schema_version", 0)) != SCHEMA_VERSION:
                raise ValueError("schema version mismatch")
            raw_entries = data.get("entries") or []
            if not isinstance(raw_entries, list):
                raise ValueError("invalid entries")
            entries: List[HistoryEntry] = []
            for item in raw_entries:
                if not isinstance(item, dict):
                    continue
                try:
                    entries.append(
                        HistoryEntry(
                            entry_id=str(item.get("entry_id") or ""),
                            template_id=item.get("template_id"),
                            title=str(item.get("title")) if item.get("title") is not None else None,
                            ts=str(item.get("ts") or ""),
                            rendered=str(item.get("rendered") or ""),
                            output=str(item.get("output") or ""),
                        )
                    )
                except Exception:
                    continue
            # Ensure newest->oldest based on ts, then insertion order as stored
            def _key(e: HistoryEntry):
                return e.ts
            entries.sort(key=_key, reverse=True)
            self._entries = entries[: self.limit]
        except Exception:
            # Quarantine corrupt file and reset
            try:
                ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
                corrupt = self.path.with_suffix(f".corrupt-{ts}")
                self.path.replace(corrupt)
                try:
                    _log.info("history.quarantined", extra={"renamed_to": str(corrupt)})
                except Exception:
                    pass
            except Exception:
                pass
            self._entries = []

    def _flush(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "limit": self.limit,
            "entries": [e.to_dict() for e in self._entries],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self.path)
        try:
            _log.info("history.flush", extra={"entries": len(self._entries)})
        except Exception:
            pass

    # --- API ----------------------------------------------------------------
    def get_entries(self) -> List[Dict[str, Any]]:
        self._load()
        # Return shallow copies as dicts newest first
        return [e.to_dict() for e in self._entries]

    def append(self, *, template: Dict[str, Any] | None, rendered_text: str, final_output: str | None = None) -> None:
        if not is_enabled():
            # Optionally purge when disabled
            if purge_on_disable():
                try:
                    if self.path.exists():
                        self.path.unlink()
                        try:
                            _log.info("history.purged_on_disable")
                        except Exception:
                            pass
                except Exception:
                    pass
            return

        self._load()
        title = None
        template_id: int | str | None = None
        try:
            if isinstance(template, dict):
                title = template.get("title")
                template_id = template.get("id")
        except Exception:
            pass
        out = final_output if final_output is not None else rendered_text
        # Redact before storing
        red_rendered = _apply_redaction(rendered_text)
        red_output = _apply_redaction(out)

        entry = HistoryEntry(
            entry_id=uuid.uuid4().hex,
            template_id=template_id,
            title=str(title) if title is not None else None,
            ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            rendered=red_rendered,
            output=red_output,
        )
        # Insert newest first
        self._entries.insert(0, entry)
        rotated = False
        if len(self._entries) > self.limit:
            self._entries = self._entries[: self.limit]
            rotated = True
        # Observability: log rotation and a safe fingerprint
        try:
            if rotated:
                _log.info("history.rotate", extra={"limit": self.limit})
            # Debug-level fingerprint (never raw content)
            try:
                fp = sha256(red_output.encode("utf-8")).hexdigest()[:12]
                _log.debug("history.append", extra={"title": title or "", "fp": fp})
            except Exception:
                pass
        except Exception:
            pass
        # Flush
        self._flush()


# Convenience singleton-style helpers ----------------------------------------
_DEFAULT_STORE: RecentHistoryStore | None = None


def _store() -> RecentHistoryStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = RecentHistoryStore()
    return _DEFAULT_STORE


def record_history(template: Dict[str, Any] | None, *, rendered_text: str, final_output: str | None = None) -> None:
    """Append a history entry if enabled, with redaction and rotation.

    - ``rendered_text``: text after placeholder fill; in GUI this is the review text.
    - ``final_output``: post-render; if None, equals rendered_text.
    """
    try:
        _store().append(template=template, rendered_text=rendered_text, final_output=final_output)
    except Exception:
        # Never block user flows on history failures
        pass


def list_history() -> List[Dict[str, Any]]:
    try:
        return _store().get_entries()
    except Exception:
        return []


__all__ = [
    "RecentHistoryStore",
    "record_history",
    "list_history",
    "is_enabled",
    "purge_on_disable",
]

