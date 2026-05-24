from __future__ import annotations

import pkgutil
import re
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

    # 4. tag_lists
    caps = {row[1] for row in conn.execute("PRAGMA table_info(tag_lists)").fetchall()}
    if "is_hidden" not in caps:
        conn.execute("ALTER TABLE tag_lists ADD COLUMN is_hidden INTEGER DEFAULT 0")


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
    if "text_likely" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_likely INTEGER")
        if "text_detected" in cols:
            conn.execute("UPDATE media_items SET text_likely = text_detected WHERE text_likely IS NULL")
    if "text_detection_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_score REAL")
    if "text_detection_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_version INTEGER")
    if "user_confirmed_text_detected" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN user_confirmed_text_detected INTEGER")
    if "detected_text" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN detected_text TEXT")
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_likely ON media_items(text_likely)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_more_likely ON media_items(text_more_likely)")


def _ensure_ocr_tables(conn: sqlite3.Connection) -> None:
    from app.mediamanager.db.ocr_repo import ensure_ocr_tables

    ensure_ocr_tables(conn)


def _ensure_people_tables(conn: sqlite3.Connection) -> None:
    from app.mediamanager.db.people_repo import ensure_people_tables

    ensure_people_tables(conn)


def _ensure_collection_folder_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_folders (
          collection_id INTEGER NOT NULL,
          folder_path TEXT NOT NULL,
          created_at_utc TEXT NOT NULL,
          PRIMARY KEY (collection_id, folder_path),
          FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_folders_collection ON collection_folders(collection_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_folders_path ON collection_folders(folder_path)")


def _ensure_local_ai_status_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS local_ai_status_cache (
          cache_key TEXT PRIMARY KEY,
          settings_key TEXT NOT NULL,
          model_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          context_json TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_local_ai_status_cache_settings ON local_ai_status_cache(settings_key)")


def _ensure_action_history_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS action_history_entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          transaction_id TEXT NOT NULL,
          timestamp_utc TEXT NOT NULL,
          action_type TEXT NOT NULL,
          origin TEXT NOT NULL DEFAULT 'user',
          summary TEXT NOT NULL,
          item_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'success',
          undo_state TEXT NOT NULL DEFAULT 'not_undoable',
          metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_entries_time ON action_history_entries(timestamp_utc DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_entries_type ON action_history_entries(action_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_entries_transaction ON action_history_entries(transaction_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_entries_undo ON action_history_entries(undo_state, id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS action_history_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entry_id INTEGER NOT NULL,
          item_type TEXT NOT NULL DEFAULT 'file',
          old_path TEXT,
          new_path TEXT,
          retention_id TEXT,
          result TEXT NOT NULL DEFAULT 'success',
          current_state TEXT NOT NULL DEFAULT 'applied',
          last_change_source TEXT NOT NULL DEFAULT 'original_action',
          notes TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          FOREIGN KEY(entry_id) REFERENCES action_history_entries(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_items_entry ON action_history_items(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_action_history_items_state ON action_history_items(current_state, last_change_source)")


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    sql = _load_schema_sql()
    # Old databases may not have newly added columns yet. Avoid creating
    # indexes against columns that are added later by the migration helpers.
    # Use a regex so this remains safe across LF/CRLF and packaged schema text.
    sql = re.sub(
        r"(?im)^\s*CREATE INDEX IF NOT EXISTS idx_media_items_(?:phash|text_detected|text_likely|text_more_likely)\s+ON\s+media_items\([^)]+\);\s*$",
        "",
        sql,
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON;")
        # The sandboxed Windows environment used in tests can fail when SQLite
        # tries to create rollback journals on disk. Keep schema initialization
        # in memory-backed journal mode.
        conn.execute("PRAGMA journal_mode=MEMORY;")
        conn.executescript(sql)
        _ensure_media_metadata_columns(conn)
        _ensure_is_hidden_columns(conn)
        _ensure_media_item_date_columns(conn)
        _ensure_ocr_tables(conn)
        _ensure_people_tables(conn)
        _ensure_collection_folder_tables(conn)
        _ensure_local_ai_status_cache_table(conn)
        _ensure_action_history_tables(conn)
        conn.commit()
    finally:
        conn.close()
