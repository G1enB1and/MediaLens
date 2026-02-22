import os
import shutil
import uuid
import time
import sqlite3
import unittest
from pathlib import Path
from app.mediamanager.db.media_repo import upsert_media_item, get_media_by_path, get_media_by_hash
from app.mediamanager.db.migrations import init_db
from app.mediamanager.utils.hashing import calculate_file_hash

class TestHashingAndMoves(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(".tmp-tests-hashing-" + str(uuid.uuid4())[:8])
        self.tmp_path.mkdir(exist_ok=True, parents=True)
        self.db_path = self.tmp_path / "test.db"
        init_db(str(self.db_path))
        self.conn = sqlite3.connect(self.db_path)

    def tearDown(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
        time.sleep(0.1)
        try:
            shutil.rmtree(self.tmp_path)
        except PermissionError:
            pass

    def test_upsert_new_item(self):
        # Create a dummy file
        f1 = self.tmp_path / "file1.jpg"
        f1.write_text("content1")
        h1 = calculate_file_hash(f1)
        
        media_id = upsert_media_item(self.conn, str(f1), "image", h1)
        self.assertEqual(media_id, 1)
        
        item = get_media_by_path(self.conn, str(f1))
        self.assertIsNotNone(item)
        self.assertEqual(item["path"], str(f1).replace("\\", "/").lower())

    def test_detect_move_by_hash(self):
        # 1. Add file
        f1 = self.tmp_path / "file1.jpg"
        f1.write_text("content1")
        h1 = calculate_file_hash(f1)
        upsert_media_item(self.conn, str(f1), "image", h1)
        
        # 2. "Move" file on disk (rename)
        f2 = self.tmp_path / "file1_moved.jpg"
        os.rename(f1, f2)
        
        # 3. Upsert at new path. It should find the old hash and update the path.
        media_id = upsert_media_item(self.conn, str(f2), "image", h1)
        self.assertEqual(media_id, 1) # Same ID
        
        # Verify old path is gone (replaced) and new path is present
        old_item = get_media_by_path(self.conn, str(f1))
        self.assertIsNone(old_item)
        
        new_item = get_media_by_path(self.conn, str(f2))
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item["id"], 1)
        
        # Check history
        history = self.conn.execute("SELECT old_path, new_path FROM media_paths_history WHERE media_id = ?", (1,)).fetchall()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1], str(f2).replace("\\", "/").lower())

    def test_duplicate_file_different_path(self):
        # Two different files with same content
        f1 = self.tmp_path / "original.jpg"
        f1.write_text("same_content")
        h1 = calculate_file_hash(f1)
        upsert_media_item(self.conn, str(f1), "image", h1)
        
        f2 = self.tmp_path / "copy.jpg"
        f2.write_text("same_content")
        h2 = calculate_file_hash(f2) # h2 == h1
        
        # Upserting f2 should NOT update f1's path because f1 still exists.
        # It should create a new record with same hash.
        media_id = upsert_media_item(self.conn, str(f2), "image", h2)
        
        self.assertEqual(media_id, 2) # New ID because f1 still exists
        item = get_media_by_path(self.conn, str(f2))
        self.assertIsNotNone(item)
        
        # Original f1 should still be there
        f1_item = get_media_by_path(self.conn, str(f1))
        self.assertIsNotNone(f1_item)
        self.assertEqual(f1_item["id"], 1)

if __name__ == "__main__":
    unittest.main()
