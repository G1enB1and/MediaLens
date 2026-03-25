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


def _file_time_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def _collect_file_stats(path: str) -> tuple[int, str, str]:
    p_obj = Path(path)
    if not p_obj.exists():
        now = _utc_now_iso()
        return 0, now, now
    stat = p_obj.stat()
    size = stat.st_size
    modified = _file_time_iso(stat.st_mtime)
    # On Windows, st_ctime is creation time. This app is Windows-first today.
    created = _file_time_iso(stat.st_ctime)
    return size, created, modified


def _ensure_phash_column(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_items)").fetchall()}
    if "phash" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN phash TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_phash ON media_items(phash)")
    conn.commit()


def add_media_item(
    conn: sqlite3.Connection,
    path: str,
    media_type: str,
    content_hash: Optional[str] = None,
    phash: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
    is_hidden: int = 0,
) -> int:
    _ensure_phash_column(conn)
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)
    
    # Simple stat collection for discovery
    size, created_time, mtime = _collect_file_stats(path)

    conn.execute(
        """
        INSERT INTO media_items(path, content_hash, phash, media_type, file_size_bytes, file_created_time_utc, modified_time_utc, width, height, duration_ms, is_hidden, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          content_hash=COALESCE(excluded.content_hash, content_hash),
          phash=COALESCE(excluded.phash, phash),
          media_type=excluded.media_type,
          file_size_bytes=excluded.file_size_bytes,
          file_created_time_utc=COALESCE(excluded.file_created_time_utc, file_created_time_utc),
          modified_time_utc=excluded.modified_time_utc,
          width=COALESCE(excluded.width, width),
          height=COALESCE(excluded.height, height),
          duration_ms=COALESCE(excluded.duration_ms, duration_ms),
          is_hidden=COALESCE(excluded.is_hidden, is_hidden),
          updated_at_utc=excluded.updated_at_utc
        """,
        (normalized, content_hash, phash, media_type, size, created_time, mtime, width, height, duration_ms, is_hidden, now, now),
    )
    row = conn.execute("SELECT id FROM media_items WHERE path = ?", (normalized,)).fetchone()
    if not row:
        raise RuntimeError("failed to insert media item")
    conn.commit()
    return int(row[0])


def get_media_by_path(conn: sqlite3.Connection, path: str) -> Optional[dict]:
    _ensure_phash_column(conn)
    normalized = normalize_windows_path(path)
    row = conn.execute(
        "SELECT id, path, media_type, file_size_bytes, file_created_time_utc, modified_time_utc, exif_date_taken, metadata_date, width, height, duration_ms, is_hidden, phash FROM media_items WHERE path = ?",
        (normalized,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "path": row[1],
        "media_type": row[2],
        "file_size": row[3],
        "file_created_time": row[4],
        "modified_time": row[5],
        "exif_date_taken": row[6],
        "metadata_date": row[7],
        "width": row[8],
        "height": row[9],
        "duration_ms": row[10],
        "is_hidden": bool(row[11]),
        "phash": row[12],
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
    phash: str | None = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> int:
    """Upsert media item, handling renames/moves via content hash."""
    _ensure_phash_column(conn)
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)

    # Collect current stats to keep DB in sync
    size, created_time, mtime = _collect_file_stats(path)

    # 1. Check if we already have this exact path
    existing_by_path = conn.execute(
        "SELECT id, content_hash FROM media_items WHERE path = ?", (normalized,)
    ).fetchone()

    if existing_by_path:
        # Path exists. Update hash AND stats
        conn.execute(
            """
                UPDATE media_items 
            SET content_hash = ?, phash = COALESCE(?, phash), file_size_bytes = ?, file_created_time_utc = ?, modified_time_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
            WHERE id = ?
            """,
            (content_hash, phash, size, created_time, mtime, width, height, duration_ms, now, existing_by_path[0]),
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
                SET path = ?, phash = COALESCE(?, phash), file_size_bytes = ?, file_created_time_utc = ?, modified_time_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
                WHERE id = ?
                """,
                (normalized, phash, size, created_time, mtime, width, height, duration_ms, now, media_id),
            )
            conn.commit()
            return int(media_id)
        else:
            # Old path still exists -> Duplicate content at new path
            # We treat this as a new media item (different file, same content)
            pass

    # 3. Brand new item (or duplicate content at new path)
    return add_media_item(conn, normalized, media_type, content_hash, phash=phash, width=width, height=height, duration_ms=duration_ms)


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
    _ensure_phash_column(conn)
    if limit is not None:
        limit_sql = f" LIMIT {limit} OFFSET {offset or 0}"
    else:
        limit_sql = ""

    sql = f"""
        SELECT 
            m.id, 
            m.path, 
            m.content_hash,
            m.phash,
            m.media_type, 
            m.file_size_bytes, 
            m.file_created_time_utc,
            m.modified_time_utc,
            m.exif_date_taken,
            m.metadata_date,
            m.width,
            m.height,
            m.duration_ms,
            m.is_hidden,
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
            ) as tags,
            (
                SELECT GROUP_CONCAT(c.name, ', ')
                FROM collections c
                JOIN collection_items ci ON c.id = ci.collection_id
                WHERE ci.media_id = m.id
            ) as collection_names
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
        "content_hash": row[2],
        "phash": row[3],
        "media_type": row[4],
        "file_size": row[5],
        "file_created_time": row[6],
        "modified_time": row[7],
        "exif_date_taken": row[8],
        "metadata_date": row[9],
        "width": row[10],
        "height": row[11],
        "duration": (row[12] / 1000.0) if row[12] else None,
        "is_hidden": bool(row[13]),
        "title": row[14],
        "description": row[15],
        "notes": row[16],
        "ai_prompt": row[17],
        "ai_negative_prompt": row[18],
        "tool_name_found": row[19],
        "tool_name_inferred": row[20],
        "model_name": row[21],
        "checkpoint_name": row[22],
        "sampler": row[23],
        "scheduler": row[24],
        "cfg_scale": row[25],
        "steps": row[26],
        "seed": row[27],
        "source_formats": row[28],
        "metadata_families": row[29],
        "ai_loras": row[30],
        "tags": row[31],
        "collection_names": row[32],
    }


def update_media_dates(
    conn: sqlite3.Connection,
    media_id: int,
    *,
    exif_date_taken: str | None = None,
    metadata_date: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE media_items
        SET exif_date_taken = ?, metadata_date = ?, updated_at_utc = ?
        WHERE id = ?
        """,
        (exif_date_taken, metadata_date, _utc_now_iso(), int(media_id)),
    )
    conn.commit()


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


def set_media_hidden(conn: sqlite3.Connection, path: str, hidden: bool) -> bool:
    """Update the is_hidden status for a specific media item in the database.
    If the item is not in the database, it will be added.
    """
    normalized = normalize_windows_path(path)
    cursor = conn.cursor()
    val = 1 if hidden else 0
    
    # Try updating existing
    cursor.execute("UPDATE media_items SET is_hidden = ?, updated_at_utc = ? WHERE path = ?", (val, _utc_now_iso(), normalized))
    if cursor.rowcount > 0:
        conn.commit()
        return True
    
    # If not found and we want to hide it, insert it
    if hidden:
        # Infer media type
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}
        p = Path(path)
        mtype = "image" if p.suffix.lower() in image_exts else "video"
        try:
            add_media_item(conn, path, mtype, is_hidden=1)
            return True
        except Exception:
            return False
            
    return False


def set_folder_hidden(conn: sqlite3.Connection, path: str, hidden: bool) -> bool:
    """Update the is_hidden status for a folder and all its contents in the database."""
    normalized = normalize_windows_path(path)
    cursor = conn.cursor()
    val = 1 if hidden else 0
    
    # Ensure the folder node exists and update its status
    # We don't have all the info for depth/parent_path here, so we just focus on the path and hidden status
    # If it's a new entry, depth and parent_path will be default/null which is acceptable for hiding logic
    cursor.execute(
        "INSERT INTO folder_nodes(path, is_hidden) VALUES (?, ?) ON CONFLICT(path) DO UPDATE SET is_hidden = excluded.is_hidden",
        (normalized, val)
    )
    
    # Update all media items within this folder (recursively)
    # We use LIKE for path prefix matching
    prefix = normalized
    if not prefix.endswith("/"):
        prefix += "/"
    cursor.execute("UPDATE media_items SET is_hidden = ? WHERE path LIKE ?", (val, prefix + "%"))
    conn.commit()
    return True


def is_path_hidden(conn: sqlite3.Connection, path: str) -> bool:
    """Check if a path is marked as hidden in the database (media or folder)."""
    normalized = normalize_windows_path(path)
    cursor = conn.cursor()
    # Check if it's a media item
    cursor.execute("SELECT is_hidden FROM media_items WHERE path = ?", (normalized,))
    row = cursor.fetchone()
    if row and row[0]:
        return True
    # Check if it's a folder
    cursor.execute("SELECT is_hidden FROM folder_nodes WHERE path = ?", (normalized,))
    row = cursor.fetchone()
    if row and row[0]:
        return True
    return False
