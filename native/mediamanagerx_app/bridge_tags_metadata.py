from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeTagsMetadataMixin:
    def _ensure_media_record_for_tag_write(self, path: str) -> dict | None:
        from app.mediamanager.db.media_repo import add_media_item, get_media_by_path

        clean = str(path or "").strip()
        if not clean:
            return None
        media = get_media_by_path(self.conn, clean)
        if media:
            return media
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return None
        media_type = "image" if p.suffix.lower() in IMAGE_EXTS else "video"
        add_media_item(self.conn, clean, media_type)
        return get_media_by_path(self.conn, clean)

    @Slot(str, "QVariantMap")
    def update_media_ai_metadata(self, path: str, payload: dict) -> None:
        from app.mediamanager.db.ai_metadata_repo import upsert_media_ai_selected_fields
        from app.mediamanager.db.media_repo import get_media_by_path
        try:
            m = get_media_by_path(self.conn, path)
            if not m:
                return
            data = dict(payload or {})
            upsert_media_ai_selected_fields(
                self.conn,
                m["id"],
                is_ai_detected=data.get("is_ai_detected"),
                is_ai_confidence=data.get("is_ai_confidence"),
                user_confirmed_ai=data.get("user_confirmed_ai", ""),
                tool_name_found=data.get("tool_name_found"),
                tool_name_inferred=data.get("tool_name_inferred"),
                tool_name_confidence=data.get("tool_name_confidence"),
                source_formats=data.get("source_formats"),
                ai_prompt=data.get("ai_prompt"),
                ai_negative_prompt=data.get("ai_negative_prompt"),
                description=data.get("description"),
                model_name=data.get("model_name"),
                checkpoint_name=data.get("checkpoint_name"),
                sampler=data.get("sampler"),
                scheduler=data.get("scheduler"),
                cfg_scale=data.get("cfg_scale"),
                steps=data.get("steps"),
                seed=data.get("seed"),
                upscaler=data.get("upscaler"),
                denoise_strength=data.get("denoise_strength"),
                metadata_families_detected=data.get("metadata_families_detected"),
                ai_detection_reasons=data.get("ai_detection_reasons"),
            )
            if self._current_gallery_filter_uses_ai():
                self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
        except Exception:
            pass

    @Slot(str, list)
    def set_media_tags(self, path: str, tags: list) -> None:
        from app.mediamanager.db.tags_repo import set_media_tags
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                set_media_tags(self.conn, m["id"], tags)
                self.galleryScopeChanged.emit()
        except Exception: pass

    @Slot(str, list)
    def attach_media_tags(self, path: str, tags: list) -> None:
        from app.mediamanager.db.tags_repo import attach_tags
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                attach_tags(self.conn, m["id"], tags)
                self.galleryScopeChanged.emit()
        except Exception: pass

    @Slot(str)
    def clear_media_tags(self, path: str) -> None:
        from app.mediamanager.db.tags_repo import clear_all_media_tags
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                clear_all_media_tags(self.conn, m["id"])
                self.galleryScopeChanged.emit()
        except Exception: pass

    @Slot(list, result=bool)
    def merge_duplicate_group_metadata(self, paths: list[str]) -> bool:
        from app.mediamanager.db.ai_metadata_repo import (
            build_media_ai_sidebar_fields,
            get_media_ai_metadata,
            replace_media_ai_workflows,
            upsert_media_ai_selected_fields,
        )
        from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates
        from app.mediamanager.db.metadata_repo import get_media_metadata, upsert_media_metadata
        from app.mediamanager.db.tags_repo import attach_tags, list_media_tags

        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if len(clean_paths) < 2:
            return False

        try:
            rows: list[tuple[dict, dict, dict, list[str]]] = []
            for path in clean_paths:
                media = get_media_by_path(self.conn, path)
                if not media:
                    continue
                meta = get_media_metadata(self.conn, media["id"]) or {}
                ai_meta = get_media_ai_metadata(self.conn, media["id"]) or {}
                tags = list_media_tags(self.conn, media["id"])
                rows.append((media, meta, ai_meta, tags))

            if len(rows) < 2:
                return False

            all_enabled = bool(self.settings.value("duplicate/rules/merge/all", False, type=bool))

            def merge_enabled(name: str, default: bool = False) -> bool:
                return all_enabled or bool(self.settings.value(f"duplicate/rules/merge/{name}", default, type=bool))

            ranked_media = self._rank_duplicate_group([dict(media) for media, _, _, _ in rows])
            path_rank = {str(entry.get("path") or ""): idx for idx, entry in enumerate(ranked_media)}
            sorted_rows = sorted(rows, key=lambda row: path_rank.get(str(row[0].get("path") or ""), 10**9))

            def pick_best_text(values: list[str]) -> str:
                for value in values:
                    text = str(value or "").strip()
                    if text:
                        return text
                return ""

            def pick_best_workflows() -> list[dict]:
                for _, _, ai_meta, _ in sorted_rows:
                    workflows = list(ai_meta.get("workflows") or [])
                    if workflows:
                        return workflows
                return []

            merged_tags = sorted({tag.strip() for _, _, _, tags in rows for tag in tags if str(tag).strip()}, key=str.casefold)
            merged_title = self._merge_duplicate_scalar_field([meta.get("title") for _, meta, _, _ in rows])
            merged_desc = self._merge_duplicate_text_field([meta.get("description") or ai_meta.get("description") for _, meta, ai_meta, _ in rows])
            merged_notes = self._merge_duplicate_text_field([meta.get("notes") for _, meta, _, _ in rows])
            merged_embedded_tags = self._merge_duplicate_text_field([meta.get("embedded_tags") for _, meta, _, _ in rows])
            merged_embedded_comments = self._merge_duplicate_text_field([meta.get("embedded_comments") for _, meta, _, _ in rows])
            merged_ai_prompt = self._merge_duplicate_text_field([meta.get("ai_prompt") or ai_meta.get("ai_prompt") for _, meta, ai_meta, _ in rows])
            merged_ai_negative = self._merge_duplicate_text_field([meta.get("ai_negative_prompt") or ai_meta.get("ai_negative_prompt") for _, meta, ai_meta, _ in rows])
            merged_ai_params = pick_best_text([meta.get("ai_params") for _, meta, _, _ in sorted_rows])
            merged_workflows = pick_best_workflows()
            merged_workflow_summary = build_media_ai_sidebar_fields({"workflows": merged_workflows}).get("ai_workflows_summary", "")
            merged_exif_date = self._merge_duplicate_scalar_field([media.get("exif_date_taken") for media, _, _, _ in rows])
            merged_metadata_date = self._merge_duplicate_scalar_field([media.get("metadata_date") for media, _, _, _ in rows])

            write_title = merged_title if all_enabled else None
            write_desc = merged_desc if merge_enabled("description", True) else None
            write_notes = merged_notes if merge_enabled("notes", True) else None
            write_embedded_tags = merged_embedded_tags if merge_enabled("tags", True) else None
            write_embedded_comments = merged_embedded_comments if merge_enabled("comments", True) else None
            write_ai_prompt = merged_ai_prompt if merge_enabled("ai_prompts", True) else None
            write_ai_negative = merged_ai_negative if merge_enabled("ai_prompts", True) else None
            write_ai_params = merged_ai_params if merge_enabled("ai_parameters", True) else None
            should_write_db_meta = any(
                value is not None
                for value in (
                    write_title,
                    write_desc,
                    write_notes,
                    write_embedded_tags,
                    write_embedded_comments,
                    write_ai_prompt,
                    write_ai_negative,
                    write_ai_params,
                )
            )

            for media, _, _, _ in rows:
                if should_write_db_meta:
                    upsert_media_metadata(
                        self.conn,
                        media["id"],
                        write_title,
                        write_desc,
                        write_notes,
                        write_embedded_tags,
                        write_embedded_comments,
                        write_ai_prompt,
                        write_ai_negative,
                        write_ai_params,
                    )
                if merge_enabled("tags", True):
                    attach_tags(self.conn, media["id"], merged_tags)
                if all_enabled:
                    update_media_dates(
                        self.conn,
                        media["id"],
                        exif_date_taken=merged_exif_date or None,
                        metadata_date=merged_metadata_date or None,
                    )
                if merge_enabled("description", True) or merge_enabled("ai_prompts", True):
                    upsert_media_ai_selected_fields(
                        self.conn,
                        media["id"],
                        ai_prompt=write_ai_prompt,
                        ai_negative_prompt=write_ai_negative,
                        description=write_desc,
                    )
                if merge_enabled("workflows", True):
                    replace_media_ai_workflows(self.conn, media["id"], merged_workflows)
                parent_win = self.parent() if isinstance(self.parent(), QWidget) else None
                if parent_win and hasattr(parent_win, "_embed_metadata_payload_to_file"):
                    try:
                        parent_win._embed_metadata_payload_to_file(
                            str(media.get("path") or ""),
                            tags=merged_tags if merge_enabled("tags", True) else [],
                            embedded_tags_text=write_embedded_tags or "",
                            description=write_desc or "",
                            comments=write_embedded_comments or "",
                            ai_prompt=write_ai_prompt or "",
                            ai_negative_prompt=write_ai_negative or "",
                            ai_params=write_ai_params or "",
                            ai_workflows=merged_workflow_summary if merge_enabled("workflows", True) else "",
                            notes=write_notes or "",
                            exif_date_taken_raw=(merged_exif_date or "") if all_enabled else "",
                            metadata_date_raw=(merged_metadata_date or "") if all_enabled else "",
                        )
                    except Exception:
                        pass
            return True
        except Exception as exc:
            try:
                self._log(f"Merge duplicate metadata failed: {exc}")
            except Exception:
                pass
            return False



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
