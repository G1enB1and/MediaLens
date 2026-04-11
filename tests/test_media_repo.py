import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from app.mediamanager.db.collections_repo import create_collection, add_media_paths_to_collection
from app.mediamanager.db.media_repo import add_media_item, is_path_hidden, list_media_in_scope, set_folder_hidden
from app.mediamanager.db.migrations import init_db
from native.mediamanagerx_app.main import _load_media_metadata_payload


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
            conn.execute("PRAGMA journal_mode=MEMORY;")
            media_id = add_media_item(conn, r"C:\\Media\\Cats\\A.JPG", 'image')
            self.assertEqual(media_id, 1)
            rows = conn.execute("SELECT path FROM media_items").fetchall()
            self.assertEqual(rows[0][0], 'c:/media/cats/a.jpg')

    def test_list_media_in_scope_filters_correctly(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(conn, r"C:\\Media\\Cats\\a.jpg", 'image')
            add_media_item(conn, r"C:\\Media\\Dogs\\b.jpg", 'image')
            add_media_item(conn, r"C:\\Elsewhere\\c.jpg", 'image')

            scoped = list_media_in_scope(conn, [r"C:\\Media\\Cats", r"C:\\Media\\Dogs"])
            self.assertEqual([r['path'] for r in scoped], ['c:/media/cats/a.jpg', 'c:/media/dogs/b.jpg'])

    def test_list_media_in_scope_supports_limit_offset(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            for i in range(5):
                add_media_item(conn, fr"C:\\Media\\Cats\\{i}.jpg", 'image')

            from app.mediamanager.db.media_repo import list_media_page
            page = list_media_page(conn, [r"C:\\Media\\Cats"], page=1, page_size=2)
            self.assertEqual([r['path'] for r in page], ['c:/media/cats/0.jpg', 'c:/media/cats/1.jpg'])

    def test_move_directory_in_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
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

    def test_list_media_in_scope_includes_ai_search_fields(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(conn, r"C:\\Media\\Cats\\ai.png", 'image')
            conn.execute(
                """
                INSERT INTO media_ai_metadata (
                  media_id, parser_version, normalized_schema_version, is_ai_detected, is_ai_confidence,
                  tool_name_found, tool_name_inferred, tool_name_confidence, ai_prompt, ai_negative_prompt,
                  description, model_name, model_hash, checkpoint_name, sampler, scheduler, cfg_scale,
                  steps, seed, width, height, denoise_strength, upscaler, source_formats_json,
                  metadata_families_json, ai_detection_reasons_json, raw_paths_json, unknown_fields_json, updated_at_utc
                ) VALUES (
                  1, 'p', 's', 1, 1.0,
                  'ChatGPT', '', 1.0, 'red panda portrait', 'blurry',
                  'desc', 'dreamshaper', '', 'dreamshaper', 'Euler', 'Karras', 7.0,
                  30, '1234', 1024, 1024, NULL, NULL, '["c2pa"]',
                  '["c2pa"]', '[]', '[]', '{}', datetime('now')
                )
                """
            )
            conn.execute(
                "INSERT INTO media_ai_loras (media_id, name, created_at_utc) VALUES (1, 'anime-helper', datetime('now'))"
            )
            conn.commit()

            scoped = list_media_in_scope(conn, [r"C:\\Media\\Cats"])

        self.assertEqual(scoped[0]["tool_name_found"], "ChatGPT")
        self.assertEqual(scoped[0]["model_name"], "dreamshaper")
        self.assertEqual(scoped[0]["sampler"], "Euler")
        self.assertEqual(scoped[0]["ai_loras"], "anime-helper")

    def test_list_media_in_scope_includes_collection_names(self) -> None:
        media_dir = self.tmp_dir / "collection-search"
        media_dir.mkdir(exist_ok=True)
        media_path = media_dir / "sunset.jpg"
        media_path.write_bytes(b"jpg")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=MEMORY;")
                add_media_item(conn, str(media_path), "image")
                collection = create_collection(conn, "Vacation Picks")
                add_media_paths_to_collection(conn, collection["id"], [str(media_path)])

                scoped = list_media_in_scope(conn, [str(media_dir)])

            self.assertEqual(scoped[0]["collection_names"], "Vacation Picks")
        finally:
            try:
                if media_path.exists():
                    media_path.unlink()
                if media_dir.exists():
                    media_dir.rmdir()
            except Exception:
                pass

    def test_hidden_folder_marks_descendant_paths_hidden(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            hidden_root = r"C:\\Media\\HiddenSet"
            child_path = r"C:\\Media\\HiddenSet\\nested\\child.jpg"
            set_folder_hidden(conn, hidden_root, True)
            add_media_item(conn, child_path, "image")

            self.assertTrue(is_path_hidden(conn, child_path))

            scoped = list_media_in_scope(conn, [r"C:\\Media"])

        self.assertEqual(len(scoped), 1)
        self.assertTrue(scoped[0]["is_hidden"])

    def test_load_media_metadata_payload_keeps_core_dates_when_optional_metadata_lookup_fails(self) -> None:
        media_dir = self.tmp_dir / "metadata-fallback"
        media_dir.mkdir(exist_ok=True)
        media_path = media_dir / "sample.jpg"
        media_path.write_bytes(b"jpg")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=MEMORY;")
                add_media_item(conn, str(media_path), "image")

                def raise_metadata_failure(_conn: sqlite3.Connection, _media_id: int):
                    raise RuntimeError("metadata table failure")

                with mock.patch(
                    "app.mediamanager.db.metadata_repo.get_media_metadata",
                    side_effect=raise_metadata_failure,
                ):
                    data = _load_media_metadata_payload(conn, str(media_path))

            self.assertEqual(data["media_type"], "image")
            self.assertEqual(data["tags"], [])
            self.assertTrue(data["file_created_time"])
            self.assertTrue(data["modified_time"])
            self.assertTrue(data["original_file_date"])
            self.assertEqual(data["exif_date_taken"], "")
            self.assertEqual(data["metadata_date"], "")
        finally:
            try:
                if media_path.exists():
                    media_path.unlink()
                if media_dir.exists():
                    media_dir.rmdir()
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
