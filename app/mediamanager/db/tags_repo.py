from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable, List


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_or_create_tag(conn: sqlite3.Connection, name: str, category: str | None = None) -> int:
    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO tags(name, category, created_at_utc)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO NOTHING
        """,
        (name, category, now),
    )
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
    if not row:
        raise RuntimeError(f"failed to create or load tag: {name}")
    conn.commit()
    return int(row[0])


def attach_tags(conn: sqlite3.Connection, media_id: int, tag_names: Iterable[str]) -> None:
    now = _utc_now_iso()
    for tag_name in sorted({t.strip() for t in tag_names if t.strip()}):
        tag_id = get_or_create_tag(conn, tag_name)
        conn.execute(
            """
            INSERT INTO media_tags(media_id, tag_id, created_at_utc)
            VALUES (?, ?, ?)
            ON CONFLICT(media_id, tag_id) DO NOTHING
            """,
            (media_id, tag_id, now),
        )
    conn.commit()


def list_media_tags(conn: sqlite3.Connection, media_id: int) -> List[str]:
    rows = conn.execute(
        """
        SELECT t.name
        FROM media_tags mt
        JOIN tags t ON t.id = mt.tag_id
        WHERE mt.media_id = ?
        ORDER BY t.name
        """,
        (media_id,),
    ).fetchall()
    return [r[0] for r in rows]


def set_media_tags(conn: sqlite3.Connection, media_id: int, tag_names: Iterable[str]) -> None:
    """Clear existing tags and set the new ones."""
    conn.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))
    attach_tags(conn, media_id, tag_names)
    conn.commit()
