import sqlite3
import unittest
import uuid
from pathlib import Path

from app.mediamanager.db.migrations import init_db
from app.mediamanager.db.repository import MediaRepository


class TestRepository(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path('.tmp-tests')
        tmp_dir.mkdir(exist_ok=True)
        self.db_path = tmp_dir / f'repository-{uuid.uuid4()}.db'
        if self.db_path.exists():
            self.db_path.unlink()
        init_db(str(self.db_path))

    def tearDown(self) -> None:
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except Exception:
            pass

    def test_end_to_end_foundation_flow(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            repo = MediaRepository(conn)
            media_id = repo.ingest_media(r"C:\\Media\\Cats\\a.jpg", 'image')

            repo.set_selection([r"C:\\Media\\Cats"])
            self.assertEqual(repo.current_selection(), ['c:/media/cats'])

            items = repo.scoped_media()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['id'], media_id)

            repo.save_metadata(media_id, title='Cat Pic', notes='favorite')
            metadata = repo.load_metadata(media_id)
            self.assertIsNotNone(metadata)
            assert metadata is not None
            self.assertEqual(metadata['title'], 'Cat Pic')

            repo.add_tags(media_id, ['cat', 'cute'])
            self.assertEqual(repo.get_tags(media_id), ['cat', 'cute'])

    def test_ingest_existing_image_auto_persists_ai_metadata(self) -> None:
        sample = Path("tests/AI_Images/stabile-diffusion-web-ui-glass-fox.png").resolve()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            repo = MediaRepository(conn)
            media_id = repo.ingest_media(str(sample), "image")
            ai_meta = repo.load_ai_metadata(media_id)

        self.assertIsNotNone(ai_meta)
        assert ai_meta is not None
        self.assertTrue(ai_meta["is_ai_detected"])
        self.assertEqual(ai_meta["model_name"], "dreamshaperXL10_alpha2Xl10")
        self.assertEqual(ai_meta["sampler"], "DPM++ 2M SDE Karras")


if __name__ == '__main__':
    unittest.main()
