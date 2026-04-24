from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *

def _load_media_metadata_payload(conn, path: str, log_fn=None) -> dict:
    image_exts = IMAGE_EXTS
    from app.mediamanager.db.media_repo import add_media_item, get_media_by_path
    from app.mediamanager.db.ai_metadata_repo import (
        NORMALIZED_SCHEMA_VERSION,
        PARSER_VERSION,
        build_media_ai_ui_fields,
        get_media_ai_metadata,
        summarize_media_ai_metadata,
        summarize_media_ai_tool_metadata,
    )
    from app.mediamanager.db.metadata_repo import get_media_metadata
    from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
    from app.mediamanager.db.tags_repo import list_media_tags

    def _log(message: str) -> None:
        if not log_fn:
            return
        try:
            log_fn(message)
        except Exception:
            pass

    try:
        media = get_media_by_path(conn, path)
        if not media:
            media_path = Path(path)
            if not media_path.exists():
                return {}
            media_type = "image" if media_path.suffix.lower() in image_exts else "video"
            add_media_item(conn, path, media_type)
            media = get_media_by_path(conn, path)
            if not media:
                return {}

        media_path = Path(path)
        if media_path.exists():
            try:
                stat = media_path.stat()
                if not media.get("file_created_time"):
                    media["file_created_time"] = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).replace(microsecond=0).isoformat()
                if not media.get("modified_time"):
                    media["modified_time"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                if not media.get("original_file_date"):
                    values = [
                        str(value).strip()
                        for value in (media.get("file_created_time"), media.get("modified_time"))
                        if str(value or "").strip()
                    ]
                    media["original_file_date"] = min(values) if values else ""
            except Exception:
                pass
            if media.get("media_type") == "image" and media_path.suffix.lower() in image_exts and media_path.suffix.lower() != ".svg":
                display_size = _image_size_with_svg_support(media_path)
                if display_size.isValid():
                    display_width, display_height = int(display_size.width()), int(display_size.height())
                    if int(media.get("width") or 0) != display_width or int(media.get("height") or 0) != display_height:
                        media["width"] = display_width
                        media["height"] = display_height
                        try:
                            conn.execute(
                                "UPDATE media_items SET width = ?, height = ? WHERE id = ?",
                                (display_width, display_height, int(media["id"])),
                            )
                            conn.commit()
                        except Exception:
                            pass

        payload = {
            "title": "",
            "description": "",
            "notes": "",
            "embedded_tags": "",
            "embedded_comments": "",
            "embedded_metadata_summary": "",
            "ai_prompt": "",
            "ai_negative_prompt": "",
            "ai_params": "",
            "ai_tool_summary": "",
            "tags": [],
            "has_metadata": False,
            "media_type": media.get("media_type") or "",
            "width": media.get("width"),
            "height": media.get("height"),
            "duration_ms": media.get("duration_ms"),
            "exif_date_taken": media.get("exif_date_taken") or "",
            "metadata_date": media.get("metadata_date") or "",
            "original_file_date": media.get("original_file_date") or "",
            "file_created_time": media.get("file_created_time") or "",
            "modified_time": media.get("modified_time") or "",
            "text_likely": media.get("text_likely"),
            "text_detected": media.get("effective_text_detected"),
            "user_confirmed_text_detected": media.get("user_confirmed_text_detected"),
            "effective_text_detected": media.get("effective_text_detected"),
            "detected_text": media.get("detected_text") or "",
        }

        meta: dict = {}
        ai_meta: dict = {}
        ai_ui: dict = {}
        try:
            meta = get_media_metadata(conn, media["id"]) or {}
            ai_meta = get_media_ai_metadata(conn, media["id"]) or {}
            needs_reinspect = (
                (ai_meta and (
                    ai_meta.get("parser_version") != PARSER_VERSION
                    or ai_meta.get("normalized_schema_version") != NORMALIZED_SCHEMA_VERSION
                ))
                or meta.get("embedded_metadata_parser_version") != PARSER_VERSION
                or (not ai_meta and not meta)
            )
            if needs_reinspect:
                inspect_and_persist_if_supported(conn, media["id"], path, media.get("media_type"))
                meta = get_media_metadata(conn, media["id"]) or {}
                ai_meta = get_media_ai_metadata(conn, media["id"]) or {}
            ai_ui = build_media_ai_ui_fields(ai_meta)
            description = meta.get("description") or ai_meta.get("description") or ""
            ai_prompt = meta.get("ai_prompt") or ai_meta.get("ai_prompt") or ""
            ai_negative_prompt = meta.get("ai_negative_prompt") or ai_meta.get("ai_negative_prompt") or ""
            ai_params = meta.get("ai_params") or summarize_media_ai_metadata(ai_meta) or ""
            ai_tool_summary = summarize_media_ai_tool_metadata(ai_meta) or ""
            payload.update({
                "title": meta.get("title") or "",
                "description": description,
                "notes": meta.get("notes") or "",
                "embedded_tags": meta.get("embedded_tags") or "",
                "embedded_comments": meta.get("embedded_comments") or "",
                "embedded_metadata_summary": meta.get("embedded_metadata_summary") or "",
                "ai_prompt": ai_prompt,
                "ai_negative_prompt": ai_negative_prompt,
                "ai_params": ai_params,
                "ai_tool_summary": ai_tool_summary,
                "has_metadata": bool(meta or ai_meta),
            })
        except Exception as exc:
            _log(f"Bridge.get_media_metadata optional metadata load failed for {path}: {exc!r}")

        try:
            payload["tags"] = list_media_tags(conn, media["id"])
        except Exception as exc:
            _log(f"Bridge.get_media_metadata tag load failed for {path}: {exc!r}")

        payload.update(ai_ui)
        return payload
    except Exception as exc:
        _log(f"Bridge.get_media_metadata failed for {path}: {exc!r}")
        return {}




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
