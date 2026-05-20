import sqlite3

from app.mediamanager.db import action_history_repo
from app.mediamanager.db.migrations import _ensure_action_history_tables
from native.mediamanagerx_app.action_edits import snapshot_edit_state
from native.mediamanagerx_app.action_history_dialog import ActionHistoryDialog
from native.mediamanagerx_app.action_history import make_history_item, validate_history_item_availability
from native.mediamanagerx_app.bridge_file_ops import BridgeFileOpsMixin


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_action_history_tables(conn)
    return conn


def test_recompute_keeps_partially_available_group_undoable():
    conn = _conn()
    entry_id = action_history_repo.create_entry(
        conn,
        action_type="move",
        summary="Moved 2 items",
        items=[
            make_history_item(old_path="C:/safe/a.jpg", new_path="C:/safe/dest/a.jpg"),
            make_history_item(old_path="C:/safe/b.jpg", new_path="C:/safe/dest/b.jpg"),
        ],
    )
    items = action_history_repo.list_items(conn, entry_id)
    action_history_repo.update_item_state(
        conn,
        int(items[0]["id"]),
        current_state="unavailable",
        last_change_source="original_action",
        notes="Destination item no longer exists.",
    )

    state = action_history_repo.recompute_entry_undo_state(conn, entry_id)

    assert state == "partially_undone"
    assert int(action_history_repo.latest_undoable_entry(conn)["id"]) == entry_id


def test_delete_all_action_history_clears_entries_and_items():
    conn = _conn()
    action_history_repo.create_entry(
        conn,
        action_type="move",
        summary="Moved file",
        items=[{"old_path": "C:/a.jpg", "new_path": "C:/b.jpg"}],
    )

    deleted = action_history_repo.delete_all(conn)

    assert deleted == 1
    assert action_history_repo.list_entries(conn) == []
    assert action_history_repo.latest_undoable_entry(conn) is None
    assert conn.execute("SELECT COUNT(*) FROM action_history_items").fetchone()[0] == 0


def test_delete_validation_marks_missing_retention_unavailable():
    entry = {"action_type": "delete"}
    item = make_history_item(old_path="C:/safe/deleted.jpg", retention_id="missing-retention-id")

    state, source, note = validate_history_item_availability(
        entry,
        item,
        path_exists_fn=lambda _path: False,
        retained_exists_fn=lambda _retention_id: False,
    )

    assert state == "unavailable"
    assert source is None
    assert "MediaLens retention" in note


def test_copy_validation_marks_missing_copy_as_externally_undone():
    entry = {"action_type": "copy"}
    item = make_history_item(old_path="C:/safe/source.jpg", new_path="C:/safe/copy.jpg")

    state, source, note = validate_history_item_availability(
        entry,
        item,
        path_exists_fn=lambda path: path.endswith("source.jpg"),
    )

    assert state == "undone"
    assert source == "external_change"
    assert "already undone" in note


def test_redo_move_validation_blocks_occupied_destination():
    entry = {"action_type": "move"}
    item = make_history_item(old_path="C:/safe/source.jpg", new_path="C:/safe/dest/source.jpg")
    item["current_state"] = "undone"
    item["last_change_source"] = "group_undo"

    state, source, note = validate_history_item_availability(
        entry,
        item,
        path_exists_fn=lambda _path: True,
    )

    assert state == "unavailable"
    assert source is None
    assert "destination path is already occupied" in note


def test_group_result_summary_reports_skipped_items():
    summary = BridgeFileOpsMixin._history_group_result_summary("Undid action", 8, 10)

    assert summary == "Undid action for 8 of 10 items; 2 items skipped"


def test_action_history_metadata_details_are_plain_english():
    dialog = ActionHistoryDialog.__new__(ActionHistoryDialog)
    item = {
        "old_path": "C:/Pictures/cat.jpg",
        "new_path": "C:/Pictures/cat.jpg",
        "current_state": "applied",
        "metadata_json": (
            '{"old":{"path":"C:/Pictures/cat.jpg","metadata":{"description":""},'
            '"media":{},"tags":[],"ai":{}},'
            '"new":{"path":"C:/Pictures/cat.jpg","metadata":{"description":"sleeping cat"},'
            '"media":{},"tags":[],"ai":{}}}'
        ),
    }
    entry = {"action_type": "metadata", "undo_state": "undoable"}

    detail = dialog._single_item_detail_text(entry, item)

    assert 'cat.jpg: Description changed from blank to "sleeping cat".' in detail
    assert "This change is still current." in detail
    assert "This change can be undone" in detail


def test_action_history_metadata_details_ignore_blank_to_blank_fields():
    dialog = ActionHistoryDialog.__new__(ActionHistoryDialog)
    old = {
        "metadata": {
            "title": None,
            "description": "",
            "notes": None,
            "embedded_tags": None,
            "embedded_comments": None,
        },
        "media": {},
        "tags": [],
        "ai": {},
    }
    new = {
        "metadata": {
            "title": "",
            "description": "new description",
            "notes": "",
            "embedded_tags": "",
            "embedded_comments": "",
        },
        "media": {},
        "tags": [],
        "ai": {},
    }

    phrases = dialog._metadata_change_phrases(old, new)

    assert phrases == ['Description changed from blank to "new description"']


def test_action_history_description_scope_ignores_ai_parameters():
    dialog = ActionHistoryDialog.__new__(ActionHistoryDialog)
    item = {
        "old_path": "C:/Pictures/0010.jpg",
        "new_path": "C:/Pictures/0010.jpg",
        "current_state": "applied",
        "metadata_json": (
            '{"old":{"metadata":{"description":""},"media":{},"tags":[],"ai":{}},'
            '"new":{"metadata":{"description":""},"media":{},"tags":[],'
            '"ai":{},"metadata_extra":"ignored"}}'
        ),
    }
    entry = {"action_type": "metadata", "summary": "Edited description", "undo_state": "undoable"}

    detail = dialog._single_item_detail_text(entry, item)

    assert "Description was edited" in detail
    assert "AI parameters" not in detail


def test_action_history_description_scope_prefers_description_over_ai_parameters():
    dialog = ActionHistoryDialog.__new__(ActionHistoryDialog)
    old = {
        "metadata": {"description": ""},
        "media": {},
        "tags": [],
        "ai": {},
    }
    new = {
        "metadata": {"description": "new description", "ai_params": "Source Formats: generic_embedded"},
        "media": {},
        "tags": [],
        "ai": {},
    }

    phrases = dialog._metadata_change_phrases(old, new, scope="description")

    assert phrases == ['Description changed from blank to "new description"']


def test_action_history_description_scope_uses_visible_description_values():
    dialog = ActionHistoryDialog.__new__(ActionHistoryDialog)
    old = {
        "metadata": {"description": ""},
        "media": {},
        "tags": [],
        "ai": {"description": "old AI fallback"},
        "visible": {"description": "old AI fallback"},
    }
    new = {
        "metadata": {"description": "new user description", "ai_params": "Source Formats: generic_embedded"},
        "media": {},
        "tags": [],
        "ai": {"description": "old AI fallback"},
        "visible": {"description": "new user description"},
    }

    phrases = dialog._metadata_change_phrases(old, new, scope="description")

    assert phrases == ['Description changed from "old AI fallback" to "new user description"']


def test_snapshot_edit_state_records_visible_description(monkeypatch):
    media = {"id": 7, "path": "C:/Pictures/0010.jpg"}
    monkeypatch.setattr("native.mediamanagerx_app.action_edits.get_media_by_path", lambda _conn, _path: media)
    monkeypatch.setattr("native.mediamanagerx_app.action_edits.get_media_metadata", lambda _conn, _media_id: {"description": ""})
    monkeypatch.setattr("native.mediamanagerx_app.action_edits.get_media_ai_metadata", lambda _conn, _media_id: {"description": "AI fallback"})
    monkeypatch.setattr("native.mediamanagerx_app.action_edits.list_media_tags", lambda _conn, _media_id: [])

    snapshot = snapshot_edit_state(object(), "C:/Pictures/0010.jpg")

    assert snapshot["visible"]["description"] == "AI fallback"
