from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable, List


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_tag_name(name: str) -> str:
    return str(name or "").strip()


def _has_display_case(name: str) -> bool:
    return any(char.isupper() for char in str(name or ""))


def _preferred_tag_name(existing: str, incoming: str) -> str:
    existing_clean = _clean_tag_name(existing)
    incoming_clean = _clean_tag_name(incoming)
    if not existing_clean:
        return incoming_clean
    if not incoming_clean:
        return existing_clean
    if existing_clean.casefold() != incoming_clean.casefold():
        return existing_clean
    if _has_display_case(incoming_clean) and not _has_display_case(existing_clean):
        return incoming_clean
    return existing_clean


def _dedupe_tag_names(tag_names: Iterable[str]) -> list[str]:
    by_key: dict[str, str] = {}
    for raw in tag_names:
        clean = _clean_tag_name(raw)
        if not clean:
            continue
        key = clean.casefold()
        by_key[key] = _preferred_tag_name(by_key.get(key, ""), clean)
    return [by_key[key] for key in sorted(by_key)]


def _merge_tag_rows(conn: sqlite3.Connection, keep_id: int, duplicate_ids: Iterable[int]) -> None:
    for duplicate_id in [int(tag_id) for tag_id in duplicate_ids if int(tag_id) != int(keep_id)]:
        conn.execute(
            """
            INSERT OR IGNORE INTO media_tags(media_id, tag_id, created_at_utc)
            SELECT media_id, ?, created_at_utc
            FROM media_tags
            WHERE tag_id = ?
            """,
            (int(keep_id), duplicate_id),
        )
        conn.execute("DELETE FROM media_tags WHERE tag_id = ?", (duplicate_id,))
        conn.execute(
            """
            INSERT OR IGNORE INTO tag_list_items(tag_list_id, tag_id, sort_order, created_at_utc)
            SELECT tag_list_id, ?, sort_order, created_at_utc
            FROM tag_list_items
            WHERE tag_id = ?
            """,
            (int(keep_id), duplicate_id),
        )
        conn.execute("DELETE FROM tag_list_items WHERE tag_id = ?", (duplicate_id,))
        conn.execute("DELETE FROM tags WHERE id = ?", (duplicate_id,))


def dedupe_tags_case_insensitive(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, name FROM tags ORDER BY LOWER(name), id").fetchall()
    grouped: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        name = _clean_tag_name(str(row[1] or ""))
        if not name:
            continue
        grouped.setdefault(name.casefold(), []).append((int(row[0]), name))

    changed = False
    for matches in grouped.values():
        if len(matches) <= 1:
            continue
        preferred = ""
        for _, name in matches:
            preferred = _preferred_tag_name(preferred, name)
        keep_id = next((tag_id for tag_id, name in matches if name == preferred), matches[0][0])
        _merge_tag_rows(conn, keep_id, [tag_id for tag_id, _ in matches if tag_id != keep_id])
        current = next((name for tag_id, name in matches if tag_id == keep_id), "")
        if preferred and preferred != current:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (preferred, keep_id))
        changed = True
    if changed:
        conn.commit()


def get_or_create_tag(conn: sqlite3.Connection, name: str, category: str | None = None) -> int:
    clean = _clean_tag_name(name)
    if not clean:
        raise ValueError("tag name is required")

    rows = conn.execute(
        """
        SELECT id, name
        FROM tags
        WHERE name = ? OR LOWER(name) = LOWER(?)
        ORDER BY
            CASE
                WHEN name = ? THEN 0
                WHEN name <> LOWER(name) THEN 1
                ELSE 2
            END,
            id
        """,
        (clean, clean, clean),
    ).fetchall()
    if rows:
        tag_id = int(rows[0][0])
        current_name = str(rows[0][1] or "")
        _merge_tag_rows(conn, tag_id, [int(row[0]) for row in rows[1:]])
        preferred_name = _preferred_tag_name(current_name, clean)
        if preferred_name != current_name:
            try:
                conn.execute("UPDATE tags SET name = ? WHERE id = ?", (preferred_name, tag_id))
            except sqlite3.IntegrityError:
                exact = conn.execute("SELECT id FROM tags WHERE name = ?", (preferred_name,)).fetchone()
                if exact:
                    exact_id = int(exact[0])
                    _merge_tag_rows(conn, exact_id, [tag_id])
                    tag_id = exact_id
        if category is not None:
            conn.execute("UPDATE tags SET category = COALESCE(category, ?) WHERE id = ?", (category, tag_id))
        conn.commit()
        return tag_id

    now = _utc_now_iso()
    try:
        conn.execute(
            """
            INSERT INTO tags(name, category, created_at_utc)
            VALUES (?, ?, ?)
            """,
            (clean, category, now),
        )
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (clean,)).fetchone()
        if row:
            return int(row[0])
        raise
    row = conn.execute("SELECT id FROM tags WHERE name = ?", (clean,)).fetchone()
    if not row:
        raise RuntimeError(f"failed to create or load tag: {clean}")
    conn.commit()
    return int(row[0])


def attach_tags(conn: sqlite3.Connection, media_id: int, tag_names: Iterable[str]) -> None:
    now = _utc_now_iso()
    for tag_name in _dedupe_tag_names(tag_names):
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
    dedupe_tags_case_insensitive(conn)
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
    return _dedupe_tag_names([r[0] for r in rows])


def set_media_tags(conn: sqlite3.Connection, media_id: int, tag_names: Iterable[str]) -> None:
    """Clear existing tags and set the new ones."""
    conn.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))
    attach_tags(conn, media_id, tag_names)
    conn.commit()


def clear_all_media_tags(conn: sqlite3.Connection, media_id: int) -> None:
    """Remove all tags from a media item."""
    conn.execute("DELETE FROM media_tags WHERE media_id = ?", (media_id,))
    conn.commit()
