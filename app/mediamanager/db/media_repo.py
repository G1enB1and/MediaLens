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
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> int:
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)
    
    # Simple stat collection for discovery
    p_obj = Path(path)
    size = p_obj.stat().st_size if p_obj.exists() else 0
    mtime = datetime.fromtimestamp(p_obj.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat() if p_obj.exists() else now

    conn.execute(
        """
        INSERT INTO media_items(path, content_hash, media_type, file_size_bytes, modified_time_utc, width, height, duration_ms, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          content_hash=COALESCE(excluded.content_hash, content_hash),
          media_type=excluded.media_type,
          file_size_bytes=excluded.file_size_bytes,
          modified_time_utc=excluded.modified_time_utc,
          width=COALESCE(excluded.width, width),
          height=COALESCE(excluded.height, height),
          duration_ms=COALESCE(excluded.duration_ms, duration_ms),
          updated_at_utc=excluded.updated_at_utc
        """,
        (normalized, content_hash, media_type, size, mtime, width, height, duration_ms, now, now),
    )
    row = conn.execute("SELECT id FROM media_items WHERE path = ?", (normalized,)).fetchone()
    if not row:
        raise RuntimeError("failed to insert media item")
    conn.commit()
    return int(row[0])


def get_media_by_path(conn: sqlite3.Connection, path: str) -> Optional[dict]:
    normalized = normalize_windows_path(path)
    row = conn.execute(
        "SELECT id, path, media_type, file_size_bytes, modified_time_utc, width, height, duration_ms FROM media_items WHERE path = ?",
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
        "width": row[5],
        "height": row[6],
        "duration_ms": row[7],
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
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> int:
    """Upsert media item, handling renames/moves via content hash."""
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)

    # Collect current stats to keep DB in sync
    p_obj = Path(path)
    size = p_obj.stat().st_size if p_obj.exists() else 0
    mtime = datetime.fromtimestamp(p_obj.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat() if p_obj.exists() else now

    # 1. Check if we already have this exact path
    existing_by_path = conn.execute(
        "SELECT id, content_hash FROM media_items WHERE path = ?", (normalized,)
    ).fetchone()

    if existing_by_path:
        # Path exists. Update hash AND stats
        conn.execute(
            """
            UPDATE media_items 
            SET content_hash = ?, file_size_bytes = ?, modified_time_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
            WHERE id = ?
            """,
            (content_hash, size, mtime, width, height, duration_ms, now, existing_by_path[0]),
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

            # Update path AND stats
            conn.execute(
                """
                UPDATE media_items 
                SET path = ?, file_size_bytes = ?, modified_time_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
                WHERE id = ?
                """,
                (normalized, size, mtime, width, height, duration_ms, now, media_id),
            )
            conn.commit()
            return int(media_id)
        else:
            # Old path still exists -> Duplicate content at new path
            # We treat this as a new media item (different file, same content)
            pass

    # 3. Brand new item (or duplicate content at new path)
    return add_media_item(conn, normalized, media_type, content_hash, width=width, height=height, duration_ms=duration_ms)


def list_media_in_scope(
    conn: sqlite3.Connection,
    selected_roots: list[str],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict]:
    where_sql, params = build_scope_where(selected_roots)
    return _list_media_with_where(conn, where_sql, params, limit=limit, offset=offset)


def list_media_in_collection(
    conn: sqlite3.Connection,
    collection_id: int,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict]:
    where_sql = """
        m.id IN (
          SELECT ci.media_id
          FROM collection_items ci
          WHERE ci.collection_id = ?
        )
    """
    return _list_media_with_where(conn, where_sql, [int(collection_id)], limit=limit, offset=offset)


def _list_media_with_where(
    conn: sqlite3.Connection,
    where_sql: str,
    params: list,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict]:
    if limit is not None:
        limit_sql = f" LIMIT {limit} OFFSET {offset or 0}"
    else:
        limit_sql = ""

    sql = f"""
        SELECT 
            m.id, 
            m.path, 
            m.media_type, 
            m.file_size_bytes, 
            m.modified_time_utc,
            m.width,
            m.height,
            m.duration_ms,
            meta.title,
            meta.description,
            meta.notes,
            ai.ai_prompt,
            ai.ai_negative_prompt,
            ai.tool_name_found,
            ai.tool_name_inferred,
            ai.model_name,
            ai.checkpoint_name,
            ai.sampler,
            ai.scheduler,
            ai.cfg_scale,
            ai.steps,
            ai.seed,
            ai.source_formats_json,
            ai.metadata_families_json,
            (
                SELECT GROUP_CONCAT(l.name, ', ')
                FROM media_ai_loras l
                WHERE l.media_id = m.id
            ) as ai_loras,
            (
                SELECT GROUP_CONCAT(t.name, ', ')
                FROM tags t
                JOIN media_tags mt ON t.id = mt.tag_id
                WHERE mt.media_id = m.id
            ) as tags
        FROM media_items m
        LEFT JOIN media_metadata meta ON m.id = meta.media_id
        LEFT JOIN media_ai_metadata ai ON m.id = ai.media_id
        WHERE {where_sql}
        ORDER BY m.path
        {limit_sql}
    """

    rows = conn.execute(sql, params).fetchall()
    return [_media_row_to_dict(r) for r in rows]


def _media_row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "path": row[1],
        "media_type": row[2],
        "file_size": row[3],
        "modified_time": row[4],
        "width": row[5],
        "height": row[6],
        "duration": (row[7] / 1000.0) if row[7] else None,
        "title": row[8],
        "description": row[9],
        "notes": row[10],
        "ai_prompt": row[11],
        "ai_negative_prompt": row[12],
        "tool_name_found": row[13],
        "tool_name_inferred": row[14],
        "model_name": row[15],
        "checkpoint_name": row[16],
        "sampler": row[17],
        "scheduler": row[18],
        "cfg_scale": row[19],
        "steps": row[20],
        "seed": row[21],
        "source_formats": row[22],
        "metadata_families": row[23],
        "ai_loras": row[24],
        "tags": row[25],
    }


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


def move_directory_in_db(conn: sqlite3.Connection, old_path: str, new_path: str) -> bool:
    """Update all stored paths for a directory and its children after an on-disk move.
    
    Returns True if any rows were updated.
    """
    old_norm = normalize_windows_path(old_path)
    new_norm = normalize_windows_path(new_path)
    now = _utc_now_iso()
    
    # Update items within the directory
    # SQL: replace(path, old_prefix, new_prefix)
    # We use lower() to ensure case-insensitive match since we normalized to lowercase.
    # Note: SQLite replace is case-sensitive, but our paths are already casefolded.
    
    old_prefix = old_norm if old_norm.endswith('/') else old_norm + '/'
    new_prefix = new_norm if new_norm.endswith('/') else new_norm + '/'
    
    # 1. Update the directory itself
    cur = conn.execute(
        "UPDATE media_items SET path = ?, updated_at_utc = ? WHERE path = ?",
        (new_norm, now, old_norm)
    )
    
    # 2. Update all children
    # We use the length of the old_prefix to perform the replacement correctly.
    conn.execute(
        """
        UPDATE media_items 
        SET path = ? || substr(path, ?), updated_at_utc = ?
        WHERE path LIKE ? || '/%'
        """,
        (new_norm, len(old_norm) + 1, now, old_norm)
    )
    
    conn.commit()
    return cur.rowcount > 0
