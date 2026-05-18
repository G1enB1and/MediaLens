import sqlite3

from app.mediamanager.db import action_history_repo
from app.mediamanager.db.migrations import _ensure_action_history_tables
from native.mediamanagerx_app.action_history import make_history_item, validate_history_item_availability


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
