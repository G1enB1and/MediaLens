from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.mediamanager.utils.pathing import normalize_windows_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_people_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT,
          display_name TEXT NOT NULL,
          is_confirmed INTEGER NOT NULL DEFAULT 0,
          preview_face_id INTEGER,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_confirmed ON people(is_confirmed)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS media_faces (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          media_id INTEGER NOT NULL,
          person_id INTEGER,
          detection_engine TEXT NOT NULL DEFAULT 'insightface',
          recognition_model TEXT,
          embedding_json TEXT,
          bbox_left REAL NOT NULL DEFAULT 0,
          bbox_top REAL NOT NULL DEFAULT 0,
          bbox_width REAL NOT NULL DEFAULT 0,
          bbox_height REAL NOT NULL DEFAULT 0,
          confidence REAL,
          match_confidence REAL,
          status TEXT NOT NULL DEFAULT 'unreviewed',
          ignored INTEGER NOT NULL DEFAULT 0,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL,
          FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE,
          FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_faces_media ON media_faces(media_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_faces_person ON media_faces(person_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_faces_status ON media_faces(status, ignored)")


def normalize_person_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())


def _person_slug(name: str) -> str:
    return normalize_person_name(name).casefold()


def upsert_person(conn: sqlite3.Connection, name: str, *, confirmed: bool = True) -> int:
    ensure_people_tables(conn)
    display_name = normalize_person_name(name)
    if not display_name:
        raise ValueError("person name is required")
    slug = _person_slug(display_name)
    now = _utc_now_iso()
    row = conn.execute("SELECT id FROM people WHERE name = ?", (slug,)).fetchone()
    if row:
        conn.execute(
            """
            UPDATE people
            SET display_name = ?, is_confirmed = CASE WHEN ? THEN 1 ELSE is_confirmed END, updated_at_utc = ?
            WHERE id = ?
            """,
            (display_name, 1 if confirmed else 0, now, int(row[0])),
        )
        conn.commit()
        return int(row[0])
    cur = conn.execute(
        """
        INSERT INTO people(name, display_name, is_confirmed, created_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?)
        """,
        (slug, display_name, 1 if confirmed else 0, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_people(conn: sqlite3.Connection, *, include_unnamed: bool = True) -> list[dict]:
    ensure_people_tables(conn)
    where = "" if include_unnamed else "WHERE p.is_confirmed != 0"
    rows = conn.execute(
        f"""
        SELECT
            p.id,
            p.name,
            p.display_name,
            p.is_confirmed,
            COUNT(DISTINCT f.media_id) AS file_count,
            COUNT(f.id) AS face_count,
            COALESCE(p.preview_face_id, MIN(f.id)) AS preview_face_id,
            (
                SELECT m.path
                FROM media_faces pf
                JOIN media_items m ON m.id = pf.media_id
                WHERE pf.person_id = p.id AND COALESCE(pf.ignored, 0) = 0
                ORDER BY pf.match_confidence DESC, pf.id
                LIMIT 1
            ) AS preview_path
        FROM people p
        LEFT JOIN media_faces f ON f.person_id = p.id AND COALESCE(f.ignored, 0) = 0
        {where}
        GROUP BY p.id
        HAVING face_count > 0 OR p.is_confirmed != 0
        ORDER BY p.is_confirmed DESC, LOWER(p.display_name), p.id
        """
    ).fetchall()
    return [
        {
            "id": int(row[0]),
            "name": row[1] or "",
            "display_name": row[2] or "",
            "is_confirmed": bool(row[3]),
            "file_count": int(row[4] or 0),
            "face_count": int(row[5] or 0),
            "preview_face_id": int(row[6] or 0),
            "preview_path": row[7] or "",
        }
        for row in rows
    ]


def list_people_for_media(conn: sqlite3.Connection, path: str) -> list[dict]:
    ensure_people_tables(conn)
    normalized = normalize_windows_path(path)
    rows = conn.execute(
        """
        SELECT f.id, p.id, p.display_name, p.is_confirmed, f.status, f.match_confidence
        FROM media_faces f
        LEFT JOIN people p ON p.id = f.person_id
        JOIN media_items m ON m.id = f.media_id
        WHERE m.path = ? AND COALESCE(f.ignored, 0) = 0
        ORDER BY p.is_confirmed DESC, LOWER(p.display_name), f.id
        """,
        (normalized,),
    ).fetchall()
    people: list[dict] = []
    for row in rows:
        face_id = int(row[0])
        display_name = row[2] or f"Unnamed {face_id}"
        people.append(
            {
                "face_id": face_id,
                "person_id": int(row[1] or 0),
                "display_name": display_name,
                "is_confirmed": bool(row[3]),
                "status": row[4] or "unreviewed",
                "match_confidence": row[5],
            }
        )
    return people


def list_faces_for_person(conn: sqlite3.Connection, person_id: int) -> list[dict]:
    ensure_people_tables(conn)
    rows = conn.execute(
        """
        SELECT f.id, f.media_id, m.path, p.display_name, f.bbox_left, f.bbox_top, f.bbox_width, f.bbox_height,
               f.confidence, f.match_confidence, f.status
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        LEFT JOIN people p ON p.id = f.person_id
        WHERE f.person_id = ? AND COALESCE(f.ignored, 0) = 0
        ORDER BY f.match_confidence DESC, m.path
        """,
        (int(person_id),),
    ).fetchall()
    return [
        {
            "face_id": int(row[0]),
            "media_id": int(row[1]),
            "path": row[2] or "",
            "display_name": row[3] or "",
            "bbox": [float(row[4] or 0), float(row[5] or 0), float(row[6] or 0), float(row[7] or 0)],
            "confidence": row[8],
            "match_confidence": row[9],
            "status": row[10] or "unreviewed",
        }
        for row in rows
    ]


def add_manual_face_assignment(
    conn: sqlite3.Connection,
    path: str,
    person_name: str,
    *,
    status: str = "confirmed",
) -> int:
    ensure_people_tables(conn)
    from app.mediamanager.db.media_repo import get_media_by_path

    media = get_media_by_path(conn, path)
    if not media:
        raise ValueError("media item not found")
    person_id = upsert_person(conn, person_name, confirmed=True)
    now = _utc_now_iso()
    row = conn.execute(
        """
        SELECT id FROM media_faces
        WHERE media_id = ? AND person_id = ? AND detection_engine = 'manual'
        """,
        (int(media["id"]), int(person_id)),
    ).fetchone()
    if row:
        conn.execute(
            """
            UPDATE media_faces
            SET status = ?, ignored = 0, updated_at_utc = ?
            WHERE id = ?
            """,
            (status, now, int(row[0])),
        )
        conn.commit()
        return int(row[0])
    cur = conn.execute(
        """
        INSERT INTO media_faces(
            media_id, person_id, detection_engine, recognition_model,
            bbox_left, bbox_top, bbox_width, bbox_height, confidence, match_confidence,
            status, ignored, created_at_utc, updated_at_utc
        )
        VALUES (?, ?, 'manual', 'user-confirmed', 0, 0, 1, 1, 1, 1, ?, 0, ?, ?)
        """,
        (int(media["id"]), int(person_id), status, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def ignore_face(conn: sqlite3.Connection, face_id: int) -> bool:
    ensure_people_tables(conn)
    cur = conn.execute(
        "UPDATE media_faces SET ignored = 1, status = 'ignored', updated_at_utc = ? WHERE id = ?",
        (_utc_now_iso(), int(face_id)),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def assign_face_to_person(conn: sqlite3.Connection, face_id: int, person_name: str) -> bool:
    ensure_people_tables(conn)
    person_id = upsert_person(conn, person_name, confirmed=True)
    cur = conn.execute(
        """
        UPDATE media_faces
        SET person_id = ?, status = 'confirmed', ignored = 0, match_confidence = 1, updated_at_utc = ?
        WHERE id = ?
        """,
        (int(person_id), _utc_now_iso(), int(face_id)),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def reject_face_from_person(conn: sqlite3.Connection, face_id: int) -> bool:
    ensure_people_tables(conn)
    cur = conn.execute(
        """
        UPDATE media_faces
        SET person_id = NULL, status = 'rejected', match_confidence = 0, updated_at_utc = ?
        WHERE id = ?
        """,
        (_utc_now_iso(), int(face_id)),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def person_names_for_row(conn: sqlite3.Connection, media_id: int) -> str:
    ensure_people_tables(conn)
    rows = conn.execute(
        """
        SELECT p.display_name
        FROM media_faces f
        JOIN people p ON p.id = f.person_id
        WHERE f.media_id = ? AND COALESCE(f.ignored, 0) = 0
        ORDER BY p.is_confirmed DESC, LOWER(p.display_name)
        """,
        (int(media_id),),
    ).fetchall()
    return ", ".join(str(row[0] or "").strip() for row in rows if str(row[0] or "").strip())


def bootstrap_people_from_tags(conn: sqlite3.Connection, paths: Iterable[str] | None = None) -> int:
    ensure_people_tables(conn)
    path_filter = ""
    params: list[str] = []
    if paths is not None:
        normalized_paths = [normalize_windows_path(path) for path in paths if str(path or "").strip()]
        if not normalized_paths:
            return 0
        placeholders = ", ".join("?" for _ in normalized_paths)
        path_filter = f"AND m.path IN ({placeholders})"
        params.extend(normalized_paths)
    rows = conn.execute(
        f"""
        SELECT m.path, t.name
        FROM media_items m
        JOIN media_tags mt ON mt.media_id = m.id
        JOIN tags t ON t.id = mt.tag_id
        WHERE LENGTH(TRIM(t.name)) > 1
          AND t.name NOT LIKE '% % %'
          {path_filter}
        ORDER BY m.path, t.name
        """,
        params,
    ).fetchall()
    created = 0
    for path, tag_name in rows:
        name = normalize_person_name(tag_name)
        if not name or len(name) > 48 or any(ch in name for ch in "#:/\\"):
            continue
        try:
            add_manual_face_assignment(conn, str(path or ""), name, status="suggested")
            created += 1
        except Exception:
            continue
    return created
