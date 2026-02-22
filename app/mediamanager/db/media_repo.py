from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Iterable

from app.mediamanager.db.pagination import page_to_limit_offset
from app.mediamanager.db.scope_query import build_scope_where
from app.mediamanager.utils.pathing import normalize_windows_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def add_media_item(
    conn: sqlite3.Connection,
    path: str,
    media_type: str,
    content_hash: Optional[str] = None,
) -> int:
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)
    
    # Simple stat collection for discovery
    p_obj = Path(path)
    size = p_obj.stat().st_size if p_obj.exists() else 0
    mtime = datetime.fromtimestamp(p_obj.stat().st_mtime, tz=timezone.utc).isoformat() if p_obj.exists() else now

    conn.execute(
        """
        INSERT INTO media_items(path, content_hash, media_type, file_size_bytes, modified_time_utc, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          content_hash=COALESCE(excluded.content_hash, content_hash),
          media_type=excluded.media_type,
          file_size_bytes=excluded.file_size_bytes,
          modified_time_utc=excluded.modified_time_utc,
          updated_at_utc=excluded.updated_at_utc
        """,
        (normalized, content_hash, media_type, size, mtime, now, now),
    )
    row = conn.execute("SELECT id FROM media_items WHERE path = ?", (normalized,)).fetchone()
    if not row:
        raise RuntimeError("failed to insert media item")
    conn.commit()
    return int(row[0])


def get_media_by_path(conn: sqlite3.Connection, path: str) -> Optional[dict]:
    normalized = normalize_windows_path(path)
    row = conn.execute(
        "SELECT id, path, media_type, file_size_bytes, modified_time_utc FROM media_items WHERE path = ?",
        (normalized,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "path": row[1],
        "media_type": row[2],
        "file_size": row[3],
        "modified_time": row[4],
    }


def rename_media_path(conn: sqlite3.Connection, old_path: str, new_path: str) -> bool:
    """Update the stored path for a media item after an on-disk rename.

    Returns True if a row was updated, False if the old path was not found.
    """
    old_norm = normalize_windows_path(old_path)
    new_norm = normalize_windows_path(new_path)
    now = _utc_now_iso()
    cur = conn.execute(
        "UPDATE media_items SET path = ?, updated_at_utc = ? WHERE path = ?",
        (new_norm, now, old_norm),
    )
    conn.commit()
    return cur.rowcount > 0



def get_media_by_hash(conn: sqlite3.Connection, content_hash: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT id, path, media_type FROM media_items WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "path": row[1], "media_type": row[2]}


def upsert_media_item(
    conn: sqlite3.Connection,
    path: str,
    media_type: str,
    content_hash: str,
) -> int:
    """Upsert media item, handling renames/moves via content hash."""
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)

    # 1. Check if we already have this exact path
    existing_by_path = conn.execute(
        "SELECT id, content_hash FROM media_items WHERE path = ?", (normalized,)
    ).fetchone()

    if existing_by_path:
        # Path exists. Update hash if it changed (unlikely but possible)
        conn.execute(
            "UPDATE media_items SET content_hash = ?, updated_at_utc = ? WHERE id = ?",
            (content_hash, now, existing_by_path[0]),
        )
        conn.commit()
        return int(existing_by_path[0])

    # 2. Path doesn't exist. Check if the hash exists (indicates a move/rename or a copy)
    # To accurately detect a move, we should see if the 'old' path still exists on disk.
    # If the old path still exists, this is a distinct copy (duplicate content).
    # If the old path is gone, it's almost certainly a move.
    existing_by_hash = get_media_by_hash(conn, content_hash)
    if existing_by_hash:
        old_path = existing_by_hash["path"]
        media_id = existing_by_hash["id"]

        if not Path(old_path).exists():
            # Old path is gone -> Move detected
            # Record history
            conn.execute(
                "INSERT INTO media_paths_history(media_id, old_path, new_path, moved_at_utc) VALUES (?, ?, ?, ?)",
                (media_id, old_path, normalized, now),
            )

            # Update path
            conn.execute(
                "UPDATE media_items SET path = ?, updated_at_utc = ? WHERE id = ?",
                (normalized, now, media_id),
            )
            conn.commit()
            return int(media_id)
        else:
            # Old path still exists -> Duplicate content at new path
            # We treat this as a new media item (different file, same content)
            pass

    # 3. Brand new item (or duplicate content at new path)
    return add_media_item(conn, normalized, media_type, content_hash)


def list_media_in_scope(
    conn: sqlite3.Connection,
    selected_roots: list[str],
    *,
    limit: int | None = None,
    offset: int | None = None,
) -> List[dict]:
    where_sql, params = build_scope_where(selected_roots)

    sql = f"SELECT id, path, media_type, file_size_bytes, modified_time_utc FROM media_items WHERE {where_sql} ORDER BY path"
    if limit is not None:
        sql += " LIMIT ?"
        params = [*params, int(limit)]
    if offset is not None:
        if limit is None:
            sql += " LIMIT -1"
        sql += " OFFSET ?"
        params = [*params, int(offset)]

    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": r[0],
            "path": r[1],
            "media_type": r[2],
            "file_size": r[3],
            "modified_time": r[4],
        }
        for r in rows
    ]


def list_media_page(
    conn: sqlite3.Connection,
    selected_roots: list[str],
    *,
    page: int,
    page_size: int = 100,
) -> List[dict]:
    """Convenience wrapper for page-based access (1-based page index)."""
    limit, offset = page_to_limit_offset(page=page, page_size=page_size)
    return list_media_in_scope(conn, selected_roots, limit=limit, offset=offset)
