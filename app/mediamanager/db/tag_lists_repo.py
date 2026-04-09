from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.mediamanager.db.tags_repo import get_or_create_tag


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def list_tag_lists(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, name, sort_mode, created_at_utc, updated_at_utc
        FROM tag_lists
        ORDER BY LOWER(name), id
        """
    ).fetchall()
    return [
        {
            "id": int(row[0]),
            "name": str(row[1] or ""),
            "sort_mode": str(row[2] or "none"),
            "created_at_utc": str(row[3] or ""),
            "updated_at_utc": str(row[4] or ""),
        }
        for row in rows
    ]


def get_tag_list(conn: sqlite3.Connection, tag_list_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, name, sort_mode, created_at_utc, updated_at_utc
        FROM tag_lists
        WHERE id = ?
        """,
        (int(tag_list_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "name": str(row[1] or ""),
        "sort_mode": str(row[2] or "none"),
        "created_at_utc": str(row[3] or ""),
        "updated_at_utc": str(row[4] or ""),
    }


def create_tag_list(conn: sqlite3.Connection, name: str) -> dict | None:
    clean = str(name or "").strip()
    if not clean:
        return None
    now = _utc_now_iso()
    try:
        cur = conn.execute(
            """
            INSERT INTO tag_lists(name, sort_mode, created_at_utc, updated_at_utc)
            VALUES (?, 'none', ?, ?)
            """,
            (clean, now, now),
        )
        conn.commit()
        return get_tag_list(conn, int(cur.lastrowid))
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT id FROM tag_lists WHERE name = ?", (clean,)).fetchone()
        return get_tag_list(conn, int(row[0])) if row else None


def rename_tag_list(conn: sqlite3.Connection, tag_list_id: int, name: str) -> bool:
    clean = str(name or "").strip()
    if not clean:
        return False
    try:
        cur = conn.execute(
            """
            UPDATE tag_lists
            SET name = ?, updated_at_utc = ?
            WHERE id = ?
            """,
            (clean, _utc_now_iso(), int(tag_list_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.IntegrityError:
        return False


def set_tag_list_sort_mode(conn: sqlite3.Connection, tag_list_id: int, sort_mode: str) -> bool:
    mode = str(sort_mode or "none").strip().lower() or "none"
    if mode not in {"none", "az", "za", "most_used", "least_used"}:
        mode = "none"
    cur = conn.execute(
        """
        UPDATE tag_lists
        SET sort_mode = ?, updated_at_utc = ?
        WHERE id = ?
        """,
        (mode, _utc_now_iso(), int(tag_list_id)),
    )
    conn.commit()
    return cur.rowcount > 0


def list_tag_list_entries(conn: sqlite3.Connection, tag_list_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            t.id,
            t.name,
            tli.sort_order,
            COUNT(mt.media_id) AS global_use_count
        FROM tag_list_items tli
        JOIN tags t ON t.id = tli.tag_id
        LEFT JOIN media_tags mt ON mt.tag_id = t.id
        WHERE tli.tag_list_id = ?
        GROUP BY t.id, t.name, tli.sort_order
        ORDER BY tli.sort_order ASC, LOWER(t.name) ASC, t.id ASC
        """,
        (int(tag_list_id),),
    ).fetchall()
    return [
        {
            "tag_id": int(row[0]),
            "name": str(row[1] or ""),
            "sort_order": int(row[2] or 0),
            "global_use_count": int(row[3] or 0),
        }
        for row in rows
    ]


def add_tag_to_list(conn: sqlite3.Connection, tag_list_id: int, tag_name: str) -> dict | None:
    clean = str(tag_name or "").strip()
    if not clean:
        return None
    tag_id = get_or_create_tag(conn, clean)
    next_sort_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM tag_list_items WHERE tag_list_id = ?",
        (int(tag_list_id),),
    ).fetchone()
    sort_order = int((next_sort_order[0] if next_sort_order else 0) or 0)
    conn.execute(
        """
        INSERT INTO tag_list_items(tag_list_id, tag_id, sort_order, created_at_utc)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tag_list_id, tag_id) DO NOTHING
        """,
        (int(tag_list_id), int(tag_id), sort_order, _utc_now_iso()),
    )
    conn.execute(
        "UPDATE tag_lists SET updated_at_utc = ? WHERE id = ?",
        (_utc_now_iso(), int(tag_list_id)),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT t.id, t.name, tli.sort_order
        FROM tag_list_items tli
        JOIN tags t ON t.id = tli.tag_id
        WHERE tli.tag_list_id = ? AND t.id = ?
        """,
        (int(tag_list_id), int(tag_id)),
    ).fetchone()
    if not row:
        return None
    return {"tag_id": int(row[0]), "name": str(row[1] or ""), "sort_order": int(row[2] or 0)}


def remove_tag_from_list(conn: sqlite3.Connection, tag_list_id: int, tag_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM tag_list_items WHERE tag_list_id = ? AND tag_id = ?",
        (int(tag_list_id), int(tag_id)),
    )
    if cur.rowcount <= 0:
        conn.commit()
        return False
    conn.execute(
        "UPDATE tag_lists SET updated_at_utc = ? WHERE id = ?",
        (_utc_now_iso(), int(tag_list_id)),
    )
    conn.commit()
    return True


def reorder_tag_list_entries(conn: sqlite3.Connection, tag_list_id: int, ordered_tag_ids: list[int]) -> bool:
    clean_ids = [int(tag_id) for tag_id in ordered_tag_ids or []]
    if not clean_ids:
        return False
    valid_ids = {
        int(row[0])
        for row in conn.execute(
            "SELECT tag_id FROM tag_list_items WHERE tag_list_id = ?",
            (int(tag_list_id),),
        ).fetchall()
    }
    next_ids = [tag_id for tag_id in clean_ids if tag_id in valid_ids]
    if len(next_ids) != len(valid_ids):
        missing = [tag_id for tag_id in sorted(valid_ids) if tag_id not in next_ids]
        next_ids.extend(missing)
    for index, tag_id in enumerate(next_ids):
        conn.execute(
            """
            UPDATE tag_list_items
            SET sort_order = ?
            WHERE tag_list_id = ? AND tag_id = ?
            """,
            (int(index), int(tag_list_id), int(tag_id)),
        )
    conn.execute(
        "UPDATE tag_lists SET updated_at_utc = ? WHERE id = ?",
        (_utc_now_iso(), int(tag_list_id)),
    )
    conn.commit()
    return True
