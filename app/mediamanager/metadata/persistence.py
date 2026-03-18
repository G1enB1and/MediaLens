from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.mediamanager.db.ai_metadata_repo import replace_media_ai_metadata
from app.mediamanager.db.media_repo import update_media_dates
from app.mediamanager.metadata.models import InspectionResult
from app.mediamanager.metadata.service import inspect_file


INSPECTABLE_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}
DATE_KEYWORDS = (
    "datetimeoriginal",
    "datetimedigitized",
    "datetimecreated",
    "createdate",
    "datecreated",
    "metadatadate",
    "datetime",
    "date",
)
DATE_PATTERN = re.compile(
    r"([0-9]{4}[-:][0-9]{2}[-:][0-9]{2}(?:[T\s][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.\d+)?)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)",
    re.IGNORECASE,
)


def should_inspect_media(path: str | Path, media_type: str | None = None) -> bool:
    target = Path(path)
    if media_type and media_type != "image":
        return False
    return target.suffix.lower() in INSPECTABLE_IMAGE_EXTS and target.exists()


def _normalize_date_string(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().strip("\x00")
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    for parser in (
        lambda raw: datetime.fromisoformat(raw),
        lambda raw: datetime.strptime(raw, "%Y:%m:%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y:%m:%d"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d"),
    ):
        try:
            parsed = parser(text)
            if parsed.tzinfo is None:
                return parsed.replace(microsecond=0).isoformat(sep="T")
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except Exception:
            continue
    return None


def _extract_first_date(text: str) -> str | None:
    if not text:
        return None
    match = DATE_PATTERN.search(str(text))
    if not match:
        return None
    return _normalize_date_string(match.group(1))


def _extract_exif_date(inspection: InspectionResult) -> str | None:
    raw = inspection.raw
    preferred = (
        "datetimeoriginal",
        "createdate",
        "datetimedigitized",
        "datetime",
    )
    normalized = {(str(key).lower()): value for key, value in (raw.exif or {}).items()}
    for target in preferred:
        for key, value in normalized.items():
            if target in key:
                parsed = _normalize_date_string(value)
                if parsed:
                    return parsed
    return None


def _extract_metadata_date(inspection: InspectionResult) -> str | None:
    raw = inspection.raw

    for packet in raw.xmp_packets or []:
        parsed = _extract_first_date(packet)
        if parsed:
            return parsed

    for entry in raw.png_text_entries or []:
        key = str(entry.keyword or "").lower()
        if any(token in key for token in DATE_KEYWORDS):
            parsed = _extract_first_date(entry.text)
            if parsed:
                return parsed

    for mapping in (raw.pillow_info or {}, raw.iptc or {}):
        for key, value in mapping.items():
            key_text = str(key).lower()
            if any(token in key_text for token in DATE_KEYWORDS):
                parsed = _normalize_date_string(value) or _extract_first_date(str(value))
                if parsed:
                    return parsed

    for parsed in inspection.parsed:
        for key, value in (parsed.normalized or {}).items():
            key_text = str(key).lower()
            if "date" not in key_text and "time" not in key_text:
                continue
            normalized = _normalize_date_string(value) or _extract_first_date(str(value))
            if normalized:
                return normalized

    return None


def inspect_and_persist_file(
    conn: sqlite3.Connection,
    media_id: int,
    path: str | Path,
) -> InspectionResult:
    inspection = inspect_file(path)
    replace_media_ai_metadata(conn, media_id, inspection)
    update_media_dates(
        conn,
        media_id,
        exif_date_taken=_extract_exif_date(inspection),
        metadata_date=_extract_metadata_date(inspection),
    )
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
