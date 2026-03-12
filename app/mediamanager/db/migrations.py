from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema_v1.sql")


def _ensure_media_metadata_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_metadata)").fetchall()}
    if "exif_tags" in cols and "embedded_tags" not in cols:
        conn.execute("ALTER TABLE media_metadata RENAME COLUMN exif_tags TO embedded_tags")
        cols.remove("exif_tags")
        cols.add("embedded_tags")
    elif "embedded_tags" not in cols:
        conn.execute("ALTER TABLE media_metadata ADD COLUMN embedded_tags TEXT")
        cols.add("embedded_tags")

    if "exif_comments" in cols and "embedded_comments" not in cols:
        conn.execute("ALTER TABLE media_metadata RENAME COLUMN exif_comments TO embedded_comments")
        cols.remove("exif_comments")
        cols.add("embedded_comments")
    elif "embedded_comments" not in cols:
        conn.execute("ALTER TABLE media_metadata ADD COLUMN embedded_comments TEXT")
        cols.add("embedded_comments")

    if "embedded_ai_prompt" in cols and "ai_prompt" not in cols:
        conn.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_prompt TO ai_prompt")
        cols.remove("embedded_ai_prompt")
        cols.add("ai_prompt")
    elif "ai_prompt" not in cols:
        conn.execute("ALTER TABLE media_metadata ADD COLUMN ai_prompt TEXT")
        cols.add("ai_prompt")

    if "ai_negative_prompt" not in cols:
        conn.execute("ALTER TABLE media_metadata ADD COLUMN ai_negative_prompt TEXT")
        cols.add("ai_negative_prompt")

    if "embedded_ai_params" in cols and "ai_params" not in cols:
        conn.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_params TO ai_params")
        cols.remove("embedded_ai_params")
        cols.add("ai_params")
    elif "ai_params" not in cols:
        conn.execute("ALTER TABLE media_metadata ADD COLUMN ai_params TEXT")


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        # The sandboxed Windows environment used in tests can fail when SQLite
        # tries to create rollback journals on disk. Keep schema initialization
        # in memory-backed journal mode.
        conn.execute("PRAGMA journal_mode=MEMORY;")
        conn.executescript(sql)
        _ensure_media_metadata_columns(conn)
        conn.commit()
