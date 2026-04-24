from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeCompareUpdatesMixin:
    def _normalize_compare_slot_name(self, slot_name: str) -> str:
        return "right" if str(slot_name or "").strip().lower() == "right" else "left"

    def _ensure_compare_media_record(self, path: str) -> dict:
        from app.mediamanager.db.media_repo import add_media_item, get_media_by_path

        clean = str(path or "").strip()
        if not clean:
            return {}
        media = get_media_by_path(self.conn, clean)
        if media:
            return media
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return {}
        media_type = "image" if p.suffix.lower() in (IMAGE_EXTS | {".tif", ".tiff", ".heic", ".heif"}) else "video"
        add_media_item(self.conn, clean, media_type)
        return get_media_by_path(self.conn, clean) or {}

    def _build_compare_entry(self, path: str) -> dict:
        from app.mediamanager.utils.hashing import calculate_media_content_hash
        from app.mediamanager.db.metadata_repo import get_media_metadata
        from app.mediamanager.db.ai_metadata_repo import get_media_ai_metadata
        from app.mediamanager.db.tags_repo import list_media_tags

        clean = str(path or "").strip()
        if not clean:
            return {}
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return {}
        media = dict(self._ensure_compare_media_record(clean) or {})
        try:
            stat = p.stat()
        except Exception:
            stat = None
        width = int(media.get("width") or 0)
        height = int(media.get("height") or 0)
        if width <= 0 or height <= 0:
            try:
                reader = QImageReader(clean)
                reader.setAutoTransform(True)
                size = reader.size()
                if size.isValid():
                    width = max(width, size.width())
                    height = max(height, size.height())
            except Exception:
                pass
        file_size = int(media.get("file_size") or 0)
        if file_size <= 0 and stat is not None:
            file_size = int(stat.st_size)
        modified_time = self._iso_to_ns(media.get("modified_time"))
        file_created_time = self._iso_to_ns(media.get("file_created_time"))
        original_file_date = self._iso_to_ns(media.get("original_file_date"))
        if modified_time <= 0 and stat is not None:
            modified_time = int(stat.st_mtime_ns)
        if file_created_time <= 0 and stat is not None:
            file_created_time = int(stat.st_ctime_ns)
        if original_file_date <= 0:
            original_file_date = self._normalized_file_date_ns(file_created_time, modified_time)
        content_hash = str(media.get("content_hash") or "").strip()
        if not content_hash or str(media.get("media_type") or "") == "image":
            try:
                content_hash = calculate_media_content_hash(p)
            except Exception:
                content_hash = ""
            if content_hash:
                media["content_hash"] = content_hash
                try:
                    self.conn.execute("UPDATE media_items SET content_hash = ? WHERE path = ?", (content_hash, clean))
                    self.conn.commit()
                except Exception:
                    pass
        media_id = int(media.get("id") or 0)
        meta = get_media_metadata(self.conn, media_id) if media_id > 0 else {}
        ai_meta = get_media_ai_metadata(self.conn, media_id) if media_id > 0 else {}
        tags = ", ".join(list_media_tags(self.conn, media_id)) if media_id > 0 else ""
        collection_names = ""
        if media_id > 0:
            try:
                row = self.conn.execute(
                    """
                    SELECT GROUP_CONCAT(c.name, ', ')
                    FROM collections c
                    JOIN collection_items ci ON c.id = ci.collection_id
                    WHERE ci.media_id = ?
                    """,
                    (media_id,),
                ).fetchone()
                collection_names = str(row[0] or "") if row else ""
            except Exception:
                collection_names = ""
        entry = {
            "path": clean,
            "name": p.name,
            "media_type": str(media.get("media_type") or "image"),
            "file_size": file_size,
            "width": width,
            "height": height,
            "modified_time": modified_time,
            "file_created_time": file_created_time,
            "original_file_date": original_file_date,
            "exif_date_taken": media.get("exif_date_taken") or "",
            "metadata_date": media.get("metadata_date") or "",
            "preferred_date": 0,
            "content_hash": content_hash,
            "phash": media.get("phash") or "",
            "tags": tags,
            "title": (meta or {}).get("title") or "",
            "description": ((meta or {}).get("description") or (ai_meta or {}).get("description") or ""),
            "notes": (meta or {}).get("notes") or "",
            "collection_names": collection_names,
            "ai_prompt": ((meta or {}).get("ai_prompt") or (ai_meta or {}).get("ai_prompt") or ""),
            "ai_loras": ", ".join(str(item.get("name") or "").strip() for item in ((ai_meta or {}).get("loras") or []) if str(item.get("name") or "").strip()),
            "model_name": (ai_meta or {}).get("model_name") or "",
            "text_detected": media.get("effective_text_detected"),
            "raw_text_likely": media.get("text_likely"),
            "user_confirmed_text_detected": media.get("user_confirmed_text_detected"),
            "detected_text": media.get("detected_text") or "",
        }
        entry["preferred_date"] = self._preferred_date_ns(entry)
        entry["file_size_text"] = self._format_file_size(file_size)
        entry["resolution_text"] = f"{width} x {height}" if width > 0 and height > 0 else ""
        entry["modified_time_text"] = self._format_compare_datetime(modified_time)
        return entry

    def _format_file_size(self, file_size: int) -> str:
        size = float(file_size or 0)
        if size <= 0:
            return ""
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        return f"{size:.1f} {units[unit_index]}" if unit_index else f"{int(size)} B"

    def _format_compare_datetime(self, value_ns: int) -> str:
        try:
            if int(value_ns or 0) <= 0:
                return ""
            dt = datetime.fromtimestamp(int(value_ns) / 1_000_000_000, tz=timezone.utc).astimezone()
            return dt.strftime("%Y-%m-%d %I:%M %p").lstrip("0")
        except Exception:
            return ""

    def _build_compare_payload(self) -> dict:
        slot_entries: dict[str, dict] = {}
        ranked_entries: list[dict] = []
        for slot_name in ("left", "right"):
            entry = self._build_compare_entry(self._compare_paths.get(slot_name, ""))
            slot_entries[slot_name] = entry
            if entry:
                ranked_entries.append(dict(entry))
        ranked = self._rank_duplicate_group(ranked_entries) if ranked_entries else []
        if ranked:
            preferred_scores = [int(entry.get("duplicate_preferred_folder_score") or 0) for entry in ranked]
            max_preferred_score = max(preferred_scores, default=0)
            min_preferred_score = min(preferred_scores, default=0)
            if max_preferred_score > 0 and max_preferred_score > min_preferred_score:
                for entry in ranked:
                    if int(entry.get("duplicate_preferred_folder_score") or 0) != max_preferred_score:
                        continue
                    reasons = list(entry.get("duplicate_category_reasons") or [])
                    if "Preferred Folder" not in reasons:
                        reasons.append("Preferred Folder")
                    entry["duplicate_category_reasons"] = reasons
                    entry["duplicate_best_reason"] = f" {chr(8226)} ".join(reasons)
        ranked_by_path = {str(entry.get("path") or ""): entry for entry in ranked}
        active_paths = {str(entry.get("path") or "") for entry in slot_entries.values() if entry}
        active_entries = [entry for entry in slot_entries.values() if entry]
        compare_identical_pair = (
            len(active_entries) == 2
            and all(str(entry.get("content_hash") or "").strip() for entry in active_entries)
            and len({str(entry.get("content_hash") or "").strip() for entry in active_entries}) == 1
        )
        overall_best_in_pair = self._compare_best_path if self._compare_best_path in active_paths else ""
        ranked_best_entry = ranked[0] if ranked else {}
        ranked_best_path = str(ranked_best_entry.get("path") or "")
        ranked_best_is_tie = bool(ranked_best_entry.get("duplicate_rank_tied_with_next"))
        comparison_best_path = ranked_best_path
        comparison_best_reason = ""
        if overall_best_in_pair:
            if ranked_best_is_tie or not ranked_best_path or ranked_best_path == overall_best_in_pair:
                comparison_best_path = overall_best_in_pair
            else:
                comparison_best_reason = str(ranked_best_entry.get("duplicate_best_reason") or "").strip()
        self._compare_keep_paths = {path for path in self._compare_keep_paths if path in active_paths}
        self._compare_delete_paths = {path for path in self._compare_delete_paths if path in active_paths}
        payload = {
            "visible": bool(self.settings.value("ui/show_bottom_panel", True, type=bool)),
            "left": {},
            "right": {},
            "best_path": self._compare_best_path,
            "comparison_best_path": comparison_best_path,
            "comparison_best_reason": comparison_best_reason,
            "compare_identical_pair": compare_identical_pair,
            "keep_paths": list(self._compare_keep_paths),
            "delete_paths": list(self._compare_delete_paths),
            "selection_revision": int(self._compare_selection_revision),
        }
        for slot_name, base_entry in slot_entries.items():
            path = str(base_entry.get("path") or "")
            entry = dict(ranked_by_path.get(path) or base_entry or {})
            if entry:
                entry["compare_keep_checked"] = path in self._compare_keep_paths
                entry["compare_delete_checked"] = path in self._compare_delete_paths
                entry["compare_marked_best"] = bool(self._compare_best_path) and path == self._compare_best_path
                entry["compare_best_in_pair"] = path == comparison_best_path
                entry["compare_best_reason"] = comparison_best_reason if path == comparison_best_path else ""
                entry["compare_identical_pair"] = compare_identical_pair
            payload[slot_name] = entry
        return payload

    def _emit_compare_state_changed(self) -> None:
        if self._compare_state_emit_pending:
            return
        self._compare_state_emit_pending = True

        def _emit() -> None:
            self._compare_state_emit_pending = False
            state = self.get_compare_state()
            self.compareStateChanged.emit(state)

        QTimer.singleShot(0, _emit)

    @Slot(result="QVariantMap")
    def get_compare_state(self) -> dict:
        return self._build_compare_payload()

    @Slot()
    def open_compare_panel(self) -> None:
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str)
    def clear_compare_slot(self, slot_name: str) -> None:
        slot = self._normalize_compare_slot_name(slot_name)
        self._compare_paths[slot] = ""
        self._emit_compare_state_changed()

    @Slot(str, str)
    def set_compare_path(self, slot_name: str, path: str) -> None:
        slot = self._normalize_compare_slot_name(slot_name)
        clean = str(path or "").strip()
        if not clean:
            return
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return
        self._compare_paths[slot] = str(p.absolute())
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str, str)
    def swap_compare_slots(self, source_slot: str, target_slot: str) -> None:
        src = self._normalize_compare_slot_name(source_slot)
        dst = self._normalize_compare_slot_name(target_slot)
        if src == dst:
            return
        self._compare_paths[src], self._compare_paths[dst] = self._compare_paths.get(dst, ""), self._compare_paths.get(src, "")
        self._emit_compare_state_changed()

    @Slot(list)
    def compare_paths(self, paths: list[str]) -> None:
        clean = [str(Path(path).absolute()) for path in (paths or []) if str(path or "").strip()]
        if not clean:
            return
        self._compare_paths["left"] = clean[0]
        if len(clean) > 1:
            self._compare_paths["right"] = clean[1]
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str)
    def compare_path_auto(self, path: str) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        slot = "left" if not self._compare_paths.get("left") else "right" if not self._compare_paths.get("right") else "right"
        self.set_compare_path(slot, clean)

    @Slot()
    def settings_modal_opened(self) -> None:
        if self._settings_modal_bottom_restore is not None:
            return
        was_visible = bool(self.settings.value("ui/show_bottom_panel", True, type=bool))
        self._settings_modal_bottom_restore = was_visible
        if was_visible:
            self.set_setting_bool("ui.show_bottom_panel", False)

    @Slot()
    def settings_modal_closed(self) -> None:
        restore = self._settings_modal_bottom_restore
        self._settings_modal_bottom_restore = None
        if restore:
            self.set_setting_bool("ui.show_bottom_panel", True)

    @Slot(str, bool)
    def set_compare_keep_path(self, path: str, checked: bool) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        before = clean in self._compare_keep_paths
        delete_before = clean in self._compare_delete_paths
        if checked:
            self._compare_keep_paths.add(clean)
            self._compare_delete_paths.discard(clean)
        else:
            self._compare_keep_paths.discard(clean)
        after = clean in self._compare_keep_paths
        delete_after = clean in self._compare_delete_paths
        if before == after and delete_before == delete_after:
            return
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot(str, bool)
    def set_compare_delete_path(self, path: str, checked: bool) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        before = clean in self._compare_delete_paths
        keep_before = clean in self._compare_keep_paths
        best_before = self._compare_best_path == clean
        if checked:
            self._compare_delete_paths.add(clean)
            self._compare_keep_paths.discard(clean)
            if self._compare_best_path == clean:
                self._compare_best_path = ""
        else:
            self._compare_delete_paths.discard(clean)
        after = clean in self._compare_delete_paths
        keep_after = clean in self._compare_keep_paths
        best_after = self._compare_best_path == clean
        if before == after and keep_before == keep_after and best_before == best_after:
            return
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot(str, list, list)
    def set_compare_selection_state(self, best_path: str, keep_paths: list, delete_paths: list) -> None:
        clean_best_path = str(best_path or "").strip()
        clean_keep_paths = {
            str(path or "").strip()
            for path in (keep_paths or [])
            if str(path or "").strip()
        }
        clean_delete_paths = {
            str(path or "").strip()
            for path in (delete_paths or [])
            if str(path or "").strip()
        }
        changed = False
        if self._compare_best_path != clean_best_path:
            self._compare_best_path = clean_best_path
            changed = True
        if self._compare_keep_paths != clean_keep_paths:
            self._compare_keep_paths = clean_keep_paths
            changed = True
        if self._compare_delete_paths != clean_delete_paths:
            self._compare_delete_paths = clean_delete_paths
            changed = True
        if clean_best_path and clean_best_path in self._compare_delete_paths:
            self._compare_delete_paths.discard(clean_best_path)
            changed = True
        if changed:
            self._compare_selection_revision += 1
            self._emit_compare_state_changed()

    @Slot(str)
    def set_compare_best_path(self, path: str) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        before_keep = clean in self._compare_keep_paths
        before_delete = clean in self._compare_delete_paths
        if self._compare_best_path == clean and before_keep and not before_delete:
            return
        self._compare_best_path = clean
        self._compare_keep_paths.add(clean)
        self._compare_delete_paths.discard(clean)
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot()
    def clear_compare_best_path(self) -> None:
        if not self._compare_best_path:
            return
        self._compare_best_path = ""
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot(result=str)
    def get_app_version(self) -> str:
        return __version__

    @Slot(bool)
    def check_for_updates(self, manual: bool = False):
        """Check GitHub for a newer version in the VERSION file."""
        request = QNetworkRequest(QUrl(UPDATE_VERSION_URL))
        self._update_reply = self.nam.get(request)
        
        def _on_finished():
            if self._update_reply.error() == QNetworkReply.NetworkError.NoError:
                remote_version = bytes(self._update_reply.readAll()).decode().strip()
                try:
                    is_newer = remote_version and Version(remote_version) > Version(__version__)
                except Exception:
                    is_newer = False

                if is_newer:
                    self.updateAvailable.emit(remote_version, manual)
                elif manual:
                    self.updateAvailable.emit("", True)
            elif manual:
                self.updateError.emit(f"Failed to check for updates: {self._update_reply.errorString()}")
            self._update_reply.deleteLater()
            self._update_reply = None

        self._update_reply.finished.connect(_on_finished)

    @Slot()
    def download_and_install_update(self):
        """Download latest installer and launch it."""
        request = QNetworkRequest(QUrl(UPDATE_INSTALLER_URL))
        self._download_reply = self.nam.get(request)
        
        def _on_progress(received, total):
            if total > 0:
                pct = int((received / total) * 100)
                self.updateDownloadProgress.emit(pct)

        def _on_finished():
            if self._download_reply.error() == QNetworkReply.NetworkError.NoError:
                data = self._download_reply.readAll()
                temp_dir = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
                setup_path = os.path.join(temp_dir, "MediaLens_Setup_New.exe")
                try:
                    with open(setup_path, "wb") as f:
                        f.write(data)
                    subprocess.Popen([setup_path, "/SILENT", "/SP-", "/NOICONS", "/RELAUNCH"])
                    QApplication.quit()
                except Exception as e:
                    self.updateError.emit(f"Failed to save or launch installer: {e}")
            else:
                self.updateError.emit(f"Download failed: {self._download_reply.errorString()}")
            self._download_reply.deleteLater()
            self._download_reply = None

        self._download_reply.downloadProgress.connect(_on_progress)
        self._download_reply.finished.connect(_on_finished)

    @Slot(result=bool)
    def should_check_on_launch(self) -> bool:
        return self.settings.value("updates/check_on_launch", True, type=bool)

    @Slot(result=dict)
    def get_scanner_status(self) -> dict:
        return {
            "text_detection": self._scanner_status_payload("text_detection"),
            "ocr_text": self._scanner_status_payload("ocr_text"),
        }

    @Slot(str, result=bool)
    def run_scanner_now(self, scanner_key: str) -> bool:
        key = str(scanner_key or "").strip()
        if key == "text_detection":
            self._ensure_background_text_processing(allow_concurrent_scan=True, force=True, rescan_existing=True)
            return True
        if key == "ocr_text":
            return self._run_ocr_text_scanner(force=True)
        return False

    @staticmethod
    def _coerce_setting_value(value):
        if isinstance(value, str):
            low = value.lower()
            if low in ("true", "false"):
                return low == "true"
        return value



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
