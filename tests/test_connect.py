import unittest
import uuid
from pathlib import Path

from app.mediamanager.db.connect import connect_db


class TestConnect(unittest.TestCase):
    def test_connect_db_creates_blank_database_if_missing(self) -> None:
        tmp_dir = Path('.tmp-tests')
        tmp_dir.mkdir(exist_ok=True)
        db_path = tmp_dir / f'connect-created-{uuid.uuid4()}.db'

        conn = connect_db(str(db_path))
        conn.close()

        self.assertTrue(db_path.exists())

    def test_connect_db_allows_simple_write(self) -> None:
        tmp_dir = Path('.tmp-tests')
        tmp_dir.mkdir(exist_ok=True)
        db_path = tmp_dir / f'connect-write-{uuid.uuid4()}.db'

        conn = connect_db(str(db_path))
        conn.execute("INSERT INTO tags(name, created_at_utc) VALUES (?, datetime('now'))", ("write-test",))
        conn.commit()
        row = conn.execute("SELECT name FROM tags WHERE name = ?", ("write-test",)).fetchone()
        conn.close()

        self.assertEqual(row[0], "write-test")


if __name__ == '__main__':
    unittest.main()
