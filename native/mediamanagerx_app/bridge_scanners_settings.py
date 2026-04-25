from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeScannersSettingsMixin:
    def _randomize_enabled(self) -> bool:
        return bool(self.settings.value("gallery/randomize", False, type=bool))

    def _reset_session_shuffle_order(self) -> None:
        self._session_shuffle_seed = random.getrandbits(32)
        self._session_shuffle_random = random.Random(self._session_shuffle_seed)
        self._session_shuffle_order = {}

    def _session_shuffle_key(self, row: dict) -> tuple[float, str]:
        path = str(row.get("path") or "")
        key = path.replace("/", "\\").casefold()
        if key not in self._session_shuffle_order:
            self._session_shuffle_order[key] = self._session_shuffle_random.random()
        return self._session_shuffle_order[key], key

    def _restore_last_enabled(self) -> bool:
        return bool(self.settings.value("gallery/restore_last", False, type=bool))

    def _show_hidden_enabled(self) -> bool:
        return bool(self.settings.value("gallery/show_hidden", False, type=bool))

    def _gallery_include_nested_files_enabled(self) -> bool:
        return bool(self.settings.value("gallery/include_nested_files", True, type=bool))

    def _gallery_show_folders_enabled(self) -> bool:
        return bool(self.settings.value("gallery/show_folders", True, type=bool))

    def _preview_above_details_enabled(self) -> bool:
        return bool(self.settings.value("ui/preview_above_details", True, type=bool))

    def _start_folder_setting(self) -> str:
        return str(self.settings.value("gallery/start_folder", "", type=str) or "")

    def _last_folder(self) -> str:
        return str(self.settings.value("gallery/last_folder", "", type=str) or "")

    def _gallery_view_mode(self) -> str:
        mode = str(self.settings.value("gallery/view_mode", "masonry", type=str) or "masonry")
        allowed = {
            "masonry",
            "grid_small",
            "grid_medium",
            "grid_large",
            "grid_xlarge",
            "list",
            "content",
            "details",
            "duplicates",
            "similar",
            "similar_only",
        }
        return mode if mode in allowed else "masonry"

    def _gallery_group_by(self) -> str:
        value = str(self.settings.value("gallery/group_by", "none", type=str) or "none")
        allowed = {"none", "date", "duplicates", "similar", "similar_only"}
        return value if value in allowed else "none"

    def _gallery_similarity_threshold(self) -> str:
        value = str(self.settings.value("gallery/similarity_threshold", "low", type=str) or "low")
        allowed = {"very_low", "low", "medium", "high", "very_high"}
        return value if value in allowed else "low"

    def _duplicates_mode_active(self) -> bool:
        return self._gallery_view_mode() == "duplicates" or self._gallery_group_by() == "duplicates"

    def _similar_mode_active(self) -> bool:
        return self._gallery_view_mode() == "similar" or self._gallery_group_by() == "similar"

    def _similar_only_mode_active(self) -> bool:
        return self._gallery_view_mode() == "similar_only" or self._gallery_group_by() == "similar_only"

    def _review_group_mode(self) -> str | None:
        if self._similar_only_mode_active():
            return "similar_only"
        if self._similar_mode_active():
            return "similar"
        if self._duplicates_mode_active():
            return "duplicates"
        return None

    @staticmethod
    def _normalized_review_pair(path_a: str, path_b: str) -> tuple[str, str] | None:
        return review_groups.normalized_review_pair(path_a, path_b)

    def _load_review_pair_exclusions(self, entries: list[dict], review_mode: str) -> set[tuple[str, str]]:
        return review_groups.load_review_pair_exclusions(self.conn, entries, review_mode)

    def _is_review_pair_excluded(self, excluded_pairs: set[tuple[str, str]], left_path: str, right_path: str) -> bool:
        return review_groups.is_review_pair_excluded(excluded_pairs, left_path, right_path)

    def _split_duplicate_group_components(
        self,
        group_entries: list[dict],
        excluded_pairs: set[tuple[str, str]],
    ) -> list[list[dict]]:
        return review_groups.split_duplicate_group_components(group_entries, excluded_pairs)

    @staticmethod
    def _folder_depth_for_duplicate(entry: dict) -> int:
        return review_groups.folder_depth_for_duplicate(entry)

    @staticmethod
    def _duplicate_parent_folder(entry: dict) -> str:
        return review_groups.duplicate_parent_folder(entry)

    def _preferred_folder_priority_state(self) -> tuple[bool, list[str], dict[str, int]]:
        return review_groups.preferred_folder_priority_state(self.settings)

    def _preferred_folder_score(self, entry: dict, *, enabled: bool, score_by_folder: dict[str, int]) -> int:
        return review_groups.preferred_folder_score(entry, enabled=enabled, score_by_folder=score_by_folder)

    @staticmethod
    def _duplicate_metadata_score(entry: dict) -> tuple[int, int]:
        return review_groups.duplicate_metadata_score(entry)

    @staticmethod
    def _split_distinct_text_blocks(values: list[str]) -> list[str]:
        return review_groups.split_distinct_text_blocks(values)

    @classmethod
    def _merge_duplicate_text_field(cls, values: list[str]) -> str:
        return review_groups.merge_duplicate_text_field(values)

    @staticmethod
    def _merge_duplicate_scalar_field(values: list[str]) -> str:
        return review_groups.merge_duplicate_scalar_field(values)

    @staticmethod
    def _duplicate_score(entry: dict) -> tuple:
        return review_groups.duplicate_score(entry)

    def _sort_duplicate_group(self, entries: list[dict]) -> list[dict]:
        return review_groups.sort_duplicate_group(
            entries,
            annotate_group_color_variants=self._annotate_group_color_variants,
        )

    def _rank_duplicate_group(self, entries: list[dict], extra_positive_categories: list[dict] | None = None) -> list[dict]:
        return review_groups.rank_duplicate_group(
            entries,
            settings=self.settings,
            annotate_group_color_variants=self._annotate_group_color_variants,
            iso_to_ns=self._iso_to_ns,
            original_file_date_ns=self._original_file_date_ns,
            preferred_date_ns=self._preferred_date_ns,
            extra_positive_categories=extra_positive_categories,
        )

    def _build_duplicate_entries(self, entries: list[dict], sort_by: str) -> list[dict]:
        return review_groups.build_duplicate_entries(
            entries,
            sort_by,
            conn=self.conn,
            rank_duplicate_group_fn=lambda group_entries, extras=None: self._rank_duplicate_group(group_entries, extras),
            preferred_date_ns=self._preferred_date_ns,
            file_type_sort_key=self._file_type_sort_key,
        )

    def _build_similar_entries(self, entries: list[dict], sort_by: str, *, include_exact: bool, threshold: int, bucket_prefix: int) -> list[dict]:
        return review_groups.build_similar_entries(
            entries,
            sort_by,
            include_exact=include_exact,
            threshold=threshold,
            bucket_prefix=bucket_prefix,
            conn=self.conn,
            rank_duplicate_group_fn=lambda group_entries, extras=None: self._rank_duplicate_group(group_entries, extras),
            file_type_sort_key=self._file_type_sort_key,
        )

    def _annotate_group_color_variants(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import classify_image_color_mode

        cache = getattr(self, "_color_variant_cache", None)
        if cache is None:
            cache = {}
            self._color_variant_cache = cache

        for entry in entries:
            if entry.get("is_folder") or entry.get("media_type") != "image" or str(entry.get("color_variant") or "").strip():
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            cached = cache.get(path)
            if cached is None:
                try:
                    p = Path(path)
                    cached = classify_image_color_mode(p) if p.exists() and p.is_file() else ""
                except Exception:
                    cached = ""
                cache[path] = cached
            if cached:
                entry["color_variant"] = cached

    def _backfill_scope_phashes(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import calculate_image_phash

        updates: list[tuple[str, str]] = []
        for entry in entries:
            if entry.get("is_folder") or entry.get("media_type") != "image" or str(entry.get("phash") or "").strip():
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                phash = calculate_image_phash(p)
            except Exception:
                phash = ""
            if not phash:
                continue
            entry["phash"] = phash
            updates.append((phash, path))
        if not updates:
            return
        try:
            self.conn.executemany("UPDATE media_items SET phash = ? WHERE path = ?", updates)
            self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"pHash backfill failed: {exc}")
            except Exception:
                pass

    @staticmethod
    def _scanner_setting_key(scanner_key: str, field: str) -> str:
        return f"scanners/{scanner_key}/{field}"

    @staticmethod
    def _scanner_display_name(scanner_key: str) -> str:
        return "OCR for Text Detected Files" if scanner_key == "ocr_text" else "Text Detection"

    def _scanner_enabled(self, scanner_key: str) -> bool:
        default_enabled = scanner_key != "ocr_text"
        return bool(self.settings.value(self._scanner_setting_key(scanner_key, "enabled"), default_enabled, type=bool))

    def _scanner_interval_hours(self, scanner_key: str) -> int:
        try:
            return max(1, int(self.settings.value(self._scanner_setting_key(scanner_key, "interval_hours"), 24, type=int) or 24))
        except Exception:
            return 24

    def _ocr_scanner_run_fast(self) -> bool:
        return bool(self.settings.value(self._scanner_setting_key("ocr_text", "run_fast"), True, type=bool))

    def _ocr_scanner_run_ai(self) -> bool:
        return bool(self.settings.value(self._scanner_setting_key("ocr_text", "run_ai"), False, type=bool))

    def _ocr_scanner_all_files(self) -> bool:
        return bool(self.settings.value(self._scanner_setting_key("ocr_text", "all_files"), False, type=bool))

    def _scanner_source_folders(self, scanner_key: str) -> list[str]:
        raw = self.settings.value(self._scanner_setting_key(scanner_key, "source_folders"), "", type=str)
        try:
            values = json.loads(str(raw or "[]"))
        except Exception:
            values = []
        folders: list[str] = []
        seen: set[str] = set()
        for value in values if isinstance(values, list) else []:
            folder = str(value or "").strip()
            if not folder:
                continue
            key = os.path.normcase(os.path.normpath(folder))
            if key in seen:
                continue
            seen.add(key)
            folders.append(folder)
        return folders

    def _scanner_last_run_utc(self, scanner_key: str) -> str:
        return str(self.settings.value(self._scanner_setting_key(scanner_key, "last_run_utc"), "", type=str) or "")

    def _set_scanner_status(self, scanner_key: str, status: str, *, mark_run: bool = False) -> None:
        self.settings.setValue(self._scanner_setting_key(scanner_key, "status"), str(status or "Idle"))
        if mark_run:
            self.settings.setValue(
                self._scanner_setting_key(scanner_key, "last_run_utc"),
                datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
        self.settings.sync()
        self.scannerStatusChanged.emit(scanner_key, self._scanner_status_payload(scanner_key))

    def _scanner_status_payload(self, scanner_key: str) -> dict:
        enabled = self._scanner_enabled(scanner_key)
        status = str(self.settings.value(self._scanner_setting_key(scanner_key, "status"), "Idle", type=str) or "Idle")
        running = bool(scanner_key == "ocr_text" and getattr(self, "_ocr_text_processing_active", False))
        return {
            "key": scanner_key,
            "name": self._scanner_display_name(scanner_key),
            "enabled": enabled,
            "running": running,
            "interval_hours": self._scanner_interval_hours(scanner_key),
            "last_run_utc": self._scanner_last_run_utc(scanner_key),
            "status": status,
            "source_folders": self._scanner_source_folders(scanner_key),
            "run_fast": self._ocr_scanner_run_fast() if scanner_key == "ocr_text" else False,
            "run_ai": self._ocr_scanner_run_ai() if scanner_key == "ocr_text" else False,
            "all_files": self._ocr_scanner_all_files() if scanner_key == "ocr_text" else False,
        }

    def _scanner_due(self, scanner_key: str) -> bool:
        if not self._scanner_enabled(scanner_key):
            return False
        last_run = self._scanner_last_run_utc(scanner_key)
        if not last_run:
            return True
        try:
            dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            return True
        return datetime.now(timezone.utc) - dt >= timedelta(hours=self._scanner_interval_hours(scanner_key))

    def _check_scanner_schedules(self) -> None:
        if self._scanner_due("text_detection"):
            folders = self._scanner_source_folders("text_detection")
            if folders:
                self._ensure_background_text_processing(folders=folders, force=True)
            else:
                self._set_scanner_status("text_detection", "Idle (no scheduled source folders)", mark_run=True)
        if self._scanner_due("ocr_text"):
            folders = self._scanner_source_folders("ocr_text")
            if folders:
                self._run_ocr_text_scanner(folders=folders, force=True)
            else:
                self._set_scanner_status("ocr_text", "Idle (no scheduled source folders)", mark_run=True)

    @staticmethod
    def _text_stage_label(stage_key: str) -> str:
        if stage_key == "waiting":
            return "Detecting Text (Waiting for Scan)"
        return "Detecting Text"

    def _text_processing_should_continue(self, generation: int | None = None) -> bool:
        if generation is None:
            return not self._text_processing_paused
        return generation == self._text_processing_generation and not self._text_processing_paused

    def _cancel_text_processing(self) -> None:
        self._text_processing_generation += 1
        self._text_processing_paused = False
        self._text_processing_active = False
        self._text_processing_scope_key = ("none",)
        self._text_processing_thread = None
        self.textProcessingFinished.emit()

    def _wait_while_scan_performance_paused(self) -> None:
        while True:
            with self._performance_pause_lock:
                paused = bool(self._scan_performance_paused)
            if not paused or self._scan_abort:
                return
            time.sleep(0.1)

    @Slot()
    def pause_lightbox_background_work(self) -> None:
        with self._performance_pause_lock:
            self._lightbox_background_pause_depth += 1
            self._scan_performance_paused = True
            should_pause_text = (
                self._lightbox_background_pause_depth == 1
                and self._text_processing_active
                and not self._text_processing_paused
            )
            if should_pause_text:
                self._lightbox_paused_text_processing = True
                self._text_processing_paused = True

    @Slot()
    def resume_lightbox_background_work(self) -> None:
        should_resume_text = False
        with self._performance_pause_lock:
            if self._lightbox_background_pause_depth > 0:
                self._lightbox_background_pause_depth -= 1
            if self._lightbox_background_pause_depth > 0:
                return
            self._scan_performance_paused = False
            should_resume_text = bool(self._lightbox_paused_text_processing)
            self._lightbox_paused_text_processing = False
        if should_resume_text:
            self._ensure_background_text_processing(allow_concurrent_scan=True)

    def _current_text_scope_key(self, folders: list[str] | None = None, collection_id: int | None = None) -> tuple:
        if folders:
            return ("folders", tuple(sorted(str(folder or "") for folder in folders if str(folder or "").strip())))
        if collection_id is not None:
            return ("collection", int(collection_id))
        if self._selected_folders:
            return ("folders", tuple(sorted(str(folder or "") for folder in self._selected_folders if str(folder or "").strip())))
        if self._active_collection_id is not None:
            return ("collection", int(self._active_collection_id))
        if self._active_smart_collection_key:
            return ("smart_collection", str(self._active_smart_collection_key))
        return ("none",)

    def _collect_text_scope_entries(self, folders: list[str] | None = None, collection_id: int | None = None) -> list[dict]:
        if folders:
            return self._get_reconciled_candidates(folders, "all", "")
        if collection_id is not None:
            return self._get_collection_candidates(collection_id, "all", "")
        if self._selected_folders:
            return self._get_reconciled_candidates(self._selected_folders, "all", "")
        if self._active_collection_id is not None:
            return self._get_collection_candidates(self._active_collection_id, "all", "")
        if self._active_smart_collection_key:
            return self._get_smart_collection_candidates(self._active_smart_collection_key, "all", "")
        return []

    def _ensure_background_text_processing(
        self,
        folders: list[str] | None = None,
        collection_id: int | None = None,
        *,
        allow_concurrent_scan: bool = False,
        force: bool = False,
        rescan_existing: bool = False,
    ) -> None:
        if not force and not self._scanner_enabled("text_detection"):
            self._set_scanner_status("text_detection", "Disabled")
            return
        scope_key = self._current_text_scope_key(folders, collection_id)
        if scope_key == ("none",):
            self._set_scanner_status("text_detection", "Idle (no active scope)")
            return
        if self._text_processing_active and not self._text_processing_paused and self._text_processing_scope_key == scope_key:
            self._set_scanner_status("text_detection", "Already running")
            return

        self._text_processing_generation += 1
        generation = self._text_processing_generation
        self._text_processing_paused = False
        self._text_processing_active = True
        self._text_processing_scope_key = scope_key
        if self._scan_lock.locked() and not allow_concurrent_scan:
            self._set_scanner_status("text_detection", "Waiting for scan")
            self.textProcessingStarted.emit(self._text_stage_label("waiting"), 0)
        else:
            self._set_scanner_status("text_detection", "Running")

        resolved_folders = list(folders) if folders else (list(self._selected_folders) if self._selected_folders else [])
        resolved_collection_id = collection_id if collection_id is not None else self._active_collection_id

        def work() -> None:
            try:
                if allow_concurrent_scan:
                    if not self._text_processing_should_continue(generation):
                        return
                    entries = self._collect_text_scope_entries(resolved_folders, resolved_collection_id)
                    if not entries:
                        return
                    self._backfill_scope_text_detection(entries, generation, rescan_existing=rescan_existing)
                else:
                    with self._scan_lock:
                        if not self._text_processing_should_continue(generation):
                            return
                        entries = self._collect_text_scope_entries(resolved_folders, resolved_collection_id)
                        if not entries:
                            return
                        self._backfill_scope_text_detection(entries, generation, rescan_existing=rescan_existing)
            except Exception as exc:
                try:
                    self._log(f"Background text processing failed: {exc}")
                except Exception:
                    pass
            finally:
                if generation == self._text_processing_generation:
                    if not self._text_processing_paused:
                        self.textProcessingFinished.emit()
                        self._set_scanner_status("text_detection", "Idle", mark_run=True)
                    self._text_processing_active = False
                    self._text_processing_thread = None

        thread = threading.Thread(target=work, daemon=True, name="text-processing")
        self._text_processing_thread = thread
        thread.start()

    @Slot()
    def resume_text_processing(self) -> None:
        self._ensure_background_text_processing(allow_concurrent_scan=True, force=True)

    @Slot()
    def pause_text_processing(self) -> None:
        self._text_processing_paused = True

    @Slot()
    def reveal_progress_toasts(self) -> None:
        self.progressToastsRevealRequested.emit()

    def _backfill_scope_text_detection(
        self,
        entries: list[dict],
        generation: int | None = None,
        *,
        rescan_existing: bool = False,
    ) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_DETECTION_VERSION, detect_text_presence
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and (
                rescan_existing
                or not (
                entry.get("text_likely") is not None
                and int(entry.get("text_detection_version") or 0) >= TEXT_DETECTION_VERSION
                )
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("detected"), total_eligible)
        updates: list[tuple] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder"):
                continue
            if (
                not rescan_existing
                and entry.get("text_likely") is not None
                and int(entry.get("text_detection_version") or 0) >= TEXT_DETECTION_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("detected"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_likely, text_score = detect_text_presence(analysis_path, source_path=path)
            except Exception:
                text_likely, text_score = False, 0.0
            existing_positive = (not rescan_existing) and self._has_existing_positive_text_signal(entry)
            if existing_positive and not text_likely:
                text_likely = True
                text_score = max(float(entry.get("text_detection_score") or 0.0), float(text_score or 0.0))
            entry["text_likely"] = bool(text_likely)
            entry["text_detection_score"] = float(text_score or 0.0)
            entry["text_detection_version"] = TEXT_DETECTION_VERSION
            if rescan_existing:
                entry["text_more_likely"] = None
                entry["text_more_likely_score"] = 0.0
                entry["text_more_likely_version"] = 0
                entry["text_verified"] = None
                entry["text_verification_score"] = 0.0
                entry["text_verification_version"] = 0
                updates.append((1 if text_likely else 0, float(text_score or 0.0), TEXT_DETECTION_VERSION, None, 0.0, 0, None, 0.0, 0, path))
            else:
                updates.append((1 if text_likely else 0, float(text_score or 0.0), TEXT_DETECTION_VERSION, path))
        try:
            if updates:
                if rescan_existing:
                    self.conn.executemany(
                        "UPDATE media_items SET text_likely = ?, text_detection_score = ?, text_detection_version = ?, text_more_likely = ?, text_more_likely_score = ?, text_more_likely_version = ?, text_verified = ?, text_verification_score = ?, text_verification_version = ? WHERE path = ?",
                        updates,
                    )
                else:
                    self.conn.executemany(
                        "UPDATE media_items SET text_likely = ?, text_detection_score = ?, text_detection_version = ? WHERE path = ?",
                        updates,
                    )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text detection backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible and completed:
                self.textProcessingFinished.emit()
        return completed

    def _backfill_scope_text_more_likely(self, entries: list[dict], generation: int | None = None) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_MORE_LIKELY_VERSION, verify_text_presence_opencv
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and bool(entry.get("text_likely"))
            and not (
                entry.get("text_more_likely") is not None
                and int(entry.get("text_more_likely_version") or 0) >= TEXT_MORE_LIKELY_VERSION
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("more_likely"), total_eligible)
        updates: list[tuple[int, float, int, str]] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder") or not bool(entry.get("text_likely")):
                continue
            if (
                entry.get("text_more_likely") is not None
                and int(entry.get("text_more_likely_version") or 0) >= TEXT_MORE_LIKELY_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("more_likely"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_more_likely, score = verify_text_presence_opencv(analysis_path)
            except Exception:
                text_more_likely, score = False, 0.0
            entry["text_more_likely"] = bool(text_more_likely)
            entry["text_more_likely_score"] = float(score or 0.0)
            entry["text_more_likely_version"] = TEXT_MORE_LIKELY_VERSION
            updates.append((1 if text_more_likely else 0, float(score or 0.0), TEXT_MORE_LIKELY_VERSION, path))
        try:
            if updates:
                self.conn.executemany(
                    "UPDATE media_items SET text_more_likely = ?, text_more_likely_score = ?, text_more_likely_version = ? WHERE path = ?",
                    updates,
                )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text more likely backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible:
                self.textProcessingFinished.emit()
        return completed

    def _backfill_scope_text_verification(self, entries: list[dict], generation: int | None = None) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_VERIFICATION_VERSION, verify_text_presence_windows_ocr
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and bool(entry.get("text_more_likely"))
            and not (
                entry.get("text_verified") is not None
                and int(entry.get("text_verification_version") or 0) >= TEXT_VERIFICATION_VERSION
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("verified"), total_eligible)
        updates: list[tuple[int, float, int, str]] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder") or not bool(entry.get("text_more_likely")):
                continue
            if (
                entry.get("text_verified") is not None
                and int(entry.get("text_verification_version") or 0) >= TEXT_VERIFICATION_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("verified"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_verified, verify_score = verify_text_presence_windows_ocr(analysis_path)
            except Exception:
                text_verified, verify_score = False, 0.0
            entry["text_verified"] = bool(text_verified)
            entry["text_verification_score"] = float(verify_score or 0.0)
            entry["text_verification_version"] = TEXT_VERIFICATION_VERSION
            updates.append((1 if text_verified else 0, float(verify_score or 0.0), TEXT_VERIFICATION_VERSION, path))
        try:
            if updates:
                self.conn.executemany(
                    "UPDATE media_items SET text_verified = ?, text_verification_score = ?, text_verification_version = ? WHERE path = ?",
                    updates,
                )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text verification backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible:
                self.textProcessingFinished.emit()
        return completed

    def _run_ocr_text_scanner(self, folders: list[str] | None = None, *, force: bool = False) -> bool:
        if self._ocr_text_processing_active:
            self._set_scanner_status("ocr_text", "Already running")
            return False
        if not force and not self._scanner_enabled("ocr_text"):
            self._set_scanner_status("ocr_text", "Disabled")
            return False
        entries = self._collect_text_scope_entries(folders=folders)
        if not entries:
            self._set_scanner_status("ocr_text", "Idle (no active scope)")
            return False
        selected_sources: list[str] = []
        if self._ocr_scanner_run_fast():
            selected_sources.append("paddle_fast")
        if self._ocr_scanner_run_ai():
            selected_sources.append("gemma4")
        if not selected_sources:
            self._set_scanner_status("ocr_text", "Idle (no OCR engines selected)")
            return False
        try:
            self._ocr_text_cancel.clear()
        except Exception:
            self._ocr_text_cancel = threading.Event()

        def work() -> None:
            self._ocr_text_processing_active = True
            self._set_scanner_status("ocr_text", "Running")
            processed = 0
            saved = 0
            try:
                from app.mediamanager.db.media_repo import add_media_item
                from app.mediamanager.db.ocr_repo import ensure_ocr_tables

                ensure_ocr_tables(self.conn)

                def has_ocr_source(media_id: int, source: str) -> bool:
                    try:
                        row = self.conn.execute(
                            "SELECT 1 FROM media_ocr_results WHERE media_id = ? AND source = ? LIMIT 1",
                            (int(media_id), str(source or "")),
                        ).fetchone()
                        return bool(row)
                    except Exception:
                        return False

                eligible = []
                for entry in entries:
                    if entry.get("is_folder"):
                        continue
                    if not self._ocr_scanner_all_files() and not self._effective_text_detected(entry):
                        continue
                    media_id = int(entry.get("id") or -1)
                    if media_id >= 0 and all(has_ocr_source(media_id, source) for source in selected_sources):
                        continue
                    if media_id < 0 or force or not str(entry.get("detected_text") or "").strip():
                        eligible.append(entry)
                total = len(eligible)
                if total <= 0:
                    self._set_scanner_status("ocr_text", "Idle (no eligible files)", mark_run=True)
                    return
                for entry in eligible:
                    if getattr(self, "_ocr_text_cancel", None) is not None and self._ocr_text_cancel.is_set():
                        self._set_scanner_status("ocr_text", f"Canceled ({processed} / {total}, {saved} saved)", mark_run=True)
                        return
                    processed += 1
                    self._set_scanner_status("ocr_text", f"Running {processed} / {total}")
                    path = str(entry.get("path") or "").strip()
                    if not path:
                        continue
                    try:
                        p = Path(path)
                        if not p.exists() or not p.is_file():
                            continue
                        if int(entry.get("id") or -1) < 0:
                            media_type = str(entry.get("media_type") or "")
                            real_path = str(entry.get("_real_path") or path)
                            media_id = add_media_item(self.conn, real_path, media_type)
                            entry["id"] = media_id
                        else:
                            media_id = int(entry.get("id") or -1)
                        ocr_source_path = self._manual_ocr_source_path(p)
                        for source in selected_sources:
                            if media_id >= 0 and has_ocr_source(media_id, source):
                                continue
                            if source == "gemma4":
                                payload = self._run_gemma_ocr_worker(ocr_source_path, media_id)
                            else:
                                payload = self._run_paddle_ocr_worker(ocr_source_path, "fast")
                            text = self._save_ocr_payload(path, payload, select_as_winner=False)
                            if not text.strip():
                                continue
                            entry["detected_text"] = text
                            saved += 1
                    except Exception as exc:
                        try:
                            self._log(f"OCR text scanner failed for {path}: {exc}")
                        except Exception:
                            pass
                self._set_scanner_status("ocr_text", f"Idle ({saved} saved)", mark_run=True)
                if saved:
                    self.galleryScopeChanged.emit()
            except Exception as exc:
                self._set_scanner_status("ocr_text", f"Error: {exc}")
            finally:
                self._ocr_text_processing_active = False
                try:
                    self._ocr_text_cancel.clear()
                except Exception:
                    pass
                try:
                    self.scannerStatusChanged.emit("ocr_text", self._scanner_status_payload("ocr_text"))
                except Exception:
                    pass

        threading.Thread(target=work, daemon=True, name="ocr-text-scanner").start()
        return True

    @Slot(str, result=bool)
    def cancel_scanner(self, scanner_key: str) -> bool:
        key = str(scanner_key or "").strip()
        if key == "ocr_text" and self._ocr_text_processing_active:
            self._ocr_text_cancel.set()
            self._set_scanner_status("ocr_text", "Canceling...")
            return True
        return False

    def _backfill_scope_content_hashes(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import calculate_media_content_hash

        updates: list[tuple[str, str]] = []
        for entry in entries:
            if entry.get("is_folder"):
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            media_type = str(entry.get("media_type") or "").strip().lower()
            existing_hash = str(entry.get("content_hash") or "").strip()
            if existing_hash and media_type != "image":
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                content_hash = calculate_media_content_hash(p)
            except Exception:
                content_hash = ""
            if not content_hash:
                continue
            if content_hash == existing_hash:
                continue
            entry["content_hash"] = content_hash
            updates.append((content_hash, path))
        if not updates:
            return
        try:
            self.conn.executemany("UPDATE media_items SET content_hash = ? WHERE path = ?", updates)
            self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"content hash backfill failed: {exc}")
            except Exception:
                pass

    def _backfill_scope_ai_decisions(self, entries: list[dict]) -> None:
        from app.mediamanager.db.ai_metadata_repo import get_media_ai_metadata
        from app.mediamanager.db.media_repo import add_media_item
        from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported

        for entry in entries:
            if entry.get("is_folder") or entry.get("is_ai_detected") is not None:
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                media_type = str(entry.get("media_type") or "")
                if int(entry.get("id") or -1) < 0:
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                inspect_and_persist_if_supported(self.conn, int(entry["id"]), path, media_type)
                ai_meta = get_media_ai_metadata(self.conn, int(entry["id"])) or {}
                entry["is_ai_detected"] = bool(ai_meta.get("is_ai_detected")) if ai_meta else False
                entry["is_ai_confidence"] = float(ai_meta.get("is_ai_confidence") or 0.0) if ai_meta else 0.0
                entry["user_confirmed_ai"] = ai_meta.get("user_confirmed_ai")
                entry["effective_is_ai"] = bool(ai_meta.get("user_confirmed_ai")) if ai_meta.get("user_confirmed_ai") is not None else bool(entry["is_ai_detected"])
            except Exception as exc:
                try:
                    self._log(f"ai decision backfill failed for {path}: {exc}")
                except Exception:
                    pass
                entry["is_ai_detected"] = False
                entry["is_ai_confidence"] = 0.0
                entry["user_confirmed_ai"] = None
                entry["effective_is_ai"] = False

    def _similarity_config(self) -> tuple[int, int]:
        level = self._gallery_similarity_threshold()
        mapping = {
            "very_low": (5, 2),
            "low": (9, 2),
            "medium": (12, 2),
            "high": (15, 1),
            "very_high": (18, 1),
        }
        return mapping.get(level, (12, 2))

    def _gallery_group_date_granularity(self) -> str:
        value = str(self.settings.value("gallery/group_date_granularity", "day", type=str) or "day")
        allowed = {"day", "month", "year"}
        return value if value in allowed else "day"

    def _mute_video_by_default_enabled(self) -> bool:
        return bool(self.settings.value("gallery/mute_video_by_default", True, type=bool))

    def _autoplay_gallery_animated_gifs_enabled(self) -> bool:
        if self.settings.contains("player/autoplay_gallery_animated_gifs"):
            return bool(self.settings.value("player/autoplay_gallery_animated_gifs", True, type=bool))
        return bool(self.settings.value("player/autoplay_animated_gifs", True, type=bool))

    def _autoplay_preview_animated_gifs_enabled(self) -> bool:
        if self.settings.contains("player/autoplay_preview_animated_gifs"):
            return bool(self.settings.value("player/autoplay_preview_animated_gifs", True, type=bool))
        return bool(self.settings.value("player/autoplay_animated_gifs", True, type=bool))

    def _video_loop_mode(self) -> str:
        value = str(self.settings.value("player/video_loop_mode", "short", type=str) or "short").strip().lower()
        return value if value in {"all", "none", "short"} else "short"

    def _video_loop_cutoff_seconds(self) -> int:
        raw = self.settings.value("player/video_loop_cutoff_seconds", "90", type=str)
        try:
            seconds = int(str(raw or "90").strip())
        except Exception:
            seconds = 90
        return max(1, seconds)

    def _should_loop_video(self, duration_ms: int) -> bool:
        mode = self._video_loop_mode()
        if mode == "all":
            return True
        if mode == "none":
            return False
        duration_ms = int(duration_ms or 0)
        cutoff_ms = self._video_loop_cutoff_seconds() * 1000
        return 0 < duration_ms < cutoff_ms

    @Slot(result=dict)
    def get_settings(self) -> dict:
        try:
            data = {
                "gallery.randomize": self._randomize_enabled(),
                "gallery.restore_last": self._restore_last_enabled(),
                "gallery.show_hidden": self._show_hidden_enabled(),
                "gallery.include_nested_files": self._gallery_include_nested_files_enabled(),
                "gallery.show_folders": self._gallery_show_folders_enabled(),
                "gallery.use_recycle_bin": bool(self.settings.value("gallery/use_recycle_bin", True, type=bool)),
                "gallery.mute_video_by_default": self._mute_video_by_default_enabled(),
                "player.autoplay_gallery_animated_gifs": self._autoplay_gallery_animated_gifs_enabled(),
                "player.autoplay_preview_animated_gifs": self._autoplay_preview_animated_gifs_enabled(),
                "player.video_loop_mode": self._video_loop_mode(),
                "player.video_loop_cutoff_seconds": self._video_loop_cutoff_seconds(),
                "gallery.start_folder": self._start_folder_setting(),
                "gallery.view_mode": self._gallery_view_mode(),
                "gallery.group_by": self._gallery_group_by(),
                "gallery.group_date_granularity": self._gallery_group_date_granularity(),
                "gallery.similarity_threshold": self._gallery_similarity_threshold(),
                "duplicate.settings.active_tab": str(self.settings.value("duplicate/settings/active_tab", "rules", type=str) or "rules"),
                "ui.accent_color": str(self.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8"),
                "ui.show_top_panel": bool(self.settings.value("ui/show_top_panel", True, type=bool)),
                "ui.show_left_panel": bool(self.settings.value("ui/show_left_panel", True, type=bool)),
                "ui.show_right_panel": bool(self.settings.value("ui/show_right_panel", True, type=bool)),
                "ui.show_bottom_panel": bool(self.settings.value("ui/show_bottom_panel", True, type=bool)),
                "ui.show_dismissed_progress_toasts": bool(self.settings.value("ui/show_dismissed_progress_toasts", False, type=bool)),
                "ui.show_splash_screen": bool(self.settings.value("ui/show_splash_screen", True, type=bool)),
                "ui.advanced_search_expanded": bool(self.settings.value("ui/advanced_search_expanded", False, type=bool)),
                "ui.advanced_search_saved_queries": str(self.settings.value(
                    "ui/advanced_search_saved_queries",
                    json.dumps([
                        {"name": "Date Range and Search Term", "query": "original-file-date:>=2024-01-06 AND original-file-date:<=2026-04-01 AND"},
                        {"name": "File Size Range and Search Term", "query": "size:>=1kb AND size:<=100kb AND"},
                    ]),
                    type=str,
                ) or "[]"),
                "ui.preview_above_details": self._preview_above_details_enabled(),
                "ui.theme_mode": str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"),
                "metadata.display.res": bool(self.settings.value("metadata/display/res", True, type=bool)),
                "metadata.display.size": bool(self.settings.value("metadata/display/size", True, type=bool)),
                "metadata.display.exifdatetaken": bool(self.settings.value("metadata/display/exifdatetaken", False, type=bool)),
                "metadata.display.metadatadate": bool(self.settings.value("metadata/display/metadatadate", False, type=bool)),
                "metadata.display.originalfiledate": bool(self.settings.value("metadata/display/originalfiledate", self.settings.value("metadata/display/filecreateddate", False, type=bool), type=bool)),
                "metadata.display.filecreateddate": bool(self.settings.value("metadata/display/filecreateddate", False, type=bool)),
                "metadata.display.filemodifieddate": bool(self.settings.value("metadata/display/filemodifieddate", False, type=bool)),
                "metadata.display.textdetected": bool(self.settings.value("metadata/display/textdetected", True, type=bool)),
                "metadata.display.description": bool(self.settings.value("metadata/display/description", True, type=bool)),
                "metadata.display.tags": bool(self.settings.value("metadata/display/tags", True, type=bool)),
                "metadata.display.notes": bool(self.settings.value("metadata/display/notes", True, type=bool)),
                "metadata.display.camera": bool(self.settings.value("metadata/display/camera", False, type=bool)),
                "metadata.display.location": bool(self.settings.value("metadata/display/location", False, type=bool)),
                "metadata.display.iso": bool(self.settings.value("metadata/display/iso", False, type=bool)),
                "metadata.display.shutter": bool(self.settings.value("metadata/display/shutter", False, type=bool)),
                "metadata.display.aperture": bool(self.settings.value("metadata/display/aperture", False, type=bool)),
                "metadata.display.software": bool(self.settings.value("metadata/display/software", False, type=bool)),
                "metadata.display.lens": bool(self.settings.value("metadata/display/lens", False, type=bool)),
                "metadata.display.dpi": bool(self.settings.value("metadata/display/dpi", False, type=bool)),
                "metadata.display.embeddedtags": bool(self.settings.value("metadata/display/embeddedtags", True, type=bool)),
                "metadata.display.embeddedcomments": bool(self.settings.value("metadata/display/embeddedcomments", True, type=bool)),
                "metadata.display.embeddedmetadata": bool(self.settings.value("metadata/display/embeddedmetadata", True, type=bool)),
                "metadata.display.aistatus": bool(self.settings.value("metadata/display/aistatus", True, type=bool)),
                "metadata.display.aigenerated": bool(self.settings.value("metadata/display/aigenerated", True, type=bool)),
                "metadata.display.aisource": bool(self.settings.value("metadata/display/aisource", True, type=bool)),
                "metadata.display.aifamilies": bool(self.settings.value("metadata/display/aifamilies", True, type=bool)),
                "metadata.display.aidetectionreasons": bool(self.settings.value("metadata/display/aidetectionreasons", False, type=bool)),
                "metadata.display.ailoras": bool(self.settings.value("metadata/display/ailoras", True, type=bool)),
                "metadata.display.aimodel": bool(self.settings.value("metadata/display/aimodel", True, type=bool)),
                "metadata.display.aicheckpoint": bool(self.settings.value("metadata/display/aicheckpoint", False, type=bool)),
                "metadata.display.aisampler": bool(self.settings.value("metadata/display/aisampler", True, type=bool)),
                "metadata.display.aischeduler": bool(self.settings.value("metadata/display/aischeduler", True, type=bool)),
                "metadata.display.aicfg": bool(self.settings.value("metadata/display/aicfg", True, type=bool)),
                "metadata.display.aisteps": bool(self.settings.value("metadata/display/aisteps", True, type=bool)),
                "metadata.display.aiseed": bool(self.settings.value("metadata/display/aiseed", True, type=bool)),
                "metadata.display.aiupscaler": bool(self.settings.value("metadata/display/aiupscaler", False, type=bool)),
                "metadata.display.aidenoise": bool(self.settings.value("metadata/display/aidenoise", False, type=bool)),
                "metadata.display.aiprompt": bool(self.settings.value("metadata/display/aiprompt", True, type=bool)),
                "metadata.display.ainegprompt": bool(self.settings.value("metadata/display/ainegprompt", True, type=bool)),
                "metadata.display.aiparams": bool(self.settings.value("metadata/display/aiparams", True, type=bool)),
                "metadata.display.aiworkflows": bool(self.settings.value("metadata/display/aiworkflows", False, type=bool)),
                "metadata.display.aiprovenance": bool(self.settings.value("metadata/display/aiprovenance", False, type=bool)),
                "metadata.display.aicharcards": bool(self.settings.value("metadata/display/aicharcards", False, type=bool)),
                "metadata.display.airawpaths": bool(self.settings.value("metadata/display/airawpaths", False, type=bool)),
                "metadata.display.order": self.settings.value("metadata/display/order", "[]", type=str),
                "updates.check_on_launch": bool(self.settings.value("updates/check_on_launch", True, type=bool)),
            }
            for scanner_key in ("text_detection", "ocr_text"):
                payload = self._scanner_status_payload(scanner_key)
                data[f"scanners.{scanner_key}.enabled"] = payload["enabled"]
                data[f"scanners.{scanner_key}.interval_hours"] = payload["interval_hours"]
                data[f"scanners.{scanner_key}.last_run_utc"] = payload["last_run_utc"]
                data[f"scanners.{scanner_key}.status"] = payload["status"]
            for qkey in self.settings.allKeys():
                if qkey.startswith("metadata/display/") or qkey.startswith("metadata/layout/") or qkey.startswith("duplicate/"):
                    data[qkey.replace("/", ".")] = self._coerce_setting_value(self.settings.value(qkey))
            return data
        except Exception:
            return {
                "gallery.randomize": False,
                "gallery.restore_last": False,
                "gallery.show_hidden": False,
                "gallery.include_nested_files": True,
                "gallery.show_folders": True,
                "gallery.use_recycle_bin": True,
                "gallery.mute_video_by_default": True,
                "player.autoplay_gallery_animated_gifs": True,
                "player.autoplay_preview_animated_gifs": True,
                "player.video_loop_mode": "short",
                "player.video_loop_cutoff_seconds": 90,
                "gallery.start_folder": "",
                "gallery.view_mode": "masonry",
                "gallery.group_by": "none",
                "gallery.group_date_granularity": "day",
                "gallery.similarity_threshold": "low",
                "duplicate.settings.active_tab": "rules",
                "ui.accent_color": "#8ab4f8",
                "ui.show_top_panel": True,
                "ui.show_left_panel": True,
                "ui.show_right_panel": True,
                "ui.show_bottom_panel": True,
                "ui.show_dismissed_progress_toasts": False,
                "ui.show_splash_screen": True,
                "ui.advanced_search_expanded": False,
                "ui.advanced_search_saved_queries": json.dumps([
                    {"name": "Date Range and Search Term", "query": "original-file-date:>=2024-01-06 AND original-file-date:<=2026-04-01 AND"},
                    {"name": "File Size Range and Search Term", "query": "size:>=1kb AND size:<=100kb AND"},
                ]),
                "ui.preview_above_details": True,
                "ui.theme_mode": "dark",
            }



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
