from __future__ import annotations

import pkgutil
import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema_v1.sql")


def _load_schema_sql() -> str:
    data = pkgutil.get_data("app.mediamanager.db", "schema_v1.sql")
    if data is not None:
        return data.decode("utf-8")
    return SCHEMA_PATH.read_text(encoding="utf-8")


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


def _ensure_is_hidden_columns(conn: sqlite3.Connection) -> None:
    # 1. media_items
    caps = {row[1] for row in conn.execute("PRAGMA table_info(media_items)").fetchall()}
    if "is_hidden" not in caps:
        conn.execute("ALTER TABLE media_items ADD COLUMN is_hidden INTEGER DEFAULT 0")

    # 2. folder_nodes
    caps = {row[1] for row in conn.execute("PRAGMA table_info(folder_nodes)").fetchall()}
    if "is_hidden" not in caps:
        conn.execute("ALTER TABLE folder_nodes ADD COLUMN is_hidden INTEGER DEFAULT 0")

    # 3. collections
    caps = {row[1] for row in conn.execute("PRAGMA table_info(collections)").fetchall()}
    if "is_hidden" not in caps:
        conn.execute("ALTER TABLE collections ADD COLUMN is_hidden INTEGER DEFAULT 0")


def _ensure_media_item_date_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_items)").fetchall()}
    if "file_created_time_utc" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN file_created_time_utc TEXT")
    if "original_file_date_utc" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN original_file_date_utc TEXT")
    if "exif_date_taken" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN exif_date_taken TEXT")
    if "metadata_date" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN metadata_date TEXT")
    if "phash" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN phash TEXT")
    if "text_detected" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detected INTEGER")
    if "text_detection_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_score REAL")
    if "text_detection_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_version INTEGER")
    if "text_more_likely" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely INTEGER")
    if "text_more_likely_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely_score REAL")
    if "text_more_likely_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely_version INTEGER")
    if "text_verified" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verified INTEGER")
    if "text_verification_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verification_score REAL")
    if "text_verification_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verification_version INTEGER")
    rows = conn.execute(
        "SELECT id, file_created_time_utc, modified_time_utc, original_file_date_utc FROM media_items"
    ).fetchall()
    for media_id, created_time, modified_time, original_file_date in rows:
        candidates = [str(value).strip() for value in (created_time, modified_time, original_file_date) if str(value or "").strip()]
        next_original = min(candidates) if candidates else None
        if next_original != (str(original_file_date).strip() if original_file_date is not None else None):
            conn.execute(
                "UPDATE media_items SET original_file_date_utc = ? WHERE id = ?",
                (next_original, int(media_id)),
            )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_phash ON media_items(phash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_detected ON media_items(text_detected)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_more_likely ON media_items(text_more_likely)")


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    sql = _load_schema_sql()
    # Old databases may not have newly added columns yet. Avoid creating indexes
    # against columns that will be added by the migration helpers below.
    sql = sql.replace(
        "CREATE INDEX IF NOT EXISTS idx_media_items_phash ON media_items(phash);\n",
        "",
    )
    sql = sql.replace(
        "CREATE INDEX IF NOT EXISTS idx_media_items_text_detected ON media_items(text_detected);\n",
        "",
    )
    sql = sql.replace(
        "CREATE INDEX IF NOT EXISTS idx_media_items_text_more_likely ON media_items(text_more_likely);\n",
        "",
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        # The sandboxed Windows environment used in tests can fail when SQLite
        # tries to create rollback journals on disk. Keep schema initialization
        # in memory-backed journal mode.
        conn.execute("PRAGMA journal_mode=MEMORY;")
        conn.executescript(sql)
        _ensure_media_metadata_columns(conn)
        _ensure_is_hidden_columns(conn)
        _ensure_media_item_date_columns(conn)
        conn.commit()
