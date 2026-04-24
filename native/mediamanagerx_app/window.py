from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *
from native.mediamanagerx_app.bridge import *
from native.mediamanagerx_app.gallery import *

from native.mediamanagerx_app.window_menus import WindowMenuShortcutMixin

from native.mediamanagerx_app.window_layout_panels import WindowLayoutPanelsMixin

from native.mediamanagerx_app.window_navigation import WindowNavigationMixin

from native.mediamanagerx_app.window_sidebar_bulk import WindowSidebarBulkMixin

from native.mediamanagerx_app.window_preview_metadata import WindowPreviewMetadataMixin

from native.mediamanagerx_app.window_native_actions import WindowNativeActionsMixin

from native.mediamanagerx_app.window_app_lifecycle import WindowAppLifecycleMixin

class MainWindow(WindowAppLifecycleMixin, WindowNativeActionsMixin, WindowPreviewMetadataMixin, WindowSidebarBulkMixin, WindowNavigationMixin, WindowLayoutPanelsMixin, WindowMenuShortcutMixin, QMainWindow):
    _DEFAULT_LEFT_PANEL_WIDTH = 200
    _DEFAULT_CENTER_WIDTH = 700
    _DEFAULT_RIGHT_PANEL_WIDTH = 300
    _DEFAULT_BOTTOM_PANEL_HEIGHT = 220
    videoSidebarMetadataReady = Signal(str, dict)
    videoSidebarPosterReady = Signal(str, str)
    debugLogUploadFinished = Signal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MediaLens")
        self.resize(1200, 800)

        startup_settings = app_settings()
        startup_theme = str(startup_settings.value("ui/theme_mode", "dark", type=str) or "dark")
        startup_accent = str(startup_settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
        Theme.set_theme_mode(startup_theme)
        startup_bg = QColor(Theme.get_bg(QColor(startup_accent)))
        startup_fg = QColor(Theme.get_text_color())
        startup_palette = self.palette()
        startup_palette.setColor(QPalette.ColorRole.Window, startup_bg)
        startup_palette.setColor(QPalette.ColorRole.Base, startup_bg)
        startup_palette.setColor(QPalette.ColorRole.Button, startup_bg)
        startup_palette.setColor(QPalette.ColorRole.WindowText, startup_fg)
        self.setAutoFillBackground(True)
        self.setPalette(startup_palette)
        self.setStyleSheet(f"QMainWindow {{ background-color: {startup_bg.name()}; color: {startup_fg.name()}; }}")
        startup_placeholder = QWidget(self)
        startup_placeholder.setAutoFillBackground(True)
        startup_placeholder.setPalette(startup_palette)
        startup_placeholder.setStyleSheet(f"background-color: {startup_bg.name()};")
        self.setCentralWidget(startup_placeholder)

        # Set window icon
        icon_path = Path(__file__).with_name("web") / "MediaLens-Logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.bridge = Bridge(self)
        try:
            from native.mediamanagerx_app.recycle_bin import auto_purge_recycle_bin
            auto_purge_recycle_bin()
        except Exception:
            pass
        self.bridge.openVideoRequested.connect(self._open_video_overlay)
        self.bridge.openVideoInPlaceRequested.connect(self._open_video_inplace)
        self.bridge.updateVideoRectRequested.connect(self._update_video_inplace_rect)
        self.bridge.closeVideoRequested.connect(self._close_video_overlay)
        self.bridge.videoMutedChanged.connect(self._on_video_muted_changed)
        self.bridge.videoPausedChanged.connect(self._on_video_paused_changed)
        self.bridge.videoPreprocessingStatus.connect(self._on_video_preprocessing_status)
        self.debugLogUploadFinished.connect(self._on_debug_log_upload_finished)
        self.bridge.uiFlagChanged.connect(self._apply_ui_flag)
        self.bridge.metadataRequested.connect(self._schedule_show_metadata_for_path)
        self.videoSidebarMetadataReady.connect(self._on_video_sidebar_metadata_ready)
        self.videoSidebarPosterReady.connect(self._on_video_sidebar_poster_ready)
        self.bridge.loadFolderRequested.connect(self._on_load_folder_requested)
        self.bridge.startNativeDragRequested.connect(self._start_native_gallery_drag)
        self.bridge.navigateToFolderRequested.connect(self._on_navigate_to_folder_requested)
        self.bridge.navigateBackRequested.connect(self._navigate_back)
        self.bridge.navigateForwardRequested.connect(self._navigate_forward)
        self.bridge.navigateUpRequested.connect(self._navigate_up)
        self.bridge.refreshFolderRequested.connect(self._refresh_current_folder)
        self.bridge.openSettingsDialogRequested.connect(self.open_settings)
        self.bridge.accentColorChanged.connect(self._on_accent_changed)
        self.bridge.galleryScopeChanged.connect(self._refresh_tag_list_scope_counts)
        self.bridge.manualOcrFinished.connect(self._on_manual_ocr_finished)
        self.bridge.localAiCaptioningStarted.connect(self._on_local_ai_captioning_started)
        self.bridge.localAiCaptioningProgress.connect(self._on_local_ai_captioning_progress)
        self.bridge.localAiCaptioningStatus.connect(self._on_local_ai_captioning_status)
        self.bridge.localAiCaptioningItemFinished.connect(self._on_local_ai_captioning_item_finished)
        self.bridge.localAiCaptioningFinished.connect(self._on_local_ai_captioning_finished)
        self._current_accent = Theme.ACCENT_DEFAULT
        self._folder_history: list[str] = []
        self._folder_history_index: int = -1
        self._settings_dialog: SettingsDialog | None = None
        self._local_ai_setup_dialog: LocalAiSetupDialog | None = None
        self._suppress_tree_selection_history = False
        self._tree_root_path: str = ""
        self._pending_tree_sync_path: str = ""
        self._pending_tree_reroot: bool = False
        self._suspend_tree_auto_reveal: bool = False
        self._tree_sync_timer = QTimer(self)
        self._tree_sync_timer.setSingleShot(True)
        self._tree_sync_timer.timeout.connect(self._apply_pending_tree_sync)
        self._pending_metadata_paths: list[str] = []
        self._metadata_request_revision = 0
        self._metadata_applied_revision = 0
        self._metadata_request_timer = QTimer(self)
        self._metadata_request_timer.setSingleShot(True)
        self._metadata_request_timer.timeout.connect(self._apply_pending_metadata_request)
        self._pending_tag_list_refresh_mode = "rows"
        self._tag_list_refresh_revision = 0
        self._tag_list_refresh_timer = QTimer(self)
        self._tag_list_refresh_timer.setSingleShot(True)
        self._tag_list_refresh_timer.timeout.connect(self._apply_pending_tag_list_refresh)

        # Native Tooltip
        self.native_tooltip = NativeDragTooltip()
        self.bridge.updateTooltipRequested.connect(self._on_update_tooltip)
        self.bridge.hideTooltipRequested.connect(self.native_tooltip.hide)

        self._build_menu()
        self._build_layout()
        
        # Monitor top menu interactions to dismiss web context menu
        for m in (self.menuBar().findChildren(QMenu)):
             m.aboutToShow.connect(self._dismiss_web_menus)
             
        # Global listener to dismiss web menus when any native part of the app is clicked
        QApplication.instance().installEventFilter(self)

        # Update connections
        self.bridge.updateAvailable.connect(self._on_update_available)
        self.bridge.updateError.connect(self._on_update_error)

        self._setup_shortcuts()



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
