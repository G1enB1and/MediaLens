from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from app.mediamanager.db.ai_metadata_repo import replace_media_ai_metadata
from app.mediamanager.metadata.models import InspectionResult
from app.mediamanager.metadata.service import inspect_file


INSPECTABLE_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def should_inspect_media(path: str | Path, media_type: str | None = None) -> bool:
    target = Path(path)
    if media_type and media_type != "image":
        return False
    return target.suffix.lower() in INSPECTABLE_IMAGE_EXTS and target.exists()


def inspect_and_persist_file(
    conn: sqlite3.Connection,
    media_id: int,
    path: str | Path,
) -> InspectionResult:
    inspection = inspect_file(path)
    replace_media_ai_metadata(conn, media_id, inspection)
    return inspection


def inspect_and_persist_if_supported(
    conn: sqlite3.Connection,
    media_id: int,
    path: str | Path,
    media_type: str | None = None,
) -> InspectionResult | None:
    if not should_inspect_media(path, media_type):
        return None
    return inspect_and_persist_file(conn, media_id, path)


def backfill_ai_metadata_for_media_rows(
    conn: sqlite3.Connection,
    media_rows: Iterable[dict],
) -> list[dict]:
    results: list[dict] = []
    for row in media_rows:
        media_id = int(row["id"])
        path = Path(str(row["path"]))
        if not path.exists():
            results.append({"media_id": media_id, "path": str(path), "status": "missing"})
            continue
        try:
            inspection = inspect_and_persist_file(conn, media_id, path)
            results.append(
                {
                    "media_id": media_id,
                    "path": str(path),
                    "status": "ok",
                    "is_ai_detected": inspection.canonical.is_ai_detected,
                    "source_formats": inspection.canonical.source_formats,
                    "tool_name_found": inspection.canonical.tool_name_found,
                    "tool_name_inferred": inspection.canonical.tool_name_inferred,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "media_id": media_id,
                    "path": str(path),
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results
