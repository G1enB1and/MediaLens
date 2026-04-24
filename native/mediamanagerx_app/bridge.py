from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

from native.mediamanagerx_app.bridge_media_tools import BridgeMediaToolsMixin
from native.mediamanagerx_app.bridge_navigation_collections import BridgeNavigationCollectionsMixin
from native.mediamanagerx_app.bridge_scanners_settings import BridgeScannersSettingsMixin
from native.mediamanagerx_app.bridge_compare_updates import BridgeCompareUpdatesMixin
from native.mediamanagerx_app.bridge_file_ops import BridgeFileOpsMixin
from native.mediamanagerx_app.bridge_video_metadata import BridgeVideoMetadataMixin
from native.mediamanagerx_app.bridge_local_ai import BridgeLocalAiMixin
from native.mediamanagerx_app.bridge_tags_metadata import BridgeTagsMetadataMixin
from native.mediamanagerx_app.bridge_media_listing_scan import BridgeMediaListingScanMixin

class Bridge(BridgeMediaListingScanMixin, BridgeTagsMetadataMixin, BridgeLocalAiMixin, BridgeVideoMetadataMixin, BridgeFileOpsMixin, BridgeCompareUpdatesMixin, BridgeScannersSettingsMixin, BridgeNavigationCollectionsMixin, BridgeMediaToolsMixin, QObject):
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



__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
