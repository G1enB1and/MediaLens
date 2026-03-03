import sqlite3
import unittest
from pathlib import Path

from app.mediamanager.db.media_repo import add_media_item, list_media_in_scope
from app.mediamanager.db.migrations import init_db


class TestMediaRepo(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path('.tmp-tests')
        self.tmp_dir.mkdir(exist_ok=True)
        import uuid
        self.db_path = self.tmp_dir / f'media-repo-{uuid.uuid4()}.db'
        init_db(str(self.db_path))

    def tearDown(self) -> None:
        try:
            if hasattr(self, 'db_path') and self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_add_media_item_normalizes_path(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            media_id = add_media_item(conn, r"C:\\Media\\Cats\\A.JPG", 'image')
            self.assertEqual(media_id, 1)
            rows = conn.execute("SELECT path FROM media_items").fetchall()
            self.assertEqual(rows[0][0], 'c:/media/cats/a.jpg')

    def test_list_media_in_scope_filters_correctly(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            add_media_item(conn, r"C:\\Media\\Cats\\a.jpg", 'image')
            add_media_item(conn, r"C:\\Media\\Dogs\\b.jpg", 'image')
            add_media_item(conn, r"C:\\Elsewhere\\c.jpg", 'image')

            scoped = list_media_in_scope(conn, [r"C:\\Media\\Cats", r"C:\\Media\\Dogs"])
            self.assertEqual([r['path'] for r in scoped], ['c:/media/cats/a.jpg', 'c:/media/dogs/b.jpg'])

    def test_list_media_in_scope_supports_limit_offset(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            for i in range(5):
                add_media_item(conn, fr"C:\\Media\\Cats\\{i}.jpg", 'image')

            from app.mediamanager.db.media_repo import list_media_page
            page = list_media_page(conn, [r"C:\\Media\\Cats"], page=1, page_size=2)
            self.assertEqual([r['path'] for r in page], ['c:/media/cats/0.jpg', 'c:/media/cats/1.jpg'])

    def test_move_directory_in_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            from app.mediamanager.db.media_repo import move_directory_in_db
            add_media_item(conn, r"C:\\Media\\Cats\\1.jpg", 'image')
            add_media_item(conn, r"C:\\Media\\Cats\\2.jpg", 'image')
            add_media_item(conn, r"C:\\Media\\Dogs\\3.jpg", 'image')
            
            # Move Cats to Pets
            move_directory_in_db(conn, r"C:\\Media\\Cats", r"C:\\Media\\Pets\\Cats")
            
            rows = conn.execute("SELECT path FROM media_items ORDER BY path").fetchall()
            paths = [r[0] for r in rows]
            self.assertIn('c:/media/pets/cats/1.jpg', paths)
            self.assertIn('c:/media/pets/cats/2.jpg', paths)
            self.assertIn('c:/media/dogs/3.jpg', paths)
            self.assertNotIn('c:/media/cats/1.jpg', paths)


if __name__ == '__main__':
    unittest.main()
