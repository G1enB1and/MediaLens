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


def _original_file_date_iso(
    file_created_time: str | None,
    modified_time: str | None,
    existing_original_file_date: str | None = None,
) -> str | None:
    candidates = [
        str(value).strip()
        for value in (file_created_time, modified_time, existing_original_file_date)
        if str(value or "").strip()
    ]
    return min(candidates) if candidates else None


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


def _effective_text_detected_value(
    text_likely,
    user_confirmed_text_detected,
    text_more_likely=None,
    text_verified=None,
):
    if user_confirmed_text_detected is not None:
        return bool(user_confirmed_text_detected)
    if text_verified is not None and bool(text_verified):
        return True
    if text_more_likely is not None and bool(text_more_likely):
        return True
    if text_verified is not None or text_more_likely is not None or text_likely is not None:
        return False
    return None


def _ensure_media_items_scan_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_items)").fetchall()}
    if "original_file_date_utc" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN original_file_date_utc TEXT")
    if "phash" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN phash TEXT")
    if "text_likely" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_likely INTEGER")
        if "text_detected" in cols:
            conn.execute("UPDATE media_items SET text_likely = text_detected WHERE text_likely IS NULL")
    if "text_detection_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_score REAL")
    if "text_detection_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_detection_version INTEGER")
    if "user_confirmed_text_detected" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN user_confirmed_text_detected INTEGER")
    if "detected_text" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN detected_text TEXT")
    if "text_more_likely" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely INTEGER")
    if "text_more_likely_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely_score REAL")
    if "text_more_likely_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_more_likely_version INTEGER")
    if "text_verified" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verified INTEGER")
    if "text_verification_score" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verification_score REAL")
    if "text_verification_version" not in cols:
        conn.execute("ALTER TABLE media_items ADD COLUMN text_verification_version INTEGER")
    rows = conn.execute(
        """
        SELECT id, file_created_time_utc, modified_time_utc
        FROM media_items
        WHERE original_file_date_utc IS NULL OR original_file_date_utc = ''
        """
    ).fetchall()
    for media_id, created_time, modified_time in rows:
        next_original = _original_file_date_iso(created_time, modified_time)
        if next_original is not None:
            conn.execute(
                "UPDATE media_items SET original_file_date_utc = ? WHERE id = ?",
                (next_original, int(media_id)),
            )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_phash ON media_items(phash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_likely ON media_items(text_likely)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_items_text_more_likely ON media_items(text_more_likely)")
    try:
        from app.mediamanager.db.ocr_repo import ensure_ocr_tables

        ensure_ocr_tables(conn)
    except Exception:
        pass
    conn.commit()


def _ensure_media_ai_columns(conn: sqlite3.Connection) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "media_ai_metadata" not in tables:
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_ai_metadata)").fetchall()}
    if "user_confirmed_ai" not in cols:
        conn.execute("ALTER TABLE media_ai_metadata ADD COLUMN user_confirmed_ai INTEGER")
        conn.commit()


def _ensure_review_pair_exclusions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_pair_exclusions (
            left_path TEXT NOT NULL,
            right_path TEXT NOT NULL,
            review_mode TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            PRIMARY KEY (left_path, right_path, review_mode)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_review_pair_exclusions_mode ON review_pair_exclusions(review_mode)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_review_pair_exclusions_left ON review_pair_exclusions(left_path, review_mode)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_review_pair_exclusions_right ON review_pair_exclusions(right_path, review_mode)")


def _normalize_review_mode(review_mode: str) -> str:
    value = str(review_mode or "").strip().casefold()
    if value in {"similar", "similar_only"}:
        return "similar"
    if value == "duplicates":
        return "duplicates"
    return ""


def _canonical_review_pair(path_a: str, path_b: str) -> tuple[str, str] | None:
    left = normalize_windows_path(path_a)
    right = normalize_windows_path(path_b)
    if not left or not right or left == right:
        return None
    return (left, right) if left < right else (right, left)


def add_review_pair_exclusions(
    conn: sqlite3.Connection,
    path: str,
    related_paths: Iterable[str],
    review_mode: str,
) -> int:
    mode = _normalize_review_mode(review_mode)
    if not mode:
        return 0
    _ensure_review_pair_exclusions_table(conn)
    pairs = sorted(
        {
            pair
            for pair in (_canonical_review_pair(path, related_path) for related_path in related_paths)
            if pair is not None
        }
    )
    if not pairs:
        return 0
    now = _utc_now_iso()
    conn.executemany(
        """
        INSERT OR IGNORE INTO review_pair_exclusions(left_path, right_path, review_mode, created_at_utc)
        VALUES (?, ?, ?, ?)
        """,
        [(left, right, mode, now) for left, right in pairs],
    )
    conn.commit()
    return len(pairs)


def list_review_pair_exclusions(
    conn: sqlite3.Connection,
    review_mode: str,
    *,
    paths: Iterable[str] | None = None,
) -> set[tuple[str, str]]:
    mode = _normalize_review_mode(review_mode)
    if not mode:
        return set()
    _ensure_review_pair_exclusions_table(conn)
    where_parts = ["review_mode = ?"]
    params: list[str] = [mode]
    if paths is not None:
        normalized_paths = sorted({normalize_windows_path(path) for path in paths if str(path or "").strip()})
        if not normalized_paths:
            return set()
        placeholders = ", ".join("?" for _ in normalized_paths)
        where_parts.append(f"left_path IN ({placeholders})")
        where_parts.append(f"right_path IN ({placeholders})")
        params.extend(normalized_paths)
        params.extend(normalized_paths)
    rows = conn.execute(
        f"""
        SELECT left_path, right_path
        FROM review_pair_exclusions
        WHERE {" AND ".join(where_parts)}
        """,
        params,
    ).fetchall()
    return {
        (str(left_path or ""), str(right_path or ""))
        for left_path, right_path in rows
        if str(left_path or "") and str(right_path or "")
    }


def clear_review_pair_exclusions(conn: sqlite3.Connection) -> int:
    _ensure_review_pair_exclusions_table(conn)
    cursor = conn.execute("DELETE FROM review_pair_exclusions")
    conn.commit()
    return int(cursor.rowcount or 0)


def add_media_item(
    conn: sqlite3.Connection,
    path: str,
    media_type: str,
    content_hash: Optional[str] = None,
    phash: Optional[str] = None,
    text_likely: Optional[bool] = None,
    text_detection_score: Optional[float] = None,
    text_detection_version: Optional[int] = None,
    text_more_likely: Optional[bool] = None,
    text_more_likely_score: Optional[float] = None,
    text_more_likely_version: Optional[int] = None,
    text_verified: Optional[bool] = None,
    text_verification_score: Optional[float] = None,
    text_verification_version: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
    is_hidden: int = 0,
) -> int:
    _ensure_media_items_scan_columns(conn)
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)

    # Simple stat collection for discovery
    size, created_time, mtime = _collect_file_stats(path)
    existing = conn.execute(
        "SELECT original_file_date_utc FROM media_items WHERE path = ?",
        (normalized,),
    ).fetchone()
    original_file_date = _original_file_date_iso(
        created_time,
        mtime,
        existing[0] if existing else None,
    )

    conn.execute(
        """
        INSERT INTO media_items(path, content_hash, phash, text_likely, text_detection_score, text_detection_version, text_more_likely, text_more_likely_score, text_more_likely_version, text_verified, text_verification_score, text_verification_version, media_type, file_size_bytes, file_created_time_utc, modified_time_utc, original_file_date_utc, width, height, duration_ms, is_hidden, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          content_hash=COALESCE(excluded.content_hash, content_hash),
          phash=COALESCE(excluded.phash, phash),
          text_likely=COALESCE(excluded.text_likely, text_likely),
          text_detection_score=COALESCE(excluded.text_detection_score, text_detection_score),
          text_detection_version=COALESCE(excluded.text_detection_version, text_detection_version),
          text_more_likely=COALESCE(excluded.text_more_likely, text_more_likely),
          text_more_likely_score=COALESCE(excluded.text_more_likely_score, text_more_likely_score),
          text_more_likely_version=COALESCE(excluded.text_more_likely_version, text_more_likely_version),
          text_verified=COALESCE(excluded.text_verified, text_verified),
          text_verification_score=COALESCE(excluded.text_verification_score, text_verification_score),
          text_verification_version=COALESCE(excluded.text_verification_version, text_verification_version),
          media_type=excluded.media_type,
          file_size_bytes=excluded.file_size_bytes,
          file_created_time_utc=COALESCE(excluded.file_created_time_utc, file_created_time_utc),
          modified_time_utc=excluded.modified_time_utc,
          original_file_date_utc=COALESCE(excluded.original_file_date_utc, original_file_date_utc),
          width=COALESCE(excluded.width, width),
          height=COALESCE(excluded.height, height),
          duration_ms=COALESCE(excluded.duration_ms, duration_ms),
          is_hidden=COALESCE(excluded.is_hidden, is_hidden),
          updated_at_utc=excluded.updated_at_utc
        """,
        (normalized, content_hash, phash, (1 if text_likely else 0) if text_likely is not None else None, text_detection_score, text_detection_version, (1 if text_more_likely else 0) if text_more_likely is not None else None, text_more_likely_score, text_more_likely_version, (1 if text_verified else 0) if text_verified is not None else None, text_verification_score, text_verification_version, media_type, size, created_time, mtime, original_file_date, width, height, duration_ms, is_hidden, now, now),
    )
    row = conn.execute("SELECT id FROM media_items WHERE path = ?", (normalized,)).fetchone()
    if not row:
        raise RuntimeError("failed to insert media item")
    conn.commit()
    return int(row[0])


def get_media_by_path(conn: sqlite3.Connection, path: str) -> Optional[dict]:
    _ensure_media_items_scan_columns(conn)
    normalized = normalize_windows_path(path)
    row = conn.execute(
        "SELECT id, path, content_hash, media_type, file_size_bytes, file_created_time_utc, modified_time_utc, original_file_date_utc, exif_date_taken, metadata_date, width, height, duration_ms, is_hidden, phash, text_likely, text_detection_score, text_detection_version, user_confirmed_text_detected, detected_text, text_more_likely, text_more_likely_score, text_more_likely_version, text_verified, text_verification_score, text_verification_version FROM media_items WHERE path = ?",
        (normalized,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "path": row[1],
        "content_hash": row[2],
        "media_type": row[3],
        "file_size": row[4],
        "file_created_time": row[5],
        "modified_time": row[6],
        "original_file_date": row[7],
        "exif_date_taken": row[8],
        "metadata_date": row[9],
        "width": row[10],
        "height": row[11],
        "duration_ms": row[12],
        "is_hidden": bool(row[13]),
        "phash": row[14],
        "text_likely": None if row[15] is None else bool(row[15]),
        "text_detection_score": row[16],
        "text_detection_version": row[17],
        "user_confirmed_text_detected": None if row[18] is None else bool(row[18]),
        "effective_text_detected": _effective_text_detected_value(row[15], row[18], row[20], row[23]),
        "detected_text": row[19] or "",
        "text_more_likely": None if row[20] is None else bool(row[20]),
        "text_more_likely_score": row[21],
        "text_more_likely_version": row[22],
        "text_verified": None if row[23] is None else bool(row[23]),
        "text_verification_score": row[24],
        "text_verification_version": row[25],
    }


def update_user_confirmed_text_detected(
    conn: sqlite3.Connection,
    media_id: int,
    user_confirmed_text_detected: bool | None,
) -> None:
    _ensure_media_items_scan_columns(conn)
    conn.execute(
        """
        UPDATE media_items
        SET user_confirmed_text_detected = ?, updated_at_utc = ?
        WHERE id = ?
        """,
        (
            None if user_confirmed_text_detected is None else (1 if bool(user_confirmed_text_detected) else 0),
            _utc_now_iso(),
            int(media_id),
        ),
    )
    conn.commit()


def update_media_detected_text(conn: sqlite3.Connection, media_id: int, detected_text: str | None) -> None:
    _ensure_media_items_scan_columns(conn)
    try:
        from app.mediamanager.db.ocr_repo import add_ocr_result

        add_ocr_result(
            conn,
            int(media_id),
            source="user",
            text=str(detected_text or "").strip(),
            confidence=1.0 if str(detected_text or "").strip() else 0.0,
            engine_version="manual",
            preprocess_profile="user_entry",
            select_as_winner=True,
            selected_by="user",
        )
    except Exception:
        conn.execute(
            """
            UPDATE media_items
            SET detected_text = ?, updated_at_utc = ?
            WHERE id = ?
            """,
            (str(detected_text or "").strip(), _utc_now_iso(), int(media_id)),
        )
        conn.commit()


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
    text_likely: bool | None = None,
    text_detection_score: float | None = None,
    text_detection_version: int | None = None,
    text_more_likely: bool | None = None,
    text_more_likely_score: float | None = None,
    text_more_likely_version: int | None = None,
    text_verified: bool | None = None,
    text_verification_score: float | None = None,
    text_verification_version: int | None = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> int:
    """Upsert media item, handling renames/moves via content hash."""
    _ensure_media_items_scan_columns(conn)
    now = _utc_now_iso()
    normalized = normalize_windows_path(path)

    # Collect current stats to keep DB in sync
    size, created_time, mtime = _collect_file_stats(path)

    # 1. Check if we already have this exact path
    existing_by_path = conn.execute(
        "SELECT id, content_hash, original_file_date_utc FROM media_items WHERE path = ?", (normalized,)
    ).fetchone()

    if existing_by_path:
        original_file_date = _original_file_date_iso(created_time, mtime, existing_by_path[2])
        # Path exists. Update hash AND stats
        conn.execute(
            """
                UPDATE media_items 
            SET content_hash = ?, phash = COALESCE(?, phash), text_likely = COALESCE(?, text_likely), text_detection_score = COALESCE(?, text_detection_score), text_detection_version = COALESCE(?, text_detection_version), text_more_likely = COALESCE(?, text_more_likely), text_more_likely_score = COALESCE(?, text_more_likely_score), text_more_likely_version = COALESCE(?, text_more_likely_version), text_verified = COALESCE(?, text_verified), text_verification_score = COALESCE(?, text_verification_score), text_verification_version = COALESCE(?, text_verification_version), file_size_bytes = ?, file_created_time_utc = ?, modified_time_utc = ?, original_file_date_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
            WHERE id = ?
            """,
            (content_hash, phash, (1 if text_likely else 0) if text_likely is not None else None, text_detection_score, text_detection_version, (1 if text_more_likely else 0) if text_more_likely is not None else None, text_more_likely_score, text_more_likely_version, (1 if text_verified else 0) if text_verified is not None else None, text_verification_score, text_verification_version, size, created_time, mtime, original_file_date, width, height, duration_ms, now, existing_by_path[0]),
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
        existing_original = conn.execute(
            "SELECT original_file_date_utc FROM media_items WHERE id = ?",
            (int(media_id),),
        ).fetchone()

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
                SET path = ?, phash = COALESCE(?, phash), text_likely = COALESCE(?, text_likely), text_detection_score = COALESCE(?, text_detection_score), text_detection_version = COALESCE(?, text_detection_version), text_more_likely = COALESCE(?, text_more_likely), text_more_likely_score = COALESCE(?, text_more_likely_score), text_more_likely_version = COALESCE(?, text_more_likely_version), text_verified = COALESCE(?, text_verified), text_verification_score = COALESCE(?, text_verification_score), text_verification_version = COALESCE(?, text_verification_version), file_size_bytes = ?, file_created_time_utc = ?, modified_time_utc = ?, original_file_date_utc = ?, width = ?, height = ?, duration_ms = ?, updated_at_utc = ? 
                WHERE id = ?
                """,
                (
                    normalized,
                    phash,
                    (1 if text_likely else 0) if text_likely is not None else None,
                    text_detection_score,
                    text_detection_version,
                    (1 if text_more_likely else 0) if text_more_likely is not None else None,
                    text_more_likely_score,
                    text_more_likely_version,
                    (1 if text_verified else 0) if text_verified is not None else None,
                    text_verification_score,
                    text_verification_version,
                    size,
                    created_time,
                    mtime,
                    _original_file_date_iso(created_time, mtime, existing_original[0] if existing_original else None),
                    width,
                    height,
                    duration_ms,
                    now,
                    media_id,
                ),
            )
            conn.commit()
            return int(media_id)
        else:
            # Old path still exists -> Duplicate content at new path
            # We treat this as a new media item (different file, same content)
            pass

    # 3. Brand new item (or duplicate content at new path)
    return add_media_item(conn, normalized, media_type, content_hash, phash=phash, text_likely=text_likely, text_detection_score=text_detection_score, text_detection_version=text_detection_version, text_more_likely=text_more_likely, text_more_likely_score=text_more_likely_score, text_more_likely_version=text_more_likely_version, text_verified=text_verified, text_verification_score=text_verification_score, text_verification_version=text_verification_version, width=width, height=height, duration_ms=duration_ms)


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


def list_media_in_smart_collection(
    conn: sqlite3.Connection,
    field_name: str,
    cutoff_iso: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict]:
    field = str(field_name or "").strip()
    predicate_map = {
        "no_tags": "NOT EXISTS (SELECT 1 FROM media_tags mt WHERE mt.media_id = m.id)",
        "no_description": "(meta.description IS NULL OR TRIM(meta.description) = '')",
        "file_size_gt_3mb": "m.file_size_bytes > 3145728",
        "file_size_gt_10mb": "m.file_size_bytes > 10485760",
        "file_size_gt_25mb": "m.file_size_bytes > 26214400",
        "file_size_gt_100mb": "m.file_size_bytes > 104857600",
        "file_size_gt_1gb": "m.file_size_bytes > 1073741824",
    }
    if field in predicate_map:
        return _list_media_with_where(conn, predicate_map[field], [], limit=limit, offset=offset)
    if field not in {"metadata_date", "modified_time_utc"}:
        return []
    db_field = "m.metadata_date" if field == "metadata_date" else "m.modified_time_utc"
    where_sql = f"{db_field} IS NOT NULL AND {db_field} != '' AND {db_field} >= ?"
    return _list_media_with_where(conn, where_sql, [str(cutoff_iso or "")], limit=limit, offset=offset)


def count_media_in_smart_collection(
    conn: sqlite3.Connection,
    field_name: str,
    cutoff_iso: str,
) -> int:
    _ensure_media_items_scan_columns(conn)
    field = str(field_name or "").strip()
    predicate_map = {
        "no_tags": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE NOT EXISTS (SELECT 1 FROM media_tags mt WHERE mt.media_id = m.id)
        """,
        "no_description": """
            SELECT COUNT(*)
            FROM media_items m
            LEFT JOIN media_metadata meta ON m.id = meta.media_id
            WHERE meta.description IS NULL OR TRIM(meta.description) = ''
        """,
        "file_size_gt_3mb": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE m.file_size_bytes > 3145728
        """,
        "file_size_gt_10mb": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE m.file_size_bytes > 10485760
        """,
        "file_size_gt_25mb": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE m.file_size_bytes > 26214400
        """,
        "file_size_gt_100mb": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE m.file_size_bytes > 104857600
        """,
        "file_size_gt_1gb": """
            SELECT COUNT(*)
            FROM media_items m
            WHERE m.file_size_bytes > 1073741824
        """,
    }
    if field in predicate_map:
        row = conn.execute(predicate_map[field]).fetchone()
        return int((row[0] if row else 0) or 0)
    if field not in {"metadata_date", "modified_time_utc"}:
        return 0
    db_field = "metadata_date" if field == "metadata_date" else "modified_time_utc"
    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM media_items
        WHERE {db_field} IS NOT NULL AND {db_field} != '' AND {db_field} >= ?
        """,
        (str(cutoff_iso or ""),),
    ).fetchone()
    return int((row[0] if row else 0) or 0)


def _list_media_with_where(
    conn: sqlite3.Connection,
    where_sql: str,
    params: list,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict]:
    _ensure_media_items_scan_columns(conn)
    _ensure_media_ai_columns(conn)
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
            m.original_file_date_utc,
            m.exif_date_taken,
            m.metadata_date,
            m.width,
            m.height,
            m.duration_ms,
            CASE
                WHEN COALESCE(m.is_hidden, 0) != 0 THEN 1
                WHEN EXISTS (
                    SELECT 1
                    FROM folder_nodes fn
                    WHERE COALESCE(fn.is_hidden, 0) != 0
                      AND (m.path = fn.path OR m.path LIKE fn.path || '/%')
                ) THEN 1
                ELSE 0
            END AS effective_is_hidden,
            m.text_likely,
            m.text_detection_score,
            m.text_detection_version,
            m.user_confirmed_text_detected,
            m.detected_text,
            m.text_more_likely,
            m.text_more_likely_score,
            m.text_more_likely_version,
            m.text_verified,
            m.text_verification_score,
            m.text_verification_version,
            ai.is_ai_detected,
            ai.is_ai_confidence,
            ai.user_confirmed_ai,
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
        "original_file_date": row[8],
        "exif_date_taken": row[9],
        "metadata_date": row[10],
        "width": row[11],
        "height": row[12],
        "duration": (row[13] / 1000.0) if row[13] else None,
        "is_hidden": bool(row[14]),
        "text_likely": None if row[15] is None else bool(row[15]),
        "text_detection_score": row[16],
        "text_detection_version": row[17],
        "user_confirmed_text_detected": None if row[18] is None else bool(row[18]),
        "effective_text_detected": _effective_text_detected_value(row[15], row[18], row[20], row[23]),
        "detected_text": row[19] or "",
        "text_more_likely": None if row[20] is None else bool(row[20]),
        "text_more_likely_score": row[21],
        "text_more_likely_version": row[22],
        "text_verified": None if row[23] is None else bool(row[23]),
        "text_verification_score": row[24],
        "text_verification_version": row[25],
        "is_ai_detected": None if row[26] is None else bool(row[26]),
        "is_ai_confidence": row[27],
        "user_confirmed_ai": None if row[28] is None else bool(row[28]),
        "effective_is_ai": (bool(row[28]) if row[28] is not None else (None if row[26] is None else bool(row[26]))),
        "title": row[29],
        "description": row[30],
        "notes": row[31],
        "ai_prompt": row[32],
        "ai_negative_prompt": row[33],
        "tool_name_found": row[34],
        "tool_name_inferred": row[35],
        "model_name": row[36],
        "checkpoint_name": row[37],
        "sampler": row[38],
        "scheduler": row[39],
        "cfg_scale": row[40],
        "steps": row[41],
        "seed": row[42],
        "source_formats": row[43],
        "metadata_families": row[44],
        "ai_loras": row[45],
        "tags": row[46],
        "collection_names": row[47],
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
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif", ".svg"}
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
    """Check if a path or any ancestor folder is marked hidden in the database."""
    normalized = normalize_windows_path(path)
    cursor = conn.cursor()
    # Check if it's a media item
    cursor.execute("SELECT is_hidden FROM media_items WHERE path = ?", (normalized,))
    row = cursor.fetchone()
    if row and row[0]:
        return True
    # Check if the path itself or any ancestor folder is hidden.
    cursor.execute(
        """
        SELECT 1
        FROM folder_nodes
        WHERE COALESCE(is_hidden, 0) != 0
          AND (? = path OR ? LIKE path || '/%')
        LIMIT 1
        """,
        (normalized, normalized),
    )
    row = cursor.fetchone()
    return bool(row and row[0])
