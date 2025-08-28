"""Usage logging with SQLite rotation."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
import os
from typing import Dict, Tuple

from .config import DB_PATH

_LOCK_FH = None


def _lock_db() -> None:
    """Acquire a cross-platform file lock, warn on failure."""
    global _LOCK_FH
    if _LOCK_FH:
        print("[prompt-automation] Warning: usage.db in use by another process")
        return
    lock_path = DB_PATH.with_suffix(".lock")
    try:
        fh = open(lock_path, "w")
    except Exception:
        # Sandbox/no permission: skip locking
        return
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        else:
            import fcntl

            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[prompt-automation] Warning: usage.db in use by another process")
    _LOCK_FH = fh


def _unlock_db() -> None:
    global _LOCK_FH
    if not _LOCK_FH:
        return
    fh = _LOCK_FH
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        else:
            import fcntl

            fcntl.flock(fh, fcntl.LOCK_UN)
    finally:
        fh.close()
        _LOCK_FH = None


def _connect() -> sqlite3.Connection:
    _lock_db()
    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception:  # pragma: no cover - permission/sandbox fallback
        conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS logs (ts TEXT, prompt_id TEXT, style TEXT, length INTEGER, tokens INTEGER)"
    )
    return conn


def log_usage(template: Dict, length: int) -> None:
    try:
        conn = _connect()
        tokens = length // 4
        conn.execute(
            "INSERT INTO logs VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), template["id"], template["style"], length, tokens),
        )
        conn.commit()
        conn.close()
        _unlock_db()
        rotate_db()
    except Exception:
        # Logging is best-effort; ignore failures in restricted environments
        try:
            _unlock_db()
        except Exception:
            pass


def usage_counts(days: int = 7) -> Dict[Tuple[str, str], int]:
    cutoff = datetime.now() - timedelta(days=days)
    conn = _connect()
    rows = conn.execute(
        "SELECT prompt_id, style, COUNT(*) FROM logs WHERE ts > ? GROUP BY prompt_id, style",
        (cutoff.isoformat(),),
    ).fetchall()
    conn.close()
    _unlock_db()
    return {(pid, style): c for pid, style, c in rows}


def rotate_db() -> None:
    if DB_PATH.exists() and DB_PATH.stat().st_size > 5 * 1024 * 1024:
        bak = DB_PATH.with_name(f"usage_{datetime.now():%Y%m%d}.db")
        DB_PATH.replace(bak)
        print("[prompt-automation] usage.db rotated")
        _lock_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS logs (ts TEXT, prompt_id TEXT, style TEXT, length INTEGER, tokens INTEGER)"
            )
            conn.commit()
            conn.execute("VACUUM")
        _unlock_db()


def clear_usage_log() -> None:
    """Remove the usage database file."""
    if DB_PATH.exists():
        DB_PATH.unlink()
