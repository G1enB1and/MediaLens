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
            allowed = (
                "gallery.randomize", 
                "gallery.restore_last", 
                "gallery.show_hidden",
                "gallery.include_nested_files",
                "gallery.show_folders",
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
                "scanners.text_detection.enabled",
                "scanners.ocr_text.enabled",
                "scanners.ocr_text.run_fast",
                "scanners.ocr_text.run_ai",
                "scanners.ocr_text.all_files",
            )
            if key not in allowed and key not in {"duplicate.rules.merge_before_delete", "duplicate.rules.preferred_folders_enabled"} and not key.startswith("metadata.display.") and not key.startswith("duplicate.rules.merge"):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))
            if key == "gallery.randomize" and bool(value):
                self._reset_session_shuffle_order()
            if key.startswith("ui.") or key.startswith("metadata.display.") or key in {"gallery.show_hidden", "gallery.include_nested_files", "gallery.show_folders", "gallery.mute_video_by_default", "player.autoplay_gallery_animated_gifs", "player.autoplay_preview_animated_gifs"}:
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
                if key in {"gallery.show_hidden", "gallery.include_nested_files"}:
                    self.galleryScopeChanged.emit()
            elif key in {"duplicate.rules.merge_before_delete", "duplicate.rules.preferred_folders_enabled"} or key.startswith("duplicate.rules.merge"):
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
            elif key.startswith("scanners."):
                self.settings.sync()
                scanner_key = "ocr_text" if "ocr_text" in key else "text_detection"
                self.scannerStatusChanged.emit(scanner_key, self._scanner_status_payload(scanner_key))
            if key == "ui.show_bottom_panel":
                self._emit_compare_state_changed()
            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            if key not in ("gallery.start_folder", "gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold", "ui.accent_color", "ui.theme_mode", "ui.advanced_search_saved_queries", "metadata.display.order", "duplicate.settings.active_tab", "player.video_loop_mode", "player.video_loop_cutoff_seconds", "scanners.text_detection.interval_hours", "scanners.ocr_text.interval_hours", "scanners.text_detection.source_folders", "scanners.ocr_text.source_folders") and not key.startswith("metadata.layout.") and not key.startswith("duplicate.rules.") and key != "duplicate.priorities.order":
                return False
            if key == "gallery.view_mode":
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
            elif key in {"scanners.text_detection.interval_hours", "scanners.ocr_text.interval_hours"}:
                try:
                    value = str(max(1, int(str(value or "24").strip())))
                except Exception:
                    return False
            elif key in {"scanners.text_detection.source_folders", "scanners.ocr_text.source_folders"}:
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
                current_accent = str(self.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
                self.accentColorChanged.emit(current_accent)
            elif key in ("gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold"):
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
                scanner_key = "ocr_text" if "ocr_text" in key else "text_detection"
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
        success = self.repo.set_media_hidden(path, hidden)
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(str, bool, result=bool)
    def set_folder_hidden(self, path: str, hidden: bool) -> bool:
        success = self.repo.set_folder_hidden(path, hidden)
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(int, bool, result=bool)
    def set_collection_hidden(self, collection_id: int, hidden: bool) -> bool:
        success = self.repo.set_collection_hidden(collection_id, hidden)
        if success:
            # Emit a signal that collections updated if we have one
            # self.collectionsUpdated.emit()
            pass
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
                is_video = path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))
                if is_video:
                    import subprocess, json, tempfile
                    
                    # 1. Probe current rotation
                    current_ccw_rot = 0.0
                    try:
                        cmd_probe = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', path]
                        res = _run_hidden_subprocess(cmd_probe, capture_output=True, text=True)
                        data = json.loads(res.stdout)
                        for st in data.get('streams', []):
                            if st.get('codec_type') == 'video': # check video stream
                                # Read tags (rare nowadays)
                                tags = st.get('tags', {})
                                if 'rotate' in tags:
                                    current_ccw_rot = float(tags['rotate'])
                                # Read side data (modern standard)
                                for sd in st.get('side_data_list', []):
                                    if 'rotation' in sd:
                                        # FFprobe reports CCW as positive.
                                        current_ccw_rot = float(sd['rotation'])
                                break
                    except Exception as e:
                        print("Warning: Failed to probe rotation:", e)
                    
                    # Frontend degrees: 90 is CCW, -90 is CW. 
                    # new_ccw = current + delta
                    new_ccw_rot = (current_ccw_rot + degrees) % 360
                    if new_ccw_rot < 0:
                        new_ccw_rot += 360
                    
                    # 2. FFmpeg copy and set rotation
                    # For FFmpeg, we set the input's display rotation so it copies that directly to the output.
                    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(path)[1], delete=False) as tmp:
                        tmp_name = tmp.name
                    
                    cmd_ffmpeg = [
                        'ffmpeg', '-y', 
                        '-display_rotation', str(new_ccw_rot),
                        '-i', path,
                        '-c', 'copy',
                        tmp_name
                    ]
                    
                    # hide ffmpeg output
                    _run_hidden_subprocess(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # 3. Replace original file
                    import shutil
                    shutil.move(tmp_name, path)
                else:
                    from PIL import Image
                    with Image.open(path) as img:
                        rotated = img.rotate(degrees, expand=True)
                        exif = img.info.get('exif')
                        if exif:
                            rotated.save(path, exif=exif)
                        else:
                            rotated.save(path)
                
                # If this is a video, delete the cached poster so it regenerates on next view
                if is_video:
                    poster = self._video_poster_path(Path(path))
                    if poster.exists():
                        try: poster.unlink()
                        except Exception: pass
                        
                # Update SQLite so width and height are inverted
                try:
                    from app.mediamanager.utils.pathing import normalize_windows_path
                    if hasattr(self, 'conn') and self.conn:
                        norm = normalize_windows_path(path)
                        # Swap width and height for 90-degree rotations
                        if degrees in (90, -90, 270, -270):
                            self.conn.execute("UPDATE media_items SET width = height, height = width WHERE path = ?", (norm,))
                            self.conn.commit()
                except Exception: pass
                
                # Finally, inform frontend that a file was modified so it can refresh the thumbnail
                self.fileOpFinished.emit("rotate", True, path, path)
            except Exception as e:
                print(f"Failed to rotate media: {e}")

        # Run in background to prevent freezing the UI on large videos
        threading.Thread(target=work, daemon=True).start()

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
            self._invalidate_scan_caches()
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
            self._invalidate_scan_caches()
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
            except Exception: pass
            self.fileOpFinished.emit("rename", ok, old, newp)
            self._invalidate_scan_caches()
        threading.Thread(target=work, daemon=True).start()
        return True

    @Slot(str, str, str, result=str)
    def themed_text_input(self, title: str, label: str, text: str = "") -> str:
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        value, ok = _run_themed_text_input_dialog(parent, str(title or ""), str(label or ""), text=str(text or ""))
        return str(value or "") if ok else ""

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

        def work():
            from app.mediamanager.db.media_repo import rename_media_path, move_directory_in_db, add_media_item, get_media_by_path
            from app.mediamanager.db.tags_repo import attach_tags, list_media_tags
            
            
            is_move = op_type in ("move", "paste_move")
            sticky_action = None
            any_ok = False
            
            try:
                for src in src_paths:
                    if not src.exists():
                        continue
                    
                    dst = target_dir / src.name
                    action = "keep_both"
                    final_dst = dst
                    
                    if dst.exists():
                        if dst.samefile(src):
                            continue
                        
                        if sticky_action:
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
                        
                        action = res["action"]
                        if action == "skip":
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
                            if src.is_dir(): shutil.copytree(src, final_dst)
                            else: shutil.copy2(src, final_dst)
                            
                            ext = final_dst.suffix.lower()
                            mtype = "image" if ext in IMAGE_EXTS else "video"
                            new_media_id = add_media_item(self.conn, str(final_dst), mtype)
                            if src.is_file():
                                src_media = get_media_by_path(self.conn, str(src))
                                if src_media:
                                    src_tags = list_media_tags(self.conn, int(src_media["id"]))
                                    if src_tags:
                                        attach_tags(self.conn, int(new_media_id), src_tags)
                        
                        any_ok = True
                    except Exception as e:
                        pass

                op_signal = "paste" if "paste" in op_type else op_type
                self.fileOpFinished.emit(op_signal, any_ok, "", str(target_dir))
            except Exception as e:
                self.fileOpFinished.emit(op_type, False, "", "")
            
            self._invalidate_scan_caches()

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
            p = Path(path_str)
            if not p.exists():
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False

            self.close_native_video()
            QApplication.processEvents()

            use_medialens_retention = bool(self.settings.value("gallery/use_medialens_retention", False, type=bool))
            use_recycle = bool(self.settings.value("gallery/use_recycle_bin", True, type=bool))
            
            if use_medialens_retention:
                from native.mediamanagerx_app.recycle_bin import move_to_recycle_bin
                days = int(self.settings.value("gallery/medialens_retention_days", 30, type=int))
                deleted = move_to_recycle_bin(path_str, days)
                if not deleted and p.exists():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
            elif use_recycle:
                deleted = send_to_recycle_bin(path_str)
                if not deleted and p.exists():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
            else:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

            from app.mediamanager.utils.pathing import normalize_windows_path
            self.conn.execute("DELETE FROM media_items WHERE path = ?", (normalize_windows_path(path_str),))
            self.conn.commit()
            self._invalidate_scan_caches()
            self.collectionsChanged.emit()
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(str, result=bool)
    def delete_path_permanent(self, path_str: str) -> bool:
        try:
            p = Path(path_str)
            if not p.exists():
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False

            self.close_native_video()
            QApplication.processEvents()

            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

            from app.mediamanager.utils.pathing import normalize_windows_path
            self.conn.execute("DELETE FROM media_items WHERE path = ?", (normalize_windows_path(path_str),))
            self.conn.commit()
            self._invalidate_scan_caches()
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(str, str, result=str)
    def create_folder(self, parent_path: str, name: str) -> str:
        try:
            p = Path(parent_path) / name
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        except Exception: return ""

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
