import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from app.mediamanager.db.migrations import init_db
from app.mediamanager.db.tag_lists_repo import add_tag_to_list, create_tag_list, list_tag_list_entries
from app.mediamanager.db.tags_repo import attach_tags, list_media_tags


class TestTagsRepo(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path('.tmp-tests')
        tmp_dir.mkdir(exist_ok=True)
        self.db_path = tmp_dir / 'tags.db'
        if self.db_path.exists():
            self.db_path.unlink()
        init_db(str(self.db_path))

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO media_items (
                  path, media_type, created_at_utc, updated_at_utc
                ) VALUES (?, ?, datetime('now'), datetime('now'))
                """,
                ('c:/media/cats/a.jpg', 'image'),
            )
            conn.commit()

    def test_attach_and_list_tags(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            attach_tags(conn, 1, ['cat', 'cute'])
            tags = list_media_tags(conn, 1)
        self.assertEqual(tags, ['cat', 'cute'])

    def test_attach_tags_is_idempotent_and_normalized(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            attach_tags(conn, 1, ['cat', 'cat', '  cat  ', ''])
            tags = list_media_tags(conn, 1)
        self.assertEqual(tags, ['cat'])

    def test_attach_tags_preserves_capitals_and_dedupes_case(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            attach_tags(conn, 1, ['bigmike'])
            attach_tags(conn, 1, ['BigMike'])
            tags = list_media_tags(conn, 1)
            rows = conn.execute("SELECT name FROM tags WHERE LOWER(name) = LOWER(?)", ('BigMike',)).fetchall()
        self.assertEqual(tags, ['BigMike'])
        self.assertEqual([row[0] for row in rows], ['BigMike'])

    def test_tag_list_import_preserves_capitals_and_dedupes_case(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            tag_list = create_tag_list(conn, 'People')
            self.assertIsNotNone(tag_list)
            tag_list_id = int(tag_list['id'])
            add_tag_to_list(conn, tag_list_id, 'bigmike')
            add_tag_to_list(conn, tag_list_id, 'BigMike')
            entries = list_tag_list_entries(conn, tag_list_id)
        self.assertEqual([entry['name'] for entry in entries], ['BigMike'])


if __name__ == '__main__':
    unittest.main()
