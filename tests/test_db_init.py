import sqlite3
import unittest
import uuid
from pathlib import Path

from app.mediamanager.db.migrations import init_db


class TestDbInit(unittest.TestCase):
    def test_init_db_creates_core_tables(self) -> None:
        tmp_dir = Path(".tmp-tests")
        tmp_dir.mkdir(exist_ok=True)
        db_path = tmp_dir / f"mm-{uuid.uuid4()}.db"
        if db_path.exists():
            db_path.unlink()

        init_db(str(db_path))

        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

        self.assertIn("media_items", tables)
        self.assertIn("media_metadata", tables)
        self.assertIn("media_ai_metadata", tables)
        self.assertIn("media_ai_metadata_raw", tables)
        self.assertIn("media_ai_loras", tables)
        self.assertIn("media_ai_workflows", tables)
        self.assertIn("media_ai_provenance", tables)
        self.assertIn("media_character_cards", tables)
        self.assertIn("tags", tables)
        self.assertIn("media_tags", tables)
        self.assertIn("folder_nodes", tables)
        self.assertIn("folder_selection_state", tables)
        self.assertIn("collections", tables)
        self.assertIn("collection_items", tables)

    def test_init_db_upgrades_legacy_media_items_without_phash(self) -> None:
        tmp_dir = Path(".tmp-tests")
        tmp_dir.mkdir(exist_ok=True)
        db_path = tmp_dir / f"mm-legacy-{uuid.uuid4()}.db"
        if db_path.exists():
            db_path.unlink()

        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE media_items (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  path TEXT NOT NULL UNIQUE,
                  content_hash TEXT,
                  media_type TEXT NOT NULL,
                  file_size_bytes INTEGER,
                  modified_time_utc TEXT,
                  width INTEGER,
                  height INTEGER,
                  duration_ms INTEGER,
                  thumb_path TEXT,
                  preview_path TEXT,
                  created_at_utc TEXT NOT NULL,
                  updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE media_metadata (
                  media_id INTEGER PRIMARY KEY,
                  title TEXT,
                  description TEXT,
                  notes TEXT,
                  updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE folder_nodes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  path TEXT NOT NULL UNIQUE,
                  parent_path TEXT,
                  depth INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE collections (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL UNIQUE,
                  created_at_utc TEXT NOT NULL,
                  updated_at_utc TEXT NOT NULL
                );
                """
            )
            conn.commit()

        init_db(str(db_path))

        with sqlite3.connect(db_path) as conn:
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(media_items)").fetchall()
            }
            indexes = {
                row[1]
                for row in conn.execute("PRAGMA index_list(media_items)").fetchall()
            }

        self.assertIn("phash", columns)
        self.assertIn("text_likely", columns)
        self.assertIn("user_confirmed_text_detected", columns)
        self.assertIn("detected_text", columns)
        self.assertIn("text_more_likely", columns)
        self.assertIn("idx_media_items_phash", indexes)

    def test_init_db_copies_legacy_text_detected_to_text_likely(self) -> None:
        tmp_dir = Path(".tmp-tests")
        tmp_dir.mkdir(exist_ok=True)
        db_path = tmp_dir / f"mm-legacy-text-{uuid.uuid4()}.db"
        if db_path.exists():
            db_path.unlink()

        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE media_items (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  path TEXT NOT NULL UNIQUE,
                  content_hash TEXT,
                  media_type TEXT NOT NULL,
                  file_size_bytes INTEGER,
                  modified_time_utc TEXT,
                  text_detected INTEGER,
                  created_at_utc TEXT NOT NULL,
                  updated_at_utc TEXT NOT NULL
                );
                INSERT INTO media_items(path, media_type, text_detected, created_at_utc, updated_at_utc)
                VALUES ('c:/media/cats/a.jpg', 'image', 1, datetime('now'), datetime('now'));
                """
            )
            conn.commit()

        init_db(str(db_path))

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT text_likely FROM media_items WHERE path = ?",
                ("c:/media/cats/a.jpg",),
            ).fetchone()

        self.assertEqual(row[0], 1)


if __name__ == "__main__":
    unittest.main()
