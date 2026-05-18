from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.mediamanager.db.ai_metadata_repo import get_media_ai_metadata, upsert_media_ai_selected_fields
from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates, update_media_detected_text, update_user_confirmed_text_detected
from app.mediamanager.db.metadata_repo import get_media_metadata, upsert_media_metadata
from app.mediamanager.db.tags_repo import list_media_tags, set_media_tags


METADATA_KEYS = (
    "title",
    "description",
    "notes",
    "embedded_tags",
    "embedded_comments",
    "ai_prompt",
    "ai_negative_prompt",
    "ai_params",
)

AI_KEYS = (
    "is_ai_detected",
    "is_ai_confidence",
    "user_confirmed_ai",
    "tool_name_found",
    "tool_name_inferred",
    "tool_name_confidence",
    "source_formats",
    "ai_prompt",
    "ai_negative_prompt",
    "description",
    "model_name",
    "checkpoint_name",
    "sampler",
    "scheduler",
    "cfg_scale",
    "steps",
    "seed",
    "upscaler",
    "denoise_strength",
    "metadata_families_detected",
    "ai_detection_reasons",
)


def _clean_dict(data: dict | None, keys: tuple[str, ...]) -> dict:
    source = data or {}
    return {key: source.get(key) for key in keys}


def _media_core_snapshot(media: dict | None) -> dict:
    if not media:
        return {}
    return {
        "exif_date_taken": media.get("exif_date_taken"),
        "metadata_date": media.get("metadata_date"),
        "detected_text": media.get("detected_text"),
        "user_confirmed_text_detected": media.get("user_confirmed_text_detected"),
        "is_hidden": media.get("is_hidden"),
        "width": media.get("width"),
        "height": media.get("height"),
    }


def snapshot_edit_state(conn, path: str) -> dict:
    media = get_media_by_path(conn, path)
    if not media:
        return {"path": path, "exists_in_db": False}
    media_id = int(media["id"])
    return {
        "path": path,
        "exists_in_db": True,
        "media": _media_core_snapshot(media),
        "metadata": _clean_dict(get_media_metadata(conn, media_id), METADATA_KEYS),
        "ai": _clean_dict(get_media_ai_metadata(conn, media_id), AI_KEYS),
        "tags": list_media_tags(conn, media_id),
    }


def snapshots_equal(left: dict, right: dict) -> bool:
    return json.dumps(left, sort_keys=True, ensure_ascii=False, default=str) == json.dumps(right, sort_keys=True, ensure_ascii=False, default=str)


def apply_edit_state(conn, snapshot: dict) -> bool:
    path = str((snapshot or {}).get("path") or "")
    if not path:
        return False
    media = get_media_by_path(conn, path)
    if not media:
        return False
    media_id = int(media["id"])
    metadata = dict(snapshot.get("metadata") or {})
    upsert_media_metadata(
        conn,
        media_id,
        metadata.get("title"),
        metadata.get("description"),
        metadata.get("notes"),
        metadata.get("embedded_tags"),
        metadata.get("embedded_comments"),
        metadata.get("ai_prompt"),
        metadata.get("ai_negative_prompt"),
        metadata.get("ai_params"),
    )
    media_state = dict(snapshot.get("media") or {})
    update_media_dates(
        conn,
        media_id,
        exif_date_taken=media_state.get("exif_date_taken"),
        metadata_date=media_state.get("metadata_date"),
    )
    update_media_detected_text(conn, media_id, media_state.get("detected_text") or "")
    update_user_confirmed_text_detected(conn, media_id, media_state.get("user_confirmed_text_detected"))
    set_media_tags(conn, media_id, snapshot.get("tags") or [])
    ai = dict(snapshot.get("ai") or {})
    if ai:
        upsert_media_ai_selected_fields(
            conn,
            media_id,
            is_ai_detected=ai.get("is_ai_detected"),
            is_ai_confidence=ai.get("is_ai_confidence"),
            user_confirmed_ai=ai.get("user_confirmed_ai"),
            tool_name_found=ai.get("tool_name_found"),
            tool_name_inferred=ai.get("tool_name_inferred"),
            tool_name_confidence=ai.get("tool_name_confidence"),
            source_formats=ai.get("source_formats"),
            ai_prompt=ai.get("ai_prompt"),
            ai_negative_prompt=ai.get("ai_negative_prompt"),
            description=ai.get("description"),
            model_name=ai.get("model_name"),
            checkpoint_name=ai.get("checkpoint_name"),
            sampler=ai.get("sampler"),
            scheduler=ai.get("scheduler"),
            cfg_scale=ai.get("cfg_scale"),
            steps=ai.get("steps"),
            seed=ai.get("seed"),
            upscaler=ai.get("upscaler"),
            denoise_strength=ai.get("denoise_strength"),
            metadata_families_detected=ai.get("metadata_families_detected"),
            ai_detection_reasons=ai.get("ai_detection_reasons"),
        )
    return True


def changed_field_labels(old: dict, new: dict) -> list[str]:
    labels: list[str] = []
    if (old.get("tags") or []) != (new.get("tags") or []):
        labels.append("tags")
    for key, label in (
        ("description", "description"),
        ("notes", "notes"),
        ("ai_prompt", "AI prompt"),
        ("ai_negative_prompt", "negative prompt"),
        ("ai_params", "AI parameters"),
    ):
        if (old.get("metadata") or {}).get(key) != (new.get("metadata") or {}).get(key):
            labels.append(label)
    for key, label in (
        ("detected_text", "OCR text"),
        ("user_confirmed_text_detected", "text detected"),
        ("exif_date_taken", "EXIF date"),
        ("metadata_date", "metadata date"),
    ):
        if (old.get("media") or {}).get(key) != (new.get("media") or {}).get(key):
            labels.append(label)
    if (old.get("ai") or {}) != (new.get("ai") or {}):
        labels.append("AI metadata")
    return labels


def history_item_for_edit(path: str, old: dict, new: dict, labels: list[str]) -> dict:
    return {
        "item_type": "file" if Path(path).suffix else "item",
        "old_path": path,
        "new_path": path,
        "result": "success",
        "current_state": "applied",
        "last_change_source": "original_action",
        "notes": ", ".join(labels[:6]),
        "metadata": {"old": old, "new": new},
    }

