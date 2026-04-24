import sqlite3
import unittest
import uuid
from pathlib import Path

from app.mediamanager.db.migrations import init_db
from app.mediamanager.db.selection_state import get_selection, replace_selection


class TestSelectionState(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path('.tmp-tests')
        tmp_dir.mkdir(exist_ok=True)
        self.db_path = tmp_dir / f'selection-state-{uuid.uuid4()}.db'
        init_db(str(self.db_path))

    def tearDown(self) -> None:
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_replace_selection_normalizes_and_dedupes(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            replace_selection(
                conn,
                [
                    r"C:\\Media\\Cats",
                    r"c:/media/cats/",
                    r"C:\\Media\\Dogs",
                ],
            )
            self.assertEqual(get_selection(conn), ['c:/media/cats', 'c:/media/dogs'])

    def test_replace_selection_can_clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            replace_selection(conn, [r"C:\\Media\\Cats"])
            self.assertEqual(get_selection(conn), ['c:/media/cats'])
            replace_selection(conn, [])
            self.assertEqual(get_selection(conn), [])


if __name__ == '__main__':
    unittest.main()
