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


if __name__ == "__main__":
    unittest.main()
