import json
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from app.mediamanager.db.collections_repo import create_collection, add_media_paths_to_collection
from app.mediamanager.db.media_repo import (
    add_media_item,
    add_review_pair_exclusions,
    clear_review_pair_exclusions,
    get_media_by_path,
    is_path_hidden,
    list_media_in_scope,
    list_review_pair_exclusions,
    set_folder_hidden,
    update_media_detected_text,
    update_user_confirmed_text_detected,
)
from app.mediamanager.db.migrations import init_db
from native.mediamanagerx_app.main import Bridge, _load_media_metadata_payload


class _SettingsStub:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self._values = dict(values or {})

    def value(self, _key, default=None, type=None):
        return self._values.get(_key, default)


def _build_test_bridge(conn: sqlite3.Connection, *, settings_values: dict[str, object] | None = None) -> Bridge:
    bridge = Bridge.__new__(Bridge)
    bridge.conn = conn
    bridge.settings = _SettingsStub(settings_values)
    bridge._annotate_group_color_variants = lambda entries: None
    return bridge


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

    def test_user_confirmed_text_detected_overrides_effective_value(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            media_id = add_media_item(conn, r"C:\\Media\\Cats\\a.jpg", "image", text_likely=False)

            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")
            self.assertIs(media["effective_text_detected"], False)

            update_user_confirmed_text_detected(conn, media_id, True)
            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")

            self.assertIs(media["text_likely"], False)
            self.assertIs(media["user_confirmed_text_detected"], True)
            self.assertIs(media["effective_text_detected"], True)

    def test_text_likely_alone_is_not_effective_text_detected(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(conn, r"C:\\Media\\Cats\\a.jpg", "image", text_likely=True)

            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")

            self.assertIs(media["text_likely"], True)
            self.assertIs(media["effective_text_detected"], False)

    def test_stronger_text_detection_signals_keep_effective_value_positive(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            media_id = add_media_item(
                conn,
                r"C:\\Media\\Cats\\a.jpg",
                "image",
                text_likely=False,
                text_more_likely=True,
            )

            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")
            self.assertIs(media["text_likely"], False)
            self.assertIs(media["text_more_likely"], True)
            self.assertIs(media["effective_text_detected"], True)

            update_user_confirmed_text_detected(conn, media_id, False)
            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")
            self.assertIs(media["user_confirmed_text_detected"], False)
            self.assertIs(media["effective_text_detected"], False)

    def test_verified_text_signal_keeps_scoped_effective_value_positive(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(
                conn,
                r"C:\\Media\\Cats\\a.jpg",
                "image",
                text_likely=False,
                text_verified=True,
            )

            scoped = list_media_in_scope(conn, [r"C:\\Media\\Cats"])
            self.assertEqual(len(scoped), 1)
            self.assertIs(scoped[0]["text_likely"], False)
            self.assertIs(scoped[0]["text_verified"], True)
            self.assertIs(scoped[0]["effective_text_detected"], True)

    def test_detected_text_is_persisted_on_media_item(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            media_id = add_media_item(conn, r"C:\\Media\\Cats\\a.jpg", "image")

            update_media_detected_text(conn, media_id, "BigMike sign\nSuite 12")
            media = get_media_by_path(conn, r"C:\\Media\\Cats\\a.jpg")

            self.assertEqual(media["detected_text"], "BigMike sign\nSuite 12")

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

    def test_review_pair_exclusions_are_normalized_and_mode_scoped(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            inserted = add_review_pair_exclusions(
                conn,
                r"C:\\Media\\Alpha\\A.JPG",
                [r"C:\\Media\\Alpha\\B.JPG", r"C:\\Media\\Alpha\\B.JPG"],
                "similar_only",
            )
            self.assertEqual(inserted, 1)
            add_review_pair_exclusions(
                conn,
                r"C:\\Media\\Alpha\\A.JPG",
                [r"C:\\Media\\Alpha\\C.JPG"],
                "duplicates",
            )

            similar_pairs = list_review_pair_exclusions(
                conn,
                "similar",
                paths=[r"C:\\Media\\Alpha\\A.JPG", r"C:\\Media\\Alpha\\B.JPG", r"C:\\Media\\Alpha\\C.JPG"],
            )
            duplicate_pairs = list_review_pair_exclusions(
                conn,
                "duplicates",
                paths=[r"C:\\Media\\Alpha\\A.JPG", r"C:\\Media\\Alpha\\B.JPG", r"C:\\Media\\Alpha\\C.JPG"],
            )

        self.assertEqual(similar_pairs, {("c:/media/alpha/a.jpg", "c:/media/alpha/b.jpg")})
        self.assertEqual(duplicate_pairs, {("c:/media/alpha/a.jpg", "c:/media/alpha/c.jpg")})

    def test_clear_review_pair_exclusions_removes_saved_pairs(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_review_pair_exclusions(
                conn,
                r"C:\\Media\\Alpha\\A.JPG",
                [r"C:\\Media\\Alpha\\B.JPG"],
                "similar",
            )

            removed = clear_review_pair_exclusions(conn)
            remaining = list_review_pair_exclusions(
                conn,
                "similar",
                paths=[r"C:\\Media\\Alpha\\A.JPG", r"C:\\Media\\Alpha\\B.JPG"],
            )

        self.assertEqual(removed, 1)
        self.assertEqual(remaining, set())

    def test_duplicate_grouping_respects_persistent_review_exclusions(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_review_pair_exclusions(
                conn,
                r"C:\\Media\\A.jpg",
                [r"C:\\Media\\B.jpg", r"C:\\Media\\C.jpg"],
                "duplicates",
            )
            bridge = _build_test_bridge(conn)
            entries = [
                {
                    "path": "c:/media/a.jpg",
                    "content_hash": "hash-1",
                    "media_type": "image",
                    "file_size": 100,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 1,
                },
                {
                    "path": "c:/media/b.jpg",
                    "content_hash": "hash-1",
                    "media_type": "image",
                    "file_size": 120,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 2,
                },
                {
                    "path": "c:/media/c.jpg",
                    "content_hash": "hash-1",
                    "media_type": "image",
                    "file_size": 130,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 3,
                },
            ]

            grouped = bridge._build_duplicate_entries(entries, "none")

        self.assertEqual({entry["path"] for entry in grouped}, {"c:/media/b.jpg", "c:/media/c.jpg"})
        self.assertEqual(len({entry["duplicate_group_key"] for entry in grouped}), 1)

    def test_similar_grouping_respects_persistent_review_exclusions(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_review_pair_exclusions(
                conn,
                r"C:\\Media\\A.jpg",
                [r"C:\\Media\\B.jpg", r"C:\\Media\\C.jpg"],
                "similar",
            )
            bridge = _build_test_bridge(conn)
            entries = [
                {
                    "path": "c:/media/a.jpg",
                    "content_hash": "",
                    "phash": "0000000000000000",
                    "media_type": "image",
                    "file_size": 100,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 1,
                },
                {
                    "path": "c:/media/b.jpg",
                    "content_hash": "",
                    "phash": "0000000000000001",
                    "media_type": "image",
                    "file_size": 120,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 2,
                },
                {
                    "path": "c:/media/c.jpg",
                    "content_hash": "",
                    "phash": "0000000000000003",
                    "media_type": "image",
                    "file_size": 130,
                    "width": 100,
                    "height": 100,
                    "file_created_time": 1,
                    "modified_time": 1,
                    "preferred_date": 3,
                },
            ]

            grouped = bridge._build_similar_entries(
                entries,
                "none",
                include_exact=True,
                threshold=2,
                bucket_prefix=15,
            )

        self.assertEqual({entry["path"] for entry in grouped}, {"c:/media/b.jpg", "c:/media/c.jpg"})
        self.assertEqual(len({entry["duplicate_group_key"] for entry in grouped}), 1)

    def test_duplicate_ranking_prefers_configured_folder_order_over_folder_depth(self) -> None:
        bridge = _build_test_bridge(
            sqlite3.connect(":memory:"),
            settings_values={
                "duplicate/rules/preferred_folders_enabled": True,
                "duplicate/rules/preferred_folders_order": json.dumps([
                    "c:/media/client outbox",
                    "All other Folders",
                    "c:/media/tests",
                ]),
                "duplicate/priorities/order": json.dumps([
                    "Preferred Folders",
                    "File Size",
                    "Resolution",
                    "File Format",
                    "Compression",
                    "Color / Grey Preference",
                    "Text / No Text Preference",
                    "Cropped / Full Preference",
                ]),
            },
        )
        entries = [
            {
                "path": "c:/media/tests/nested/deeper/file-a.png",
                "content_hash": "hash-1",
                "media_type": "image",
                "file_size": 500,
                "width": 100,
                "height": 100,
                "preferred_date": 1,
            },
            {
                "path": "c:/media/client outbox/file-b.png",
                "content_hash": "hash-1",
                "media_type": "image",
                "file_size": 400,
                "width": 100,
                "height": 100,
                "preferred_date": 1,
            },
            {
                "path": "c:/media/misc/file-c.png",
                "content_hash": "hash-1",
                "media_type": "image",
                "file_size": 450,
                "width": 100,
                "height": 100,
                "preferred_date": 1,
            },
        ]

        ranked = bridge._rank_duplicate_group(entries)

        self.assertEqual(ranked[0]["path"], "c:/media/client outbox/file-b.png")
        self.assertIn("Preferred Folder", ranked[0]["duplicate_category_reasons"])
        self.assertEqual(ranked[1]["path"], "c:/media/misc/file-c.png")
        self.assertEqual(ranked[2]["path"], "c:/media/tests/nested/deeper/file-a.png")

    def test_compare_entry_uses_live_file_size_over_stale_database_size(self) -> None:
        file_path = self.tmp_dir / "compare-stale-size.jpg"
        file_path.write_bytes(b"same-size-current")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(conn, str(file_path), "image")
            conn.execute(
                "UPDATE media_items SET file_size_bytes = ? WHERE path = ?",
                (999_999, str(file_path).replace("\\", "/").lower()),
            )
            conn.commit()
            bridge = _build_test_bridge(conn)

            entry = bridge._build_compare_entry(str(file_path))

        self.assertEqual(entry["file_size"], file_path.stat().st_size)
        self.assertEqual(entry["file_size_text"], f"{file_path.stat().st_size} B")

    def test_compare_payload_does_not_mark_equal_live_sizes_as_size_winners(self) -> None:
        left_path = self.tmp_dir / "compare-equal-left.jpg"
        right_path = self.tmp_dir / "compare-equal-right.jpg"
        left_path.write_bytes(b"equal-live-size")
        right_path.write_bytes(b"equal-live-size")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=MEMORY;")
            add_media_item(conn, str(left_path), "image")
            add_media_item(conn, str(right_path), "image")
            conn.execute(
                "UPDATE media_items SET file_size_bytes = ? WHERE path = ?",
                (100, str(left_path).replace("\\", "/").lower()),
            )
            conn.execute(
                "UPDATE media_items SET file_size_bytes = ? WHERE path = ?",
                (200, str(right_path).replace("\\", "/").lower()),
            )
            conn.commit()
            bridge = _build_test_bridge(conn)
            bridge._compare_paths = {"left": str(left_path), "right": str(right_path)}
            bridge._compare_keep_paths = set()
            bridge._compare_delete_paths = set()
            bridge._compare_best_path = ""
            bridge._compare_selection_revision = 0

            payload = bridge._build_compare_payload()

        reasons = (
            list(payload["left"].get("duplicate_category_reasons") or [])
            + list(payload["right"].get("duplicate_category_reasons") or [])
        )
        self.assertNotIn("Largest file size", reasons)
        self.assertNotIn("Smallest file size", reasons)


if __name__ == '__main__':
    unittest.main()
