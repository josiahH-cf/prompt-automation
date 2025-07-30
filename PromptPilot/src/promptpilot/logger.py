import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

DB_PATH = Path.home() / ".promptpilot" / "usage.db"
DB_PATH.parent.mkdir(exist_ok=True)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS logs (timestamp TEXT, prompt_id INTEGER, length INTEGER, tokens INTEGER)"
        )


def rotate_db() -> None:
    if DB_PATH.exists() and DB_PATH.stat().st_size > 5 * 1024 * 1024:
        backup = DB_PATH.with_name(f"usage_{datetime.now():%Y%m%d}.db")
        DB_PATH.rename(backup)


def log_usage(template: Dict) -> None:
    init_db()
    length = sum(len(line) for line in template.get("template", []))
    tokens = length // 4
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO logs VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), template.get("id"), length, tokens),
        )
    rotate_db()
