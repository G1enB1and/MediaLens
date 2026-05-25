from __future__ import annotations

import sqlite3
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.mediamanager.utils.pathing import normalize_windows_path


PEOPLE_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".avif",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_people_supported_image_path(path: str) -> bool:
    return Path(str(path or "")).suffix.lower() in PEOPLE_IMAGE_EXTENSIONS


def ensure_people_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT,
          display_name TEXT NOT NULL,
          is_confirmed INTEGER NOT NULL DEFAULT 0,
          is_favorite INTEGER NOT NULL DEFAULT 0,
          preview_face_id INTEGER,
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_confirmed ON people(is_confirmed)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_favorite ON people(is_favorite)")
    people_cols = {str(row[1] or "") for row in conn.execute("PRAGMA table_info(people)").fetchall()}
    if "is_favorite" not in people_cols:
        conn.execute("ALTER TABLE people ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS media_faces (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          media_id INTEGER NOT NULL,
          person_id INTEGER,
          detection_engine TEXT NOT NULL DEFAULT 'insightface',
          recognition_model TEXT,
          embedding_json TEXT,
          landmarks_json TEXT,
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
    cols = {str(row[1] or "") for row in conn.execute("PRAGMA table_info(media_faces)").fetchall()}
    if "landmarks_json" not in cols:
        conn.execute("ALTER TABLE media_faces ADD COLUMN landmarks_json TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS people_scan_state (
          media_id INTEGER NOT NULL,
          detection_engine TEXT NOT NULL DEFAULT 'insightface',
          face_count INTEGER NOT NULL DEFAULT 0,
          scanned_at_utc TEXT NOT NULL,
          PRIMARY KEY(media_id, detection_engine),
          FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_scan_state_engine ON people_scan_state(detection_engine, scanned_at_utc)")


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


def name_person_group(conn: sqlite3.Connection, person_id: int, name: str) -> int:
    ensure_people_tables(conn)
    display_name = normalize_person_name(name)
    if not display_name:
        raise ValueError("person name is required")
    source_id = int(person_id or 0)
    slug = _person_slug(display_name)
    now = _utc_now_iso()
    existing = conn.execute("SELECT id FROM people WHERE name = ? AND id != ?", (slug, source_id)).fetchone()
    if existing:
        target_id = int(existing[0])
        conn.execute(
            "UPDATE media_faces SET person_id = ?, status = CASE WHEN status = 'unreviewed' THEN 'suggested' ELSE status END, updated_at_utc = ? WHERE person_id = ?",
            (target_id, now, source_id),
        )
        conn.execute("UPDATE people SET is_confirmed = 1, updated_at_utc = ? WHERE id = ?", (now, target_id))
        conn.execute("DELETE FROM people WHERE id = ? AND is_confirmed = 0", (source_id,))
        conn.commit()
        return target_id
    conn.execute(
        """
        UPDATE people
        SET name = ?, display_name = ?, is_confirmed = 1, updated_at_utc = ?
        WHERE id = ?
        """,
        (slug, display_name, now, source_id),
    )
    conn.execute(
        "UPDATE media_faces SET status = CASE WHEN status = 'unreviewed' THEN 'suggested' ELSE status END, updated_at_utc = ? WHERE person_id = ?",
        (now, source_id),
    )
    conn.commit()
    return source_id


def confirm_person_group(conn: sqlite3.Connection, person_id: int) -> bool:
    ensure_people_tables(conn)
    now = _utc_now_iso()
    cur = conn.execute(
        """
        UPDATE media_faces
        SET status = 'confirmed', match_confidence = COALESCE(match_confidence, 1), ignored = 0, updated_at_utc = ?
        WHERE person_id = ? AND COALESCE(ignored, 0) = 0
        """,
        (now, int(person_id or 0)),
    )
    conn.execute("UPDATE people SET is_confirmed = 1, updated_at_utc = ? WHERE id = ?", (now, int(person_id or 0)))
    conn.commit()
    return int(cur.rowcount or 0) > 0


def ignore_person_group(conn: sqlite3.Connection, person_id: int) -> bool:
    ensure_people_tables(conn)
    now = _utc_now_iso()
    cur = conn.execute(
        """
        UPDATE media_faces
        SET ignored = 1, status = 'ignored', updated_at_utc = ?
        WHERE person_id = ? AND COALESCE(ignored, 0) = 0
        """,
        (now, int(person_id or 0)),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def confirm_face(conn: sqlite3.Connection, face_id: int) -> bool:
    ensure_people_tables(conn)
    now = _utc_now_iso()
    cur = conn.execute(
        """
        UPDATE media_faces
        SET status = 'confirmed', match_confidence = COALESCE(match_confidence, 1), ignored = 0, updated_at_utc = ?
        WHERE id = ? AND COALESCE(ignored, 0) = 0
        """,
        (now, int(face_id or 0)),
    )
    row = conn.execute("SELECT person_id FROM media_faces WHERE id = ?", (int(face_id or 0),)).fetchone()
    if row and row[0]:
        conn.execute("UPDATE people SET is_confirmed = 1, updated_at_utc = ? WHERE id = ?", (now, int(row[0])))
    conn.commit()
    return int(cur.rowcount or 0) > 0


def _preview_face_for_person(conn: sqlite3.Connection, person_id: int) -> dict:
    explicit_row = conn.execute(
        """
        SELECT f.id, m.path, f.bbox_left, f.bbox_top, f.bbox_width, f.bbox_height, f.landmarks_json
        FROM people p
        JOIN media_faces f ON f.id = p.preview_face_id
        JOIN media_items m ON m.id = f.media_id
        WHERE p.id = ?
          AND f.person_id = p.id
          AND COALESCE(f.ignored, 0) = 0
        """,
        (int(person_id or 0),),
    ).fetchone()
    rows = [explicit_row] if explicit_row else []
    if not rows:
        rows = conn.execute(
            """
            SELECT f.id, m.path, f.bbox_left, f.bbox_top, f.bbox_width, f.bbox_height, f.landmarks_json
            FROM media_faces f
            JOIN media_items m ON m.id = f.media_id
            WHERE f.person_id = ? AND COALESCE(f.ignored, 0) = 0
            ORDER BY f.match_confidence DESC, f.id
            """,
            (int(person_id or 0),),
        ).fetchall()
    for row in rows:
        path = row[1] or ""
        if not _is_people_supported_image_path(path):
            continue
        return {
            "preview_face_id": int(row[0] or 0),
            "preview_path": path,
            "preview_bbox": [float(row[2] or 0), float(row[3] or 0), float(row[4] or 0), float(row[5] or 0)],
            "preview_landmarks": _landmarks_from_json(row[6]),
        }
    return {"preview_face_id": 0, "preview_path": "", "preview_bbox": [], "preview_landmarks": []}


def _person_id_for_name(conn: sqlite3.Connection, name: str) -> int:
    display_name = normalize_person_name(name)
    if not display_name:
        return 0
    slug = _person_slug(display_name)
    row = conn.execute("SELECT id FROM people WHERE name = ? OR display_name = ?", (slug, display_name)).fetchone()
    return int(row[0] or 0) if row else 0


def set_person_preview_face(conn: sqlite3.Connection, person_id: int, face_id: int) -> bool:
    ensure_people_tables(conn)
    target_person_id = int(person_id or 0)
    target_face_id = int(face_id or 0)
    if target_person_id <= 0 or target_face_id <= 0:
        return False
    row = conn.execute(
        """
        SELECT id
        FROM media_faces
        WHERE id = ? AND person_id = ? AND COALESCE(ignored, 0) = 0
        """,
        (target_face_id, target_person_id),
    ).fetchone()
    if not row:
        return False
    now = _utc_now_iso()
    conn.execute(
        "UPDATE people SET preview_face_id = ?, updated_at_utc = ? WHERE id = ?",
        (target_face_id, now, target_person_id),
    )
    conn.commit()
    return True


def set_person_preview_for_media(conn: sqlite3.Connection, person_name: str, path: str) -> bool:
    ensure_people_tables(conn)
    target_person_id = _person_id_for_name(conn, person_name)
    clean_path = normalize_windows_path(path)
    if target_person_id <= 0 or not clean_path:
        return False
    row = conn.execute(
        """
        SELECT f.id
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        WHERE f.person_id = ?
          AND m.path = ?
          AND COALESCE(f.ignored, 0) = 0
        ORDER BY
          CASE COALESCE(f.status, 'unreviewed')
            WHEN 'confirmed' THEN 0
            WHEN 'suggested' THEN 1
            WHEN 'unreviewed' THEN 2
            ELSE 3
          END,
          COALESCE(f.match_confidence, 0) DESC,
          COALESCE(f.confidence, 0) DESC,
          f.id
        LIMIT 1
        """,
        (target_person_id, clean_path),
    ).fetchone()
    if not row:
        return False
    return set_person_preview_face(conn, target_person_id, int(row[0] or 0))


def set_person_favorite(conn: sqlite3.Connection, person_id: int, favorite: bool) -> bool:
    ensure_people_tables(conn)
    target_person_id = int(person_id or 0)
    if target_person_id <= 0:
        return False
    now = _utc_now_iso()
    cur = conn.execute(
        "UPDATE people SET is_favorite = ?, updated_at_utc = ? WHERE id = ?",
        (1 if favorite else 0, now, target_person_id),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def _supported_face_counts_for_person(conn: sqlite3.Connection, person_id: int) -> tuple[int, int]:
    rows = conn.execute(
        """
        SELECT f.id, f.media_id, m.path
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        WHERE f.person_id = ? AND COALESCE(f.ignored, 0) = 0
        """,
        (int(person_id or 0),),
    ).fetchall()
    media_ids: set[int] = set()
    face_count = 0
    for face_id, media_id, path in rows:
        if not _is_people_supported_image_path(path or ""):
            continue
        face_count += 1 if face_id else 0
        media_ids.add(int(media_id or 0))
    return len(media_ids), face_count


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
            p.is_favorite,
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
        ORDER BY p.is_favorite DESC, p.is_confirmed DESC, LOWER(p.display_name), p.id
        """
    ).fetchall()
    people: list[dict] = []
    for row in rows:
        file_count, face_count = _supported_face_counts_for_person(conn, int(row[0]))
        if face_count <= 0:
            continue
        preview = _preview_face_for_person(conn, int(row[0]))
        people.append(
            {
                "id": int(row[0]),
                "name": row[1] or "",
                "display_name": row[2] or "",
                "is_confirmed": bool(row[3]),
                "is_favorite": bool(row[4]),
                "file_count": file_count,
                "face_count": face_count,
                "preview_face_id": int(preview.get("preview_face_id") or row[7] or 0),
                "preview_path": preview.get("preview_path") or "",
                "preview_bbox": preview.get("preview_bbox") or [],
                "preview_landmarks": preview.get("preview_landmarks") or [],
            }
        )
    return people


def list_people_for_media(conn: sqlite3.Connection, path: str) -> list[dict]:
    ensure_people_tables(conn)
    normalized = normalize_windows_path(path)
    if not _is_people_supported_image_path(normalized):
        return []
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
               f.confidence, f.match_confidence, f.status, f.landmarks_json
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        LEFT JOIN people p ON p.id = f.person_id
        WHERE f.person_id = ? AND COALESCE(f.ignored, 0) = 0
        ORDER BY f.match_confidence DESC, m.path
        """,
        (int(person_id),),
    ).fetchall()
    faces: list[dict] = []
    for row in rows:
        path = row[2] or ""
        if not _is_people_supported_image_path(path):
            continue
        faces.append(
            {
                "face_id": int(row[0]),
                "media_id": int(row[1]),
                "path": path,
                "display_name": row[3] or "",
                "bbox": [float(row[4] or 0), float(row[5] or 0), float(row[6] or 0), float(row[7] or 0)],
                "confidence": row[8],
                "match_confidence": row[9],
                "status": row[10] or "unreviewed",
                "landmarks": _landmarks_from_json(row[11]),
            }
        )
    return faces


def list_unconfirmed_faces(conn: sqlite3.Connection) -> list[dict]:
    ensure_people_tables(conn)
    rows = conn.execute(
        """
        SELECT f.id, f.media_id, m.path, p.id, p.display_name, p.is_confirmed,
               f.bbox_left, f.bbox_top, f.bbox_width, f.bbox_height,
               f.confidence, f.match_confidence, f.status, f.landmarks_json
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        LEFT JOIN people p ON p.id = f.person_id
        WHERE COALESCE(f.ignored, 0) = 0
          AND COALESCE(f.status, 'unreviewed') != 'confirmed'
        ORDER BY LOWER(COALESCE(p.display_name, '')), f.match_confidence DESC, m.path
        """
    ).fetchall()
    faces: list[dict] = []
    for row in rows:
        path = row[2] or ""
        if not _is_people_supported_image_path(path):
            continue
        face_id = int(row[0])
        display_name = row[4] or f"Unnamed {row[3] or face_id}"
        faces.append(
            {
                "face_id": face_id,
                "media_id": int(row[1]),
                "path": path,
                "person_id": int(row[3] or 0),
                "display_name": display_name,
                "is_confirmed": bool(row[5]),
                "bbox": [float(row[6] or 0), float(row[7] or 0), float(row[8] or 0), float(row[9] or 0)],
                "confidence": row[10],
                "match_confidence": row[11],
                "status": row[12] or "unreviewed",
                "landmarks": _landmarks_from_json(row[13]),
            }
        )
    return faces


def list_prescanned_people_paths(
    conn: sqlite3.Connection,
    paths: Iterable[str],
    *,
    detection_engine: str = "insightface",
) -> set[str]:
    ensure_people_tables(conn)
    normalized_paths = [normalize_windows_path(path) for path in paths if str(path or "").strip()]
    if not normalized_paths:
        return set()
    placeholders = ", ".join("?" for _ in normalized_paths)
    params = [str(detection_engine or "insightface"), str(detection_engine or "insightface"), *normalized_paths]
    rows = conn.execute(
        f"""
        SELECT DISTINCT m.path
        FROM media_items m
        LEFT JOIN people_scan_state s
          ON s.media_id = m.id
         AND s.detection_engine = ?
        LEFT JOIN media_faces f
          ON f.media_id = m.id
         AND f.detection_engine = ?
        WHERE m.path IN ({placeholders})
          AND (s.media_id IS NOT NULL OR f.id IS NOT NULL)
        """
        ,
        params,
    ).fetchall()
    return {str(row[0] or "") for row in rows if str(row[0] or "").strip()}


def _embedding_from_json(raw: str | None) -> list[float]:
    try:
        values = json.loads(str(raw or "[]"))
        return [float(value) for value in values]
    except Exception:
        return []


def _landmarks_from_json(raw: str | None) -> list[list[float]]:
    try:
        values = json.loads(str(raw or "[]"))
        points: list[list[float]] = []
        for item in list(values or []):
            coords = [float(value) for value in list(item or [])[:2]]
            if len(coords) == 2:
                points.append(coords)
        return points
    except Exception:
        return []


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return float(dot / (left_norm * right_norm))


def _best_person_match(conn: sqlite3.Connection, embedding: list[float], threshold: float) -> tuple[int | None, float]:
    rows = conn.execute(
        """
        SELECT f.person_id, f.embedding_json, f.status, m.path
        FROM media_faces f
        JOIN media_items m ON m.id = f.media_id
        WHERE f.person_id IS NOT NULL
          AND f.embedding_json IS NOT NULL
          AND f.embedding_json != ''
          AND COALESCE(f.ignored, 0) = 0
          AND f.status IN ('unreviewed', 'suggested', 'confirmed')
        """
    ).fetchall()
    best_person_id: int | None = None
    best_score = 0.0
    scores: dict[int, list[tuple[float, bool]]] = {}
    for person_id, raw_embedding, status, path in rows:
        if not _is_people_supported_image_path(path or ""):
            continue
        candidate = _embedding_from_json(raw_embedding)
        score = _cosine_similarity(embedding, candidate)
        if score <= 0.0:
            continue
        scores.setdefault(int(person_id), []).append((score, str(status or "") == "confirmed"))
    for person_id, person_scores in scores.items():
        weighted_scores = [min(1.0, score * (1.04 if confirmed else 1.0)) for score, confirmed in person_scores]
        strongest = max(weighted_scores)
        top_scores = sorted(weighted_scores, reverse=True)[:5]
        averaged = sum(top_scores) / max(1, len(top_scores))
        confirmed_scores = [score for score, confirmed in person_scores if confirmed]
        confirmed_best = max(confirmed_scores) if confirmed_scores else 0.0
        score = max(strongest, averaged, min(1.0, confirmed_best * 1.06))
        if score > best_score:
            best_score = score
            best_person_id = person_id
    if best_person_id is None or best_score < threshold:
        return None, best_score
    return best_person_id, best_score


def _create_unnamed_person(conn: sqlite3.Connection) -> int:
    now = _utc_now_iso()
    row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM people").fetchone()
    next_id = int(row[0] or 1)
    cur = conn.execute(
        """
        INSERT INTO people(name, display_name, is_confirmed, created_at_utc, updated_at_utc)
        VALUES (NULL, ?, 0, ?, ?)
        """,
        (f"Unnamed {next_id}", now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def replace_detected_faces(
    conn: sqlite3.Connection,
    path: str,
    faces: list[dict],
    *,
    detection_engine: str = "insightface",
    recognition_model: str = "buffalo_l",
    match_threshold: float = 0.45,
) -> int:
    ensure_people_tables(conn)
    if not _is_people_supported_image_path(path):
        return 0
    from app.mediamanager.db.media_repo import get_media_by_path

    media = get_media_by_path(conn, path)
    if not media:
        raise ValueError("media item not found")
    media_id = int(media["id"])
    now = _utc_now_iso()
    conn.execute(
        """
        DELETE FROM media_faces
        WHERE media_id = ?
          AND detection_engine = ?
          AND status IN ('unreviewed', 'suggested', 'rejected')
        """,
        (media_id, detection_engine),
    )
    inserted = 0
    for face in faces:
        embedding = [float(value) for value in list(face.get("embedding") or [])]
        bbox = [float(value) for value in list(face.get("bbox") or [])[:4]]
        landmarks = [
            [float(point[0]), float(point[1])]
            for point in list(face.get("landmarks") or [])
            if isinstance(point, (list, tuple)) and len(point) >= 2
        ]
        if len(bbox) != 4 or not embedding:
            continue
        person_id, match_confidence = _best_person_match(conn, embedding, float(match_threshold))
        if person_id is None:
            person_id = _create_unnamed_person(conn)
            match_confidence = None
        status = "suggested" if match_confidence is not None else "unreviewed"
        conn.execute(
            """
            INSERT INTO media_faces(
                media_id, person_id, detection_engine, recognition_model, embedding_json, landmarks_json,
                bbox_left, bbox_top, bbox_width, bbox_height, confidence, match_confidence,
                status, ignored, created_at_utc, updated_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                media_id,
                int(person_id),
                detection_engine,
                recognition_model,
                json.dumps(embedding, separators=(",", ":")),
                json.dumps(landmarks, separators=(",", ":")),
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3],
                float(face.get("confidence") or 0.0),
                match_confidence,
                status,
                now,
                now,
            ),
        )
        inserted += 1
    conn.execute(
        """
        INSERT INTO people_scan_state(media_id, detection_engine, face_count, scanned_at_utc)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(media_id, detection_engine)
        DO UPDATE SET face_count = excluded.face_count, scanned_at_utc = excluded.scanned_at_utc
        """,
        (media_id, detection_engine, inserted, now),
    )
    conn.commit()
    return inserted


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
