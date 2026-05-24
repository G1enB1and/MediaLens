from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeFileOpsMixin:
    @Slot(str, bool, result=bool)
    def set_setting_bool(self, key: str, value: bool) -> bool:
        try:
            worker_keys = getattr(self, "BACKGROUND_WORKER_KEYS", ("text_detection", "ocr_text", "ai_tags", "ai_descriptions"))
            allowed = (
                "gallery.randomize", 
                "gallery.restore_last", 
                "gallery.show_hidden",
                "gallery.include_nested_files",
                "gallery.show_folders",
                "gallery.show_all_file_types",
                "gallery.use_recycle_bin",
                "gallery.mute_video_by_default",
                "player.autoplay_gallery_animated_gifs",
                "player.autoplay_preview_animated_gifs",
                "ui.show_top_panel",
                "ui.show_left_panel", 
                "ui.show_right_panel", 
                "ui.show_bottom_panel",
                "ui.show_dismissed_progress_toasts",
                "ui.show_splash_screen",
                "ui.advanced_search_expanded",
                "ui.preview_above_details",
                "updates.check_on_launch",
                *(f"scanners.{scanner_key}.enabled" for scanner_key in worker_keys),
                "scanners.ocr_text.run_fast",
                "scanners.ocr_text.run_ai",
                "scanners.ocr_text.all_files",
            )
            if key not in allowed and key not in {"duplicate.rules.merge_before_delete", "duplicate.rules.preferred_folders_enabled"} and not key.startswith("metadata.display.") and not key.startswith("duplicate.rules.merge") and not key.startswith("people."):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))
            if key == "gallery.randomize" and bool(value):
                self._reset_session_shuffle_order()
            if key.startswith("ui.") or key.startswith("metadata.display.") or key in {"gallery.show_hidden", "gallery.include_nested_files", "gallery.show_folders", "gallery.show_all_file_types", "gallery.mute_video_by_default", "player.autoplay_gallery_animated_gifs", "player.autoplay_preview_animated_gifs"}:
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
                if key in {"gallery.show_hidden", "gallery.include_nested_files", "gallery.show_all_file_types"}:
                    self.galleryScopeChanged.emit()
            elif key in {"duplicate.rules.merge_before_delete", "duplicate.rules.preferred_folders_enabled"} or key.startswith("duplicate.rules.merge") or key.startswith("people."):
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
            elif key.startswith("scanners."):
                self.settings.sync()
                scanner_key = next((item for item in worker_keys if f".{item}." in key), "text_detection")
                self.scannerStatusChanged.emit(scanner_key, self._scanner_status_payload(scanner_key))
            elif key.startswith("updates."):
                self.settings.sync()
            if key == "ui.show_bottom_panel":
                self._emit_compare_state_changed()
            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            worker_keys = getattr(self, "BACKGROUND_WORKER_KEYS", ("text_detection", "ocr_text", "ai_tags", "ai_descriptions"))
            scanner_schedule_keys = {
                f"scanners.{scanner_key}.{field}"
                for scanner_key in worker_keys
                for field in (
                    "interval_hours",
                    "source_folders",
                    "schedule_mode",
                    "schedule_time",
                    "schedule_days",
                    "schedule_month_day",
                )
            }
            if key not in ("gallery.startup_mode", "gallery.start_folder", "gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold", "gallery.medialens_retention_days", "ui.accent_color", "ui.theme_mode", "ui.advanced_search_saved_queries", "metadata.display.order", "duplicate.settings.active_tab", "player.video_loop_mode", "player.video_loop_cutoff_seconds", "people.match_threshold") and key not in scanner_schedule_keys and not key.startswith("metadata.layout.") and not key.startswith("duplicate.rules.") and key != "duplicate.priorities.order":
                return False
            if key == "gallery.startup_mode":
                value = str(value or "none").strip().lower()
                if value not in {"none", "last", "specific"}:
                    return False
            elif key == "gallery.view_mode":
                allowed = {"masonry", "grid_small", "grid_medium", "grid_large", "grid_xlarge", "list", "content", "details", "duplicates", "similar", "similar_only"}
                if value not in allowed:
                    return False
            elif key == "gallery.group_by":
                if value not in {"none", "date", "duplicates", "similar", "similar_only"}:
                    return False
            elif key == "gallery.group_date_granularity":
                if value not in {"day", "month", "year"}:
                    return False
            elif key == "gallery.similarity_threshold":
                if value not in {"very_low", "low", "medium", "high", "very_high"}:
                    return False
            elif key == "duplicate.settings.active_tab":
                if value not in {"rules", "priorities"}:
                    return False
            elif key == "player.video_loop_mode":
                if value not in {"all", "none", "short"}:
                    return False
            elif key == "player.video_loop_cutoff_seconds":
                try:
                    value = str(max(1, int(str(value or "90").strip())))
                except Exception:
                    return False
            elif key == "people.match_threshold":
                if value not in {"conservative", "balanced", "loose"}:
                    return False
            elif key == "gallery.medialens_retention_days":
                try:
                    value = str(max(1, min(3650, int(str(value or "30").strip()))))
                except Exception:
                    return False
            elif key.startswith("scanners.") and key.endswith(".interval_hours"):
                try:
                    value = str(max(1, int(str(value or "24").strip())))
                except Exception:
                    return False
            elif key.startswith("scanners.") and key.endswith(".schedule_mode"):
                value = str(value or "weekly").strip().lower()
                if value not in {"hours", "daily", "weekly", "monthly"}:
                    return False
            elif key.startswith("scanners.") and key.endswith(".schedule_time"):
                match = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", str(value or "02:00").strip())
                if not match:
                    return False
                value = f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
            elif key.startswith("scanners.") and key.endswith(".schedule_days"):
                try:
                    parsed = json.loads(str(value or "[]"))
                except Exception:
                    return False
                if not isinstance(parsed, list):
                    return False
                clean_days: list[int] = []
                for item in parsed:
                    try:
                        day = int(item)
                    except Exception:
                        continue
                    if 0 <= day <= 6 and day not in clean_days:
                        clean_days.append(day)
                value = json.dumps(sorted(clean_days))
            elif key.startswith("scanners.") and key.endswith(".schedule_month_day"):
                try:
                    value = str(max(1, min(31, int(str(value or "1").strip()))))
                except Exception:
                    return False
            elif key.startswith("scanners.") and key.endswith(".source_folders"):
                try:
                    parsed = json.loads(str(value or "[]"))
                except Exception:
                    return False
                if not isinstance(parsed, list):
                    return False
                clean_folders: list[str] = []
                seen: set[str] = set()
                for item in parsed:
                    folder = str(item or "").strip()
                    if not folder:
                        continue
                    folder_key = os.path.normcase(os.path.normpath(folder))
                    if folder_key in seen:
                        continue
                    seen.add(folder_key)
                    clean_folders.append(folder)
                value = json.dumps(clean_folders)
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, str(value or ""))
            if key == "ui.accent_color":
                self.settings.sync()
                self.accentColorChanged.emit(str(value or "#8ab4f8"))
            elif key == "ui.theme_mode":
                Theme.set_theme_mode(value)
                self.settings.sync()
                self.uiFlagChanged.emit(key, value == "light")
            elif key in ("gallery.startup_mode", "gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold"):
                self.settings.sync()
                self.uiFlagChanged.emit(key, True)
            elif key.startswith("duplicate.rules.") or key == "duplicate.priorities.order":
                self.settings.sync()
                self.uiFlagChanged.emit(key, True)
            elif key == "ui.advanced_search_saved_queries":
                self.settings.sync()
            elif key == "metadata.display.order" or key.startswith("metadata.layout."):
                self.settings.sync()
                self.uiFlagChanged.emit(key, True)
            elif key.startswith("scanners."):
                self.settings.sync()
                scanner_key = next((item for item in worker_keys if f".{item}." in key), "text_detection")
                self.scannerStatusChanged.emit(scanner_key, self._scanner_status_payload(scanner_key))
            return True
        except Exception:
            return False

    @Slot(str)
    def load_folder_now(self, path: str) -> None:
        self.loadFolderRequested.emit(str(path))

    @Slot(list, str, int, int)
    def start_native_drag(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> None:
        clean_paths = [str(p) for p in (paths or []) if p]
        if not clean_paths:
            return
        self.set_drag_paths(clean_paths)
        self.startNativeDragRequested.emit(clean_paths, str(preview_path or ""), int(preview_width or 0), int(preview_height or 0))

    @Slot(str)
    def navigate_to_folder(self, path: str) -> None:
        self.navigateToFolderRequested.emit(str(path))

    @Slot()
    def navigate_back(self) -> None:
        self.navigateBackRequested.emit()

    @Slot()
    def navigate_forward(self) -> None:
        self.navigateForwardRequested.emit()

    @Slot()
    def navigate_up(self) -> None:
        self.navigateUpRequested.emit()

    @Slot()
    def refresh_current_folder(self) -> None:
        self.refreshFolderRequested.emit()

    @Slot()
    def open_settings_dialog(self) -> None:
        self.openSettingsDialogRequested.emit()

    @Slot(result=str)
    def pick_folder(self) -> str:
        try:
            from PySide6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(None, "Choose folder")
            return str(folder) if folder else ""
        except Exception:
            return ""

    def _unique_path(self, target: Path) -> Path:
        if not target.exists(): return target
        suffix, stem, parent, i = target.suffix, target.stem, target.parent, 2
        while True:
            cand = parent / f"{stem} ({i}){suffix}"
            if not cand.exists(): return cand
            i += 1

    def _hide_by_renaming_dot(self, path: str) -> str:
        """DEPRECATED: Use set_media_hidden instead."""
        p = Path(path)
        if not p.exists() or p.name.startswith("."): return str(p)
        target = self._unique_path(p.with_name(f".{p.name}"))
        p.rename(target)
        return str(target)

    @Slot(str, bool, result=bool)
    def set_media_hidden(self, path: str, hidden: bool) -> bool:
        try:
            before_hidden = bool(self.repo.is_path_hidden(path))
        except Exception:
            before_hidden = None
        success = self.repo.set_media_hidden(path, hidden)
        if success:
            self._invalidate_scan_caches_for_paths([path])
            if before_hidden is None or before_hidden != bool(hidden):
                try:
                    from native.mediamanagerx_app.action_history import record_user_action
                    record_user_action(
                        self.conn,
                        action_type="hidden",
                        summary="Hid item" if hidden else "Unhid item",
                        items=[{
                            "item_type": "file",
                            "old_path": path,
                            "new_path": path,
                            "result": "success",
                            "current_state": "applied",
                            "last_change_source": "original_action",
                            "notes": "hidden" if hidden else "visible",
                            "metadata": {"old_hidden": before_hidden, "new_hidden": bool(hidden), "target": "media"},
                        }],
                    )
                    self.actionHistoryChanged.emit()
                except Exception as exc:
                    try: self._log(f"Action history hidden record failed: {exc}")
                    except Exception: pass
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(str, bool, result=bool)
    def set_folder_hidden(self, path: str, hidden: bool) -> bool:
        try:
            before_hidden = bool(self.repo.is_path_hidden(path))
        except Exception:
            before_hidden = None
        success = self.repo.set_folder_hidden(path, hidden)
        if success:
            self._invalidate_scan_caches_for_paths([path])
            if before_hidden is None or before_hidden != bool(hidden):
                try:
                    from native.mediamanagerx_app.action_history import record_user_action
                    record_user_action(
                        self.conn,
                        action_type="hidden",
                        summary="Hid folder" if hidden else "Unhid folder",
                        items=[{
                            "item_type": "folder",
                            "old_path": path,
                            "new_path": path,
                            "result": "success",
                            "current_state": "applied",
                            "last_change_source": "original_action",
                            "notes": "hidden" if hidden else "visible",
                            "metadata": {"old_hidden": before_hidden, "new_hidden": bool(hidden), "target": "folder"},
                        }],
                    )
                    self.actionHistoryChanged.emit()
                except Exception as exc:
                    try: self._log(f"Action history folder hidden record failed: {exc}")
                    except Exception: pass
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(int, bool, result=bool)
    def set_collection_hidden(self, collection_id: int, hidden: bool) -> bool:
        try:
            row = self.conn.execute("SELECT name, is_hidden FROM collections WHERE id = ?", (int(collection_id),)).fetchone()
            collection_name = str(row[0] or f"Collection {collection_id}") if row else f"Collection {collection_id}"
            before_hidden = bool(row[1]) if row else None
        except Exception:
            collection_name = f"Collection {collection_id}"
            before_hidden = None
        success = self.repo.set_collection_hidden(collection_id, hidden)
        if success:
            if before_hidden is None or before_hidden != bool(hidden):
                try:
                    from native.mediamanagerx_app.action_history import record_user_action
                    record_user_action(
                        self.conn,
                        action_type="hidden",
                        summary="Hid collection" if hidden else "Unhid collection",
                        items=[{
                            "item_type": "collection",
                            "old_path": collection_name,
                            "new_path": collection_name,
                            "result": "success",
                            "current_state": "applied",
                            "last_change_source": "original_action",
                            "notes": "hidden" if hidden else "visible",
                            "metadata": {"old_hidden": before_hidden, "new_hidden": bool(hidden), "target": "collection", "collection_id": int(collection_id)},
                        }],
                    )
                    self.actionHistoryChanged.emit()
                except Exception as exc:
                    try: self._log(f"Action history collection hidden record failed: {exc}")
                    except Exception: pass
        return success

    @Slot(result="QVariantMap")
    def get_external_editors(self):
        """Find installation paths for external editors."""
        editors = {"photoshop": None, "affinity": None}
        import winreg
        
        # Check Photoshop via App Paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe") as key:
                editors["photoshop"] = winreg.QueryValue(key, None)
        except Exception:
            pass
            
        # Check Affinity Photo 2 via App Paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photo.exe") as key:
                editors["affinity"] = winreg.QueryValue(key, None)
        except Exception:
            pass
            
        # Fallback for Affinity
        if not editors["affinity"]:
            affinity_fallbacks = [
                r"C:\Program Files\Affinity\Photo 2\Photo.exe",
                r"C:\Program Files\Affinity\Photo\Photo.exe"
            ]
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                windows_apps = os.path.join(local_appdata, "Microsoft", "WindowsApps")
                affinity_fallbacks.extend([
                    os.path.join(windows_apps, "Affinity.exe"),
                    os.path.join(windows_apps, "AffinityPhoto2.exe"),
                    os.path.join(windows_apps, "AffinityPhoto.exe")
                ])
                
            for fb in affinity_fallbacks:
                if os.path.exists(fb):
                    editors["affinity"] = fb
                    break
                    
        return {k: v for k, v in editors.items() if v}

    @Slot(str, str)
    def open_in_editor(self, editor_key: str, path: str):
        """Open a file in the specified external editor."""
        editors = self.get_external_editors()
        editor_path = editors.get(editor_key)
        if not editor_path or not os.path.exists(path):
            return
            
        try:
            subprocess.Popen([editor_path, path])
        except Exception as e:
            print(f"Failed to open in {editor_key}: {e}")

    @Slot(str, int)
    def rotate_image(self, path: str, degrees: int):
        """Rotate an image or video by degrees and update it in-place."""
        if not os.path.exists(path):
            return

        def work():
            try:
                self._rotate_media_sync(path, int(degrees or 0))
                try:
                    from native.mediamanagerx_app.action_history import record_user_action
                    record_user_action(
                        self.conn,
                        action_type="rotate",
                        summary=f"Rotated {Path(path).name}",
                        items=[{
                            "item_type": "file",
                            "old_path": path,
                            "new_path": path,
                            "result": "success",
                            "current_state": "applied",
                            "last_change_source": "original_action",
                            "notes": f"{int(degrees or 0)} degrees",
                            "metadata": {"degrees": int(degrees or 0)},
                        }],
                    )
                    self.actionHistoryChanged.emit()
                except Exception as exc:
                    try: self._log(f"Action history rotate record failed: {exc}")
                    except Exception: pass
                # Finally, inform frontend that a file was modified so it can refresh the thumbnail
                self.fileOpFinished.emit("rotate", True, path, path)
            except Exception as e:
                print(f"Failed to rotate media: {e}")

        # Run in background to prevent freezing the UI on large videos
        threading.Thread(target=work, daemon=True).start()

    def _rotate_media_sync(self, path: str, degrees: int) -> None:
        is_video = path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))
        if is_video:
            import subprocess, tempfile
            current_ccw_rot = 0.0
            try:
                cmd_probe = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', path]
                res = _run_hidden_subprocess(cmd_probe, capture_output=True, text=True)
                data = json.loads(res.stdout)
                for st in data.get('streams', []):
                    if st.get('codec_type') == 'video':
                        tags = st.get('tags', {})
                        if 'rotate' in tags:
                            current_ccw_rot = float(tags['rotate'])
                        for sd in st.get('side_data_list', []):
                            if 'rotation' in sd:
                                current_ccw_rot = float(sd['rotation'])
                        break
            except Exception as e:
                print("Warning: Failed to probe rotation:", e)
            new_ccw_rot = (current_ccw_rot + degrees) % 360
            if new_ccw_rot < 0:
                new_ccw_rot += 360
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(path)[1], delete=False) as tmp:
                tmp_name = tmp.name
            cmd_ffmpeg = [
                'ffmpeg', '-y',
                '-display_rotation', str(new_ccw_rot),
                '-i', path,
                '-c', 'copy',
                tmp_name
            ]
            _run_hidden_subprocess(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.move(tmp_name, path)
            poster = self._video_poster_path(Path(path))
            if poster.exists():
                try: poster.unlink()
                except Exception: pass
        else:
            from PIL import Image
            with Image.open(path) as img:
                rotated = img.rotate(degrees, expand=True)
                exif = img.info.get('exif')
                if exif:
                    rotated.save(path, exif=exif)
                else:
                    rotated.save(path)
        try:
            from app.mediamanager.utils.pathing import normalize_windows_path
            if hasattr(self, 'conn') and self.conn:
                norm = normalize_windows_path(path)
                if degrees in (90, -90, 270, -270):
                    self.conn.execute("UPDATE media_items SET width = height, height = width WHERE path = ?", (norm,))
                    self.conn.commit()
        except Exception:
            pass

    @Slot(str, result=str)
    def hide_by_renaming_dot(self, path: str) -> str:
        try: return self._hide_by_renaming_dot(path)
        except Exception: return ""

    @Slot(str, result=bool)
    def hide_by_renaming_dot_async(self, path: str) -> bool:
        old = str(path)
        def work():
            newp = ""
            try: newp = self._hide_by_renaming_dot(old)
            except Exception: pass
            self.fileOpFinished.emit("hide", bool(newp), old, newp)
            if newp:
                self._invalidate_scan_caches_for_paths([old, newp])
        threading.Thread(target=work, daemon=True).start()
        return True

    def _unhide_by_renaming_dot(self, path: str) -> str:
        p = Path(path)
        if not p.exists() or not p.name.startswith("."): return str(p)
        target = self._unique_path(p.with_name(p.name[1:]))
        p.rename(target)
        return str(target)

    @Slot(str, result=str)
    def unhide_by_renaming_dot(self, path: str) -> str:
        try: return self._unhide_by_renaming_dot(path)
        except Exception: return ""

    @Slot(str, result=bool)
    def unhide_by_renaming_dot_async(self, path: str) -> bool:
        old = str(path)
        def work():
            newp = ""
            try: newp = self._unhide_by_renaming_dot(old)
            except Exception: pass
            self.fileOpFinished.emit("unhide", bool(newp), old, newp)
            if newp:
                self._invalidate_scan_caches_for_paths([old, newp])
        threading.Thread(target=work, daemon=True).start()
        return True

    def _rename_path(self, path: str, new_name: str) -> str:
        p = Path(path)
        if not p.exists() or not new_name.strip(): return ""
        target = self._unique_path(p.with_name(new_name.strip()))
        # Use shutil.move for robustness across drives if necessary, 
        # though usually rename is fine for same folder.
        shutil.move(str(p), str(target))
        return str(target)

    @Slot(str, str, result=str)
    def rename_path(self, path: str, new_name: str) -> str:
        try: return self._rename_path(path, new_name)
        except Exception: return ""

    @Slot(str, str, result=bool)
    def rename_path_async(self, path: str, new_name: str) -> bool:
        old, newn = str(path), str(new_name)
        def work():
            ok, newp = False, ""
            try:
                newp = self._rename_path(old, newn)
                ok = bool(newp)
                if ok:
                    from app.mediamanager.db.media_repo import rename_media_path
                    try: rename_media_path(self.conn, old, newp)
                    except Exception: pass
                    try:
                        from native.mediamanagerx_app.action_history import make_history_item, record_user_action
                        record_user_action(
                            self.conn,
                            action_type="rename",
                            summary=f'Renamed "{Path(old).name}" to "{Path(newp).name}"',
                            items=[make_history_item(old_path=old, new_path=newp, item_type="folder" if Path(newp).is_dir() else "file")],
                        )
                        self.actionHistoryChanged.emit()
                    except Exception as exc:
                        try: self._log(f"Action history rename record failed: {exc}")
                        except Exception: pass
            except Exception: pass
            self.fileOpFinished.emit("rename", ok, old, newp)
            if ok:
                self._invalidate_scan_caches_for_paths([old, newp])
        threading.Thread(target=work, daemon=True).start()
        return True

    @Slot(str, str, str, result=str)
    def themed_text_input(self, title: str, label: str, text: str = "") -> str:
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        value, ok = _run_themed_text_input_dialog(parent, str(title or ""), str(label or ""), text=str(text or ""))
        return str(value or "") if ok else ""

    @Slot(str, str, result=bool)
    def themed_confirm(self, title: str, message: str) -> bool:
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        reply = _run_themed_question_dialog(
            parent,
            str(title or "Delete Confirmation"),
            str(message or ""),
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    @Slot(str, result=str)
    def path_to_url(self, path: str) -> str:
        try: return QUrl.fromLocalFile(str(path)).toString()
        except Exception: return ""

    @Slot(str, str)
    def _invoke_conflict_dialog(self, dst_str: str, src_str: str):
        """Helper to show dialog on main thread."""
        dst, src = Path(dst_str), Path(src_str)
        # Ensure parent is a QWidget if possible
        parent_win = self.parent() if isinstance(self.parent(), QWidget) else None
        dlg = FileConflictDialog(dst, src, self, parent=parent_win)
        if dlg.exec():
            # Store results so processing thread can pick them up
            self._last_dlg_res = {
                "action": dlg.result_action,
                "apply_all": dlg.apply_to_all,
                "new_existing": dlg.new_existing_name,
                "new_incoming": dlg.new_incoming_name
            }
        else:
            self._last_dlg_res = {"action": "skip"}

    def _process_file_op(self, op_type: str, src_paths: list[Path], target_dir: Path) -> None:
        if not target_dir.exists() or not target_dir.is_dir():
            self.fileOpFinished.emit(op_type, False, "", "")
            return
        is_move = op_type in ("move", "paste_move")
        try:
            target_key = str(target_dir.resolve()).replace("/", "\\").rstrip("\\").casefold()
        except Exception:
            target_key = str(target_dir).replace("/", "\\").rstrip("\\").casefold()
        safe_src_paths: list[Path] = []
        for src in src_paths:
            try:
                src_key = str(src.resolve()).replace("/", "\\").rstrip("\\").casefold()
            except Exception:
                src_key = str(src).replace("/", "\\").rstrip("\\").casefold()
            if src_key and target_key and (target_key == src_key or target_key.startswith(src_key + "\\")):
                continue
            if is_move and src_key and target_key and str(src.parent).replace("/", "\\").rstrip("\\").casefold() == target_key:
                continue
            safe_src_paths.append(src)
        src_paths = safe_src_paths
        if not src_paths:
            self.fileOpFinished.emit(op_type, False, "", str(target_dir))
            return

        def work():
            from app.mediamanager.db.media_repo import rename_media_path, move_directory_in_db, add_media_item, get_media_by_path
            from app.mediamanager.db.tags_repo import attach_tags, list_media_tags
            
            
            sticky_action = None
            any_ok = False
            changed_paths: list[str] = [str(target_dir)]
            history_items: list[dict] = []
            
            try:
                for src in src_paths:
                    if not src.exists():
                        history_items.append({
                            "item_type": "folder" if src.is_dir() else "file",
                            "old_path": str(src),
                            "new_path": str(target_dir / src.name),
                            "result": "failed",
                            "current_state": "failed",
                            "last_change_source": "original_action",
                            "notes": "Source path no longer exists.",
                        })
                        continue
                    
                    dst = target_dir / src.name
                    action = "keep_both"
                    final_dst = dst
                    
                    if dst.exists():
                        if is_move and dst.samefile(src):
                            continue
                        if not is_move and dst.samefile(src):
                            final_dst = self._unique_path(dst)
                            action = "keep_both"
                        elif sticky_action:
                            res = {"action": sticky_action, "new_incoming": src.name}
                        else:
                            # Invoke dialog on main thread via signal
                            self._last_dlg_res = None
                            self.conflictDialogRequested.emit(str(dst), str(src))

                            # Busy wait for result (max 10 mins)
                            start_t = time.time()
                            while self._last_dlg_res is None and (time.time() - start_t < 600):
                                time.sleep(0.05)

                            res = self._last_dlg_res or {"action": "skip"}
                            if res.get("apply_all"): sticky_action = res["action"]
                        
                        if not (not is_move and action == "keep_both" and final_dst != dst):
                            action = res["action"]
                            if action == "skip":
                                history_items.append({
                                    "item_type": "folder" if src.is_dir() else "file",
                                    "old_path": str(src),
                                    "new_path": str(dst),
                                    "result": "failed",
                                    "current_state": "failed",
                                    "last_change_source": "original_action",
                                    "notes": "Skipped because of a destination conflict.",
                                })
                                continue
                            elif action == "replace":
                                 final_dst = dst
                            elif action == "keep_both":
                                 # Use the new name from dialog if provided
                                 new_name = res.get("new_incoming", src.name)
                                 final_dst = target_dir / new_name
                                 if final_dst.exists():
                                     final_dst = self._unique_path(final_dst)
                    
                    # Execute with correct atomic logic
                    try:
                        if is_move:
                            try:
                                # Try atomic os.replace (removes source, overwrites target if exists)
                                os.replace(src, final_dst)
                            except OSError:
                                # Cross-device move fallback
                                shutil.move(src, final_dst)
                            
                            # Double check: ensure source is gone (as requested by user)
                            if src.exists():
                                try:
                                    if src.is_dir(): shutil.rmtree(src)
                                    else: src.unlink()
                                except: pass
                            
                            if src.is_dir(): move_directory_in_db(self.conn, str(src), str(final_dst))
                            else: rename_media_path(self.conn, str(src), str(final_dst))
                        else:
                            # Copy operation
                            if src.is_dir():
                                shutil.copytree(src, final_dst)
                            else:
                                shutil.copy2(src, final_dst)
                                ext = final_dst.suffix.lower()
                                if ext in (IMAGE_EXTS | VIDEO_EXTS):
                                    mtype = "image" if ext in IMAGE_EXTS else "video"
                                    new_media_id = add_media_item(self.conn, str(final_dst), mtype)
                                    src_media = get_media_by_path(self.conn, str(src))
                                    if src_media:
                                        src_tags = list_media_tags(self.conn, int(src_media["id"]))
                                        if src_tags:
                                            attach_tags(self.conn, int(new_media_id), src_tags)
                        
                        any_ok = True
                        history_items.append({
                            "item_type": "folder" if final_dst.is_dir() else "file",
                            "old_path": str(src),
                            "new_path": str(final_dst),
                            "result": "success",
                            "current_state": "applied",
                            "last_change_source": "original_action",
                            "notes": "",
                        })
                        if is_move:
                            changed_paths.extend([str(src), str(final_dst)])
                        else:
                            changed_paths.append(str(final_dst))
                    except Exception as e:
                        history_items.append({
                            "item_type": "folder" if src.is_dir() else "file",
                            "old_path": str(src),
                            "new_path": str(final_dst),
                            "result": "failed",
                            "current_state": "failed",
                            "last_change_source": "original_action",
                            "notes": str(e) or "Operation failed.",
                        })

                op_signal = "paste" if "paste" in op_type else op_type
                if history_items:
                    try:
                        from native.mediamanagerx_app.action_history import action_summary, record_user_action
                        success_count = sum(1 for item in history_items if item.get("result") == "success")
                        record_user_action(
                            self.conn,
                            action_type="move" if is_move else "copy",
                            summary=action_summary("move" if is_move else "copy", success_count),
                            items=history_items,
                            metadata={"target_dir": str(target_dir), "op_type": op_type},
                        )
                        self.actionHistoryChanged.emit()
                    except Exception as exc:
                        try: self._log(f"Action history file-op record failed: {exc}")
                        except Exception: pass
                self.fileOpFinished.emit(op_signal, any_ok, "", str(target_dir))
            except Exception as e:
                self.fileOpFinished.emit(op_type, False, "", "")
            
            if any_ok:
                self._invalidate_scan_caches_for_paths(changed_paths)

        threading.Thread(target=work, daemon=True).start()

    @Slot(list, str)
    def move_paths_async(self, src_paths: list[str], target_folder: str) -> None:
        self._process_file_op("move", [Path(p) for p in self._dedupe_file_op_paths(src_paths)], Path(target_folder))

    @Slot(list, str)
    def copy_paths_async(self, src_paths: list[str], target_folder: str) -> None:
        self._process_file_op("copy", [Path(p) for p in self._dedupe_file_op_paths(src_paths)], Path(target_folder))

    @Slot(list, result=bool)
    def show_metadata(self, paths: list) -> bool:
        try: self.metadataRequested.emit(paths); return True
        except Exception: return False

    @Slot(str)
    def open_in_explorer(self, path: str) -> None:
        try:
            p_obj = Path(path).absolute()
            p = str(p_obj).replace("/", "\\")
            if not p_obj.exists(): return
            if p_obj.is_dir(): os.startfile(p)
            else: subprocess.Popen(f'explorer.exe /select,"{p}"', shell=True)
        except Exception: pass

    @Slot(str)
    def open_file_external(self, path: str) -> None:
        try:
            p_obj = Path(path).absolute()
            if not p_obj.exists() or not p_obj.is_file():
                return
            os.startfile(str(p_obj).replace("/", "\\"))
        except Exception:
            pass

    def _build_dropfiles_w(self, abs_paths: list[str]) -> bytes:
        import struct
        header = struct.pack("IiiII", 20, 0, 0, 0, 1)
        files_data = b"".join([p.encode("utf-16-le") + b"\x00\x00" for p in abs_paths]) + b"\x00\x00"
        return header + files_data

    @Slot(list)
    def copy_to_clipboard(self, paths: list[str]) -> None:
        try:
            clipboard, mime = QApplication.clipboard(), QMimeData()
            abs_paths = self._dedupe_file_op_paths(paths)
            mime.setUrls([QUrl.fromLocalFile(p) for p in abs_paths])
            mime.setText("\n".join(abs_paths))
            mime.setData("Preferred DropEffect", b'\x05\x00\x00\x00')
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            clipboard.setMimeData(mime)
        except Exception: pass

    @Slot(list)
    def cut_to_clipboard(self, paths: list[str]) -> None:
        try:
            clipboard, mime = QApplication.clipboard(), QMimeData()
            abs_paths = self._dedupe_file_op_paths(paths)
            mime.setUrls([QUrl.fromLocalFile(p) for p in abs_paths])
            mime.setText("\n".join(abs_paths))
            mime.setData("Preferred DropEffect", b'\x02\x00\x00\x00')
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            clipboard.setMimeData(mime)
        except Exception: pass

    @Slot(result=bool)
    def has_files_in_clipboard(self) -> bool:
        try: return QApplication.clipboard().mimeData().hasUrls()
        except Exception: return False

    @Slot()
    def empty_recycle_bin(self) -> None:
        from native.mediamanagerx_app.recycle_bin import empty_all
        empty_all()
        self.collectionsChanged.emit()

    @Slot()
    def restore_all_recycle_bin(self) -> None:
        from native.mediamanagerx_app.recycle_bin import restore_all
        restore_all()
        self.collectionsChanged.emit()

    @Slot(str, result=bool)
    def delete_path(self, path_str: str) -> bool:
        try:
            self.close_native_video()
            QApplication.processEvents()
            from native.mediamanagerx_app.action_delete import perform_delete
            ok, item = perform_delete(self.conn, self.settings, path_str, permanent=False)
            if not ok:
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False
            self._invalidate_scan_caches_for_paths([path_str])
            self.collectionsChanged.emit()
            try:
                from native.mediamanagerx_app.action_history import record_user_action
                retention_id = str(item.get("retention_id") or "")
                record_user_action(
                    self.conn,
                    action_type="delete",
                    summary=f'Deleted "{Path(path_str).name}"',
                    items=[item],
                    undo_state=None if retention_id else "not_undoable",
                    metadata={"permanent": False},
                )
                self.actionHistoryChanged.emit()
            except Exception as exc:
                try: self._log(f"Action history delete record failed: {exc}")
                except Exception: pass
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(str, result=bool)
    def delete_path_permanent(self, path_str: str) -> bool:
        try:
            self.close_native_video()
            QApplication.processEvents()
            from native.mediamanagerx_app.action_delete import perform_delete
            ok, item = perform_delete(self.conn, self.settings, path_str, permanent=True)
            if not ok:
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False
            self._invalidate_scan_caches_for_paths([path_str])
            try:
                from native.mediamanagerx_app.action_history import record_user_action
                record_user_action(
                    self.conn,
                    action_type="delete",
                    summary=f'Permanently deleted "{Path(path_str).name}"',
                    items=[item],
                    undo_state="not_undoable",
                    metadata={"permanent": True},
                )
                self.actionHistoryChanged.emit()
            except Exception as exc:
                try: self._log(f"Action history permanent delete record failed: {exc}")
                except Exception: pass
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(list, bool, result=bool)
    def delete_paths(self, paths: list[str], permanent: bool = False) -> bool:
        clean_paths = self._dedupe_file_op_paths([str(path or "") for path in (paths or []) if str(path or "").strip()])
        if not clean_paths:
            self.fileOpFinished.emit("delete", False, "", "")
            return False
        try:
            self.close_native_video()
            QApplication.processEvents()
            from native.mediamanagerx_app.action_delete import perform_delete
            from native.mediamanagerx_app.action_history import record_user_action
            history_items: list[dict] = []
            changed_paths: list[str] = []
            for path_str in clean_paths:
                try:
                    ok, item = perform_delete(self.conn, self.settings, path_str, permanent=bool(permanent))
                except Exception as exc:
                    ok = False
                    item = {
                        "item_type": "file",
                        "old_path": path_str,
                        "new_path": "",
                        "retention_id": "",
                        "result": "failed",
                        "current_state": "failed",
                        "last_change_source": "original_action",
                        "notes": str(exc) or "Delete failed.",
                    }
                history_items.append(item)
                if ok:
                    changed_paths.append(path_str)
            success_count = sum(1 for item in history_items if item.get("result") == "success")
            if history_items:
                has_retention = any(str(item.get("retention_id") or "") for item in history_items if item.get("result") == "success")
                record_user_action(
                    self.conn,
                    action_type="delete",
                    summary=("Permanently deleted " if permanent else "Deleted ") + ("1 item" if success_count == 1 else f"{success_count} items"),
                    items=history_items,
                    undo_state=None if has_retention else "not_undoable",
                    metadata={"permanent": bool(permanent), "grouped": True},
                )
                self.actionHistoryChanged.emit()
            if changed_paths:
                self._invalidate_scan_caches_for_paths(changed_paths)
                self.collectionsChanged.emit()
            self.fileOpFinished.emit("delete", bool(changed_paths), "", "")
            return bool(changed_paths)
        except Exception:
            self.fileOpFinished.emit("delete", False, "", "")
            return False

    @Slot(str, str, result=str)
    def create_folder(self, parent_path: str, name: str) -> str:
        try:
            p = Path(parent_path) / name
            existed = p.exists()
            p.mkdir(parents=True, exist_ok=True)
            try:
                from native.mediamanagerx_app.action_history import make_history_item, record_user_action
                if not existed:
                    record_user_action(
                        self.conn,
                        action_type="create_folder",
                        summary=f'Created folder "{p.name}"',
                        items=[make_history_item(new_path=str(p), item_type="folder")],
                    )
                    self.actionHistoryChanged.emit()
            except Exception as exc:
                try: self._log(f"Action history create-folder record failed: {exc}")
                except Exception: pass
            return str(p)
        except Exception: return ""

    @Slot(result=bool)
    def undo_last_action(self) -> bool:
        try:
            from app.mediamanager.db import action_history_repo
            for _attempt in range(3):
                entry = action_history_repo.latest_undoable_entry(self.conn)
                if not entry:
                    self._set_action_history_message("Nothing available to undo.")
                    return False
                if self._validate_action_history_entry(int(entry["id"])):
                    continue
                if self._undo_history_entry(int(entry["id"]), group=True):
                    self._set_action_history_message("")
                    return True
                self._set_action_history_message(self._history_entry_unavailable_message(int(entry["id"]), "Undo"))
                return False
            self._set_action_history_message("Undo not available: recent history changed during validation.")
            return False
        except Exception as exc:
            try: self._log(f"Undo failed: {exc}")
            except Exception: pass
            self._set_action_history_message(f"Undo failed: {exc}")
            return False

    @Slot(result=bool)
    def redo_last_action(self) -> bool:
        try:
            from app.mediamanager.db import action_history_repo
            for _attempt in range(3):
                entry = action_history_repo.latest_redoable_entry(self.conn)
                if not entry:
                    self._set_action_history_message("Nothing available to redo.")
                    return False
                if self._validate_action_history_entry(int(entry["id"])):
                    continue
                if self._redo_history_entry(int(entry["id"]), group=True):
                    self._set_action_history_message("")
                    return True
                self._set_action_history_message(self._history_entry_unavailable_message(int(entry["id"]), "Redo"))
                return False
            self._set_action_history_message("Redo not available: recent history changed during validation.")
            return False
        except Exception as exc:
            try: self._log(f"Redo failed: {exc}")
            except Exception: pass
            self._set_action_history_message(f"Redo failed: {exc}")
            return False

    @Slot(int, result=bool)
    def undo_history_item(self, item_id: int) -> bool:
        return self._undo_history_item(int(item_id), source="individual_undo")

    @Slot(int, result=bool)
    def redo_history_item(self, item_id: int) -> bool:
        return self._redo_history_item(int(item_id), source="individual_redo")

    @Slot(result="QVariantMap")
    def get_action_history_state(self):
        try:
            from app.mediamanager.db import action_history_repo
            return {
                "can_undo": bool(action_history_repo.latest_undoable_entry(self.conn)),
                "can_redo": bool(action_history_repo.latest_redoable_entry(self.conn)),
            }
        except Exception:
            return {"can_undo": False, "can_redo": False}

    @Slot(str, str, int, result=list)
    def list_action_history(self, action_type: str = "all", search: str = "", limit: int = 200):
        try:
            from app.mediamanager.db import action_history_repo
            return action_history_repo.list_entries(self.conn, limit=int(limit or 200), action_type=action_type, search=search)
        except Exception:
            return []

    @Slot(int, result=list)
    def list_action_history_items(self, entry_id: int):
        try:
            from app.mediamanager.db import action_history_repo
            return action_history_repo.list_items(self.conn, int(entry_id))
        except Exception:
            return []

    @Slot(result=int)
    def delete_all_action_history(self) -> int:
        try:
            from app.mediamanager.db import action_history_repo
            count = action_history_repo.delete_all(self.conn)
            self._set_action_history_message("")
            self.actionHistoryChanged.emit()
            return int(count or 0)
        except Exception as exc:
            try: self._log(f"Delete all action history failed: {exc}")
            except Exception: pass
            self._set_action_history_message(f"Delete all action history failed: {exc}")
            return 0

    @Slot(int, result=int)
    def validate_action_history(self, limit: int = 100) -> int:
        try:
            from app.mediamanager.db import action_history_repo

            entries = action_history_repo.list_validation_candidate_entries(self.conn, limit=max(1, int(limit or 100)))
            changed = 0
            for entry in entries:
                changed += self._validate_action_history_entry(int(entry.get("id") or 0), emit=False)
            if changed:
                self.actionHistoryChanged.emit()
            return changed
        except Exception as exc:
            try: self._log(f"Action history validation failed: {exc}")
            except Exception: pass
            return 0

    def _set_action_history_message(self, message: str) -> None:
        self._last_action_history_message = str(message or "")
        if message:
            try: self._log(str(message))
            except Exception: pass

    def _validate_action_history_entry(self, entry_id: int, *, emit: bool = True) -> int:
        from app.mediamanager.db import action_history_repo
        from app.mediamanager.db.media_repo import get_media_by_path
        from native.mediamanagerx_app import action_history

        entry = action_history_repo.get_entry(self.conn, int(entry_id))
        if not entry:
            return 0
        changed = 0

        def media_exists(path: str) -> bool:
            return bool(get_media_by_path(self.conn, str(path or "")))

        for item in action_history_repo.list_items(self.conn, int(entry_id)):
            current_state, source, note = action_history.validate_history_item_availability(
                entry,
                item,
                media_exists_fn=media_exists,
            )
            if not current_state:
                continue
            next_source = source or str(item.get("last_change_source") or "original_action")
            if (
                current_state == str(item.get("current_state") or "")
                and next_source == str(item.get("last_change_source") or "")
                and (note or "") == str(item.get("notes") or "")
            ):
                continue
            action_history_repo.update_item_state(
                self.conn,
                int(item.get("id") or 0),
                current_state=current_state,
                last_change_source=next_source,
                notes=note,
            )
            changed += 1
        if changed:
            action_history_repo.recompute_entry_undo_state(self.conn, int(entry_id))
            if emit:
                self.actionHistoryChanged.emit()
        return changed

    def _history_entry_unavailable_message(self, entry_id: int, verb: str) -> str:
        try:
            from app.mediamanager.db import action_history_repo

            items = action_history_repo.list_items(self.conn, int(entry_id))
            notes = [
                str(item.get("notes") or "").strip()
                for item in items
                if str(item.get("current_state") or "") == "unavailable" and str(item.get("notes") or "").strip()
            ]
            if notes:
                return f"{verb} not available: {notes[0]}"
        except Exception:
            pass
        return f"{verb} not available for the next action."

    def _record_history_system_event(self, action_type: str, summary: str, items: list[dict], origin: str) -> None:
        try:
            from app.mediamanager.db import action_history_repo
            action_history_repo.create_entry(
                self.conn,
                action_type=action_type,
                summary=summary,
                items=items,
                origin=origin,
                status="success",
                undo_state="not_undoable",
            )
        except Exception:
            pass

    def _undo_history_entry(self, entry_id: int, *, group: bool) -> bool:
        from app.mediamanager.db import action_history_repo
        items = action_history_repo.list_items(self.conn, entry_id)
        successful = [item for item in items if str(item.get("result") or "") == "success"]
        changed = 0
        for item in items:
            if str(item.get("current_state") or "") != "applied":
                continue
            if self._undo_history_item(int(item["id"]), source="group_undo", emit=False):
                changed += 1
        action_history_repo.recompute_entry_undo_state(self.conn, entry_id)
        if changed:
            self._after_history_restore()
            self._record_history_system_event(
                "undo",
                self._history_group_result_summary("Undid action", changed, len(successful)),
                [],
                "undo",
            )
            self.actionHistoryChanged.emit()
        return changed > 0

    def _redo_history_entry(self, entry_id: int, *, group: bool) -> bool:
        from app.mediamanager.db import action_history_repo
        items = action_history_repo.list_items(self.conn, entry_id)
        successful = [item for item in items if str(item.get("result") or "") == "success"]
        changed = 0
        for item in items:
            if str(item.get("current_state") or "") != "undone":
                continue
            if str(item.get("last_change_source") or "") != "group_undo":
                continue
            if self._redo_history_item(int(item["id"]), source="group_redo", emit=False):
                changed += 1
        action_history_repo.recompute_entry_undo_state(self.conn, entry_id)
        if changed:
            self._after_history_restore()
            self._record_history_system_event(
                "redo",
                self._history_group_result_summary("Redid action", changed, len(successful)),
                [],
                "redo",
            )
            self.actionHistoryChanged.emit()
        return changed > 0

    @staticmethod
    def _history_group_result_summary(verb: str, changed: int, total: int) -> str:
        changed = int(changed or 0)
        total = int(total or 0)
        changed_label = "item" if changed == 1 else "items"
        if total > 0 and changed != total:
            skipped = max(0, total - changed)
            skipped_label = "item" if skipped == 1 else "items"
            total_label = "item" if total == 1 else "items"
            return f"{verb} for {changed} of {total} {total_label}; {skipped} {skipped_label} skipped"
        return f"{verb} for {changed} {changed_label}"

    def _undo_history_item(self, item_id: int, *, source: str, emit: bool = True) -> bool:
        from app.mediamanager.db import action_history_repo
        from native.mediamanagerx_app import action_history
        found = action_history_repo.get_item_with_entry(self.conn, int(item_id))
        if not found:
            return False
        item, entry = found
        action_type = str(entry.get("action_type") or "")
        entry_id = int(entry["id"])
        if not item or str(item.get("current_state") or "") != "applied":
            return False
        old_path = str(item.get("old_path") or "")
        new_path = str(item.get("new_path") or "")
        item_type = str(item.get("item_type") or "file")
        ok = False
        note = None
        try:
            if action_type in {"move", "rename"}:
                ok = action_history.move_path(new_path, old_path)
                if ok:
                    action_history.update_media_path_after_restore(self.conn, new_path, old_path, item_type)
            elif action_type == "copy":
                ok = action_history.delete_path_for_undo(new_path)
            elif action_type == "create_folder":
                target = Path(new_path)
                ok = target.exists() and target.is_dir() and not any(target.iterdir())
                if ok:
                    target.rmdir()
                else:
                    note = "Folder is not empty or no longer exists."
            elif action_type == "delete":
                retention_id = str(item.get("retention_id") or "")
                ok = bool(retention_id) and action_history.restore_retained_path(retention_id)
                if ok:
                    from app.mediamanager.db.media_repo import add_media_item
                    try:
                        if Path(old_path).is_file() and Path(old_path).suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS):
                            ext = Path(old_path).suffix.lower()
                            add_media_item(self.conn, old_path, "image" if ext in IMAGE_EXTS else "video")
                    except Exception:
                        pass
                else:
                    note = "Undo not available: file no longer exists in MediaLens retention."
            elif action_type == "metadata":
                from native.mediamanagerx_app.action_edits import apply_edit_state
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                ok = apply_edit_state(self.conn, dict(payload.get("old") or {}))
            elif action_type == "hidden":
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                old_hidden = bool(payload.get("old_hidden"))
                target = str(payload.get("target") or item_type)
                if target == "collection":
                    ok = self.repo.set_collection_hidden(int(payload.get("collection_id") or 0), old_hidden)
                elif target == "folder" or item_type == "folder":
                    ok = self.repo.set_folder_hidden(old_path, old_hidden)
                else:
                    ok = self.repo.set_media_hidden(old_path, old_hidden)
            elif action_type == "rotate":
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                degrees = int(payload.get("degrees") or 0)
                if degrees:
                    self._rotate_media_sync(old_path, -degrees)
                    ok = True
        except Exception as exc:
            ok = False
            note = str(exc) or "Undo failed."
        action_history_repo.update_item_state(
            self.conn,
            item_id,
            current_state="undone" if ok else "unavailable",
            last_change_source=source if ok else str(item.get("last_change_source") or "original_action"),
            notes=note,
        )
        action_history_repo.recompute_entry_undo_state(self.conn, entry_id)
        if ok and emit:
            self._after_history_restore()
            self.actionHistoryChanged.emit()
        return ok

    def _redo_history_item(self, item_id: int, *, source: str, emit: bool = True) -> bool:
        from app.mediamanager.db import action_history_repo
        from native.mediamanagerx_app import action_history
        found = action_history_repo.get_item_with_entry(self.conn, int(item_id))
        if not found:
            return False
        item, entry = found
        action_type = str(entry.get("action_type") or "")
        entry_id = int(entry["id"])
        if not item or str(item.get("current_state") or "") != "undone":
            return False
        old_path = str(item.get("old_path") or "")
        new_path = str(item.get("new_path") or "")
        item_type = str(item.get("item_type") or "file")
        ok = False
        retention_id = None
        note = None
        try:
            if action_type in {"move", "rename"}:
                ok = action_history.move_path(old_path, new_path)
                if ok:
                    action_history.update_media_path_after_restore(self.conn, old_path, new_path, item_type)
            elif action_type == "copy":
                if item_type == "folder":
                    shutil.copytree(old_path, new_path)
                else:
                    shutil.copy2(old_path, new_path)
                ok = True
            elif action_type == "create_folder":
                Path(new_path).mkdir(parents=True, exist_ok=False)
                ok = True
            elif action_type == "delete":
                days = int(self.settings.value("gallery/medialens_retention_days", 30, type=int))
                retention_id = action_history.retain_path(old_path, days)
                ok = bool(retention_id)
                if not ok:
                    note = "Redo delete failed because the path no longer exists."
            elif action_type == "metadata":
                from native.mediamanagerx_app.action_edits import apply_edit_state
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                ok = apply_edit_state(self.conn, dict(payload.get("new") or {}))
            elif action_type == "hidden":
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                new_hidden = bool(payload.get("new_hidden"))
                target = str(payload.get("target") or item_type)
                if target == "collection":
                    ok = self.repo.set_collection_hidden(int(payload.get("collection_id") or 0), new_hidden)
                elif target == "folder" or item_type == "folder":
                    ok = self.repo.set_folder_hidden(old_path, new_hidden)
                else:
                    ok = self.repo.set_media_hidden(old_path, new_hidden)
            elif action_type == "rotate":
                payload = json.loads(str(item.get("metadata_json") or "{}"))
                degrees = int(payload.get("degrees") or 0)
                if degrees:
                    self._rotate_media_sync(old_path, degrees)
                    ok = True
        except Exception as exc:
            ok = False
            note = str(exc) or "Redo failed."
        action_history_repo.update_item_state(
            self.conn,
            item_id,
            current_state="applied" if ok else "unavailable",
            last_change_source=source if ok else str(item.get("last_change_source") or "group_undo"),
            retention_id=retention_id,
            notes=note,
        )
        action_history_repo.recompute_entry_undo_state(self.conn, entry_id)
        if ok and emit:
            self._after_history_restore()
            self.actionHistoryChanged.emit()
        return ok

    def _after_history_restore(self) -> None:
        try:
            self._invalidate_scan_caches()
        except Exception:
            pass
        try:
            self.collectionsChanged.emit()
        except Exception:
            pass
        try:
            self.galleryScopeChanged.emit()
        except Exception:
            pass
        try:
            self.galleryFilterSensitiveMetadataChanged.emit()
        except Exception:
            pass

    @Slot(str)
    def paste_into_folder_async(self, target_folder: str) -> None:
        target_dir = Path(target_folder)
        try:
            mime = QApplication.clipboard().mimeData()
            if not mime.hasUrls():
                self.fileOpFinished.emit("paste", False, "", "")
                return
            is_move = bool(mime.hasFormat("Preferred DropEffect") and mime.data("Preferred DropEffect")[0] == 2)
            src_paths = [Path(p) for p in self._dedupe_file_op_paths([url.toLocalFile() for url in mime.urls() if url.toLocalFile()])]
            op_type = "paste_move" if is_move else "paste_copy"
            self._process_file_op(op_type, src_paths, target_dir)
        except Exception:
            self.fileOpFinished.emit("paste", False, "", "")

    @staticmethod
    def _path_contains(parent: str, child: str) -> bool:
        parent_key = str(parent or "").replace("/", "\\").rstrip("\\").casefold()
        child_key = str(child or "").replace("/", "\\").rstrip("\\").casefold()
        if not parent_key or not child_key:
            return False
        return child_key == parent_key or child_key.startswith(parent_key + "\\")

    def _dedupe_file_op_paths(self, paths: list[str]) -> list[str]:
        resolved_paths: list[str] = []
        seen: set[str] = set()
        for raw_path in list(paths or []):
            clean = str(raw_path or "").strip()
            if not clean:
                continue
            try:
                resolved = str(Path(clean).resolve())
            except Exception:
                resolved = clean
            key = resolved.replace("/", "\\").rstrip("\\").casefold()
            if key in seen:
                continue
            seen.add(key)
            resolved_paths.append(resolved)

        folder_paths: list[str] = []
        for path in resolved_paths:
            try:
                if Path(path).is_dir():
                    folder_paths.append(path)
            except Exception:
                continue

        deduped: list[str] = []
        for path in sorted(resolved_paths, key=lambda value: (len(str(value)), str(value).casefold())):
            if any(self._path_contains(folder, path) for folder in folder_paths if not self._path_contains(path, folder)):
                continue
            deduped.append(path)
        return deduped



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
