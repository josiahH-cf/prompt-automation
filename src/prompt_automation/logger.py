"""Usage logging with SQLite rotation."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
import os
from pathlib import Path
from typing import Dict, Tuple

DEFAULT_DB_PATH = Path.home() / ".prompt-automation" / "usage.db"
DB_PATH = Path(os.environ.get("PROMPT_AUTOMATION_DB", DEFAULT_DB_PATH))
DB_PATH.parent.mkdir(exist_ok=True)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS logs (ts TEXT, prompt_id TEXT, style TEXT, length INTEGER, tokens INTEGER)"
    )
    return conn


def log_usage(template: Dict, length: int) -> None:
    conn = _connect()
    tokens = length // 4
    conn.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), template["id"], template["style"], length, tokens),
    )
    conn.commit()
    conn.close()
    rotate_db()


def usage_counts(days: int = 7) -> Dict[Tuple[str, str], int]:
    cutoff = datetime.now() - timedelta(days=days)
    conn = _connect()
    rows = conn.execute(
        "SELECT prompt_id, style, COUNT(*) FROM logs WHERE ts > ? GROUP BY prompt_id, style",
        (cutoff.isoformat(),),
    ).fetchall()
    conn.close()
    return {(pid, style): c for pid, style, c in rows}


def rotate_db() -> None:
    if DB_PATH.exists() and DB_PATH.stat().st_size > 5 * 1024 * 1024:
        bak = DB_PATH.with_name(f"usage_{datetime.now():%Y%m%d}.db")
        DB_PATH.replace(bak)
        print("[prompt-automation] usage.db rotated")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS logs (ts TEXT, prompt_id TEXT, style TEXT, length INTEGER, tokens INTEGER)"
            )
            conn.commit()
            conn.execute("VACUUM")

