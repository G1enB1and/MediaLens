from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class Bridge(QObject):
    selectedFolderChanged = Signal(str)
    openVideoRequested = Signal(str, bool, bool, bool, int, int)  # path, autoplay, loop, muted, w, h
    openVideoInPlaceRequested = Signal(str, int, int, int, int, bool, bool, bool, int, int) # path, x, y, w, h, autoplay, loop, muted, pw, ph
    updateVideoRectRequested = Signal(int, int, int, int)
    videoPreprocessingStatus = Signal(str)  # status message (empty = done)
    videoPlaybackStarted = Signal() # Signal that native player has received first frame
    videoSuppressed = Signal(bool) # Signal when video is hidden/suppressed (e.g. by header)
    closeVideoRequested = Signal()
    videoMutedChanged = Signal(bool)
    videoPausedChanged = Signal(bool)

    uiFlagChanged = Signal(str, bool)  # key, value
    compareStateChanged = Signal("QVariantMap")
    compareSelectionStateChanged = Signal(str, list)
    compareKeepPathChanged = Signal(str, bool)
    compareDeletePathChanged = Signal(str, bool)
    compareBestPathChanged = Signal(str, bool)
    metadataRequested = Signal(list)
    loadFolderRequested = Signal(str)
    startNativeDragRequested = Signal(list, str, int, int)
    navigateToFolderRequested = Signal(str)
    navigateBackRequested = Signal()
    navigateForwardRequested = Signal()
    navigateUpRequested = Signal()
    refreshFolderRequested = Signal()
    openSettingsDialogRequested = Signal()

    accentColorChanged = Signal(str)
    # Async file ops (so WebEngine UI doesn't freeze during rename)
    fileOpFinished = Signal(str, bool, str, str)  # op, ok, old_path, new_path

    # Media scanning signals
    scanStarted = Signal(str)
    scanFinished = Signal(str, int)  # folder, count
    selectionChanged = Signal(list)  # list of folder paths
    scanProgress = Signal(str, int)  # file_path, percentage
    navigationStateChanged = Signal(bool, bool, bool, str)  # can_back, can_forward, can_up, current_path
    childFoldersListed = Signal(str, list)  # request_id, folders
    mediaCounted = Signal(str, int)  # request_id, count
    mediaFileCounted = Signal(str, int)  # request_id, file count
    mediaListed = Signal(str, list)  # request_id, items
    galleryScopeChanged = Signal()
    galleryFilterSensitiveMetadataChanged = Signal()
    textProcessingStarted = Signal(str, int)  # stage label, total items
    textProcessingProgress = Signal(str, int, int)  # stage label, current, total
    textProcessingFinished = Signal()
    manualOcrFinished = Signal(str, str, str)  # path, text, error
    localAiCaptioningStarted = Signal(int)
    localAiCaptioningProgress = Signal(str, int, int)
    localAiCaptioningStatus = Signal(str)
    localAiCaptioningItemFinished = Signal(str, list, str, str)
    localAiCaptioningFinished = Signal(int, str)
    localAiModelInstallStatus = Signal(str, "QVariantMap")
    scannerStatusChanged = Signal(str, "QVariantMap")
    progressToastsRevealRequested = Signal()
    
    # Update Signals
    updateAvailable = Signal(str, bool)  # version, manual
    updateDownloadProgress = Signal(int)
    updateError = Signal(str)
    
    dragOverFolder = Signal(str)
    collectionsChanged = Signal()
    pinnedFoldersChanged = Signal(list)
    # Native Tooltip Controls
    updateTooltipRequested = Signal(int, bool, str) # count, isCopy, targetFolder
    hideTooltipRequested = Signal()
    conflictDialogRequested = Signal(str, str)
    nativeDragFinished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        print("Bridge: Initializing...")
        self._selected_folders: list[str] = []
        self._active_collection_id: int | None = None
        self._active_collection_name: str = ""
        self._active_smart_collection_key: str = ""
        self._active_smart_collection_name: str = ""
        self._scan_abort = False
        self._scan_lock = threading.Lock()
        self.drag_paths: list[str] = []
        self.drag_target_folder: str = ""
        self._last_dlg_res = None
        self._can_nav_back = False
        self._can_nav_forward = False
        self._local_ai_service = None
        self._local_ai_service_key = ""
        self._local_ai_running = False
        self._local_ai_lock = threading.Lock()
        self._local_ai_cancel = threading.Event()
        self._local_ai_processes: set[subprocess.Popen] = set()
        self._local_ai_shutting_down = False
        self._local_ai_model_installs: set[str] = set()
        self._local_ai_runtime_status_cache: dict[str, tuple[float, dict]] = {}
        
        appdata = _appdata_runtime_dir()
        _migrate_legacy_debugging_logs(appdata)
        self._thumb_dir = appdata / "thumbs"
        self._thumb_dir.mkdir(parents=True, exist_ok=True)
        self._logged_tool_paths: set[str] = set()
        self._logged_missing_tools: set[str] = set()
        
        # Initialize Logging
        self.log_path = _debugging_logs_dir(appdata) / "app.log"
        self._verbose_logs = str(os.environ.get("MEDIALENS_VERBOSE_LOGS", "") or "").strip().lower() in {"1", "true", "yes", "on"}
        def _log(msg):
            try:
                msg = _sanitize_diagnostic_text(msg)
                if not _diagnostic_log_should_write(msg, verbose=self._verbose_logs):
                    return
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.ctime()}] {msg}\n")
            except Exception: pass
        self._log = _log
        self._log(f"Bridge: Initializing (Version: {__version__})...")
        if os.name == "nt":
            self._log(
                "WebEngine runtime: "
                f"enabled={bool(_WINDOWS_WEBENGINE_RUNTIME.get('enabled'))} "
                f"reason={_WINDOWS_WEBENGINE_RUNTIME.get('reason') or 'n/a'} "
                f"QT_OPENGL={_WINDOWS_WEBENGINE_RUNTIME.get('qt_opengl') or '<unset>'} "
                f"QTWEBENGINE_CHROMIUM_FLAGS={_WINDOWS_WEBENGINE_RUNTIME.get('chromium_flags') or '<unset>'}"
            )
        
        # Initialize Database
        from app.mediamanager.db.connect import connect_db
        self.db_path = _runtime_db_path(appdata)
        self._log(f"DB Path = {self.db_path}")
        self.conn = connect_db(str(self.db_path))
        from app.mediamanager.db.repository import MediaRepository
        self.repo = MediaRepository(self.conn)

        # Migration for AI EXIF fields -> Embedded
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(media_metadata)")
            cols = [c[1] for c in cursor.fetchall()]
            if "exif_tags" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN exif_tags TO embedded_tags")
            elif "embedded_tags" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_tags TEXT")

            if "exif_comments" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN exif_comments TO embedded_comments")
            elif "embedded_comments" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_comments TEXT")

            if "embedded_metadata_parser_version" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_parser_version TEXT")

            if "embedded_metadata_json" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_json TEXT NOT NULL DEFAULT '{}'")

            if "embedded_metadata_summary" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_summary TEXT")

            if "embedded_ai_prompt" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_prompt TO ai_prompt")
            elif "ai_prompt" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_prompt TEXT")

            if "ai_negative_prompt" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_negative_prompt TEXT")

            if "embedded_ai_params" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_params TO ai_params")
            elif "ai_params" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_params TEXT")
            self.conn.commit()
        except Exception as e:
            print(f"Migration Error: {e}")

        self.settings = app_settings()
        Theme.set_theme_mode(str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"))
        self._ocr_text_processing_active = False
        self._scanner_schedule_timer = QTimer(self)
        self._scanner_schedule_timer.setInterval(60_000)
        self._scanner_schedule_timer.timeout.connect(self._check_scanner_schedules)
        self._scanner_schedule_timer.start()
        self.nam = QNetworkAccessManager(self)
        self.nam.setRedirectPolicy(QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self._update_reply = None
        self._download_reply = None
        self._session_shuffle_seed = random.getrandbits(32)
        self._session_shuffle_random = random.Random(self._session_shuffle_seed)
        self._session_shuffle_order: dict[str, float] = {}
        self._current_gallery_filter: str = "all"
        self._current_gallery_search: str = ""
        self._current_gallery_tag_scope_search: str = ""
        
        # Hybrid Fast-Load Cache
        self._disk_cache: dict[str, Path] = {}
        self._disk_cache_key: str = "" # Hash of selected folders list
        self._last_full_scan_key: str = ""
        self._disk_cache_by_scope: dict[str, dict[str, Path]] = {}
        self._warm_scan_keys: set[str] = set()
        self._text_processing_generation: int = 0
        self._text_processing_paused: bool = False
        self._text_processing_active: bool = False
        self._text_processing_scope_key: tuple = ("none",)
        self._text_processing_thread: threading.Thread | None = None
        self._lightbox_background_pause_depth: int = 0
        self._lightbox_paused_text_processing: bool = False
        self._scan_performance_paused: bool = False
        self._performance_pause_lock = threading.Lock()

        # Viewport-priority scanning: paths currently visible in gallery jump to front of scan queue.
        self._priority_paths: set[str] = set()
        self._priority_lock = threading.Lock()

        # Scan checkpointing: track which paths have been deep-scanned per scope, persisted to disk.
        self._checkpoint_path = appdata / "scan_checkpoint.json"
        self._checkpoint_lock = threading.Lock()
        self._checkpoint_dirty_count = 0
        self._scan_checkpoint: dict[str, set[str]] = self._load_scan_checkpoint()

        # Set by app.aboutToQuit so daemon threads stop emitting signals before
        # Qt deletes the Bridge's C++ half during shutdown.
        self._shutting_down: bool = False

        self._compare_paths: dict[str, str] = {"left": "", "right": ""}
        self._compare_keep_paths: set[str] = set()
        self._compare_delete_paths: set[str] = set()
        self._compare_best_path: str = ""
        self._compare_selection_revision: int = 0
        self._compare_state_emit_pending: bool = False
        self._settings_modal_bottom_restore: bool | None = None

        # Connect blocking signal for cross-thread dialogs
        self.conflictDialogRequested.connect(self._invoke_conflict_dialog, Qt.BlockingQueuedConnection)
        self._last_dlg_res = {"action": "skip", "apply_all": False, "new_existing": "", "new_incoming": ""}

        print(f"Bridge: Initialized (Session Seed: {self._session_shuffle_seed})")

    @Slot(str)
    def debug_log(self, msg: str) -> None:
        """Receive frontend diagnostics without bloating logs during normal use."""
        text = str(msg or "")
        if "JS ERROR" in text or getattr(self, "_verbose_logs", False):
            self._log(f"JS Debug: {text}")

    def _thumb_key(self, path: Path) -> str:
        s = str(path).replace("\\", "/").lower().encode("utf-8")
        return hashlib.sha1(s).hexdigest()

    def _video_poster_path(self, video_path: Path) -> Path:
        return self._thumb_dir / f"{self._thumb_key(video_path)}.jpg"

    def _video_needs_ascii_runtime_path(self, video_path: Path) -> bool:
        try:
            raw = str(video_path)
        except Exception:
            return False
        return any(ord(ch) > 127 for ch in raw)

    def _video_runtime_alias_path(self, video_path: Path) -> Path:
        runtime_dir = _appdata_runtime_dir() / "video-runtime-aliases"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        suffix = video_path.suffix or ".bin"
        return runtime_dir / f"{self._thumb_key(video_path)}{suffix.lower()}"

    def _video_runtime_path(self, video_path: str | Path) -> str:
        path_obj = Path(video_path)
        if not self._video_needs_ascii_runtime_path(path_obj):
            return str(path_obj)

        alias_path = self._video_runtime_alias_path(path_obj)
        try:
            src_stat = path_obj.stat()
        except Exception:
            return str(path_obj)

        try:
            if alias_path.exists():
                alias_stat = alias_path.stat()
                if alias_stat.st_size == src_stat.st_size and alias_stat.st_mtime >= (src_stat.st_mtime - 1):
                    return str(alias_path)
                alias_path.unlink(missing_ok=True)
        except Exception:
            pass

        try:
            shutil.copy2(str(path_obj), str(alias_path))
            self._log(f"Using ASCII-safe runtime alias for video path: {path_obj.name}")
            return str(alias_path)
        except Exception as exc:
            try:
                self._log(f"Failed to create ASCII-safe runtime alias for '{path_obj.name}': {exc}")
            except Exception:
                pass
            return str(path_obj)

    def _bundled_tool_candidates(self, name: str) -> list[Path]:
        exe_name = f"{name}.exe" if os.name == "nt" else name
        roots: list[Path] = []
        try:
            roots.append(Path(sys.executable).resolve().parent)
        except Exception:
            pass
        try:
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                roots.append(Path(meipass).resolve())
        except Exception:
            pass
        try:
            roots.append(Path(__file__).resolve().parents[2])
        except Exception:
            pass

        candidates: list[Path] = []
        for root in roots:
            candidates.extend(
                [
                    root / "tools" / "ffmpeg" / "bin" / exe_name,
                    root / "tools" / exe_name,
                    root / exe_name,
                ]
            )
        return candidates

    def _media_tool_bin(self, name: str) -> str | None:
        env_key = f"MEDIALENS_{name.upper()}_PATH"
        env_path = str(os.environ.get(env_key, "") or "").strip().strip('"')
        candidates = [Path(env_path)] if env_path else []
        candidates.extend(self._bundled_tool_candidates(name))

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    resolved = str(candidate.resolve())
                    if name not in self._logged_tool_paths:
                        self._log(f"Using {name} binary: {resolved}")
                        self._logged_tool_paths.add(name)
                    return resolved
            except Exception:
                continue

        found = shutil.which(name)
        if found:
            if name not in self._logged_tool_paths:
                self._log(f"Using {name} from PATH: {found}")
                self._logged_tool_paths.add(name)
            return found

        if name not in self._logged_missing_tools:
            self._log(f"{name} binary not found. Bundled video tooling is missing and PATH lookup failed.")
            self._logged_missing_tools.add(name)
        return None

    def _ffmpeg_bin(self) -> str | None:
        return self._media_tool_bin("ffmpeg")

    def _ffprobe_bin(self) -> str | None:
        return self._media_tool_bin("ffprobe")

    def _ensure_video_poster(self, video_path: Path) -> Path | None:
        """Generate a poster jpg for a video or image using ffmpeg (if missing)."""
        out = self._video_poster_path(video_path)
        if out.exists():
            return out
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            self._log(f"Video poster unavailable; ffmpeg not found for {video_path}")
            return None
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            ext = video_path.suffix.lower()
            is_vid = ext in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}
            runtime_path = self._video_runtime_path(video_path) if is_vid else str(video_path)
            # For images, don't use -ss as it can fail for 0-duration files
            vf = "thumbnail,scale=min(640\\,iw):-2" if is_vid else "scale=min(640\\,iw):-2"
            
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            if is_vid:
                cmd += ["-ss", "0.5"]
            cmd += ["-i", runtime_path, "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out)]
            
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "").strip().replace("\r", " ").replace("\n", " ")
                self._log(f"Video poster generation failed for {video_path}: exit={r.returncode} {err[:500]}")
                return None
            return out if out.exists() else None
        except Exception as e:
            self._log(f"Video poster generation error for {video_path}: {type(e).__name__}: {e}")
            return None
        
    def _is_animated(self, path: Path) -> bool:
        """Check if image is animated (GIF or animated WebP)."""
        suffix = path.suffix.lower()
        if suffix == ".gif":
            return True
        if suffix == ".webp":
            try:
                with open(path, "rb") as f:
                    header = f.read(32)
                if header[0:4] == b"RIFF" and header[8:12] == b"WEBP" and header[12:16] == b"VP8X":
                    flags = header[20]
                    return bool(flags & 2)
            except Exception:
                pass
        return False

    @Slot(list)
    def set_selected_folders(self, folders: list[str]) -> None:
        if folders == self._selected_folders:
            return
        self._selected_folders = folders
        self._current_gallery_tag_scope_search = ""
        if folders:
            self._active_collection_id = None
            self._active_collection_name = ""
            self._active_smart_collection_key = ""
            self._active_smart_collection_name = ""
        try:
            # Persistent settings
            settings = app_settings()
            primary = folders[0] if folders else ""
            settings.setValue("gallery/last_folder", primary)
        except Exception:
            pass
        self.selectionChanged.emit(self._selected_folders)

    def _pinned_folders_setting_key(self) -> str:
        return "folders/pinned"

    def _normalize_pinned_folder_paths(self, folders: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                resolved = str(path_obj.absolute())
            except Exception:
                resolved = path_str
            key = resolved.replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(resolved)
        return normalized

    def _read_pinned_folders(self) -> list[str]:
        raw_value = self.settings.value(self._pinned_folders_setting_key(), "[]", type=str)
        try:
            parsed = json.loads(str(raw_value or "[]"))
        except Exception:
            parsed = []
        if not isinstance(parsed, list):
            parsed = []
        normalized = self._normalize_pinned_folder_paths(parsed)
        if normalized != parsed:
            try:
                self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
            except Exception:
                pass
        return normalized

    def _write_pinned_folders(self, folders: list[str]) -> None:
        normalized = self._normalize_pinned_folder_paths(folders)
        self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
        self.settings.sync()
        self.pinnedFoldersChanged.emit(normalized)

    @Slot(result=list)
    def list_pinned_folders(self) -> list:
        return self._read_pinned_folders()

    @Slot(str, result=bool)
    def is_folder_pinned(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        return any(path.replace("\\", "/").lower() == target_key for path in self._read_pinned_folders())

    @Slot(str, result=bool)
    def pin_folder(self, folder_path: str) -> bool:
        return self.pin_folders([folder_path]) > 0

    @Slot(list, result=int)
    def pin_folders(self, folders: list[str]) -> int:
        existing = self._read_pinned_folders()
        existing_keys = {path.replace("\\", "/").lower() for path in existing}
        added_count = 0
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                if not path_obj.exists() or not path_obj.is_dir():
                    continue
                normalized = str(path_obj.absolute())
            except Exception:
                continue
            key = normalized.replace("\\", "/").lower()
            if key in existing_keys:
                continue
            existing.append(normalized)
            existing_keys.add(key)
            added_count += 1
        if added_count:
            self._write_pinned_folders(existing)
        return added_count

    @Slot(str, result=bool)
    def unpin_folder(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        existing = self._read_pinned_folders()
        remaining = [path for path in existing if path.replace("\\", "/").lower() != target_key]
        if remaining == existing:
            return False
        self._write_pinned_folders(remaining)
        return True

    @Slot(list)
    def set_drag_paths(self, paths: list[str]) -> None:
        """Called from JS to register the actual files being dragged."""
        self.drag_paths = [str(p) for p in paths]
        if not self.drag_paths:
            self.drag_target_folder = ""

    @Slot(str)
    def set_drag_target_folder(self, folder_path: str) -> None:
        self.drag_target_folder = str(folder_path or "")

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

    @Slot(result=list)
    def get_selected_folders(self) -> list:
        return self._selected_folders

    @Slot(str, str)
    def set_current_gallery_scope_state(self, filter_type: str, search_query: str) -> None:
        next_filter = str(filter_type or "all")
        next_search = str(search_query or "")
        if next_filter == self._current_gallery_filter and next_search == self._current_gallery_search:
            return
        self._current_gallery_filter = next_filter
        self._current_gallery_search = next_search
        self._current_gallery_tag_scope_search = ""
        self.galleryScopeChanged.emit()

    @Slot(str)
    def set_current_gallery_tag_scope_state(self, search_query: str) -> None:
        next_search = str(search_query or "")
        if next_search == self._current_gallery_tag_scope_search:
            return
        self._current_gallery_tag_scope_search = next_search
        self.galleryScopeChanged.emit()

    def _current_gallery_filter_uses_text(self) -> bool:
        _, text_filter, _, _, _ = self._parse_filter_groups(getattr(self, "_current_gallery_filter", "all"))
        return text_filter in {"text_detected", "no_text_detected"}

    def _current_gallery_filter_uses_ai(self) -> bool:
        _, _, _, _, ai_filter = self._parse_filter_groups(getattr(self, "_current_gallery_filter", "all"))
        return ai_filter in {"ai_generated", "non_ai"}

    @Slot(result="QVariantMap")
    def get_navigation_state(self) -> dict:
        current_path = self._selected_folders[0] if self._selected_folders else ""
        can_up = False
        if current_path:
            try:
                parent = Path(current_path).parent
                can_up = str(parent) != str(Path(current_path))
            except Exception:
                can_up = False
        return {
            "canBack": self._can_nav_back,
            "canForward": self._can_nav_forward,
            "canUp": can_up,
            "currentPath": current_path,
        }

    def emit_navigation_state(self) -> None:
        state = self.get_navigation_state()
        self.navigationStateChanged.emit(
            bool(state.get("canBack")),
            bool(state.get("canForward")),
            bool(state.get("canUp")),
            str(state.get("currentPath", "")),
        )

    def _list_child_folders_impl(self, folder_path: str) -> list:
        try:
            root = Path(str(folder_path or ""))
            if not root.exists() or not root.is_dir():
                return []
            children: list[dict] = []
            for child in root.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    children.append({
                        "name": child.name or str(child),
                        "path": str(child),
                    })
                except Exception:
                    continue
            children.sort(key=lambda item: str(item.get("name", "")).lower())
            return children
        except Exception:
            return []

    @Slot(str, result=list)
    def list_child_folders(self, folder_path: str) -> list:
        return self._list_child_folders_impl(folder_path)

    @Slot(str, str)
    def list_child_folders_async(self, request_id: str, folder_path: str) -> None:
        req = str(request_id or "")
        path = str(folder_path or "")

        def work() -> None:
            items = self._list_child_folders_impl(path)
            self.childFoldersListed.emit(req, items)

        threading.Thread(target=work, daemon=True).start()

    @Slot(int, result=bool)
    def set_active_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import get_collection
        try:
            collection = get_collection(self.conn, int(collection_id))
            if not collection:
                return False
            self._active_collection_id = int(collection["id"])
            self._active_collection_name = str(collection["name"])
            self._active_smart_collection_key = ""
            self._active_smart_collection_name = ""
            self._selected_folders = []
            self.selectionChanged.emit([])
            return True
        except Exception:
            return False

    @Slot(result=dict)
    def get_active_collection(self) -> dict:
        if self._active_collection_id is not None:
            return {"id": self._active_collection_id, "name": self._active_collection_name}
        if self._active_smart_collection_key:
            return {"id": -1, "name": self._active_smart_collection_name, "key": self._active_smart_collection_key, "smart": True}
        return {}

    def _smart_collection_defs(self) -> list[dict]:
        return [
            {"key": "acquired_7d", "name": "Acquired Last 7 Days", "field": "metadata_date", "days": 7},
            {"key": "acquired_14d", "name": "Acquired Last 14 Days", "field": "metadata_date", "days": 14},
            {"key": "acquired_30d", "name": "Acquired Last 30 Days", "field": "metadata_date", "days": 30},
            {"key": "modified_7d", "name": "Modified Last 7 Days", "field": "modified_time_utc", "days": 7},
            {"key": "modified_14d", "name": "Modified Last 14 Days", "field": "modified_time_utc", "days": 14},
            {"key": "modified_30d", "name": "Modified Last 30 Days", "field": "modified_time_utc", "days": 30},
            {"key": "no_tags", "name": "No Tags", "field": "no_tags"},
            {"key": "no_description", "name": "No Description", "field": "no_description"},
            {"key": "large_3mb", "name": "Larger Than 3 MB", "field": "file_size_gt_3mb"},
            {"key": "large_10mb", "name": "Larger Than 10 MB", "field": "file_size_gt_10mb"},
            {"key": "large_25mb", "name": "Larger Than 25 MB", "field": "file_size_gt_25mb"},
            {"key": "large_100mb", "name": "Larger Than 100 MB", "field": "file_size_gt_100mb"},
            {"key": "large_1gb", "name": "Larger Than 1 GB", "field": "file_size_gt_1gb"},
        ]

    def _smart_collection_def(self, key: str) -> dict | None:
        wanted = str(key or "").strip().lower()
        if not wanted:
            return None
        return next((item for item in self._smart_collection_defs() if str(item.get("key") or "").lower() == wanted), None)

    def _smart_collection_cutoff_iso(self, days: int) -> str:
        try:
            count = max(1, int(days or 0))
        except Exception:
            count = 7
        return (datetime.now(timezone.utc) - timedelta(days=count)).replace(microsecond=0).isoformat()

    @Slot(str, result=bool)
    def set_active_smart_collection(self, smart_key: str) -> bool:
        try:
            definition = self._smart_collection_def(str(smart_key or ""))
            if not definition:
                return False
            self._active_smart_collection_key = str(definition["key"])
            self._active_smart_collection_name = str(definition["name"])
            self._active_collection_id = None
            self._active_collection_name = ""
            self._selected_folders = []
            self.selectionChanged.emit([])
            return True
        except Exception:
            return False

    @Slot(result=dict)
    def get_active_smart_collection(self) -> dict:
        if not self._active_smart_collection_key:
            return {}
        return {"key": self._active_smart_collection_key, "name": self._active_smart_collection_name}

    @Slot(result=list)
    def list_smart_collections(self) -> list:
        from app.mediamanager.db.media_repo import count_media_in_smart_collection
        items: list[dict] = []
        try:
            for definition in self._smart_collection_defs():
                cutoff_iso = self._smart_collection_cutoff_iso(int(definition.get("days") or 0))
                count = count_media_in_smart_collection(self.conn, str(definition.get("field") or ""), cutoff_iso)
                items.append({
                    "key": str(definition.get("key") or ""),
                    "name": str(definition.get("name") or ""),
                    "field": str(definition.get("field") or ""),
                    "days": int(definition.get("days") or 0),
                    "item_count": int(count or 0),
                })
            return items
        except Exception:
            return []

    @Slot(result=list)
    def list_collections(self) -> list:
        from app.mediamanager.db.collections_repo import list_collections
        try:
            return list_collections(self.conn)
        except Exception:
            return []

    @Slot(str, result=dict)
    def create_collection(self, name: str) -> dict:
        from app.mediamanager.db.collections_repo import create_collection
        try:
            created = create_collection(self.conn, name)
            self.collectionsChanged.emit()
            return created
        except Exception:
            return {}

    @Slot(int, str, result=bool)
    def rename_collection(self, collection_id: int, name: str) -> bool:
        from app.mediamanager.db.collections_repo import rename_collection, get_collection
        try:
            ok = rename_collection(self.conn, int(collection_id), name)
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                collection = get_collection(self.conn, int(collection_id))
                self._active_collection_name = str(collection["name"]) if collection else ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, result=bool)
    def delete_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import delete_collection
        try:
            ok = delete_collection(self.conn, int(collection_id))
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                self._active_collection_id = None
                self._active_collection_name = ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, list, result=int)
    def add_paths_to_collection(self, collection_id: int, paths: list[str]) -> int:
        from app.mediamanager.db.collections_repo import add_media_paths_to_collection
        try:
            added = add_media_paths_to_collection(self.conn, int(collection_id), paths)
            self.collectionsChanged.emit()
            if added and self._active_collection_id == int(collection_id):
                self.selectionChanged.emit([])
            return int(added)
        except Exception:
            return 0

    @Slot(list, result=bool)
    def add_paths_to_collection_interactive(self, paths: list[str]) -> bool:
        from app.mediamanager.db.collections_repo import create_collection, list_collections
        clean_paths = [str(path or "").strip() for path in paths if str(path or "").strip()]
        if not clean_paths:
            return False
        try:
            collections = list_collections(self.conn)
            options = ["New collection..."] + [str(collection["name"]) for collection in collections]
            choice, ok = _run_themed_item_input_dialog(
                None,
                "Add to Collection",
                "Collection:",
                options,
                current=0,
                editable=False,
            )
            if not ok or not choice:
                return False

            if choice == "New collection...":
                name, created_ok = _run_themed_text_input_dialog(None, "New Collection", "Collection Name:")
                if not created_ok or not name.strip():
                    return False
                created = create_collection(self.conn, name)
                collection_id = int(created["id"])
            else:
                selected = next((c for c in collections if str(c["name"]) == choice), None)
                if not selected:
                    return False
                collection_id = int(selected["id"])

            added = self.add_paths_to_collection(collection_id, clean_paths)
            return added > 0
        except Exception:
            return False

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
        if not enabled:
            status = "Disabled"
        return {
            "key": scanner_key,
            "name": self._scanner_display_name(scanner_key),
            "enabled": enabled,
            "interval_hours": self._scanner_interval_hours(scanner_key),
            "last_run_utc": self._scanner_last_run_utc(scanner_key),
            "status": status,
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
            self._ensure_background_text_processing(force=True)
        if self._scanner_due("ocr_text"):
            self._run_ocr_text_scanner(force=True)

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

    def _run_ocr_text_scanner(self, *, force: bool = False) -> bool:
        if self._ocr_text_processing_active:
            return False
        if not force and not self._scanner_enabled("ocr_text"):
            self._set_scanner_status("ocr_text", "Disabled")
            return False
        entries = self._collect_text_scope_entries()
        if not entries:
            self._set_scanner_status("ocr_text", "Idle (no active scope)")
            return False

        def work() -> None:
            self._ocr_text_processing_active = True
            self._set_scanner_status("ocr_text", "Running")
            processed = 0
            saved = 0
            try:
                from app.mediamanager.db.media_repo import add_media_item, update_media_detected_text
                from app.mediamanager.utils.text_detection import extract_text_windows_ocr

                eligible = [
                    entry for entry in entries
                    if not entry.get("is_folder")
                    and self._effective_text_detected(entry)
                    and not str(entry.get("detected_text") or "").strip()
                ]
                total = len(eligible)
                if total <= 0:
                    self._set_scanner_status("ocr_text", "Idle", mark_run=True)
                    return
                for entry in eligible:
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
                        ocr_source_path = self._manual_ocr_source_path(p)
                        text = extract_text_windows_ocr(ocr_source_path)
                        if not text.strip():
                            continue
                        update_media_detected_text(self.conn, int(entry["id"]), text)
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

        threading.Thread(target=work, daemon=True, name="ocr-text-scanner").start()
        return True

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
                    entry["duplicate_best_reason"] = " â€¢ ".join(reasons)
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
            if key not in ("gallery.start_folder", "gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold", "ui.accent_color", "ui.theme_mode", "ui.advanced_search_saved_queries", "metadata.display.order", "duplicate.settings.active_tab", "player.video_loop_mode", "player.video_loop_cutoff_seconds", "scanners.text_detection.interval_hours", "scanners.ocr_text.interval_hours") and not key.startswith("metadata.layout.") and not key.startswith("duplicate.rules.") and key != "duplicate.priorities.order":
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

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

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

    @Slot(str, result=float)
    def get_video_duration_seconds(self, video_path: str) -> float:
        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe:
                self._log(f"Video duration unavailable; ffprobe not found for {video_path}")
                return 0.0
            runtime_path = self._video_runtime_path(video_path)
            cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", runtime_path]
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, check=True, timeout=5)
            return float((r.stdout or "").strip() or 0.0)
        except Exception as exc:
            self._log(f"Video duration probe failed for {video_path}: {type(exc).__name__}: {exc}")
            return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int, bool]:
        ffprobe = self._ffprobe_bin()
        if not ffprobe:
            self._log(f"Video size probe unavailable; ffprobe not found for {video_path}")
            return (0, 0, False)
        runtime_path = self._video_runtime_path(video_path)
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", runtime_path]
        try:
            import json
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "").strip().replace("\r", " ").replace("\n", " ")
                self._log(f"Video size probe failed for {video_path}: exit={r.returncode} {err[:500]}")
                return (0, 0, False)
            data = json.loads(r.stdout)
            streams = data.get("streams", [])
            if not streams: return (0, 0, False)
            for s in streams:
                if s.get("codec_type") == "video":
                    w_raw, h_raw = int(s.get("width", 0)), int(s.get("height", 0))
                    sar = s.get("sample_aspect_ratio", "1:1")
                    parsed_sar = 1.0
                    if sar and ":" in sar and sar != "1:1":
                        try: num, den = sar.split(":", 1); parsed_sar = float(num) / float(den)
                        except Exception: pass
                    w, h = max(2, int(w_raw * parsed_sar)), max(2, h_raw)
                    
                    cw_rot = 0
                    tags = s.get("tags", {})
                    if "rotate" in tags:
                        cw_rot = int(tags["rotate"]) % 360
                    for sd in s.get("side_data_list", []):
                        if "rotation" in sd:
                            cw_rot = int(abs(float(sd["rotation"]))) % 360
                    
                    if cw_rot in (90, 270): 
                        w, h = h, w
                        
                    return (w, h, (w % 2 != 0 or h % 2 != 0))
            return (0, 0, False)
        except Exception as exc:
            self._log(f"Video size probe error for {video_path}: {type(exc).__name__}: {exc}")
            return (0, 0, False)

    @Slot(str, bool, bool, bool, int, int, result=bool)
    def open_native_video(self, video_path: str, autoplay: bool, loop: bool, muted: bool, w: int = 0, h: int = 0) -> bool:
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video for non-file path: {video_path}")
                return False
            runtime_path = self._video_runtime_path(video_path)
            if w <= 0 or h <= 0:
                w, h, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (w % 2 != 0 or h % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, w, h)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoRequested.emit(str(fixed), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoRequested.emit(runtime_path, bool(autoplay), bool(loop), bool(muted), int(w), int(h))
            return True
        except Exception:
            return False

    @Slot(str, int, int, int, int, bool, bool, bool, int, int)
    def open_native_video_inplace(self, video_path: str, x: int, y: int, w: int, h: int, autoplay: bool, loop: bool, muted: bool, vw: int = 0, vh: int = 0) -> None:
        if not loop:
            d_s = self.get_video_duration_seconds(video_path)
            if self._should_loop_video(int(float(d_s or 0) * 1000)):
                loop = True
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video_inplace for non-file path: {video_path}")
                return
            runtime_path = self._video_runtime_path(video_path)

            if vw <= 0 or vh <= 0:
                vw, vh, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (vw % 2 != 0 or vh % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, vw, vh)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoInPlaceRequested.emit(str(fixed), int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoInPlaceRequested.emit(runtime_path, int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(vw), int(vh))
        except Exception:
            pass

    @Slot(str, int, int)
    def preload_video(self, video_path: str, w: int = 0, h: int = 0) -> None:
        """Proactively prepare a video for playback in the background."""
        def work():
            try:
                # 1. Probe if dimensions unknown
                nonlocal w, h
                if w <= 0 or h <= 0:
                    w, h, is_malformed = self._probe_video_size(video_path)
                else:
                    is_malformed = (w % 2 != 0 or h % 2 != 0)
                
                # 2. Trigger "safety gate" preprocessing ahead of time if malformed
                if is_malformed:
                    self._preprocess_to_even_dims(video_path, w, h)
                    
                # 3. Future: Warm up QMediaPlayer instance if needed
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    @Slot(int, int, int, int)
    def update_native_video_rect(self, x, y, w, h):
        self.updateVideoRectRequested.emit(x, y, w, h)

    @Slot(bool)
    def set_video_muted(self, muted: bool) -> None:
        self.videoMutedChanged.emit(muted)

    @Slot(bool)
    def set_video_paused(self, paused: bool) -> None:
        self.videoPausedChanged.emit(paused)

    def _preprocess_to_even_dims(self, video_path: str, w: int, h: int) -> str | None:
        import tempfile
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            self._log(f"Video preprocessing unavailable; ffmpeg not found for {video_path}")
            return None
        runtime_path = self._video_runtime_path(video_path)
        ew, eh = (w if w % 2 == 0 else w - 1), (h if h % 2 == 0 else h - 1)
        if ew <= 0 or eh <= 0: return None
        tmp = tempfile.NamedTemporaryFile(prefix="mmx_fixed_", suffix=".mkv", delete=False)
        tmp.close()
        out_path = tmp.name
        vf = f"scale={ew}:{eh},setsar=1,format=yuv420p"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", runtime_path, "-vf", vf, "-c:v", "mjpeg", "-q:v", "3", "-c:a", "copy", out_path]
        try:
            result = _run_hidden_subprocess(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                self._log(f"Video preprocessing succeeded for {video_path}: {out_path}")
                return out_path
            err_bytes = result.stderr or result.stdout or b""
            err = err_bytes.decode("utf-8", errors="replace") if isinstance(err_bytes, bytes) else str(err_bytes)
            self._log(f"Video preprocessing failed for {video_path}: exit={result.returncode} {err.strip()[:500]}")
        except Exception as exc:
            self._log(f"Video preprocessing error for {video_path}: {type(exc).__name__}: {exc}")
        return None

    @Slot(result=bool)
    def close_native_video(self) -> bool:
        try:
            self.closeVideoRequested.emit()
            return True
        except Exception:
            return False

    @Slot(str, list, str, result=bool)
    def dismiss_review_pair(self, path: str, related_paths: list, review_mode: str) -> bool:
        from app.mediamanager.db.media_repo import add_review_pair_exclusions

        try:
            return add_review_pair_exclusions(self.conn, path, related_paths or [], review_mode) > 0
        except Exception as exc:
            try:
                self._log(f"Dismiss review pair failed for {path!r}: {exc}")
            except Exception:
                pass
            return False

    @Slot(result=bool)
    def reset_review_group_exclusions(self) -> bool:
        from app.mediamanager.db.media_repo import clear_review_pair_exclusions

        try:
            clear_review_pair_exclusions(self.conn)
            return True
        except Exception as exc:
            try:
                self._log(f"Reset review group exclusions failed: {exc}")
            except Exception:
                pass
            return False

    @Slot(str, result=dict)
    def get_media_metadata(self, path: str) -> dict:
        return _load_media_metadata_payload(self.conn, path, self._log)

    @Slot(str, str, str, str, str, str, str, str, str)
    def update_media_metadata(self, path, title, desc, notes, etags="", ecomm="", aip="", ainp="", aiparam="") -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.metadata_repo import upsert_media_metadata
        try:
            m = get_media_by_path(self.conn, path)
            if m: upsert_media_metadata(self.conn, m["id"], title, desc, notes, etags, ecomm, aip, ainp, aiparam)
        except Exception: pass

    @Slot(str, str, str)
    def update_media_dates(self, path: str, exif_date_taken: str, metadata_date: str) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                update_media_dates(
                    self.conn,
                    m["id"],
                    exif_date_taken=exif_date_taken.strip() or None,
                    metadata_date=metadata_date.strip() or None,
                )
        except Exception:
            pass

    @Slot(str, bool)
    def update_media_text_override(self, path: str, text_present_override: bool) -> None:
        from app.mediamanager.db.media_repo import update_user_confirmed_text_detected
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                update_user_confirmed_text_detected(self.conn, m["id"], bool(text_present_override))
                if self._current_gallery_filter_uses_text():
                    self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
        except Exception:
            pass

    @Slot(str, str)
    def update_media_detected_text(self, path: str, detected_text: str) -> None:
        from app.mediamanager.db.media_repo import update_media_detected_text
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                update_media_detected_text(self.conn, m["id"], detected_text)
                self.galleryScopeChanged.emit()
        except Exception:
            pass

    def _manual_ocr_source_path(self, media_path: Path) -> Path:
        if media_path.suffix.lower() not in VIDEO_EXTS:
            return media_path
        poster = self._video_poster_path(media_path)
        if poster.exists():
            return poster
        poster = self._ensure_video_poster(media_path)
        if poster and poster.exists():
            return poster
        raise RuntimeError("No video preview image is available for OCR.")

    @Slot(str)
    def run_manual_ocr(self, path: str) -> None:
        def work() -> None:
            text = ""
            error = ""
            try:
                media_path = Path(path)
                if not media_path.exists() or not media_path.is_file():
                    raise FileNotFoundError("Selected file was not found.")
                from app.mediamanager.db.media_repo import update_media_detected_text, update_user_confirmed_text_detected
                from app.mediamanager.utils.text_detection import extract_text_windows_ocr

                ocr_source_path = self._manual_ocr_source_path(media_path)
                text = extract_text_windows_ocr(ocr_source_path)
                if text.strip():
                    m = self._ensure_media_record_for_tag_write(path)
                    if m:
                        update_media_detected_text(self.conn, m["id"], text)
                        update_user_confirmed_text_detected(self.conn, m["id"], True)
                        self.galleryScopeChanged.emit()
            except Exception as exc:
                error = str(exc) or "OCR failed."
            self.manualOcrFinished.emit(path, text, error)

        threading.Thread(target=work, daemon=True, name="manual-ocr").start()

    def _local_ai_source_path(self, media_path: Path) -> Path:
        suffix = media_path.suffix.lower()
        needs_poster = (
            suffix in VIDEO_EXTS
            or suffix in {".avif", ".heic", ".heif", ".tif", ".tiff", ".webp"}
            or self._is_animated(media_path)
        )
        if not needs_poster:
            return media_path
        poster = self._video_poster_path(media_path)
        if poster.exists():
            return poster
        poster = self._ensure_video_poster(media_path)
        if poster and poster.exists():
            return poster
        raise RuntimeError("No preview image is available for local AI captioning.")

    def _local_ai_models_dir_default(self) -> str:
        if bool(getattr(sys, "frozen", False)):
            return str(_appdata_runtime_dir() / "local_ai_models")
        from app.mediamanager.ai_captioning.local_captioning import project_models_dir

        return str(project_models_dir())

    def _local_ai_worker_source_root(self) -> Path:
        roots: list[Path] = []
        meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
        if meipass:
            roots.append(Path(meipass))
        if bool(getattr(sys, "frozen", False)):
            roots.append(Path(sys.executable).resolve().parent)
            roots.append(Path(sys.executable).resolve().parent / "_internal")
        roots.append(Path(__file__).resolve().parents[2])

        for root in roots:
            if (root / "app" / "mediamanager" / "ai_captioning" / "model_registry.py").is_file():
                return root
        return roots[0] if roots else Path(__file__).resolve().parents[2]

    def _local_ai_runtime_root(self) -> Path:
        configured = str(self.settings.value("ai_caption/runtime_root", "", type=str) or "").strip()
        if configured:
            return Path(configured)
        if bool(getattr(sys, "frozen", False)):
            return _appdata_runtime_dir() / "ai-runtimes"
        return Path(__file__).resolve().parents[2]

    def _local_ai_python_bootstrap_root(self) -> Path:
        configured = str(self.settings.value("ai_caption/python_bootstrap_root", "", type=str) or "").strip()
        if configured:
            return Path(configured)
        return _appdata_runtime_dir() / "python" / f"cpython-{LOCAL_AI_PYTHON_VERSION}"

    def _local_ai_python_bootstrap_exe(self) -> Path:
        if os.name == "nt":
            return self._local_ai_python_bootstrap_root() / "python.exe"
        return self._local_ai_python_bootstrap_root() / "bin" / "python"

    def _local_ai_bootstrap_download_dir(self) -> Path:
        return _appdata_runtime_dir() / "python-bootstrap"

    def _local_ai_requirements_path(self, spec) -> Path:
        source_root = self._local_ai_worker_source_root()
        candidates = [
            source_root / spec.requirements_file,
            source_root / "_internal" / spec.requirements_file,
            Path(__file__).resolve().parents[2] / spec.requirements_file,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]

    def _local_ai_worker_launcher(self, python_path: str | Path, worker_module: str) -> tuple[list[str], Path, str]:
        source_root = self._local_ai_worker_source_root()
        worker_script = source_root / Path(*str(worker_module).split(".")).with_suffix(".py")
        if worker_script.is_file():
            return [str(python_path), str(worker_script)], self._local_ai_runtime_root(), ""
        return [str(python_path), "-m", str(worker_module)], source_root, str(source_root)

    def _local_ai_subprocess_env(self, worker_pythonpath: str = "") -> dict[str, str]:
        parent_env = os.environ.copy()
        child_env = parent_env.copy()
        if bool(getattr(sys, "frozen", False)):
            safe_env: dict[str, str] = {}
            for key in (
                "APPDATA",
                "COMSPEC",
                "HOMEDRIVE",
                "HOMEPATH",
                "LOCALAPPDATA",
                "NUMBER_OF_PROCESSORS",
                "OS",
                "PATHEXT",
                "PROCESSOR_ARCHITECTURE",
                "PROCESSOR_IDENTIFIER",
                "PROCESSOR_LEVEL",
                "PROCESSOR_REVISION",
                "PROGRAMDATA",
                "SYSTEMDRIVE",
                "SYSTEMROOT",
                "TEMP",
                "TMP",
                "USERDOMAIN",
                "USERNAME",
                "USERPROFILE",
                "WINDIR",
            ):
                value = str(parent_env.get(key, "") or "").strip()
                if value:
                    safe_env[key] = value
            for key, value in parent_env.items():
                upper = str(key).upper()
                if upper.startswith(("CUDA_", "NVIDIA_", "NV_")):
                    safe_env[str(key)] = str(value)
            blocked_roots: list[str] = []
            try:
                app_root = Path(sys.executable).resolve().parent
                blocked_roots.append(str(app_root).replace("\\", "/").casefold())
                blocked_roots.append(str((app_root / "_internal")).replace("\\", "/").casefold())
            except Exception:
                pass
            try:
                meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
                if meipass:
                    blocked_roots.append(str(Path(meipass).resolve()).replace("\\", "/").casefold())
            except Exception:
                pass
            allowed_path_prefixes = (
                "c:/windows",
                "c:\\windows",
            )
            allowed_path_markers = (
                "nvidia",
                "cuda",
                "cudnn",
                "powershell",
                "system32",
                "wbem",
            )
            path_entries = [entry.strip() for entry in str(parent_env.get("PATH") or "").split(os.pathsep) if entry.strip()]
            filtered_entries: list[str] = []
            seen_entries: set[str] = set()
            for entry in path_entries:
                normalized = entry.replace("\\", "/").casefold()
                if any(normalized.startswith(root) for root in blocked_roots if root):
                    continue
                if normalized in seen_entries:
                    continue
                if normalized.startswith(allowed_path_prefixes) or any(marker in normalized for marker in allowed_path_markers):
                    filtered_entries.append(entry)
                    seen_entries.add(normalized)
            safe_env["PATH"] = os.pathsep.join(filtered_entries)
            child_env = safe_env
            self._log(
                "Local AI subprocess env prepared: "
                f"mode=frozen-clean path_entries={len(filtered_entries)} "
                f"pythonpath={'yes' if bool(worker_pythonpath) else 'no'}"
            )
        if worker_pythonpath:
            child_env["PYTHONPATH"] = worker_pythonpath + (os.pathsep + child_env["PYTHONPATH"] if child_env.get("PYTHONPATH") else "")
        else:
            child_env.pop("PYTHONPATH", None)
        return child_env

    def _local_ai_runtime_python_path(self, spec) -> Path:
        from app.mediamanager.ai_captioning.model_registry import default_python_for_runtime

        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        return Path(configured) if configured else default_python_for_runtime(self._local_ai_runtime_root(), spec)

    def _local_ai_status_payload_for_spec(self, spec) -> dict:
        python_path = self._local_ai_runtime_python_path(spec)
        requirements_path = self._local_ai_requirements_path(spec)
        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        model_files_installed = self._local_ai_model_files_installed(models_dir, spec.id)
        installed = python_path.is_file() and model_files_installed
        dev_fallback = False
        if not installed and model_files_installed and not bool(getattr(sys, "frozen", False)) and not configured:
            installed = True
            dev_fallback = True
        running = spec.settings_key in self._local_ai_model_installs
        profile_download_id = str(getattr(self, "_local_ai_profile_downloads", {}).get(spec.settings_key, "") or "").strip()
        profile_downloading = bool(profile_download_id)
        if running:
            state = "installing"
            message = f"Installing {spec.install_label}..."
        elif installed:
            state = "installed"
            message = "Installed."
        else:
            state = "not_installed"
            message = "Not installed. Install this model before using it."
        runtime_probe = self._local_ai_probe_runtime(spec) if installed else {}
        runtime_summary = self._local_ai_runtime_summary(runtime_probe)
        runtime_details_html = self._local_ai_runtime_details_html(runtime_probe)
        gemma_downloaded_profiles: list[str] = []
        selected_profile_id = ""
        if spec.settings_key == "gemma4":
            self._sync_selected_gemma_profile_settings(sync_qsettings=False)
            gemma_downloaded_profiles = self._local_ai_gemma_downloaded_profile_ids(models_dir)
            selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        return {
            "id": spec.id,
            "kind": spec.kind,
            "label": spec.label,
            "settings_key": spec.settings_key,
            "description": spec.description,
            "estimated_size": spec.estimated_size,
            "state": state,
            "installed": installed,
            "running": running,
            "dev_fallback": dev_fallback,
            "model_files_installed": model_files_installed,
            "model_files_cached": model_files_installed,
            "message": message,
            "runtime_python": str(python_path),
            "runtime_dir": str(Path(python_path).parent.parent),
            "location": str(Path(python_path).parent.parent),
            "requirements_file": str(requirements_path),
            "python_bootstrap": str(self._local_ai_python_bootstrap_exe()),
            "runtime_probe": runtime_probe,
            "runtime_summary": runtime_summary,
            "runtime_details_html": runtime_details_html,
            "gemma_downloaded_profiles": gemma_downloaded_profiles,
            "gemma_selected_profile_id": selected_profile_id,
            "gemma_profile_downloading": profile_downloading,
            "gemma_profile_downloading_id": profile_download_id,
        }

    def _local_ai_model_cache_targets(self, models_dir: Path, spec) -> list[Path]:
        targets = [Path(models_dir) / spec.id]
        if spec.id == "internlm/internlm-xcomposer2-vl-1_8b":
            targets.append(Path(models_dir) / "openai" / "clip-vit-large-patch14-336")
        if spec.id == "google/gemma-4-E2B-it":
            targets.append(Path(models_dir) / "gemma_gguf")
            targets.append(Path(models_dir) / "gemma4_runtime")
        return targets

    def _local_ai_gemma_downloaded_profile_ids(self, models_dir: Path) -> list[str]:
        from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_is_installed, gemma_profile_options

        downloaded: list[str] = []
        for profile in gemma_profile_options():
            try:
                if gemma_profile_is_installed(models_dir, profile):
                    downloaded.append(profile.id)
            except Exception:
                continue
        return downloaded

    def _local_ai_model_files_installed(self, models_dir: Path, model_id: str) -> bool:
        from app.mediamanager.ai_captioning.model_registry import CAPTION_MODEL_ID, GEMMA4_MODEL_ID, TAG_MODEL_ID
        from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id, gemma_profile_is_installed

        local_dir = Path(models_dir) / model_id
        if model_id == TAG_MODEL_ID:
            return (local_dir / "model.onnx").is_file() and (local_dir / "selected_tags.csv").is_file()
        if model_id == CAPTION_MODEL_ID:
            clip_dir = Path(models_dir) / "openai" / "clip-vit-large-patch14-336"
            return (local_dir / "config.json").is_file() and any(local_dir.glob("*.safetensors")) and (clip_dir / "config.json").is_file()
        if model_id == GEMMA4_MODEL_ID:
            profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""))
            if profile and gemma_profile_is_installed(models_dir, profile):
                return True
            if (local_dir / "config.json").is_file() and any(local_dir.glob("*.safetensors")):
                return True
            hf_home = Path(models_dir) / "gemma4_runtime" / "hf_home"
            return any((snapshot / "config.json").is_file() and any(snapshot.glob("*.safetensors")) for snapshot in hf_home.glob("hub/models--google--gemma-4-E2B-it/snapshots/*"))
        return (local_dir / "config.json").is_file()

    @staticmethod
    def _verify_python_can_create_venvs(command: list[str]) -> str:
        result = subprocess.run(
            [*command, "-c", "import venv, sys; print(sys.executable)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(str(result.stderr or result.stdout or "Python cannot create virtual environments.").strip())
        return str(result.stdout.strip() or command[0])

    def _local_ai_bundled_python_installer(self) -> Path | None:
        source_root = self._local_ai_worker_source_root()
        candidates = [
            source_root / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME,
            source_root / "_internal" / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME,
            Path(sys.executable).resolve().parent / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME if bool(getattr(sys, "frozen", False)) else Path(),
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _file_sha512_base64(path: Path) -> str:
        digest = hashlib.sha512()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return base64.b64encode(digest.digest()).decode("ascii")

    def _verify_local_ai_python_package(self, path: Path) -> None:
        actual = self._file_sha512_base64(path)
        if actual != LOCAL_AI_PYTHON_PACKAGE_SHA512:
            raise RuntimeError("Python bootstrap package did not match the expected checksum.")

    def _download_local_ai_python_package(self, emit_status) -> Path:
        download_dir = self._local_ai_bootstrap_download_dir()
        download_dir.mkdir(parents=True, exist_ok=True)
        package_path = download_dir / LOCAL_AI_PYTHON_PACKAGE_NAME
        if package_path.is_file():
            self._verify_local_ai_python_package(package_path)
            return package_path
        temp_path = package_path.with_suffix(".download")
        if temp_path.exists():
            temp_path.unlink()
        request = urllib.request.Request(
            LOCAL_AI_PYTHON_PACKAGE_URL,
            headers={"User-Agent": f"MediaLens/{__version__}"},
        )
        emit_status(f"Downloading Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")
        with urllib.request.urlopen(request, timeout=45) as response:
            total = int(response.headers.get("Content-Length") or 0)
            received = 0
            last_emit = 0.0
            with open(temp_path, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    handle.write(chunk)
                    received += len(chunk)
                    if time.monotonic() - last_emit >= 1.0:
                        last_emit = time.monotonic()
                        if total:
                            percent = int(round((received / total) * 100))
                            emit_status(f"Downloading Python bootstrap: {percent}% ({received // (1024 * 1024)} MB / {total // (1024 * 1024)} MB)")
                        else:
                            emit_status(f"Downloading Python bootstrap: {received // (1024 * 1024)} MB")
        self._verify_local_ai_python_package(temp_path)
        if package_path.exists():
            package_path.unlink()
        temp_path.replace(package_path)
        return package_path

    def _extract_local_ai_python_package(self, package_path: Path, emit_status) -> None:
        self._verify_local_ai_python_package(package_path)
        target_dir = self._local_ai_python_bootstrap_root()
        temp_dir = target_dir.with_name(f"{target_dir.name}.extracting")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if target_dir.exists() and not self._local_ai_python_bootstrap_exe().is_file():
            shutil.rmtree(target_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        emit_status(f"Extracting Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")
        try:
            with zipfile.ZipFile(package_path, "r") as archive:
                for member in archive.infolist():
                    name = member.filename.replace("\\", "/")
                    if not name.startswith("tools/") or name.endswith("/"):
                        continue
                    relative = Path(*name.split("/")[1:])
                    if not relative.parts:
                        continue
                    target = temp_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, open(target, "wb") as dest:
                        shutil.copyfileobj(source, dest)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            temp_dir.replace(target_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _ensure_local_ai_python_bootstrap(self, emit_status) -> str:
        bootstrap_python = self._local_ai_python_bootstrap_exe()
        if bootstrap_python.is_file():
            try:
                return self._verify_python_can_create_venvs([str(bootstrap_python)])
            except Exception:
                pass
        if os.name != "nt":
            return self._find_local_ai_bootstrap_python()

        package_path = self._local_ai_bundled_python_installer()
        if package_path is None:
            package_path = self._download_local_ai_python_package(emit_status)
        else:
            self._verify_local_ai_python_package(package_path)
            emit_status(f"Using bundled Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")

        self._extract_local_ai_python_package(package_path, emit_status)
        if not bootstrap_python.is_file():
            raise RuntimeError("Python bootstrap install finished, but python.exe was not found.")
        emit_status(f"Python {LOCAL_AI_PYTHON_VERSION} bootstrap is ready.")
        return self._verify_python_can_create_venvs([str(bootstrap_python)])

    def _find_local_ai_bootstrap_python(self) -> str:
        candidates: list[list[str]] = []
        if not bool(getattr(sys, "frozen", False)) and Path(sys.executable).is_file():
            candidates.append([sys.executable])
        if os.name == "nt":
            candidates.extend([["py", "-3.12"], ["py", "-3"], ["python"]])
        else:
            candidates.extend([["python3"], ["python"]])
        for command in candidates:
            try:
                return self._verify_python_can_create_venvs(command)
            except Exception:
                continue
        return ""

    def _local_ai_detect_nvidia_vram(self) -> dict[str, object]:
        result: dict[str, object] = {
            "available": False,
            "gpu_name": "",
            "driver_version": "",
            "total_vram_gb": 0.0,
            "free_vram_gb": 0.0,
            "reason": "",
        }
        if os.name != "nt":
            result["reason"] = "NVIDIA VRAM detection is implemented for Windows only."
            return result
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            result["reason"] = str(exc) or exc.__class__.__name__
            return result
        if completed.returncode != 0:
            result["reason"] = str(completed.stderr or completed.stdout or "nvidia-smi failed").strip()
            return result
        first_line = next((line.strip() for line in str(completed.stdout or "").splitlines() if line.strip()), "")
        if not first_line:
            result["reason"] = "nvidia-smi returned no GPU rows."
            return result
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) < 4:
            result["reason"] = f"Unexpected nvidia-smi output: {first_line}"
            return result
        try:
            total_gb = round(float(parts[2]) / 1024.0, 2)
            free_gb = round(float(parts[3]) / 1024.0, 2)
        except Exception as exc:
            result["reason"] = f"Could not parse VRAM values: {exc}"
            return result
        result.update(
            {
                "available": True,
                "gpu_name": parts[0],
                "driver_version": parts[1],
                "total_vram_gb": total_gb,
                "free_vram_gb": free_gb,
            }
        )
        return result

    @staticmethod
    def _download_file(url: str, destination: Path, emit_status, should_cancel=None) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_suffix(destination.suffix + ".download")
        if temp_path.exists():
            temp_path.unlink()
        request = urllib.request.Request(
            str(url),
            headers={"User-Agent": f"MediaLens/{__version__}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                total = int(response.headers.get("Content-Length") or 0)
                received = 0
                last_emit = 0.0
                with open(temp_path, "wb") as handle:
                    while True:
                        if callable(should_cancel) and should_cancel():
                            raise RuntimeError("Download canceled.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        received += len(chunk)
                        if time.monotonic() - last_emit >= 1.0:
                            last_emit = time.monotonic()
                            if total:
                                emit_status(
                                    f"Downloading {destination.name}: {int(round((received / total) * 100))}% "
                                    f"({received // (1024 * 1024)} MB / {total // (1024 * 1024)} MB)"
                                )
                            else:
                                emit_status(f"Downloading {destination.name}: {received // (1024 * 1024)} MB")
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise
        if destination.exists():
            destination.unlink()
        temp_path.replace(destination)
        return destination

    def _local_ai_gemma_llama_dir(self, runtime_dir: Path) -> Path:
        return Path(runtime_dir) / "llama.cpp"

    def _local_ai_gemma_llama_server_path(self, runtime_dir: Path) -> Path:
        return self._local_ai_gemma_llama_dir(runtime_dir) / "llama-server.exe"

    @staticmethod
    def _extract_zip_into(archive_path: Path, target_dir: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(target_dir)

    def _ensure_gemma_llama_cpp_runtime(self, runtime_dir: Path, emit_status) -> Path:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            LLAMA_CPP_WINDOWS_CUDA12_BIN_URL,
            LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP,
            LLAMA_CPP_WINDOWS_CUDA12_URL,
            LLAMA_CPP_WINDOWS_CUDA12_ZIP,
        )

        llama_dir = self._local_ai_gemma_llama_dir(runtime_dir)
        server_path = self._local_ai_gemma_llama_server_path(runtime_dir)
        if server_path.is_file():
            return server_path
        llama_dir.mkdir(parents=True, exist_ok=True)
        bin_archive_path = llama_dir / LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP
        archive_path = llama_dir / LLAMA_CPP_WINDOWS_CUDA12_ZIP
        emit_status("Downloading llama.cpp CUDA binaries...")
        self._download_file(LLAMA_CPP_WINDOWS_CUDA12_BIN_URL, bin_archive_path, emit_status)
        emit_status("Downloading llama.cpp CUDA runtime libraries...")
        self._download_file(LLAMA_CPP_WINDOWS_CUDA12_URL, archive_path, emit_status)
        temp_dir = llama_dir.with_name(f"{llama_dir.name}.extracting")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        emit_status("Extracting llama.cpp CUDA files...")
        try:
            self._extract_zip_into(bin_archive_path, temp_dir)
            self._extract_zip_into(archive_path, temp_dir)
            server_candidates = list(temp_dir.rglob("llama-server.exe"))
            if not server_candidates:
                raise RuntimeError("llama.cpp archives were extracted, but llama-server.exe was not found in the release contents.")
            extracted_root = server_candidates[0].parent
            if llama_dir.exists():
                shutil.rmtree(llama_dir, ignore_errors=True)
            extracted_root.replace(llama_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        if not server_path.is_file():
            raise RuntimeError("llama.cpp runtime install completed, but llama-server.exe was not found.")
        return server_path

    def _choose_gemma_gguf_profile(self):
        from app.mediamanager.ai_captioning.gemma_gguf import choose_best_gemma_profile, gemma_profile_by_id

        vram = self._local_ai_detect_nvidia_vram()
        selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        selected_profile = gemma_profile_by_id(selected_profile_id) if selected_profile_id else None
        if selected_profile is not None:
            return selected_profile, vram
        return choose_best_gemma_profile(vram.get("total_vram_gb"), vram.get("free_vram_gb")), vram

    def _ensure_gemma_gguf_profile_downloaded(self, models_dir: Path, profile, emit_status) -> tuple[Path, Path]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            gemma_profile_install_dir,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        install_dir = gemma_profile_install_dir(models_dir, profile)
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        install_dir.mkdir(parents=True, exist_ok=True)
        if not model_path.is_file():
            emit_status(f"Downloading {profile.label} model weights...")
            self._download_file(profile.model_url, model_path, emit_status)
        if not mmproj_path.is_file():
            emit_status(f"Downloading {profile.label} vision projector...")
            self._download_file(profile.mmproj_url, mmproj_path, emit_status)
        return model_path, mmproj_path

    def _download_gemma_gguf_profile_concurrent(self, models_dir: Path, profile, emit_install_status, payload: dict) -> tuple[Path, Path]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            gemma_profile_install_dir,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        install_dir = gemma_profile_install_dir(models_dir, profile)
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        install_dir.mkdir(parents=True, exist_ok=True)
        errors: list[Exception] = []
        lock = threading.Lock()
        download_messages: dict[str, str] = {}

        def emit_download_status(kind: str, message: str) -> None:
            with lock:
                download_messages[kind] = str(message or "").strip()
                payload.update(
                    {
                        "running": True,
                        "download_message": "\n".join(text for text in download_messages.values() if text),
                        "download_messages": dict(download_messages),
                        "gemma_profile_downloading": True,
                        "gemma_profile_downloading_id": profile.id,
                    }
                )
                self.localAiModelInstallStatus.emit("gemma4", dict(payload))

        cancel_check = lambda: bool(getattr(self, "_local_ai_profile_download_cancel", {}).get("gemma4"))

        def download_one(kind: str, url: str, destination: Path) -> None:
            try:
                self._download_file(url, destination, lambda message: emit_download_status(kind, message), cancel_check)
            except Exception as exc:
                errors.append(exc)
            finally:
                with lock:
                    download_messages.pop(kind, None)
                    payload.update(
                        {
                            "download_message": "\n".join(text for text in download_messages.values() if text),
                            "download_messages": dict(download_messages),
                            "gemma_profile_downloading": bool(download_messages),
                            "gemma_profile_downloading_id": profile.id if download_messages else "",
                        }
                    )
                    self.localAiModelInstallStatus.emit("gemma4", dict(payload))

        workers: list[threading.Thread] = []
        if not model_path.is_file():
            workers.append(threading.Thread(target=download_one, args=("model", profile.model_url, model_path), daemon=True, name=f"gemma-model-{profile.id}"))
        if not mmproj_path.is_file():
            workers.append(threading.Thread(target=download_one, args=("mmproj", profile.mmproj_url, mmproj_path), daemon=True, name=f"gemma-mmproj-{profile.id}"))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        if errors:
            raise errors[0]
        with lock:
            payload["download_message"] = ""
            payload["download_messages"] = {}
            payload["gemma_profile_downloading"] = False
            payload["gemma_profile_downloading_id"] = ""
            self.localAiModelInstallStatus.emit("gemma4", dict(payload))
        return model_path, mmproj_path

    def _configure_gemma_gguf_settings(self, profile, runtime_dir: Path, models_dir: Path, vram_info: dict[str, object]) -> dict[str, str | int]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        server_path = self._local_ai_gemma_llama_server_path(runtime_dir)
        ctx_size = int(profile.recommended_ctx)
        self.settings.setValue("ai_caption/gemma_backend", GEMMA_GGUF_BACKEND_ID)
        self.settings.setValue("ai_caption/gemma_profile_id", profile.id)
        self.settings.setValue("ai_caption/gemma_profile_label", profile.label)
        self.settings.setValue("ai_caption/gemma_model_path", str(model_path))
        self.settings.setValue("ai_caption/gemma_mmproj_path", str(mmproj_path))
        self.settings.setValue("ai_caption/gemma_llama_server", str(server_path))
        self.settings.setValue("ai_caption/gemma_ctx_size", ctx_size)
        self.settings.setValue("ai_caption/gemma_gpu_layers", 999)
        self.settings.setValue("ai_caption/gemma_detected_total_vram_gb", float(vram_info.get("total_vram_gb") or 0.0))
        self.settings.setValue("ai_caption/gemma_detected_free_vram_gb", float(vram_info.get("free_vram_gb") or 0.0))
        self.settings.sync()
        return {
            "backend": GEMMA_GGUF_BACKEND_ID,
            "profile_id": profile.id,
            "profile_label": profile.label,
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
            "server_path": str(server_path),
            "ctx_size": ctx_size,
        }

    def _sync_selected_gemma_profile_settings(self, *, sync_qsettings: bool = True) -> dict[str, str] | None:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        if not selected_profile_id:
            return None
        profile = gemma_profile_by_id(selected_profile_id)
        if profile is None:
            return None
        models_dir = Path(
            str(
                self.settings.value(
                    "ai_caption/models_dir",
                    self._local_ai_models_dir_default(),
                    type=str,
                )
                or self._local_ai_models_dir_default()
            )
        )
        if not gemma_profile_is_installed(models_dir, profile):
            return None
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        self.settings.setValue("ai_caption/gemma_backend", GEMMA_GGUF_BACKEND_ID)
        self.settings.setValue("ai_caption/gemma_profile_id", profile.id)
        self.settings.setValue("ai_caption/gemma_profile_label", profile.label)
        self.settings.setValue("ai_caption/gemma_profile_quantization", profile.quantization)
        self.settings.setValue("ai_caption/gemma_model_path", str(model_path))
        self.settings.setValue("ai_caption/gemma_mmproj_path", str(mmproj_path))
        if sync_qsettings:
            self.settings.sync()
        return {
            "profile_id": profile.id,
            "profile_label": profile.label,
            "profile_quantization": profile.quantization,
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
        }

    def _local_ai_gemma_probe(self, spec) -> dict:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_install_dir,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        python_path = self._local_ai_runtime_python_path(spec)
        requested_device = str(self.settings.value("ai_caption/device", "gpu", type=str) or "gpu").strip().lower() or "gpu"
        backend = str(self.settings.value("ai_caption/gemma_backend", "", type=str) or "").strip().lower()
        server_path = Path(str(self.settings.value("ai_caption/gemma_llama_server", "", type=str) or "").strip())
        configured_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""))
        selected_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or ""))
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        profile = configured_profile
        model_path = Path(str(self.settings.value("ai_caption/gemma_model_path", "", type=str) or "").strip())
        mmproj_path = Path(str(self.settings.value("ai_caption/gemma_mmproj_path", "", type=str) or "").strip())
        if selected_profile and gemma_profile_is_installed(models_dir, selected_profile):
            profile = selected_profile
            model_path = gemma_profile_model_path(models_dir, selected_profile)
            mmproj_path = gemma_profile_mmproj_path(models_dir, selected_profile)
        ctx_size = int(self.settings.value("ai_caption/gemma_ctx_size", 2048, type=int) or 2048)
        vram = self._local_ai_detect_nvidia_vram()
        selected_device = "cpu"
        reason = ""
        if backend != GEMMA_GGUF_BACKEND_ID:
            reason = "Gemma is configured to use the legacy Transformers runtime."
        elif requested_device != "gpu":
            reason = "GPU was not requested."
        elif not server_path.is_file():
            reason = "llama.cpp CUDA runtime is missing."
        elif not model_path.is_file() or not mmproj_path.is_file():
            reason = "Gemma GGUF model files are missing."
        elif not bool(vram.get("available")):
            reason = str(vram.get("reason") or "NVIDIA GPU was not detected.")
        else:
            selected_device = "gpu"
        return {
            "backend": "gguf",
            "ok": backend == GEMMA_GGUF_BACKEND_ID and python_path.is_file(),
            "requested_device": requested_device,
            "selected_device": selected_device,
            "python_executable": str(python_path),
            "profile_id": profile.id if profile else str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""),
            "profile_label": profile.label if profile else str(self.settings.value("ai_caption/gemma_profile_label", "", type=str) or ""),
            "quantization": profile.quantization if profile else "",
            "effective_params_label": profile.effective_params_label if profile else "",
            "approx_model_gb": float(profile.approx_model_gb) if profile else 0.0,
            "approx_total_gb": float(profile.approx_total_gb) if profile else 0.0,
            "ctx_size": ctx_size,
            "llama_server": str(server_path),
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
            "detected_total_vram_gb": float(vram.get("total_vram_gb") or 0.0),
            "detected_free_vram_gb": float(vram.get("free_vram_gb") or 0.0),
            "nvidia_smi": {
                "available": bool(vram.get("available")),
                "gpus": (
                    [
                        {
                            "name": str(vram.get("gpu_name") or "").strip(),
                            "driver_version": str(vram.get("driver_version") or "").strip(),
                        }
                    ]
                    if str(vram.get("gpu_name") or "").strip()
                    else []
                ),
            },
            "reason": reason,
        }

    def _local_ai_runtime_backend(self, spec) -> str:
        if str(getattr(spec, "settings_key", "") or "") == "wd_swinv2":
            return "onnx"
        if str(getattr(spec, "settings_key", "") or "") == "gemma4":
            from app.mediamanager.ai_captioning.gemma_gguf import GEMMA_GGUF_BACKEND_ID

            backend = str(self.settings.value("ai_caption/gemma_backend", "", type=str) or "").strip().lower()
            if backend == GEMMA_GGUF_BACKEND_ID:
                return "gguf"
        return "torch"

    def _local_ai_runtime_probe_command(self, spec, python_path: str | Path, requested_device: str, gpu_index: int) -> tuple[list[str], Path, dict[str, str]]:
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(
            python_path,
            "app.mediamanager.ai_captioning.runtime_probe",
        )
        command = [
            *launcher,
            "--backend",
            self._local_ai_runtime_backend(spec),
            "--requested-device",
            str(requested_device or "gpu"),
            "--gpu-index",
            str(max(0, int(gpu_index or 0))),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        return command, worker_cwd, child_env

    def _local_ai_run_command_stream(self, command: list[str], cwd: Path, message: str, emit_status, env: dict[str, str] | None = None) -> tuple[int, str]:
        payload_message = str(message or "").strip()
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        assert process.stdout is not None
        last_emit = 0.0
        last_line = payload_message
        for line in process.stdout:
            clean = " ".join(str(line or "").split()).strip()
            if clean:
                last_line = clean[-240:]
            if time.monotonic() - last_emit >= 1.0:
                last_emit = time.monotonic()
                emit_status(last_line)
        return process.wait(), last_line

    def _local_ai_run_command_capture(self, command: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 25) -> tuple[int, str, str]:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        return completed.returncode, str(completed.stdout or ""), str(completed.stderr or "")

    def _local_ai_probe_runtime(self, spec, force: bool = False) -> dict:
        cache_key = str(getattr(spec, "settings_key", "") or "")
        now = time.monotonic()
        cached = self._local_ai_runtime_status_cache.get(cache_key)
        if not force and cached and (now - cached[0]) < LOCAL_AI_STATUS_CACHE_TTL_SECONDS:
            cached_payload = dict(cached[1])
            if cache_key != "gemma4":
                return cached_payload
            selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
            if str(cached_payload.get("profile_id") or "").strip() == selected_profile_id:
                return cached_payload

        backend = self._local_ai_runtime_backend(spec)
        if backend == "gguf":
            payload = self._local_ai_gemma_probe(spec)
            self._local_ai_runtime_status_cache[cache_key] = (now, dict(payload))
            return dict(payload)

        python_path = self._local_ai_runtime_python_path(spec)
        if not python_path.is_file():
            payload = {"ok": False, "reason": "Runtime Python was not found.", "selected_device": "cpu"}
            self._local_ai_runtime_status_cache[cache_key] = (now, payload)
            return dict(payload)

        ai_settings = self._local_ai_caption_settings()
        requested_device = str(ai_settings.device or "gpu")
        gpu_index = int(ai_settings.gpu_index or 0)
        command, worker_cwd, child_env = self._local_ai_runtime_probe_command(spec, python_path, requested_device, gpu_index)
        try:
            returncode, stdout, stderr = self._local_ai_run_command_capture(command, worker_cwd, env=child_env, timeout=30)
        except Exception as exc:
            payload = {"ok": False, "reason": f"Runtime probe failed: {exc}", "selected_device": "cpu"}
            self._local_ai_runtime_status_cache[cache_key] = (now, payload)
            return dict(payload)

        combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
        payload = None
        for line in reversed([line.strip() for line in combined.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            payload = {
                "ok": False,
                "reason": f"Runtime probe exited without JSON ({self._local_ai_exit_code_text(returncode)}).",
                "selected_device": "cpu",
            }
        if returncode != 0 and not payload.get("reason"):
            payload["reason"] = f"Runtime probe failed ({self._local_ai_exit_code_text(returncode)})."
        self._local_ai_runtime_status_cache[cache_key] = (now, dict(payload))
        return dict(payload)

    @staticmethod
    def _local_ai_runtime_summary(probe: dict) -> str:
        if not probe:
            return "Runtime: unavailable"
        backend = str(probe.get("backend") or "").strip().lower()
        selected_device = str(probe.get("selected_device") or "cpu").strip().lower() or "cpu"
        status_label = "GPU" if selected_device.startswith("cuda") or selected_device == "gpu" else "CPU"
        if backend == "torch":
            gpu_names = [str(name).strip() for name in list(probe.get("gpu_names") or []) if str(name).strip()]
            parts = [
                f"Runtime: {status_label}",
                f"Torch {probe.get('torch_version') or '?'}",
            ]
            if probe.get("torch_cuda_version"):
                parts.append(f"CUDA {probe.get('torch_cuda_version')}")
            if selected_device.startswith("cuda") and gpu_names:
                selected_index = int(probe.get("selected_gpu_index") or 0)
                if 0 <= selected_index < len(gpu_names):
                    parts.append(gpu_names[selected_index])
                else:
                    parts.append(gpu_names[0])
            elif gpu_names:
                parts.append(f"Visible GPUs: {len(gpu_names)}")
            if probe.get("reason") and selected_device == "cpu":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        if backend == "onnx":
            active_provider = str(probe.get("active_provider") or "CPUExecutionProvider")
            parts = [
                f"Runtime: {status_label}",
                f"ONNX Runtime {probe.get('onnxruntime_version') or '?'}",
                active_provider,
            ]
            if probe.get("reason") and status_label == "CPU":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        if backend == "gguf":
            parts = [
                f"Runtime: {status_label}",
                "llama.cpp GGUF",
            ]
            profile_label = str(probe.get("profile_label") or "").strip()
            quantization = str(probe.get("quantization") or "").strip()
            if profile_label:
                parts.append(profile_label)
            if quantization:
                parts.append(quantization)
            total_vram = float(probe.get("detected_total_vram_gb") or 0.0)
            if total_vram > 0:
                parts.append(f"VRAM {total_vram:.1f} GB")
            if probe.get("reason") and status_label == "CPU":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        reason = str(probe.get("reason") or "").strip()
        return f"Runtime: {'unavailable' if not probe.get('ok') else status_label}{f' | {reason}' if reason else ''}"

    @staticmethod
    def _local_ai_runtime_details_html(probe: dict) -> str:
        if not probe:
            return ""
        lines: list[str] = []
        backend = str(probe.get("backend") or "").strip().lower()
        selected_device = str(probe.get("selected_device") or "cpu").strip() or "cpu"
        requested_device = str(probe.get("requested_device") or "").strip()
        if requested_device:
            lines.append(f"<b>Device:</b> requested {html.escape(requested_device.upper())}, using {html.escape(selected_device.upper())}")
        if probe.get("python_version"):
            lines.append(f"<b>Python:</b> {html.escape(str(probe.get('python_version')))}")
        if backend == "torch":
            if probe.get("torch_version"):
                lines.append(f"<b>Torch:</b> {html.escape(str(probe.get('torch_version')))}")
            if probe.get("torch_cuda_version"):
                lines.append(f"<b>CUDA:</b> {html.escape(str(probe.get('torch_cuda_version')))}")
            gpu_names = [str(name).strip() for name in list(probe.get("gpu_names") or []) if str(name).strip()]
            if gpu_names:
                lines.append(f"<b>GPUs:</b> {html.escape(', '.join(gpu_names[:3]))}")
        elif backend == "onnx":
            if probe.get("onnxruntime_version"):
                lines.append(f"<b>ONNX Runtime:</b> {html.escape(str(probe.get('onnxruntime_version')))}")
            providers = [str(name).strip() for name in list(probe.get("available_providers") or []) if str(name).strip()]
            if providers:
                lines.append(f"<b>Providers:</b> {html.escape(', '.join(providers[:4]))}")
        elif backend == "gguf":
            profile_label = str(probe.get("profile_label") or "").strip()
            if profile_label:
                lines.append(f"<b>Profile:</b> {html.escape(profile_label)}")
            quantization = str(probe.get("quantization") or "").strip()
            if quantization:
                lines.append(f"<b>Quantization:</b> {html.escape(quantization)}")
            effective_params = str(probe.get("effective_params_label") or "").strip()
            if effective_params:
                lines.append(f"<b>Model:</b> {html.escape(effective_params)}")
            approx_total_gb = float(probe.get("approx_total_gb") or 0.0)
            if approx_total_gb > 0:
                lines.append(f"<b>Approx Size:</b> {html.escape(f'{approx_total_gb:.2f} GB incl. mmproj')}")
            ctx_size = int(probe.get("ctx_size") or 0)
            if ctx_size > 0:
                lines.append(f"<b>Context:</b> {html.escape(str(ctx_size))} tokens")
            total_vram = float(probe.get("detected_total_vram_gb") or 0.0)
            free_vram = float(probe.get("detected_free_vram_gb") or 0.0)
            if total_vram > 0:
                if free_vram > 0:
                    lines.append(f"<b>VRAM:</b> {html.escape(f'{total_vram:.2f} GB total, {free_vram:.2f} GB free at install/probe time')}")
                else:
                    lines.append(f"<b>VRAM:</b> {html.escape(f'{total_vram:.2f} GB total')}")
        nvidia_smi = dict(probe.get("nvidia_smi") or {})
        smi_gpus = [dict(item or {}) for item in list(nvidia_smi.get("gpus") or [])]
        if smi_gpus:
            first_gpu = smi_gpus[0]
            gpu_name = str(first_gpu.get("name") or "").strip()
            driver_version = str(first_gpu.get("driver_version") or "").strip()
            driver_text = f"{gpu_name} (driver {driver_version})" if gpu_name and driver_version else gpu_name or driver_version
            if driver_text:
                lines.append(f"<b>NVIDIA:</b> {html.escape(driver_text)}")
        reason = str(probe.get("reason") or "").strip()
        if reason:
            lines.append(f"<b>Note:</b> {html.escape(reason)}")
        return "<br>".join(line for line in lines if line)

    @staticmethod
    def _local_ai_probe_requests_gpu(ai_settings) -> bool:
        return str(getattr(ai_settings, "device", "") or "").strip().lower() == "gpu"

    @staticmethod
    def _local_ai_probe_is_gpu_ready(probe: dict) -> bool:
        selected_device = str(probe.get("selected_device") or "").strip().lower()
        active_provider = str(probe.get("active_provider") or "").strip()
        return selected_device.startswith("cuda") or selected_device == "gpu" or active_provider in {"CUDAExecutionProvider", "DmlExecutionProvider"}

    def _local_ai_preload_model(self, spec, python_path: Path, settings_payload: dict, message: str, payload: dict) -> None:
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(python_path, spec.worker_module)
        command = [
            *launcher,
            "--operation",
            "preload",
            "--source",
            str(Path(__file__).resolve()),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        process = subprocess.Popen(
            command,
            cwd=str(worker_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        assert process.stdout is not None
        last_emit = 0.0
        last_line = message
        for line in process.stdout:
            clean = " ".join(str(line or "").split()).strip()
            if clean:
                last_line = clean[-240:]
            if time.monotonic() - last_emit >= 1.0:
                last_emit = time.monotonic()
                payload.update({"state": "installing", "running": True, "message": last_line})
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")

    def _install_gemma_gguf_model(self, spec, payload: dict, emit_install_status) -> None:
        python_path = self._local_ai_runtime_python_path(spec)
        runtime_dir = Path(python_path).parent.parent
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        profile, vram_info = self._choose_gemma_gguf_profile()
        emit_install_status(
            f"Selected {profile.label} for {float(vram_info.get('total_vram_gb') or 0.0):.1f} GB VRAM "
            f"({float(vram_info.get('free_vram_gb') or 0.0):.1f} GB free)."
        )
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        download_error: list[Exception] = []
        download_done = threading.Event()

        def download_worker() -> None:
            try:
                self._download_gemma_gguf_profile_concurrent(models_dir, profile, emit_install_status, payload)
            except Exception as exc:
                download_error.append(exc)
            finally:
                download_done.set()

        threading.Thread(target=download_worker, daemon=True, name=f"gemma-download-{profile.id}").start()
        bootstrap_python = self._ensure_local_ai_python_bootstrap(emit_install_status)
        if not bootstrap_python:
            raise RuntimeError(
                "MediaLens could not prepare the Python bootstrap needed to create the Gemma runtime. "
                "Check your internet connection, then try again."
            )
        if not python_path.is_file():
            message = f"Creating {spec.install_label} runtime..."
            payload.update({"state": "installing", "running": True, "message": message})
            self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
            returncode, last_line = self._local_ai_run_command_stream(
                [bootstrap_python, "-m", "venv", str(runtime_dir)],
                self._local_ai_worker_source_root(),
                message,
                emit_install_status,
            )
            if returncode != 0:
                raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")
        self.settings.setValue("ai_caption/runtime_python/gemma4", str(python_path))
        self.settings.setValue("ai_caption/gemma_python", str(python_path))
        self._ensure_gemma_llama_cpp_runtime(runtime_dir, emit_install_status)
        emit_install_status("Waiting for model downloads to finish...")
        download_done.wait()
        if download_error:
            raise download_error[0]
        configured = self._configure_gemma_gguf_settings(profile, runtime_dir, models_dir, vram_info)
        message = f"Validating {configured['profile_label']} runtime..."
        payload.update({"state": "installing", "running": True, "message": message})
        self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
        self._local_ai_preload_model(spec, python_path, self._local_ai_default_settings_payload_for_spec(spec), message, payload)

    def _local_ai_gpu_repair_commands(self, spec, python_path: Path) -> list[tuple[list[str], str]]:
        if os.name != "nt":
            return []
        backend = self._local_ai_runtime_backend(spec)
        if backend == "torch":
            return [
                (
                    [
                        str(python_path),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "--force-reinstall",
                        "--no-cache-dir",
                        "--index-url",
                        LOCAL_AI_TORCH_INDEX_URL_CU124,
                        f"torch=={LOCAL_AI_TORCH_VERSION_CU124}",
                        f"torchvision=={LOCAL_AI_TORCHVISION_VERSION_CU124}",
                    ],
                    "Repairing CUDA Torch packages...",
                ),
            ]
        if backend == "onnx":
            return [
                (
                    [
                        str(python_path),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "--force-reinstall",
                        "--no-cache-dir",
                        f"onnxruntime-gpu=={LOCAL_AI_ORT_GPU_VERSION}",
                    ],
                    "Repairing ONNX Runtime GPU package...",
                ),
            ]
        return []

    def _ensure_local_ai_gpu_runtime(self, spec, python_path: Path, emit_install_status) -> dict:
        ai_settings = self._local_ai_caption_settings()
        probe = self._local_ai_probe_runtime(spec, force=True)
        if not self._local_ai_probe_requests_gpu(ai_settings):
            return probe
        if self._local_ai_probe_is_gpu_ready(probe):
            return probe
        for command, message in self._local_ai_gpu_repair_commands(spec, python_path):
            emit_install_status(message)
            returncode, last_line = self._local_ai_run_command_stream(
                command,
                self._local_ai_worker_source_root(),
                message,
                emit_install_status,
            )
            if returncode != 0:
                self._log(
                    f"Local AI GPU repair failed for {spec.install_label} ({self._local_ai_exit_code_text(returncode)}): {last_line}"
                )
                continue
            probe = self._local_ai_probe_runtime(spec, force=True)
            if self._local_ai_probe_is_gpu_ready(probe):
                return probe
        return probe

    @Slot(str, str, result="QVariantMap")
    def get_local_ai_model_status(self, model_id: str, kind: str) -> dict:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            return self._local_ai_status_payload_for_spec(model_spec(str(model_id), str(kind)))
        except Exception as exc:
            return {"state": "error", "installed": False, "running": False, "message": str(exc) or "Could not read model status."}

    @Slot(str, str, result=bool)
    def install_local_ai_model(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return False

        self._local_ai_model_installs.add(spec.settings_key)
        self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))

        def work() -> None:
            payload = self._local_ai_status_payload_for_spec(spec)

            def emit_install_status(message: str) -> None:
                payload.update({"state": "installing", "running": True, "message": str(message or "").strip()})
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))

            try:
                if spec.settings_key == "gemma4" and os.name == "nt":
                    self._install_gemma_gguf_model(spec, payload, emit_install_status)
                    self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
                    probe = self._local_ai_probe_runtime(spec, force=True)
                    payload = self._local_ai_status_payload_for_spec(spec)
                    final_message = f"{spec.install_label} is installed."
                    if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                        final_message = f"{final_message} GPU was requested but this runtime is still using CPU."
                    payload.update({"state": "installed", "installed": True, "running": False, "message": final_message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, payload)
                    return
                requirements_path = self._local_ai_requirements_path(spec)
                if not requirements_path.is_file():
                    raise RuntimeError(f"Install instructions for {spec.install_label} were not found.")
                python_path = self._local_ai_runtime_python_path(spec)
                runtime_dir = Path(python_path).parent.parent
                runtime_dir.parent.mkdir(parents=True, exist_ok=True)
                bootstrap_python = self._ensure_local_ai_python_bootstrap(emit_install_status)
                if not bootstrap_python:
                    raise RuntimeError(
                        "MediaLens could not prepare the Python bootstrap needed to create the model runtime. "
                        "Check your internet connection, then try again."
                    )
                commands = [
                    ([bootstrap_python, "-m", "venv", str(runtime_dir)], f"Creating {spec.install_label} runtime..."),
                    ([str(python_path), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], "Updating package installer..."),
                    ([str(python_path), "-m", "pip", "install", "-r", str(requirements_path)], f"Installing {spec.install_label} support..."),
                ]
                for command, message in commands:
                    payload.update({"state": "installing", "running": True, "message": message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                    returncode, last_line = self._local_ai_run_command_stream(
                        command,
                        self._local_ai_worker_source_root(),
                        message,
                        emit_install_status,
                    )
                    if returncode != 0:
                        raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")
                probe = self._ensure_local_ai_gpu_runtime(spec, python_path, emit_install_status)
                if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                    emit_install_status(
                        self._local_ai_runtime_summary(probe)
                    )
                models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
                if self._local_ai_model_files_installed(models_dir, spec.id):
                    payload.update({"state": "installing", "running": True, "message": f"{spec.install_label} model files are already present."})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                else:
                    message = f"Downloading {spec.install_label} model files..."
                    payload.update({"state": "installing", "running": True, "message": message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                    try:
                        self._local_ai_preload_model(spec, python_path, self._local_ai_default_settings_payload_for_spec(spec), message, payload)
                    except Exception as exc:
                        if self._local_ai_model_files_installed(models_dir, spec.id):
                            self._log(f"Local AI model preload failed for {spec.install_label}, but required model files are present: {exc}")
                        else:
                            raise
                self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
                probe = self._local_ai_probe_runtime(spec, force=True)
                payload = self._local_ai_status_payload_for_spec(spec)
                final_message = f"{spec.install_label} is installed."
                if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                    final_message = f"{final_message} GPU was requested but this runtime is still using CPU."
                payload.update({"state": "installed", "installed": True, "running": False, "message": final_message})
                self.localAiModelInstallStatus.emit(spec.settings_key, payload)
            except Exception as exc:
                payload.update({"state": "error", "installed": False, "running": False, "message": str(exc) or "Model installation failed."})
                self.localAiModelInstallStatus.emit(spec.settings_key, payload)
                self._log(f"Local AI model install failed for {spec.install_label}: {payload['message']}")
            finally:
                self._local_ai_model_installs.discard(spec.settings_key)

        threading.Thread(target=work, daemon=True, name=f"local-ai-install-{spec.settings_key}").start()
        return True

    @Slot(str, str, result=bool)
    def uninstall_local_ai_model(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "This model is currently installing."})
            return False

        try:
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            targets = [self._local_ai_runtime_python_path(spec).parent.parent]
            for target in targets:
                if target.exists():
                    shutil.rmtree(target)
            if spec.settings_key == "gemma4":
                for key in (
                    "ai_caption/runtime_python/gemma4",
                    "ai_caption/gemma_backend",
                    "ai_caption/gemma_profile_id",
                    "ai_caption/gemma_profile_label",
                    "ai_caption/gemma_model_path",
                    "ai_caption/gemma_mmproj_path",
                    "ai_caption/gemma_llama_server",
                    "ai_caption/gemma_ctx_size",
                    "ai_caption/gemma_gpu_layers",
                    "ai_caption/gemma_detected_total_vram_gb",
                    "ai_caption/gemma_detected_free_vram_gb",
                    "ai_caption/gemma_python",
                ):
                    self.settings.remove(key)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": str(exc) or "Uninstall failed."})
            self._log(f"Local AI model uninstall failed for {spec.install_label}: {exc}")
            return False

    @Slot(str, str, result=bool)
    def delete_local_ai_model_files(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "This model is currently installing."})
            return False
        try:
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            for target in self._local_ai_model_cache_targets(models_dir, spec):
                if target.exists():
                    shutil.rmtree(target)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": str(exc) or "Delete model files failed."})
            self._log(f"Local AI model file delete failed for {spec.install_label}: {exc}")
            return False

    @Slot(str, result=bool)
    def download_gemma_profile_files(self, profile_id: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id
            from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID, model_spec

            spec = model_spec(GEMMA4_MODEL_ID, "captioner")
            profile = gemma_profile_by_id(str(profile_id or "").strip())
            if profile is None:
                raise RuntimeError("Unknown Gemma profile.")
        except Exception as exc:
            self.localAiModelInstallStatus.emit("gemma4", {"state": "error", "message": str(exc) or "Unknown Gemma profile."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "Gemma is currently busy."})
            return False

        downloads = getattr(self, "_local_ai_profile_downloads", None)
        if downloads is None:
            downloads = {}
            self._local_ai_profile_downloads = downloads
        cancel_flags = getattr(self, "_local_ai_profile_download_cancel", None)
        if cancel_flags is None:
            cancel_flags = {}
            self._local_ai_profile_download_cancel = cancel_flags
        downloads[spec.settings_key] = profile.id
        cancel_flags[spec.settings_key] = False
        payload = self._local_ai_status_payload_for_spec(spec)
        payload.update(
            {
                "running": True,
                "message": f"Downloading {profile.label}...",
                "gemma_profile_downloading": True,
                "gemma_profile_downloading_id": profile.id,
                "download_messages": {},
                "download_message": "",
            }
        )
        self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))

        def work() -> None:
            try:
                models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
                self._download_gemma_gguf_profile_concurrent(models_dir, profile, None, payload)
                refreshed = self._local_ai_status_payload_for_spec(spec)
                refreshed.update(
                    {
                        "message": f"{profile.label} is downloaded.",
                        "state": refreshed.get("state") or "not_installed",
                        "running": False,
                        "gemma_profile_downloading": False,
                        "gemma_profile_downloading_id": "",
                        "download_messages": {},
                        "download_message": "",
                    }
                )
                self.localAiModelInstallStatus.emit(spec.settings_key, refreshed)
            except Exception as exc:
                payload.update(
                    {
                        "state": "error",
                        "running": False,
                        "message": str(exc) or "Gemma profile download failed.",
                        "gemma_profile_downloading": False,
                        "gemma_profile_downloading_id": "",
                    }
                )
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                self._log(f"Gemma profile download failed for {profile.label}: {payload['message']}")
            finally:
                getattr(self, "_local_ai_profile_downloads", {}).pop(spec.settings_key, None)
                getattr(self, "_local_ai_profile_download_cancel", {}).pop(spec.settings_key, None)

        threading.Thread(target=work, daemon=True, name=f"gemma-profile-download-{profile.id}").start()
        return True

    @Slot(result=bool)
    def cancel_gemma_profile_download(self) -> bool:
        downloads = getattr(self, "_local_ai_profile_downloads", {})
        if not downloads.get("gemma4"):
            return False
        cancel_flags = getattr(self, "_local_ai_profile_download_cancel", None)
        if cancel_flags is None:
            cancel_flags = {}
            self._local_ai_profile_download_cancel = cancel_flags
        cancel_flags["gemma4"] = True
        return True

    @Slot(str, result=bool)
    def delete_gemma_profile_files(self, profile_id: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id, gemma_profile_install_dir
            from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID, model_spec

            spec = model_spec(GEMMA4_MODEL_ID, "captioner")
            profile = gemma_profile_by_id(str(profile_id or "").strip())
            if profile is None:
                raise RuntimeError("Unknown Gemma profile.")
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            target = gemma_profile_install_dir(models_dir, profile)
            if target.exists():
                shutil.rmtree(target)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit("gemma4", {"state": "error", "message": str(exc) or "Delete Gemma profile failed."})
            self._log(f"Gemma profile delete failed for {profile_id}: {exc}")
            return False

    def _local_ai_caption_settings(self):
        from app.mediamanager.ai_captioning.local_captioning import (
            CAPTION_MODEL_ID,
            DEFAULT_BAD_WORDS,
            DEFAULT_CAPTION_PROMPT,
            DEFAULT_CAPTION_START,
            TAG_MODEL_ID,
            LocalAiSettings,
        )
        from app.mediamanager.ai_captioning.model_registry import model_ids_for_kind

        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        tag_model_id = str(self.settings.value("ai_caption/tag_model_id", TAG_MODEL_ID, type=str) or TAG_MODEL_ID)
        caption_model_id = str(self.settings.value("ai_caption/caption_model_id", CAPTION_MODEL_ID, type=str) or CAPTION_MODEL_ID)
        if tag_model_id not in model_ids_for_kind("tagger"):
            self._log(f"Unsupported local AI tag model '{tag_model_id}' was reset to '{TAG_MODEL_ID}'.")
            tag_model_id = TAG_MODEL_ID
            self.settings.setValue("ai_caption/tag_model_id", TAG_MODEL_ID)
        if caption_model_id not in model_ids_for_kind("captioner"):
            self._log(f"Unsupported local AI description model '{caption_model_id}' was reset to '{CAPTION_MODEL_ID}'.")
            caption_model_id = CAPTION_MODEL_ID
            self.settings.setValue("ai_caption/caption_model_id", CAPTION_MODEL_ID)
        return LocalAiSettings(
            models_dir=models_dir,
            tag_model_id=tag_model_id,
            caption_model_id=caption_model_id,
            tag_min_probability=float(self.settings.value("ai_caption/tag_min_probability", 0.35, type=float) or 0.35),
            tag_max_tags=int(self.settings.value("ai_caption/tag_max_tags", 75, type=int) or 75),
            tags_to_exclude=str(self.settings.value("ai_caption/tags_to_exclude", "", type=str) or ""),
            tag_prompt=str(self.settings.value("ai_caption/tag_prompt", "", type=str) or ""),
            tag_write_mode=str(self.settings.value("ai_caption/tag_write_mode", "union", type=str) or "union"),
            caption_prompt=str(self.settings.value("ai_caption/caption_prompt", DEFAULT_CAPTION_PROMPT, type=str) or DEFAULT_CAPTION_PROMPT),
            caption_start=str(self.settings.value("ai_caption/caption_start", DEFAULT_CAPTION_START, type=str) or DEFAULT_CAPTION_START),
            description_write_mode=str(self.settings.value("ai_caption/description_write_mode", "overwrite", type=str) or "overwrite"),
            device=str(self.settings.value("ai_caption/device", "gpu", type=str) or "gpu"),
            gpu_index=int(self.settings.value("ai_caption/gpu_index", 0, type=int) or 0),
            load_in_4_bit=bool(self.settings.value("ai_caption/load_in_4_bit", False, type=bool)),
            bad_words=str(self.settings.value("ai_caption/bad_words", DEFAULT_BAD_WORDS, type=str) or DEFAULT_BAD_WORDS),
            forced_words=str(self.settings.value("ai_caption/forced_words", "", type=str) or ""),
            min_new_tokens=int(self.settings.value("ai_caption/min_new_tokens", 1, type=int) or 1),
            max_new_tokens=int(self.settings.value("ai_caption/max_new_tokens", 200, type=int) or 200),
            num_beams=int(self.settings.value("ai_caption/num_beams", 1, type=int) or 1),
            length_penalty=float(self.settings.value("ai_caption/length_penalty", 1.0, type=float) or 1.0),
            do_sample=bool(self.settings.value("ai_caption/do_sample", False, type=bool)),
            temperature=float(self.settings.value("ai_caption/temperature", 1.0, type=float) or 1.0),
            top_k=int(self.settings.value("ai_caption/top_k", 50, type=int) or 50),
            top_p=float(self.settings.value("ai_caption/top_p", 1.0, type=float) or 1.0),
            repetition_penalty=float(self.settings.value("ai_caption/repetition_penalty", 1.0, type=float) or 1.0),
            no_repeat_ngram_size=int(self.settings.value("ai_caption/no_repeat_ngram_size", 3, type=int) or 3),
        )

    def _local_ai_service_for_settings(self, ai_settings):
        from app.mediamanager.ai_captioning.local_captioning import LocalAiCaptioningService

        key = json.dumps(
            {
                "models_dir": str(ai_settings.models_dir),
                "tag_model_id": ai_settings.tag_model_id,
                "caption_model_id": ai_settings.caption_model_id,
                "device": ai_settings.device,
                "gpu_index": ai_settings.gpu_index,
                "load_in_4_bit": ai_settings.load_in_4_bit,
            },
            sort_keys=True,
        )
        if self._local_ai_service is None or self._local_ai_service_key != key:
            self._local_ai_service = LocalAiCaptioningService(ai_settings, self._log)
            self._local_ai_service_key = key
        else:
            self._local_ai_service.settings = ai_settings
        return self._local_ai_service

    def _try_start_local_ai(self) -> bool:
        with self._local_ai_lock:
            if self._local_ai_running:
                return False
            self._local_ai_running = True
            self._local_ai_shutting_down = False
            self._local_ai_cancel.clear()
            return True

    def _finish_local_ai(self) -> None:
        with self._local_ai_lock:
            self._local_ai_running = False
            self._local_ai_cancel.clear()

    def _emit_local_ai_signal(self, signal, *args) -> bool:
        if self._local_ai_shutting_down:
            return False
        try:
            signal.emit(*args)
            return True
        except RuntimeError as exc:
            if "already deleted" not in str(exc):
                self._log(f"Local AI signal emit failed: {exc}")
            return False
        except Exception as exc:
            self._log(f"Local AI signal emit failed: {exc}")
            return False

    def _safe_emit(self, signal, *args) -> bool:
        """Emit a Bridge signal from a worker thread, swallowing the race where
        Qt has already deleted the Bridge's C++ half during app shutdown."""
        if self._shutting_down:
            return False
        try:
            signal.emit(*args)
            return True
        except RuntimeError:
            # "Internal C++ object (Bridge) already deleted" â€” Qt tore down
            # before this daemon thread finished. Nothing to do.
            return False
        except Exception:
            return False

    def _emit_local_ai_status(self, message: str) -> None:
        self._emit_local_ai_signal(self.localAiCaptioningStatus, str(message or "").strip())

    def _local_ai_settings_payload(self, ai_settings) -> dict:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        self._sync_selected_gemma_profile_settings(sync_qsettings=False)
        payload = {
            "models_dir": str(ai_settings.models_dir),
            "tag_model_id": str(ai_settings.tag_model_id),
            "caption_model_id": str(ai_settings.caption_model_id),
            "tag_min_probability": float(ai_settings.tag_min_probability),
            "tag_max_tags": int(ai_settings.tag_max_tags),
            "tags_to_exclude": str(ai_settings.tags_to_exclude),
            "tag_prompt": str(ai_settings.tag_prompt),
            "tag_write_mode": str(ai_settings.tag_write_mode),
            "caption_prompt": str(ai_settings.caption_prompt),
            "caption_start": str(ai_settings.caption_start),
            "description_write_mode": str(ai_settings.description_write_mode),
            "device": str(ai_settings.device),
            "gpu_index": int(ai_settings.gpu_index),
            "load_in_4_bit": bool(ai_settings.load_in_4_bit),
            "bad_words": str(ai_settings.bad_words),
            "forced_words": str(ai_settings.forced_words),
            "min_new_tokens": int(ai_settings.min_new_tokens),
            "max_new_tokens": int(ai_settings.max_new_tokens),
            "num_beams": int(ai_settings.num_beams),
            "length_penalty": float(ai_settings.length_penalty),
            "do_sample": bool(ai_settings.do_sample),
            "temperature": float(ai_settings.temperature),
            "top_k": int(ai_settings.top_k),
            "top_p": float(ai_settings.top_p),
            "repetition_penalty": float(ai_settings.repetition_penalty),
            "no_repeat_ngram_size": int(ai_settings.no_repeat_ngram_size),
        }
        for key, default in (
            ("gemma_backend", ""),
            ("gemma_profile_id", ""),
            ("gemma_profile_label", ""),
            ("gemma_model_path", ""),
            ("gemma_mmproj_path", ""),
            ("gemma_llama_server", ""),
            ("gemma_ctx_size", 2048),
            ("gemma_gpu_layers", 999),
        ):
            settings_key = f"ai_caption/{key}"
            if isinstance(default, int):
                payload[key] = int(self.settings.value(settings_key, default, type=int) or default)
            else:
                payload[key] = str(self.settings.value(settings_key, default, type=str) or default)
        backend = str(payload.get("gemma_backend") or "").strip().lower()
        selected_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip())
        if backend == GEMMA_GGUF_BACKEND_ID and selected_profile and gemma_profile_is_installed(ai_settings.models_dir, selected_profile):
            payload["gemma_profile_id"] = selected_profile.id
            payload["gemma_profile_label"] = selected_profile.label
            payload["gemma_profile_quantization"] = selected_profile.quantization
            payload["gemma_model_path"] = str(gemma_profile_model_path(ai_settings.models_dir, selected_profile))
            payload["gemma_mmproj_path"] = str(gemma_profile_mmproj_path(ai_settings.models_dir, selected_profile))
        return payload

    def _local_ai_default_settings_payload_for_spec(self, spec) -> dict:
        payload = self._local_ai_settings_payload(self._local_ai_caption_settings())
        if spec.kind == "tagger":
            payload["tag_model_id"] = spec.id
        else:
            payload["caption_model_id"] = spec.id
        return payload

    def _local_ai_worker_command(self, operation: str, ai_settings) -> tuple[str, str]:
        from app.mediamanager.ai_captioning.model_registry import (
            current_python_matches_runtime,
            default_python_for_runtime,
            model_spec,
        )

        kind = "tagger" if operation == "tags" else "captioner"
        selected_model = ai_settings.tag_model_id if operation == "tags" else ai_settings.caption_model_id
        spec = model_spec(selected_model, kind)
        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        runtime_root = self._local_ai_runtime_root()
        default_python = default_python_for_runtime(runtime_root, spec)
        python_path = Path(configured) if configured else default_python
        if not python_path.is_file():
            if not bool(getattr(sys, "frozen", False)) and (current_python_matches_runtime(spec) or not configured):
                python_path = Path(sys.executable)
            else:
                raise RuntimeError(
                    f"{spec.install_label} is not installed yet. Install this local AI model before using it."
                )
        return str(python_path), spec.worker_module

    def _run_local_ai_worker_process(self, operation: str, source_path: Path, ai_settings, tags: list[str] | None = None) -> dict:
        timeout_seconds = int(self.settings.value("ai_caption/item_timeout_seconds", 900, type=int) or 900)
        timeout_seconds = max(30, timeout_seconds)
        operation_label = "description" if operation == "description" else "tags"
        python_exe, worker_module = self._local_ai_worker_command(operation, ai_settings)
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(python_exe, worker_module)
        settings_payload = self._local_ai_settings_payload(ai_settings)
        command = [
            *launcher,
            "--operation",
            operation,
            "--source",
            str(source_path),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        if tags is not None:
            command.extend(["--tags-json", json.dumps(tags, ensure_ascii=False)])
        if str(settings_payload.get("gemma_backend") or "").strip().lower() == "llama_cpp_gguf":
            self._log(
                "Local AI Gemma launch: "
                f"profile={str(settings_payload.get('gemma_profile_id') or '').strip()} "
                f"quant={str(settings_payload.get('gemma_profile_quantization') or '').strip()} "
                f"model={Path(str(settings_payload.get('gemma_model_path') or '')).name} "
                f"mmproj={Path(str(settings_payload.get('gemma_mmproj_path') or '')).name} "
                f"ctx={int(settings_payload.get('gemma_ctx_size') or 0)} "
                f"ngl={int(settings_payload.get('gemma_gpu_layers') or 0)} "
                f"source={source_path.name}"
            )
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        popen_kwargs = dict(
            cwd=str(worker_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
        if _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS:
            popen_kwargs.update(_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS)
        process = subprocess.Popen(command, **popen_kwargs)
        with self._local_ai_lock:
            self._local_ai_processes.add(process)
        started = time.monotonic()
        last_status = 0.0
        try:
            while process.poll() is None:
                if self._local_ai_cancel.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
                        try:
                            process.wait(timeout=5)
                        except Exception:
                            pass
                    raise RuntimeError("Local AI scan was canceled.")
                elapsed = time.monotonic() - started
                if elapsed - last_status >= 5.0:
                    last_status = elapsed
                    self._emit_local_ai_status(
                        f"Generating {operation_label}: still working ({int(elapsed)}s elapsed, timeout {timeout_seconds}s)"
                    )
                if time.monotonic() - started > timeout_seconds:
                    process.kill()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        pass
                    raise TimeoutError(f"Local AI timed out after {timeout_seconds} seconds on {source_path.name}.")
                time.sleep(0.25)
            stdout, stderr = process.communicate(timeout=5)
        finally:
            with self._local_ai_lock:
                self._local_ai_processes.discard(process)
        if stderr.strip():
            self._log(f"Local AI worker stderr for {source_path}: {stderr.strip()[-2000:]}")
        payload = None
        for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            raise RuntimeError(self._local_ai_worker_failure_message(process.returncode, stdout, stderr))
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or "Local AI worker failed."))
        return payload

    @staticmethod
    def _local_ai_exit_code_text(returncode: int | None) -> str:
        if returncode is None:
            return "no exit code"
        if os.name == "nt":
            return f"exit code {returncode} / 0x{returncode & 0xFFFFFFFF:08X}"
        return f"exit code {returncode}"

    @staticmethod
    def _local_ai_worker_failure_message(returncode: int | None, stdout: str, stderr: str) -> str:
        combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
        lines = []
        for raw_line in combined.replace("\r", "\n").splitlines():
            line = " ".join(str(raw_line or "").split()).strip()
            if not line:
                continue
            lowered = line.lower()
            if "loading weights:" in lowered or "it/s]" in lowered:
                continue
            if "you are using a model of type" in lowered:
                continue
            if "set max length" in lowered:
                continue
            if line.startswith("{") and line.endswith("}"):
                continue
            lines.append(line)
        if lines:
            return lines[-1][-500:]
        if returncode:
            return f"Local AI worker exited without a result ({Bridge._local_ai_exit_code_text(returncode)})."
        return "Local AI worker exited without a result."

    def cancel_local_ai_captioning(self) -> None:
        self._local_ai_shutting_down = True
        self._local_ai_cancel.set()
        with self._local_ai_lock:
            processes = list(self._local_ai_processes)
        for process in processes:
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

    @Slot(result=list)
    def list_local_ai_models(self) -> list:
        from app.mediamanager.ai_captioning.model_registry import available_models

        return available_models()

    @Slot(list, result=bool)
    def run_local_ai_tags_descriptions(self, paths: list) -> bool:
        return self.run_local_ai_tags(paths)

    @Slot(list, result=bool)
    def run_local_ai_tags(self, paths: list) -> bool:
        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if not clean_paths or not self._try_start_local_ai():
            return False

        def work() -> None:
            from app.mediamanager.ai_captioning.local_captioning import apply_tags_to_database

            completed = 0
            error = ""
            item_errors: list[str] = []
            self._emit_local_ai_signal(self.localAiCaptioningStarted, len(clean_paths))
            try:
                ai_settings = self._local_ai_caption_settings()
                ai_settings.models_dir.mkdir(parents=True, exist_ok=True)
                for index, raw_path in enumerate(clean_paths, start=1):
                    if self._local_ai_cancel.is_set():
                        error = "Local AI scan was canceled."
                        break
                    self._emit_local_ai_signal(self.localAiCaptioningProgress, raw_path, index, len(clean_paths))
                    try:
                        media = self._ensure_media_record_for_tag_write(raw_path)
                        if not media:
                            raise FileNotFoundError("Selected media record could not be created.")
                        source_path = self._local_ai_source_path(Path(raw_path))
                        result = self._run_local_ai_worker_process("tags", source_path, ai_settings)
                        tags = [str(tag) for tag in (result.get("tags") or []) if str(tag).strip()]
                        if not tags:
                            raise RuntimeError("Local AI generated no tags.")
                        apply_tags_to_database(self.conn, raw_path, tags, ai_settings)
                        completed += 1
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, tags, "", "")
                    except Exception as item_exc:
                        item_error = str(item_exc) or "Local AI captioning failed."
                        item_errors.append(f"{Path(raw_path).name}: {item_error}")
                        self._log(f"Local AI tag generation failed for {raw_path}: {item_error}")
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], "", item_error)
                self._emit_local_ai_signal(self.galleryScopeChanged)
                if item_errors and completed <= 0:
                    error = item_errors[0]
            except Exception as exc:
                error = str(exc) or "Local AI tag generation failed."
                self._log(f"Local AI tag generation failed: {error}")
            finally:
                self._finish_local_ai()
                self._emit_local_ai_signal(self.localAiCaptioningFinished, completed, error)

        threading.Thread(target=work, daemon=True, name="local-ai-captioning").start()
        return True

    @Slot(list, result=bool)
    def run_local_ai_descriptions(self, paths: list) -> bool:
        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if not clean_paths or not self._try_start_local_ai():
            return False

        def work() -> None:
            from app.mediamanager.ai_captioning.local_captioning import apply_description_to_database
            from app.mediamanager.db.tags_repo import list_media_tags

            completed = 0
            error = ""
            item_errors: list[str] = []
            self._emit_local_ai_signal(self.localAiCaptioningStarted, len(clean_paths))
            try:
                ai_settings = self._local_ai_caption_settings()
                ai_settings.models_dir.mkdir(parents=True, exist_ok=True)
                for index, raw_path in enumerate(clean_paths, start=1):
                    if self._local_ai_cancel.is_set():
                        error = "Local AI scan was canceled."
                        break
                    self._emit_local_ai_signal(self.localAiCaptioningProgress, raw_path, index, len(clean_paths))
                    try:
                        media = self._ensure_media_record_for_tag_write(raw_path)
                        if not media:
                            raise FileNotFoundError("Selected media record could not be created.")
                        source_path = self._local_ai_source_path(Path(raw_path))
                        tags = list_media_tags(self.conn, int(media["id"]))
                        result = self._run_local_ai_worker_process("description", source_path, ai_settings, tags)
                        description = str(result.get("description") or "").strip()
                        if not str(description or "").strip():
                            raise RuntimeError("Local AI generated no description.")
                        apply_description_to_database(self.conn, raw_path, description, ai_settings)
                        completed += 1
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], description, "")
                    except Exception as item_exc:
                        item_error = str(item_exc) or "Local AI description generation failed."
                        item_errors.append(f"{Path(raw_path).name}: {item_error}")
                        self._log(f"Local AI description generation failed for {raw_path}: {item_error}")
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], "", item_error)
                self._emit_local_ai_signal(self.galleryScopeChanged)
                if item_errors and completed <= 0:
                    error = item_errors[0]
            except Exception as exc:
                error = str(exc) or "Local AI description generation failed."
                self._log(f"Local AI description generation failed: {error}")
            finally:
                self._finish_local_ai()
                self._emit_local_ai_signal(self.localAiCaptioningFinished, completed, error)

        threading.Thread(target=work, daemon=True, name="local-ai-description").start()
        return True

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
            self.mediaListed.emit(req, items or [])

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
            self.mediaCounted.emit(req, int(count or 0))

        threading.Thread(target=work, daemon=True).start()

    @Slot(str, list, str, str)
    def count_media_files_async(self, request_id: str, folders: list, filter_type: str = "all", search_query: str = "") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            count = self.count_media_files(folder_list, ftype, query)
            self.mediaFileCounted.emit(req, int(count or 0))

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
