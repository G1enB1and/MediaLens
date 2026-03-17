from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.mediamanager.db.media_repo import add_media_item, get_media_by_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def list_collections(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
          c.id,
          c.name,
          c.is_hidden,
          c.created_at_utc,
          c.updated_at_utc,
          COUNT(ci.media_id) AS item_count
        FROM collections c
        LEFT JOIN collection_items ci ON ci.collection_id = c.id
        GROUP BY c.id, c.name, c.is_hidden, c.created_at_utc, c.updated_at_utc
        ORDER BY LOWER(c.name), c.id
        """
    ).fetchall()
    return [
        {
            "id": int(row[0]),
            "name": row[1],
            "is_hidden": bool(row[2]),
            "created_at_utc": row[3],
            "updated_at_utc": row[4],
            "item_count": int(row[5] or 0),
        }
        for row in rows
    ]


def get_collection(conn: sqlite3.Connection, collection_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, name, is_hidden, created_at_utc, updated_at_utc
        FROM collections
        WHERE id = ?
        """,
        (int(collection_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "name": row[1],
        "is_hidden": bool(row[2]),
        "created_at_utc": row[3],
        "updated_at_utc": row[4],
    }


def create_collection(conn: sqlite3.Connection, name: str) -> dict:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise ValueError("Collection name is required")
    now = _utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO collections(name, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?)
        """,
        (cleaned, now, now),
    )
    conn.commit()
    created = get_collection(conn, int(cur.lastrowid))
    if not created:
        raise RuntimeError("failed to create collection")
    return created


def rename_collection(conn: sqlite3.Connection, collection_id: int, name: str) -> bool:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise ValueError("Collection name is required")
    cur = conn.execute(
        """
        UPDATE collections
        SET name = ?, updated_at_utc = ?
        WHERE id = ?
        """,
        (cleaned, _utc_now_iso(), int(collection_id)),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> bool:
    cur = conn.execute("DELETE FROM collections WHERE id = ?", (int(collection_id),))
    conn.commit()
    return cur.rowcount > 0


def remove_media_from_collection(conn: sqlite3.Connection, collection_id: int, media_ids: Iterable[int]) -> int:
    unique_ids = sorted({int(media_id) for media_id in media_ids})
    if not unique_ids:
        return 0
    cur = conn.executemany(
        "DELETE FROM collection_items WHERE collection_id = ? AND media_id = ?",
        [(int(collection_id), media_id) for media_id in unique_ids],
    )
    conn.commit()
    return cur.rowcount if cur.rowcount != -1 else 0


def add_media_paths_to_collection(conn: sqlite3.Connection, collection_id: int, paths: Iterable[str]) -> int:
    collection = get_collection(conn, collection_id)
    if not collection:
        return 0

    media_ids: list[int] = []
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

    for raw_path in paths:
        path = str(raw_path or "").strip()
        if not path:
            continue
        media = get_media_by_path(conn, path)
        if not media:
            p = Path(path)
            if not p.exists():
                continue
            media_type = "image" if p.suffix.lower() in image_exts else "video"
            media_id = add_media_item(conn, path, media_type)
        else:
            media_id = int(media["id"])
        media_ids.append(media_id)

    unique_ids = sorted(set(media_ids))
    if not unique_ids:
        return 0

    now = _utc_now_iso()
    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO collection_items(collection_id, media_id, created_at_utc)
        VALUES (?, ?, ?)
        """,
        [(int(collection_id), media_id, now) for media_id in unique_ids],
    )
    conn.execute(
        "UPDATE collections SET updated_at_utc = ? WHERE id = ?",
        (now, int(collection_id)),
    )
    conn.commit()
    return max(0, conn.total_changes - before - 1)


def set_collection_hidden(conn: sqlite3.Connection, collection_id: int, hidden: bool) -> bool:
    now = _utc_now_iso()
    cur = conn.execute(
        "UPDATE collections SET is_hidden = ?, updated_at_utc = ? WHERE id = ?",
        (1 if hidden else 0, now, int(collection_id))
    )
    conn.commit()
    return cur.rowcount > 0
