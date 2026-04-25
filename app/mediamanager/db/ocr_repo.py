from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any


OCR_SOURCE_RANK = {
    "windows_ocr_legacy": 10,
    "paddle_fast": 30,
    "paddle_accurate": 40,
    "gemma4": 50,
    "user": 100,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def ensure_ocr_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS media_ocr_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          media_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          text TEXT NOT NULL,
          confidence REAL,
          engine_version TEXT,
          preprocess_profile TEXT,
          run_id TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          is_user_selected INTEGER NOT NULL DEFAULT 0,
          created_at_utc TEXT NOT NULL,
          FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_media_ocr_results_media ON media_ocr_results(media_id, created_at_utc);
        CREATE INDEX IF NOT EXISTS idx_media_ocr_results_source ON media_ocr_results(source);

        CREATE TABLE IF NOT EXISTS media_ocr_winners (
          media_id INTEGER PRIMARY KEY,
          result_id INTEGER,
          source TEXT NOT NULL,
          text TEXT NOT NULL,
          selected_by TEXT NOT NULL DEFAULT 'rules',
          updated_at_utc TEXT NOT NULL,
          FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE,
          FOREIGN KEY(result_id) REFERENCES media_ocr_results(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS media_ocr_review_items (
          media_id INTEGER PRIMARY KEY,
          reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'open',
          created_at_utc TEXT NOT NULL,
          updated_at_utc TEXT NOT NULL,
          FOREIGN KEY(media_id) REFERENCES media_items(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_media_ocr_review_status ON media_ocr_review_items(status, updated_at_utc);
        """
    )


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _token_set(text: str) -> set[str]:
    return {item.casefold() for item in re.findall(r"[A-Za-z0-9]+", str(text or "")) if item.strip()}


def _similarity(left: str, right: str) -> float:
    a = _token_set(left)
    b = _token_set(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


def add_ocr_result(
    conn: sqlite3.Connection,
    media_id: int,
    *,
    source: str,
    text: str,
    confidence: float | None = None,
    engine_version: str = "",
    preprocess_profile: str = "",
    run_id: str = "",
    metadata: dict[str, Any] | None = None,
    select_as_winner: bool = False,
    selected_by: str = "rules",
) -> int:
    ensure_ocr_tables(conn)
    clean_text = str(text or "").strip()
    now = _utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO media_ocr_results (
          media_id, source, text, confidence, engine_version, preprocess_profile,
          run_id, metadata_json, is_user_selected, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(media_id),
            str(source or "").strip() or "unknown",
            clean_text,
            None if confidence is None else float(confidence),
            str(engine_version or ""),
            str(preprocess_profile or ""),
            str(run_id or ""),
            _json_dumps(metadata),
            1 if select_as_winner or str(source).strip() == "user" else 0,
            now,
        ),
    )
    result_id = int(cursor.lastrowid)
    if select_as_winner or str(source).strip() == "user":
        set_ocr_winner(conn, int(media_id), result_id, selected_by=selected_by)
    else:
        resolve_ocr_winner(conn, int(media_id))
    conn.commit()
    return result_id


def get_ocr_results(conn: sqlite3.Connection, media_id: int) -> list[dict[str, Any]]:
    ensure_ocr_tables(conn)
    rows = conn.execute(
        """
        SELECT id, media_id, source, text, confidence, engine_version, preprocess_profile,
               run_id, metadata_json, is_user_selected, created_at_utc
        FROM media_ocr_results
        WHERE media_id = ?
        ORDER BY created_at_utc DESC, id DESC
        """,
        (int(media_id),),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            metadata = json.loads(row[8] or "{}")
        except Exception:
            metadata = {}
        out.append(
            {
                "id": row[0],
                "media_id": row[1],
                "source": row[2],
                "text": row[3] or "",
                "confidence": row[4],
                "engine_version": row[5] or "",
                "preprocess_profile": row[6] or "",
                "run_id": row[7] or "",
                "metadata": metadata,
                "is_user_selected": bool(row[9]),
                "created_at_utc": row[10] or "",
            }
        )
    return out


def get_ocr_winner(conn: sqlite3.Connection, media_id: int) -> dict[str, Any] | None:
    ensure_ocr_tables(conn)
    row = conn.execute(
        """
        SELECT media_id, result_id, source, text, selected_by, updated_at_utc
        FROM media_ocr_winners
        WHERE media_id = ?
        """,
        (int(media_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "media_id": row[0],
        "result_id": row[1],
        "source": row[2],
        "text": row[3] or "",
        "selected_by": row[4] or "",
        "updated_at_utc": row[5] or "",
    }


def set_ocr_winner(conn: sqlite3.Connection, media_id: int, result_id: int, *, selected_by: str = "user") -> None:
    ensure_ocr_tables(conn)
    result = conn.execute(
        "SELECT id, source, text FROM media_ocr_results WHERE id = ? AND media_id = ?",
        (int(result_id), int(media_id)),
    ).fetchone()
    if not result:
        raise KeyError("OCR result was not found.")
    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO media_ocr_winners (media_id, result_id, source, text, selected_by, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          result_id=excluded.result_id,
          source=excluded.source,
          text=excluded.text,
          selected_by=excluded.selected_by,
          updated_at_utc=excluded.updated_at_utc
        """,
        (int(media_id), int(result[0]), result[1], result[2] or "", str(selected_by or "user"), now),
    )
    conn.execute(
        "UPDATE media_ocr_results SET is_user_selected = CASE WHEN id = ? THEN 1 ELSE 0 END WHERE media_id = ?",
        (int(result_id), int(media_id)),
    )
    conn.execute(
        "UPDATE media_items SET detected_text = ?, user_confirmed_text_detected = ?, updated_at_utc = ? WHERE id = ?",
        (str(result[2] or "").strip(), 1 if str(result[2] or "").strip() else None, now, int(media_id)),
    )
    conn.execute(
        "UPDATE media_ocr_review_items SET status = 'resolved', updated_at_utc = ? WHERE media_id = ?",
        (now, int(media_id)),
    )
    conn.commit()


def resolve_ocr_winner(conn: sqlite3.Connection, media_id: int) -> dict[str, Any] | None:
    ensure_ocr_tables(conn)
    existing = get_ocr_winner(conn, media_id)
    if existing and existing.get("selected_by") == "user":
        _maybe_flag_review(conn, media_id)
        return existing
    results = [item for item in get_ocr_results(conn, media_id) if str(item.get("text") or "").strip()]
    if not results:
        return None
    results.sort(
        key=lambda item: (
            OCR_SOURCE_RANK.get(str(item.get("source") or ""), 0),
            0.0 if item.get("confidence") is None else float(item.get("confidence") or 0.0),
            str(item.get("created_at_utc") or ""),
            int(item.get("id") or 0),
        ),
        reverse=True,
    )
    best = results[0]
    set_ocr_winner(conn, int(media_id), int(best["id"]), selected_by="rules")
    _maybe_flag_review(conn, media_id)
    return get_ocr_winner(conn, media_id)


def _maybe_flag_review(conn: sqlite3.Connection, media_id: int) -> None:
    results = [item for item in get_ocr_results(conn, media_id) if str(item.get("text") or "").strip()]
    if len(results) < 2:
        return
    latest_by_source: dict[str, dict[str, Any]] = {}
    for item in results:
        latest_by_source.setdefault(str(item.get("source") or ""), item)
    distinct_texts = {_normalize_for_compare(item["text"]) for item in latest_by_source.values() if _normalize_for_compare(item["text"])}
    low_conf = [
        item for item in latest_by_source.values()
        if item.get("confidence") is not None and float(item.get("confidence") or 0.0) < 0.55
    ]
    conflict = False
    values = list(latest_by_source.values())
    for idx, left in enumerate(values):
        for right in values[idx + 1:]:
            if _similarity(left["text"], right["text"]) < 0.55:
                conflict = True
                break
        if conflict:
            break
    if len(distinct_texts) <= 1 and not low_conf and not conflict:
        return
    reason_bits = []
    if conflict or len(distinct_texts) > 1:
        reason_bits.append("conflicting OCR results")
    if low_conf:
        reason_bits.append("low confidence OCR result")
    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO media_ocr_review_items (media_id, reason, status, created_at_utc, updated_at_utc)
        VALUES (?, ?, 'open', ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          reason=excluded.reason,
          status='open',
          updated_at_utc=excluded.updated_at_utc
        """,
        (int(media_id), ", ".join(reason_bits) or "review needed", now, now),
    )


def list_open_ocr_reviews(conn: sqlite3.Connection, limit: int = 500) -> list[dict[str, Any]]:
    ensure_ocr_tables(conn)
    rows = conn.execute(
        """
        SELECT r.media_id, r.reason, r.status, r.updated_at_utc, m.path, m.detected_text
        FROM media_ocr_review_items r
        JOIN media_items m ON m.id = r.media_id
        WHERE r.status = 'open'
        ORDER BY r.updated_at_utc DESC
        LIMIT ?
        """,
        (max(1, int(limit)),),
    ).fetchall()
    return [
        {
            "media_id": row[0],
            "reason": row[1] or "",
            "status": row[2] or "",
            "updated_at_utc": row[3] or "",
            "path": row[4] or "",
            "detected_text": row[5] or "",
            "results": get_ocr_results(conn, int(row[0])),
            "winner": get_ocr_winner(conn, int(row[0])),
        }
        for row in rows
    ]
