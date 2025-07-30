from prompt_automation import logger
from pathlib import Path
import sqlite3


def test_db_rotation(tmp_path, capsys):
    logger.DB_PATH = tmp_path / "usage.db"
    conn = sqlite3.connect(logger.DB_PATH)
    conn.execute("CREATE TABLE logs(ts TEXT, prompt_id TEXT, style TEXT, length INTEGER, tokens INTEGER)")
    conn.commit()
    conn.close()
    logger.DB_PATH.write_bytes(b"0" * (5 * 1024 * 1024 + 1))
    logger.rotate_db()
    out = capsys.readouterr().out
    assert "rotated" in out
