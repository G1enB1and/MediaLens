from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(str(value or ""))
    except Exception:
        return fallback


def _preview_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _append_embedded_metadata_lines(lines: list[str], key: str, value: Any, *, depth: int = 0, max_lines: int = 120) -> None:
    if len(lines) >= max_lines or depth > 6 or value in (None, "", [], {}):
        return
    label = str(key or "").strip()
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            next_key = f"{label}.{child_key}" if label else str(child_key)
            _append_embedded_metadata_lines(lines, next_key, child_value, depth=depth + 1, max_lines=max_lines)
            if len(lines) >= max_lines:
                return
        return
    if isinstance(value, list):
        if value and all(not isinstance(item, (dict, list, tuple, set)) for item in value):
            rendered = " | ".join(_preview_text(item, 500) for item in value if _preview_text(item, 500))
            if rendered:
                lines.append(f"{label}: {rendered}" if label else rendered)
            return
        for index, item in enumerate(value, start=1):
            next_key = f"{label}[{index}]" if label else f"[{index}]"
            _append_embedded_metadata_lines(lines, next_key, item, depth=depth + 1, max_lines=max_lines)
            if len(lines) >= max_lines:
                return
        return
    rendered = _preview_text(value, 700)
    if rendered:
        lines.append(f"{label}: {rendered}" if label else rendered)


def build_embedded_metadata_summary(embedded_metadata: dict[str, Any] | None) -> str:
    if not embedded_metadata:
        return ""
    lines: list[str] = []
    _append_embedded_metadata_lines(lines, "", embedded_metadata)
    return "\n".join(lines[:120])


def upsert_media_metadata(
    conn: sqlite3.Connection,
    media_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    embedded_tags: Optional[str] = None,
    embedded_comments: Optional[str] = None,
    ai_prompt: Optional[str] = None,
    ai_negative_prompt: Optional[str] = None,
    ai_params: Optional[str] = None,
    embedded_metadata_parser_version: Optional[str] = None,
    embedded_metadata_json: Optional[str] = None,
    embedded_metadata_summary: Optional[str] = None,
) -> None:
    now = _utc_now_iso()
    existing = get_media_metadata(conn, media_id) or {}
    conn.execute(
        """
        INSERT INTO media_metadata (
          media_id, title, description, notes, embedded_tags, embedded_comments,
          ai_prompt, ai_negative_prompt, ai_params, embedded_metadata_parser_version,
          embedded_metadata_json, embedded_metadata_summary, updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          title=excluded.title,
          description=excluded.description,
          notes=excluded.notes,
          embedded_tags=excluded.embedded_tags,
          embedded_comments=excluded.embedded_comments,
          ai_prompt=excluded.ai_prompt,
          ai_negative_prompt=excluded.ai_negative_prompt,
          ai_params=excluded.ai_params,
          embedded_metadata_parser_version=excluded.embedded_metadata_parser_version,
          embedded_metadata_json=excluded.embedded_metadata_json,
          embedded_metadata_summary=excluded.embedded_metadata_summary,
          updated_at_utc=excluded.updated_at_utc
        """,
        (
            media_id,
            title,
            description,
            notes,
            embedded_tags,
            embedded_comments,
            ai_prompt,
            ai_negative_prompt,
            ai_params,
            embedded_metadata_parser_version if embedded_metadata_parser_version is not None else existing.get("embedded_metadata_parser_version"),
            embedded_metadata_json if embedded_metadata_json is not None else _json_dumps(existing.get("embedded_metadata") or {}),
            embedded_metadata_summary if embedded_metadata_summary is not None else existing.get("embedded_metadata_summary"),
            now,
        ),
    )
    conn.commit()


def upsert_media_embedded_metadata(
    conn: sqlite3.Connection,
    media_id: int,
    embedded_metadata: dict[str, Any] | None,
    *,
    parser_version: str | None = None,
) -> None:
    now = _utc_now_iso()
    payload = embedded_metadata or {}
    summary = build_embedded_metadata_summary(payload)
    conn.execute(
        """
        INSERT INTO media_metadata (media_id, embedded_metadata_parser_version, embedded_metadata_json, embedded_metadata_summary, updated_at_utc)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          embedded_metadata_parser_version=excluded.embedded_metadata_parser_version,
          embedded_metadata_json=excluded.embedded_metadata_json,
          embedded_metadata_summary=excluded.embedded_metadata_summary,
          updated_at_utc=excluded.updated_at_utc
        """,
        (media_id, parser_version, _json_dumps(payload), summary, now),
    )
    conn.commit()


def get_media_metadata(conn: sqlite3.Connection, media_id: int) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT media_id, title, description, notes, embedded_tags, embedded_comments,
               ai_prompt, ai_negative_prompt, ai_params, embedded_metadata_parser_version,
               embedded_metadata_json, embedded_metadata_summary, updated_at_utc
        FROM media_metadata
        WHERE media_id = ?
        """,
        (media_id,),
    ).fetchone()
    if not row:
        return None
    embedded_metadata = _json_loads(row[10], {})
    return {
        "media_id": row[0],
        "title": row[1],
        "description": row[2],
        "notes": row[3],
        "embedded_tags": row[4],
        "embedded_comments": row[5],
        "ai_prompt": row[6],
        "ai_negative_prompt": row[7],
        "ai_params": row[8],
        "embedded_metadata_parser_version": row[9],
        "embedded_metadata": embedded_metadata,
        "embedded_metadata_summary": row[11] or build_embedded_metadata_summary(embedded_metadata),
        "updated_at_utc": row[12],
    }
