from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeMediaListingScanMixin:
    @Slot(list, int, int, str, str, str, result=list)
    def list_media(self, folders, limit=100, offset=0, sort_by="none", filter_type="all", search_query="") -> list:
        try:
            try:
                self.conn.commit()
            except Exception:
                pass
            candidates = self._get_gallery_entries(folders, sort_by, filter_type, search_query)
            start, end = max(0, int(offset)), max(0, int(offset)) + max(0, int(limit))
            out = []
            for r in candidates[start:end]:
                if r.get("is_folder"):
                    created_time = int(r.get("file_created_time") or 0)
                    modified_time = int(r.get("modified_time") or 0)
                    original_file_date = int(r.get("original_file_date") or self._normalized_file_date_ns(created_time, modified_time))
                    auto_date = int(r.get("preferred_date") or original_file_date or created_time or modified_time)
                    out.append(
                        {
                            "path": str(r["path"]),
                            "url": "",
                            "media_type": "folder",
                            "is_folder": True,
                            "thumb_bg_hint": "",
                            "is_hidden": bool(r.get("is_hidden")),
                            "is_animated": False,
                            "width": None,
                            "height": None,
                            "duration": None,
                            "file_created_time": created_time,
                            "modified_time": modified_time,
                            "original_file_date": original_file_date,
                            "exif_date_taken": None,
                            "metadata_date": None,
                            "auto_date": auto_date,
                            "file_size": None,
                            "content_hash": "",
                            "phash": "",
                            "duplicate_group_key": "",
                            "duplicate_group_size": 0,
                            "duplicate_group_position": -1,
                            "duplicate_keep_suggestion": False,
                            "duplicate_space_savings": 0,
                            "duplicate_preferred_folder_score": 0,
                            "duplicate_category_reasons": [],
                            "duplicate_is_overall_best": False,
                            "color_variant": "",
                            "duplicate_crop_variant": "",
                            "duplicate_size_variant": "",
                            "duplicate_file_format": "",
                            "review_group_mode": "",
                            "text_likely": None,
                            "text_detected": None,
                            "user_confirmed_text_detected": None,
                            "effective_text_detected": None,
                            "detected_text": "",
                            "text_detection_score": 0.0,
                            "text_detection_version": 0,
                            "text_more_likely": None,
                            "text_more_likely_score": 0.0,
                            "text_more_likely_version": 0,
                            "text_verified": None,
                            "text_verification_score": 0.0,
                            "text_verification_version": 0,
                        }
                    )
                    continue
                real = r.get("_real_path")
                p = real if isinstance(real, Path) else Path(r["path"])
                try:
                    stat = p.stat()
                    mtime = int(stat.st_mtime_ns)
                    ctime = int(stat.st_ctime_ns)
                except Exception:
                    mtime = self._iso_to_ns(r.get("modified_time"))
                    ctime = self._iso_to_ns(r.get("file_created_time"))
                original_file_date = self._original_file_date_ns(r)
                auto_date = int(r.get("preferred_date") or self._preferred_date_ns(r))
                display_width = r.get("width")
                display_height = r.get("height")
                if r.get("media_type") == "image" and p.suffix.lower() != ".svg":
                    display_size = _image_size_with_svg_support(p)
                    if display_size.isValid():
                        next_width, next_height = int(display_size.width()), int(display_size.height())
                        if int(display_width or 0) != next_width or int(display_height or 0) != next_height:
                            display_width, display_height = next_width, next_height
                            try:
                                self.conn.execute(
                                    "UPDATE media_items SET width = ?, height = ? WHERE path = ?",
                                    (display_width, display_height, str(r.get("path") or str(p)).replace("\\", "/").lower()),
                                )
                                self.conn.commit()
                            except Exception:
                                pass
                    
                out.append({
                    "path": str(p), 
                    "url": f"{QUrl.fromLocalFile(str(p)).toString()}?t={mtime}", 
                    "media_type": r["media_type"], 
                    "is_folder": False,
                    "thumb_bg_hint": _thumbnail_bg_hint(p),
                    "is_hidden": bool(r.get("is_hidden")),
                    "is_animated": self._is_animated(p),
                    "width": display_width,
                    "height": display_height,
                    "duration": r.get("duration"),
                    "file_created_time": ctime,
                    "modified_time": mtime,
                    "original_file_date": original_file_date or self._normalized_file_date_ns(ctime, mtime),
                    "exif_date_taken": r.get("exif_date_taken"),
                    "metadata_date": r.get("metadata_date"),
                    "auto_date": auto_date,
                    "file_size": r.get("file_size"),
                    "content_hash": r.get("content_hash") or "",
                    "phash": r.get("phash") or "",
                    "duplicate_group_key": r.get("duplicate_group_key") or "",
                    "duplicate_group_size": int(r.get("duplicate_group_size") or 0),
                    "duplicate_group_position": int(r.get("duplicate_group_position") or 0),
                    "duplicate_keep_suggestion": bool(r.get("duplicate_keep_suggestion")),
                    "duplicate_space_savings": int(r.get("duplicate_space_savings") or 0),
                    "duplicate_preferred_folder_score": int(r.get("duplicate_preferred_folder_score") or 0),
                    "duplicate_category_reasons": list(r.get("duplicate_category_reasons") or []),
                    "duplicate_best_reason": r.get("duplicate_best_reason") or "",
                    "duplicate_is_overall_best": bool(r.get("duplicate_is_overall_best")),
                    "color_variant": r.get("color_variant") or "",
                    "duplicate_crop_variant": r.get("duplicate_crop_variant") or "",
                    "duplicate_size_variant": r.get("duplicate_size_variant") or "",
                    "duplicate_file_format": r.get("duplicate_file_format") or "",
                    "review_group_mode": r.get("review_group_mode") or "",
                    "text_likely": r.get("text_likely"),
                    "text_detected": self._effective_text_detected(r),
                    "user_confirmed_text_detected": r.get("user_confirmed_text_detected"),
                    "effective_text_detected": self._effective_text_detected(r),
                    "detected_text": r.get("detected_text") or "",
                    "text_detection_score": float(r.get("text_detection_score") or 0.0),
                    "text_detection_version": int(r.get("text_detection_version") or 0),
                    "text_more_likely": r.get("text_more_likely"),
                    "text_more_likely_score": float(r.get("text_more_likely_score") or 0.0),
                    "text_more_likely_version": int(r.get("text_more_likely_version") or 0),
                    "text_verified": r.get("text_verified"),
                    "text_verification_score": float(r.get("text_verification_score") or 0.0),
                    "text_verification_version": int(r.get("text_verification_version") or 0),
                })
            return out
        except Exception: return []

    @Slot(str, list, int, int, str, str, str)
    def list_media_async(self, request_id: str, folders, limit=100, offset=0, sort_by="none", filter_type="all", search_query="") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        lim = int(limit or 0)
        off = int(offset or 0)
        sort = str(sort_by or "none")
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            items = self.list_media(folder_list, lim, off, sort, ftype, query)
            self._safe_emit(self.mediaListed, req, items or [])

        threading.Thread(target=work, daemon=True).start()

    @Slot(list, str, str, result=int)
    def count_media(self, folders: list, filter_type: str = "all", search_query: str = "") -> int:
        try:
            try:
                self.conn.commit()
            except Exception:
                pass
            return len(self._get_gallery_entries(folders, "none", filter_type, search_query))
        except Exception: return 0

    @Slot(list, str, str, result=int)
    def count_media_files(self, folders: list, filter_type: str = "all", search_query: str = "") -> int:
        try:
            try:
                self.conn.commit()
            except Exception:
                pass
            return sum(1 for entry in self._get_gallery_entries(folders, "none", filter_type, search_query) if not entry.get("is_folder"))
        except Exception:
            return 0

    @Slot(str, list, str, str)
    def count_media_async(self, request_id: str, folders: list, filter_type: str = "all", search_query: str = "") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            count = self.count_media(folder_list, ftype, query)
            self._safe_emit(self.mediaCounted, req, int(count or 0))

        threading.Thread(target=work, daemon=True).start()

    @Slot(str, list, str, str)
    def count_media_files_async(self, request_id: str, folders: list, filter_type: str = "all", search_query: str = "") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            count = self.count_media_files(folder_list, ftype, query)
            self._safe_emit(self.mediaFileCounted, req, int(count or 0))

        threading.Thread(target=work, daemon=True).start()

    def _get_reconciled_candidates(self, folders: list, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_scope
        from app.mediamanager.utils.pathing import normalize_windows_path
        ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS
        image_exts = IMAGE_EXTS
        media_filter, _, tags_filter, desc_filter, ai_filter = self._parse_filter_groups(filter_type)
        if not folders: return []
        show_hidden = self._show_hidden_enabled()
        include_nested = self._gallery_include_nested_files_enabled()
        current_key = hashlib.sha1(
            json.dumps(
                {
                    "folders": sorted(str(folder or "") for folder in folders),
                    "show_hidden": bool(show_hidden),
                    "include_nested": bool(include_nested),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        cached_scope = self._disk_cache_by_scope.get(current_key)
        if cached_scope is not None:
            disk_files = cached_scope
            self._disk_cache = disk_files
            self._disk_cache_key = current_key
        else:
            disk_files = {}
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.is_dir(): continue
                try:
                    if include_nested:
                        for root_dir, dir_names, files in os.walk(str(folder_path), followlinks=True):
                            curr_root = Path(root_dir)
                            if not show_hidden:
                                dir_names[:] = [
                                    name for name in dir_names
                                    if not self.repo.is_path_hidden(str(curr_root / name))
                                ]
                            for f in files:
                                p = curr_root / f
                                if not show_hidden and self.repo.is_path_hidden(str(p)):
                                    continue
                                if p.suffix.lower() in ALL_EXTS:
                                    disk_files[normalize_windows_path(str(p))] = p
                    else:
                        for child in folder_path.iterdir():
                            if not child.is_file():
                                continue
                            if not show_hidden and self.repo.is_path_hidden(str(child)):
                                continue
                            if child.suffix.lower() in ALL_EXTS:
                                disk_files[normalize_windows_path(str(child))] = child
                except Exception: pass
            self._disk_cache_by_scope[current_key] = disk_files
            self._disk_cache, self._disk_cache_key = disk_files, current_key
        db_candidates = list_media_in_scope(self.conn, folders)
        surviving, covered = [], set()
        
        for r in db_candidates:
            norm = normalize_windows_path(r["path"])
            covered.add(norm)
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = disk_files.get(norm) or Path(r["path"])
            if path_obj.exists() and path_obj.is_dir():
                continue
            if norm in disk_files or (include_nested and path_obj.exists()):
                if norm in disk_files:
                    r = dict(r)
                    r["_real_path"] = disk_files[norm]
                surviving.append(r)
        
        for norm, p_obj in disk_files.items():
            if norm not in covered:
                if not show_hidden and self.repo.is_path_hidden(str(p_obj)):
                    continue
                surviving.append({"id": -1, "path": norm, "media_type": ("image" if p_obj.suffix.lower() in image_exts else "video"), "file_size": None, "modified_time": None, "duration": None, "_real_path": p_obj})
        
        candidates = surviving
        if media_filter == "image":
            candidates = [
                r for r in candidates
                if Path(r["path"]).suffix.lower() in image_exts
                and Path(r["path"]).suffix.lower() != ".svg"
                and not self._is_animated(Path(r["path"]))
            ]
        elif media_filter == "svg":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() == ".svg"]
        elif media_filter == "video":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() not in image_exts]
        elif media_filter == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        candidates = self._apply_tags_filter(candidates, tags_filter)
        candidates = self._apply_desc_filter(candidates, desc_filter)
        if ai_filter != "all":
            self._backfill_scope_ai_decisions(candidates)
        candidates = self._apply_ai_filter(candidates, ai_filter)
        
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _get_collection_candidates(self, collection_id: int, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_collection
        image_exts = IMAGE_EXTS
        show_hidden = self._show_hidden_enabled()
        media_filter, _, tags_filter, desc_filter, ai_filter = self._parse_filter_groups(filter_type)
        
        raw_candidates = list_media_in_collection(self.conn, int(collection_id))
        candidates = []
        for r in raw_candidates:
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = Path(r["path"])
            if path_obj.exists() and path_obj.is_file():
                candidates.append(r)
                
        if media_filter == "image":
            candidates = [
                r for r in candidates
                if Path(r["path"]).suffix.lower() in image_exts
                and Path(r["path"]).suffix.lower() != ".svg"
                and not self._is_animated(Path(r["path"]))
            ]
        elif media_filter == "svg":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() == ".svg"]
        elif media_filter == "video":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() not in image_exts]
        elif media_filter == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        candidates = self._apply_tags_filter(candidates, tags_filter)
        candidates = self._apply_desc_filter(candidates, desc_filter)
        if ai_filter != "all":
            self._backfill_scope_ai_decisions(candidates)
        candidates = self._apply_ai_filter(candidates, ai_filter)
            
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _get_smart_collection_candidates(self, smart_key: str, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_smart_collection
        definition = self._smart_collection_def(smart_key)
        if not definition:
            return []
        image_exts = IMAGE_EXTS
        show_hidden = self._show_hidden_enabled()
        media_filter, _, tags_filter, desc_filter, ai_filter = self._parse_filter_groups(filter_type)
        cutoff_iso = self._smart_collection_cutoff_iso(int(definition.get("days") or 0))
        raw_candidates = list_media_in_smart_collection(self.conn, str(definition.get("field") or ""), cutoff_iso)
        candidates = []
        for r in raw_candidates:
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = Path(r["path"])
            if path_obj.exists() and path_obj.is_file():
                candidates.append(r)

        if media_filter == "image":
            candidates = [
                r for r in candidates
                if Path(r["path"]).suffix.lower() in image_exts
                and Path(r["path"]).suffix.lower() != ".svg"
                and not self._is_animated(Path(r["path"]))
            ]
        elif media_filter == "svg":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() == ".svg"]
        elif media_filter == "video":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() not in image_exts]
        elif media_filter == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        candidates = self._apply_tags_filter(candidates, tags_filter)
        candidates = self._apply_desc_filter(candidates, desc_filter)
        if ai_filter != "all":
            self._backfill_scope_ai_decisions(candidates)
        candidates = self._apply_ai_filter(candidates, ai_filter)

        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    @staticmethod
    def _apply_tags_filter(candidates: list[dict], tags_filter: str) -> list[dict]:
        mode = str(tags_filter or "all").strip().lower()
        if mode == "has_tags":
            return [r for r in candidates if str(r.get("tags") or "").strip()]
        if mode == "no_tags":
            return [r for r in candidates if not str(r.get("tags") or "").strip()]
        return candidates

    @staticmethod
    def _apply_desc_filter(candidates: list[dict], desc_filter: str) -> list[dict]:
        mode = str(desc_filter or "all").strip().lower()
        if mode == "has_description":
            return [r for r in candidates if str(r.get("description") or "").strip()]
        if mode == "no_description":
            return [r for r in candidates if not str(r.get("description") or "").strip()]
        return candidates

    @staticmethod
    def _apply_ai_filter(candidates: list[dict], ai_filter: str) -> list[dict]:
        mode = str(ai_filter or "all").strip().lower()
        if mode == "ai_generated":
            return [r for r in candidates if bool(r.get("effective_is_ai"))]
        if mode == "non_ai":
            return [r for r in candidates if r.get("effective_is_ai") is False]
        return candidates

    @staticmethod
    def _effective_text_detected(entry: dict) -> bool:
        override = entry.get("user_confirmed_text_detected")
        if override is not None:
            return bool(override)
        if entry.get("text_verified") is True:
            return True
        if entry.get("text_more_likely") is True:
            return True
        effective = entry.get("effective_text_detected")
        if effective is not None:
            return bool(effective)
        return False

    @staticmethod
    def _has_existing_positive_text_signal(entry: dict) -> bool:
        return bool(
            entry.get("text_more_likely") is True
            or entry.get("text_verified") is True
        )

    def _matches_media_search(self, row: dict, search_query: str) -> bool:
        from app.mediamanager.search_query import matches_media_search
        return matches_media_search(row, search_query)

    @staticmethod
    def _parse_filter_groups(filter_type: str) -> tuple[str, str, str, str, str]:
        raw = str(filter_type or "all").strip()
        media_filter = "all"
        text_filter = "all"
        tags_filter = "all"
        desc_filter = "all"
        ai_filter = "all"
        if not raw or raw == "all":
            return media_filter, text_filter, tags_filter, desc_filter, ai_filter
        if ":" not in raw:
            if raw in {"text_detected", "text_more_likely", "text_verified"}:
                return media_filter, "text_detected", tags_filter, desc_filter, ai_filter
            if raw == "no_text_detected":
                return media_filter, "no_text_detected", tags_filter, desc_filter, ai_filter
            if raw in {"has_tags", "no_tags"}:
                return media_filter, text_filter, raw, desc_filter, ai_filter
            if raw in {"has_description", "no_description"}:
                return media_filter, text_filter, tags_filter, raw, ai_filter
            if raw in {"ai_generated", "non_ai"}:
                return media_filter, text_filter, tags_filter, desc_filter, raw
            if raw in {"image", "svg", "video", "animated"}:
                return raw, text_filter, tags_filter, desc_filter, ai_filter
            return media_filter, text_filter, tags_filter, desc_filter, ai_filter
        for part in raw.split(";"):
            group, _, value = str(part or "").partition(":")
            group = group.strip().lower()
            value = value.strip().lower()
            if group == "media" and value in {"image", "svg", "video", "animated"}:
                media_filter = value
            elif group == "text":
                if value in {"text_detected", "text_more_likely", "text_verified"}:
                    text_filter = "text_detected"
                elif value == "no_text_detected":
                    text_filter = "no_text_detected"
            elif group == "tags" and value in {"has_tags", "no_tags"}:
                tags_filter = value
            elif group == "desc" and value in {"has_description", "no_description"}:
                desc_filter = value
            elif group == "meta" and value in {"no_tags", "no_description"}:
                if value == "no_tags":
                    tags_filter = "no_tags"
                elif value == "no_description":
                    desc_filter = "no_description"
            elif group == "ai" and value in {"ai_generated", "non_ai"}:
                ai_filter = value
        return media_filter, text_filter, tags_filter, desc_filter, ai_filter

    @staticmethod
    def _iso_to_ns(value) -> int:
        if value is None:
            return 0
        text = str(value).strip()
        if not text:
            return 0
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                return int(dt.timestamp() * 1_000_000_000)
            return int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000)
        except Exception:
            return 0

    def _preferred_date_ns(self, row: dict) -> int:
        for key in ("exif_date_taken", "metadata_date"):
            value = self._iso_to_ns(row.get(key))
            if value > 0:
                return value
        original_file_date = self._original_file_date_ns(row)
        if original_file_date > 0:
            return original_file_date
        file_created_value = row.get("file_created_time")
        if isinstance(file_created_value, int):
            if file_created_value > 0:
                return file_created_value
        else:
            value = self._iso_to_ns(file_created_value)
            if value > 0:
                return value
        raw_modified = row.get("modified_time")
        if isinstance(raw_modified, int):
            return raw_modified
        return self._iso_to_ns(raw_modified)

    def _normalized_file_date_ns(self, file_created_value, modified_value) -> int:
        values: list[int] = []
        for raw_value in (file_created_value, modified_value):
            if isinstance(raw_value, int):
                value = raw_value
            else:
                value = self._iso_to_ns(raw_value)
            if value > 0:
                values.append(value)
        return min(values) if values else 0

    def _original_file_date_ns(self, row: dict) -> int:
        raw_value = row.get("original_file_date")
        if isinstance(raw_value, int):
            if raw_value > 0:
                return raw_value
        else:
            value = self._iso_to_ns(raw_value)
            if value > 0:
                return value
        return self._normalized_file_date_ns(row.get("file_created_time"), row.get("modified_time"))

    def _list_folder_entries(self, folders: list[str], search_query: str = "") -> list[dict]:
        if not folders:
            return []

        show_hidden = self._show_hidden_enabled()
        query = (search_query or "").strip().lower()
        seen: set[str] = set()
        entries: list[dict] = []

        for folder in folders:
            root = Path(folder)
            if not root.is_dir():
                continue
            try:
                for child in root.iterdir():
                    if not child.is_dir():
                        continue
                    norm = str(child).lower().replace("\\", "/")
                    if norm in seen:
                        continue
                    is_hidden = self.repo.is_path_hidden(str(child))
                    if not show_hidden and is_hidden:
                        continue
                    if query:
                        haystack = f"{child.name} {child}".lower()
                        if query not in haystack:
                            continue
                    seen.add(norm)
                    try:
                        stat = child.stat()
                        modified_time = int(stat.st_mtime_ns)
                        created_time = int(stat.st_ctime_ns)
                    except Exception:
                        modified_time = 0
                        created_time = 0
                    entries.append(
                        {
                            "path": str(child),
                            "media_type": "folder",
                            "is_folder": True,
                            "is_hidden": is_hidden,
                            "file_size": None,
                            "file_created_time": created_time,
                            "modified_time": modified_time,
                            "original_file_date": self._normalized_file_date_ns(created_time, modified_time),
                            "preferred_date": self._normalized_file_date_ns(created_time, modified_time) or created_time or modified_time,
                            "width": None,
                            "height": None,
                            "duration": None,
                        }
                    )
            except Exception:
                continue

        return entries

    def _sort_gallery_entries(self, entries: list[dict], sort_by: str) -> list[dict]:
        name_key = lambda row: Path(str(row.get("path", ""))).name.lower()
        date_key = lambda row: row.get("preferred_date") or self._preferred_date_ns(row)
        size_key = lambda row: row.get("file_size") or 0
        folders = [row for row in entries if row.get("is_folder")]
        media = [row for row in entries if not row.get("is_folder")]

        if self._randomize_enabled() and sort_by == "none":
            folders.sort(key=name_key)
            media.sort(key=self._session_shuffle_key)
            return folders + media

        if sort_by == "none":
            folders.sort(key=name_key)
            media.sort(key=name_key)
            return folders + media

        if sort_by == "name_desc":
            folders.sort(key=name_key, reverse=True)
            media.sort(key=name_key, reverse=True)
            return folders + media
        if sort_by == "date_desc":
            folders.sort(key=lambda row: (date_key(row), name_key(row)), reverse=True)
            media.sort(key=lambda row: (date_key(row), name_key(row)), reverse=True)
            return folders + media
        if sort_by == "date_asc":
            folders.sort(key=lambda row: (date_key(row), name_key(row)))
            media.sort(key=lambda row: (date_key(row), name_key(row)))
            return folders + media
        if sort_by == "type_asc":
            folders.sort(key=name_key)
            media.sort(key=lambda row: (self._file_type_sort_key(row), name_key(row)))
            return folders + media
        if sort_by == "type_desc":
            folders.sort(key=name_key)
            media.sort(key=lambda row: (self._file_type_sort_key(row), name_key(row)), reverse=True)
            return folders + media
        if sort_by == "size_desc":
            folders.sort(key=lambda row: (size_key(row), name_key(row)), reverse=True)
            media.sort(key=lambda row: (size_key(row), name_key(row)), reverse=True)
            return folders + media
        if sort_by == "size_asc":
            folders.sort(key=lambda row: (size_key(row), name_key(row)))
            media.sort(key=lambda row: (size_key(row), name_key(row)))
            return folders + media
        folders.sort(key=name_key)
        media.sort(key=name_key)
        return folders + media

    @staticmethod
    def _file_type_sort_key(row: dict) -> str:
        path = str(row.get("path") or "").strip()
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix:
            return suffix
        media_type = str(row.get("media_type") or "").strip().lower()
        return media_type or ""

    def _get_gallery_entries(self, folders: list[str], sort_by: str = "none", filter_type: str = "all", search_query: str = "") -> list[dict]:
        _, text_filter, _, _, _ = self._parse_filter_groups(filter_type)
        if folders:
            entries = self._get_reconciled_candidates(folders, filter_type, search_query)
            if self._gallery_show_folders_enabled() and self._gallery_view_mode() != "masonry" and self._review_group_mode() is None:
                entries = self._list_folder_entries(folders, search_query) + entries
        elif self._active_collection_id is not None:
            entries = self._get_collection_candidates(self._active_collection_id, filter_type, search_query)
        elif self._active_smart_collection_key:
            entries = self._get_smart_collection_candidates(self._active_smart_collection_key, filter_type, search_query)
        else:
            entries = []
        if text_filter in {"text_detected", "no_text_detected"}:
            if text_filter == "no_text_detected":
                entries = [entry for entry in entries if not self._effective_text_detected(entry)]
            else:
                entries = [entry for entry in entries if self._effective_text_detected(entry)]
        review_mode = self._review_group_mode()
        if review_mode in {"similar", "similar_only"}:
            self._backfill_scope_content_hashes(entries)
            self._backfill_scope_phashes(entries)
            threshold, bucket_prefix = self._similarity_config()
            return self._build_similar_entries(
                entries,
                sort_by,
                include_exact=(review_mode == "similar"),
                threshold=threshold,
                bucket_prefix=bucket_prefix,
            )
        if review_mode == "duplicates":
            self._backfill_scope_content_hashes(entries)
            return self._build_duplicate_entries(entries, sort_by)
        return self._sort_gallery_entries(entries, sort_by)

    def _evaluate_scan_scope(
        self,
        entries: list[dict],
        primary: str = "",
        *,
        emit_progress: bool = False,
        show_progress_after_s: float = 0.75,
    ) -> tuple[bool, list[Path], bool]:
        """Single-pass scope evaluation.

        Returns:
        - is_warm: every file is still up to date and fully scanned
        - changed_paths: files that need a deep scan
        - progress_started: whether this pass emitted scanStarted/scanProgress
        """
        media_entries = [entry for entry in entries if not entry.get("is_folder")]
        if not media_entries:
            return True, [], False

        changed_paths: list[Path] = []
        is_warm = True
        progress_started = False
        started_at = time.monotonic()
        total = len(media_entries)

        for i, entry in enumerate(media_entries):
            if emit_progress and not progress_started and (time.monotonic() - started_at) >= show_progress_after_s:
                progress_started = self._safe_emit(self.scanStarted, primary)
            if progress_started and total > 0 and (i == 0 or (i + 1) % 50 == 0 or (i + 1) == total):
                phase_percent = max(1, min(99, int(((i + 1) / total) * 100)))
                self._safe_emit(self.scanProgress, "Checking for changes...", phase_percent)

            raw_path = entry.get("_real_path") or entry.get("path") or ""
            path = str(raw_path).strip()
            if not path:
                is_warm = False
                continue
            p = raw_path if isinstance(raw_path, Path) else Path(path)
            try:
                stat = p.stat()
                if not p.is_file():
                    is_warm = False
                    changed_paths.append(p)
                    continue
                current_mtime = datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).replace(microsecond=0).isoformat()
            except Exception:
                is_warm = False
                changed_paths.append(p)
                continue

            needs_deep_scan = False
            if int(entry.get("file_size") or 0) != int(stat.st_size):
                needs_deep_scan = True
            elif str(entry.get("modified_time") or "") != current_mtime:
                needs_deep_scan = True
            elif not str(entry.get("content_hash") or "").strip():
                needs_deep_scan = True
            elif not (entry.get("width") and entry.get("height")):
                needs_deep_scan = True
            else:
                suffix = p.suffix.lower()
                if str(entry.get("media_type") or "") == "image" and suffix != ".svg":
                    if not str(entry.get("phash") or "").strip():
                        needs_deep_scan = True

            if needs_deep_scan:
                is_warm = False
                changed_paths.append(p)

        return is_warm, changed_paths, progress_started

    def _invalidate_scan_caches(self) -> None:
        self._disk_cache = {}
        self._disk_cache_key = ""
        self._disk_cache_by_scope.clear()
        self._last_full_scan_key = ""
        self._warm_scan_keys.clear()
        with self._checkpoint_lock:
            self._scan_checkpoint.clear()
            self._checkpoint_dirty_count = 0
        try:
            if self._checkpoint_path.exists():
                self._checkpoint_path.unlink()
        except Exception:
            pass

    def _load_scan_checkpoint(self) -> dict[str, set[str]]:
        try:
            if self._checkpoint_path.exists():
                data = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): set(v) for k, v in data.items() if isinstance(v, list)}
        except Exception:
            pass
        return {}

    def _save_scan_checkpoint(self) -> None:
        try:
            with self._checkpoint_lock:
                payload = {k: sorted(v) for k, v in self._scan_checkpoint.items()}
                self._checkpoint_dirty_count = 0
            self._checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            try:
                self._log(f"Checkpoint save failed: {exc}")
            except Exception:
                pass

    def _checkpoint_mark(self, scope_key: str, path: str) -> bool:
        if not scope_key:
            return False
        with self._checkpoint_lock:
            self._scan_checkpoint.setdefault(scope_key, set()).add(path)
            self._checkpoint_dirty_count += 1
            should_flush = self._checkpoint_dirty_count >= 50
        return should_flush

    def _checkpoint_done_paths(self, scope_key: str) -> set[str]:
        if not scope_key:
            return set()
        with self._checkpoint_lock:
            return set(self._scan_checkpoint.get(scope_key, set()))

    @Slot(list, str)
    def start_scan(self, folders: list, search_query: str = "") -> None:
        if not folders:
            return
        scan_key = hashlib.sha1(",".join(sorted(str(folder) for folder in folders)).encode()).hexdigest()
        if self._last_full_scan_key == scan_key or scan_key in self._warm_scan_keys:
            primary = folders[0] if folders else ""
            def emit_cached_scan_finished() -> None:
                try:
                    count = len(self._get_reconciled_candidates(folders, "all", search_query))
                except Exception:
                    count = 0
                self._safe_emit(self.scanFinished, primary, int(count))
                if not self._shutting_down:
                    self._ensure_background_text_processing(list(folders), None)

            threading.Thread(target=emit_cached_scan_finished, daemon=True).start()
            return
        self._cancel_text_processing()
        self._scan_abort = True
        def work():
            primary = folders[0] if folders else ""
            emitted_finish = False
            try:
                time.sleep(0.1)
                self._scan_abort = False
                with self._scan_lock:
                    # Always evaluate scanner scope against the full folder tree,
                    # independent of the current search filter, so change
                    # detection is correct and stable.
                    reconciled_scope = self._get_reconciled_candidates(folders, "all", "")
                    is_warm, changed_paths, progress_started = self._evaluate_scan_scope(
                        reconciled_scope,
                        primary,
                        emit_progress=True,
                    )
                    if is_warm:
                        self._last_full_scan_key = scan_key
                        self._warm_scan_keys.add(scan_key)
                        finish_count = len(reconciled_scope) if not str(search_query or "").strip() else len(self._get_reconciled_candidates(folders, "all", search_query))
                        self._safe_emit(self.scanFinished, primary, finish_count)
                        emitted_finish = True
                    else:
                        paths = changed_paths
                        if paths:
                            if not progress_started:
                                self._safe_emit(self.scanStarted, primary)
                            self._do_full_scan(paths, self.conn, emit_progress=True, scope_key=scan_key)
                        self._last_full_scan_key = scan_key
                        self._warm_scan_keys.add(scan_key)
                        finish_count = len(reconciled_scope) if not str(search_query or "").strip() else len(self._get_reconciled_candidates(folders, "all", search_query))
                        self._safe_emit(self.scanFinished, primary, finish_count)
                        emitted_finish = True
                if not self._shutting_down:
                    self._ensure_background_text_processing(list(folders), None)
            except Exception as exc:
                try:
                    self._log(f"Background scan failed: {exc}")
                except Exception:
                    pass
            finally:
                # Belt-and-suspenders: guarantee scanFinished fires even if the
                # scan crashed mid-flight. Without this, the JS toast would be
                # stuck "Initializing..." forever because gScanActive is never
                # cleared (no scanFinished = no handler = no flag reset).
                if not emitted_finish:
                    try:
                        self._safe_emit(self.scanFinished, primary, 0)
                    except Exception:
                        pass
        threading.Thread(target=work, daemon=True).start()

    @Slot(list)
    def start_scan_paths(self, paths: list[str]) -> None:
        clean_paths = [Path(path) for path in paths if str(path or "").strip()]
        if not clean_paths:
            return
        # Always refresh the priority set so an in-flight full scan reorders its
        # tail toward what's now visible on screen.
        with self._priority_lock:
            self._priority_paths = {str(p) for p in clean_paths}
        # If a full scan is already running it will pick up the new priority on
        # its next re-sort tick â€” no need to queue another lock-blocked scan.
        if self._scan_lock.locked():
            return
        def work():
            try:
                with self._scan_lock:
                    self._do_full_scan(clean_paths, self.conn, emit_progress=False)
            except Exception as exc:
                try:
                    self._log(f"Page scan failed: {exc}")
                except Exception:
                    pass
        threading.Thread(target=work, daemon=True).start()

    def _do_full_scan(self, paths: list[Path], conn, emit_progress: bool = True, scope_key: str = "") -> int:
        from app.mediamanager.db.media_repo import get_media_by_path, upsert_media_item
        from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
        from app.mediamanager.utils.hashing import calculate_media_content_hash, calculate_image_phash
        from datetime import datetime, timezone

        # Priority + checkpoint-aware ordering: visible paths first, then
        # unfinished, then already-checkpointed (the per-file skip block below
        # remains authoritative â€” checkpoint only changes iteration order).
        with self._priority_lock:
            priority = set(self._priority_paths)
        done = self._checkpoint_done_paths(scope_key)
        if priority or done:
            paths = sorted(
                paths,
                key=lambda x: (
                    0 if str(x) in priority else 1,
                    0 if str(x) not in done else 1,
                ),
            )
        # Mutable copy so we can re-sort the unprocessed tail mid-scan if the
        # visible page changes while we're working.
        paths = list(paths)
        total, count = len(paths), 0
        for i, p in enumerate(paths):
            self._wait_while_scan_performance_paused()
            if self._scan_abort: break
            # Every 25 files, check if the priority set changed (e.g. user paged
            # the gallery) and reorder the remaining tail accordingly.
            if i and i % 25 == 0:
                with self._priority_lock:
                    new_priority = set(self._priority_paths)
                if new_priority != priority:
                    priority = new_priority
                    tail = sorted(
                        paths[i:],
                        key=lambda x: (
                            0 if str(x) in priority else 1,
                            0 if str(x) not in done else 1,
                        ),
                    )
                    paths[i:] = tail
                    p = paths[i]
            if emit_progress:
                self._safe_emit(self.scanProgress, p.name, int(((i + 1) / total) * 100) if total > 0 else 100)
            try:
                stat = p.stat()
                existing, skip = get_media_by_path(conn, str(p)), False
                media_id = existing["id"] if existing else None
                display_size = QSize()
                suffix = p.suffix.lower()
                if suffix in IMAGE_EXTS and suffix != ".svg":
                    display_size = _image_size_with_svg_support(p)
                if existing:
                    curr_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    if existing["file_size"] == stat.st_size and existing.get("modified_time") == curr_mtime:
                        has_required_content_hash = bool(str(existing.get("content_hash") or "").strip())
                        has_required_visual_data = bool(existing.get("width") and existing.get("height"))
                        if suffix in IMAGE_EXTS and suffix != ".svg":
                            has_required_visual_data = has_required_visual_data and bool(str(existing.get("phash") or "").strip())
                            if display_size.isValid() and (
                                int(existing.get("width") or 0) != int(display_size.width())
                                or int(existing.get("height") or 0) != int(display_size.height())
                            ):
                                has_required_visual_data = False
                        if has_required_content_hash and has_required_visual_data:
                            skip = True
                
                if not skip:
                    width, height, d_ms = None, None, None
                    mtype = "image" if p.suffix.lower() in IMAGE_EXTS else "video"
                    
                    phash = None
                    if mtype == "image":
                        sz = display_size if display_size.isValid() else _image_size_with_svg_support(p)
                        if sz.isValid():
                            width, height = sz.width(), sz.height()
                        
                        # Fallback for formats like AVIF that Qt can't read natively
                        if width is None or height is None:
                            w, h, _ = self._probe_video_size(str(p))
                            if w > 0 and h > 0:
                                width, height = w, h
                        phash = calculate_image_phash(p)
                    else:
                        w, h, _ = self._probe_video_size(str(p))
                        if w > 0 and h > 0:
                            width, height = w, h
                        # Capture duration for looping logic
                        d_s = self.get_video_duration_seconds(str(p))
                        if d_s > 0:
                            d_ms = int(d_s * 1000)
                        
                    media_id = upsert_media_item(
                        conn,
                        str(p),
                        mtype,
                        calculate_media_content_hash(p),
                        phash=phash,
                        width=width,
                        height=height,
                        duration_ms=d_ms,
                    )
                if media_id is not None:
                    inspect_and_persist_if_supported(conn, media_id, str(p), "image" if p.suffix.lower() in IMAGE_EXTS else "video")
                count += 1
                if scope_key and self._checkpoint_mark(scope_key, str(p)):
                    self._save_scan_checkpoint()
            except Exception as exc:
                try:
                    self._log(f"Background scan item failed for {p}: {exc}")
                except Exception:
                    pass
        if scope_key:
            self._save_scan_checkpoint()
        return count

    @Slot(str, result=str)
    def get_video_poster(self, video_path: str) -> str:
        try:
            p = Path(video_path)
            if not p.exists() or not p.is_file():
                return ""
            out = self._ensure_video_poster(p)
            if out:
                try:
                    mtime = int(out.stat().st_mtime_ns)
                except Exception:
                    import time
                    mtime = int(time.time() * 1000)
                return f"{QUrl.fromLocalFile(str(out)).toString()}?t={mtime}"
            return ""
        except Exception: return ""

    @Slot(result=dict)
    def get_tools_status(self) -> dict:
        return {"ffmpeg": bool(self._ffmpeg_bin()), "ffmpeg_path": self._ffmpeg_bin() or "", "ffprobe": bool(self._ffprobe_bin()), "ffprobe_path": self._ffprobe_bin() or "", "thumb_dir": str(self._thumb_dir)}




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]


__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
