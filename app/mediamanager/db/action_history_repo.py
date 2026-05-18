from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


UNDOABLE_ACTIONS = {"delete", "move", "copy", "rename", "create_folder", "metadata", "hidden", "rotate"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False)
    except Exception:
        return "{}"


ENTRY_COLUMNS = (
    "id",
    "transaction_id",
    "timestamp_utc",
    "action_type",
    "origin",
    "summary",
    "item_count",
    "status",
    "undo_state",
    "metadata_json",
    "first_old_path",
    "first_new_path",
)

ITEM_COLUMNS = (
    "id",
    "entry_id",
    "item_type",
    "old_path",
    "new_path",
    "retention_id",
    "result",
    "current_state",
    "last_change_source",
    "notes",
    "metadata_json",
)


def _row_to_dict(row, columns: tuple[str, ...]) -> dict:
    if hasattr(row, "keys"):
        return dict(row)
    return {key: row[index] for index, key in enumerate(columns)}


def create_entry(
    conn: sqlite3.Connection,
    *,
    action_type: str,
    summary: str,
    items: list[dict],
    origin: str = "user",
    status: str = "success",
    undo_state: str | None = None,
    transaction_id: str | None = None,
    metadata: dict | None = None,
) -> int:
    action_type = str(action_type or "").strip()
    if undo_state is None:
        undo_state = "undoable" if origin == "user" and action_type in UNDOABLE_ACTIONS and status != "failed" else "not_undoable"
    tx_id = transaction_id or str(uuid.uuid4())
    cursor = conn.execute(
        """
        INSERT INTO action_history_entries(
            transaction_id, timestamp_utc, action_type, origin, summary,
            item_count, status, undo_state, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tx_id,
            utc_now_iso(),
            action_type,
            str(origin or "user"),
            str(summary or action_type.title()),
            int(len(items or [])),
            str(status or "success"),
            str(undo_state or "not_undoable"),
            _json_dumps(metadata),
        ),
    )
    entry_id = int(cursor.lastrowid)
    item_rows = []
    for item in items or []:
        item_rows.append(
            (
                entry_id,
                str(item.get("item_type") or "file"),
                item.get("old_path"),
                item.get("new_path"),
                item.get("retention_id"),
                str(item.get("result") or "success"),
                str(item.get("current_state") or ("applied" if item.get("result", "success") == "success" else "failed")),
                str(item.get("last_change_source") or "original_action"),
                item.get("notes"),
                _json_dumps(item.get("metadata")),
            )
        )
    if item_rows:
        conn.executemany(
            """
            INSERT INTO action_history_items(
                entry_id, item_type, old_path, new_path, retention_id, result,
                current_state, last_change_source, notes, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            item_rows,
        )
    conn.commit()
    return entry_id


def list_entries(conn: sqlite3.Connection, *, limit: int = 200, action_type: str = "", search: str = "") -> list[dict]:
    where = []
    params: list[Any] = []
    if action_type and action_type != "all":
        where.append("action_type = ?")
        params.append(action_type)
    if search:
        like = f"%{search}%"
        where.append(
            """
            (
                summary LIKE ?
                OR EXISTS (
                    SELECT 1 FROM action_history_items i
                    WHERE i.entry_id = action_history_entries.id
                      AND (i.old_path LIKE ? OR i.new_path LIKE ? OR i.notes LIKE ?)
                )
            )
            """
        )
        params.extend([like, like, like, like])
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"""
        SELECT id, transaction_id, timestamp_utc, action_type, origin, summary,
               item_count, status, undo_state, metadata_json,
               (
                   SELECT old_path
                   FROM action_history_items i
                   WHERE i.entry_id = action_history_entries.id
                   ORDER BY i.id
                   LIMIT 1
               ) AS first_old_path,
               (
                   SELECT new_path
                   FROM action_history_items i
                   WHERE i.entry_id = action_history_entries.id
                   ORDER BY i.id
                   LIMIT 1
               ) AS first_new_path
        FROM action_history_entries
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """,
        [*params, max(1, int(limit or 200))],
    ).fetchall()
    return [_row_to_dict(row, ENTRY_COLUMNS) for row in rows]


def get_entry(conn: sqlite3.Connection, entry_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, transaction_id, timestamp_utc, action_type, origin, summary,
               item_count, status, undo_state, metadata_json,
               NULL AS first_old_path,
               NULL AS first_new_path
        FROM action_history_entries
        WHERE id = ?
        """,
        (int(entry_id),),
    ).fetchone()
    return _row_to_dict(row, ENTRY_COLUMNS) if row else None


def list_items(conn: sqlite3.Connection, entry_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, entry_id, item_type, old_path, new_path, retention_id, result,
               current_state, last_change_source, notes, metadata_json
        FROM action_history_items
        WHERE entry_id = ?
        ORDER BY id
        """,
        (int(entry_id),),
    ).fetchall()
    return [_row_to_dict(row, ITEM_COLUMNS) for row in rows]


def get_item_with_entry(conn: sqlite3.Connection, item_id: int) -> tuple[dict, dict] | None:
    item_row = conn.execute(
        """
        SELECT id, entry_id, item_type, old_path, new_path, retention_id, result,
               current_state, last_change_source, notes, metadata_json
        FROM action_history_items
        WHERE id = ?
        """,
        (int(item_id),),
    ).fetchone()
    if not item_row:
        return None
    item = _row_to_dict(item_row, ITEM_COLUMNS)
    entry = get_entry(conn, int(item["entry_id"]))
    if not entry:
        return None
    return item, entry


def latest_undoable_entry(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT id, transaction_id, timestamp_utc, action_type, origin, summary,
               item_count, status, undo_state, metadata_json,
               NULL AS first_old_path,
               NULL AS first_new_path
        FROM action_history_entries
        WHERE origin = 'user' AND undo_state IN ('undoable', 'partially_undone')
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return _row_to_dict(row, ENTRY_COLUMNS) if row else None


def latest_redoable_entry(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT id, transaction_id, timestamp_utc, action_type, origin, summary,
               item_count, status, undo_state, metadata_json,
               NULL AS first_old_path,
               NULL AS first_new_path
        FROM action_history_entries
        WHERE origin = 'user' AND undo_state = 'redoable'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return _row_to_dict(row, ENTRY_COLUMNS) if row else None


def clear_redo_stack(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE action_history_entries
        SET undo_state = 'not_undoable'
        WHERE origin = 'user' AND undo_state = 'redoable'
        """
    )
    conn.commit()


def update_entry_state(conn: sqlite3.Connection, entry_id: int, undo_state: str, status: str | None = None) -> None:
    if status is None:
        conn.execute(
            "UPDATE action_history_entries SET undo_state = ? WHERE id = ?",
            (str(undo_state), int(entry_id)),
        )
    else:
        conn.execute(
            "UPDATE action_history_entries SET undo_state = ?, status = ? WHERE id = ?",
            (str(undo_state), str(status), int(entry_id)),
        )
    conn.commit()


def update_item_state(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    current_state: str,
    last_change_source: str,
    retention_id: str | None = None,
    notes: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE action_history_items
        SET current_state = ?,
            last_change_source = ?,
            retention_id = COALESCE(?, retention_id),
            notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (str(current_state), str(last_change_source), retention_id, notes, int(item_id)),
    )
    conn.commit()


def recompute_entry_undo_state(conn: sqlite3.Connection, entry_id: int) -> str:
    rows = list_items(conn, entry_id)
    successful = [row for row in rows if str(row.get("result") or "") == "success"]
    if not successful:
        state = "not_undoable"
    else:
        applied = [row for row in successful if str(row.get("current_state") or "") == "applied"]
        undone = [row for row in successful if str(row.get("current_state") or "") == "undone"]
        group_undone = [
            row
            for row in undone
            if str(row.get("last_change_source") or "") == "group_undo"
        ]
        if len(group_undone) == len(successful):
            state = "redoable"
        elif group_undone and not applied:
            state = "redoable"
        elif applied and undone:
            state = "partially_undone"
        elif applied:
            state = "undoable"
        else:
            state = "not_undoable"
    update_entry_state(conn, entry_id, state)
    return state
