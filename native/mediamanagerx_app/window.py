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

class MainWindow(QMainWindow):
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

    def _setup_shortcuts(self) -> None:
        """Standard Windows-style keyboard shortcuts."""
        self.act_copy = QAction("Copy", self)
        self.act_copy.setShortcut("Ctrl+C")
        self.act_copy.triggered.connect(self._on_copy_shortcut)
        self.addAction(self.act_copy)

        self.act_cut = QAction("Cut", self)
        self.act_cut.setShortcut("Ctrl+X")
        self.act_cut.triggered.connect(self._on_cut_shortcut)
        self.addAction(self.act_cut)

        self.act_paste = QAction("Paste", self)
        self.act_paste.setShortcut("Ctrl+V")
        self.act_paste.triggered.connect(self._on_paste_shortcut)
        self.addAction(self.act_paste)

        self.act_delete = QAction("Delete", self)
        self.act_delete.setShortcut("Del")
        self.act_delete.triggered.connect(self._on_delete_shortcut)
        self.addAction(self.act_delete)

        self.act_shift_delete = QAction("Permanent Delete", self)
        self.act_shift_delete.setShortcut("Shift+Del")
        self.act_shift_delete.triggered.connect(self._on_shift_delete_shortcut)
        self.addAction(self.act_shift_delete)

        self.act_rename = QAction("Rename", self)
        self.act_rename.setShortcut("F2")
        self.act_rename.triggered.connect(self._on_rename_shortcut)
        self.addAction(self.act_rename)

        self.act_select_all = QAction("Select All", self)
        self.act_select_all.setShortcut("Ctrl+A")
        self.act_select_all.triggered.connect(self._on_select_all_shortcut)
        self.addAction(self.act_select_all)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        edit_menu = menubar.addMenu("&Edit")
        
        self.act_open_bulk_tag_editor = QAction("Bulk Tag Editor", self)
        self.act_open_bulk_tag_editor.triggered.connect(self._open_bulk_tag_editor_from_menu)
        edit_menu.addAction(self.act_open_bulk_tag_editor)
        
        edit_menu.addSeparator()

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_action)

        pick_action = QAction("Choose &Folderâ€¦", self)
        pick_action.triggered.connect(self.choose_folder)
        file_menu.addAction(pick_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")

        self.act_open_bulk_caption_editor = QAction("Bulk Captioning Editor", self)
        self.act_open_bulk_caption_editor.triggered.connect(self._open_bulk_caption_editor_from_menu)
        view_menu.addAction(self.act_open_bulk_caption_editor)
        view_menu.addSeparator()

        self.gallery_view_group = QActionGroup(self)
        self.gallery_view_group.setExclusive(True)
        self.gallery_view_actions: dict[str, QAction] = {}
        for mode, label in (
            ("grid_small", "Grid (Small)"),
            ("grid_medium", "Grid (Medium)"),
            ("grid_large", "Grid (Large)"),
            ("grid_xlarge", "Grid (Extra Large)"),
            ("list", "List"),
            ("details", "Details"),
            ("content", "Content"),
            ("duplicates", "Duplicates"),
            ("similar", "Duplicates and Similar"),
            ("similar_only", "Similar"),
            ("masonry", "Masonry"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, mode=mode: self._set_gallery_view_mode(mode))
            self.gallery_view_group.addAction(action)
            self.gallery_view_actions[mode] = action
            view_menu.addAction(action)
        self._sync_gallery_view_actions()

        view_menu.addSeparator()

        self.act_toggle_top_panel = QAction("Show Top Panel", self)
        self.act_toggle_top_panel.setCheckable(True)
        self.act_toggle_top_panel.setChecked(bool(self.bridge.settings.value("ui/show_top_panel", True, type=bool)))
        self.act_toggle_top_panel.triggered.connect(lambda checked=False: self._toggle_panel_setting("ui/show_top_panel"))
        view_menu.addAction(self.act_toggle_top_panel)

        self.act_toggle_left_panel = QAction("Show Left Panel", self)
        self.act_toggle_left_panel.setCheckable(True)
        self.act_toggle_left_panel.setChecked(bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool)))
        self.act_toggle_left_panel.triggered.connect(lambda checked=False: self._toggle_panel_setting("ui/show_left_panel"))
        view_menu.addAction(self.act_toggle_left_panel)

        self.act_toggle_bottom_panel = QAction("Show Bottom Panel", self)
        self.act_toggle_bottom_panel.setCheckable(True)
        self.act_toggle_bottom_panel.setChecked(bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool)))
        self.act_toggle_bottom_panel.triggered.connect(lambda checked=False: self._toggle_panel_setting("ui/show_bottom_panel"))
        view_menu.addAction(self.act_toggle_bottom_panel)

        self.act_toggle_right_panel = QAction("Show Right Panel", self)
        self.act_toggle_right_panel.setCheckable(True)
        self.act_toggle_right_panel.setChecked(bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)))
        self.act_toggle_right_panel.triggered.connect(lambda checked=False: self._toggle_panel_setting("ui/show_right_panel"))
        view_menu.addAction(self.act_toggle_right_panel)

        self.act_toggle_tag_list_panel = QAction("Show Tag List", self)
        self.act_toggle_tag_list_panel.setCheckable(True)
        self.act_toggle_tag_list_panel.triggered.connect(self._toggle_tag_list_panel_from_menu)
        view_menu.addAction(self.act_toggle_tag_list_panel)

        self.act_show_dismissed_progress_toasts = QAction("Show Hidden Progress Toasts", self)
        self.act_show_dismissed_progress_toasts.triggered.connect(self.bridge.reveal_progress_toasts)
        view_menu.addAction(self.act_show_dismissed_progress_toasts)

        view_menu.addSeparator()
        self.act_show_ai_models_status = QAction("Show AI Models and Status", self)
        self.act_show_ai_models_status.triggered.connect(lambda: self.open_local_ai_setup())
        view_menu.addAction(self.act_show_ai_models_status)

        view_menu.addSeparator()

        devtools_action = QAction("Toggle &DevTools", self)
        devtools_action.setShortcut("F12")
        devtools_action.triggered.connect(self.toggle_devtools)
        view_menu.addAction(devtools_action)

        help_menu = menubar.addMenu("&Help")
        
        whats_new_action = QAction("&What's New", self)
        whats_new_action.triggered.connect(self.show_whats_new)
        help_menu.addAction(whats_new_action)
        
        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

        tos_action = QAction("&Terms of Service", self)
        tos_action.triggered.connect(self.show_tos)
        help_menu.addAction(tos_action)
        
        help_menu.addSeparator()
        
        bug_action = QAction("&Report a Bug", self)
        bug_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/G1enB1and/MediaLens/issues"))
        help_menu.addAction(bug_action)
        
        website_action = QAction("&Project Website", self)
        website_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/G1enB1and/MediaLens"))
        help_menu.addAction(website_action)

        help_menu.addSeparator()

        diagnostics_action = QAction("Create &Debugging Log Bundle", self)
        diagnostics_action.triggered.connect(self.create_diagnostic_report)
        help_menu.addAction(diagnostics_action)

        submit_diagnostics_action = QAction("&Submit Debugging Logs...", self)
        submit_diagnostics_action.triggered.connect(self.submit_debugging_logs)
        help_menu.addAction(submit_diagnostics_action)

        crash_logs_action = QAction("Open &Debugging Logs Folder", self)
        crash_logs_action.triggered.connect(self.open_crash_report_folder)
        help_menu.addAction(crash_logs_action)

        help_menu.addSeparator()

        check_updates_action = QAction("Check for &Updates...", self)
        check_updates_action.triggered.connect(lambda: self.bridge.check_for_updates(manual=True))
        help_menu.addAction(check_updates_action)

        for m in (file_menu, edit_menu, view_menu, help_menu):
            m.aboutToShow.connect(self._dismiss_web_menus)

        self._build_menu_bar_controls()

    def _menu_bar_icon_path(self, base_name: str) -> str:
        suffix = "-black" if Theme.get_is_light() else ""
        return str(Path(__file__).with_name("web") / f"{base_name}{suffix}.png")

    def _menu_bar_settings_icon_path(self) -> str:
        icon_name = "settings-cog.svg" if Theme.get_is_light() else "settings-cog-white.svg"
        return str(Path(__file__).with_name("web") / "icons" / icon_name)

    def _build_menu_bar_controls(self) -> None:
        menubar = self.menuBar()
        if menubar is None:
            return

        container = QWidget(self)
        container.setObjectName("menuBarControls")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(6)

        self.menu_btn_toggle_left = QPushButton(container)
        self.menu_btn_toggle_left.setObjectName("menuBarIconButton")
        self.menu_btn_toggle_left.setToolTip("Toggle Left Sidebar")
        self.menu_btn_toggle_left.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn_toggle_left.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn_toggle_left.clicked.connect(lambda: self._toggle_panel_setting("ui/show_left_panel"))
        layout.addWidget(self.menu_btn_toggle_left)

        self.menu_btn_toggle_top = QPushButton(container)
        self.menu_btn_toggle_top.setObjectName("menuBarIconButton")
        self.menu_btn_toggle_top.setToolTip("Toggle Top Panel")
        self.menu_btn_toggle_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn_toggle_top.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn_toggle_top.clicked.connect(lambda: self._toggle_panel_setting("ui/show_top_panel"))
        layout.addWidget(self.menu_btn_toggle_top)

        self.menu_btn_toggle_bottom = QPushButton(container)
        self.menu_btn_toggle_bottom.setObjectName("menuBarIconButton")
        self.menu_btn_toggle_bottom.setToolTip("Toggle Bottom Panel")
        self.menu_btn_toggle_bottom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn_toggle_bottom.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn_toggle_bottom.clicked.connect(lambda: self._toggle_panel_setting("ui/show_bottom_panel"))
        layout.addWidget(self.menu_btn_toggle_bottom)

        self.menu_btn_toggle_right = QPushButton(container)
        self.menu_btn_toggle_right.setObjectName("menuBarIconButton")
        self.menu_btn_toggle_right.setToolTip("Toggle Right Sidebar")
        self.menu_btn_toggle_right.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn_toggle_right.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn_toggle_right.clicked.connect(lambda: self._toggle_panel_setting("ui/show_right_panel"))
        layout.addWidget(self.menu_btn_toggle_right)

        self.menu_btn_settings = QPushButton(container)
        self.menu_btn_settings.setObjectName("menuBarSettingsButton")
        self.menu_btn_settings.setToolTip("Settings")
        self.menu_btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.menu_btn_settings)

        menubar.setCornerWidget(container, Qt.Corner.TopRightCorner)
        self._sync_menu_bar_controls()

    def _set_menu_bar_button_icon(self, button: QPushButton | None, visible: bool, prefix: str) -> None:
        if button is None:
            return
        state = "opened" if visible else "closed"
        path = self._menu_bar_icon_path(f"{prefix}-{state}")
        if Path(path).exists():
            button.setIcon(QIcon(path))
            button.setText("")
        else:
            button.setIcon(QIcon())
            button.setText("*")
        button.setIconSize(QSize(18, 18))

    def _set_menu_bar_settings_icon(self, button: QPushButton | None) -> None:
        if button is None:
            return
        path = self._menu_bar_settings_icon_path()
        if Path(path).exists():
            button.setIcon(QIcon(path))
            button.setText("")
        else:
            button.setIcon(QIcon())
            button.setText("S")
        button.setIconSize(QSize(18, 18))

    def _sync_close_button_icons(self) -> None:
        icon_path = (Path(__file__).with_name("web") / "icons" / "close.svg").as_posix()
        icon = QIcon(icon_path)
        for button in (
            getattr(self, "tag_list_close_btn", None),
            getattr(self, "btn_close_preview", None),
            getattr(self, "bottom_panel_close_btn", None),
        ):
            if button is None:
                continue
            button.setText("")
            button.setIcon(icon)
            button.setIconSize(QSize(14, 14))

    def _sync_menu_bar_controls(self) -> None:
        try:
            self._set_menu_bar_button_icon(
                getattr(self, "menu_btn_toggle_left", None),
                bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool)),
                "left-sidebar",
            )
            self._set_menu_bar_button_icon(
                getattr(self, "menu_btn_toggle_top", None),
                bool(self.bridge.settings.value("ui/show_top_panel", True, type=bool)),
                "top",
            )
            self._set_menu_bar_button_icon(
                getattr(self, "menu_btn_toggle_bottom", None),
                bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool)),
                "bottom",
            )
            self._set_menu_bar_button_icon(
                getattr(self, "menu_btn_toggle_right", None),
                bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)),
                "right-sidebar",
            )
            self._set_menu_bar_settings_icon(getattr(self, "menu_btn_settings", None))
        except Exception:
            pass

    def _set_gallery_view_mode(self, mode: str) -> None:
        self.bridge.set_setting_str("gallery.view_mode", mode)
        if mode == "duplicates":
            self.bridge.set_setting_str("gallery.group_by", "duplicates")
        elif mode == "similar":
            self.bridge.set_setting_str("gallery.group_by", "similar")
        elif mode == "similar_only":
            self.bridge.set_setting_str("gallery.group_by", "similar_only")
        elif self.bridge._gallery_group_by() == "duplicates":
            self.bridge.set_setting_str("gallery.group_by", "none")
        elif self.bridge._gallery_group_by() in {"similar", "similar_only"}:
            self.bridge.set_setting_str("gallery.group_by", "none")
        self._sync_gallery_view_actions()

    def _sync_gallery_view_actions(self) -> None:
        mode = self.bridge._gallery_view_mode()
        for key, action in getattr(self, "gallery_view_actions", {}).items():
            action.setChecked(key == mode)

    def _get_focused_paths(self) -> list[str]:
        """Get selected paths from whichever view (Tree or Gallery) has focus."""
        if self.tree.hasFocus():
            idx = self.tree.currentIndex()
            if idx.isValid():
                source_idx = self.proxy_model.mapToSource(idx)
                return [self.fs_model.filePath(source_idx)]
        # Default to gallery selection
        return getattr(self, "_current_paths", [])

    def _is_input_focused(self) -> bool:
        """Check if focus is in a text input where shortcuts should be ignored."""
        f = QApplication.focusWidget()
        while f is not None:
            if isinstance(f, (QLineEdit, QTextEdit, QPlainTextEdit)):
                return True
            parent_widget = getattr(f, "parentWidget", None)
            f = parent_widget() if callable(parent_widget) else None
        return False

    def _focused_text_input(self):
        f = QApplication.focusWidget()
        while f is not None:
            if isinstance(f, (QLineEdit, QTextEdit, QPlainTextEdit)):
                return f
            parent_widget = getattr(f, "parentWidget", None)
            f = parent_widget() if callable(parent_widget) else None
        return None

    def _on_copy_shortcut(self) -> None:
        focused_input = self._focused_text_input()
        if focused_input is not None:
            try:
                focused_input.copy()
            except Exception:
                pass
            return
        paths = self._get_focused_paths()
        if paths: self.bridge.copy_to_clipboard(paths)

    def _on_cut_shortcut(self) -> None:
        if self._is_input_focused(): return
        paths = self._get_focused_paths()
        if paths: self.bridge.cut_to_clipboard(paths)

    def _on_paste_shortcut(self) -> None:
        if self._is_input_focused(): return
        # Logic to determine where to paste:
        # 1. If tree has focus and selection, paste INTO that folder.
        # 2. Otherwise, if gallery has a folder loaded, paste into that folder.
        target = ""
        if self.tree.hasFocus():
            idx = self.tree.currentIndex()
            if idx.isValid():
                source_idx = self.proxy_model.mapToSource(idx)
                path = self.fs_model.filePath(source_idx)
                if Path(path).is_dir(): target = path
        
        if not target and hasattr(self, "_current_paths") and self._current_paths:
            # If a file is selected, use its parent folder
            target = str(Path(self._current_paths[0]).parent)
        elif not target and self.bridge._selected_folders:
            target = self.bridge._selected_folders[0]
            
        if target:
            self.bridge.paste_into_folder_async(target)

    def _on_delete_shortcut(self) -> None:
        if self._is_input_focused(): return
        paths = self._get_focused_paths()
        if not paths: return
        
        use_recycle = bool(self.bridge.settings.value("gallery/use_recycle_bin", True, type=bool))
        use_retention = bool(self.bridge.settings.value("gallery/use_medialens_retention", False, type=bool))
        if use_recycle or use_retention:
            for p in paths:
                self.bridge.delete_path(p)
        else:
            count = len(paths)
            msg = f"Are you sure you want to permanently delete {count} items?" if count > 1 else f"Are you sure you want to permanently delete '{Path(paths[0]).name}'?"
            ret = _run_themed_question_dialog(self, "Confirm Permanent Delete", msg)
            if ret == QMessageBox.StandardButton.Yes:
                for p in paths:
                    self.bridge.delete_path_permanent(p)

    def _on_shift_delete_shortcut(self) -> None:
        if self._is_input_focused(): return
        paths = self._get_focused_paths()
        if not paths: return
        
        count = len(paths)
        msg = f"Are you sure you want to permanently delete {count} items?" if count > 1 else f"Are you sure you want to permanently delete '{Path(paths[0]).name}'?"
        ret = _run_themed_question_dialog(self, "Confirm Permanent Delete", msg)
        if ret == QMessageBox.StandardButton.Yes:
            for p in paths:
                self.bridge.delete_path_permanent(p)

    def _on_rename_shortcut(self) -> None:
        if self._is_input_focused(): return
        if self.tree.hasFocus():
            idx = self.tree.currentIndex()
            if idx.isValid():
                self._on_tree_context_menu_rename(idx)
        else:
            # Tell web gallery to rename its selected item (usually just the first if multiple)
            self.web.page().runJavaScript("if(window.triggerRename) window.triggerRename();")

    def _on_select_all_shortcut(self) -> None:
        if self._is_input_focused(): return
        if self.tree.hasFocus():
            # Standard tree Select All? usually doesn't exist but we could select all under parent
            pass
        else:
            self.web.page().runJavaScript("if(window.selectAll) window.selectAll();")

    def _build_layout(self) -> None:
        try:
            accent_val = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
        except Exception:
            accent_val = Theme.ACCENT_DEFAULT
        
        self._current_accent = accent_val
        accent_q = QColor(accent_val)

        splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter

        # Left: folder tree (native)
        self.left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(0)

        # Choose initial root based on settings.
        default_root = None
        if self.bridge._restore_last_enabled():
            lf = self.bridge._last_folder()
            if lf:
                p = Path(lf)
                if p.exists() and p.is_dir():
                    default_root = p

        if default_root is None:
            sf = self.bridge._start_folder_setting()
            if sf:
                p = Path(sf)
                if p.exists() and p.is_dir():
                    default_root = p

        if default_root is None:
            p = Path("C:/Pictures")
            if p.exists():
                default_root = p

        if default_root is None:
            default_root = Path.home()

        self.bridge._log(f"Tree: Initializing with root={default_root}")
        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath(str(default_root))

        # Use a proxy model to show the root folder itself at the top.
        self.proxy_model = RootFilterProxyModel(self.bridge, self)
        self.proxy_model.setSourceModel(self.fs_model)
        self.proxy_model.setRootPath(str(default_root))

        self.tree = FolderTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setProperty("showDecorationSelected", False)
        self.tree.setItemDelegate(AccentSelectionTreeDelegate(self.bridge, self.tree))
        
        # Set the tree root to the PARENT of our desired root folder
        # root_parent needs to be loaded by fs_model for visibility.
        root_parent = default_root.parent
        self.bridge._log(f"Tree: Setting root index to parent={root_parent}")
        parent_idx = self.fs_model.setRootPath(str(root_parent))
        
        proxy_parent_idx = self.proxy_model.mapFromSource(parent_idx)
        self.bridge._log(f"Tree: Proxy parent index valid={proxy_parent_idx.isValid()}")
        self.tree.setRootIndex(proxy_parent_idx)

        # Expand the root folder by default
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(str(default_root)))
        self.bridge._log(f"Tree: Root index valid={root_idx.isValid()}")
        if root_idx.isValid():
            self.tree.expand(root_idx)
        else:
            # If still invalid, it might be because the model hasn't loaded the parent yet.
            # We'll rely on directoryLoaded to fix this.
            self.bridge._log(f"Tree: Root index (late load pending) for {default_root}")
        
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setExpandsOnDoubleClick(True)
        from PySide6.QtWidgets import QAbstractItemView
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Hide columns: keep only name (indices are on the proxy model)
        for col in range(1, self.proxy_model.columnCount()):
            self.tree.hideColumn(col)

        self.tree.selectionModel().selectionChanged.connect(self._on_tree_selection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Connect to directoryLoaded so we can refresh icons/expansion once ready
        self.fs_model.directoryLoaded.connect(self._on_directory_loaded)

        self.left_sections_splitter = CustomSplitter(Qt.Orientation.Vertical)
        self.left_sections_splitter.setObjectName("leftSectionsSplitter")
        self.left_sections_splitter.setChildrenCollapsible(False)
        self.left_sections_splitter.setHandleWidth(5)

        pinned_section = QWidget(self.left_sections_splitter)
        pinned_layout = QVBoxLayout(pinned_section)
        pinned_layout.setContentsMargins(0, 0, 0, 0)
        pinned_layout.setSpacing(6)
        self.pinned_header = QLabel("Pinned Folders")
        pinned_layout.addWidget(self.pinned_header)

        self.pinned_folders_list = PinnedFolderListWidget()
        self.pinned_folders_list.setObjectName("pinnedFoldersList")
        self.pinned_folders_list.setMinimumHeight(0)
        self.pinned_folders_list.itemSelectionChanged.connect(self._on_pinned_folder_selection_changed)
        self.pinned_folders_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pinned_folders_list.customContextMenuRequested.connect(self._on_pinned_folders_context_menu)
        pinned_layout.addWidget(self.pinned_folders_list, 1)
        pinned_section.setMinimumHeight(self.pinned_header.sizeHint().height() + pinned_layout.contentsMargins().top())

        folders_section = QWidget(self.left_sections_splitter)
        folders_layout = QVBoxLayout(folders_section)
        folders_layout.setContentsMargins(0, 8, 0, 0)
        folders_layout.setSpacing(6)

        folders_header_row = QWidget(folders_section)
        folders_header_layout = QHBoxLayout(folders_header_row)
        folders_header_layout.setContentsMargins(0, 0, 0, 0)
        folders_header_layout.setSpacing(6)
        self.folders_header = QLabel("Folders")
        folders_header_layout.addWidget(self.folders_header)
        folders_header_layout.addStretch(1)

        self.folders_menu_btn = QPushButton("...")
        self.folders_menu_btn.setObjectName("foldersMenuButton")
        self.folders_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folders_menu_btn.setFixedSize(QSize(26, 22))
        self.folders_menu_btn.clicked.connect(self._show_folders_header_menu)
        folders_header_layout.addWidget(self.folders_menu_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        folders_layout.addWidget(folders_header_row)
        folders_layout.addWidget(self.tree, 1)

        collections_section = QWidget(self.left_sections_splitter)
        collections_layout = QVBoxLayout(collections_section)
        collections_layout.setContentsMargins(0, 8, 0, 0)
        collections_layout.setSpacing(6)
        self.collections_header = QLabel("Collections")
        collections_layout.addWidget(self.collections_header)

        self.collections_list = CollectionListWidget()
        self.collections_list.setObjectName("collectionsList")
        self.collections_list.setMinimumHeight(0)
        self.collections_list.itemSelectionChanged.connect(self._on_collection_selection_changed)
        self.collections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.collections_list.customContextMenuRequested.connect(self._on_collections_context_menu)
        collections_layout.addWidget(self.collections_list, 1)
        collections_section.setMinimumHeight(self.collections_header.sizeHint().height() + collections_layout.contentsMargins().top())

        smart_collections_section = QWidget(self.left_sections_splitter)
        smart_collections_layout = QVBoxLayout(smart_collections_section)
        smart_collections_layout.setContentsMargins(0, 8, 0, 0)
        smart_collections_layout.setSpacing(6)
        self.smart_collections_header = QLabel("Smart Collections")
        smart_collections_layout.addWidget(self.smart_collections_header)

        self.smart_collections_list = CollectionListWidget()
        self.smart_collections_list.setObjectName("smartCollectionsList")
        self.smart_collections_list.setMinimumHeight(0)
        self.smart_collections_list.setAcceptDrops(False)
        self.smart_collections_list.setDropIndicatorShown(False)
        self.smart_collections_list.itemSelectionChanged.connect(self._on_smart_collection_selection_changed)
        smart_collections_layout.addWidget(self.smart_collections_list, 1)
        smart_collections_section.setMinimumHeight(self.smart_collections_header.sizeHint().height() + smart_collections_layout.contentsMargins().top())

        self.left_sections_splitter.addWidget(pinned_section)
        self.left_sections_splitter.addWidget(folders_section)
        self.left_sections_splitter.addWidget(collections_section)
        self.left_sections_splitter.addWidget(smart_collections_section)
        self.left_sections_splitter.setStretchFactor(0, 0)
        self.left_sections_splitter.setStretchFactor(1, 1)
        self.left_sections_splitter.setStretchFactor(2, 0)
        self.left_sections_splitter.setStretchFactor(3, 0)
        left_sections_state = self.bridge.settings.value("ui/left_sections_splitter_state_v3")
        if left_sections_state:
            self.left_sections_splitter.restoreState(left_sections_state)
        else:
            self.left_sections_splitter.setSizes([140, 260, 150, 150])
        self.left_sections_splitter.splitterMoved.connect(lambda *args: self._save_splitter_state())

        left_layout.addWidget(self.left_sections_splitter, 1)

        self.bridge.pinnedFoldersChanged.connect(self._reload_pinned_folders)
        self.bridge.collectionsChanged.connect(self._reload_collections)
        self.bridge.collectionsChanged.connect(self._reload_smart_collections)
        self._reload_pinned_folders()
        self._reload_collections()
        self._reload_smart_collections()

        self._navigate_to_folder(str(default_root), record_history=True, re_root_tree=True)

        # Apply UI flags from settings
        try:
            show_left = bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool))
            self._apply_ui_flag("ui.show_left_panel", show_left)
        except Exception:
            pass

        # Center: embedded WebEngine UI scaffold + future bottom chat panel
        center_container = QWidget(splitter)
        center_container_layout = QVBoxLayout(center_container)
        center_container_layout.setContentsMargins(0, 0, 0, 0)

        center_splitter = CustomSplitter(Qt.Orientation.Vertical)
        center_splitter.setObjectName("centerSplitter")
        center_splitter.setMouseTracking(True)
        center_splitter.setHandleWidth(7)
        center_splitter.setChildrenCollapsible(False)
        self.center_splitter = center_splitter

        center = QWidget(center_splitter)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.web = GalleryView(center)
        self.web.setPage(GalleryWebPage(self.web))
        center_layout.addWidget(self.web)

        # Native loading overlay shown while the WebEngine page itself is loading.
        self.web_loading = QWidget(self.web)
        self.web_loading.setStyleSheet(f"background: {Theme.get_bg(accent_q)};")
        self.web_loading.setGeometry(self.web.rect())
        self.web_loading.setVisible(True)

        wl_layout = QVBoxLayout(self.web_loading)
        wl_layout.setContentsMargins(24, 24, 24, 24)
        wl_layout.setSpacing(10)

        loading_center = QWidget(self.web_loading)
        center_layout_loading = QVBoxLayout(loading_center)
        center_layout_loading.setContentsMargins(0, 0, 0, 0)
        center_layout_loading.setSpacing(10)

        self.web_loading_label = QLabel("Loading gallery UIâ€¦")
        self.web_loading_label.setObjectName("webLoadingLabel")
        self.web_loading_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center_layout_loading.addWidget(self.web_loading_label)

        self.web_loading_bar = QProgressBar()
        self.web_loading_bar.setRange(0, 100)
        self.web_loading_bar.setValue(0)
        self.web_loading_bar.setTextVisible(False)
        self.web_loading_bar.setFixedSize(QSize(320, 10))
        try:
            accent = str(self.bridge.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8")
        except Exception:
            accent = "#8ab4f8"

        self.web_loading_bar.setStyleSheet(
            "QProgressBar{background: rgba(255,255,255,25); border-radius: 5px;} "
            f"QProgressBar::chunk{{background: {accent}; border-radius: 5px;}}"
        )
        center_layout_loading.addWidget(self.web_loading_bar, 0, Qt.AlignmentFlag.AlignHCenter)

        wl_layout.addStretch(1)
        wl_layout.addWidget(loading_center, 0, Qt.AlignmentFlag.AlignCenter)
        wl_layout.addStretch(1)

        # Right: Tag List + Metadata Panels
        self.right_panel_host = QWidget(splitter)
        self.right_panel_host.setObjectName("rightPanelHost")
        right_host_layout = QVBoxLayout(self.right_panel_host)
        right_host_layout.setContentsMargins(0, 0, 0, 0)
        right_host_layout.setSpacing(0)

        self.right_splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.right_splitter.setObjectName("rightSplitter")
        self.right_splitter.setHandleWidth(7)
        self.right_splitter.setChildrenCollapsible(False)
        right_host_layout.addWidget(self.right_splitter)

        self.tag_list_panel = QWidget(self.right_splitter)
        self.tag_list_panel.setObjectName("tagListPanel")
        self.tag_list_panel.setMinimumWidth(220)
        self.tag_list_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.tag_list_panel_layout = QVBoxLayout(self.tag_list_panel)
        self.tag_list_panel_layout.setContentsMargins(12, 12, 12, 12)
        self.tag_list_panel_layout.setSpacing(8)

        self.tag_list_header_row = QWidget(self.tag_list_panel)
        self.tag_list_header_row.setObjectName("tagListHeaderRow")
        tag_list_header_layout = QHBoxLayout(self.tag_list_header_row)
        tag_list_header_layout.setContentsMargins(0, 0, 0, 0)
        tag_list_header_layout.setSpacing(8)
        self.tag_list_title_lbl = QLabel("Tag List")
        self.tag_list_title_lbl.setObjectName("tagListTitleLabel")
        tag_list_header_layout.addWidget(self.tag_list_title_lbl)
        tag_list_header_layout.addStretch(1)
        self.tag_list_close_btn = QPushButton("")
        self.tag_list_close_btn.setObjectName("tagListCloseButton")
        self.tag_list_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tag_list_close_btn.setFixedSize(22, 22)
        self.tag_list_close_btn.clicked.connect(self._close_tag_list_panel)
        tag_list_header_layout.addWidget(self.tag_list_close_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tag_list_panel_layout.addWidget(self.tag_list_header_row)

        self.tag_list_select = QComboBox(self.tag_list_panel)
        self.tag_list_select.setObjectName("tagListSelect")
        self._configure_tag_list_combo(self.tag_list_select)
        self.tag_list_select.currentIndexChanged.connect(self._on_tag_list_changed)
        self.tag_list_panel_layout.addWidget(self.tag_list_select)

        self.btn_create_tag_list = QPushButton("Create New List")
        self.btn_create_tag_list.setObjectName("btnCreateTagList")
        self.btn_create_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create_tag_list.clicked.connect(self._create_tag_list)
        self.tag_list_panel_layout.addWidget(self.btn_create_tag_list)

        self.active_tag_list_name_lbl = ContextClickableLabel("")
        self.active_tag_list_name_lbl.setObjectName("activeTagListNameLabel")
        self.active_tag_list_name_lbl.setVisible(False)
        self.active_tag_list_name_lbl.rightClicked.connect(self._rename_active_tag_list)
        self.tag_list_panel_layout.addWidget(self.active_tag_list_name_lbl)

        self.tag_list_sort_lbl = QLabel("Sort By")
        self.tag_list_sort_lbl.setObjectName("tagListSortLabel")
        self.tag_list_sort_lbl.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.tag_list_sort_lbl)

        self.tag_list_sort_select = QComboBox(self.tag_list_panel)
        self.tag_list_sort_select.setObjectName("tagListSortSelect")
        self._configure_tag_list_combo(self.tag_list_sort_select)
        self.tag_list_sort_select.addItem("None", "none")
        self.tag_list_sort_select.addItem("A-Z", "az")
        self.tag_list_sort_select.addItem("Z-A", "za")
        self.tag_list_sort_select.addItem("Most Used", "most_used")
        self.tag_list_sort_select.addItem("Least Used", "least_used")
        self.tag_list_sort_select.currentIndexChanged.connect(self._on_tag_list_sort_changed)
        self.tag_list_sort_select.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.tag_list_sort_select)

        self.btn_add_tag_list_tag = QPushButton("Add New Tag")
        self.btn_add_tag_list_tag.setObjectName("btnAddTagListTag")
        self.btn_add_tag_list_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_tag_list_tag.clicked.connect(self._add_tag_to_active_list)
        self.btn_add_tag_list_tag.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_add_tag_list_tag)

        self.btn_import_tag_list_tags = QPushButton("Import Tags from Selected File(s)")
        self.btn_import_tag_list_tags.setObjectName("btnImportTagListTags")
        self.btn_import_tag_list_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_tag_list_tags.clicked.connect(self._import_tags_from_current_file_into_active_list)
        self.btn_import_tag_list_tags.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_import_tag_list_tags)

        self.btn_clear_tag_scope_filter = QPushButton("Deselect Tag Filter")
        self.btn_clear_tag_scope_filter.setObjectName("btnClearTagScopeFilter")
        self.btn_clear_tag_scope_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_tag_scope_filter.clicked.connect(self._clear_tag_scope_filter)
        self.btn_clear_tag_scope_filter.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_clear_tag_scope_filter)

        self.tag_list_rows = TagListRowsWidget(self.tag_list_panel)
        self.tag_list_rows.setObjectName("tagListRows")
        self.tag_list_rows.setMinimumHeight(0)
        self.tag_list_rows.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tag_list_rows.orderChanged.connect(self._persist_active_tag_list_order)
        self.tag_list_rows.backgroundClicked.connect(self._clear_tag_scope_filter)
        self.tag_list_panel_layout.addWidget(self.tag_list_rows, 1)

        self.tag_list_empty_lbl = QLabel("Create or select a tag list.")
        self.tag_list_empty_lbl.setObjectName("tagListEmptyLabel")
        self.tag_list_empty_lbl.setWordWrap(True)
        self.tag_list_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.tag_list_empty_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tag_list_empty_lbl.setVisible(True)
        self.tag_list_panel_layout.addWidget(self.tag_list_empty_lbl)

        self.tag_list_bottom_spacer = QSpacerItem(
            0,
            0,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )
        self.tag_list_panel_layout.addItem(self.tag_list_bottom_spacer)

        self.right_panel = QWidget(self.right_splitter)
        self.right_panel.setObjectName("rightPanel")
        outer_right_layout = QVBoxLayout(self.right_panel)
        outer_right_layout.setContentsMargins(0, 0, 0, 0)
        outer_right_layout.setSpacing(0)

        self.right_workspace_stack = QStackedWidget(self.right_panel)
        self.right_workspace_stack.setObjectName("rightWorkspaceStack")
        outer_right_layout.addWidget(self.right_workspace_stack)

        self.details_workspace = QWidget(self.right_workspace_stack)
        self.details_workspace.setObjectName("detailsWorkspace")
        details_workspace_layout = QVBoxLayout(self.details_workspace)
        details_workspace_layout.setContentsMargins(0, 0, 0, 0)
        details_workspace_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("metaScrollArea")
        self.scroll_area.viewport().installEventFilter(self)
        
        self.scroll_container = QWidget(self.scroll_area)
        self.scroll_container.setObjectName("rightPanelScrollContainer")
        right_layout = QVBoxLayout(self.scroll_container)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(6)
        self.right_layout = right_layout

        # Preview Header Row (Always visible title + toggle buttons)
        self.preview_header_row = QWidget(self.scroll_container)
        self.preview_header_row.setObjectName("previewHeaderRow")
        preview_header_layout = QHBoxLayout(self.preview_header_row)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(6)
        
        self.preview_header_lbl = QLabel("Preview")
        self.preview_header_lbl.setObjectName("previewHeaderLabel")
        preview_header_layout.addWidget(self.preview_header_lbl)
        preview_header_layout.addStretch(1)

        self.btn_play_preview = QPushButton("Play")
        self.btn_play_preview.setObjectName("btnPlayPreview")
        self.btn_play_preview.setToolTip("Open selected video preview")
        self.btn_play_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_preview.clicked.connect(self._play_selected_video_in_sidebar)
        self.btn_play_preview.hide()
        preview_header_layout.addWidget(self.btn_play_preview)

        # Toggle OFF (Hide) button
        self.btn_close_preview = QPushButton("")
        self.btn_close_preview.setObjectName("btnClosePreview")
        self.btn_close_preview.setToolTip("Hide preview image")
        self.btn_close_preview.setFixedSize(QSize(22, 22))
        self.btn_close_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_preview.clicked.connect(lambda: self.bridge.set_setting_bool("ui.preview_above_details", False))
        preview_header_layout.addWidget(self.btn_close_preview)

        # Toggle ON (Show) button
        self.btn_show_preview_inline = QPushButton("â›¶") # Unicode maximize/corners
        self.btn_show_preview_inline.setObjectName("btnShowPreviewInline")
        self.btn_show_preview_inline.setToolTip("Show preview image")
        self.btn_show_preview_inline.setFixedSize(QSize(22, 22))
        self.btn_show_preview_inline.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_preview_inline.clicked.connect(lambda: self.bridge.set_setting_bool("ui.preview_above_details", True))
        preview_header_layout.addWidget(self.btn_show_preview_inline)

        right_layout.addWidget(self.preview_header_row)

        self.preview_image_lbl = QLabel()
        self.preview_image_lbl.setObjectName("previewImageLabel")
        self.preview_image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_lbl.setMinimumHeight(0)
        self.preview_image_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.preview_image_lbl.setText("No preview")
        self.preview_image_lbl.setWordWrap(True)
        self.preview_image_lbl.setCursor(Qt.CursorShape.ArrowCursor)
        self._preview_bg_hint = ""
        self._preview_source_pixmap: QPixmap | None = None
        self._preview_movie: QMovie | None = None
        self._preview_aspect_ratio = 1.0
        right_layout.addWidget(self.preview_image_lbl)

        # Sidebar preview overlay is manually positioned to the preview label's rect.
        # Avoid also putting it in a layout, which can produce bad geometry/clipping.
        self.sidebar_video_overlay: LightboxVideoOverlay | None = None

        self.btn_preview_overlay_play = QPushButton(self.preview_image_lbl)
        self.btn_preview_overlay_play.setObjectName("btnPreviewOverlayPlay")
        self.btn_preview_overlay_play.setToolTip("Play video in preview")
        self.btn_preview_overlay_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_overlay_play.setFixedSize(QSize(52, 52))
        self.btn_preview_overlay_play.setIconSize(QSize(30, 30))
        self._update_preview_play_button_icon()
        self.btn_preview_overlay_play.clicked.connect(self._play_selected_video_in_sidebar)
        self.btn_preview_overlay_play.installEventFilter(self)
        self.btn_preview_overlay_play.hide()
        self.btn_preview_overlay_play.raise_()
        self._video_preview_transition_active = False

        self.preview_sep = self._add_sep("preview_sep_line")
        right_layout.addWidget(self.preview_sep)

        self.details_header_lbl = QLabel("Details")
        self.details_header_lbl.setObjectName("detailsHeaderLabel")
        right_layout.addWidget(self.details_header_lbl)

        self.meta_empty_state_lbl = QLabel("Select a file to show details")
        self.meta_empty_state_lbl.setObjectName("metaEmptyStateLabel")
        self.meta_empty_state_lbl.setWordWrap(True)
        self.meta_empty_state_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self.meta_empty_state_lbl)
        self.meta_empty_state_lbl.setVisible(False)

        self.meta_empty_select_all_btn = QPushButton("Select All")
        self.meta_empty_select_all_btn.setObjectName("metaEmptySelectAllButton")
        self.meta_empty_select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_empty_select_all_btn.clicked.connect(self._select_all_visible_gallery_items)
        self.meta_empty_select_all_btn.setVisible(False)
        right_layout.addWidget(self.meta_empty_select_all_btn)

        self.scroll_area.setWidget(self.scroll_container)
        details_workspace_layout.addWidget(self.scroll_area)

        # --- Filename (editable, triggers rename) ---
        self.lbl_fn_cap = QLabel("Filename:")
        right_layout.addWidget(self.lbl_fn_cap)
        self.meta_filename_edit = QLineEdit()
        self.meta_filename_edit.setPlaceholderText("filename.ext")
        self.meta_filename_edit.setObjectName("metaFilenameEdit")
        self.meta_filename_edit.editingFinished.connect(self._rename_from_panel)
        right_layout.addWidget(self.meta_filename_edit)

        # --- Read-only file info (single label per field, label + value inline) ---
        self.meta_path_lbl = QLabel("Folder:")
        self.meta_path_lbl.setObjectName("metaPathLabel")
        self.meta_path_lbl.setWordWrap(True)
        right_layout.addWidget(self.meta_path_lbl)

        self.meta_size_lbl = QLabel("File Size:")
        self.meta_size_lbl.setObjectName("metaSizeLabel")

        self.meta_res_lbl = QLabel("")
        self.meta_res_lbl.setObjectName("metaResLabel")

        self.lbl_exif_date_taken_cap = QLabel("Date Taken:")
        self.lbl_exif_date_taken_cap.setObjectName("metaExifDateTakenCaption")
        self.meta_exif_date_taken_edit = QLineEdit()
        self.meta_exif_date_taken_edit.setObjectName("metaExifDateTakenEdit")
        self.meta_exif_date_taken_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")

        self.lbl_metadata_date_cap = QLabel("Date Acquired:")
        self.lbl_metadata_date_cap.setObjectName("metaMetadataDateCaption")
        self.meta_metadata_date_edit = QLineEdit()
        self.meta_metadata_date_edit.setObjectName("metaMetadataDateEdit")
        self.meta_metadata_date_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")

        self.lbl_original_file_date_cap = QLabel("Original File Date:")
        self.lbl_original_file_date_cap.setObjectName("metaOriginalFileDateCaption")
        self.meta_original_file_date_lbl = QLabel("")
        self.meta_original_file_date_lbl.setObjectName("metaOriginalFileDateLabel")
        self.meta_original_file_date_lbl.setWordWrap(True)

        self.lbl_file_created_date_cap = QLabel("Windows ctime:")
        self.lbl_file_created_date_cap.setObjectName("metaFileCreatedDateCaption")
        self.meta_file_created_date_lbl = QLabel("")
        self.meta_file_created_date_lbl.setObjectName("metaFileCreatedDateLabel")
        self.meta_file_created_date_lbl.setWordWrap(True)

        self.lbl_file_modified_date_cap = QLabel("Date Modified:")
        self.lbl_file_modified_date_cap.setObjectName("metaFileModifiedDateCaption")
        self.meta_file_modified_date_lbl = QLabel("")
        self.meta_file_modified_date_lbl.setObjectName("metaFileModifiedDateLabel")
        self.meta_file_modified_date_lbl.setWordWrap(True)

        self.lbl_text_detected_cap = QLabel("Text Detected?")
        self.lbl_text_detected_cap.setObjectName("metaTextDetectedCaption")
        self.meta_text_detected_row = QWidget()
        self.meta_text_detected_row.setObjectName("metaSwitchRow")
        text_detected_layout = QHBoxLayout(self.meta_text_detected_row)
        text_detected_layout.setContentsMargins(0, 0, 0, 0)
        text_detected_layout.setSpacing(8)
        self.meta_text_detected_toggle = QCheckBox()
        self.meta_text_detected_toggle.setObjectName("metaSwitch")
        self.meta_text_detected_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_text_detected_value_lbl = QLabel("No Text")
        self.meta_text_detected_value_lbl.setObjectName("metaSwitchValueLabel")
        text_detected_layout.addWidget(self.meta_text_detected_toggle)
        text_detected_layout.addWidget(self.meta_text_detected_value_lbl)
        text_detected_layout.addStretch(1)
        self.meta_text_detected_toggle.toggled.connect(
            lambda checked: self._set_switch_value_label(self.meta_text_detected_value_lbl, checked, "Text", "No Text")
        )
        self.meta_text_detected_toggle.clicked.connect(self._save_text_detected_override_from_toggle)
        self.lbl_text_detected_note = QLabel("This overrides the auto text detection value of [No Text Detected]")
        self.lbl_text_detected_note.setObjectName("metaFieldNoteLabel")
        self.lbl_text_detected_note.setWordWrap(True)

        self.lbl_detected_text_cap = QLabel("Text Detected:")
        self.lbl_detected_text_cap.setObjectName("metaDetectedTextCaption")
        self.meta_detected_text_edit = QPlainTextEdit()
        self.meta_detected_text_edit.setObjectName("metaDetectedTextEdit")
        self.meta_detected_text_edit.setPlaceholderText("OCR text or manually entered text...")
        self.meta_detected_text_edit.setMaximumHeight(90)
        self.btn_use_ocr = QPushButton("Use OCR")
        self.btn_use_ocr.setObjectName("btnUseOcr")
        self.btn_use_ocr.setProperty("baseText", "Use OCR")
        self.btn_use_ocr.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use_ocr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_use_ocr.clicked.connect(self._run_text_ocr)
        
        self.meta_fields_layout = QVBoxLayout()
        self.meta_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.meta_fields_layout.setSpacing(6)
        right_layout.addLayout(self.meta_fields_layout)

        # --- Group Labels ---
        self.lbl_group_general = QLabel("General")
        self.lbl_group_general.setObjectName("metaGroupLabel")
        self.lbl_group_general.hide()

        self.lbl_group_camera = QLabel("Camera")
        self.lbl_group_camera.setObjectName("metaGroupLabel")
        self.lbl_group_camera.hide()

        self.lbl_group_ai = QLabel("AI")
        self.lbl_group_ai.setObjectName("metaGroupLabel")
        self.lbl_group_ai.hide()

        self.meta_camera_lbl = QLabel("")
        self.meta_camera_lbl.setObjectName("metaCameraLabel")

        self.meta_location_lbl = QLabel("")
        self.meta_location_lbl.setObjectName("metaLocationLabel")

        self.meta_iso_lbl = QLabel("")
        self.meta_iso_lbl.setObjectName("metaISOLabel")

        self.meta_shutter_lbl = QLabel("")
        self.meta_shutter_lbl.setObjectName("metaShutterLabel")

        self.meta_aperture_lbl = QLabel("")
        self.meta_aperture_lbl.setObjectName("metaApertureLabel")

        self.meta_software_lbl = QLabel("")
        self.meta_software_lbl.setObjectName("metaSoftwareLabel")

        self.meta_lens_lbl = QLabel("")
        self.meta_lens_lbl.setObjectName("metaLensLabel")

        self.meta_dpi_lbl = QLabel("")
        self.meta_dpi_lbl.setObjectName("metaDPILabel")

        self.meta_duration_lbl = QLabel("")
        self.meta_duration_lbl.setObjectName("metaDurationLabel")

        self.meta_fps_lbl = QLabel("")
        self.meta_fps_lbl.setObjectName("metaFPSLabel")

        self.meta_codec_lbl = QLabel("")
        self.meta_codec_lbl.setObjectName("metaCodecLabel")

        self.meta_audio_lbl = QLabel("")
        self.meta_audio_lbl.setObjectName("metaAudioLabel")

        self.lbl_embedded_tags_cap = QLabel("Embedded-Tags (semicolon separated):")
        self.lbl_embedded_tags_cap.setObjectName("metaEmbeddedTagsCaption")
        self.meta_embedded_tags_edit = QLineEdit()
        self.meta_embedded_tags_edit.setObjectName("metaEmbeddedTagsEdit")
        self.meta_embedded_tags_edit.setPlaceholderText("keyword1; keyword2; keyword3")

        self.lbl_embedded_comments_cap = QLabel("Embedded-Comments:")
        self.lbl_embedded_comments_cap.setObjectName("metaEmbeddedCommentsCaption")
        self.meta_embedded_comments_edit = QTextEdit()
        self.meta_embedded_comments_edit.setObjectName("metaEmbeddedCommentsEdit")
        self.meta_embedded_comments_edit.setPlaceholderText("Embedded comments...")
        self.meta_embedded_comments_edit.setMaximumHeight(70)

        self.lbl_embedded_metadata_cap = QLabel("Embedded Metadata:")
        self.lbl_embedded_metadata_cap.setObjectName("metaEmbeddedMetadataCaption")
        self.meta_embedded_metadata_edit = QTextEdit()
        self.meta_embedded_metadata_edit.setObjectName("metaEmbeddedMetadataEdit")
        self.meta_embedded_metadata_edit.setReadOnly(True)
        self.meta_embedded_metadata_edit.setPlaceholderText("Embedded XMP/RDF and custom metadata...")
        self.meta_embedded_metadata_edit.setMaximumHeight(110)

        self.lbl_ai_status_cap = QLabel("AI Detection:")
        self.lbl_ai_status_cap.setObjectName("metaAIStatusCaption")
        self.meta_ai_status_edit = QLineEdit()
        self.meta_ai_status_edit.setObjectName("metaAIStatusEdit")
        self.meta_ai_status_edit.setReadOnly(True)
        self.meta_ai_status_edit.setPlaceholderText("AI detection status...")

        self.lbl_ai_generated_cap = QLabel("AI Generated?")
        self.lbl_ai_generated_cap.setObjectName("metaAIGeneratedCaption")
        self.meta_ai_generated_row = QWidget()
        self.meta_ai_generated_row.setObjectName("metaSwitchRow")
        ai_generated_layout = QHBoxLayout(self.meta_ai_generated_row)
        ai_generated_layout.setContentsMargins(0, 0, 0, 0)
        ai_generated_layout.setSpacing(8)
        self.meta_ai_generated_toggle = QCheckBox()
        self.meta_ai_generated_toggle.setObjectName("metaSwitch")
        self.meta_ai_generated_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_ai_generated_value_lbl = QLabel("Non-AI")
        self.meta_ai_generated_value_lbl.setObjectName("metaSwitchValueLabel")
        ai_generated_layout.addWidget(self.meta_ai_generated_toggle)
        ai_generated_layout.addWidget(self.meta_ai_generated_value_lbl)
        ai_generated_layout.addStretch(1)
        self.meta_ai_generated_toggle.toggled.connect(
            lambda checked: self._set_switch_value_label(self.meta_ai_generated_value_lbl, checked, "AI", "Non-AI")
        )
        self.meta_ai_generated_toggle.clicked.connect(self._save_ai_generated_override_from_toggle)
        self.lbl_ai_generated_note = QLabel("This overrides the auto AI Detection value of [Not AI Generated]")
        self.lbl_ai_generated_note.setObjectName("metaFieldNoteLabel")
        self.lbl_ai_generated_note.setWordWrap(True)

        self.lbl_ai_source_cap = QLabel("AI Tool / Source:")
        self.lbl_ai_source_cap.setObjectName("metaAISourceCaption")
        self.meta_ai_source_edit = QTextEdit()
        self.meta_ai_source_edit.setObjectName("metaAISourceEdit")
        self.meta_ai_source_edit.setReadOnly(False)
        self.meta_ai_source_edit.setPlaceholderText("Tool and source metadata...")
        self.meta_ai_source_edit.setMaximumHeight(60)

        self.lbl_ai_families_cap = QLabel("AI Metadata Families:")
        self.lbl_ai_families_cap.setObjectName("metaAIFamiliesCaption")
        self.meta_ai_families_edit = QLineEdit()
        self.meta_ai_families_edit.setObjectName("metaAIFamiliesEdit")
        self.meta_ai_families_edit.setReadOnly(False)
        self.meta_ai_families_edit.setPlaceholderText("Detected metadata families...")

        self.lbl_ai_detection_reasons_cap = QLabel("AI Detection Reasons:")
        self.lbl_ai_detection_reasons_cap.setObjectName("metaAIDetectionReasonsCaption")
        self.meta_ai_detection_reasons_edit = QTextEdit()
        self.meta_ai_detection_reasons_edit.setObjectName("metaAIDetectionReasonsEdit")
        self.meta_ai_detection_reasons_edit.setReadOnly(False)
        self.meta_ai_detection_reasons_edit.setPlaceholderText("Detection reasons...")
        self.meta_ai_detection_reasons_edit.setMaximumHeight(60)

        self.lbl_ai_loras_cap = QLabel("AI LoRAs:")
        self.lbl_ai_loras_cap.setObjectName("metaAILorasCaption")
        self.meta_ai_loras_edit = QTextEdit()
        self.meta_ai_loras_edit.setObjectName("metaAILorasEdit")
        self.meta_ai_loras_edit.setReadOnly(True)
        self.meta_ai_loras_edit.setPlaceholderText("LoRAs...")
        self.meta_ai_loras_edit.setMaximumHeight(60)

        self.lbl_ai_model_cap = QLabel("AI Model:")
        self.lbl_ai_model_cap.setObjectName("metaAIModelCaption")
        self.meta_ai_model_edit = QLineEdit()
        self.meta_ai_model_edit.setObjectName("metaAIModelEdit")
        self.meta_ai_model_edit.setReadOnly(False)
        self.meta_ai_model_edit.setPlaceholderText("Model...")

        self.lbl_ai_checkpoint_cap = QLabel("AI Checkpoint:")
        self.lbl_ai_checkpoint_cap.setObjectName("metaAICheckpointCaption")
        self.meta_ai_checkpoint_edit = QLineEdit()
        self.meta_ai_checkpoint_edit.setObjectName("metaAICheckpointEdit")
        self.meta_ai_checkpoint_edit.setReadOnly(False)
        self.meta_ai_checkpoint_edit.setPlaceholderText("Checkpoint...")

        self.lbl_ai_sampler_cap = QLabel("AI Sampler:")
        self.lbl_ai_sampler_cap.setObjectName("metaAISamplerCaption")
        self.meta_ai_sampler_edit = QLineEdit()
        self.meta_ai_sampler_edit.setObjectName("metaAISamplerEdit")
        self.meta_ai_sampler_edit.setReadOnly(False)
        self.meta_ai_sampler_edit.setPlaceholderText("Sampler...")

        self.lbl_ai_scheduler_cap = QLabel("AI Scheduler:")
        self.lbl_ai_scheduler_cap.setObjectName("metaAISchedulerCaption")
        self.meta_ai_scheduler_edit = QLineEdit()
        self.meta_ai_scheduler_edit.setObjectName("metaAISchedulerEdit")
        self.meta_ai_scheduler_edit.setReadOnly(False)
        self.meta_ai_scheduler_edit.setPlaceholderText("Scheduler...")

        self.lbl_ai_cfg_cap = QLabel("AI CFG:")
        self.lbl_ai_cfg_cap.setObjectName("metaAICFGCaption")
        self.meta_ai_cfg_edit = QLineEdit()
        self.meta_ai_cfg_edit.setObjectName("metaAICFGEdit")
        self.meta_ai_cfg_edit.setReadOnly(False)
        self.meta_ai_cfg_edit.setPlaceholderText("CFG...")

        self.lbl_ai_steps_cap = QLabel("AI Steps:")
        self.lbl_ai_steps_cap.setObjectName("metaAIStepsCaption")
        self.meta_ai_steps_edit = QLineEdit()
        self.meta_ai_steps_edit.setObjectName("metaAIStepsEdit")
        self.meta_ai_steps_edit.setReadOnly(False)
        self.meta_ai_steps_edit.setPlaceholderText("Steps...")

        self.lbl_ai_seed_cap = QLabel("AI Seed:")
        self.lbl_ai_seed_cap.setObjectName("metaAISeedCaption")
        self.meta_ai_seed_edit = QLineEdit()
        self.meta_ai_seed_edit.setObjectName("metaAISeedEdit")
        self.meta_ai_seed_edit.setReadOnly(False)
        self.meta_ai_seed_edit.setPlaceholderText("Seed...")

        self.lbl_ai_upscaler_cap = QLabel("AI Upscaler:")
        self.lbl_ai_upscaler_cap.setObjectName("metaAIUpscalerCaption")
        self.meta_ai_upscaler_edit = QLineEdit()
        self.meta_ai_upscaler_edit.setObjectName("metaAIUpscalerEdit")
        self.meta_ai_upscaler_edit.setReadOnly(False)
        self.meta_ai_upscaler_edit.setPlaceholderText("Upscaler...")

        self.lbl_ai_denoise_cap = QLabel("AI Denoise:")
        self.lbl_ai_denoise_cap.setObjectName("metaAIDenoiseCaption")
        self.meta_ai_denoise_edit = QLineEdit()
        self.meta_ai_denoise_edit.setObjectName("metaAIDenoiseEdit")
        self.meta_ai_denoise_edit.setReadOnly(False)
        self.meta_ai_denoise_edit.setPlaceholderText("Denoise strength...")

        # --- Separators ---
        self.meta_sep1 = self._add_sep("meta_sep1_line")
        self.meta_sep2 = self._add_sep("meta_sep2_line")
        self.meta_sep3 = self._add_sep("meta_sep3_line")
        # --- Separators (Container + Line pattern for perfect 1px rendering) ---

        # --- Editable metadata ---
        self.lbl_desc_cap = QLabel("Description:")
        self.meta_desc = QTextEdit()
        self.meta_desc.setPlaceholderText("Add a description...")
        self.meta_desc.setMaximumHeight(130)
        self.meta_desc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.generate_description_btn_row = QWidget()
        self.generate_description_btn_row.setObjectName("generateDescriptionButtonRow")
        self.generate_description_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_btn_row.setMinimumWidth(0)
        generate_description_btn_layout = QHBoxLayout(self.generate_description_btn_row)
        generate_description_btn_layout.setContentsMargins(0, 0, 0, 0)
        generate_description_btn_layout.setSpacing(0)
        self.btn_generate_description = QPushButton("Generate Description")
        self.btn_generate_description.setObjectName("btnGenerateDescription")
        self.btn_generate_description.setProperty("baseText", "Generate Description")
        self.btn_generate_description.setToolTip("Generate a local AI description using the current database tags as context")
        self.btn_generate_description.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_generate_description.clicked.connect(self._run_local_ai_description)
        generate_description_btn_layout.addWidget(self.btn_generate_description)
        self.generate_description_progress_lbl = ProgressStatusLabel("")
        self.generate_description_progress_lbl.setObjectName("localAiProgressLabel")
        self._configure_progress_status_label(self.generate_description_progress_lbl)
        self.generate_description_progress_lbl.setVisible(False)
        self.generate_description_progress_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_progress_lbl.setMinimumWidth(0)
        self.generate_description_error_edit = QPlainTextEdit()
        self.generate_description_error_edit.setObjectName("localAiErrorText")
        self._configure_local_ai_error_widget(self.generate_description_error_edit)
        self.generate_description_error_edit.setVisible(False)
        self.generate_description_error_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_error_edit.setMinimumWidth(0)

        self.lbl_tags_cap = QLabel("Tags (comma separated):")
        self.meta_tags = QTextEdit()
        self.meta_tags.setPlaceholderText("tag1, tag2...")
        self.meta_tags.setMaximumHeight(118)
        self.meta_tags.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.meta_tags.textChanged.connect(self._save_native_tags)
        self.meta_tags.textChanged.connect(lambda: self._refresh_tag_list_rows_state())

        self.generate_tags_btn_row = QWidget()
        self.generate_tags_btn_row.setObjectName("generateTagsButtonRow")
        self.generate_tags_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_btn_row.setMinimumWidth(0)
        generate_tags_btn_layout = QHBoxLayout(self.generate_tags_btn_row)
        generate_tags_btn_layout.setContentsMargins(0, 0, 0, 0)
        generate_tags_btn_layout.setSpacing(0)
        self.btn_generate_tags = QPushButton("Generate Tags")
        self.btn_generate_tags.setObjectName("btnGenerateTags")
        self.btn_generate_tags.setProperty("baseText", "Generate Tags")
        self.btn_generate_tags.setToolTip("Generate local AI tags and merge them into the database tag field")
        self.btn_generate_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_generate_tags.clicked.connect(self._run_local_ai_tags)
        generate_tags_btn_layout.addWidget(self.btn_generate_tags)
        self.generate_tags_progress_lbl = ProgressStatusLabel("")
        self.generate_tags_progress_lbl.setObjectName("localAiProgressLabel")
        self._configure_progress_status_label(self.generate_tags_progress_lbl)
        self.generate_tags_progress_lbl.setVisible(False)
        self.generate_tags_progress_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_progress_lbl.setMinimumWidth(0)
        self.generate_tags_error_edit = QPlainTextEdit()
        self.generate_tags_error_edit.setObjectName("localAiErrorText")
        self._configure_local_ai_error_widget(self.generate_tags_error_edit)
        self.generate_tags_error_edit.setVisible(False)
        self.generate_tags_error_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_error_edit.setMinimumWidth(0)

        self.tag_list_open_btn_row = QWidget()
        self.tag_list_open_btn_row.setObjectName("tagListOpenButtonRow")
        self.tag_list_open_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        tag_list_open_btn_layout = QHBoxLayout(self.tag_list_open_btn_row)
        tag_list_open_btn_layout.setContentsMargins(0, 0, 0, 0)
        tag_list_open_btn_layout.setSpacing(0)
        self.btn_open_tag_list = QPushButton("Open Tag List")
        self.btn_open_tag_list.setObjectName("btnOpenTagList")
        self.btn_open_tag_list.setProperty("baseText", "Open Tag List")
        self.btn_open_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_tag_list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_open_tag_list.clicked.connect(self._toggle_tag_list_panel)
        tag_list_open_btn_layout.addWidget(self.btn_open_tag_list)

        self.lbl_ai_prompt_cap = QLabel("AI Prompt:")
        self.lbl_ai_prompt_cap.setObjectName("metaAIPromptCaption")
        self.meta_ai_prompt_edit = QTextEdit()
        self.meta_ai_prompt_edit.setObjectName("metaAIPromptEdit")
        self.meta_ai_prompt_edit.setPlaceholderText("AI prompt...")
        self.meta_ai_prompt_edit.setMaximumHeight(70)

        self.lbl_ai_negative_prompt_cap = QLabel("AI Negative Prompt:")
        self.lbl_ai_negative_prompt_cap.setObjectName("metaAINegativePromptCaption")
        self.meta_ai_negative_prompt_edit = QTextEdit()
        self.meta_ai_negative_prompt_edit.setObjectName("metaAINegativePromptEdit")
        self.meta_ai_negative_prompt_edit.setPlaceholderText("AI negative prompt...")
        self.meta_ai_negative_prompt_edit.setMaximumHeight(70)

        self.lbl_ai_params_cap = QLabel("AI Parameters:")
        self.lbl_ai_params_cap.setObjectName("metaAIParamsCaption")
        self.meta_ai_params_edit = QTextEdit()
        self.meta_ai_params_edit.setObjectName("metaAIParamsEdit")
        self.meta_ai_params_edit.setPlaceholderText("AI parameters...")
        self.meta_ai_params_edit.setMaximumHeight(70)

        self.lbl_ai_workflows_cap = QLabel("AI Workflows:")
        self.lbl_ai_workflows_cap.setObjectName("metaAIWorkflowsCaption")
        self.meta_ai_workflows_edit = QTextEdit()
        self.meta_ai_workflows_edit.setObjectName("metaAIWorkflowsEdit")
        self.meta_ai_workflows_edit.setReadOnly(True)
        self.meta_ai_workflows_edit.setPlaceholderText("Workflow metadata...")
        self.meta_ai_workflows_edit.setMaximumHeight(70)

        self.lbl_ai_provenance_cap = QLabel("AI Provenance:")
        self.lbl_ai_provenance_cap.setObjectName("metaAIProvenanceCaption")
        self.meta_ai_provenance_edit = QTextEdit()
        self.meta_ai_provenance_edit.setObjectName("metaAIProvenanceEdit")
        self.meta_ai_provenance_edit.setReadOnly(True)
        self.meta_ai_provenance_edit.setPlaceholderText("Provenance metadata...")
        self.meta_ai_provenance_edit.setMaximumHeight(70)

        self.lbl_ai_character_cards_cap = QLabel("AI Character Cards:")
        self.lbl_ai_character_cards_cap.setObjectName("metaAICharacterCardsCaption")
        self.meta_ai_character_cards_edit = QTextEdit()
        self.meta_ai_character_cards_edit.setObjectName("metaAICharacterCardsEdit")
        self.meta_ai_character_cards_edit.setReadOnly(True)
        self.meta_ai_character_cards_edit.setPlaceholderText("Character card metadata...")
        self.meta_ai_character_cards_edit.setMaximumHeight(70)

        self.lbl_ai_raw_paths_cap = QLabel("AI Metadata Paths:")
        self.lbl_ai_raw_paths_cap.setObjectName("metaAIRawPathsCaption")
        self.meta_ai_raw_paths_edit = QTextEdit()
        self.meta_ai_raw_paths_edit.setObjectName("metaAIRawPathsEdit")
        self.meta_ai_raw_paths_edit.setReadOnly(True)
        self.meta_ai_raw_paths_edit.setPlaceholderText("Embedded metadata paths...")
        self.meta_ai_raw_paths_edit.setMaximumHeight(70)

        self.lbl_notes_cap = QLabel("Notes:")
        self.meta_notes = QPlainTextEdit()
        self.meta_notes.setPlaceholderText("Personal notes...")
        self.meta_notes.setMaximumHeight(90)

        right_layout.addStretch(1)

        self.btn_clear_bulk_tags = QPushButton("Clear All Tags")
        self.btn_clear_bulk_tags.setObjectName("btnClearBulkTags")
        self.btn_clear_bulk_tags.setProperty("baseText", "Clear All Tags")
        self.btn_clear_bulk_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bulk_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_clear_bulk_tags.clicked.connect(self._clear_bulk_tags)
        right_layout.addWidget(self.btn_clear_bulk_tags)
        self.btn_clear_bulk_tags.setVisible(False)

        self.btn_save_meta = QPushButton("Save Changes to Database")
        self.btn_save_meta.setObjectName("btnSaveMeta")
        self.btn_save_meta.setProperty("baseText", "Save Changes to Database")
        self.btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_meta.clicked.connect(self._save_native_metadata)
        self.btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.btn_save_meta)

        for attr_name, widget in self.__dict__.items():
            if not isinstance(widget, QLabel):
                continue
            if not (attr_name.startswith("lbl_") or attr_name.startswith("meta_")):
                continue
            if widget is self.preview_image_lbl:
                continue
            widget.setIndent(0)
            widget.setMargin(0)
            self._make_detail_label_copyable(widget)
            if attr_name.startswith("lbl_"):
                widget.setProperty("detailCaption", True)

        # AI/EXIF Actions
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        self.btn_import_exif = QPushButton("Import Metadata")
        self.btn_import_exif.setObjectName("btnImportExif")
        self.btn_import_exif.setProperty("baseText", "Import Metadata")
        self.btn_import_exif.setToolTip("Append tags/comments from file to database")
        self.btn_import_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_import_exif.clicked.connect(self._import_exif_to_db)
        action_layout.addWidget(self.btn_import_exif)

        self.btn_merge_hidden_meta = QPushButton("Merge Hidden Metadata Into Visible Comments Field")
        self.btn_merge_hidden_meta.setObjectName("btnMergeHiddenMeta")
        self.btn_merge_hidden_meta.setProperty("baseText", "Merge Hidden Metadata Into Visible Comments Field")
        self.btn_merge_hidden_meta.setToolTip("Write combined hidden metadata into the Windows-visible comments field using the existing embed path")
        self.btn_merge_hidden_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_merge_hidden_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_merge_hidden_meta.clicked.connect(self._merge_hidden_metadata_into_visible_comments)
        action_layout.addWidget(self.btn_merge_hidden_meta)

        self.btn_save_to_exif = QPushButton("Embed Data in File")
        self.btn_save_to_exif.setObjectName("btnSaveToExif")
        self.btn_save_to_exif.setProperty("baseText", "Embed Data in File")
        self.btn_save_to_exif.setToolTip("Write tags and comments from these fields into the file's embedded metadata")
        self.btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_to_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_save_to_exif.clicked.connect(self._save_to_exif_cmd)
        action_layout.addWidget(self.btn_save_to_exif)
        right_layout.addLayout(action_layout)

        self.meta_status_lbl = StatusTextEdit("")
        self.meta_status_lbl.setObjectName("metaStatusLabel")
        self.meta_status_lbl.setMinimumWidth(0)
        self._configure_status_text_widget(self.meta_status_lbl)
        right_layout.addWidget(self.meta_status_lbl)

        self.bulk_editor_panel = QWidget(self.right_workspace_stack)
        self.bulk_editor_panel.setObjectName("bulkTagEditorPanel")
        bulk_editor_outer_layout = QVBoxLayout(self.bulk_editor_panel)
        bulk_editor_outer_layout.setContentsMargins(12, 12, 12, 12)
        bulk_editor_outer_layout.setSpacing(8)

        self.bulk_header_lbl = QLabel("Bulk Editor")
        self.bulk_header_lbl.setObjectName("bulkTagEditorHeaderLabel")
        bulk_editor_outer_layout.addWidget(self.bulk_header_lbl)

        self.bulk_editor_mode_row = QWidget(self.bulk_editor_panel)
        self.bulk_editor_mode_row.setObjectName("bulkEditorModeRow")
        bulk_editor_mode_layout = QHBoxLayout(self.bulk_editor_mode_row)
        bulk_editor_mode_layout.setContentsMargins(0, 0, 0, 0)
        bulk_editor_mode_layout.setSpacing(8)
        self.bulk_mode_tags_btn = QPushButton("Tags")
        self.bulk_mode_tags_btn.setObjectName("bulkEditorModeButton")
        self.bulk_mode_tags_btn.setCheckable(True)
        self.bulk_mode_tags_btn.clicked.connect(lambda checked=False: self._set_active_bulk_editor_mode("tags"))
        bulk_editor_mode_layout.addWidget(self.bulk_mode_tags_btn)
        self.bulk_mode_captions_btn = QPushButton("Captions")
        self.bulk_mode_captions_btn.setObjectName("bulkEditorModeButton")
        self.bulk_mode_captions_btn.setCheckable(True)
        self.bulk_mode_captions_btn.clicked.connect(lambda checked=False: self._set_active_bulk_editor_mode("captions"))
        bulk_editor_mode_layout.addWidget(self.bulk_mode_captions_btn)
        bulk_editor_mode_layout.addStretch(1)
        bulk_editor_outer_layout.addWidget(self.bulk_editor_mode_row)

        self.bulk_pages_stack = QStackedWidget(self.bulk_editor_panel)
        self.bulk_pages_stack.setObjectName("bulkEditorPagesStack")
        bulk_editor_outer_layout.addWidget(self.bulk_pages_stack, 1)

        self.bulk_tags_page = QWidget(self.bulk_pages_stack)
        self.bulk_tags_page.setObjectName("bulkTagsPage")
        bulk_tags_page_layout = QVBoxLayout(self.bulk_tags_page)
        bulk_tags_page_layout.setContentsMargins(0, 0, 0, 0)
        bulk_tags_page_layout.setSpacing(0)

        self.bulk_scroll_area = QScrollArea()
        self.bulk_scroll_area.setWidgetResizable(True)
        self.bulk_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.bulk_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bulk_scroll_area.setObjectName("bulkTagEditorScrollArea")
        self.bulk_scroll_area.viewport().installEventFilter(self)

        self.bulk_scroll_container = QWidget(self.bulk_scroll_area)
        self.bulk_scroll_container.setObjectName("bulkTagEditorScrollContainer")
        self.bulk_right_layout = QVBoxLayout(self.bulk_scroll_container)
        self.bulk_right_layout.setContentsMargins(12, 12, 12, 12)
        self.bulk_right_layout.setSpacing(6)

        self.bulk_btn_open_tag_list = QPushButton("Open Tag Lists")
        self.bulk_btn_open_tag_list.setObjectName("bulkBtnOpenTagList")
        self.bulk_btn_open_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_open_tag_list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        bulk_open_font = QFont(self.bulk_btn_open_tag_list.font())
        bulk_open_font.setBold(True)
        self.bulk_btn_open_tag_list.setFont(bulk_open_font)
        self.bulk_btn_open_tag_list.clicked.connect(self._toggle_tag_list_panel)
        self.bulk_right_layout.addWidget(self.bulk_btn_open_tag_list)

        self.bulk_selection_lbl = QLabel("")
        self.bulk_selection_lbl.setObjectName("bulkTagEditorSelectionLabel")
        self.bulk_selection_lbl.setWordWrap(True)
        self.bulk_right_layout.addWidget(self.bulk_selection_lbl)

        self.bulk_btn_select_all_gallery = QPushButton("Select All Files in Gallery")
        self.bulk_btn_select_all_gallery.setObjectName("bulkBtnSelectAllGallery")
        self.bulk_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_btn_select_all_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_select_all_gallery.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_select_all_gallery.clicked.connect(self._select_all_visible_gallery_items)
        self.bulk_right_layout.addWidget(self.bulk_btn_select_all_gallery)

        self.bulk_tags_cap_lbl = QLabel("Tags to add to all selected files:")
        self.bulk_tags_cap_lbl.setObjectName("bulkTagEditorTagsLabel")
        self.bulk_right_layout.addWidget(self.bulk_tags_cap_lbl)

        self.bulk_meta_tags = QLineEdit()
        self.bulk_meta_tags.setObjectName("bulkTagEditorTagsEdit")
        self.bulk_meta_tags.setPlaceholderText("tag1, tag2, tag3")
        self.bulk_meta_tags.editingFinished.connect(self._save_native_tags)
        self.bulk_meta_tags.textChanged.connect(lambda _text: self._refresh_tag_list_rows_state())
        self.bulk_right_layout.addWidget(self.bulk_meta_tags)

        self.bulk_common_tags_toggle = QToolButton()
        self.bulk_common_tags_toggle.setObjectName("bulkTagEditorSectionToggle")
        self.bulk_common_tags_toggle.setText("â–¸ Common Tags")
        self.bulk_common_tags_toggle.setCheckable(True)
        self.bulk_common_tags_toggle.setChecked(False)
        self.bulk_common_tags_toggle.clicked.connect(
            lambda checked: self._toggle_bulk_tag_section(self.bulk_common_tags_toggle, self.bulk_common_tags_text, checked)
        )
        self.bulk_right_layout.addWidget(self.bulk_common_tags_toggle)

        self.bulk_common_tags_text = QPlainTextEdit()
        self.bulk_common_tags_text.setObjectName("bulkTagEditorCommonTagsText")
        self.bulk_common_tags_text.setReadOnly(True)
        self.bulk_common_tags_text.setPlaceholderText("Tags present in all selected files")
        self.bulk_common_tags_text.setMaximumHeight(72)
        self.bulk_common_tags_text.setVisible(False)
        self.bulk_right_layout.addWidget(self.bulk_common_tags_text)

        self.bulk_uncommon_tags_toggle = QToolButton()
        self.bulk_uncommon_tags_toggle.setObjectName("bulkTagEditorSectionToggle")
        self.bulk_uncommon_tags_toggle.setText("â–¸ Uncommon Tags")
        self.bulk_uncommon_tags_toggle.setCheckable(True)
        self.bulk_uncommon_tags_toggle.setChecked(False)
        self.bulk_uncommon_tags_toggle.clicked.connect(
            lambda checked: self._toggle_bulk_tag_section(self.bulk_uncommon_tags_toggle, self.bulk_uncommon_tags_text, checked)
        )
        self.bulk_right_layout.addWidget(self.bulk_uncommon_tags_toggle)

        self.bulk_uncommon_tags_text = QPlainTextEdit()
        self.bulk_uncommon_tags_text.setObjectName("bulkTagEditorUncommonTagsText")
        self.bulk_uncommon_tags_text.setReadOnly(True)
        self.bulk_uncommon_tags_text.setPlaceholderText("Tags present in some, but not all, selected files")
        self.bulk_uncommon_tags_text.setMaximumHeight(96)
        self.bulk_uncommon_tags_text.setVisible(False)
        self.bulk_right_layout.addWidget(self.bulk_uncommon_tags_text)

        self.bulk_selected_files_lbl = QLabel("Selected Files:")
        self.bulk_selected_files_lbl.setObjectName("bulkTagEditorSelectedFilesLabel")
        self.bulk_right_layout.addWidget(self.bulk_selected_files_lbl)

        self.bulk_selected_files_list = BulkSelectedFilesListWidget()
        self.bulk_selected_files_list.setObjectName("bulkSelectedFilesList")
        self.bulk_selected_files_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.bulk_selected_files_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bulk_selected_files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_selected_files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.bulk_selected_files_list.setSpacing(4)
        self.bulk_selected_files_list.setMinimumHeight(120)
        self.bulk_selected_files_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bulk_selected_files_list.setViewportMargins(0, 0, 4, 0)
        self.bulk_selected_files_list.layoutSyncRequested.connect(self._sync_bulk_selected_files_layout)
        self.bulk_selected_files_list.verticalScrollBar().rangeChanged.connect(lambda _min, _max: self._queue_bulk_selected_files_layout_sync())
        self.bulk_right_layout.addWidget(self.bulk_selected_files_list, 1)

        self.bulk_status_lbl = StatusTextEdit("")
        self.bulk_status_lbl.setObjectName("bulkTagEditorStatusLabel")
        self._configure_status_text_widget(self.bulk_status_lbl)
        self.bulk_right_layout.addWidget(self.bulk_status_lbl)

        self.bulk_btn_run_local_ai = QPushButton("Generate Tags for All")
        self.bulk_btn_run_local_ai.setObjectName("bulkBtnRunLocalAI")
        self.bulk_btn_run_local_ai.setProperty("baseText", "Generate Tags for All")
        self.bulk_btn_run_local_ai.setToolTip("Run local AI tag generation for selected files")
        self.bulk_btn_run_local_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_run_local_ai.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_run_local_ai.clicked.connect(self._run_local_ai_tags)
        self.bulk_right_layout.addWidget(self.bulk_btn_run_local_ai)

        self.bulk_btn_save_meta = QPushButton("Save Tags to DB")
        self.bulk_btn_save_meta.setObjectName("bulkBtnSaveMeta")
        self.bulk_btn_save_meta.setProperty("baseText", "Save Tags to DB")
        self.bulk_btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_save_meta.clicked.connect(self._save_native_metadata)
        self.bulk_right_layout.addWidget(self.bulk_btn_save_meta)

        self.bulk_btn_clear_tags = QPushButton("Clear All Tags")
        self.bulk_btn_clear_tags.setObjectName("bulkBtnClearTags")
        self.bulk_btn_clear_tags.setProperty("baseText", "Clear All Tags")
        self.bulk_btn_clear_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_clear_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_clear_tags.clicked.connect(self._clear_bulk_tags)
        self.bulk_right_layout.addWidget(self.bulk_btn_clear_tags)

        self.bulk_btn_save_to_exif = QPushButton("Embed Tags in Files")
        self.bulk_btn_save_to_exif.setObjectName("bulkBtnSaveToExif")
        self.bulk_btn_save_to_exif.setProperty("baseText", "Embed Tags in Files")
        self.bulk_btn_save_to_exif.setToolTip("Write only the entered tags into each selected file's embedded metadata")
        self.bulk_btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_save_to_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_save_to_exif.clicked.connect(self._save_to_exif_cmd)
        self.bulk_right_layout.addWidget(self.bulk_btn_save_to_exif)

        self.bulk_scroll_area.setWidget(self.bulk_scroll_container)
        bulk_tags_page_layout.addWidget(self.bulk_scroll_area)

        self.bulk_captions_page = QWidget(self.bulk_pages_stack)
        self.bulk_captions_page.setObjectName("bulkCaptionsPage")
        bulk_captions_page_layout = QVBoxLayout(self.bulk_captions_page)
        bulk_captions_page_layout.setContentsMargins(0, 0, 0, 0)
        bulk_captions_page_layout.setSpacing(0)

        self.bulk_caption_scroll_area = QScrollArea()
        self.bulk_caption_scroll_area.setWidgetResizable(True)
        self.bulk_caption_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.bulk_caption_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_caption_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bulk_caption_scroll_area.setObjectName("bulkCaptionEditorScrollArea")
        self.bulk_caption_scroll_area.viewport().installEventFilter(self)

        self.bulk_caption_scroll_container = QWidget(self.bulk_caption_scroll_area)
        self.bulk_caption_scroll_container.setObjectName("bulkCaptionEditorScrollContainer")
        self.bulk_caption_right_layout = QVBoxLayout(self.bulk_caption_scroll_container)
        self.bulk_caption_right_layout.setContentsMargins(12, 12, 12, 12)
        self.bulk_caption_right_layout.setSpacing(6)

        self.bulk_caption_selection_lbl = QLabel("")
        self.bulk_caption_selection_lbl.setObjectName("bulkTagEditorSelectionLabel")
        self.bulk_caption_selection_lbl.setWordWrap(True)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selection_lbl)

        self.bulk_caption_btn_select_all_gallery = QPushButton("Select All Files in Gallery")
        self.bulk_caption_btn_select_all_gallery.setObjectName("bulkBtnSelectAllGallery")
        self.bulk_caption_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_caption_btn_select_all_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_select_all_gallery.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_select_all_gallery.clicked.connect(self._select_all_visible_gallery_items)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_select_all_gallery)

        self.bulk_caption_selected_files_lbl = QLabel("Selected Files:")
        self.bulk_caption_selected_files_lbl.setObjectName("bulkTagEditorSelectedFilesLabel")
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selected_files_lbl)

        self.bulk_caption_selected_files_list = BulkSelectedFilesListWidget()
        self.bulk_caption_selected_files_list.setObjectName("bulkSelectedFilesList")
        self.bulk_caption_selected_files_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.bulk_caption_selected_files_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bulk_caption_selected_files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_caption_selected_files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.bulk_caption_selected_files_list.setSpacing(4)
        self.bulk_caption_selected_files_list.setMinimumHeight(120)
        self.bulk_caption_selected_files_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bulk_caption_selected_files_list.setViewportMargins(0, 0, 4, 0)
        self.bulk_caption_selected_files_list.layoutSyncRequested.connect(self._sync_bulk_caption_selected_files_layout)
        self.bulk_caption_selected_files_list.verticalScrollBar().rangeChanged.connect(lambda _min, _max: self._queue_bulk_caption_selected_files_layout_sync())
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selected_files_list, 1)

        self.bulk_caption_status_lbl = StatusTextEdit("")
        self.bulk_caption_status_lbl.setObjectName("bulkTagEditorStatusLabel")
        self._configure_status_text_widget(self.bulk_caption_status_lbl)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_status_lbl)

        self.bulk_caption_btn_run_local_ai = QPushButton("Generate Descriptions for All")
        self.bulk_caption_btn_run_local_ai.setObjectName("bulkBtnRunLocalAI")
        self.bulk_caption_btn_run_local_ai.setProperty("baseText", "Generate Descriptions for All")
        self.bulk_caption_btn_run_local_ai.setToolTip("Run local AI description generation for selected files")
        self.bulk_caption_btn_run_local_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_run_local_ai.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_run_local_ai.clicked.connect(self._run_local_ai_description)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_run_local_ai)

        self.bulk_caption_btn_save_meta = QPushButton("Save Descriptions to DB")
        self.bulk_caption_btn_save_meta.setObjectName("bulkBtnSaveMeta")
        self.bulk_caption_btn_save_meta.setProperty("baseText", "Save Descriptions to DB")
        self.bulk_caption_btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_save_meta.clicked.connect(self._save_bulk_descriptions_to_db)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_save_meta)

        self.bulk_caption_btn_clear = QPushButton("Clear Descriptions from DB")
        self.bulk_caption_btn_clear.setObjectName("bulkBtnClearTags")
        self.bulk_caption_btn_clear.setProperty("baseText", "Clear Descriptions from DB")
        self.bulk_caption_btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_clear.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_clear.clicked.connect(self._clear_bulk_descriptions)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_clear)

        self.bulk_caption_scroll_area.setWidget(self.bulk_caption_scroll_container)
        bulk_captions_page_layout.addWidget(self.bulk_caption_scroll_area)

        self.bulk_pages_stack.addWidget(self.bulk_tags_page)
        self.bulk_pages_stack.addWidget(self.bulk_captions_page)

        self.right_workspace_stack.addWidget(self.details_workspace)
        self.right_workspace_stack.addWidget(self.bulk_editor_panel)
        self.right_workspace_stack.setCurrentWidget(self.details_workspace)
        self._bulk_editor_mode = "tags"
        self._set_active_bulk_editor_mode("tags")
        self._sync_close_button_icons()
        self._sync_sidebar_panel_widths()

        self._update_native_styles(accent_val)
        self._update_splitter_style(accent_val)

        self._devtools: QWebEngineView | None = None
        self.video_overlay = LightboxVideoOverlay(parent=self.web)
        self.video_overlay.setGeometry(self.web.rect())
        # When native overlay closes, also close the web lightbox chrome.
        self.video_overlay.on_close = self._close_web_lightbox
        self.video_overlay.on_prev = self._on_video_prev
        self.video_overlay.on_next = self._on_video_next
        self.video_overlay.on_log = self.bridge._log
        self.video_overlay.raise_()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)
        try:
            self.web.page().renderProcessTerminated.connect(
                lambda status, exit_code: self.bridge._log(
                    f"Web render process terminated: status={status} exit_code={int(exit_code)}"
                )
            )
        except Exception:
            pass

        index_path = Path(__file__).with_name("web") / "index.html"

        # Web loading signals (with minimum on-screen time to avoid flashing)
        self._web_loading_shown_ms: int | None = None
        self._web_loading_min_ms = 1000
        self.web.loadStarted.connect(lambda: self._set_web_loading(True))
        self.web.loadProgress.connect(self._on_web_load_progress)
        self.web.loadFinished.connect(lambda _ok: self._set_web_loading(False))
        self.web.loadFinished.connect(
            lambda ok: self.bridge._log(
                f"Web load finished: ok={bool(ok)} url={self.web.url().toString()}"
            )
        )

        self.web.setUrl(QUrl.fromLocalFile(str(index_path.resolve())))

        self.bottom_panel = QWidget(center_splitter)
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setMinimumHeight(0)
        self.bottom_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(14, 10, 14, 14)
        bottom_layout.setSpacing(10)

        self.bottom_panel_header_row = QWidget(self.bottom_panel)
        bottom_panel_header_layout = QHBoxLayout(self.bottom_panel_header_row)
        bottom_panel_header_layout.setContentsMargins(0, 0, 0, 0)
        bottom_panel_header_layout.setSpacing(8)

        self.bottom_panel_prev_group_btn = QPushButton("â†Previous Group")
        self.bottom_panel_prev_group_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_prev_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_prev_group_btn.setToolTip("Jump to Previous Group")
        self.bottom_panel_prev_group_btn.setFixedHeight(22)
        self.bottom_panel_prev_group_btn.clicked.connect(lambda: self._jump_review_group(-1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_prev_group_btn, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_header = QLabel("Image Comparison")
        self.bottom_panel_header.setObjectName("bottomPanelHeader")
        self.bottom_panel_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addWidget(self.bottom_panel_header, 0, Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_next_group_btn = QPushButton("Next Groupâ†’")
        self.bottom_panel_next_group_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_next_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_next_group_btn.setToolTip("Jump to Next Group")
        self.bottom_panel_next_group_btn.setFixedHeight(22)
        self.bottom_panel_next_group_btn.clicked.connect(lambda: self._jump_review_group(1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_next_group_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_close_btn = QPushButton("")
        self.bottom_panel_close_btn.setObjectName("bottomPanelCloseButton")
        self.bottom_panel_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_close_btn.setFixedSize(22, 22)
        self.bottom_panel_close_btn.clicked.connect(lambda: self.bridge.set_setting_bool("ui.show_bottom_panel", False))
        bottom_panel_header_layout.addWidget(self.bottom_panel_close_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addWidget(self.bottom_panel_header_row)

        self.compare_panel = ComparePanel(self.bridge, self.bottom_panel)
        bottom_layout.addWidget(self.compare_panel, 1)
        self._apply_compare_panel_theme(accent_val)

        center_splitter.addWidget(center)
        center_splitter.addWidget(self.bottom_panel)
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 0)
        center_container_layout.addWidget(center_splitter)

        splitter.addWidget(self.left_panel)
        splitter.addWidget(center_container)

        self.right_splitter.addWidget(self.tag_list_panel)
        self.right_splitter.addWidget(self.right_panel)
        self.right_splitter.setStretchFactor(0, 0)
        self.right_splitter.setStretchFactor(1, 1)

        splitter.addWidget(self.right_panel_host)
        splitter.setStretchFactor(1, 1)
        splitter.setObjectName("mainSplitter")
        splitter.setMouseTracking(True)
        splitter.setHandleWidth(7)

        self._restore_main_splitter_sizes()
        self._restore_center_splitter_sizes()
        self._restore_right_splitter_sizes()

        splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())
        center_splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())
        self.right_splitter.splitterMoved.connect(lambda *args: self._on_right_splitter_moved())

        self.setCentralWidget(splitter)

        # Apply initial style
        self._update_splitter_style(accent_val)

        # Apply right panel flag from settings
        try:
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            self._apply_ui_flag("ui.show_right_panel", show_right)
        except Exception:
            pass
        try:
            show_bottom = bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool))
            self._apply_ui_flag("ui.show_bottom_panel", show_bottom)
        except Exception:
            pass

        # Initial clear/hide based on default settings
        # Must be at the very end to ensure all UI attributes (meta_desc, etc.) are initialized.
        self._setup_metadata_layout()
        self._reload_tag_lists()
        self._sync_tag_list_panel_visibility()
        self._update_preview_visibility()
        self._clear_metadata_panel()
        self._gallery_relayout_timer = QTimer(self)
        self._gallery_relayout_timer.setSingleShot(True)
        self._gallery_relayout_timer.setInterval(90)
        self._gallery_relayout_timer.timeout.connect(self._notify_gallery_container_resized)
        QTimer.singleShot(0, self._apply_initial_web_background)
        QTimer.singleShot(0, self._schedule_gallery_container_relayout)

    def _apply_initial_web_background(self) -> None:
        # Some Windows installs abort inside Qt WebEngine if this runs during
        # synchronous layout construction. Defer it until the event loop starts.
        try:
            page = self.web.page()
            if page is None:
                self.bridge._log("Web background skipped: page unavailable")
                return
            accent_q = QColor(self._current_accent)
            page.setBackgroundColor(QColor(Theme.get_bg(accent_q)))
            self.bridge._log("Web background applied")
        except Exception as exc:
            self.bridge._log(f"Web background apply failed: {exc}")

    def _schedule_gallery_container_relayout(self, delay_ms: int = 90) -> None:
        timer = getattr(self, "_gallery_relayout_timer", None)
        if timer is None:
            return
        try:
            timer.start(max(0, int(delay_ms or 0)))
        except Exception:
            pass

    def _notify_gallery_container_resized(self) -> None:
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_scheduleGalleryRelayout && window.__mmx_scheduleGalleryRelayout('qt'); }catch(e){}"
            )
        except Exception:
            pass

    def _set_selected_folders(self, folder_paths: list[str]) -> None:
        self.bridge.set_selected_folders(folder_paths)

    def _get_saved_panel_width(self, qkey: str, default: int) -> int:
        try:
            val = int(self.bridge.settings.value(qkey, default, type=int) or default)
        except Exception:
            val = default
        return max(120, val)

    def _get_saved_panel_height(self, qkey: str, default: int) -> int:
        try:
            val = int(self.bridge.settings.value(qkey, default, type=int) or default)
        except Exception:
            val = default
        return max(140, val)

    def _current_splitter_sizes(self) -> list[int]:
        try:
            sizes = [int(v) for v in self.splitter.sizes()]
        except Exception:
            sizes = []
        if len(sizes) < 3:
            return [
                self._DEFAULT_LEFT_PANEL_WIDTH,
                self._DEFAULT_CENTER_WIDTH,
                self._DEFAULT_RIGHT_PANEL_WIDTH,
            ]
        return sizes[:3]

    def _save_main_panel_widths(self) -> None:
        try:
            sizes = self._current_splitter_sizes()
            if self.left_panel.isVisible() and sizes[0] > 0:
                self.bridge.settings.setValue("ui/left_panel_width", int(sizes[0]))
            if self.right_panel_host.isVisible():
                self.bridge.settings.setValue("ui/right_panel_width", int(self._details_panel_width_without_tag_list()))
        except Exception:
            pass

    def _save_bottom_panel_height(self) -> None:
        try:
            if not hasattr(self, "center_splitter") or not hasattr(self, "bottom_panel"):
                return
            sizes = [int(v) for v in self.center_splitter.sizes()]
            if len(sizes) >= 2 and self.bottom_panel.isVisible() and sizes[1] > 0:
                self.bridge.settings.setValue("ui/bottom_panel_height", int(sizes[1]))
        except Exception:
            pass

    def _restore_main_splitter_sizes(self) -> None:
        try:
            show_left = bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool))
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            left_width = self._get_saved_panel_width("ui/left_panel_width", self._DEFAULT_LEFT_PANEL_WIDTH)
            right_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
            sizes = [
                left_width if show_left else 0,
                self._DEFAULT_CENTER_WIDTH,
                right_width if show_right else 0,
            ]
            self.splitter.setSizes(sizes)
        except Exception:
            pass

    def _restore_center_splitter_sizes(self) -> None:
        try:
            show_bottom = bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool))
            bottom_height = self._get_saved_panel_height("ui/bottom_panel_height", self._DEFAULT_BOTTOM_PANEL_HEIGHT)
            sizes = [
                self._DEFAULT_CENTER_WIDTH,
                bottom_height if show_bottom else 0,
            ]
            self.center_splitter.setSizes(sizes)
        except Exception:
            pass

    def _current_right_splitter_sizes(self) -> list[int]:
        try:
            sizes = [int(v) for v in self.right_splitter.sizes()]
        except Exception:
            sizes = []
        if len(sizes) < 2:
            return [0, self._DEFAULT_RIGHT_PANEL_WIDTH]
        return sizes[:2]

    def _save_tag_list_panel_width(self) -> None:
        try:
            sizes = self._current_right_splitter_sizes()
            if self.tag_list_panel.isVisible() and sizes[0] > 0:
                self.bridge.settings.setValue("ui/tag_list_panel_width", int(sizes[0]))
        except Exception:
            pass

    def _restore_right_splitter_sizes(self) -> None:
        try:
            saved_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH), type=int) or self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)))
            details_width = saved_details_width
            tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
            show_tag_list = bool(self.bridge.settings.value("ui/show_tag_list_panel", False, type=bool)) and self._can_show_tag_list_panel()
            self.tag_list_panel.setVisible(show_tag_list)
            if show_tag_list:
                self.right_splitter.setSizes([tag_width, details_width])
            else:
                self.right_splitter.setSizes([0, details_width])
        except Exception:
            pass

    def _details_panel_width_without_tag_list(self) -> int:
        try:
            if hasattr(self, "right_panel") and self.right_panel.width() > 0:
                return max(240, int(self.right_panel.width()))
            if hasattr(self, "right_splitter") and self.tag_list_panel.isVisible():
                sizes = self._current_right_splitter_sizes()
                if len(sizes) >= 2 and sizes[1] > 0:
                    return max(240, int(sizes[1]))
        except Exception:
            pass
        return max(240, int(self.right_panel_host.width() or self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)))

    def _resize_window_for_tag_list_visibility(self, show: bool) -> None:
        if not hasattr(self, "splitter"):
            return
        sizes = self._current_splitter_sizes()
        if len(sizes) < 3:
            return
        tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
        if show:
            if not hasattr(self, "_tag_list_prev_main_sizes") or not isinstance(getattr(self, "_tag_list_prev_main_sizes", None), list):
                self._tag_list_prev_main_sizes = [int(v) for v in sizes[:3]]

            saved_hidden_details_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
            saved_tag_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", saved_hidden_details_width, type=int) or saved_hidden_details_width))
            current_details_width = max(240, self._details_panel_width_without_tag_list())
            baseline_details_width = saved_tag_details_width if self.tag_list_panel.isVisible() else saved_hidden_details_width
            details_width = max(baseline_details_width, current_details_width)
            self.bridge.settings.setValue("ui/tag_list_last_details_width", details_width)
            desired_right_width = details_width + tag_width
            current_right_width = max(0, int(sizes[2]))
            needed_extra = max(0, desired_right_width - current_right_width)
            left_width = int(sizes[0])
            center_width = int(sizes[1])
            right_width = current_right_width + needed_extra
            remaining_extra = needed_extra
            if remaining_extra > 0:
                center_shrink = min(max(0, center_width - 120), remaining_extra)
                center_width -= center_shrink
                remaining_extra -= center_shrink
            if remaining_extra > 0:
                left_shrink = min(max(0, left_width - 120), remaining_extra)
                left_width -= left_shrink
                remaining_extra -= left_shrink
            if remaining_extra > 0:
                right_width -= remaining_extra

            self.splitter.setSizes([left_width, center_width, right_width])
            self.tag_list_panel.setVisible(True)
            self.right_splitter.setSizes([tag_width, details_width])
            return

        prev_main_sizes = getattr(self, "_tag_list_prev_main_sizes", None)
        details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._DEFAULT_RIGHT_PANEL_WIDTH, type=int) or self._DEFAULT_RIGHT_PANEL_WIDTH))
        if isinstance(prev_main_sizes, list) and len(prev_main_sizes) >= 3:
            self.splitter.setSizes([int(prev_main_sizes[0]), int(prev_main_sizes[1]), int(prev_main_sizes[2])])
        else:
            current_sizes = self._current_splitter_sizes()
            if len(current_sizes) >= 3:
                left_width = int(current_sizes[0])
                center_width = int(current_sizes[1])
                right_width = int(current_sizes[2])
                target_right_width = max(240, details_width)
                released_width = max(0, right_width - target_right_width)
                if released_width > 0:
                    center_width += released_width
                right_width = target_right_width
                self.splitter.setSizes([left_width, center_width, right_width])
        self.tag_list_panel.setVisible(False)
        self.right_splitter.setSizes([0, details_width])
        self._tag_list_prev_main_sizes = None

    def _is_tag_list_panel_requested_visible(self) -> bool:
        try:
            return bool(self.bridge.settings.value("ui/show_tag_list_panel", False, type=bool))
        except Exception:
            return False

    def _update_tag_list_toggle_controls(self, visible: bool | None = None) -> None:
        is_visible = self.tag_list_panel.isVisible() if visible is None else bool(visible)
        if hasattr(self, "btn_open_tag_list"):
            self.btn_open_tag_list.setText("Close Tag List" if is_visible else "Open Tag List")
            self.btn_open_tag_list.setEnabled(bool(hasattr(self, "tag_list_open_btn_row") and self.tag_list_open_btn_row.isVisible()))
        if hasattr(self, "bulk_btn_open_tag_list"):
            self.bulk_btn_open_tag_list.setText("Close Tag Lists" if is_visible else "Open Tag Lists")
            self.bulk_btn_open_tag_list.setEnabled(True)
        if hasattr(self, "act_toggle_tag_list_panel"):
            self.act_toggle_tag_list_panel.blockSignals(True)
            self.act_toggle_tag_list_panel.setChecked(is_visible)
            self.act_toggle_tag_list_panel.blockSignals(False)
            self.act_toggle_tag_list_panel.setEnabled(True)

    def _set_tag_list_panel_requested_visible(self, visible: bool) -> None:
        self.bridge.settings.setValue("ui/show_tag_list_panel", bool(visible))
        self._sync_tag_list_panel_visibility()

    def _toggle_tag_list_panel(self) -> None:
        self._set_tag_list_panel_requested_visible(not self.tag_list_panel.isVisible())

    def _toggle_tag_list_panel_from_menu(self, checked: bool) -> None:
        if checked and not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
            self.bridge.settings.setValue("ui/show_right_panel", True)
            self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        self._set_tag_list_panel_requested_visible(bool(checked))

    def _can_show_tag_list_panel(self) -> bool:
        return bool(hasattr(self, "right_panel_host") and self.right_panel_host.isVisible())

    def _sync_tag_list_panel_visibility(self, refresh_contents: bool = True) -> None:
        if not hasattr(self, "tag_list_panel"):
            return
        should_show = self._is_tag_list_panel_requested_visible() and self._can_show_tag_list_panel()
        if not should_show:
            self._save_tag_list_panel_width()
        was_visible = self.tag_list_panel.isVisible()
        saved_hidden_details_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
        saved_tag_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", saved_hidden_details_width, type=int) or saved_hidden_details_width))
        tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
        desired_right_width = saved_tag_details_width + tag_width
        current_right_width = max(0, int(self._current_splitter_sizes()[2] if hasattr(self, "splitter") else 0))
        needs_outer_resize = should_show and current_right_width < max(240, desired_right_width - 2)
        if should_show and (not was_visible or needs_outer_resize):
            if not was_visible:
                self.bridge.settings.setValue("ui/tag_list_last_details_width", max(saved_hidden_details_width, self._details_panel_width_without_tag_list()))
            self._resize_window_for_tag_list_visibility(True)
        elif not should_show and was_visible:
            self._resize_window_for_tag_list_visibility(False)
        self.tag_list_panel.setVisible(should_show)
        if should_show:
            self._restore_right_splitter_sizes()
            if refresh_contents:
                if was_visible:
                    self._refresh_tag_list_rows_state()
                else:
                    self._refresh_tag_list_panel()
        elif hasattr(self, "right_splitter"):
            details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._DEFAULT_RIGHT_PANEL_WIDTH, type=int) or self._DEFAULT_RIGHT_PANEL_WIDTH))
            self.right_splitter.setSizes([0, details_width])
        self._update_tag_list_toggle_controls(should_show)

    def _open_tag_list_panel(self) -> None:
        self._set_tag_list_panel_requested_visible(True)

    def _close_tag_list_panel(self) -> None:
        self._save_tag_list_panel_width()
        self._set_tag_list_panel_requested_visible(False)

    def _update_navigation_state(self) -> None:
        self.bridge._can_nav_back = self._folder_history_index > 0
        self.bridge._can_nav_forward = 0 <= self._folder_history_index < (len(self._folder_history) - 1)
        self.bridge.emit_navigation_state()

    def _sync_tree_to_folder(self, path_str: str) -> None:
        if not path_str:
            return
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(path_str))
        self._suppress_tree_selection_history = True
        try:
            if root_idx.isValid():
                selection_model = self.tree.selectionModel()
                if selection_model is not None:
                    selection_model.clearSelection()
                    selection_model.setCurrentIndex(
                        root_idx,
                        QItemSelectionModel.SelectionFlag.ClearAndSelect
                        | QItemSelectionModel.SelectionFlag.Rows
                        | QItemSelectionModel.SelectionFlag.Current,
                    )
                else:
                    self.tree.setCurrentIndex(root_idx)
                self.tree.scrollTo(root_idx)
                self.tree.expand(root_idx)
        finally:
            self._suppress_tree_selection_history = False

    def _queue_tree_sync(self, path_str: str, *, re_root_tree: bool = False) -> None:
        if not path_str:
            return
        self._suspend_tree_auto_reveal = False
        self._pending_tree_sync_path = str(path_str)
        self._pending_tree_reroot = self._pending_tree_reroot or bool(re_root_tree)
        if not self.left_panel.isVisible():
            return
        self._tree_sync_timer.start(0)

    def _apply_pending_tree_sync(self) -> None:
        path_str = str(self._pending_tree_sync_path or "")
        re_root_tree = bool(self._pending_tree_reroot)
        self._pending_tree_sync_path = ""
        self._pending_tree_reroot = False
        if not path_str or not self.left_panel.isVisible():
            return
        self._suppress_tree_selection_history = True
        try:
            if re_root_tree or not self._tree_root_path:
                self._set_tree_root(path_str)
            self._sync_tree_to_folder(path_str)
        except Exception as exc:
            self.bridge._log(f"Tree sync failed for {path_str}: {exc}")
        finally:
            self._suppress_tree_selection_history = False

    def _set_tree_root(self, folder_path: str) -> None:
        if not folder_path:
            return
        p = Path(folder_path)
        path_str = str(p.absolute())
        self._tree_root_path = path_str
        self.proxy_model.setRootPath(path_str)

        root_parent = p.parent
        parent_idx = self.fs_model.setRootPath(str(root_parent))
        self.tree.setRootIndex(self.proxy_model.mapFromSource(parent_idx))

        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(path_str))
        if root_idx.isValid():
            self.tree.expand(root_idx)
        self._sync_pinned_selection_to_root()

    def _tree_needs_reroot_for_path(self, folder_path: str) -> bool:
        path_str = str(folder_path or "").strip()
        current_root = str(self._tree_root_path or "").strip()
        if not path_str or not current_root:
            return True
        try:
            from app.mediamanager.utils.pathing import normalize_windows_path
            norm_target = normalize_windows_path(path_str).rstrip("/")
            norm_root = normalize_windows_path(current_root).rstrip("/")
        except Exception:
            norm_target = path_str.replace("\\", "/").rstrip("/").lower()
            norm_root = current_root.replace("\\", "/").rstrip("/").lower()
        if not norm_target or not norm_root:
            return True
        if norm_target == norm_root:
            return False
        return not norm_target.startswith(norm_root + "/")

    def _navigate_to_folder(self, folder_path: str, *, record_history: bool = True, refresh: bool = False, re_root_tree: bool = False) -> None:
        if not folder_path:
            return
        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            QMessageBox.warning(self, "Invalid Folder", f"The folder does not exist:\n{folder_path}")
            return

        path_str = str(p.absolute())
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        is_new_target = path_str != current_path
        re_root_tree = bool(re_root_tree or self._tree_needs_reroot_for_path(path_str))

        if is_new_target or refresh:
            self._set_selected_folders([path_str])
            if refresh and not is_new_target:
                self.bridge.selectionChanged.emit([path_str])
        self._queue_tree_sync(path_str, re_root_tree=re_root_tree)

        if record_history:
            if self._folder_history_index >= 0 and self._folder_history[self._folder_history_index] == path_str:
                pass
            else:
                if self._folder_history_index < len(self._folder_history) - 1:
                    self._folder_history = self._folder_history[: self._folder_history_index + 1]
                self._folder_history.append(path_str)
                self._folder_history_index = len(self._folder_history) - 1
        self._update_navigation_state()

    def _on_load_folder_requested(self, folder_path: str) -> None:
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)

    def _load_drag_source_pixmap(self, path_str: str) -> QPixmap:
        source_pixmap = QPixmap()
        if path_str:
            try:
                p = Path(path_str)
                if p.exists():
                    candidates: list[Path] = [p]
                    poster = self.bridge._ensure_video_poster(p)
                    if poster and poster.exists() and poster not in candidates:
                        candidates.append(poster)

                    for candidate in candidates:
                        source_pixmap = QPixmap(str(candidate))
                        if not source_pixmap.isNull():
                            break
                        reader = QImageReader(str(candidate))
                        img = reader.read()
                        if not img.isNull():
                            source_pixmap = QPixmap.fromImage(img)
                            break
            except Exception:
                source_pixmap = QPixmap()

        if source_pixmap.isNull():
            provider = QFileIconProvider()
            source_pixmap = provider.icon(QFileIconProvider.IconType.File).pixmap(QSize(64, 64))
        return source_pixmap

    def _scaled_drag_preview_pixmap(self, path_str: str, preferred_width: int = 0, preferred_height: int = 0) -> QPixmap:
        max_preview = 100
        source_pixmap = self._load_drag_source_pixmap(path_str)
        src_w = int(preferred_width or source_pixmap.width() or max_preview)
        src_h = int(preferred_height or source_pixmap.height() or max_preview)
        if src_w <= 0:
            src_w = max_preview
        if src_h <= 0:
            src_h = max_preview
        scale = min(max_preview / src_w, max_preview / src_h, 1.0)
        draw_w = max(1, int(round(src_w * scale)))
        draw_h = max(1, int(round(src_h * scale)))
        return source_pixmap.scaled(draw_w, draw_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _build_drag_preview_pixmap(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> QPixmap:
        clean_paths = [str(Path(p).absolute()) for p in (paths or []) if p]
        if not clean_paths and preview_path:
            clean_paths = [str(Path(preview_path).absolute())]
        if not clean_paths:
            return QPixmap()

        stack_paths: list[str] = []
        for candidate in [preview_path, *clean_paths]:
            if candidate and candidate not in stack_paths:
                stack_paths.append(candidate)
            if len(stack_paths) >= 3:
                break

        layered: list[tuple[QPixmap, int, int]] = []
        spread = 14
        max_w = 0
        max_h = 0
        back_to_front = list(reversed(stack_paths))
        layer_count = len(back_to_front)
        for idx, candidate in enumerate(back_to_front):
            preferred_w = preview_width if candidate == preview_path else 0
            preferred_h = preview_height if candidate == preview_path else 0
            pixmap = self._scaled_drag_preview_pixmap(candidate, preferred_w, preferred_h)
            x = (layer_count - 1 - idx) * spread
            y = idx * spread
            layered.append((pixmap, x, y))
            max_w = max(max_w, x + pixmap.width())
            max_h = max(max_h, y + pixmap.height())

        canvas = QPixmap(max_w, max_h)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        for pixmap, x, y in layered:
            painter.drawPixmap(x, y, pixmap)
        painter.end()
        return canvas

    def _start_native_gallery_drag(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> None:
        clean_paths = [str(Path(p).absolute()) for p in (paths or []) if p]
        if not clean_paths:
            return

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in clean_paths])
        mime.setText("\n".join(clean_paths))

        drag = QDrag(self.web)
        drag.setMimeData(mime)
        preview_pixmap = self._build_drag_preview_pixmap(clean_paths, preview_path, preview_width, preview_height)
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.set_preview_pixmap(preview_pixmap)
        empty_drag = QPixmap(1, 1)
        empty_drag.fill(Qt.GlobalColor.transparent)
        drag.setPixmap(empty_drag)
        drag.setHotSpot(QPoint(0, 0))

        try:
            self.bridge.drag_target_folder = ""
            drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        finally:
            self.bridge.drag_target_folder = ""
            if hasattr(self, "native_tooltip"):
                self.native_tooltip.set_preview_pixmap(None)
            self.bridge.hide_drag_tooltip()
            self.bridge.set_drag_paths([])
            self.bridge.nativeDragFinished.emit()

    def show_recycle_bin_viewer(self):
        try:
            from native.mediamanagerx_app.recycle_bin import RecycleBinViewerWindow
            self.recycle_bin_viewer = RecycleBinViewerWindow(self)
            self.recycle_bin_viewer.show()
            self.recycle_bin_viewer.raise_()
            self.recycle_bin_viewer.activateWindow()
        except Exception as e:
            print("Failed to open recycle bin viewer:", e)

    def _on_navigate_to_folder_requested(self, folder_path: str) -> None:
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=False)

    def _navigate_back(self) -> None:
        if self._folder_history_index <= 0:
            self._update_navigation_state()
            return
        self._folder_history_index -= 1
        self._navigate_to_folder(self._folder_history[self._folder_history_index], record_history=False)

    def _navigate_forward(self) -> None:
        if self._folder_history_index >= len(self._folder_history) - 1:
            self._update_navigation_state()
            return
        self._folder_history_index += 1
        self._navigate_to_folder(self._folder_history[self._folder_history_index], record_history=False)

    def _navigate_up(self) -> None:
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if not current_path:
            self._update_navigation_state()
            return
        current = Path(current_path)
        parent = current.parent
        if str(parent) == str(current):
            self._update_navigation_state()
            return
        self._navigate_to_folder(str(parent), record_history=True)

    def _refresh_current_folder(self) -> None:
        self.bridge._invalidate_scan_caches()
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if not current_path:
            self._update_navigation_state()
            return
        self._navigate_to_folder(current_path, record_history=False, refresh=True)

    def _on_directory_loaded(self, path: str) -> None:
        """Triggered when QFileSystemModel finishes loading a directory's contents."""
        self.bridge._log(f"Tree: Directory loaded: {path}")
        self._suppress_tree_selection_history = True
        try:
            self._on_directory_loaded_impl(path)
        finally:
            self._suppress_tree_selection_history = False

    def _on_directory_loaded_impl(self, path: str) -> None:
        self.proxy_model.invalidate()
        
        # If the tree's root index is still invalid, try to fix it now
        if not self.tree.rootIndex().isValid():
            root_path_str = self.proxy_model._root_path
            root_parent = Path(root_path_str).parent
            parent_idx = self.fs_model.index(str(root_parent))
            
            self.bridge._log(f"Tree: Late loading check - parent_idx valid={parent_idx.isValid()} for {root_parent}")
            
            if parent_idx.isValid():
                proxy_idx = self.proxy_model.mapFromSource(parent_idx)
                if proxy_idx.isValid():
                    self.bridge._log(f"Tree: Setting root index from directoryLoaded (late load success) for {root_parent}")
                    self.tree.setRootIndex(proxy_idx)
                else:
                    self.bridge._log(f"Tree: Proxy index still invalid for {root_parent}")
        
        # Also ensure the actual root is expanded
        root_path_str = self.proxy_model._root_path
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(root_path_str))
        if root_idx.isValid():
            if not self.tree.isExpanded(root_idx):
                self.bridge._log(f"Tree: Expanding root index for {root_path_str}")
                self.tree.expand(root_idx)
        else:
            # Try with normalized path if exact match fails
            norm_root = root_path_str.rstrip("/")
            root_idx = self.proxy_model.mapFromSource(self.fs_model.index(norm_root))
            if root_idx.isValid() and not self.tree.isExpanded(root_idx):
                self.bridge._log(f"Tree: Expanding root index (normalized) for {norm_root}")
                self.tree.expand(root_idx)

        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if current_path and not self._suspend_tree_auto_reveal:
            try:
                self._sync_tree_to_folder(current_path)
                self.tree.viewport().update()
            except Exception as exc:
                self.bridge._log(f"Tree current-folder sync failed after directory load: {exc}")

    def _on_tree_selection(self, *_args) -> None:
        if self._suppress_tree_selection_history:
            return
        self._suspend_tree_auto_reveal = False
        selection_model = self.tree.selectionModel()
        selected_indices = selection_model.selectedRows()
        
        paths = []
        for idx in selected_indices:
            if idx.isValid():
                source_idx = self.proxy_model.mapToSource(idx)
                path = self.fs_model.filePath(source_idx)
                if path:
                    paths.append(path)
        
        if paths:
            if hasattr(self, "collections_list"):
                self.collections_list.blockSignals(True)
                self.collections_list.clearSelection()
                self.collections_list.blockSignals(False)
            if hasattr(self, "smart_collections_list"):
                self.smart_collections_list.blockSignals(True)
                self.smart_collections_list.clearSelection()
                self.smart_collections_list.blockSignals(False)
            if len(paths) == 1:
                self._navigate_to_folder(paths[0], record_history=True)
            else:
                self._set_selected_folders(paths)
                self._update_navigation_state()

    def _reload_pinned_folders(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        try:
            pinned_folders = self.bridge.list_pinned_folders()
        except Exception:
            pinned_folders = []

        current_root = str(self._tree_root_path or "")
        current_root_key = current_root.replace("\\", "/").lower()
        show_hidden = self.bridge._show_hidden_enabled()

        self.pinned_folders_list.blockSignals(True)
        self.pinned_folders_list.clear()
        for folder_path in pinned_folders:
            path_str = str(folder_path or "").strip()
            if not path_str:
                continue
            is_hidden = self.bridge.repo.is_path_hidden(path_str)
            if is_hidden and not show_hidden:
                continue
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, path_str)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(is_hidden))
            item.setToolTip(path_str)
            self.pinned_folders_list.addItem(item)
            row_widget = self._build_pinned_folder_item_widget(path_str, is_hidden=is_hidden)
            item.setSizeHint(row_widget.sizeHint())
            self.pinned_folders_list.setItemWidget(item, row_widget)
            if path_str.replace("\\", "/").lower() == current_root_key:
                item.setSelected(True)
                self.pinned_folders_list.setCurrentItem(item)
                self._set_pinned_folder_row_selected(row_widget, True)
        self.pinned_folders_list.blockSignals(False)

    def _build_pinned_folder_item_widget(self, folder_path: str, *, is_hidden: bool = False) -> QWidget:
        row = QWidget()
        row.setObjectName("pinnedFolderRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        provider = QFileIconProvider()
        folder_icon = provider.icon(QFileIconProvider.IconType.Folder)

        icon_label = QLabel()
        icon_label.setObjectName("pinnedFolderIcon")
        folder_pixmap = folder_icon.pixmap(QSize(16, 16))
        icon_label.setPixmap(folder_pixmap)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_label = QLabel(Path(folder_path).name or folder_path)
        text_label.setObjectName("pinnedFolderText")
        text_label.setToolTip(folder_path)
        layout.addWidget(text_label, 1)

        pin_label = QLabel()
        pin_label.setObjectName("pinnedFolderPin")
        pin_label.setPixmap(self._create_pinned_icon_pixmap())
        pin_label.setToolTip("Pinned folder")
        layout.addWidget(pin_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        item_height = max(28, row.sizeHint().height())
        row.setMinimumHeight(item_height)
        row.setProperty("folderPixmap", folder_pixmap)
        row.setProperty("iconLabel", icon_label)
        row.setProperty("textLabel", text_label)
        row.setProperty("pinLabel", pin_label)
        row.setProperty("hidden", bool(is_hidden))
        text_label.setProperty("hidden", bool(is_hidden))
        icon_label.setProperty("hidden", bool(is_hidden))
        pin_label.setProperty("hidden", bool(is_hidden))
        if is_hidden:
            row.setToolTip(f"{folder_path}\nHidden")
            pin_label.setToolTip("Pinned folder\nHidden")
        self._set_pinned_folder_row_selected(row, False)
        return row

    def _set_pinned_folder_row_selected(self, row: QWidget, selected: bool) -> None:
        if row is None:
            return

        row.setProperty("selected", bool(selected))

        text_label = row.property("textLabel")
        if isinstance(text_label, QLabel):
            text_label.setProperty("selected", bool(selected))
            font = text_label.font()
            font.setBold(bool(selected))
            text_label.setFont(font)
            text_label.style().unpolish(text_label)
            text_label.style().polish(text_label)

        icon_label = row.property("iconLabel")
        folder_pixmap = row.property("folderPixmap")
        if isinstance(icon_label, QLabel) and isinstance(folder_pixmap, QPixmap):
            icon_label.setPixmap(folder_pixmap)
            icon_label.setProperty("selected", bool(selected))
            icon_label.style().unpolish(icon_label)
            icon_label.style().polish(icon_label)

        row.style().unpolish(row)
        row.style().polish(row)
        row.update()

    def _create_pinned_icon_pixmap(self, size: int = 14) -> QPixmap:
        asset_path = Path(__file__).with_name("web") / "icons" / "pin.svg"
        renderer = QSvgRenderer(str(asset_path))
        if not renderer.isValid():
            return QPixmap()

        logical_size = max(16, size + 2)
        device_pixel_ratio = 2.0
        canvas_size = int(logical_size * device_pixel_ratio)
        inset = int(2 * device_pixel_ratio)
        image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter, QRect(inset, inset, canvas_size - (inset * 2), canvas_size - (inset * 2)))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor(Theme.get_text_color()))
        painter.end()

        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        return pixmap

    def _sync_pinned_selection_to_root(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        root_key = str(self._tree_root_path or "").replace("\\", "/").lower()
        self.pinned_folders_list.blockSignals(True)
        matched_item: QListWidgetItem | None = None
        for row in range(self.pinned_folders_list.count()):
            item = self.pinned_folders_list.item(row)
            item_key = str(item.data(Qt.ItemDataRole.UserRole) or "").replace("\\", "/").lower()
            is_match = bool(root_key) and item_key == root_key
            item.setSelected(is_match)
            row_widget = self.pinned_folders_list.itemWidget(item)
            if isinstance(row_widget, QWidget):
                self._set_pinned_folder_row_selected(row_widget, is_match)
            if is_match:
                matched_item = item
        if matched_item is not None:
            self.pinned_folders_list.setCurrentItem(matched_item)
        else:
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.setCurrentItem(None)
        self.pinned_folders_list.blockSignals(False)

    def _on_pinned_folder_selection_changed(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        item = self.pinned_folders_list.currentItem()
        if not item:
            return
        folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not folder_path:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "collections_list"):
            self.collections_list.blockSignals(True)
            self.collections_list.clearSelection()
            self.collections_list.blockSignals(False)
        if hasattr(self, "smart_collections_list"):
            self.smart_collections_list.blockSignals(True)
            self.smart_collections_list.clearSelection()
            self.smart_collections_list.blockSignals(False)
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)

    def _on_pinned_folders_context_menu(self, pos: QPoint) -> None:
        item = self.pinned_folders_list.itemAt(pos)
        if not item:
            return

        folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not folder_path:
            return
        is_hidden = bool(item.data(Qt.ItemDataRole.UserRole + 1))

        menu = QMenu(self)
        act_open = menu.addAction("Open Folder")
        act_hide = None
        act_unhide = None
        if is_hidden:
            act_unhide = menu.addAction("Unhide Folder")
        else:
            act_hide = menu.addAction("Hide Folder")
        act_unpin = menu.addAction("Unpin Folder")
        menu.addSeparator()
        act_explorer = menu.addAction("Open in File Explorer")

        chosen = menu.exec(self.pinned_folders_list.viewport().mapToGlobal(pos))
        if chosen == act_open:
            self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)
        elif chosen == act_hide:
            if self.bridge.set_folder_hidden(folder_path, True):
                self.proxy_model.invalidateFilter()
                self._reload_pinned_folders()
        elif chosen == act_unhide:
            if self.bridge.set_folder_hidden(folder_path, False):
                self.proxy_model.invalidateFilter()
                self._reload_pinned_folders()
        elif chosen == act_unpin:
            self.bridge.unpin_folder(folder_path)
        elif chosen == act_explorer:
            self.bridge.open_in_explorer(folder_path)

    def _show_folders_header_menu(self) -> None:
        menu = QMenu(self)
        act_expand_all = menu.addAction("Expand All")
        act_collapse_all = menu.addAction("Collapse All")
        chosen = menu.exec(self.folders_menu_btn.mapToGlobal(QPoint(0, self.folders_menu_btn.height())))
        if chosen == act_expand_all:
            self._expand_tree_from_root()
        elif chosen == act_collapse_all:
            self._collapse_tree_to_root()

    def _expand_tree_branch(self, parent_index: QModelIndex) -> None:
        model = self.tree.model()
        if model is None or not parent_index.isValid():
            return
        row_count = model.rowCount(parent_index)
        for row in range(row_count):
            child_index = model.index(row, 0, parent_index)
            if not child_index.isValid():
                continue
            if model.hasChildren(child_index):
                self.tree.expand(child_index)
                self._expand_tree_branch(child_index)

    def _expand_tree_from_root(self) -> None:
        root_index = self.tree.rootIndex()
        if not root_index.isValid():
            return
        self._suspend_tree_auto_reveal = False
        self.tree.expand(root_index)
        self._expand_tree_branch(root_index)

    def _collapse_tree_to_root(self) -> None:
        root_index = self.tree.rootIndex()
        if not root_index.isValid():
            return
        self._suspend_tree_auto_reveal = True
        self._pending_tree_sync_path = ""
        self._pending_tree_reroot = False
        self._tree_sync_timer.stop()
        self.tree.collapseAll()
        root_path = str(self._tree_root_path or "")
        if root_path:
            root_item = self.proxy_model.mapFromSource(self.fs_model.index(root_path))
            if root_item.isValid():
                self.tree.expand(root_item)

    def _reload_collections(self) -> None:
        if not hasattr(self, "collections_list"):
            return
        try:
            collections = self.bridge.list_collections()
            active = self.bridge.get_active_collection()
            active_id = int(active.get("id", 0) or 0)
        except Exception:
            collections = []
            active_id = 0

        self.collections_list.blockSignals(True)
        self.collections_list.clear()
        for collection in collections:
            count = int(collection.get("item_count", 0) or 0)
            label = str(collection.get("name", ""))
            is_hidden = bool(collection.get("is_hidden", 0))
            
            # If show_hidden is False, skip hidden collections in the list
            if not self.bridge._show_hidden_enabled() and is_hidden:
                continue

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, int(collection.get("id", 0)))
            item.setData(Qt.ItemDataRole.UserRole + 1, is_hidden)
            item.setToolTip(f"{label} ({count} items)")
            
            if is_hidden:
                # Dim the text for hidden collections if they are shown
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setForeground(QColor(128, 128, 128))

            self.collections_list.addItem(item)
            if int(collection.get("id", 0)) == active_id:
                item.setSelected(True)
                self.collections_list.setCurrentItem(item)
        self.collections_list.blockSignals(False)

    def _reload_smart_collections(self) -> None:
        if not hasattr(self, "smart_collections_list"):
            return
        try:
            smart_collections = self.bridge.list_smart_collections()
            active = self.bridge.get_active_smart_collection()
            active_key = str(active.get("key", "") or "")
        except Exception:
            smart_collections = []
            active_key = ""

        self.smart_collections_list.blockSignals(True)
        self.smart_collections_list.clear()
        for definition in smart_collections:
            count = int(definition.get("item_count", 0) or 0)
            label = str(definition.get("name", ""))
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(definition.get("key", "") or ""))
            item.setToolTip(f"{label} ({count} items)")
            self.smart_collections_list.addItem(item)
            if str(definition.get("key", "") or "") == active_key:
                item.setSelected(True)
                self.smart_collections_list.setCurrentItem(item)
        self.smart_collections_list.blockSignals(False)

    def _on_collection_selection_changed(self) -> None:
        if not hasattr(self, "collections_list"):
            return
        item = self.collections_list.currentItem()
        if not item:
            return
        collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if collection_id <= 0:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "pinned_folders_list"):
            self.pinned_folders_list.blockSignals(True)
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.blockSignals(False)
        if hasattr(self, "smart_collections_list"):
            self.smart_collections_list.blockSignals(True)
            self.smart_collections_list.clearSelection()
            self.smart_collections_list.blockSignals(False)
        self.bridge.set_active_collection(collection_id)

    def _on_smart_collection_selection_changed(self) -> None:
        if not hasattr(self, "smart_collections_list"):
            return
        item = self.smart_collections_list.currentItem()
        if not item:
            return
        smart_key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not smart_key:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "pinned_folders_list"):
            self.pinned_folders_list.blockSignals(True)
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.blockSignals(False)
        if hasattr(self, "collections_list"):
            self.collections_list.blockSignals(True)
            self.collections_list.clearSelection()
            self.collections_list.blockSignals(False)
        self.bridge.set_active_smart_collection(smart_key)

    def _on_collections_context_menu(self, pos: QPoint) -> None:
        item = self.collections_list.itemAt(pos)
        menu = QMenu(self)
        act_new = menu.addAction("New Collection...")
        act_rename = None
        act_delete = None
        act_hide = None
        act_unhide = None
        if item:
            is_hidden = item.data(Qt.ItemDataRole.UserRole + 1)
            if is_hidden:
                act_unhide = menu.addAction("Unhide Collection")
            else:
                act_hide = menu.addAction("Hide Collection")
            
            act_rename = menu.addAction("Rename...")
            act_delete = menu.addAction("Delete")

        chosen = menu.exec(self.collections_list.viewport().mapToGlobal(pos))
        if chosen == act_new:
            name, ok = _run_themed_text_input_dialog(self, "New Collection", "Collection Name:")
            if ok and name.strip():
                created = self.bridge.create_collection(name)
                if created:
                    self._reload_collections()
                    self.bridge.set_active_collection(int(created.get("id", 0) or 0))
                    self._reload_collections()
        elif item and chosen == act_rename:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            current_name = item.text()
            name, ok = _run_themed_text_input_dialog(self, "Rename Collection", "Collection Name:", text=current_name)
            if ok and name.strip() and name.strip() != current_name:
                if self.bridge.rename_collection(collection_id, name):
                    self._reload_collections()
        elif item and chosen == act_hide:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            if self.bridge.set_collection_hidden(collection_id, True):
                self._reload_collections()
        elif item and chosen == act_unhide:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            if self.bridge.set_collection_hidden(collection_id, False):
                self._reload_collections()
        elif item and chosen == act_delete:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            reply = QMessageBox.question(
                self,
                "Delete Collection",
                f"Delete collection '{item.text()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.bridge.delete_collection(collection_id):
                    self._reload_collections()

    def _apply_ui_flag(self, key: str, value: bool) -> None:
        try:
            schedule_gallery_relayout = key in {
                "ui.show_top_panel",
                "ui.show_left_panel",
                "ui.show_right_panel",
                "ui.show_bottom_panel",
            }
            if key == "gallery.view_mode":
                self._sync_gallery_view_actions()
            elif key == "ui.show_top_panel":
                if hasattr(self, "act_toggle_top_panel"):
                    self.act_toggle_top_panel.setChecked(bool(value))
                self._sync_menu_bar_controls()
            elif key == "ui.show_left_panel":
                if not bool(value):
                    self._save_main_panel_widths()
                self.left_panel.setVisible(bool(value))
                QTimer.singleShot(0, self._restore_main_splitter_sizes)
                if bool(value):
                    current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
                    if current_path:
                        self._queue_tree_sync(current_path)
                self._sync_menu_bar_controls()
            elif key == "ui.show_right_panel":
                if not bool(value):
                    self._save_main_panel_widths()
                self.right_panel_host.setVisible(bool(value))
                QTimer.singleShot(0, self._restore_main_splitter_sizes)
                if bool(value):
                    if self._is_tag_list_panel_requested_visible():
                        QTimer.singleShot(0, self._sync_tag_list_panel_visibility)
                    else:
                        QTimer.singleShot(0, self._restore_right_splitter_sizes)
                if hasattr(self, "act_toggle_right_panel"):
                    self.act_toggle_right_panel.setChecked(bool(value))
                self._sync_menu_bar_controls()
            elif key == "ui.show_bottom_panel":
                if not bool(value):
                    self._save_bottom_panel_height()
                self.bottom_panel.setVisible(bool(value))
                QTimer.singleShot(0, self._restore_center_splitter_sizes)
                if hasattr(self, "act_toggle_bottom_panel"):
                    self.act_toggle_bottom_panel.setChecked(bool(value))
                self._sync_menu_bar_controls()
            elif key == "ui.preview_above_details":
                if hasattr(self, "preview_header_row"):
                    visible = bool(value)
                    
                    # Stop video playback asynchronously before hiding the UI to prevent Qt FFmpeg deadlock
                    overlay = getattr(self, "sidebar_video_overlay", None)
                    if not visible and overlay is not None:
                        overlay.close_overlay(notify_web=False)

                    # "Preview" title row stays visible; toggle image/sep and corresponding buttons
                    self.preview_header_row.setVisible(True)
                    self.preview_image_lbl.setVisible(visible)
                    self.preview_sep.setVisible(visible)
                    if hasattr(self, "btn_play_preview"):
                        self.btn_play_preview.setVisible(False)
                    if hasattr(self, "btn_close_preview"):
                        self.btn_close_preview.setVisible(visible)
                    if hasattr(self, "btn_show_preview_inline"):
                        self.btn_show_preview_inline.setVisible(not visible)

                    # Reload the correct media (image or video) when toggled back on
                    if visible:
                        QTimer.singleShot(0, lambda: self._refresh_preview_for_path(getattr(self, "_current_path", None)))
                if hasattr(self, "act_preview_above_details"):
                    self.act_preview_above_details.setChecked(bool(value))
                if hasattr(self, "right_layout"):
                    self.right_layout.activate()
                    self._sync_sidebar_panel_widths()
                self._sync_tag_list_panel_visibility()
                self._sync_sidebar_video_preview_controls()
            elif key == "player.autoplay_preview_animated_gifs":
                if getattr(self, "_preview_movie", None) is not None:
                    if bool(value):
                        self._update_preview_display()
                    else:
                        try:
                            self._preview_movie.stop()
                            self._preview_movie.jumpToFrame(0)
                        except Exception:
                            pass
                        self._render_preview_movie_frame()
                        self._sync_sidebar_video_preview_controls()
            elif key == "ui.theme_mode":
                self._update_native_styles(self._current_accent)
                self._update_splitter_style(self._current_accent)
                self._apply_compare_panel_theme(self._current_accent)
                if hasattr(self, "compare_panel"):
                    self.compare_panel.update()
                    self.compare_panel.repaint()
                if hasattr(self, "native_tooltip"):
                    self.native_tooltip.update_style(QColor(self._current_accent), Theme.get_is_light())
                self._update_app_style(QColor(self._current_accent))
                QTimer.singleShot(0, lambda: self._apply_compare_panel_theme(self._current_accent))
            elif key == "metadata.display.order" or key.startswith("metadata.layout."):
                self._setup_metadata_layout()
                if hasattr(self, "_current_paths") and self._current_paths:
                    self._show_metadata_for_path(self._current_paths)
                else:
                    self._clear_metadata_panel()
            elif key.startswith("metadata.display."):
                # Refresh current metadata display to apply visibility
                if hasattr(self, "_current_paths") and self._current_paths:
                    self._show_metadata_for_path(self._current_paths)
                else:
                    self._clear_metadata_panel()
            elif key == "gallery.show_hidden":
                if hasattr(self, "proxy_model"):
                    self.proxy_model.invalidateFilter()
                if hasattr(self, "pinned_folders_list"):
                    self._reload_pinned_folders()
                if hasattr(self, "collections_list"):
                    self._reload_collections()
                if hasattr(self, "tag_list_select"):
                    self._reload_tag_lists()
            if key == "ui.show_left_panel" and hasattr(self, "act_toggle_left_panel"):
                self.act_toggle_left_panel.setChecked(bool(value))
            if schedule_gallery_relayout:
                QTimer.singleShot(0, lambda: self._schedule_gallery_container_relayout(120))
        except Exception:
            pass

    def _update_preview_visibility(self) -> None:
        visible = self.bridge._preview_above_details_enabled()
        self.preview_header_row.setVisible(True)
        self.preview_image_lbl.setVisible(visible)
        self.preview_sep.setVisible(visible)
        if hasattr(self, "btn_play_preview"):
            self.btn_play_preview.setVisible(False)
        if hasattr(self, "btn_close_preview"):
            self.btn_close_preview.setVisible(visible)
        if hasattr(self, "btn_show_preview_inline"):
            self.btn_show_preview_inline.setVisible(not visible)
        if hasattr(self, "act_preview_above_details"):
            self.act_preview_above_details.setChecked(visible)
        self._sync_sidebar_video_preview_controls()

    def _wrap_button_text(self, button: QPushButton, base_text: str, max_width: int) -> None:
        metrics = QFontMetrics(button.font())
        inner_width = max(40, max_width - 22)
        words = base_text.split()
        if not words:
            if button.text() != base_text:
                button.setText(base_text)
            return

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if metrics.horizontalAdvance(candidate) <= inner_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        wrapped = "\n".join(lines)
        if button.text() != wrapped:
            button.setText(wrapped)

    def _right_panel_content_width(self) -> int:
        if not hasattr(self, "scroll_area"):
            return 180
        if self._is_bulk_editor_active() and hasattr(self, "bulk_scroll_area") and hasattr(self, "bulk_right_layout"):
            if self._current_bulk_editor_mode() == "captions" and hasattr(self, "bulk_caption_scroll_area") and hasattr(self, "bulk_caption_right_layout"):
                scroll_area = self.bulk_caption_scroll_area
                layout = self.bulk_caption_right_layout
            else:
                scroll_area = self.bulk_scroll_area
                layout = self.bulk_right_layout
        else:
            scroll_area = self.scroll_area
            layout = self.right_layout if hasattr(self, "right_layout") else None
        margins = layout.contentsMargins() if layout is not None else None
        left = margins.left() if margins else 12
        right = margins.right() if margins else 12
        viewport_w = scroll_area.viewport().width()
        return max(90, viewport_w - left - right)

    def _queue_sidebar_panel_width_sync(self) -> None:
        if bool(getattr(self, "_sidebar_width_sync_pending", False)):
            return
        self._sidebar_width_sync_pending = True
        QTimer.singleShot(0, self._sync_sidebar_panel_widths)

    def _sync_sidebar_panel_widths(self) -> None:
        self._sidebar_width_sync_pending = False
        if not hasattr(self, "scroll_area"):
            return
        available_w = self._right_panel_content_width()
        self._update_sidebar_action_buttons(available_w)
        self._update_sidebar_input_widths(available_w)
        if hasattr(self, "right_layout"):
            self.right_layout.activate()
        if hasattr(self, "bulk_right_layout"):
            self.bulk_right_layout.activate()
        if hasattr(self, "bulk_caption_right_layout"):
            self.bulk_caption_right_layout.activate()

    def _update_sidebar_action_buttons(self, available_w: int | None = None) -> None:
        if not hasattr(self, "scroll_area"):
            return
        if available_w is None:
            available_w = self._right_panel_content_width()
        buttons = [
            getattr(self, "meta_empty_select_all_btn", None),
            getattr(self, "btn_open_tag_list", None),
            getattr(self, "btn_clear_bulk_tags", None),
            getattr(self, "btn_save_meta", None),
            getattr(self, "btn_use_ocr", None),
            getattr(self, "btn_generate_tags", None),
            getattr(self, "btn_generate_description", None),
            getattr(self, "btn_import_exif", None),
            getattr(self, "btn_merge_hidden_meta", None),
            getattr(self, "btn_save_to_exif", None),
            getattr(self, "bulk_btn_select_all_gallery", None),
            getattr(self, "bulk_btn_open_tag_list", None),
            getattr(self, "bulk_btn_clear_tags", None),
            getattr(self, "bulk_btn_run_local_ai", None),
            getattr(self, "bulk_btn_save_meta", None),
            getattr(self, "bulk_btn_save_to_exif", None),
        ]
        for button in buttons:
            if button is None:
                continue
            base_text = str(button.property("baseText") or button.text()).replace("\n", " ").strip()
            button.setProperty("baseText", base_text)
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setFixedWidth(available_w)
            self._wrap_button_text(button, base_text, available_w)
            button.updateGeometry()

    def _update_sidebar_input_widths(self, available_w: int | None = None) -> None:
        if not hasattr(self, "scroll_container"):
            return
        if available_w is None:
            available_w = self._right_panel_content_width()
        if hasattr(self, "preview_image_lbl"):
            self.preview_image_lbl.setFixedWidth(available_w)
        for wrapper in [
            getattr(self, "generate_description_btn_row", None),
            getattr(self, "generate_tags_btn_row", None),
            getattr(self, "tag_list_open_btn_row", None),
        ]:
            if wrapper is None:
                continue
            wrapper.setMinimumWidth(0)
            wrapper.setMaximumWidth(16777215)
            wrapper.setFixedWidth(available_w)
            wrapper.setSizePolicy(QSizePolicy.Policy.Ignored, wrapper.sizePolicy().verticalPolicy())
            wrapper.updateGeometry()
        for label in [
            getattr(self, "generate_description_progress_lbl", None),
            getattr(self, "generate_description_error_edit", None),
            getattr(self, "generate_tags_progress_lbl", None),
            getattr(self, "generate_tags_error_edit", None),
            getattr(self, "meta_status_lbl", None),
            getattr(self, "bulk_status_lbl", None),
            getattr(self, "bulk_caption_status_lbl", None),
        ]:
            if label is None:
                continue
            label.setMinimumWidth(0)
            label.setMaximumWidth(16777215)
            label.setFixedWidth(available_w)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, label.sizePolicy().verticalPolicy())
            label.updateGeometry()
        if self._is_bulk_editor_active():
            active_container = self.bulk_caption_scroll_container if self._current_bulk_editor_mode() == "captions" and hasattr(self, "bulk_caption_scroll_container") else self.bulk_scroll_container
        else:
            active_container = self.scroll_container
        for widget in active_container.findChildren(QWidget):
            if not isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
                continue
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)
            widget.setFixedWidth(available_w)
            widget.setSizePolicy(QSizePolicy.Policy.Ignored, widget.sizePolicy().verticalPolicy())
            widget.updateGeometry()

    def _metadata_content_widgets(self) -> list[QWidget]:
        widgets: list[QWidget] = [
            self.preview_header_row,
            self.preview_image_lbl,
            self.preview_sep,
            self.details_header_lbl,
            self.lbl_fn_cap,
            self.meta_filename_edit,
            self.meta_path_lbl,
            self.btn_clear_bulk_tags,
            self.btn_save_meta,
            self.btn_import_exif,
            self.btn_merge_hidden_meta,
            self.btn_save_to_exif,
            self.meta_status_lbl,
        ]
        seen: set[int] = set()
        for group_widgets in getattr(self, "_meta_groups", {}).values():
            for widget in group_widgets:
                ident = id(widget)
                if ident in seen:
                    continue
                seen.add(ident)
                widgets.append(widget)
        return widgets

    def _set_metadata_empty_state(self, visible: bool) -> None:
        if not hasattr(self, "meta_empty_state_lbl"):
            return
        self.meta_empty_state_lbl.setVisible(visible)
        if hasattr(self, "meta_empty_select_all_btn"):
            self.meta_empty_select_all_btn.setVisible(visible)
        if visible:
            self._clear_preview_media()
            self.preview_image_lbl.setText("")
            for widget in self._metadata_content_widgets():
                widget.setVisible(False)

    def _current_bulk_editor_mode(self) -> str:
        mode = str(getattr(self, "_bulk_editor_mode", "tags") or "tags").strip().lower()
        return "captions" if mode == "captions" else "tags"

    def _set_active_bulk_editor_mode(self, mode: str) -> None:
        next_mode = "captions" if str(mode or "").strip().lower() == "captions" else "tags"
        self._bulk_editor_mode = next_mode
        if hasattr(self, "bulk_mode_tags_btn"):
            self.bulk_mode_tags_btn.blockSignals(True)
            self.bulk_mode_tags_btn.setChecked(next_mode == "tags")
            self.bulk_mode_tags_btn.blockSignals(False)
        if hasattr(self, "bulk_mode_captions_btn"):
            self.bulk_mode_captions_btn.blockSignals(True)
            self.bulk_mode_captions_btn.setChecked(next_mode == "captions")
            self.bulk_mode_captions_btn.blockSignals(False)
        if hasattr(self, "bulk_pages_stack"):
            target = getattr(self, "bulk_captions_page", None) if next_mode == "captions" else getattr(self, "bulk_tags_page", None)
            if target is not None:
                self.bulk_pages_stack.setCurrentWidget(target)
        if self._is_bulk_editor_active():
            selection_count = len(self._current_file_paths())
            if next_mode == "captions":
                self._configure_bulk_caption_editor(selection_count)
            else:
                self._configure_bulk_tag_editor(selection_count)

    def _configure_bulk_tag_editor(self, selection_count: int) -> None:
        self._set_active_right_workspace("bulk")
        self._set_active_bulk_editor_mode("tags") if self._current_bulk_editor_mode() != "tags" else None
        self.bulk_selection_lbl.setText(f"<span style=\"font-weight:700;\">{selection_count}</span> files selected")
        self.bulk_meta_tags.setPlaceholderText("tag1, tag2, tag3")
        self.bulk_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_btn_run_local_ai.setProperty("baseText", f"Generate Tags for All ({selection_count} Files)")
        self.bulk_btn_save_meta.setProperty("baseText", f"Save Tags to DB for {selection_count} Items")
        self.bulk_btn_clear_tags.setProperty("baseText", f"Clear Tags from DB for {selection_count} Items")
        self.bulk_btn_save_to_exif.setProperty("baseText", f"Embed Tags in {selection_count} Files")
        self.bulk_btn_save_to_exif.setToolTip("Write only the entered tags into each selected file's embedded metadata")
        self._refresh_bulk_tag_editor_summary()
        self._sync_sidebar_panel_widths()

    def _configure_bulk_caption_editor(self, selection_count: int) -> None:
        self._set_active_right_workspace("bulk")
        self._set_active_bulk_editor_mode("captions") if self._current_bulk_editor_mode() != "captions" else None
        self.bulk_caption_selection_lbl.setText(f"<span style=\"font-weight:700;\">{selection_count}</span> files selected")
        self.bulk_caption_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_caption_btn_run_local_ai.setProperty("baseText", f"Generate Descriptions for All ({selection_count} Files)")
        self.bulk_caption_btn_save_meta.setProperty("baseText", f"Save Descriptions to DB for {selection_count} Items")
        self.bulk_caption_btn_clear.setProperty("baseText", f"Clear Descriptions from DB for {selection_count} Items")
        self._refresh_bulk_caption_editor_summary()
        self._sync_sidebar_panel_widths()

    def _select_all_visible_gallery_items(self, _checked: bool = False) -> None:
        try:
            self.web.page().runJavaScript(
                "try{ if(window.__mmx_selectAllVisible){ window.__mmx_selectAllVisible(); } else if(window.selectAll){ window.selectAll(); } }catch(e){}"
            )
        except Exception:
            pass

    def _jump_review_group(self, direction: int) -> None:
        step = -1 if int(direction or 0) < 0 else 1
        try:
            self.web.page().runJavaScript(
                f"try{{ window.__mmx_jumpReviewGroup && window.__mmx_jumpReviewGroup({step}); }}catch(e){{}}"
            )
        except Exception:
            pass

    def _open_bulk_tag_editor_from_menu(self, _checked: bool = False) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
                self.bridge.settings.setValue("ui/show_right_panel", True)
                self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        except Exception:
            pass
        self._set_tag_list_panel_requested_visible(True)
        self._set_active_bulk_editor_mode("tags")
        scope_paths = self._current_gallery_scope_paths()
        if len(scope_paths) > 1:
            self._show_metadata_for_path(scope_paths)
        QTimer.singleShot(0, self._select_all_visible_gallery_items)

    def _open_bulk_caption_editor_from_menu(self, _checked: bool = False) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
                self.bridge.settings.setValue("ui/show_right_panel", True)
                self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        except Exception:
            pass
        self._set_active_bulk_editor_mode("captions")
        scope_paths = self._current_gallery_scope_paths()
        if len(scope_paths) > 1:
            self._show_metadata_for_path(scope_paths)
        QTimer.singleShot(0, self._select_all_visible_gallery_items)

    def _save_bulk_descriptions_to_db(self) -> None:
        paths = self._current_file_paths()
        if not paths:
            return
        updated = 0
        for i in range(self.bulk_caption_selected_files_list.count()):
            item = self.bulk_caption_selected_files_list.item(i)
            row = self.bulk_caption_selected_files_list.itemWidget(item)
            if not isinstance(row, BulkSelectedFileRow):
                continue
            clean_path = str(getattr(row, "_path", "") or "").strip()
            if not clean_path:
                continue
            try:
                existing = dict(self.bridge.get_media_metadata(clean_path) or {})
                self.bridge.update_media_metadata(
                    clean_path,
                    str(existing.get("title") or ""),
                    row.tags_edit.toPlainText(),
                    str(existing.get("notes") or ""),
                    str(existing.get("embedded_tags") or ""),
                    str(existing.get("embedded_comments") or ""),
                    str(existing.get("ai_prompt") or ""),
                    str(existing.get("ai_negative_prompt") or ""),
                    str(existing.get("ai_params") or ""),
                )
                updated += 1
            except Exception:
                pass
        self._refresh_bulk_caption_editor_summary()
        self.bulk_caption_status_lbl.setText(f"âœ“ Descriptions saved for {updated} items")
        QTimer.singleShot(3000, lambda: self.bulk_caption_status_lbl.setText(""))

    def _clear_bulk_descriptions(self) -> None:
        paths = self._current_file_paths()
        if not paths:
            return
        for path in paths:
            try:
                existing = dict(self.bridge.get_media_metadata(path) or {})
                self.bridge.update_media_metadata(
                    path,
                    str(existing.get("title") or ""),
                    "",
                    str(existing.get("notes") or ""),
                    str(existing.get("embedded_tags") or ""),
                    str(existing.get("embedded_comments") or ""),
                    str(existing.get("ai_prompt") or ""),
                    str(existing.get("ai_negative_prompt") or ""),
                    str(existing.get("ai_params") or ""),
                )
            except Exception:
                pass
        self._refresh_bulk_caption_editor_summary()
        self.bulk_caption_status_lbl.setText(f"âœ“ Descriptions cleared for {len(paths)} items")
        QTimer.singleShot(3000, lambda: self.bulk_caption_status_lbl.setText(""))

    @staticmethod
    def _normalize_tag_list(text: str) -> list[str]:
        parts = re.split(r"[;,]", str(text or ""))
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _merge_tag_lists(existing: list[str] | None, new_tags: list[str] | None) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for tag in list(existing or []) + list(new_tags or []):
            normalized = str(tag or "").strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
        return merged

    def _active_tag_list_id(self) -> int:
        if not hasattr(self, "tag_list_select"):
            return 0
        return int(self.tag_list_select.currentData() or 0)

    def _is_bulk_editor_active(self) -> bool:
        return bool(hasattr(self, "right_workspace_stack") and self.right_workspace_stack.currentWidget() is getattr(self, "bulk_editor_panel", None))

    def _set_active_right_workspace(self, workspace: str) -> None:
        if not hasattr(self, "right_workspace_stack"):
            return
        if workspace == "bulk" and hasattr(self, "bulk_editor_panel"):
            self.right_workspace_stack.setCurrentWidget(self.bulk_editor_panel)
        elif hasattr(self, "details_workspace"):
            self.right_workspace_stack.setCurrentWidget(self.details_workspace)
        self._sync_sidebar_panel_widths()
        if hasattr(self, "tag_list_panel") and self.tag_list_panel.isVisible():
            self._refresh_tag_list_rows_state()

    def _active_tag_editor(self):
        if self._is_bulk_editor_active() and hasattr(self, "bulk_meta_tags"):
            return self.bulk_meta_tags
        return self.meta_tags

    def _tag_editor_text(self, editor=None) -> str:
        editor = editor or self._active_tag_editor()
        if isinstance(editor, QTextEdit):
            return editor.toPlainText()
        return editor.text()

    def _set_tag_editor_text(self, text: str, editor=None) -> None:
        editor = editor or self._active_tag_editor()
        if isinstance(editor, QTextEdit):
            editor.setPlainText(str(text or ""))
        else:
            editor.setText(str(text or ""))

    def _active_status_label(self):
        if self._is_bulk_editor_active():
            if self._current_bulk_editor_mode() == "captions" and hasattr(self, "bulk_caption_status_lbl"):
                return self.bulk_caption_status_lbl
            if hasattr(self, "bulk_status_lbl"):
                return self.bulk_status_lbl
        return self.meta_status_lbl

    def _scroll_bottom_status_into_view(self) -> None:
        if not hasattr(self, "scroll_area") or not hasattr(self, "meta_status_lbl"):
            return
        if self._is_bulk_editor_active():
            return
        try:
            self.scroll_area.ensureWidgetVisible(self.meta_status_lbl, 0, 16)
        except Exception:
            try:
                bar = self.scroll_area.verticalScrollBar()
                bar.setValue(bar.maximum())
            except Exception:
                pass

    def _current_file_paths(self, paths: list[str] | None = None) -> list[str]:
        raw_paths = list(paths if paths is not None else getattr(self, "_current_paths", []) or [])
        file_paths: list[str] = []
        seen: set[str] = set()
        for raw_path in raw_paths:
            path = str(raw_path or "").strip()
            if not path:
                continue
            key = path.casefold()
            if key in seen:
                continue
            try:
                if not Path(path).is_file():
                    continue
            except Exception:
                continue
            seen.add(key)
            file_paths.append(path)
        return file_paths

    def _selected_paths_tag_summary(self) -> tuple[list[str], list[str]]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        paths = self._current_file_paths()
        if not paths:
            return [], []
        unique_paths: list[str] = []
        seen_paths: set[str] = set()
        for path in paths:
            normalized_path = normalize_windows_path(path)
            key = normalized_path.casefold()
            if key in seen_paths:
                continue
            seen_paths.add(key)
            unique_paths.append(normalized_path)
        placeholders = ",".join("?" for _ in unique_paths)
        ordered_names: dict[str, str] = {}
        counts: Counter[str] = Counter()
        try:
            rows = self.bridge.conn.execute(
                f"""
                SELECT t.name, COUNT(DISTINCT mi.id) AS usage_count
                FROM media_items mi
                JOIN media_tags mt ON mt.media_id = mi.id
                JOIN tags t ON t.id = mt.tag_id
                WHERE mi.path IN ({placeholders})
                GROUP BY t.id, t.name
                ORDER BY t.name COLLATE NOCASE
                """,
                unique_paths,
            ).fetchall()
        except Exception:
            rows = []
        for row in rows:
            tag = str((row[0] if len(row) > 0 else "") or "").strip()
            if not tag:
                continue
            key = tag.casefold()
            ordered_names.setdefault(key, tag)
            counts[key] = int(row[1] or 0)
        total = max(1, len(unique_paths))
        common = [ordered_names[key] for key, count in counts.items() if count == total]
        uncommon = [ordered_names[key] for key, count in counts.items() if 0 < count < total]
        return sorted(common, key=str.casefold), sorted(uncommon, key=str.casefold)

    def _current_gallery_scope_paths(self) -> list[str]:
        try:
            entries = self.bridge._get_gallery_entries(
                list(getattr(self.bridge, "_selected_folders", []) or []),
                "none",
                getattr(self.bridge, "_current_gallery_filter", "all"),
                self._effective_gallery_scope_search(include_tag_scope=False),
            )
        except Exception:
            entries = []
        paths: list[str] = []
        seen: set[str] = set()
        for entry in entries or []:
            if entry.get("is_folder"):
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            key = path.casefold()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
        return paths

    def _bulk_tag_selection_states(self) -> tuple[set[str], set[str]]:
        common, uncommon = self._selected_paths_tag_summary()
        return {tag.casefold() for tag in common}, {tag.casefold() for tag in uncommon}

    def _bulk_selected_file_thumbnail(self, path: str, content_height: int | None = None) -> QPixmap | None:
        clean = str(path or "").strip()
        if not clean:
            return None
        try:
            p = Path(clean)
            try:
                preview_path = self.bridge._local_ai_source_path(p)
            except Exception:
                preview_path = p
            image = _read_image_with_svg_support(preview_path)
            if image is None or image.isNull():
                return None
            target_size = max(72, int(content_height or BulkSelectedFileRow._TAG_CONTENT_HEIGHT))
            return QPixmap.fromImage(image).scaled(
                target_size,
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception:
            return None

    def _toggle_bulk_tag_section(self, toggle: QToolButton, widget: QWidget, checked: bool) -> None:
        if toggle is not None:
            label = toggle.text()
            if " " in label:
                _, suffix = label.split(" ", 1)
            else:
                suffix = label
            toggle.setText(("â–¾ " if checked else "â–¸ ") + suffix)
        if widget is not None:
            widget.setVisible(bool(checked))

    def _save_bulk_selected_file_tags(self, path: str, text: str) -> None:
        clean_path = str(path or "").strip()
        if not clean_path:
            return
        try:
            self.bridge.set_media_tags(clean_path, self._normalize_tag_list(text))
        except Exception:
            pass
        self._refresh_bulk_tag_editor_summary()
        if self._is_bulk_editor_active():
            self.bulk_status_lbl.setText(f"âœ“ Saved tags for {Path(clean_path).name}")
            QTimer.singleShot(2500, lambda: self.bulk_status_lbl.setText(""))

    def _save_bulk_selected_file_description(self, path: str, text: str) -> None:
        clean_path = str(path or "").strip()
        if not clean_path:
            return
        try:
            existing = dict(self.bridge.get_media_metadata(clean_path) or {})
            self.bridge.update_media_metadata(
                clean_path,
                str(existing.get("title") or ""),
                str(text or ""),
                str(existing.get("notes") or ""),
                str(existing.get("embedded_tags") or ""),
                str(existing.get("embedded_comments") or ""),
                str(existing.get("ai_prompt") or ""),
                str(existing.get("ai_negative_prompt") or ""),
                str(existing.get("ai_params") or ""),
            )
        except Exception:
            pass
        self._refresh_bulk_caption_editor_summary()
        if self._is_bulk_editor_active():
            self.bulk_caption_status_lbl.setText(f"âœ“ Saved description for {Path(clean_path).name}")
            QTimer.singleShot(2500, lambda: self.bulk_caption_status_lbl.setText(""))

    @staticmethod
    def _bulk_selected_file_tags_text(tags: list[str]) -> str:
        clean = [str(tag or "").strip() for tag in list(tags or []) if str(tag or "").strip()]
        return ", ".join(clean)

    def _refresh_bulk_selected_files_list(
        self,
        list_widget: QListWidget,
        *,
        content_height: int,
        value_getter,
        edit_handler,
        placeholder_text: str,
    ) -> None:
        if list_widget is None:
            return
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import list_media_tags

        list_widget.clear()
        paths = self._current_file_paths()
        for path in paths:
            try:
                media = get_media_by_path(self.bridge.conn, path)
                tags = list_media_tags(self.bridge.conn, int(media.get("id") or 0)) if media else []
                metadata = dict(self.bridge.get_media_metadata(path) or {})
            except Exception:
                tags = []
                metadata = {}
            item = QListWidgetItem()
            row = BulkSelectedFileRow(
                path,
                self._bulk_selected_file_thumbnail(path, content_height),
                Path(path).name,
                str(value_getter(tags, metadata) or ""),
                content_height=content_height,
                placeholder_text=placeholder_text,
            )
            item.setSizeHint(QSize(0, row.item_height()))
            row.tagsEdited.connect(edit_handler)
            list_widget.addItem(item)
            list_widget.setItemWidget(item, row)
        list_widget.doItemsLayout()

    def _refresh_bulk_tag_selected_files_list(self) -> None:
        self._refresh_bulk_selected_files_list(
            getattr(self, "bulk_selected_files_list", None),
            content_height=BulkSelectedFileRow._TAG_CONTENT_HEIGHT,
            value_getter=lambda tags, metadata: self._bulk_selected_file_tags_text(tags),
            edit_handler=self._save_bulk_selected_file_tags,
            placeholder_text="Tags for this file",
        )
        self._queue_bulk_selected_files_layout_sync()

    def _refresh_bulk_caption_selected_files_list(self) -> None:
        self._refresh_bulk_selected_files_list(
            getattr(self, "bulk_caption_selected_files_list", None),
            content_height=BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT,
            value_getter=lambda tags, metadata: str(metadata.get("description") or ""),
            edit_handler=self._save_bulk_selected_file_description,
            placeholder_text="Description for this file",
        )
        self._queue_bulk_caption_selected_files_layout_sync()

    def _queue_bulk_selected_files_layout_sync(self) -> None:
        if not hasattr(self, "bulk_selected_files_list"):
            return
        QTimer.singleShot(0, self._sync_bulk_selected_files_layout)

    def _sync_bulk_selected_files_layout(self) -> None:
        if not hasattr(self, "bulk_selected_files_list"):
            return
        list_widget = self.bulk_selected_files_list
        viewport = list_widget.viewport()
        if viewport is None:
            return
        viewport_width = max(0, viewport.width())
        if viewport_width <= 0 or list_widget.count() <= 0:
            return
        first_row = list_widget.itemWidget(list_widget.item(0))
        if not isinstance(first_row, BulkSelectedFileRow):
            return
        root_margins = first_row._root_layout.contentsMargins()
        row_margins = first_row._content_row.contentsMargins()
        thumb_width = first_row.thumb_lbl.width()
        spacing = first_row._content_row.spacing()
        host_width = max(
            BulkSelectedFileRow._MIN_EDITOR_WIDTH,
            viewport_width
            - root_margins.left()
            - root_margins.right()
            - row_margins.left()
            - row_margins.right()
            - thumb_width
            - spacing
            - BulkSelectedFileRow._RIGHT_GUTTER,
        )
        list_widget.doItemsLayout()
        for i in range(list_widget.count()):
            row = list_widget.itemWidget(list_widget.item(i))
            if isinstance(row, BulkSelectedFileRow):
                row.set_shared_editor_widths(host_width)
                row.updateGeometry()
                row.update()
        viewport.update()

    def _queue_bulk_caption_selected_files_layout_sync(self) -> None:
        if not hasattr(self, "bulk_caption_selected_files_list"):
            return
        QTimer.singleShot(0, self._sync_bulk_caption_selected_files_layout)

    def _sync_bulk_caption_selected_files_layout(self) -> None:
        if not hasattr(self, "bulk_caption_selected_files_list"):
            return
        list_widget = self.bulk_caption_selected_files_list
        viewport = list_widget.viewport()
        if viewport is None:
            return
        viewport_width = max(0, viewport.width())
        if viewport_width <= 0 or list_widget.count() <= 0:
            return
        first_row = list_widget.itemWidget(list_widget.item(0))
        if not isinstance(first_row, BulkSelectedFileRow):
            return
        root_margins = first_row._root_layout.contentsMargins()
        row_margins = first_row._content_row.contentsMargins()
        thumb_width = first_row.thumb_lbl.width()
        spacing = first_row._content_row.spacing()
        host_width = max(
            BulkSelectedFileRow._MIN_EDITOR_WIDTH,
            viewport_width
            - root_margins.left()
            - root_margins.right()
            - row_margins.left()
            - row_margins.right()
            - thumb_width
            - spacing
            - BulkSelectedFileRow._RIGHT_GUTTER,
        )
        list_widget.doItemsLayout()
        for i in range(list_widget.count()):
            row = list_widget.itemWidget(list_widget.item(i))
            if isinstance(row, BulkSelectedFileRow):
                row.set_shared_editor_widths(host_width)
                row.updateGeometry()
                row.update()
        viewport.update()

    def _refresh_bulk_tag_editor_summary(self) -> None:
        if not hasattr(self, "bulk_common_tags_text"):
            return
        common, uncommon = self._selected_paths_tag_summary()
        self.bulk_common_tags_text.setPlainText(", ".join(common))
        self.bulk_uncommon_tags_text.setPlainText(", ".join(uncommon))
        self._refresh_bulk_tag_selected_files_list()

    def _refresh_bulk_caption_editor_summary(self) -> None:
        if not hasattr(self, "bulk_caption_selected_files_list"):
            return
        self._refresh_bulk_caption_selected_files_list()

    def _configure_tag_list_combo(self, combo: QComboBox) -> None:
        is_tag_list_selector = combo.objectName() == "tagListSelect"
        view = TagListComboPopupView(self.bridge, combo, combo) if is_tag_list_selector else QListView(combo)
        view.setObjectName(f"{combo.objectName()}Popup")
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.setUniformItemSizes(False)
        view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        view.setMouseTracking(True)
        if is_tag_list_selector and isinstance(view, TagListComboPopupView):
            view.deleteRequested.connect(self._delete_tag_list)
            view.renameRequested.connect(self._rename_tag_list_by_id)
            view.hiddenToggled.connect(self._set_tag_list_hidden)
        combo.setView(view)
        combo.setItemDelegate(TagListComboDelegate(self.bridge, combo, view, show_actions=is_tag_list_selector))

    def _selected_tag_names_from_editor(self) -> set[str]:
        return {tag.casefold() for tag in self._normalize_tag_list(self._tag_editor_text())}

    def _invalidate_tag_list_scope_counts_cache(self) -> None:
        self._tag_list_scope_counts_cache_key = None
        self._tag_list_scope_counts_cache_value = None

    def _effective_gallery_scope_search(self, include_tag_scope: bool = True) -> str:
        base_query = str(getattr(self.bridge, "_current_gallery_search", "") or "").strip()
        if not include_tag_scope:
            return base_query
        tag_scope_query = str(getattr(self.bridge, "_current_gallery_tag_scope_search", "") or "").strip()
        if not tag_scope_query:
            return base_query
        return f"{base_query} {tag_scope_query}".strip() if base_query else tag_scope_query

    def _current_scope_tag_counts(self) -> dict[str, int]:
        cache_key = (
            tuple(str(path or "").casefold() for path in list(getattr(self.bridge, "_selected_folders", []) or [])),
            str(getattr(self.bridge, "_current_gallery_filter", "all") or "all"),
            self._effective_gallery_scope_search(include_tag_scope=False),
        )
        if getattr(self, "_tag_list_scope_counts_cache_key", None) == cache_key:
            cached = getattr(self, "_tag_list_scope_counts_cache_value", None)
            if isinstance(cached, dict):
                return dict(cached)
        counts: Counter[str] = Counter()
        try:
            entries = self.bridge._get_gallery_entries(
                list(getattr(self.bridge, "_selected_folders", []) or []),
                "none",
                getattr(self.bridge, "_current_gallery_filter", "all"),
                self._effective_gallery_scope_search(include_tag_scope=False),
            )
        except Exception:
            entries = []
        for entry in entries or []:
            if entry.get("is_folder"):
                continue
            tags = self._normalize_tag_list(entry.get("tags") or "")
            seen: set[str] = set()
            for tag in tags:
                key = tag.casefold()
                if key in seen:
                    continue
                seen.add(key)
                counts[key] += 1
        resolved = dict(counts)
        self._tag_list_scope_counts_cache_key = cache_key
        self._tag_list_scope_counts_cache_value = dict(resolved)
        return resolved

    def _reload_tag_lists(self, preferred_id: int | None = None) -> None:
        from app.mediamanager.db.tag_lists_repo import list_tag_lists

        current_id = preferred_id if preferred_id is not None else self._active_tag_list_id()
        rows = list_tag_lists(self.bridge.conn, include_hidden=self.bridge._show_hidden_enabled())
        self.tag_list_select.blockSignals(True)
        self.tag_list_select.clear()
        for row in rows:
            self.tag_list_select.addItem(str(row.get("name") or ""), int(row.get("id") or 0))
            index = self.tag_list_select.count() - 1
            self.tag_list_select.setItemData(index, bool(row.get("is_hidden")), Qt.ItemDataRole.UserRole + 1)
        self.tag_list_select.blockSignals(False)
        self.tag_list_select.setVisible(bool(rows))

        index = -1
        for i, row in enumerate(rows):
            if int(row.get("id") or 0) == int(current_id or 0):
                index = i
                break
        if index < 0 and rows:
            index = 0
        if index >= 0:
            self.tag_list_select.setCurrentIndex(index)
        self._refresh_tag_list_panel()

    def _create_tag_list(self) -> None:
        from app.mediamanager.db.tag_lists_repo import create_tag_list

        name, ok = _run_themed_text_input_dialog(self, "Create Tag List", "List name:")
        if not ok or not str(name or "").strip():
            return
        created = create_tag_list(self.bridge.conn, name)
        if not created:
            QMessageBox.warning(self, "Create Tag List", "Unable to create that tag list.")
            return
        self._reload_tag_lists(int(created.get("id") or 0))
        self._open_tag_list_panel()

    def _rename_tag_list_by_id(self, tag_list_id: int) -> None:
        from app.mediamanager.db.tag_lists_repo import get_tag_list, rename_tag_list

        if tag_list_id <= 0:
            return
        current = get_tag_list(self.bridge.conn, tag_list_id) or {}
        name, ok = _run_themed_text_input_dialog(self, "Rename Tag List", "List name:", text=str(current.get("name") or ""))
        if not ok or not str(name or "").strip():
            return
        if not rename_tag_list(self.bridge.conn, tag_list_id, name):
            QMessageBox.warning(self, "Rename Tag List", "That tag list name is already in use.")
            return
        self._reload_tag_lists(tag_list_id)

    def _rename_active_tag_list(self) -> None:
        self._rename_tag_list_by_id(self._active_tag_list_id())

    def _set_tag_list_hidden(self, tag_list_id: int, hidden: bool) -> None:
        from app.mediamanager.db.tag_lists_repo import set_tag_list_hidden

        resolved_id = int(tag_list_id or 0)
        if resolved_id <= 0:
            return
        if set_tag_list_hidden(self.bridge.conn, resolved_id, bool(hidden)):
            self._reload_tag_lists(None if hidden and not self.bridge._show_hidden_enabled() else resolved_id)

    def _delete_tag_list(self, tag_list_id: int | None = None) -> None:
        from app.mediamanager.db.tag_lists_repo import delete_tag_list, get_tag_list

        resolved_id = int(tag_list_id or self._active_tag_list_id() or 0)
        if resolved_id <= 0:
            return
        current = get_tag_list(self.bridge.conn, resolved_id) or {}
        current_name = str(current.get("name") or "")
        reply = _run_themed_question_dialog(
            self,
            "Delete Tag List",
            f"Delete tag list '{current_name}'?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if not delete_tag_list(self.bridge.conn, resolved_id):
            QMessageBox.warning(self, "Delete Tag List", "Unable to delete that tag list.")
            return
        self._reload_tag_lists()

    def _add_tag_to_active_list(self) -> None:
        from app.mediamanager.db.tag_lists_repo import add_tag_to_list

        tag_list_id = self._active_tag_list_id()
        if tag_list_id <= 0:
            return
        tag_name, ok = _run_themed_text_input_dialog(self, "Add New Tag", "Tag:")
        if not ok or not str(tag_name or "").strip():
            return
        add_tag_to_list(self.bridge.conn, tag_list_id, tag_name)
        self._refresh_tag_list_panel()

    def _import_tags_from_current_file_into_active_list(self) -> None:
        from app.mediamanager.db.tag_lists_repo import add_tag_to_list

        tag_list_id = self._active_tag_list_id()
        if tag_list_id <= 0:
            return
        tags: list[str] = []
        for path in self._current_file_paths():
            try:
                payload = self.bridge.get_media_metadata(path)
                tags = self._merge_tag_lists(tags, list(payload.get("tags") or []))
            except Exception:
                pass
        if not tags:
            tags = self._normalize_tag_list(self._tag_editor_text())
        if not tags:
            self.meta_status_lbl.setText("No tags available to import")
            QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
            return
        for tag in tags:
            add_tag_to_list(self.bridge.conn, tag_list_id, tag)
        self._refresh_tag_list_panel()

    def _sort_tag_list_entries(self, entries: list[dict], sort_mode: str) -> list[dict]:
        mode = str(sort_mode or "none")
        if mode == "az":
            return sorted(entries, key=lambda row: str(row.get("name") or "").casefold())
        if mode == "za":
            return sorted(entries, key=lambda row: str(row.get("name") or "").casefold(), reverse=True)
        if mode == "most_used":
            return sorted(entries, key=lambda row: (-int(row.get("global_use_count") or 0), str(row.get("name") or "").casefold()))
        if mode == "least_used":
            return sorted(entries, key=lambda row: (int(row.get("global_use_count") or 0), str(row.get("name") or "").casefold()))
        return sorted(entries, key=lambda row: (int(row.get("sort_order") or 0), str(row.get("name") or "").casefold()))

    def _refresh_tag_list_panel(self) -> None:
        from app.mediamanager.db.tag_lists_repo import get_tag_list, list_tag_list_entries

        if not hasattr(self, "tag_list_rows"):
            return
        tag_list_id = self._active_tag_list_id()
        tag_list = get_tag_list(self.bridge.conn, tag_list_id) if tag_list_id > 0 else None

        self.tag_list_rows.clear()
        has_list = bool(tag_list)
        self.active_tag_list_name_lbl.setVisible(has_list)
        self.tag_list_sort_lbl.setVisible(has_list)
        self.tag_list_sort_select.setVisible(has_list)
        self.btn_add_tag_list_tag.setVisible(has_list)
        self.btn_import_tag_list_tags.setVisible(has_list)
        self.btn_clear_tag_scope_filter.setVisible(has_list)
        self.tag_list_rows.setVisible(has_list)
        self.tag_list_panel_layout.setStretchFactor(self.tag_list_rows, 1 if has_list else 0)
        self.tag_list_rows.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding if has_list else QSizePolicy.Policy.Fixed,
        )
        if hasattr(self, "tag_list_bottom_spacer"):
            self.tag_list_bottom_spacer.changeSize(
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed if has_list else QSizePolicy.Policy.Expanding,
            )
            self.tag_list_panel_layout.invalidate()

        if not has_list:
            self.active_tag_list_name_lbl.setText("")
            self.tag_list_empty_lbl.setText("Create or select a tag list.")
            self.tag_list_empty_lbl.setVisible(False)
            self.tag_list_empty_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return

        self.active_tag_list_name_lbl.setText(str(tag_list.get("name") or ""))
        sort_mode = str(tag_list.get("sort_mode") or "none")
        sort_index = max(0, self.tag_list_sort_select.findData(sort_mode))
        self.tag_list_sort_select.blockSignals(True)
        self.tag_list_sort_select.setCurrentIndex(sort_index)
        self.tag_list_sort_select.blockSignals(False)

        scope_counts = self._current_scope_tag_counts()
        selected_tags = self._selected_tag_names_from_editor()
        common_tags, uncommon_tags = self._bulk_tag_selection_states() if self._is_bulk_editor_active() else (set(), set())
        active_filter_key = str(getattr(self, "_active_tag_scope_name", "") or "").casefold()
        entries = list_tag_list_entries(self.bridge.conn, tag_list_id)
        for entry in entries:
            key = str(entry.get("name") or "").casefold()
            entry["scope_use_count"] = int(scope_counts.get(key, 0))
            entry["filter_active"] = bool(active_filter_key and key == active_filter_key)
            if self._is_bulk_editor_active():
                if key in common_tags:
                    entry["selection_state"] = "common"
                elif key in uncommon_tags:
                    entry["selection_state"] = "uncommon"
                else:
                    entry["selection_state"] = "none"
            else:
                entry["selection_state"] = "selected" if key in selected_tags else "none"
        entries = self._sort_tag_list_entries(entries, sort_mode)
        self.tag_list_rows.set_user_sort_enabled(sort_mode == "none")

        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, int(entry.get("tag_id") or 0))
            item.setSizeHint(QSize(0, 36))
            self.tag_list_rows.addItem(item)
            row = TagListTagRow(self.tag_list_rows, item, entry)
            row.addToSelectionRequested.connect(self._add_tag_to_current_editor)
            row.removeFromSelectionRequested.connect(self._remove_tag_from_current_editor)
            row.removeFromListRequested.connect(self._remove_tag_from_active_list)
            row.filterRequested.connect(self._filter_gallery_by_tag)
            self.tag_list_rows.setItemWidget(item, row)

        self.tag_list_empty_lbl.setText("No tags in this list yet." if not entries else "")
        self.tag_list_empty_lbl.setVisible(not entries)
        self.tag_list_empty_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_tag_list_theme()

    def _refresh_tag_list_scope_counts(self) -> None:
        if not hasattr(self, "tag_list_panel") or not self.tag_list_panel.isVisible():
            return
        if not str(getattr(self.bridge, "_current_gallery_tag_scope_search", "") or "").strip():
            self._active_tag_scope_name = ""
        self._invalidate_tag_list_scope_counts_cache()
        self._refresh_tag_list_panel()

    def _refresh_tag_list_rows_state(self) -> None:
        if not hasattr(self, "tag_list_panel") or not self.tag_list_panel.isVisible():
            return
        if not hasattr(self, "tag_list_rows") or self.tag_list_rows.count() <= 0:
            self._refresh_tag_list_panel()
            return

        selected_tags = self._selected_tag_names_from_editor()
        common_tags, uncommon_tags = self._bulk_tag_selection_states() if self._is_bulk_editor_active() else (set(), set())
        active_filter_key = str(getattr(self, "_active_tag_scope_name", "") or "").casefold()
        changed_rows: list[TagListTagRow] = []
        updated_rows = 0
        theme_kwargs = self._tag_list_theme_kwargs()
        if theme_kwargs is None:
            self._refresh_tag_list_panel()
            return

        for index in range(self.tag_list_rows.count()):
            item = self.tag_list_rows.item(index)
            row = self.tag_list_rows.itemWidget(item)
            if not isinstance(row, TagListTagRow):
                continue
            key = str(row.tag_name or "").casefold()
            if self._is_bulk_editor_active():
                if key in common_tags:
                    selection_state = "common"
                elif key in uncommon_tags:
                    selection_state = "uncommon"
                else:
                    selection_state = "none"
            else:
                selection_state = "selected" if key in selected_tags else "none"
            changed = row.update_entry({
                "scope_use_count": row._scope_use_count,
                "global_use_count": row._global_use_count,
                "selection_state": selection_state,
                "filter_active": bool(active_filter_key and key == active_filter_key),
            })
            if changed:
                changed_rows.append(row)
            updated_rows += 1

        if updated_rows != self.tag_list_rows.count():
            self._refresh_tag_list_panel()
            return
        for row in changed_rows:
            row.apply_theme(**theme_kwargs)

    def _tag_list_theme_kwargs(self) -> dict | None:
        if not hasattr(self, "tag_list_rows"):
            return None
        accent = QColor(getattr(self, "_current_accent", Theme.ACCENT_DEFAULT))
        text = Theme.get_text_color()
        text_muted = Theme.get_text_muted()
        return {
            "accent_color": accent.name(),
            "accent_text": Theme.mix(text, accent, 0.78),
            "accent_text_muted": Theme.mix(text_muted, accent, 0.48),
            "text": text,
            "text_muted": text_muted,
            "btn_bg": Theme.get_input_bg(accent),
            "btn_hover": Theme.get_btn_save_hover(accent),
            "btn_border": Theme.get_input_border(accent),
            "btn_border_hover": Theme.mix(Theme.get_border(accent), accent, 0.28),
            "is_light": Theme.get_is_light(),
        }

    def _apply_tag_list_theme(self) -> None:
        theme_kwargs = self._tag_list_theme_kwargs()
        if theme_kwargs is None:
            return
        for index in range(self.tag_list_rows.count()):
            item = self.tag_list_rows.item(index)
            row = self.tag_list_rows.itemWidget(item)
            if isinstance(row, TagListTagRow):
                row.apply_theme(**theme_kwargs)

    def _on_tag_list_changed(self, _index: int) -> None:
        self._refresh_tag_list_panel()

    def _on_tag_list_sort_changed(self, _index: int) -> None:
        from app.mediamanager.db.tag_lists_repo import set_tag_list_sort_mode

        tag_list_id = self._active_tag_list_id()
        if tag_list_id <= 0:
            return
        sort_mode = str(self.tag_list_sort_select.currentData() or "none")
        set_tag_list_sort_mode(self.bridge.conn, tag_list_id, sort_mode)
        self._refresh_tag_list_panel()

    def _persist_active_tag_list_order(self) -> None:
        from app.mediamanager.db.tag_lists_repo import reorder_tag_list_entries

        tag_list_id = self._active_tag_list_id()
        if tag_list_id <= 0:
            return
        if str(self.tag_list_sort_select.currentData() or "none") != "none":
            return
        ordered_ids: list[int] = []
        for index in range(self.tag_list_rows.count()):
            item = self.tag_list_rows.item(index)
            ordered_ids.append(int(item.data(Qt.ItemDataRole.UserRole) or 0))
        reorder_tag_list_entries(self.bridge.conn, tag_list_id, ordered_ids)
        self._save_tag_list_panel_width()

    def _add_tag_to_current_editor(self, tag_name: str) -> None:
        if self._is_bulk_editor_active():
            paths = self._current_file_paths()
            for path in paths:
                try:
                    self.bridge.attach_media_tags(path, [tag_name])
                    self._invalidate_tag_list_scope_counts_cache()
                except Exception:
                    pass
            self.bulk_status_lbl.setText(f"âœ“ Added '{tag_name}' to {len(paths)} selected files")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
            self._refresh_bulk_tag_editor_summary()
            self._refresh_tag_list_rows_state()
            return
        path = str(getattr(self, "_current_path", "") or "").strip()
        if not path:
            return
        editor = self._active_tag_editor()
        next_tags = self._merge_tag_lists(self._normalize_tag_list(self._tag_editor_text(editor)), [tag_name])
        self._set_tag_editor_text(", ".join(next_tags), editor)
        try:
            self.bridge.set_media_tags(path, next_tags)
            self._invalidate_tag_list_scope_counts_cache()
        except Exception:
            pass
        self.meta_status_lbl.setText(f"âœ“ Added '{tag_name}'")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        self._refresh_tag_list_rows_state()

    def _remove_tag_from_current_editor(self, tag_name: str) -> None:
        if self._is_bulk_editor_active():
            from app.mediamanager.db.media_repo import get_media_by_path
            from app.mediamanager.db.tags_repo import list_media_tags

            remove_key = str(tag_name or "").casefold()
            paths = self._current_file_paths()
            for path in paths:
                try:
                    media = get_media_by_path(self.bridge.conn, path)
                    existing = list_media_tags(self.bridge.conn, int(media.get("id") or 0)) if media else []
                    next_tags = [tag for tag in list(existing or []) if str(tag or "").strip() and str(tag).casefold() != remove_key]
                    self.bridge.set_media_tags(path, next_tags)
                    self._invalidate_tag_list_scope_counts_cache()
                except Exception:
                    pass
            self.bulk_status_lbl.setText(f"âœ“ Removed '{tag_name}' from {len(paths)} selected files")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
            self._refresh_bulk_tag_editor_summary()
        self._refresh_tag_list_rows_state()
        return
        remove_key = str(tag_name or "").casefold()
        editor = self._active_tag_editor()
        next_tags = [tag for tag in self._normalize_tag_list(self._tag_editor_text(editor)) if tag.casefold() != remove_key]
        self._set_tag_editor_text(", ".join(next_tags), editor)
        path = str(getattr(self, "_current_path", "") or "").strip()
        if path:
            try:
                self.bridge.set_media_tags(path, next_tags)
                self._invalidate_tag_list_scope_counts_cache()
            except Exception:
                pass
        self.meta_status_lbl.setText(f"Ã¢Å“â€œ Removed '{tag_name}'")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        self._refresh_tag_list_rows_state()

    def _remove_tag_from_active_list(self, tag_id: int, _tag_name: str) -> None:
        from app.mediamanager.db.tag_lists_repo import remove_tag_from_list

        tag_list_id = self._active_tag_list_id()
        if tag_list_id <= 0:
            return
        if remove_tag_from_list(self.bridge.conn, tag_list_id, tag_id):
            self._refresh_tag_list_panel()

    def _filter_gallery_by_tag(self, tag_name: str) -> None:
        escaped_tag_name = str(tag_name or "").replace('"', '\\"')
        query = f'tag:"{escaped_tag_name}"'
        self._active_tag_scope_name = str(tag_name or "").strip()
        try:
            self.web.page().runJavaScript(
                f"try{{ if(window.__mmx_applyTagScopeAndSelectAll){{ window.__mmx_applyTagScopeAndSelectAll({json.dumps(query)}); }}else if(window.__mmx_applyTagScope){{ window.__mmx_applyTagScope({json.dumps(query)}); if(window.selectAll) window.selectAll(); }} }}catch(e){{}}"
            )
        except Exception:
            pass
        self._refresh_tag_list_rows_state()

    def _clear_tag_scope_filter(self) -> None:
        self._active_tag_scope_name = ""
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_clearTagScope && window.__mmx_clearTagScope(); }catch(e){}"
            )
        except Exception:
            pass
        self._refresh_tag_list_rows_state()


    def _clear_preview_media(self) -> None:
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is not None:
            overlay.close_overlay(notify_web=False)
        if self._preview_movie is not None:
            try:
                self._preview_movie.frameChanged.disconnect(self._on_preview_movie_frame_changed)
            except Exception:
                pass
            self._preview_movie.stop()
            self._preview_movie.deleteLater()
            self._preview_movie = None
        self._preview_source_pixmap = None
        self._preview_aspect_ratio = 1.0
        self.preview_image_lbl.setPixmap(QPixmap())
        self._sync_sidebar_video_preview_controls()

    def _ensure_sidebar_video_overlay(self) -> LightboxVideoOverlay:
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is None:
            overlay = LightboxVideoOverlay(parent=self.preview_image_lbl)
            overlay.set_mode(True)
            overlay.on_close = self._sync_sidebar_video_preview_controls
            overlay.on_log = self.bridge._log
            overlay.setGeometry(self.preview_image_lbl.rect())
            overlay.hide()
            self.sidebar_video_overlay = overlay
        return overlay

    def _render_preview_movie_frame(self) -> None:
        movie = self._preview_movie
        if movie is None:
            return
        frame = movie.currentPixmap()
        if frame.isNull():
            return
        available_w = max(120, self._right_panel_content_width() - 8)
        scaled = frame.scaled(
            available_w,
            320,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_image_lbl.setPixmap(scaled)
        self.preview_image_lbl.setFixedHeight(max(96, scaled.height()))
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is not None and overlay.isVisible():
            overlay.setGeometry(self.preview_image_lbl.rect())

    def _on_preview_movie_frame_changed(self, _frame_number: int) -> None:
        self._render_preview_movie_frame()
        self._sync_sidebar_video_preview_controls()

    def _selected_video_path(self) -> str | None:
        path = getattr(self, "_current_path", None)
        if not path:
            return None
        if Path(path).suffix.lower() not in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}:
            return None
        return path

    def _set_preview_play_button_hovered(self, hovered: bool) -> None:
        if not hasattr(self, "btn_preview_overlay_play"):
            return
        size = 57 if hovered else 52
        self.btn_preview_overlay_play.setFixedSize(QSize(size, size))
        self._position_sidebar_preview_play_button()

    def _position_sidebar_preview_play_button(self) -> None:
        if not hasattr(self, "btn_preview_overlay_play"):
            return
        btn = self.btn_preview_overlay_play
        host = self.preview_image_lbl
        x = max(0, (host.width() - btn.width()) // 2)
        y = max(0, (host.height() - btn.height()) // 2)
        btn.move(x, y)
        btn.raise_()

    def _sync_sidebar_video_preview_controls(self) -> None:
        if not hasattr(self, "btn_preview_overlay_play"):
            return
        path = self._selected_video_path()
        preview_visible = hasattr(self, "preview_image_lbl") and self.preview_image_lbl.isVisible()
        has_preview = (
            (self._preview_movie is not None) or
            (self._preview_source_pixmap is not None and not self._preview_source_pixmap.isNull())
        )
        overlay = getattr(self, "sidebar_video_overlay", None)
        overlay_open = overlay is not None and overlay.isVisible()
        show_overlay_play = bool(path and preview_visible and has_preview and not overlay_open)
        self.btn_preview_overlay_play.setVisible(show_overlay_play)
        self.btn_preview_overlay_play.setEnabled(show_overlay_play)
        self._position_sidebar_preview_play_button()

    def _update_preview_play_button_icon(self) -> None:
        if not hasattr(self, "btn_preview_overlay_play"):
            return
        asset_path = Path(__file__).with_name("web") / "icons" / "play.svg"
        renderer = QSvgRenderer(str(asset_path))
        if not renderer.isValid():
            self.btn_preview_overlay_play.setIcon(QIcon())
            return

        canvas_size = 42
        icon_rect = QRect(6, 6, 30, 30)

        shadow_mask = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
        shadow_mask.fill(Qt.GlobalColor.transparent)
        shadow_painter = QPainter(shadow_mask)
        shadow_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(shadow_painter, icon_rect)
        shadow_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        shadow_painter.fillRect(shadow_mask.rect(), QColor(0, 0, 0, 255))
        shadow_painter.end()

        icon_image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
        icon_image.fill(Qt.GlobalColor.transparent)
        icon_painter = QPainter(icon_image)
        icon_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(icon_painter, icon_rect)
        icon_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        icon_painter.fillRect(icon_image.rect(), QColor("#ffffff"))
        icon_painter.end()

        image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        glow_layers = [
            (0, 0, 0.55),
            (-1, 0, 0.40), (1, 0, 0.40), (0, -1, 0.40), (0, 1, 0.40),
            (-2, 0, 0.28), (2, 0, 0.28), (0, -2, 0.28), (0, 2, 0.28),
            (-1, -1, 0.22), (1, 1, 0.22), (-1, 1, 0.22), (1, -1, 0.22),
            (-3, 0, 0.14), (3, 0, 0.14), (0, -3, 0.14), (0, 3, 0.14),
        ]
        for dx, dy, opacity in glow_layers:
            painter.setOpacity(opacity)
            painter.drawImage(dx, dy, shadow_mask)

        painter.setOpacity(1.0)
        painter.drawImage(0, 0, icon_image)
        painter.end()

        self.btn_preview_overlay_play.setIcon(QIcon(QPixmap.fromImage(image)))

    def _apply_preview_image_label_style(self) -> None:
        if not hasattr(self, "preview_image_lbl"):
            return
        accent = QColor(getattr(self, "_current_accent", Theme.ACCENT_DEFAULT))
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        hint = str(getattr(self, "_preview_bg_hint", "") or "")
        if hint == "light":
            bg = "#ffffff" if Theme.get_is_light() else "#f7f8fa"
        elif hint == "dark":
            bg = "#101114"
        else:
            bg = Theme.get_control_bg(accent)
        self.preview_image_lbl.setStyleSheet(
            "QLabel#previewImageLabel {"
            f"background-color: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 6px; color: {text};"
            "}"
        )

    def _update_preview_display(self, placeholder: str = "No preview") -> None:
        self._apply_preview_image_label_style()
        available_w = max(120, self._right_panel_content_width() - 8)
        self.preview_image_lbl.setFixedWidth(self._right_panel_content_width())
        target_h = max(96, min(320, int(available_w / max(0.2, self._preview_aspect_ratio))))

        if self._preview_movie is not None:
            self.preview_image_lbl.setText("")
            movie_rect = self._preview_movie.currentPixmap().rect()
            if movie_rect.isEmpty():
                movie_rect = self._preview_movie.frameRect()
            movie_w = max(1, movie_rect.width())
            movie_h = max(1, movie_rect.height())
            movie_aspect = max(0.2, movie_w / movie_h)
            scaled_h = max(96, min(320, int(available_w / movie_aspect)))
            self.preview_image_lbl.setFixedHeight(scaled_h)
            autoplay_gifs = self.bridge._autoplay_preview_animated_gifs_enabled()
            if autoplay_gifs and self._preview_movie.state() != QMovie.MovieState.Running:
                self._preview_movie.start()
            elif not autoplay_gifs and self._preview_movie.state() == QMovie.MovieState.Running:
                self._preview_movie.stop()
            self._render_preview_movie_frame()
            overlay = getattr(self, "sidebar_video_overlay", None)
            if overlay is not None and overlay.isVisible():
                overlay.setGeometry(self.preview_image_lbl.rect())
            self._sync_sidebar_video_preview_controls()
            return

        if self._preview_source_pixmap is not None and not self._preview_source_pixmap.isNull():
            self.preview_image_lbl.setText("")
            scaled = self._preview_source_pixmap.scaled(
                available_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_image_lbl.setFixedHeight(max(96, scaled.height()))
            self.preview_image_lbl.setPixmap(scaled)
            overlay = getattr(self, "sidebar_video_overlay", None)
            if overlay is not None and overlay.isVisible():
                overlay.setGeometry(self.preview_image_lbl.rect())
            self._sync_sidebar_video_preview_controls()
            return

        self.preview_image_lbl.setFixedHeight(96)
        self.preview_image_lbl.setText(placeholder)
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is not None and overlay.isVisible():
            overlay.setGeometry(self.preview_image_lbl.rect())
        self._sync_sidebar_video_preview_controls()

    def _set_preview_pixmap(self, pixmap: QPixmap | None, placeholder: str = "No preview", bg_hint: str = "") -> None:
        self._clear_preview_media()
        self._preview_bg_hint = str(bg_hint or "")
        self._preview_source_pixmap = pixmap if pixmap and not pixmap.isNull() else None
        if self._preview_source_pixmap is not None:
            self._preview_aspect_ratio = max(
                0.2,
                self._preview_source_pixmap.width() / max(1, self._preview_source_pixmap.height()),
            )
        self._update_preview_display(placeholder)

    def _set_preview_movie(self, path: Path, aspect_ratio: float) -> None:
        self._clear_preview_media()
        self._preview_bg_hint = ""
        movie = QMovie(str(path))
        if not movie.isValid():
            self._set_preview_pixmap(None)
            return
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.setSpeed(100)
        movie.finished.connect(movie.start)
        try:
            movie.start()
            movie.jumpToFrame(0)
            movie_rect = movie.currentPixmap().rect()
            if movie_rect.isEmpty():
                movie_rect = movie.frameRect()
            if not movie_rect.isEmpty() and movie_rect.height() > 0:
                aspect_ratio = movie_rect.width() / movie_rect.height()
            movie.stop()
        except Exception:
            pass
        self._preview_movie = movie
        movie.frameChanged.connect(self._on_preview_movie_frame_changed)
        self._preview_aspect_ratio = max(0.2, aspect_ratio)
        self.preview_image_lbl.setText("")
        self._update_preview_display("No preview")

    def _load_video_preview_async(self, path: str) -> None:
        def work() -> None:
            poster_path = ""
            try:
                poster = self.bridge._ensure_video_poster(Path(path))
                if poster and poster.exists():
                    poster_path = str(poster)
            except Exception:
                poster_path = ""
            self.videoSidebarPosterReady.emit(path, poster_path)
        threading.Thread(target=work, daemon=True).start()

    @Slot(str, str)
    def _on_video_sidebar_poster_ready(self, path: str, poster_path: str) -> None:
        if getattr(self, "_current_path", None) != path:
            return
        if poster_path and Path(poster_path).exists():
            self._refresh_preview_for_path(path)
        else:
            self._set_preview_pixmap(None, "No video preview")

    def _play_selected_video_in_sidebar(self) -> None:
        if getattr(self, "_video_preview_transition_active", False):
            return
        path = self._selected_video_path()
        if not path:
            return
        muted = self.bridge._mute_video_by_default_enabled()
        width = int(getattr(self, "_current_video_width", 0) or 0)
        height = int(getattr(self, "_current_video_height", 0) or 0)
        duration_ms = int(getattr(self, "_current_video_duration_ms", 0) or 0)
        should_loop = self.bridge._should_loop_video(duration_ms)
        if hasattr(self, "video_overlay") and self.video_overlay.isVisible():
            self.video_overlay.close_overlay(notify_web=False)
        overlay = self._ensure_sidebar_video_overlay()
        overlay.setGeometry(self.preview_image_lbl.rect())
        overlay.set_mode(True)
        overlay.open_video(
            VideoRequest(
                path=path,
                autoplay=True,
                loop=should_loop,
                muted=muted,
                width=width,
                height=height,
            )
        )
        overlay.raise_()
        self._sync_sidebar_video_preview_controls()

    def _open_selected_video_lightbox(self) -> None:
        if getattr(self, "_video_preview_transition_active", False):
            return
        path = self._selected_video_path()
        if not path:
            return
        muted = self.bridge._mute_video_by_default_enabled()
        width = int(getattr(self, "_current_video_width", 0) or 0)
        height = int(getattr(self, "_current_video_height", 0) or 0)
        duration_ms = int(getattr(self, "_current_video_duration_ms", 0) or 0)
        should_loop = self.bridge._should_loop_video(duration_ms)
        self._video_preview_transition_active = True
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is not None:
            overlay.close_overlay(notify_web=False)
        if hasattr(self, "video_overlay"):
            self.video_overlay.close_overlay(notify_web=False)
        QApplication.processEvents()

        def _finish_open() -> None:
            try:
                self.bridge.open_native_video(path, True, should_loop, muted, width, height)
            finally:
                self._video_preview_transition_active = False
                self._sync_sidebar_video_preview_controls()

        QTimer.singleShot(120, _finish_open)

    def _refresh_preview_for_path(self, path: str | None) -> None:
        if not hasattr(self, "preview_image_lbl"):
            return
        if not path:
            self._set_preview_pixmap(None)
            return
        p = Path(path)
        if not p.exists() or p.is_dir():
            self._set_preview_pixmap(None)
            return
        suffix = p.suffix.lower()
        preview_path = p
        if suffix in VIDEO_EXTS:
            poster = self.bridge._video_poster_path(p)
            if not poster.exists():
                self._set_preview_pixmap(None, "Loading video preview...")
                overlay = getattr(self, "sidebar_video_overlay", None)
                if overlay is not None:
                    overlay.close_overlay(notify_web=False)
                self._load_video_preview_async(str(p))
                return
            preview_path = poster
        size = _image_size_with_svg_support(preview_path)
        
        # Fallback for AVIF/unsupported formats
        if suffix == ".avif":
            # Native QImageReader usually fails for AVIF without plugins
            poster = self.bridge._ensure_video_poster(p)
            if poster and poster.exists():
                preview_path = poster
                size = _image_size_with_svg_support(preview_path)

        aspect_ratio = max(0.2, size.width() / max(1, size.height())) if size.isValid() else 1.0
        if suffix == ".gif" and self.bridge._autoplay_preview_animated_gifs_enabled():
            self._set_preview_movie(p, aspect_ratio)
            return
        img = _read_image_with_svg_support(preview_path)
        if img is None or img.isNull():
            self._set_preview_pixmap(None)
            return
        self._set_preview_pixmap(QPixmap.fromImage(img), bg_hint=_thumbnail_bg_hint(preview_path))
        if suffix in VIDEO_EXTS:
            overlay = getattr(self, "sidebar_video_overlay", None)
            if overlay is not None:
                overlay.close_overlay(notify_web=False)
        else:
            overlay = getattr(self, "sidebar_video_overlay", None)
            if overlay is not None:
                overlay.close_overlay(notify_web=False)


    def _rename_from_panel(self) -> None:
        """Rename the current file using the filename field in the metadata panel."""
        if not hasattr(self, "_current_path") or not self._current_path:
            return
        new_name = self.meta_filename_edit.text().strip()
        if not new_name:
            return
        p = Path(self._current_path)
        if new_name == p.name:
            return
        new_path = p.parent / new_name
        try:
            self.bridge.rename_path_async(self._current_path, new_name)
            self._current_path = str(new_path)
        except Exception:
            pass

    def _save_native_metadata(self) -> None:
        """Save rename (if changed) + description/tags/notes, then show confirmation."""
        # Use paths list if available, else fallback to current_path
        paths = self._current_file_paths()
        if not paths and hasattr(self, "_current_path") and self._current_path:
            paths = [self._current_path]
            
        if not paths:
            return

        is_bulk = len(paths) > 1
        tags_str = self._tag_editor_text()
        tags = self._normalize_tag_list(tags_str)

        if not is_bulk:
            path = paths[0]
            # --- Rename if the filename was changed ---
            new_name = self.meta_filename_edit.text().strip()
            p = Path(path)
            if new_name and new_name != p.name:
                new_path = p.parent / new_name
                try:
                    self.bridge.rename_path_async(path, new_name)
                    path = str(new_path)
                    self._current_path = path
                    self._current_paths = [path]
                except Exception:
                    pass

            # --- Save metadata fields ---
            desc = self.meta_desc.toPlainText()
            notes = self.meta_notes.toPlainText()
            detected_text = self.meta_detected_text_edit.toPlainText()
            
            ai_prompt = self.meta_ai_prompt_edit.toPlainText()
            ai_neg_prompt = self.meta_ai_negative_prompt_edit.toPlainText()
            ai_params = self.meta_ai_params_edit.toPlainText()
            current_ai_meta = dict(getattr(self, "_current_ai_meta", {}) or {})
            is_ai_detected = bool(current_ai_meta.get("is_ai_detected"))
            is_ai_confidence = float(current_ai_meta.get("is_ai_confidence") or 0.0)
            ai_override_dirty = bool(getattr(self, "_ai_generated_override_dirty", False))
            text_override_dirty = bool(getattr(self, "_text_detected_override_dirty", False))
            existing_ai_override = current_ai_meta.get("user_confirmed_ai")
            existing_text_override = getattr(self, "_current_user_confirmed_text_detected", None)
            user_confirmed_ai = (
                bool(self.meta_ai_generated_toggle.isChecked())
                if ai_override_dirty or existing_ai_override is not None
                else ""
            )
            user_confirmed_text_detected = (
                bool(self.meta_text_detected_toggle.isChecked())
                if text_override_dirty or existing_text_override is not None
                else None
            )
            source_override = self._parse_ai_source_override(self.meta_ai_source_edit.toPlainText(), current_ai_meta)
            ai_detection_reasons = self._parse_ai_text_list(self.meta_ai_detection_reasons_edit.toPlainText())
            if user_confirmed_ai != "" and user_confirmed_ai != current_ai_meta.get("user_confirmed_ai") and not ai_detection_reasons:
                ai_detection_reasons = ["Manual override from details panel"]
            ai_payload = {
                "is_ai_detected": is_ai_detected,
                "is_ai_confidence": is_ai_confidence,
                "user_confirmed_ai": user_confirmed_ai,
                "tool_name_found": source_override.get("tool_name_found"),
                "tool_name_inferred": source_override.get("tool_name_inferred"),
                "tool_name_confidence": source_override.get("tool_name_confidence"),
                "source_formats": source_override.get("source_formats"),
                "ai_prompt": ai_prompt,
                "ai_negative_prompt": ai_neg_prompt,
                "description": desc,
                "model_name": self.meta_ai_model_edit.text().strip(),
                "checkpoint_name": self.meta_ai_checkpoint_edit.text().strip(),
                "sampler": self.meta_ai_sampler_edit.text().strip(),
                "scheduler": self.meta_ai_scheduler_edit.text().strip(),
                "cfg_scale": self._parse_optional_float(self.meta_ai_cfg_edit.text()),
                "steps": self._parse_optional_int(self.meta_ai_steps_edit.text()),
                "seed": self.meta_ai_seed_edit.text().strip() or None,
                "upscaler": self.meta_ai_upscaler_edit.text().strip(),
                "denoise_strength": self._parse_optional_float(self.meta_ai_denoise_edit.text()),
                "metadata_families_detected": self._parse_ai_text_list(self.meta_ai_families_edit.text()),
                "ai_detection_reasons": ai_detection_reasons,
            }
            exif_date_taken = self._normalize_metadata_datetime(self.meta_exif_date_taken_edit.text())
            metadata_date = self._normalize_metadata_datetime(self.meta_metadata_date_edit.text())

            try:
                # Save Changes is DB-only. Embedded fields are file-only and should not be persisted here.
                self.bridge.update_media_metadata(path, "", desc, notes, "", "", ai_prompt, ai_neg_prompt, ai_params)
                self.bridge.update_media_ai_metadata(path, ai_payload)
                if user_confirmed_text_detected is not None:
                    self.bridge.update_media_text_override(path, user_confirmed_text_detected)
                self.bridge.update_media_detected_text(path, detected_text)
                self.bridge.update_media_dates(path, exif_date_taken, metadata_date)
                self.bridge.set_media_tags(path, tags)
                self._invalidate_tag_list_scope_counts_cache()
                self._current_ai_meta = {
                    "is_ai_detected": is_ai_detected,
                    "is_ai_confidence": is_ai_confidence,
                    "user_confirmed_ai": bool(user_confirmed_ai) if user_confirmed_ai != "" else existing_ai_override,
                    "tool_name_found": source_override.get("tool_name_found"),
                    "tool_name_inferred": source_override.get("tool_name_inferred"),
                    "tool_name_confidence": source_override.get("tool_name_confidence"),
                    "source_formats": list(source_override.get("source_formats") or []),
                }
                if user_confirmed_text_detected is not None:
                    self._current_user_confirmed_text_detected = user_confirmed_text_detected
                self._ai_generated_override_dirty = False
                self._text_detected_override_dirty = False
            except Exception:
                pass
        else:
            for p in paths:
                try:
                    existing = self.bridge.get_media_metadata(p).get("tags", [])
                    self.bridge.set_media_tags(p, self._merge_tag_lists(existing, tags))
                    self._invalidate_tag_list_scope_counts_cache()
                except Exception:
                    pass

        status_label = self._active_status_label()
        status_label.setText(f"âœ“ {'Tags' if is_bulk else 'Changes'} saved")
        QTimer.singleShot(3000, lambda: status_label.setText(""))
        self._refresh_tag_list_scope_counts()
        return

        # --- Show confirmation then auto-clear after 3s ---
        self.meta_status_lbl.setText(f"âœ“ {'Tags' if is_bulk else 'Changes'} saved")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        if hasattr(self, "bulk_status_lbl"):
            self.bulk_status_lbl.setText(f"âœ“ Tags cleared for {len(paths)} items")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
        if hasattr(self, "bulk_status_lbl"):
            self.bulk_status_lbl.setText(f"âœ“ Tags cleared for {len(paths)} items")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
        if is_bulk and hasattr(self, "bulk_status_lbl"):
            self.bulk_status_lbl.setText("âœ“ Tags saved")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
        self._refresh_tag_list_scope_counts()

    def _harvest_universal_metadata(self, img) -> dict:
        """Systematically extract tags/comments from XMP, IPTC, and all EXIF IFDs."""
        from PIL import ExifTags, IptcImagePlugin
        res = {"tags": [], "comment": "", "tool_metadata": "", "ai_prompt": "", "ai_params": ""}

        def add_comment(val):
            if not val: return
            if isinstance(val, (bytes, bytearray)):
                try: val = val.decode("utf-8", errors="replace").strip()
                except: val = str(val).strip()
            else:
                val = str(val).strip()
                
            if val:
                # Strip XML/HTML tags if present
                clean = re.sub(r'<[^>]+>', '', val).strip()
                if not clean: return
                if not res["comment"]: res["comment"] = clean
                elif clean not in res["comment"]: res["comment"] = f"{res['comment']}\n{clean}"

        def add_tool_meta(key, val):
            if not val: return
            s_val = str(val).strip()
            if not s_val: return
            entry = f"[{key}]\n{s_val}"
            if not res["tool_metadata"]: res["tool_metadata"] = entry
            elif entry not in res["tool_metadata"]: res["tool_metadata"] = f"{res['tool_metadata']}\n\n{entry}"

        def add_tags(val):
            if not val: return
            if isinstance(val, (bytes, bytearray, list, tuple)):
                if isinstance(val, (bytes, bytearray)):
                    try: val = val.decode("utf-8", errors="replace").strip()
                    except: val = str(val).strip()
                else: # list/tuple
                    for v in val: add_tags(v)
                    return

            if val:
                # Split and strip tags, ensuring we don't include XML junk
                clean_val = re.sub(r'<[^>]+>', '', str(val)).strip()
                # Handle both comma and semicolon
                parts = [t.strip() for t in clean_val.replace(";", ",").split(",") if t.strip()]
                for p in parts:
                    if p not in res["tags"]: res["tags"].append(p)

        # 1. Standard Info & PNG Text
        if hasattr(img, "info"):
            for k, v in img.info.items():
                k_low = str(k).lower()
                if k_low in ("comment", "description", "usercomment", "title", "subject", "author", "copyright"):
                    add_comment(v)
                elif k_low in ("parameters", "software", "hardware", "tool", "civitai metadata"):
                    add_tool_meta(k, v)
                elif k_low in ("keywords", "tags"):
                    add_tags(v)
                elif k == "xmp" and isinstance(v, (bytes, str)):
                    txt = v.decode(errors="replace") if isinstance(v, bytes) else v
                    # Robust Subject (Tags)
                    subj_match = re.search(r"<dc:subject>(.*?)</dc:subject>", txt, re.DOTALL | re.IGNORECASE)
                    if subj_match:
                        tags = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", subj_match.group(1), re.DOTALL)
                        for t in tags: add_tags(t)
                    # Robust Description (Comments)
                    desc_match = re.search(r"<dc:description>(.*?)</dc:description>", txt, re.DOTALL | re.IGNORECASE)
                    if desc_match:
                        descs = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", desc_match.group(1), re.DOTALL)
                        for d in descs: add_comment(d)
                    # Check for Hierarchical Subject (lr:hierarchicalSubject)
                    hier_match = re.search(r"<lr:hierarchicalSubject>(.*?)</lr:hierarchicalSubject>", txt, re.DOTALL | re.IGNORECASE)
                    if hier_match:
                        htags = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", hier_match.group(1), re.DOTALL)
                        for h in htags: add_tags(h)

        # 2. IPTC
        try:
            iptc = IptcImagePlugin.getiptcinfo(img)
            if iptc:
                for k, v in iptc.items():
                    if k == (2, 120): add_comment(v)
                    elif k == (2, 5): add_tags(v) # Title (as tag)
                    elif k == (2, 25): add_tags(v) # Keywords
        except: pass

        # 3. EXIF (Root & Sub-IFDs)
        exif = img.getexif()
        if exif:
            def scan_ifd(ifd_obj):
                if not ifd_obj: return
                for tid, val in ifd_obj.items():
                    name = ExifTags.TAGS.get(tid, str(tid))
                    # Native decoding for XP Tags
                    if tid in (0x9c9b, 0x9c9c, 0x9c9d, 0x9c9e, 0x9c9f):
                        if isinstance(val, (bytes, bytearray)):
                            try: val = val.decode("utf-16le", errors="replace").rstrip("\x00")
                            except: pass
                    
                    if tid == 0x9c9c or name in ("XPComment", "Comment", "ImageDescription"):
                        add_comment(val)
                    elif tid == 37510: # UserComment
                        if isinstance(val, (bytes, bytearray)):
                            try:
                                prefix = val[:8].upper()
                                if b"UNICODE" in prefix: val = val[8:].decode("utf-16le", errors="replace").rstrip("\x00")
                                elif b"ASCII" in prefix: val = val[8:].decode("ascii", errors="replace").rstrip("\x00")
                                else: val = val.decode(errors="replace").rstrip("\x00")
                            except: pass
                        add_comment(val)
                    elif tid == 0x9c9e or name in ("XPKeywords", "Keywords", "Subject"):
                        add_tags(val)
                    elif name in ("Software", "Artist", "Make", "Model"):
                        add_tool_meta(name, val)

            scan_ifd(exif)
            for ifd_id in [ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo, ExifTags.IFD.Interop]:
                try: scan_ifd(exif.get_ifd(ifd_id))
                except: pass

        # Deduplicate results
        res["tags"] = sorted(list(set(res["tags"])))
        return res

    @staticmethod
    def _decode_xp_field(val):
        if val is None:
            return ""
        if isinstance(val, (bytes, bytearray)):
            try:
                return bytes(val).decode("utf-16le", errors="replace").rstrip("\x00").strip()
            except Exception:
                return bytes(val).decode(errors="replace").rstrip("\x00").strip()
        if isinstance(val, (list, tuple)):
            try:
                return bytes(val).decode("utf-16le", errors="replace").rstrip("\x00").strip()
            except Exception:
                try:
                    return "".join(chr(x) for x in val if isinstance(x, int)).rstrip("\x00").strip()
                except Exception:
                    return str(val).strip()
        return str(val).strip()

    @staticmethod
    def _decode_user_comment_field(val):
        if val is None:
            return ""
        if isinstance(val, (bytes, bytearray)):
            raw = bytes(val)
            try:
                prefix = raw[:8].upper()
                body = raw[8:] if len(raw) >= 8 else raw
                if b"UNICODE" in prefix:
                    return body.decode("utf-16le", errors="replace").rstrip("\x00").strip()
                if b"ASCII" in prefix:
                    return body.decode("ascii", errors="replace").rstrip("\x00").strip()
                return raw.decode(errors="replace").rstrip("\x00").strip()
            except Exception:
                return str(val).strip()
        return str(val).strip()

    @staticmethod
    def _build_png_xmp_packet(comment: str, tags: list[str], exif_date_taken: str = "", metadata_date: str = "") -> str:
        """Build a minimal XMP packet for PNG that Windows/tools can parse.

        Windows Explorer reliably reads PNG tags from XMP dc:subject on many systems.
        For PNG comments, Windows maps System.Comment from exif:UserComment only when
        encoded as an rdf:Alt localized string (not a plain text node).
        """
        safe_comment = html.escape(comment or "", quote=False)
        safe_tags = [html.escape(t, quote=False) for t in (tags or []) if str(t).strip()]
        tag_items = "".join(f"<rdf:li>{t}</rdf:li>" for t in safe_tags)
        safe_exif_date_taken = html.escape(exif_date_taken or "", quote=False)
        safe_metadata_date = html.escape(metadata_date or "", quote=False)

        parts = []
        if safe_comment:
            # Avoid writing dc:description/dc:title here because Windows can map
            # those to System.Title for PNG, which causes long comments to appear in
            # the Title field instead of Comments.
            parts.append(
                "<exif:UserComment><rdf:Alt>"
                f"<rdf:li xml:lang=\"x-default\">{safe_comment}</rdf:li>"
                "</rdf:Alt></exif:UserComment>"
            )
        if tag_items:
            parts.append(f"<dc:subject><rdf:Bag>{tag_items}</rdf:Bag></dc:subject>")
        if safe_exif_date_taken:
            parts.append(f"<exif:DateTimeOriginal>{safe_exif_date_taken}</exif:DateTimeOriginal>")
        if safe_metadata_date:
            parts.append(f"<xmp:CreateDate>{safe_metadata_date}</xmp:CreateDate>")
            parts.append(f"<xmp:MetadataDate>{safe_metadata_date}</xmp:MetadataDate>")
            parts.append(f"<MicrosoftPhoto:DateAcquired>{safe_metadata_date}</MicrosoftPhoto:DateAcquired>")

        if not parts:
            return ""

        body = "".join(parts)
        return (
            "<?xpacket begin=\"\ufeff\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?>"
            "<x:xmpmeta xmlns:x=\"adobe:ns:meta/\">"
            "<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\">"
            "<rdf:Description rdf:about=\"\" "
            "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
            "xmlns:exif=\"http://ns.adobe.com/exif/1.0/\" "
            "xmlns:xmp=\"http://ns.adobe.com/xap/1.0/\" "
            "xmlns:MicrosoftPhoto=\"http://ns.microsoft.com/photo/1.2/\">"
            f"{body}"
            "</rdf:Description>"
            "</rdf:RDF>"
            "</x:xmpmeta>"
            "<?xpacket end=\"w\"?>"
        )

    def _harvest_windows_visible_metadata(self, img) -> dict:
        """Return only fields meant to mirror Windows Explorer Tags/Comments."""
        result = {"tags": [], "comment": ""}

        def add_comment(val):
            if val is None:
                return
            s = str(val).strip()
            if s and not result["comment"]:
                result["comment"] = s

        def add_tags(val):
            if val is None:
                return
            if isinstance(val, (bytes, bytearray, list, tuple)):
                if isinstance(val, (list, tuple)) and not isinstance(val, (bytes, bytearray)):
                    for item in val:
                        add_tags(item)
                    return
                s = self._decode_xp_field(val)
            else:
                s = str(val).strip()
            for part in s.replace(",", ";").split(";"):
                tag = part.strip()
                if tag and tag not in result["tags"]:
                    result["tags"].append(tag)

        if hasattr(img, "info"):
            for k, v in img.info.items():
                key = str(k).strip().lower()
                if key in {"comment", "comments", "description"}:
                    add_comment(v)
                elif key in {"keywords", "tags"}:
                    add_tags(v)
                elif key in {"xmp", "xml:com.adobe.xmp"}:
                    try:
                        xmp_txt = v.decode(errors="replace") if isinstance(v, (bytes, bytearray)) else str(v)
                    except Exception:
                        xmp_txt = str(v)
                    # Windows/tool PNG metadata commonly lives in XMP.
                    for m in re.findall(r"<dc:subject>(.*?)</dc:subject>", xmp_txt, re.DOTALL | re.IGNORECASE):
                        for li in re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", m, re.DOTALL | re.IGNORECASE):
                            add_tags(re.sub(r"<[^>]+>", "", li))
                    if not result["comment"]:
                        m = re.search(r"<exif:UserComment[^>]*>(.*?)</exif:UserComment>", xmp_txt, re.DOTALL | re.IGNORECASE)
                        if m:
                            add_comment(re.sub(r"<[^>]+>", "", m.group(1)))
                    if not result["comment"]:
                        m = re.search(r"<dc:description>(.*?)</dc:description>", xmp_txt, re.DOTALL | re.IGNORECASE)
                        if m:
                            vals = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", m.group(1), re.DOTALL | re.IGNORECASE)
                            if vals:
                                add_comment(re.sub(r"<[^>]+>", "", vals[0]))
                    if not result["comment"]:
                        m = re.search(r"<dc:title>(.*?)</dc:title>", xmp_txt, re.DOTALL | re.IGNORECASE)
                        if m:
                            vals = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", m.group(1), re.DOTALL | re.IGNORECASE)
                            if vals:
                                add_comment(re.sub(r"<[^>]+>", "", vals[0]))

        try:
            exif = img.getexif()
        except Exception:
            exif = None
        if exif:
            xp_comment = exif.get(0x9C9C)
            if xp_comment:
                add_comment(self._decode_xp_field(xp_comment))
            if not result["comment"]:
                img_desc = exif.get(270)
                if img_desc:
                    add_comment(img_desc)
            if not result["comment"]:
                user_comment = exif.get(37510)
                if user_comment:
                    add_comment(self._decode_user_comment_field(user_comment))

            xp_keywords = exif.get(0x9C9E)
            if xp_keywords:
                add_tags(self._decode_xp_field(xp_keywords))
            xp_subject = exif.get(0x9C9F)
            if xp_subject:
                add_tags(self._decode_xp_field(xp_subject))

        return result

    @Slot()
    def _import_exif_to_db(self):
        """Action for 'Import Metadata' button: Strictly File -> UI.
        
        This should REPLACE the Embedded UI fields with file data.
        It should APPEND file tags to the Database Tags UI field.
        It does NOT automatically save to the database.
        """
        path = self._current_path
        if not path:
            return

        p = Path(path)
        if not p.exists():
            return

        try:
            from app.mediamanager.db.ai_metadata_repo import (
                build_media_ai_ui_fields,
                get_media_ai_metadata,
                summarize_media_ai_tool_metadata,
            )
            from app.mediamanager.db.media_repo import add_media_item, get_media_by_path
            from app.mediamanager.db.metadata_repo import get_media_metadata
            from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
            visible = {"comment": "", "tags": []}
            res = {"tool_metadata": ""}
            if p.suffix.lower() != ".svg":
                from PIL import Image
                with Image.open(str(p)) as img:
                    try:
                        img.load()
                    except Exception:
                        pass
                    visible = self._harvest_windows_visible_metadata(img)
                    res = self._harvest_universal_metadata(img)
            media = get_media_by_path(self.bridge.conn, path)
            if not media:
                media_type = "image" if p.suffix.lower() in IMAGE_EXTS else "video"
                add_media_item(self.bridge.conn, path, media_type)
                media = get_media_by_path(self.bridge.conn, path)
            ai_ui = {}
            ai_tool_summary = ""
            meta = {}
            if media:
                inspect_and_persist_if_supported(self.bridge.conn, media["id"], path, media.get("media_type"))
                media = get_media_by_path(self.bridge.conn, path) or media
                meta = get_media_metadata(self.bridge.conn, media["id"]) or {}
                ai_meta = get_media_ai_metadata(self.bridge.conn, media["id"]) or {}
                ai_ui = build_media_ai_ui_fields(ai_meta)
                ai_tool_summary = summarize_media_ai_tool_metadata(ai_meta) or ""

            has_pipeline_data = any(
                [
                    ai_ui.get("ai_status_summary"),
                    ai_ui.get("ai_source_summary"),
                    ai_ui.get("ai_families_summary"),
                    ai_ui.get("ai_loras_summary"),
                    ai_ui.get("ai_workflows_summary"),
                    ai_ui.get("ai_provenance_summary"),
                    ai_ui.get("ai_character_cards_summary"),
                    ai_ui.get("ai_raw_paths_summary"),
                    meta.get("embedded_metadata_summary"),
                ]
            )
            has_date_data = bool((media or {}).get("exif_date_taken") or (media or {}).get("metadata_date"))
            if not visible["comment"] and not visible["tags"] and not res["tool_metadata"] and not has_pipeline_data and not has_date_data:
                self.meta_status_lbl.setText("No metadata found in file.")
                return

            # 1. REPLACE Embedded UI fields (Strictly File -> UI)
            self.meta_embedded_tags_edit.setText("; ".join(visible["tags"]))
            self.meta_embedded_comments_edit.setPlainText(visible["comment"] or "")
            self.meta_ai_status_edit.setText(ai_ui.get("ai_status_summary", ""))
            self.meta_ai_source_edit.setPlainText(ai_ui.get("ai_source_summary", ""))
            self.meta_ai_families_edit.setText(ai_ui.get("ai_families_summary", ""))
            self.meta_ai_detection_reasons_edit.setPlainText(ai_ui.get("ai_detection_reasons_summary", ""))
            self.meta_ai_loras_edit.setPlainText(ai_ui.get("ai_loras_summary", ""))
            self.meta_ai_workflows_edit.setPlainText(ai_ui.get("ai_workflows_summary", ""))
            self.meta_ai_provenance_edit.setPlainText(ai_ui.get("ai_provenance_summary", ""))
            self.meta_ai_character_cards_edit.setPlainText(ai_ui.get("ai_character_cards_summary", ""))
            self.meta_ai_raw_paths_edit.setPlainText(ai_ui.get("ai_raw_paths_summary", ""))
            self.meta_embedded_metadata_edit.setPlainText(meta.get("embedded_metadata_summary", ""))
            self.meta_exif_date_taken_edit.setText(self._format_editable_datetime((media or {}).get("exif_date_taken")))
            self.meta_metadata_date_edit.setText(self._format_editable_datetime((media or {}).get("metadata_date")))
            original_file_text = self._format_sidebar_datetime((media or {}).get("original_file_date"))
            if original_file_text:
                self.meta_original_file_date_lbl.setText(original_file_text)
            file_created_text = self._format_sidebar_datetime((media or {}).get("file_created_time"))
            if file_created_text:
                self.meta_file_created_date_lbl.setText(file_created_text)
            file_modified_text = self._format_sidebar_datetime((media or {}).get("modified_time"))
            if file_modified_text:
                self.meta_file_modified_date_lbl.setText(file_modified_text)

            # 2. Status update
            self.meta_status_lbl.setText("Metadata imported to UI. Click 'Save Changes' to persist.")
        except Exception as e:
            self.meta_status_lbl.setText(f"Import Error: {e}")

    @staticmethod
    def _parse_embed_comment(text: str) -> dict:
        """Parse a bracketed-header comment string into a dict of sections.
        Recognizes [Description], [Comments], [AI Prompt], [AI Negative Prompt], [AI Params], [Notes].
        If no headers are found, treats entire text as [Comments]."""
        import re
        result = {"description": "", "comments": "", "ai_prompt": "", "ai_negative_prompt": "", "ai_params": "", "notes": ""}
        pattern = re.compile(r'^\[([^\]]+)\]\s*$', re.MULTILINE)
        parts = pattern.split(text)
        if len(parts) == 1:
            # No headers â€“ treat whole thing as plain comment
            result["comments"] = text.strip()
            return result
        # parts[0] = text before first header (usually blank)
        for i in range(1, len(parts), 2):
            header = parts[i].strip().lower()
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if header == "description":
                result["description"] = content
            elif header == "comments":
                result["comments"] = content
            elif header == "ai prompt":
                result["ai_prompt"] = content
            elif header == "ai negative prompt":
                result["ai_negative_prompt"] = content
            elif header == "ai params" or header == "ai parameters":
                result["ai_params"] = content
            elif header == "notes":
                result["notes"] = content
        return result

    def _build_embed_comment(self) -> str:
        """Build a single Windows-compatible comment string from all editable fields.
        Each non-empty field is written as a [Header] section."""
        sections = []
        desc = self.meta_desc.toPlainText().strip()
        if desc:
            sections.append(f"[Description]\n{desc}")
        ai_prompt = self.meta_ai_prompt_edit.toPlainText().strip()
        if ai_prompt:
            sections.append(f"[AI Prompt]\n{ai_prompt}")
        ai_negative_prompt = self.meta_ai_negative_prompt_edit.toPlainText().strip()
        if ai_negative_prompt:
            sections.append(f"[AI Negative Prompt]\n{ai_negative_prompt}")
        ai_params = self.meta_ai_params_edit.toPlainText().strip()
        if ai_params:
            sections.append(f"[AI Parameters]\n{ai_params}")
        notes = self.meta_notes.toPlainText().strip()
        if notes:
            sections.append(f"[Notes]\n{notes}")
        return "\n\n".join(sections)

    @staticmethod
    def _build_embed_comment_from_values(
        *,
        description: str = "",
        comments: str = "",
        ai_prompt: str = "",
        ai_negative_prompt: str = "",
        ai_params: str = "",
        ai_workflows: str = "",
        notes: str = "",
    ) -> str:
        sections: list[str] = []

        def add_section(title: str, value: str) -> None:
            text = str(value or "").strip()
            if text:
                sections.append(f"[{title}]\n{text}")

        add_section("Description", description)
        add_section("Comments", comments)
        add_section("AI Prompt", ai_prompt)
        add_section("AI Negative Prompt", ai_negative_prompt)
        add_section("AI Parameters", ai_params)
        add_section("AI Workflows", ai_workflows)
        add_section("Notes", notes)
        return "\n\n".join(sections)

    def _embed_metadata_payload_to_file(
        self,
        path: str,
        *,
        tags: list[str] | None = None,
        embedded_tags_text: str = "",
        description: str = "",
        comments: str = "",
        ai_prompt: str = "",
        ai_negative_prompt: str = "",
        ai_params: str = "",
        ai_workflows: str = "",
        notes: str = "",
        exif_date_taken_raw: str = "",
        metadata_date_raw: str = "",
    ) -> bool:
        p = Path(str(path or ""))
        if not p.exists():
            return False

        ext = p.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
            return False

        merged_tags = self._merge_tag_lists(
            self._normalize_tag_list(embedded_tags_text),
            list(tags or []),
        )
        tags_raw = "; ".join(merged_tags)
        comm_raw = self._build_embed_comment_from_values(
            description=description,
            comments=comments,
            ai_prompt=ai_prompt,
            ai_negative_prompt=ai_negative_prompt,
            ai_params=ai_params,
            ai_workflows=ai_workflows,
            notes=notes,
        ).strip()

        try:
            from PIL import Image, PngImagePlugin
            import tempfile, os

            exif_date_taken_exif = self._format_exif_datetime(exif_date_taken_raw)
            metadata_date_exif = self._format_exif_datetime(metadata_date_raw)
            exif_date_taken_xmp = self._format_xmp_datetime(exif_date_taken_raw)
            metadata_date_xmp = self._format_xmp_datetime(metadata_date_raw)

            with Image.open(str(p)) as img:
                if ext == ".png":
                    pnginfo = PngImagePlugin.PngInfo()
                    skip_keys = {
                        "parameters", "comment", "comments", "keywords", "subject", "description",
                        "title", "author", "copyright", "software", "creation time", "source",
                        "xmp", "xml:com.adobe.xmp", "exif", "itxt", "ztxt", "text", "tags", "xpcomment", "xpkeywords", "xpsubject"
                    }
                    for k, v in img.info.items():
                        if isinstance(k, str) and k.strip().lower() not in skip_keys:
                            try:
                                pnginfo.add_text(k, str(v))
                            except Exception:
                                pass

                    win_tags = tags_raw.replace(",", ";")
                    if comm_raw:
                        pnginfo.add_text("Description", comm_raw)
                        pnginfo.add_text("Comment", comm_raw)
                        pnginfo.add_text("Comments", comm_raw)
                        pnginfo.add_text("Subject", comm_raw)
                        pnginfo.add_text("Title", comm_raw)
                    if tags_raw:
                        pnginfo.add_text("Keywords", win_tags)
                        pnginfo.add_text("Tags", win_tags)
                        if not comm_raw:
                            pnginfo.add_text("Subject", win_tags)
                    png_date_taken_text = exif_date_taken_xmp or metadata_date_xmp
                    if png_date_taken_text:
                        pnginfo.add_text("Creation Time", png_date_taken_text)

                    parsed_tags = [t.strip() for t in win_tags.split(";") if t.strip()]
                    xmp_packet = self._build_png_xmp_packet(
                        comm_raw,
                        parsed_tags,
                        exif_date_taken=exif_date_taken_xmp,
                        metadata_date=metadata_date_xmp,
                    )
                    if xmp_packet:
                        try:
                            pnginfo.add_itxt("XML:com.adobe.xmp", xmp_packet)
                        except Exception:
                            try:
                                pnginfo.add_text("XML:com.adobe.xmp", xmp_packet)
                            except Exception:
                                pass

                    exif = img.getexif()
                    for tag_id in (0x9C9C, 270, 306, 36867, 36868, 37510, 0x9C9E, 0x9C9F):
                        try:
                            del exif[tag_id]
                        except Exception:
                            pass
                    if comm_raw:
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                        exif[270] = comm_raw
                        exif[37510] = b"UNICODE\x00" + comm_raw.encode("utf-16le") + b"\x00\x00"
                    if tags_raw:
                        exif[0x9C9E] = (win_tags + "\x00").encode("utf-16le")
                        exif[0x9C9F] = (win_tags + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.load()
                        img.save(tmp_path, "PNG", pnginfo=pnginfo, exif=exif.tobytes())
                        os.replace(tmp_path, str(p))
                    except Exception:
                        if tmp_path.exists():
                            tmp_path.unlink()
                        raise

                elif ext in (".jpg", ".jpeg"):
                    exif = img.getexif()
                    if comm_raw:
                        exif[270] = comm_raw
                        exif[37510] = comm_raw
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                    if tags_raw:
                        win_tags = tags_raw.replace(",", ";")
                        exif[0x9C9E] = (win_tags + "\x00").encode("utf-16le")
                        exif[0x9C9F] = (win_tags + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "JPEG", exif=exif, quality="keep" if hasattr(img, "quality") else 95)
                        os.replace(tmp_path, str(p))
                    except Exception:
                        if tmp_path.exists():
                            tmp_path.unlink()
                        raise

                elif ext == ".webp":
                    exif = img.getexif()
                    if comm_raw:
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                    if tags_raw:
                        exif[0x9C9E] = (tags_raw.replace(",", ";") + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webp", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "WEBP", exif=exif, lossless=True)
                        os.replace(tmp_path, str(p))
                    except Exception:
                        if tmp_path.exists():
                            tmp_path.unlink()
                        raise

            try:
                from app.mediamanager.db.media_repo import get_media_by_path
                from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
                media = get_media_by_path(self.bridge.conn, str(p))
                if media:
                    inspect_and_persist_if_supported(self.bridge.conn, media["id"], str(p), media.get("media_type"))
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _build_hidden_metadata_merge_comment(self) -> str:
        sections = []

        def add_section(title: str, value: str) -> None:
            text = str(value or "").strip()
            if text:
                sections.append(f"[{title}]\n{text}")

        add_section("Description", self.meta_desc.toPlainText())
        add_section("AI Prompt", self.meta_ai_prompt_edit.toPlainText())
        add_section("AI Negative Prompt", self.meta_ai_negative_prompt_edit.toPlainText())

        ai_params_lines = []
        for label, value in (
            ("Tool / Source", self.meta_ai_source_edit.toPlainText()),
            ("Families", self.meta_ai_families_edit.text()),
            ("Model", self.meta_ai_model_edit.text()),
            ("Checkpoint", self.meta_ai_checkpoint_edit.text()),
            ("Sampler", self.meta_ai_sampler_edit.text()),
            ("Scheduler", self.meta_ai_scheduler_edit.text()),
            ("CFG", self.meta_ai_cfg_edit.text()),
            ("Steps", self.meta_ai_steps_edit.text()),
            ("Seed", self.meta_ai_seed_edit.text()),
            ("Upscaler", self.meta_ai_upscaler_edit.text()),
            ("Denoise", self.meta_ai_denoise_edit.text()),
            ("LoRAs", self.meta_ai_loras_edit.toPlainText()),
            ("Legacy Params", self.meta_ai_params_edit.toPlainText()),
        ):
            text = str(value or "").strip()
            if text:
                ai_params_lines.append(f"{label}: {text}")
        add_section("AI Parameters", "\n".join(ai_params_lines))
        add_section("AI Detection Reasons", self.meta_ai_detection_reasons_edit.toPlainText())
        add_section("AI Workflows", self.meta_ai_workflows_edit.toPlainText())
        add_section("AI Provenance", self.meta_ai_provenance_edit.toPlainText())
        add_section("AI Character Cards", self.meta_ai_character_cards_edit.toPlainText())
        add_section("AI Metadata Paths", self.meta_ai_raw_paths_edit.toPlainText())
        add_section("Notes", self.meta_notes.toPlainText())
        return "\n\n".join(sections)

    @Slot()
    def _merge_hidden_metadata_into_visible_comments(self) -> None:
        if not self._current_path:
            return
        merged = self._build_hidden_metadata_merge_comment()
        if not merged:
            self.meta_status_lbl.setText("No hidden metadata available to merge.")
            return
        self.meta_embedded_comments_edit.setPlainText(merged)
        self._save_to_exif_cmd()

    def _embed_bulk_tags_to_files(self, paths: list[str], tags: list[str]) -> None:
        if not paths:
            return
        if not tags:
            self.meta_status_lbl.setText("Enter tags to embed.")
            return

        original_path = getattr(self, "_current_path", None)
        original_paths = list(getattr(self, "_current_paths", []))
        original_embedded_tags = self.meta_embedded_tags_edit.text()
        original_embedded_comments = self.meta_embedded_comments_edit.toPlainText()

        completed = 0
        skipped = 0
        try:
            for path in paths:
                p = Path(path)
                if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
                    skipped += 1
                    continue
                existing_comment = ""
                existing_tags: list[str] = []
                try:
                    from PIL import Image
                    with Image.open(str(p)) as img:
                        visible_meta = self._harvest_windows_visible_metadata(img) or {}
                        existing_comment = visible_meta.get("comment", "") or ""
                        existing_tags = [str(tag).strip() for tag in visible_meta.get("tags", []) if str(tag).strip()]
                except Exception:
                    existing_comment = ""
                    existing_tags = []
                merged_tags = self._merge_tag_lists(existing_tags, tags)
                self.meta_embedded_tags_edit.setText("; ".join(merged_tags))
                self.meta_embedded_comments_edit.setPlainText(existing_comment)
                self._current_path = path
                self._current_paths = [path]
                try:
                    self._save_to_exif_cmd()
                    completed += 1
                except Exception:
                    skipped += 1
        finally:
            self._current_path = original_path
            self._current_paths = original_paths
            self.meta_embedded_tags_edit.setText(original_embedded_tags)
            self.meta_embedded_comments_edit.setPlainText(original_embedded_comments)

        if completed:
            message = f"âœ“ Tags embedded in {completed} file{'s' if completed != 1 else ''}"
            if skipped:
                message += f" ({skipped} skipped)"
            self.meta_status_lbl.setText(message)
            QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
            if hasattr(self, "bulk_status_lbl"):
                self.bulk_status_lbl.setText(message.replace("Ã¢Å“â€œ", "âœ“"))
                QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))
        elif skipped:
            self.meta_status_lbl.setText("No selected files support embedded tags.")
            if hasattr(self, "bulk_status_lbl"):
                self.bulk_status_lbl.setText("No selected files support embedded tags.")

    @Slot()
    def _save_to_exif_cmd(self) -> None:
        """Embed tags and comments from the 'Embedded' UI fields INTO the file."""
        paths = self._current_file_paths()
        if len(paths) > 1:
            self._embed_bulk_tags_to_files(paths, self._normalize_tag_list(self._tag_editor_text()))
            return
        if not self._current_path: return
        p = Path(self._current_path)
        if not p.exists(): return

        ext = p.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
            self.meta_status_lbl.setText("Embed not supported for this file type.")
            return

        try:
            from PIL import Image, PngImagePlugin
            import tempfile, os

            # Isolation Rule: Only use the 'Embedded' UI boxes for actual embedding
            tags_raw = self.meta_embedded_tags_edit.text().strip()
            comm_raw = self.meta_embedded_comments_edit.toPlainText().strip()
            exif_date_taken_raw = self.meta_exif_date_taken_edit.text().strip()
            metadata_date_raw = self.meta_metadata_date_edit.text().strip()
            exif_date_taken_exif = self._format_exif_datetime(exif_date_taken_raw)
            metadata_date_exif = self._format_exif_datetime(metadata_date_raw)
            exif_date_taken_xmp = self._format_xmp_datetime(exif_date_taken_raw)
            metadata_date_xmp = self._format_xmp_datetime(metadata_date_raw)
            
            with Image.open(str(p)) as img:
                if ext == ".png":
                    pnginfo = PngImagePlugin.PngInfo()
                    # Wipe EVERYTHING to prevent stale data sync issues
                    skip_keys = {
                        "parameters", "comment", "comments", "keywords", "subject", "description",
                        "title", "author", "copyright", "software", "creation time", "source",
                        "xmp", "xml:com.adobe.xmp", "exif", "itxt", "ztxt", "text", "tags", "xpcomment", "xpkeywords", "xpsubject"
                    }
                    for k, v in img.info.items():
                        if isinstance(k, str) and k.strip().lower() not in skip_keys:
                            try: pnginfo.add_text(k, str(v))
                            except: pass
                    
                    # Target Standard chunks + Windows specific chunks
                    # Use standard add_text (tEXt chunks) since Windows Explorer prioritizes them over iTXt
                    win_tags = tags_raw.replace(",", ";")
                    if comm_raw:
                        pnginfo.add_text("Description", comm_raw)
                        pnginfo.add_text("Comment", comm_raw)
                        pnginfo.add_text("Comments", comm_raw)
                        pnginfo.add_text("Subject", comm_raw)
                        pnginfo.add_text("Title", comm_raw)
                    
                    if tags_raw:
                        pnginfo.add_text("Keywords", win_tags)
                        pnginfo.add_text("Tags", win_tags)
                        if not comm_raw:
                            pnginfo.add_text("Subject", win_tags)
                    png_date_taken_text = exif_date_taken_xmp or metadata_date_xmp
                    if png_date_taken_text:
                        pnginfo.add_text("Creation Time", png_date_taken_text)

                    # PNG + Windows Explorer: tags are often read from XMP dc:subject
                    # rather than PNG tEXt or EXIF XP* fields. Emit XMP in addition to
                    # legacy keys for maximum compatibility.
                    parsed_tags = [t.strip() for t in win_tags.split(";") if t.strip()]
                    xmp_packet = self._build_png_xmp_packet(
                        comm_raw,
                        parsed_tags,
                        exif_date_taken=exif_date_taken_xmp,
                        metadata_date=metadata_date_xmp,
                    )
                    if xmp_packet:
                        try:
                            pnginfo.add_itxt("XML:com.adobe.xmp", xmp_packet)
                        except Exception:
                            try:
                                pnginfo.add_text("XML:com.adobe.xmp", xmp_packet)
                            except Exception:
                                pass

                    # EXIF for Windows 10/11 Explorer compatibility
                    exif = img.getexif()
                    for tag_id in (0x9C9C, 270, 306, 36867, 36868, 37510, 0x9C9E, 0x9C9F):
                        try:
                            del exif[tag_id]
                        except Exception:
                            pass
                    if comm_raw:
                        # 0x9C9C = XPComment (UTF-16LE null terminated)
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                        # 270 = ImageDescription
                        exif[270] = comm_raw
                        # 37510 = UserComment
                        exif[37510] = b"UNICODE\x00" + comm_raw.encode("utf-16le") + b"\x00\x00"

                    if tags_raw:
                        # 0x9C9E = XPKeywords
                        exif[0x9C9E] = (win_tags + "\x00").encode("utf-16le")
                        # 0x9C9F = XPSubject
                        exif[0x9C9F] = (win_tags + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        # Force img.load() to ensure EXIF can be saved back
                        img.load()
                        # Save with EVERYTHING
                        img.save(tmp_path, "PNG", pnginfo=pnginfo, exif=exif.tobytes())
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e
                
                elif ext in (".jpg", ".jpeg"):
                    exif = img.getexif()
                    if comm_raw:
                        # Tag 270 = ImageDescription
                        exif[270] = comm_raw
                        # Tag 37510 = UserComment
                        exif[37510] = comm_raw
                        # Tag 0x9C9C = XPComment
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                    if tags_raw:
                        win_tags = tags_raw.replace(",", ";") 
                        # Tag 0x9C9E = XPKeywords
                        exif[0x9C9E] = (win_tags + "\x00").encode("utf-16le")
                        # Tag 0x9C9F = XPSubject
                        exif[0x9C9F] = (win_tags + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "JPEG", exif=exif, quality="keep" if hasattr(img, "quality") else 95)
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e
                
                elif ext == ".webp":
                    exif = img.getexif()
                    if comm_raw:
                        exif[0x9C9C] = (comm_raw + "\x00").encode("utf-16le")
                    if tags_raw:
                        exif[0x9C9E] = (tags_raw.replace(",", ";") + "\x00").encode("utf-16le")
                    if metadata_date_exif:
                        exif[306] = metadata_date_exif
                        exif[36868] = metadata_date_exif
                    if exif_date_taken_exif:
                        exif[36867] = exif_date_taken_exif
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webp", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "WEBP", exif=exif, lossless=True)
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e

            try:
                from app.mediamanager.db.media_repo import get_media_by_path
                from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
                media = get_media_by_path(self.bridge.conn, str(p))
                if media:
                    inspect_and_persist_if_supported(self.bridge.conn, media["id"], str(p), media.get("media_type"))
                data = self.bridge.get_media_metadata(str(p))
                self.meta_exif_date_taken_edit.setText(self._format_editable_datetime(data.get("exif_date_taken")))
                self.meta_metadata_date_edit.setText(self._format_editable_datetime(data.get("metadata_date")))
                original_file_text = self._format_sidebar_datetime(data.get("original_file_date"))
                if original_file_text:
                    self.meta_original_file_date_lbl.setText(original_file_text)
                file_created_text = self._format_sidebar_datetime(data.get("file_created_time"))
                if file_created_text:
                    self.meta_file_created_date_lbl.setText(file_created_text)
                file_modified_text = self._format_sidebar_datetime(data.get("modified_time"))
                if file_modified_text:
                    self.meta_file_modified_date_lbl.setText(file_modified_text)
            except Exception:
                pass
            self.meta_status_lbl.setText("âœ“ Metadata embedded in file")
            QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        except Exception as e:
            self.meta_status_lbl.setText(f"Embed Error: {e}")
    def _clear_bulk_tags(self) -> None:
        """Remove all tags from currently selected files with warning."""
        paths = self._current_file_paths()
        if not paths:
            return

        from PySide6.QtWidgets import QMessageBox
        msg = f"Are you sure you want to remove ALL tags from {len(paths)} selected files?"
        ret = QMessageBox.warning(
            self, "Clear All Tags", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        for p in paths:
            try:
                self.bridge.clear_media_tags(p)
            except Exception:
                pass

        self.meta_status_lbl.setText(f"âœ“ Tags cleared for {len(paths)} items")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        
        if hasattr(self, "bulk_status_lbl"):
            self.bulk_status_lbl.setText(f"âœ“ Tags cleared for {len(paths)} items")
            QTimer.singleShot(3000, lambda: self.bulk_status_lbl.setText(""))

        # Clear the UI text box
        self._set_tag_editor_text("")
        self._refresh_bulk_tag_editor_summary()
        self._refresh_tag_list_scope_counts()

    def _save_native_tags(self) -> None:
        # We delegate to the main metadata saver to avoid logic duplication
        # (Editing tags triggers a soft save).
        self._save_native_metadata()

    def _schedule_show_metadata_for_path(self, paths: list[str]) -> None:
        self._pending_metadata_paths = [str(path or "") for path in list(paths or [])]
        self._metadata_request_revision += 1
        self._metadata_request_timer.start(0)

    def _apply_pending_metadata_request(self) -> None:
        revision = int(getattr(self, "_metadata_request_revision", 0))
        paths = list(getattr(self, "_pending_metadata_paths", []) or [])
        self._show_metadata_for_path(paths, request_revision=revision)

    def _schedule_tag_list_refresh(self, mode: str = "rows", *, request_revision: int | None = None) -> None:
        if not hasattr(self, "tag_list_panel") or not self.tag_list_panel.isVisible():
            return
        next_mode = "full" if str(mode or "rows") == "full" else "rows"
        current_mode = str(getattr(self, "_pending_tag_list_refresh_mode", "rows") or "rows")
        if current_mode != "full":
            self._pending_tag_list_refresh_mode = next_mode
        self._tag_list_refresh_revision = int(
            request_revision
            if request_revision is not None
            else getattr(self, "_metadata_request_revision", 0)
        )
        self._tag_list_refresh_timer.start(0)

    def _apply_pending_tag_list_refresh(self) -> None:
        request_revision = int(getattr(self, "_tag_list_refresh_revision", 0))
        if request_revision < int(getattr(self, "_metadata_request_revision", 0)):
            return
        mode = str(getattr(self, "_pending_tag_list_refresh_mode", "rows") or "rows")
        self._pending_tag_list_refresh_mode = "rows"
        if mode == "full":
            self._refresh_tag_list_panel()
        else:
            self._refresh_tag_list_rows_state()

    def _show_metadata_for_path(self, paths: list[str], request_revision: int | None = None) -> None:
        active_revision = int(request_revision if request_revision is not None else getattr(self, "_metadata_request_revision", 0))
        if active_revision < int(getattr(self, "_metadata_request_revision", 0)):
            return
        # Ignore empty lists (e.g. from background clicks that deselect cards).
        raw_paths = [str(path or "").strip() for path in list(paths or []) if str(path or "").strip()]
        if not raw_paths:
            self._clear_metadata_panel()
            self._metadata_applied_revision = active_revision
            self._schedule_tag_list_refresh("rows", request_revision=active_revision)
            return
        file_paths = self._current_file_paths(raw_paths)
        self._current_paths = raw_paths
        if not file_paths:
            self._current_path = None
            self._clear_metadata_panel()
            self._metadata_applied_revision = active_revision
            self._schedule_tag_list_refresh("rows", request_revision=active_revision)
            return

        is_bulk = len(file_paths) > 1
        primary_path = file_paths[0] if file_paths else None
        if is_bulk:
            self._current_path = None
            self._current_metadata_kind = self._metadata_kind_for_path(primary_path)
            self._refresh_preview_for_path(None)
            if self._current_bulk_editor_mode() == "captions":
                self._configure_bulk_caption_editor(len(file_paths))
            else:
                self._configure_bulk_tag_editor(len(file_paths))
            self.bulk_meta_tags.blockSignals(True)
            self.bulk_meta_tags.setText("")
            self.bulk_meta_tags.blockSignals(False)
            self.bulk_status_lbl.setText("")
            if hasattr(self, "bulk_caption_status_lbl"):
                self.bulk_caption_status_lbl.setText("")
            self._sync_tag_list_panel_visibility(refresh_contents=False)
            self._metadata_applied_revision = active_revision
            self._schedule_tag_list_refresh("rows", request_revision=active_revision)
            return

        self._set_active_right_workspace("details")
        is_video = bool(primary_path and Path(primary_path).suffix.lower() in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"})
        self._set_metadata_empty_state(False)
        self._current_path = primary_path if not is_bulk else None
        self._refresh_preview_for_path(primary_path if not is_bulk else None)
        metadata_kind = self._metadata_kind_for_path(primary_path)
        self._current_metadata_kind = metadata_kind
        self._setup_metadata_layout(metadata_kind)

        self.preview_header_row.setVisible(not is_bulk)
        self.preview_image_lbl.setVisible(not is_bulk and self.bridge._preview_above_details_enabled())
        self.preview_sep.setVisible(not is_bulk and self.bridge._preview_above_details_enabled())
        self.details_header_lbl.setVisible(not is_bulk)
        self.preview_image_lbl.setCursor(Qt.CursorShape.ArrowCursor)
        if hasattr(self, "btn_play_preview"):
            self.btn_play_preview.setVisible(False)
        if hasattr(self, "btn_close_preview"):
            self.btn_close_preview.setVisible(not is_bulk and self.bridge._preview_above_details_enabled())
        if hasattr(self, "btn_show_preview_inline"):
            self.btn_show_preview_inline.setVisible(not is_bulk and not self.bridge._preview_above_details_enabled())
        if hasattr(self, "right_layout"):
            self.right_layout.activate()
            self._sync_sidebar_panel_widths()
        self._sync_sidebar_video_preview_controls()
        self.btn_save_meta.setVisible(True)
        self.btn_clear_bulk_tags.setVisible(False)
        self.btn_import_exif.setVisible(not is_bulk)
        self.btn_merge_hidden_meta.setVisible(not is_bulk)
        self.btn_save_to_exif.setVisible(not is_bulk)
        self.meta_status_lbl.setVisible(True)
        embed_supported = bool(primary_path and Path(primary_path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".avif"})
        self.btn_save_to_exif.setEnabled(not is_bulk and embed_supported)
        if not is_bulk and not embed_supported:
            self.btn_save_to_exif.setToolTip("Embedding file metadata is not supported for this file type.")
        else:
            self.btn_save_to_exif.setToolTip("Write tags and comments from these fields into the file's embedded metadata")

        # Toggle UI for bulk mode
        self.lbl_fn_cap.setVisible(not is_bulk)
        self.meta_filename_edit.setVisible(not is_bulk)
        self.meta_path_lbl.setVisible(not is_bulk)

        visible_group_keys = [group for group in self._metadata_group_order(metadata_kind) if self._is_metadata_group_enabled(metadata_kind, group, True)]
        active_fields = {
            field
            for group in visible_group_keys
            for field in self._metadata_group_fields(metadata_kind).get(group, [])
        }
        show_res = "res" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "res", True)
        show_size = "size" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "size", True)
        show_exif_date_taken = "exifdatetaken" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "exifdatetaken", False)
        show_metadata_date = "metadatadate" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "metadatadate", False)
        show_original_file_date = "originalfiledate" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "originalfiledate", False)
        show_file_created_date = "filecreateddate" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "filecreateddate", False)
        show_file_modified_date = "filemodifieddate" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "filemodifieddate", False)
        show_text_detected = "textdetected" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "textdetected", True)
        show_duration = "duration" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "duration", True)
        show_fps = "fps" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "fps", True)
        show_codec = "codec" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "codec", True)
        show_audio = "audio" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "audio", True)
        show_description = "description" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "description", True)
        show_notes = "notes" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "notes", True)
        show_camera = "camera" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "camera", False)
        show_location = "location" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "location", False)
        show_iso = "iso" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "iso", False)
        show_shutter = "shutter" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "shutter", False)
        show_aperture = "aperture" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aperture", False)
        show_software = "software" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "software", False)
        show_lens = "lens" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "lens", False)
        show_dpi = "dpi" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "dpi", False)
        show_embedded_tags = "embeddedtags" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "embeddedtags", True)
        show_embedded_comments = "embeddedcomments" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "embeddedcomments", True)
        show_embedded_metadata = "embeddedmetadata" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "embeddedmetadata", True)
        show_ai_status = "aistatus" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aistatus", True)
        show_ai_generated = "aigenerated" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aigenerated", True)
        show_ai_source = "aisource" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aisource", True)
        show_ai_families = "aifamilies" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aifamilies", True)
        show_ai_detection_reasons = "aidetectionreasons" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aidetectionreasons", False)
        show_ai_loras = "ailoras" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "ailoras", True)
        show_ai_model = "aimodel" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aimodel", True)
        show_ai_checkpoint = "aicheckpoint" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aicheckpoint", False)
        show_ai_sampler = "aisampler" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aisampler", True)
        show_ai_scheduler = "aischeduler" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aischeduler", True)
        show_ai_cfg = "aicfg" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aicfg", True)
        show_ai_steps = "aisteps" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aisteps", True)
        show_ai_seed = "aiseed" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiseed", True)
        show_ai_upscaler = "aiupscaler" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiupscaler", False)
        show_ai_denoise = "aidenoise" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aidenoise", False)
        show_ai_prompt = "aiprompt" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiprompt", True)
        show_ai_neg_prompt = "ainegprompt" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "ainegprompt", True)
        show_ai_params = "aiparams" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiparams", True)
        show_ai_workflows = "aiworkflows" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiworkflows", False)
        show_ai_provenance = "aiprovenance" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aiprovenance", False)
        show_ai_character_cards = "aicharcards" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "aicharcards", False)
        show_ai_raw_paths = "airawpaths" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "airawpaths", False)
        visible_groups = visible_group_keys
        self.lbl_group_general.setVisible(not is_bulk and "general" in visible_groups)
        self.lbl_group_camera.setVisible(not is_bulk and "camera" in visible_groups)
        self.lbl_group_ai.setVisible(not is_bulk and "ai" in visible_groups)

        self.meta_res_lbl.setVisible(not is_bulk and show_res)
        self.meta_size_lbl.setVisible(not is_bulk and show_size)
        self.lbl_exif_date_taken_cap.setVisible(not is_bulk and show_exif_date_taken)
        self.meta_exif_date_taken_edit.setVisible(not is_bulk and show_exif_date_taken)
        self.lbl_metadata_date_cap.setVisible(not is_bulk and show_metadata_date)
        self.meta_metadata_date_edit.setVisible(not is_bulk and show_metadata_date)
        self.lbl_original_file_date_cap.setVisible(not is_bulk and show_original_file_date)
        self.meta_original_file_date_lbl.setVisible(not is_bulk and show_original_file_date)
        self.lbl_file_created_date_cap.setVisible(not is_bulk and show_file_created_date)
        self.meta_file_created_date_lbl.setVisible(not is_bulk and show_file_created_date)
        self.lbl_file_modified_date_cap.setVisible(not is_bulk and show_file_modified_date)
        self.meta_file_modified_date_lbl.setVisible(not is_bulk and show_file_modified_date)
        self.lbl_text_detected_cap.setVisible(not is_bulk and show_text_detected)
        self.meta_text_detected_row.setVisible(not is_bulk and show_text_detected)
        self.lbl_text_detected_note.setVisible(not is_bulk and show_text_detected)
        self.lbl_detected_text_cap.setVisible(not is_bulk and show_text_detected)
        self.meta_detected_text_edit.setVisible(not is_bulk and show_text_detected)
        self.btn_use_ocr.setVisible(not is_bulk and show_text_detected)
        self.meta_duration_lbl.setVisible(not is_bulk and show_duration)
        self.meta_fps_lbl.setVisible(not is_bulk and show_fps)
        self.meta_codec_lbl.setVisible(not is_bulk and show_codec)
        self.meta_audio_lbl.setVisible(not is_bulk and show_audio)
        self.meta_camera_lbl.setVisible(not is_bulk and show_camera)
        self.meta_location_lbl.setVisible(not is_bulk and show_location)
        self.meta_iso_lbl.setVisible(not is_bulk and show_iso)
        self.meta_shutter_lbl.setVisible(not is_bulk and show_shutter)
        self.meta_aperture_lbl.setVisible(not is_bulk and show_aperture)
        self.meta_software_lbl.setVisible(not is_bulk and show_software)
        self.meta_lens_lbl.setVisible(not is_bulk and show_lens)
        self.meta_dpi_lbl.setVisible(not is_bulk and show_dpi)
        self.meta_embedded_tags_edit.setVisible(not is_bulk and show_embedded_tags)
        self.lbl_embedded_tags_cap.setVisible(not is_bulk and show_embedded_tags)
        self.meta_embedded_comments_edit.setVisible(not is_bulk and show_embedded_comments)
        self.lbl_embedded_comments_cap.setVisible(not is_bulk and show_embedded_comments)
        self.meta_embedded_metadata_edit.setVisible(not is_bulk and show_embedded_metadata)
        self.lbl_embedded_metadata_cap.setVisible(not is_bulk and show_embedded_metadata)
        self.meta_ai_status_edit.setVisible(not is_bulk and show_ai_status)
        self.lbl_ai_status_cap.setVisible(not is_bulk and show_ai_status)
        self.meta_ai_generated_row.setVisible(not is_bulk and show_ai_generated)
        self.lbl_ai_generated_cap.setVisible(not is_bulk and show_ai_generated)
        self.lbl_ai_generated_note.setVisible(not is_bulk and show_ai_generated)
        self.meta_ai_source_edit.setVisible(not is_bulk and show_ai_source)
        self.lbl_ai_source_cap.setVisible(not is_bulk and show_ai_source)
        self.meta_ai_families_edit.setVisible(not is_bulk and show_ai_families)
        self.lbl_ai_families_cap.setVisible(not is_bulk and show_ai_families)
        self.meta_ai_detection_reasons_edit.setVisible(not is_bulk and show_ai_detection_reasons)
        self.lbl_ai_detection_reasons_cap.setVisible(not is_bulk and show_ai_detection_reasons)
        self.meta_ai_loras_edit.setVisible(not is_bulk and show_ai_loras)
        self.lbl_ai_loras_cap.setVisible(not is_bulk and show_ai_loras)
        self.meta_ai_model_edit.setVisible(not is_bulk and show_ai_model)
        self.lbl_ai_model_cap.setVisible(not is_bulk and show_ai_model)
        self.meta_ai_checkpoint_edit.setVisible(not is_bulk and show_ai_checkpoint)
        self.lbl_ai_checkpoint_cap.setVisible(not is_bulk and show_ai_checkpoint)
        self.meta_ai_sampler_edit.setVisible(not is_bulk and show_ai_sampler)
        self.lbl_ai_sampler_cap.setVisible(not is_bulk and show_ai_sampler)
        self.meta_ai_scheduler_edit.setVisible(not is_bulk and show_ai_scheduler)
        self.lbl_ai_scheduler_cap.setVisible(not is_bulk and show_ai_scheduler)
        self.meta_ai_cfg_edit.setVisible(not is_bulk and show_ai_cfg)
        self.lbl_ai_cfg_cap.setVisible(not is_bulk and show_ai_cfg)
        self.meta_ai_steps_edit.setVisible(not is_bulk and show_ai_steps)
        self.lbl_ai_steps_cap.setVisible(not is_bulk and show_ai_steps)
        self.meta_ai_seed_edit.setVisible(not is_bulk and show_ai_seed)
        self.lbl_ai_seed_cap.setVisible(not is_bulk and show_ai_seed)
        self.meta_ai_upscaler_edit.setVisible(not is_bulk and show_ai_upscaler)
        self.lbl_ai_upscaler_cap.setVisible(not is_bulk and show_ai_upscaler)
        self.meta_ai_denoise_edit.setVisible(not is_bulk and show_ai_denoise)
        self.lbl_ai_denoise_cap.setVisible(not is_bulk and show_ai_denoise)
        
        self.meta_ai_prompt_edit.setVisible(not is_bulk and show_ai_prompt)
        self.lbl_ai_prompt_cap.setVisible(not is_bulk and show_ai_prompt)
        self.meta_ai_negative_prompt_edit.setVisible(not is_bulk and show_ai_neg_prompt)
        self.lbl_ai_negative_prompt_cap.setVisible(not is_bulk and show_ai_neg_prompt)
        self.meta_ai_params_edit.setVisible(not is_bulk and show_ai_params)
        self.lbl_ai_params_cap.setVisible(not is_bulk and show_ai_params)
        self.meta_ai_workflows_edit.setVisible(not is_bulk and show_ai_workflows)
        self.lbl_ai_workflows_cap.setVisible(not is_bulk and show_ai_workflows)
        self.meta_ai_provenance_edit.setVisible(not is_bulk and show_ai_provenance)
        self.lbl_ai_provenance_cap.setVisible(not is_bulk and show_ai_provenance)
        self.meta_ai_character_cards_edit.setVisible(not is_bulk and show_ai_character_cards)
        self.lbl_ai_character_cards_cap.setVisible(not is_bulk and show_ai_character_cards)
        self.meta_ai_raw_paths_edit.setVisible(not is_bulk and show_ai_raw_paths)
        self.lbl_ai_raw_paths_cap.setVisible(not is_bulk and show_ai_raw_paths)
        self.meta_sep1.setVisible(not is_bulk and len(visible_groups) > 1)
        self.meta_sep2.setVisible(not is_bulk and len(visible_groups) > 2)
        self.meta_sep3.setVisible(False)

        # Set default text prefixes so they show even if blank
        self.meta_res_lbl.setText("Resolution: ")
        self.meta_size_lbl.setText("File Size: ")
        self.meta_exif_date_taken_edit.setText("")
        self.meta_metadata_date_edit.setText("")
        self.meta_original_file_date_lbl.setText("")
        self.meta_file_created_date_lbl.setText("")
        self.meta_file_modified_date_lbl.setText("")
        self._set_metadata_switch(self.meta_text_detected_toggle, False)
        self.meta_detected_text_edit.setPlainText("")
        self.meta_duration_lbl.setText("Duration: ")
        self.meta_fps_lbl.setText("FPS: ")
        self.meta_codec_lbl.setText("Codec: ")
        self.meta_audio_lbl.setText("Audio: ")
        self.meta_camera_lbl.setText("Camera: ")
        self.meta_location_lbl.setText("Location: ")
        self.meta_iso_lbl.setText("ISO: ")
        self.meta_shutter_lbl.setText("Shutter: ")
        self.meta_aperture_lbl.setText("Aperture: ")
        self.meta_software_lbl.setText("Software: ")
        self.meta_lens_lbl.setText("Lens: ")
        self.meta_dpi_lbl.setText("DPI: ")
        self.meta_embedded_tags_edit.setText("")
        self.meta_embedded_metadata_edit.setPlainText("")
        # Clear the text edits
        self.meta_embedded_comments_edit.setPlainText("")
        self._current_ai_meta = {}
        self._current_user_confirmed_text_detected = None
        self._current_auto_text_detected = None
        self._ai_generated_override_dirty = False
        self._text_detected_override_dirty = False
        self._update_override_note_labels(auto_text_detected=None, auto_ai_detected=None)
        self.meta_ai_status_edit.setText("")
        self._set_metadata_switch(self.meta_ai_generated_toggle, False)
        self.meta_ai_source_edit.setPlainText("")
        self.meta_ai_families_edit.setText("")
        self.meta_ai_detection_reasons_edit.setPlainText("")
        self.meta_ai_loras_edit.setPlainText("")
        self.meta_ai_model_edit.setText("")
        self.meta_ai_checkpoint_edit.setText("")
        self.meta_ai_sampler_edit.setText("")
        self.meta_ai_scheduler_edit.setText("")
        self.meta_ai_cfg_edit.setText("")
        self.meta_ai_steps_edit.setText("")
        self.meta_ai_seed_edit.setText("")
        self.meta_ai_upscaler_edit.setText("")
        self.meta_ai_denoise_edit.setText("")
        self.meta_ai_prompt_edit.setPlainText("")
        self.meta_ai_negative_prompt_edit.setPlainText("")
        self.meta_ai_params_edit.setPlainText("")
        self.meta_ai_workflows_edit.setPlainText("")
        self.meta_ai_provenance_edit.setPlainText("")
        self.meta_ai_character_cards_edit.setPlainText("")
        self.meta_ai_raw_paths_edit.setPlainText("")

        self.lbl_desc_cap.setVisible(not is_bulk and show_description)
        self.meta_desc.setVisible(not is_bulk and show_description)
        self.generate_description_btn_row.setVisible(not is_bulk and show_description)
        self.generate_description_progress_lbl.setVisible(
            not is_bulk and show_description and bool(self.generate_description_progress_lbl.text().strip())
        )
        self.generate_description_error_edit.setVisible(
            not is_bulk and show_description and bool(self.generate_description_error_edit.toPlainText().strip())
        )
        self.lbl_notes_cap.setVisible(not is_bulk and show_notes)
        self.meta_notes.setVisible(not is_bulk and show_notes)
        
        tags_visible = not is_bulk and ("tags" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "tags", True))
        self.lbl_tags_cap.setVisible(tags_visible)
        self.meta_tags.setVisible(tags_visible)
        self.generate_tags_btn_row.setVisible(tags_visible)
        self.generate_tags_progress_lbl.setVisible(tags_visible and bool(self.generate_tags_progress_lbl.text().strip()))
        self.generate_tags_error_edit.setVisible(tags_visible and bool(self.generate_tags_error_edit.toPlainText().strip()))
        self.tag_list_open_btn_row.setVisible(tags_visible)
        self.btn_clear_bulk_tags.setVisible(is_bulk)
        
        self.meta_filename_edit.blockSignals(True)
        self.meta_desc.blockSignals(True)
        self.meta_tags.blockSignals(True)
        self.meta_notes.blockSignals(True)
        self.meta_exif_date_taken_edit.blockSignals(True)
        self.meta_metadata_date_edit.blockSignals(True)
        self.meta_detected_text_edit.blockSignals(True)
        self.meta_text_detected_toggle.blockSignals(True)
        self.meta_ai_generated_toggle.blockSignals(True)

        if not is_bulk:
            path = paths[0]
            p = Path(path)
            self._current_video_width = 0
            self._current_video_height = 0
            self._current_video_duration_ms = 0
            self.meta_filename_edit.setText(p.name)
            self.meta_path_lbl.setText(f"Folder: {p.parent}")
            data = {}

            # 1. Database Metadata (Load FIRST)
            try:
                data = self.bridge.get_media_metadata(path)
                self._current_ai_meta = {
                    "is_ai_detected": bool(data.get("is_ai_detected")),
                    "is_ai_confidence": float(data.get("is_ai_confidence") or 0.0),
                    "user_confirmed_ai": data.get("user_confirmed_ai"),
                    "tool_name_found": data.get("tool_name_found", "") or "",
                    "tool_name_inferred": data.get("tool_name_inferred", "") or "",
                    "tool_name_confidence": float(data.get("tool_name_confidence") or 0.0),
                    "source_formats": list(data.get("source_formats") or []),
                }
                self._current_user_confirmed_text_detected = data.get("user_confirmed_text_detected")
                self._current_auto_text_detected = data.get("effective_text_detected")
                self._ai_generated_override_dirty = False
                self._text_detected_override_dirty = False
                self.meta_desc.setPlainText(data.get("description", ""))
                self.meta_notes.setPlainText(data.get("notes", ""))
                
                db_prompt = data.get('ai_prompt', '')
                if db_prompt: self.meta_ai_prompt_edit.setPlainText(db_prompt)

                db_neg_prompt = data.get('ai_negative_prompt', '')
                if db_neg_prompt: self.meta_ai_negative_prompt_edit.setPlainText(db_neg_prompt)
                
                db_params = data.get('ai_params', '')
                if db_params: self.meta_ai_params_edit.setPlainText(db_params)

                self.meta_ai_status_edit.setText(data.get("ai_status_summary", ""))
                self._update_override_note_labels(
                    auto_text_detected=data.get("effective_text_detected"),
                    auto_ai_detected=data.get("is_ai_detected"),
                )
                self._set_metadata_switch(self.meta_ai_generated_toggle, bool(data.get("effective_is_ai")))
                self._set_metadata_switch(self.meta_text_detected_toggle, bool(data.get("effective_text_detected")))
                self.meta_detected_text_edit.setPlainText(data.get("detected_text", "") or "")
                self.meta_ai_source_edit.setPlainText(data.get("ai_source_summary", ""))
                self.meta_ai_families_edit.setText(", ".join(data.get("metadata_families_detected", [])))
                self.meta_ai_detection_reasons_edit.setPlainText("\n".join(data.get("ai_detection_reasons", [])))
                self.meta_ai_loras_edit.setPlainText(data.get("ai_loras_summary", ""))
                self.meta_ai_model_edit.setText(data.get("model_name", "") or data.get("ai_model_summary", ""))
                self.meta_ai_checkpoint_edit.setText(data.get("checkpoint_name", "") or data.get("ai_checkpoint_summary", ""))
                self.meta_ai_sampler_edit.setText(data.get("sampler", "") or data.get("ai_sampler_summary", ""))
                self.meta_ai_scheduler_edit.setText(data.get("scheduler", "") or data.get("ai_scheduler_summary", ""))
                self.meta_ai_cfg_edit.setText("" if data.get("cfg_scale") in (None, "") else str(data.get("cfg_scale")))
                self.meta_ai_steps_edit.setText("" if data.get("steps") in (None, "") else str(data.get("steps")))
                self.meta_ai_seed_edit.setText("" if data.get("seed") in (None, "") else str(data.get("seed")))
                self.meta_ai_upscaler_edit.setText(data.get("upscaler", "") or data.get("ai_upscaler_summary", ""))
                self.meta_ai_denoise_edit.setText("" if data.get("denoise_strength") in (None, "") else str(data.get("denoise_strength")))
                self.meta_ai_workflows_edit.setPlainText(data.get("ai_workflows_summary", ""))
                self.meta_ai_provenance_edit.setPlainText(data.get("ai_provenance_summary", ""))
                self.meta_ai_character_cards_edit.setPlainText(data.get("ai_character_cards_summary", ""))
                self.meta_ai_raw_paths_edit.setPlainText(data.get("ai_raw_paths_summary", ""))
                self.meta_embedded_metadata_edit.setPlainText(data.get("embedded_metadata_summary", ""))
                
                self._set_tag_editor_text(", ".join(data.get("tags", [])), self.meta_tags)
                exif_date_taken = self._format_editable_datetime(data.get("exif_date_taken"))
                if exif_date_taken:
                    self.meta_exif_date_taken_edit.setText(exif_date_taken)
                metadata_date = self._format_editable_datetime(data.get("metadata_date"))
                if metadata_date:
                    self.meta_metadata_date_edit.setText(metadata_date)
                original_file_date = self._format_sidebar_datetime(data.get("original_file_date"))
                if original_file_date:
                    self.meta_original_file_date_lbl.setText(original_file_date)
                file_created_date = self._format_sidebar_datetime(data.get("file_created_time"))
                if file_created_date:
                    self.meta_file_created_date_lbl.setText(file_created_date)
                file_modified_date = self._format_sidebar_datetime(data.get("modified_time"))
                if file_modified_date:
                    self.meta_file_modified_date_lbl.setText(file_modified_date)
                
                width = int(data.get("width") or 0)
                height = int(data.get("height") or 0)
                self._current_video_width = width
                self._current_video_height = height
                if width > 0 and height > 0:
                    self.meta_res_lbl.setText(f"Resolution: {width} x {height} px")
                duration_ms = int(data.get("duration_ms") or 0)
                self._current_video_duration_ms = duration_ms
                if duration_ms > 0:
                    self.meta_duration_lbl.setText(f"Duration: {self._format_duration_seconds(duration_ms / 1000.0)}")
            except Exception:
                pass

            # 2. File size
            try:
                size_bytes = p.stat().st_size
                if size_bytes >= 1048576:
                    size_str = f"{size_bytes / 1048576:.1f} MB"
                elif size_bytes >= 1024:
                    size_str = f"{size_bytes / 1024:.0f} KB"
                else:
                    size_str = f"{size_bytes} B"
                self.meta_size_lbl.setText(f"File Size: {size_str}")
            except Exception:
                self.meta_size_lbl.setText("File Size:")

            if is_video:
                try:
                    stat = p.stat()
                    created_iso = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    modified_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    self.meta_original_file_date_lbl.setText(self._format_sidebar_datetime(min(created_iso, modified_iso)))
                    self.meta_file_created_date_lbl.setText(self._format_sidebar_datetime(created_iso))
                    self.meta_file_modified_date_lbl.setText(self._format_sidebar_datetime(modified_iso))
                except Exception:
                    pass
                self.meta_fps_lbl.setText("FPS: ")
                self.meta_codec_lbl.setText("Codec: ")
                self.meta_audio_lbl.setText("Audio: ")
                self._load_video_sidebar_metadata_async(path)
            elif p.is_dir():
                pass
            else:

                # 3. Real-time Harvest (Update/Enrich Labels)
                ext = p.suffix.lower()
                if ext in IMAGE_EXTS:
                    try:
                        sz = _image_size_with_svg_support(p)
                        if sz.isValid():
                            self.meta_res_lbl.setText(f"Resolution: {sz.width()} x {sz.height()} px")
                        else:
                            self.meta_res_lbl.setText("Resolution: ")
                    except Exception:
                        self.meta_res_lbl.setText("Resolution: ")
                # Additional info via Pillow
                if ext != ".svg":
                    try:
                        from PIL import Image
                        with Image.open(str(p)) as img:
                            if hasattr(img, "info"):
                                dpi = img.info.get("dpi")
                                if dpi:
                                    self.meta_dpi_lbl.setText(f"DPI: {dpi[0]} x {dpi[1]}")
                                if metadata_kind == "gif":
                                    animated = self._probe_animated_image_details(str(p))
                                    if animated.get("duration"):
                                        self.meta_duration_lbl.setText(f"Duration: {animated['duration']}")
                                    if animated.get("fps"):
                                        self.meta_fps_lbl.setText(f"FPS: {animated['fps']}")
                                    if animated.get("codec"):
                                        self.meta_codec_lbl.setText(f"Codec: {animated['codec']}")
                                    if animated.get("audio"):
                                        self.meta_audio_lbl.setText(f"Audio: {animated['audio']}")

                            try:
                                img.load()
                            except Exception:
                                pass
                            visible = self._harvest_windows_visible_metadata(img)
                            self.meta_embedded_tags_edit.setText("; ".join(visible.get("tags", [])))
                            self.meta_embedded_comments_edit.setPlainText(visible.get("comment", "") or "")
                            self.meta_embedded_metadata_edit.setPlainText(data.get("embedded_metadata_summary", ""))

                            exif = img.getexif()
                            if exif:
                                from PIL import ExifTags
                                model = exif.get(ExifTags.Base.Model)
                                if model:
                                    self.meta_camera_lbl.setText(f"Camera: {model}")
                                soft = exif.get(ExifTags.Base.Software)
                                if soft:
                                    self.meta_software_lbl.setText(f"Software: {soft}")

                                try:
                                    sub = exif.get_ifd(ExifTags.IFD.Exif)
                                    if sub:
                                        iso = sub.get(ExifTags.Base.ISOSpeedRatings)
                                        if iso:
                                            self.meta_iso_lbl.setText(f"ISO: {iso}")

                                        shutter = sub.get(ExifTags.Base.ExposureTime)
                                        if shutter:
                                            if shutter < 1:
                                                self.meta_shutter_lbl.setText(f"Shutter: 1/{int(1 / shutter)}s")
                                            else:
                                                self.meta_shutter_lbl.setText(f"Shutter: {shutter}s")

                                        aperture = sub.get(ExifTags.Base.FNumber)
                                        if aperture:
                                            self.meta_aperture_lbl.setText(f"Aperture: f/{aperture}")

                                        lens = sub.get(0xA434)
                                        if lens:
                                            self.meta_lens_lbl.setText(f"Lens: {lens}")
                                except Exception:
                                    pass

                                try:
                                    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
                                    if gps:
                                        lat = gps.get(2)
                                        lon = gps.get(4)
                                        if lat and lon:
                                            self.meta_location_lbl.setText(f"Location: {lat}, {lon}")
                                except Exception:
                                    pass
                    except Exception as e:
                        print(f"Metadata Read Error for {p.name}: {e}")
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
                # video metadata probing disabled for stability during selection
        
            self.btn_save_meta.setProperty("baseText", "Save Changes to Database")
            self.btn_clear_bulk_tags.setProperty("baseText", "Clear All Tags")
            self.btn_save_to_exif.setProperty("baseText", "Embed Data in File")
            self._sync_sidebar_panel_widths()
        else:
            # Bulk mode
            self._set_tag_editor_text("", self.meta_tags)
            if self._current_bulk_editor_mode() == "captions":
                self._configure_bulk_caption_editor(len(paths))
            else:
                self._configure_bulk_tag_editor(len(paths))

        self.meta_filename_edit.blockSignals(False)
        self.meta_desc.blockSignals(False)
        self.meta_tags.blockSignals(False)
        self.meta_notes.blockSignals(False)
        self.meta_exif_date_taken_edit.blockSignals(False)
        self.meta_metadata_date_edit.blockSignals(False)
        self.meta_detected_text_edit.blockSignals(False)
        self.meta_text_detected_toggle.blockSignals(False)
        self.meta_ai_generated_toggle.blockSignals(False)
        self._metadata_applied_revision = active_revision
        self._sync_tag_list_panel_visibility(refresh_contents=False)
        self._schedule_tag_list_refresh("rows", request_revision=active_revision)

    def _clear_embedded_labels(self):
        self.meta_camera_lbl.setText("Camera: ")
        self.meta_location_lbl.setText("Location: ")
        self.meta_iso_lbl.setText("ISO: ")
        self.meta_shutter_lbl.setText("Shutter: ")
        self.meta_aperture_lbl.setText("Aperture: ")
        self.meta_software_lbl.setText("Software: ")
        self.meta_lens_lbl.setText("Lens: ")
        self.meta_dpi_lbl.setText("DPI: ")
        self.meta_embedded_tags_edit.setText("")
        self.meta_embedded_comments_edit.setPlainText("")
        self.meta_ai_status_edit.setText("")
        self._set_metadata_switch(self.meta_ai_generated_toggle, False)
        self._set_metadata_switch(self.meta_text_detected_toggle, False)
        self.meta_detected_text_edit.setPlainText("")
        self._current_user_confirmed_text_detected = None
        self._current_auto_text_detected = None
        self._ai_generated_override_dirty = False
        self._text_detected_override_dirty = False
        self._update_override_note_labels(auto_text_detected=None, auto_ai_detected=None)
        self.meta_ai_source_edit.setPlainText("")
        self.meta_ai_families_edit.setText("")
        self.meta_ai_detection_reasons_edit.setPlainText("")
        self.meta_ai_loras_edit.setPlainText("")
        self.meta_ai_model_edit.setText("")
        self.meta_ai_checkpoint_edit.setText("")
        self.meta_ai_sampler_edit.setText("")
        self.meta_ai_scheduler_edit.setText("")
        self.meta_ai_cfg_edit.setText("")
        self.meta_ai_steps_edit.setText("")
        self.meta_ai_seed_edit.setText("")
        self.meta_ai_upscaler_edit.setText("")
        self.meta_ai_denoise_edit.setText("")
        self.meta_ai_prompt_edit.setPlainText("")
        self.meta_ai_negative_prompt_edit.setPlainText("")
        self.meta_ai_params_edit.setPlainText("")
        self.meta_ai_workflows_edit.setPlainText("")
        self.meta_ai_provenance_edit.setPlainText("")
        self.meta_ai_character_cards_edit.setPlainText("")
        self.meta_ai_raw_paths_edit.setPlainText("")

    def _is_metadata_enabled(self, key: str, default: bool = True) -> bool:
        """Read metadata visibility setting with robust boolean conversion."""
        try:
            qkey = f"metadata/display/{key}"
            # Ensure we have the latest from disk
            self.bridge.settings.sync()
            val = self.bridge.settings.value(qkey)
            if val is None:
                if key == "originalfiledate":
                    fallback = self.bridge.settings.value("metadata/display/filecreateddate")
                    if fallback is None:
                        return default
                    if isinstance(fallback, str):
                        return fallback.lower() in ("true", "1")
                    return bool(fallback)
                return default
            # Handle PySide6/Qt behavior on different platforms
            if isinstance(val, str):
                return val.lower() in ("true", "1")
            return bool(val)
        except Exception:
            return default

    def _metadata_kind_for_path(self, path: str | None) -> str:
        if not path:
            return "image"
        p = Path(path)
        if self.bridge._is_animated(p):
            return "gif"
        if p.suffix.lower() == ".svg":
            return "svg"
        if p.suffix.lower() in IMAGE_EXTS - {".gif"}:
            return "image"
        return "video"

    def _metadata_group_fields(self, kind: str) -> dict[str, list[str]]:
        image_general = ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "textdetected", "description", "tags", "notes", "embeddedtags", "embeddedcomments", "embeddedmetadata"]
        image_camera = ["camera", "location", "iso", "shutter", "aperture", "software", "lens", "dpi"]
        image_ai = [
            "aistatus", "aigenerated", "aisource", "aifamilies", "aidetectionreasons", "ailoras", "aimodel", "aicheckpoint",
            "aisampler", "aischeduler", "aicfg", "aisteps", "aiseed", "aiupscaler", "aidenoise",
            "aiprompt", "ainegprompt", "aiparams", "aiworkflows", "aiprovenance", "aicharcards", "airawpaths",
        ]
        if kind == "video":
            return {
                "general": ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "textdetected", "duration", "fps", "codec", "audio", "description", "tags", "notes", "embeddedmetadata"],
                "ai": image_ai,
            }
        if kind == "gif":
            return {
                "general": ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "textdetected", "duration", "fps", "description", "tags", "notes", "embeddedtags", "embeddedcomments", "embeddedmetadata"],
                "ai": image_ai,
            }
        if kind == "svg":
            return {
                "general": ["res", "size", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "textdetected", "description", "tags", "notes", "embeddedmetadata"],
            }
        return {"general": image_general, "camera": image_camera, "ai": image_ai}

    def _run_text_ocr(self) -> None:
        path = str(getattr(self, "_current_path", "") or "").strip()
        if not path:
            return
        self.btn_use_ocr.setEnabled(False)
        self.btn_use_ocr.setProperty("baseText", "Running OCR...")
        self._wrap_button_text(self.btn_use_ocr, "Running OCR...", self._right_panel_content_width())
        self.meta_status_lbl.setText("Running OCR...")
        self.bridge.run_manual_ocr(path)

    @Slot(str, str, str)
    def _on_manual_ocr_finished(self, path: str, text: str, error: str) -> None:
        if hasattr(self, "btn_use_ocr"):
            self.btn_use_ocr.setEnabled(True)
            self.btn_use_ocr.setProperty("baseText", "Use OCR")
            self._wrap_button_text(self.btn_use_ocr, "Use OCR", self._right_panel_content_width())
        if str(getattr(self, "_current_path", "") or "") != str(path or ""):
            return
        if error:
            self.meta_status_lbl.setText(f"OCR Error: {error}")
            QTimer.singleShot(4000, lambda: self.meta_status_lbl.setText(""))
            return
        clean_text = str(text or "").strip()
        if clean_text:
            self.meta_detected_text_edit.setPlainText(clean_text)
            self._set_metadata_switch(self.meta_text_detected_toggle, True)
            self._current_user_confirmed_text_detected = True
            self._text_detected_override_dirty = False
            self.meta_status_lbl.setText("OCR text saved")
        else:
            self.meta_status_lbl.setText("No OCR text found")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))

    def _local_ai_target_paths(self) -> list[str]:
        paths = self._current_file_paths()
        if not paths:
            path = str(getattr(self, "_current_path", "") or "").strip()
            paths = [path] if path else []
        return [str(path) for path in paths if str(path or "").strip()]

    def _run_local_ai_captioning(self) -> None:
        self._run_local_ai_tags()

    def _local_ai_progress_label(self):
        operation = str(getattr(self, "_local_ai_operation", "tags") or "tags")
        if operation == "descriptions":
            return getattr(self, "generate_description_progress_lbl", None)
        return getattr(self, "generate_tags_progress_lbl", None)

    def _local_ai_error_widget(self, operation: str):
        if operation == "descriptions":
            return getattr(self, "generate_description_error_edit", None)
        return getattr(self, "generate_tags_error_edit", None)

    def _set_local_ai_progress_text(self, text: str, operation: str | None = None) -> None:
        operation = str(operation or getattr(self, "_local_ai_operation", "tags") or "tags")
        progress_label = getattr(self, "generate_description_progress_lbl", None) if operation == "descriptions" else getattr(self, "generate_tags_progress_lbl", None)
        error_widget = self._local_ai_error_widget(operation)
        if progress_label is None or error_widget is None:
            return
        clean_text = str(text or "").strip()
        is_error = clean_text.startswith("Error:")
        if clean_text:
            if operation == "descriptions":
                visible = self.generate_description_btn_row.isVisible()
            else:
                visible = self.generate_tags_btn_row.isVisible()
            progress_label.setText("" if is_error else clean_text)
            progress_label.setVisible(bool(visible and not is_error))
            error_widget.setPlainText(clean_text if is_error else "")
            error_widget.setVisible(bool(visible and is_error))
            if hasattr(self, "meta_status_lbl"):
                self.meta_status_lbl.setVisible(False)
        else:
            progress_label.setText("")
            progress_label.setVisible(False)
            error_widget.setPlainText("")
            error_widget.setVisible(False)
            if hasattr(self, "meta_status_lbl"):
                self.meta_status_lbl.setVisible(bool(self.meta_status_lbl.text().strip()))
        try:
            self._sync_sidebar_panel_widths()
        except Exception:
            pass

    def _local_ai_progress_message(self, current: int, total: int) -> str:
        total = max(0, int(total or 0))
        current = max(0, min(int(current or 0), total))
        percent = int(round((current / total) * 100)) if total else 0
        label = "description" if getattr(self, "_local_ai_operation", "tags") == "descriptions" else "tags"
        return f"Generating {label}: {percent}% ({current}/{total})"

    def _set_bulk_local_ai_status(self, text: str) -> None:
        if not hasattr(self, "bulk_status_lbl"):
            return
        if self._is_bulk_editor_active():
            if getattr(self, "_local_ai_operation", "tags") == "descriptions" and hasattr(self, "bulk_caption_status_lbl"):
                self.bulk_caption_status_lbl.setText(str(text or ""))
            else:
                self.bulk_status_lbl.setText(str(text or ""))

    def _run_local_ai_tags(self) -> None:
        paths = self._local_ai_target_paths()
        if not paths:
            self._set_local_ai_progress_text("Select one or more media files first.", "tags")
            return
        if not self._ensure_local_ai_model_ready("tagger"):
            return
        if hasattr(self.bridge, "run_local_ai_tags"):
            self._local_ai_operation = "tags"
            self._local_ai_total = len(paths)
            self._local_ai_completed = 0
            self._set_local_ai_progress_text("", "descriptions")
            self._set_local_ai_progress_text(self._local_ai_progress_message(0, len(paths)), "tags")
            self._set_bulk_local_ai_status(f"Generating tags for all: 0/{len(paths)}")
            started = self.bridge.run_local_ai_tags(paths)
            if not started:
                self._set_local_ai_progress_text("Local AI tags are already running or no valid files were selected.", "tags")
                self._set_bulk_local_ai_status("Local AI tags are already running or no valid files were selected.")

    def _run_local_ai_description(self) -> None:
        paths = self._local_ai_target_paths()
        if not paths:
            self._set_local_ai_progress_text("Select one or more media files first.", "descriptions")
            return
        if not self._ensure_local_ai_model_ready("captioner"):
            return
        if hasattr(self.bridge, "run_local_ai_descriptions"):
            self._local_ai_operation = "descriptions"
            self._local_ai_total = len(paths)
            self._local_ai_completed = 0
            self._set_local_ai_progress_text("", "tags")
            self._set_local_ai_progress_text(self._local_ai_progress_message(0, len(paths)), "descriptions")
            self._set_bulk_local_ai_status(f"Generating descriptions for all: 0/{len(paths)}")
            started = self.bridge.run_local_ai_descriptions(paths)
            if not started:
                self._set_local_ai_progress_text("Local AI descriptions are already running or no valid files were selected.", "descriptions")
                self._set_bulk_local_ai_status("Local AI descriptions are already running or no valid files were selected.")

    def _set_local_ai_buttons_enabled(self, enabled: bool) -> None:
        for btn in (
            getattr(self, "btn_generate_tags", None),
            getattr(self, "btn_generate_description", None),
            getattr(self, "bulk_btn_run_local_ai", None),
            getattr(self, "bulk_caption_btn_run_local_ai", None),
        ):
            if btn is not None:
                btn.setEnabled(enabled)

    @Slot(int)
    def _on_local_ai_captioning_started(self, total: int) -> None:
        self._set_local_ai_buttons_enabled(False)
        self._local_ai_total = int(total or 0)
        self._local_ai_completed = 0
        self._set_local_ai_progress_text(self._local_ai_progress_message(0, int(total or 0)))
        if getattr(self, "_local_ai_operation", "tags") == "tags":
            self._set_bulk_local_ai_status(f"Generating tags for all: 0/{int(total or 0)}")
        elif getattr(self, "_local_ai_operation", "tags") == "descriptions":
            self._set_bulk_local_ai_status(f"Generating descriptions for all: 0/{int(total or 0)}")

    @Slot(str, int, int)
    def _on_local_ai_captioning_progress(self, path: str, current: int, total: int) -> None:
        completed_before_current = max(0, int(current or 0) - 1)
        self._set_local_ai_progress_text(self._local_ai_progress_message(completed_before_current, int(total or 0)))
        if getattr(self, "_local_ai_operation", "tags") == "tags":
            self._set_bulk_local_ai_status(f"Generating tags for all: {completed_before_current}/{int(total or 0)}")
        elif getattr(self, "_local_ai_operation", "tags") == "descriptions":
            self._set_bulk_local_ai_status(f"Generating descriptions for all: {completed_before_current}/{int(total or 0)}")

    @Slot(str)
    def _on_local_ai_captioning_status(self, message: str) -> None:
        clean = str(message or "").strip()
        if not clean:
            return
        self._set_local_ai_progress_text(clean)
        if getattr(self, "_local_ai_operation", "tags") in {"tags", "descriptions"}:
            self._set_bulk_local_ai_status(clean)

    @staticmethod
    def _format_local_ai_error(error: str) -> str:
        clean = " ".join(str(error or "").replace("\r", " ").replace("\n", " ").split()).strip()
        if not clean:
            return "Local AI failed."
        if len(clean) > 360:
            clean = clean[:357].rstrip() + "..."
        return clean

    @Slot(str, list, str, str)
    def _on_local_ai_captioning_item_finished(self, path: str, tags: list, description: str, error: str) -> None:
        current_path = str(getattr(self, "_current_path", "") or "")
        if error:
            clean_error = self._format_local_ai_error(error)
            self._set_local_ai_progress_text(f"Error: {clean_error}")
            if getattr(self, "_local_ai_operation", "tags") in {"tags", "descriptions"}:
                self._set_bulk_local_ai_status(f"Error: {clean_error}")
            return
        total = int(getattr(self, "_local_ai_total", 0) or 0)
        completed = min(total, int(getattr(self, "_local_ai_completed", 0) or 0) + 1) if total else 0
        self._local_ai_completed = completed
        self._set_local_ai_progress_text(self._local_ai_progress_message(completed, total))
        if getattr(self, "_local_ai_operation", "tags") == "tags":
            self._set_bulk_local_ai_status(f"Generating tags for all: {completed}/{total}")
            self._refresh_bulk_tag_selected_files_list()
        elif getattr(self, "_local_ai_operation", "tags") == "descriptions":
            self._set_bulk_local_ai_status(f"Generating descriptions for all: {completed}/{total}")
            self._refresh_bulk_caption_selected_files_list()
        if current_path and os.path.normcase(os.path.abspath(current_path)) == os.path.normcase(os.path.abspath(str(path or ""))):
            clean_tags = [str(tag) for tag in (tags or []) if str(tag).strip()]
            if clean_tags:
                self._set_tag_editor_text(", ".join(clean_tags), self.meta_tags)
                self._refresh_tag_list_scope_counts()
            clean_description = str(description or "").strip()
            if clean_description:
                self.meta_desc.setPlainText(clean_description)

    @Slot(int, str)
    def _on_local_ai_captioning_finished(self, completed: int, error: str) -> None:
        self._set_local_ai_buttons_enabled(True)
        if error:
            clean_error = self._format_local_ai_error(error)
            self._set_local_ai_progress_text(f"Error: {clean_error}")
            if getattr(self, "_local_ai_operation", "tags") in {"tags", "descriptions"}:
                self._set_bulk_local_ai_status(f"Error: {clean_error}")
            return
        total = int(getattr(self, "_local_ai_total", completed) or completed or 0)
        self._local_ai_completed = int(completed or 0)
        self._set_local_ai_progress_text(f"Complete: 100% ({int(completed or 0)}/{total})")
        if getattr(self, "_local_ai_operation", "tags") == "tags":
            self._set_bulk_local_ai_status(f"Generating tags for all: {int(completed or 0)}/{total}")
            self._refresh_bulk_tag_selected_files_list()
        elif getattr(self, "_local_ai_operation", "tags") == "descriptions":
            self._set_bulk_local_ai_status(f"Generating descriptions for all: {int(completed or 0)}/{total}")
            self._refresh_bulk_caption_selected_files_list()
        if getattr(self, "_current_paths", None):
            self._show_metadata_for_path(self._current_paths)

    @Slot(bool)
    def _save_text_detected_override_from_toggle(self, checked: bool) -> None:
        self._text_detected_override_dirty = False
        path = str(getattr(self, "_current_path", "") or "").strip()
        if not path:
            self._text_detected_override_dirty = True
            return
        try:
            value = bool(checked)
            self.bridge.update_media_text_override(path, value)
            self._current_user_confirmed_text_detected = value
            self.meta_status_lbl.setText("Text detection override saved")
            QTimer.singleShot(2500, lambda: self.meta_status_lbl.setText(""))
        except Exception:
            self._text_detected_override_dirty = True

    @Slot(bool)
    def _save_ai_generated_override_from_toggle(self, checked: bool) -> None:
        self._ai_generated_override_dirty = False
        path = str(getattr(self, "_current_path", "") or "").strip()
        if not path:
            self._ai_generated_override_dirty = True
            return
        try:
            current_ai_meta = dict(getattr(self, "_current_ai_meta", {}) or {})
            value = bool(checked)
            payload = {
                "is_ai_detected": bool(current_ai_meta.get("is_ai_detected")),
                "is_ai_confidence": float(current_ai_meta.get("is_ai_confidence") or 0.0),
                "user_confirmed_ai": value,
                "tool_name_found": current_ai_meta.get("tool_name_found"),
                "tool_name_inferred": current_ai_meta.get("tool_name_inferred"),
                "tool_name_confidence": current_ai_meta.get("tool_name_confidence"),
                "source_formats": list(current_ai_meta.get("source_formats") or []),
            }
            self.bridge.update_media_ai_metadata(path, payload)
            current_ai_meta["user_confirmed_ai"] = value
            self._current_ai_meta = current_ai_meta
            self.meta_status_lbl.setText("AI detection override saved")
            QTimer.singleShot(2500, lambda: self.meta_status_lbl.setText(""))
        except Exception:
            self._ai_generated_override_dirty = True

    def _metadata_default_group_order(self, kind: str) -> list[str]:
        return list(self._metadata_group_fields(kind).keys())

    def _metadata_group_order(self, kind: str) -> list[str]:
        default_order = self._metadata_default_group_order(kind)
        raw = str(self.bridge.settings.value(f"metadata/layout/{kind}/group_order", "[]") or "[]")
        try:
            order = json.loads(raw)
        except Exception:
            order = []
        if not isinstance(order, list):
            order = []
        for key in default_order:
            if key not in order:
                order.append(key)
        return [key for key in order if key in default_order]

    def _metadata_field_order(self, kind: str, group: str) -> list[str]:
        defaults = list(self._metadata_group_fields(kind).get(group, []))
        raw = str(self.bridge.settings.value(f"metadata/layout/{kind}/field_order/{group}", "[]") or "[]")
        try:
            order = json.loads(raw)
        except Exception:
            order = []
        if not isinstance(order, list):
            order = []
        for key in defaults:
            if key not in order:
                order.append(key)
        return [key for key in order if key in defaults]

    def _is_metadata_group_enabled(self, kind: str, group: str, default: bool = True) -> bool:
        try:
            qkey = f"metadata/display/{kind}/groups/{group}"
            self.bridge.settings.sync()
            val = self.bridge.settings.value(qkey)
            if val is None:
                return default
            if isinstance(val, str):
                return val.lower() in ("true", "1")
            return bool(val)
        except Exception:
            return default

    def _is_metadata_enabled_for_kind(self, kind: str, key: str, default: bool = True) -> bool:
        try:
            qkey = f"metadata/display/{kind}/{key}"
            self.bridge.settings.sync()
            val = self.bridge.settings.value(qkey)
            if val is None:
                if key == "originalfiledate":
                    fallback = self.bridge.settings.value(f"metadata/display/{kind}/filecreateddate")
                    if fallback is None:
                        return self._is_metadata_enabled("filecreateddate", default)
                    if isinstance(fallback, str):
                        return fallback.lower() in ("true", "1")
                    return bool(fallback)
                return self._is_metadata_enabled(key, default)
            if isinstance(val, str):
                return val.lower() in ("true", "1")
            return bool(val)
        except Exception:
            return default

    @staticmethod
    def _format_sidebar_datetime(value: str | None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return dt.strftime("%Y-%m-%d %I:%M %p").lstrip("0").replace(" 0", " ")
        except Exception:
            return str(value or "")

    @staticmethod
    def _normalize_metadata_datetime(value: str | None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        for parser in (
            lambda raw: datetime.fromisoformat(raw),
            lambda raw: datetime.strptime(raw, "%Y:%m:%d %H:%M:%S"),
            lambda raw: datetime.strptime(raw, "%Y:%m:%d"),
            lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
            lambda raw: datetime.strptime(raw, "%Y-%m-%d"),
        ):
            try:
                parsed = parser(text)
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed.replace(microsecond=0).isoformat(sep="T")
            except Exception:
                continue
        return text

    @classmethod
    def _format_editable_datetime(cls, value: str | None) -> str:
        normalized = cls._normalize_metadata_datetime(value)
        if not normalized:
            return ""
        try:
            return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return normalized

    @classmethod
    def _format_exif_datetime(cls, value: str | None) -> str:
        normalized = cls._normalize_metadata_datetime(value)
        if not normalized:
            return ""
        try:
            return datetime.fromisoformat(normalized).strftime("%Y:%m:%d %H:%M:%S")
        except Exception:
            return ""

    @classmethod
    def _format_xmp_datetime(cls, value: str | None) -> str:
        normalized = cls._normalize_metadata_datetime(value)
        if not normalized:
            return ""
        try:
            return datetime.fromisoformat(normalized).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return ""

    @staticmethod
    def _parse_ai_text_list(value: str | None) -> list[str]:
        raw = str(value or "").replace("\r", "\n")
        parts: list[str] = []
        for chunk in raw.replace(",", "\n").split("\n"):
            text = chunk.strip()
            if text and text not in parts:
                parts.append(text)
        return parts

    @staticmethod
    def _parse_optional_float(value: str | None):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _parse_optional_int(value: str | None):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return int(float(text))
        except Exception:
            return None

    @staticmethod
    def _parse_ai_status_override(value: str | None, fallback_detected: bool, fallback_confidence: float) -> tuple[bool, float]:
        text = str(value or "").strip()
        if not text:
            return bool(fallback_detected), float(fallback_confidence or 0.0)
        lowered = text.lower()
        detected = bool(fallback_detected)
        if any(token in lowered for token in ("not detected", "non-ai", "non ai", "no ai", "false", "no")):
            detected = False
        elif any(token in lowered for token in ("detected", "ai generated", "true", "yes")):
            detected = True

        confidence = float(fallback_confidence or 0.0)
        pct_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
        if pct_match:
            confidence = max(0.0, min(1.0, float(pct_match.group(1)) / 100.0))
        else:
            num_match = re.search(r"(-?\d+(?:\.\d+)?)", text)
            if num_match:
                parsed = float(num_match.group(1))
                confidence = max(0.0, min(1.0, parsed if parsed <= 1.0 else parsed / 100.0))
            elif detected != bool(fallback_detected):
                confidence = 1.0 if detected else 0.0
        return detected, confidence

    @classmethod
    def _parse_ai_source_override(cls, value: str | None, fallback: dict | None = None) -> dict:
        text = str(value or "").replace("\r", "\n").strip()
        existing = dict(fallback or {})
        tool_found = str(existing.get("tool_name_found") or "").strip()
        tool_inferred = str(existing.get("tool_name_inferred") or "").strip()
        tool_confidence = float(existing.get("tool_name_confidence") or 0.0)
        source_formats = [str(item).strip() for item in (existing.get("source_formats") or []) if str(item).strip()]
        if not text:
            return {
                "tool_name_found": tool_found,
                "tool_name_inferred": tool_inferred,
                "tool_name_confidence": tool_confidence,
                "source_formats": source_formats,
            }

        freeform_lines: list[str] = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("found:"):
                tool_found = line.split(":", 1)[1].strip()
                continue
            if lower.startswith("inferred:"):
                tool_inferred = line.split(":", 1)[1].strip()
                continue
            if lower.startswith("inference confidence:"):
                parsed = cls._parse_ai_status_override(line, True, tool_confidence)[1]
                tool_confidence = parsed
                continue
            if lower.startswith("formats:") or lower.startswith("source formats:"):
                source_formats = cls._parse_ai_text_list(line.split(":", 1)[1])
                continue
            freeform_lines.append(line)

        if freeform_lines:
            if not tool_found and len(freeform_lines) == 1:
                tool_found = freeform_lines[0]
            elif not tool_found:
                tool_found = freeform_lines[0]
                for line in freeform_lines[1:]:
                    if line not in source_formats:
                        source_formats.append(line)
        return {
            "tool_name_found": tool_found,
            "tool_name_inferred": tool_inferred,
            "tool_name_confidence": tool_confidence,
            "source_formats": source_formats,
        }

    @staticmethod
    def _set_switch_value_label(label: QLabel, checked: bool, on_text: str, off_text: str) -> None:
        label.setText(on_text if checked else off_text)

    @staticmethod
    def _auto_text_detected_note_value(value) -> str:
        if isinstance(value, str):
            detected = value.strip().lower() in {"1", "true", "yes", "text", "text_detected"}
        else:
            detected = bool(value)
        return "Text Detected" if detected else "No Text Detected"

    @staticmethod
    def _auto_ai_detected_note_value(value) -> str:
        if isinstance(value, str):
            detected = value.strip().lower() in {"1", "true", "yes", "ai", "ai_generated"}
        else:
            detected = bool(value)
        return "AI Generated" if detected else "Not AI Generated"

    def _update_override_note_labels(self, *, auto_text_detected=None, auto_ai_detected=None) -> None:
        if hasattr(self, "lbl_text_detected_note"):
            self.lbl_text_detected_note.setText(
                "This overrides the auto text detection value of "
                f"[{self._auto_text_detected_note_value(auto_text_detected)}]"
            )
        if hasattr(self, "lbl_ai_generated_note"):
            self.lbl_ai_generated_note.setText(
                "This overrides the auto AI Detection value of "
                f"[{self._auto_ai_detected_note_value(auto_ai_detected)}]"
            )

    def _set_metadata_switch(self, toggle: QCheckBox, checked: bool) -> None:
        toggle.setChecked(bool(checked))
        if toggle is getattr(self, "meta_ai_generated_toggle", None):
            self._set_switch_value_label(self.meta_ai_generated_value_lbl, bool(checked), "AI", "Non-AI")
        elif toggle is getattr(self, "meta_text_detected_toggle", None):
            self._set_switch_value_label(self.meta_text_detected_value_lbl, bool(checked), "Text", "No Text")

    @staticmethod
    def _parse_user_confirmed_ai(value: str | None):
        text = str(value or "").strip().lower()
        if not text:
            return None
        if text in {"yes", "true", "1", "ai", "detected"}:
            return True
        if text in {"no", "false", "0", "non-ai", "non ai", "not detected"}:
            return False
        return None

    @staticmethod
    def _format_duration_seconds(seconds: float | None) -> str:
        if not seconds or seconds <= 0:
            return ""
        total_ms = int(round(seconds * 1000))
        total_seconds = total_ms // 1000
        hours, rem = divmod(total_seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _probe_video_details(self, video_path: str) -> dict[str, str]:
        ffprobe = self.bridge._ffprobe_bin()
        if not ffprobe:
            return {}
        runtime_path = self.bridge._video_runtime_path(video_path)
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", runtime_path]
        try:
            probe = json.loads(_run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5).stdout or "{}")
        except Exception:
            return {}
        video_stream = None
        audio_stream = None
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream
        fps_text = ""
        if video_stream:
            rate = str(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "")
            if rate and "/" in rate:
                try:
                    num, den = rate.split("/", 1)
                    den_v = float(den)
                    if den_v:
                        fps_text = f"{float(num) / den_v:.2f}".rstrip("0").rstrip(".")
                except Exception:
                    fps_text = ""
        duration = ""
        try:
            duration = self._format_duration_seconds(float(probe.get("format", {}).get("duration") or 0.0))
        except Exception:
            duration = ""
        return {
            "duration": duration,
            "fps": fps_text,
            "codec": str((video_stream or {}).get("codec_name") or "").upper(),
            "audio": "Yes" if audio_stream else "No",
        }

    def _load_video_sidebar_metadata_async(self, path: str) -> None:
        def work() -> None:
            payload: dict[str, str] = {}
            try:
                payload = self._probe_video_details(path)
            except Exception:
                payload = {}
            self.videoSidebarMetadataReady.emit(path, payload)
        threading.Thread(target=work, daemon=True).start()

    @Slot(str, dict)
    def _on_video_sidebar_metadata_ready(self, path: str, payload: dict) -> None:
        if getattr(self, "_current_path", None) != path:
            return
        if payload.get("duration"):
            self.meta_duration_lbl.setText(f"Duration: {payload['duration']}")
        if payload.get("fps"):
            self.meta_fps_lbl.setText(f"FPS: {payload['fps']}")
        if payload.get("codec"):
            self.meta_codec_lbl.setText(f"Codec: {payload['codec']}")
        if payload.get("audio"):
            self.meta_audio_lbl.setText(f"Audio: {payload['audio']}")

    def _probe_animated_image_details(self, path: str) -> dict[str, str]:
        try:
            from PIL import Image
            with Image.open(path) as img:
                frames = int(getattr(img, "n_frames", 1) or 1)
                total_ms = 0
                for idx in range(frames):
                    try:
                        img.seek(idx)
                        total_ms += int(img.info.get("duration") or 0)
                    except Exception:
                        pass
                fps = ""
                if total_ms > 0 and frames > 0:
                    fps_val = frames / (total_ms / 1000.0)
                    fps = f"{fps_val:.2f}".rstrip("0").rstrip(".")
                return {
                    "duration": self._format_duration_seconds(total_ms / 1000.0),
                    "fps": fps,
                    "codec": "ANIMATED WEBP" if path.lower().endswith(".webp") else "GIF",
                    "audio": "No",
                }
        except Exception:
            return {}

    def _setup_metadata_layout(self, kind: str | None = None):
        """Group metadata widgets and apply the saved display order."""
        kind = kind or getattr(self, "_current_metadata_kind", "image")

        self._meta_groups = {
            "res": [self.meta_res_lbl],
            "size": [self.meta_size_lbl],
            "exifdatetaken": [self.lbl_exif_date_taken_cap, self.meta_exif_date_taken_edit],
            "metadatadate": [self.lbl_metadata_date_cap, self.meta_metadata_date_edit],
            "originalfiledate": [self.lbl_original_file_date_cap, self.meta_original_file_date_lbl],
            "filecreateddate": [self.lbl_file_created_date_cap, self.meta_file_created_date_lbl],
            "filemodifieddate": [self.lbl_file_modified_date_cap, self.meta_file_modified_date_lbl],
            "textdetected": [
                self.lbl_text_detected_cap,
                self.meta_text_detected_row,
                self.lbl_text_detected_note,
                self.lbl_detected_text_cap,
                self.meta_detected_text_edit,
                self.btn_use_ocr,
            ],
            "duration": [self.meta_duration_lbl],
            "fps": [self.meta_fps_lbl],
            "codec": [self.meta_codec_lbl],
            "audio": [self.meta_audio_lbl],
            "description": [
                self.lbl_desc_cap,
                self.meta_desc,
                self.generate_description_btn_row,
                self.generate_description_progress_lbl,
                self.generate_description_error_edit,
            ],
            "tags": [
                self.lbl_tags_cap,
                self.meta_tags,
                self.generate_tags_btn_row,
                self.generate_tags_progress_lbl,
                self.generate_tags_error_edit,
                self.tag_list_open_btn_row,
            ],
            "notes": [self.lbl_notes_cap, self.meta_notes],
            "camera": [self.meta_camera_lbl],
            "location": [self.meta_location_lbl],
            "iso": [self.meta_iso_lbl],
            "shutter": [self.meta_shutter_lbl],
            "aperture": [self.meta_aperture_lbl],
            "software": [self.meta_software_lbl],
            "lens": [self.meta_lens_lbl],
            "dpi": [self.meta_dpi_lbl],
            "embeddedtags": [self.lbl_embedded_tags_cap, self.meta_embedded_tags_edit],
            "embeddedcomments": [self.lbl_embedded_comments_cap, self.meta_embedded_comments_edit],
            "embeddedmetadata": [self.lbl_embedded_metadata_cap, self.meta_embedded_metadata_edit],
            "aistatus": [self.lbl_ai_status_cap, self.meta_ai_status_edit],
            "aigenerated": [self.lbl_ai_generated_cap, self.meta_ai_generated_row, self.lbl_ai_generated_note],
            "aisource": [self.lbl_ai_source_cap, self.meta_ai_source_edit],
            "aifamilies": [self.lbl_ai_families_cap, self.meta_ai_families_edit],
            "aidetectionreasons": [self.lbl_ai_detection_reasons_cap, self.meta_ai_detection_reasons_edit],
            "ailoras": [self.lbl_ai_loras_cap, self.meta_ai_loras_edit],
            "aimodel": [self.lbl_ai_model_cap, self.meta_ai_model_edit],
            "aicheckpoint": [self.lbl_ai_checkpoint_cap, self.meta_ai_checkpoint_edit],
            "aisampler": [self.lbl_ai_sampler_cap, self.meta_ai_sampler_edit],
            "aischeduler": [self.lbl_ai_scheduler_cap, self.meta_ai_scheduler_edit],
            "aicfg": [self.lbl_ai_cfg_cap, self.meta_ai_cfg_edit],
            "aisteps": [self.lbl_ai_steps_cap, self.meta_ai_steps_edit],
            "aiseed": [self.lbl_ai_seed_cap, self.meta_ai_seed_edit],
            "aiupscaler": [self.lbl_ai_upscaler_cap, self.meta_ai_upscaler_edit],
            "aidenoise": [self.lbl_ai_denoise_cap, self.meta_ai_denoise_edit],
            "aiprompt": [self.lbl_ai_prompt_cap, self.meta_ai_prompt_edit],
            "ainegprompt": [self.lbl_ai_negative_prompt_cap, self.meta_ai_negative_prompt_edit],
            "aiparams": [self.lbl_ai_params_cap, self.meta_ai_params_edit],
            "aiworkflows": [self.lbl_ai_workflows_cap, self.meta_ai_workflows_edit],
            "aiprovenance": [self.lbl_ai_provenance_cap, self.meta_ai_provenance_edit],
            "aicharcards": [self.lbl_ai_character_cards_cap, self.meta_ai_character_cards_edit],
            "airawpaths": [self.lbl_ai_raw_paths_cap, self.meta_ai_raw_paths_edit],
            "sep1": [self.meta_sep1],
            "sep2": [self.meta_sep2],
            "sep3": [self.meta_sep3],
        }

        # Clear existing layout items AND HIDE THEM to prevent visual duplication
        while self.meta_fields_layout.count():
            item = self.meta_fields_layout.takeAt(0)
            if item.widget():
                item.widget().hide()

        group_order = self._metadata_group_order(kind)
        visible_groups = [group for group in group_order if self._is_metadata_group_enabled(kind, group, True)]
        group_labels = {
            "general": self.lbl_group_general,
            "camera": self.lbl_group_camera,
            "ai": self.lbl_group_ai
        }
        sep_widgets = [self.meta_sep1, self.meta_sep2]
        sep_index = 0
        for index, group in enumerate(visible_groups):
            field_order = self._metadata_field_order(kind, group)
            label = group_labels.get(group)
            if label:
                self.meta_fields_layout.addWidget(label)
                label.show()
            for key in field_order:
                for widget in self._meta_groups.get(key, []):
                    self.meta_fields_layout.addWidget(widget)
            if index < len(visible_groups) - 1 and sep_index < len(sep_widgets):
                self.meta_fields_layout.addWidget(sep_widgets[sep_index])
                sep_index += 1

    def _clear_metadata_panel(self):
        """Reset all labels and hide/show them based on current settings."""
        self._set_active_right_workspace("details")
        self._current_path = None
        self._current_paths = []
        kind = getattr(self, "_current_metadata_kind", "image")
        self._setup_metadata_layout(kind)
        self._refresh_preview_for_path(None)
        
        self.meta_filename_edit.setText("")
        self.meta_path_lbl.setText("Folder: ")
        self.meta_size_lbl.setText("File Size: ")
        self.meta_res_lbl.setText("Resolution: ")
        self.meta_exif_date_taken_edit.setText("")
        self.meta_metadata_date_edit.setText("")
        self.meta_original_file_date_lbl.setText("")
        self.meta_file_created_date_lbl.setText("")
        self.meta_file_modified_date_lbl.setText("")
        self.meta_duration_lbl.setText("Duration: ")
        self.meta_fps_lbl.setText("FPS: ")
        self.meta_codec_lbl.setText("Codec: ")
        self.meta_audio_lbl.setText("Audio: ")
        self._clear_embedded_labels()
        
        # UI visibility logic
        visible_groups = [group for group in self._metadata_group_order(kind) if self._is_metadata_group_enabled(kind, group, True)]
        self.lbl_group_general.setVisible(False)
        self.lbl_group_camera.setVisible(False)
        self.lbl_group_ai.setVisible(False)
        active_fields = {
            field
            for group in visible_groups
            for field in self._metadata_group_fields(kind).get(group, [])
        }
        self.meta_res_lbl.setVisible("res" in active_fields and self._is_metadata_enabled_for_kind(kind, "res", True))
        self.meta_size_lbl.setVisible("size" in active_fields and self._is_metadata_enabled_for_kind(kind, "size", True))
        self.lbl_exif_date_taken_cap.setVisible("exifdatetaken" in active_fields and self._is_metadata_enabled_for_kind(kind, "exifdatetaken", False))
        self.meta_exif_date_taken_edit.setVisible("exifdatetaken" in active_fields and self._is_metadata_enabled_for_kind(kind, "exifdatetaken", False))
        self.lbl_metadata_date_cap.setVisible("metadatadate" in active_fields and self._is_metadata_enabled_for_kind(kind, "metadatadate", False))
        self.meta_metadata_date_edit.setVisible("metadatadate" in active_fields and self._is_metadata_enabled_for_kind(kind, "metadatadate", False))
        self.lbl_original_file_date_cap.setVisible("originalfiledate" in active_fields and self._is_metadata_enabled_for_kind(kind, "originalfiledate", False))
        self.meta_original_file_date_lbl.setVisible("originalfiledate" in active_fields and self._is_metadata_enabled_for_kind(kind, "originalfiledate", False))
        self.lbl_file_created_date_cap.setVisible("filecreateddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filecreateddate", False))
        self.meta_file_created_date_lbl.setVisible("filecreateddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filecreateddate", False))
        self.lbl_file_modified_date_cap.setVisible("filemodifieddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filemodifieddate", False))
        self.meta_file_modified_date_lbl.setVisible("filemodifieddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filemodifieddate", False))
        self.lbl_text_detected_cap.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.meta_text_detected_row.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.lbl_text_detected_note.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.lbl_detected_text_cap.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.meta_detected_text_edit.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.btn_use_ocr.setVisible("textdetected" in active_fields and self._is_metadata_enabled_for_kind(kind, "textdetected", True))
        self.meta_duration_lbl.setVisible("duration" in active_fields and self._is_metadata_enabled_for_kind(kind, "duration", True))
        self.meta_fps_lbl.setVisible("fps" in active_fields and self._is_metadata_enabled_for_kind(kind, "fps", True))
        self.meta_codec_lbl.setVisible("codec" in active_fields and self._is_metadata_enabled_for_kind(kind, "codec", True))
        self.meta_audio_lbl.setVisible("audio" in active_fields and self._is_metadata_enabled_for_kind(kind, "audio", True))
        self.meta_camera_lbl.setVisible("camera" in active_fields and self._is_metadata_enabled_for_kind(kind, "camera", False))
        self.meta_location_lbl.setVisible("location" in active_fields and self._is_metadata_enabled_for_kind(kind, "location", False))
        self.meta_iso_lbl.setVisible("iso" in active_fields and self._is_metadata_enabled_for_kind(kind, "iso", False))
        self.meta_shutter_lbl.setVisible("shutter" in active_fields and self._is_metadata_enabled_for_kind(kind, "shutter", False))
        self.meta_aperture_lbl.setVisible("aperture" in active_fields and self._is_metadata_enabled_for_kind(kind, "aperture", False))
        self.meta_software_lbl.setVisible("software" in active_fields and self._is_metadata_enabled_for_kind(kind, "software", False))
        self.meta_lens_lbl.setVisible("lens" in active_fields and self._is_metadata_enabled_for_kind(kind, "lens", False))
        self.meta_dpi_lbl.setVisible("dpi" in active_fields and self._is_metadata_enabled_for_kind(kind, "dpi", False))
        self.meta_embedded_tags_edit.setVisible("embeddedtags" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedtags", True))
        self.lbl_embedded_tags_cap.setVisible("embeddedtags" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedtags", True))
        self.meta_embedded_comments_edit.setVisible("embeddedcomments" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedcomments", True))
        self.lbl_embedded_comments_cap.setVisible("embeddedcomments" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedcomments", True))
        self.meta_embedded_metadata_edit.setVisible("embeddedmetadata" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedmetadata", True))
        self.lbl_embedded_metadata_cap.setVisible("embeddedmetadata" in active_fields and self._is_metadata_enabled_for_kind(kind, "embeddedmetadata", True))
        self.meta_ai_status_edit.setVisible("aistatus" in active_fields and self._is_metadata_enabled_for_kind(kind, "aistatus", True))
        self.lbl_ai_status_cap.setVisible("aistatus" in active_fields and self._is_metadata_enabled_for_kind(kind, "aistatus", True))
        self.meta_ai_generated_row.setVisible("aigenerated" in active_fields and self._is_metadata_enabled_for_kind(kind, "aigenerated", True))
        self.lbl_ai_generated_cap.setVisible("aigenerated" in active_fields and self._is_metadata_enabled_for_kind(kind, "aigenerated", True))
        self.lbl_ai_generated_note.setVisible("aigenerated" in active_fields and self._is_metadata_enabled_for_kind(kind, "aigenerated", True))
        self.meta_ai_source_edit.setVisible("aisource" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisource", True))
        self.lbl_ai_source_cap.setVisible("aisource" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisource", True))
        self.meta_ai_families_edit.setVisible("aifamilies" in active_fields and self._is_metadata_enabled_for_kind(kind, "aifamilies", True))
        self.lbl_ai_families_cap.setVisible("aifamilies" in active_fields and self._is_metadata_enabled_for_kind(kind, "aifamilies", True))
        self.meta_ai_detection_reasons_edit.setVisible("aidetectionreasons" in active_fields and self._is_metadata_enabled_for_kind(kind, "aidetectionreasons", False))
        self.lbl_ai_detection_reasons_cap.setVisible("aidetectionreasons" in active_fields and self._is_metadata_enabled_for_kind(kind, "aidetectionreasons", False))
        self.meta_ai_loras_edit.setVisible("ailoras" in active_fields and self._is_metadata_enabled_for_kind(kind, "ailoras", True))
        self.lbl_ai_loras_cap.setVisible("ailoras" in active_fields and self._is_metadata_enabled_for_kind(kind, "ailoras", True))
        self.meta_ai_model_edit.setVisible("aimodel" in active_fields and self._is_metadata_enabled_for_kind(kind, "aimodel", True))
        self.lbl_ai_model_cap.setVisible("aimodel" in active_fields and self._is_metadata_enabled_for_kind(kind, "aimodel", True))
        self.meta_ai_checkpoint_edit.setVisible("aicheckpoint" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicheckpoint", False))
        self.lbl_ai_checkpoint_cap.setVisible("aicheckpoint" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicheckpoint", False))
        self.meta_ai_sampler_edit.setVisible("aisampler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisampler", True))
        self.lbl_ai_sampler_cap.setVisible("aisampler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisampler", True))
        self.meta_ai_scheduler_edit.setVisible("aischeduler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aischeduler", True))
        self.lbl_ai_scheduler_cap.setVisible("aischeduler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aischeduler", True))
        self.meta_ai_cfg_edit.setVisible("aicfg" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicfg", True))
        self.lbl_ai_cfg_cap.setVisible("aicfg" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicfg", True))
        self.meta_ai_steps_edit.setVisible("aisteps" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisteps", True))
        self.lbl_ai_steps_cap.setVisible("aisteps" in active_fields and self._is_metadata_enabled_for_kind(kind, "aisteps", True))
        self.meta_ai_seed_edit.setVisible("aiseed" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiseed", True))
        self.lbl_ai_seed_cap.setVisible("aiseed" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiseed", True))
        self.meta_ai_upscaler_edit.setVisible("aiupscaler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiupscaler", False))
        self.lbl_ai_upscaler_cap.setVisible("aiupscaler" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiupscaler", False))
        self.meta_ai_denoise_edit.setVisible("aidenoise" in active_fields and self._is_metadata_enabled_for_kind(kind, "aidenoise", False))
        self.lbl_ai_denoise_cap.setVisible("aidenoise" in active_fields and self._is_metadata_enabled_for_kind(kind, "aidenoise", False))
        self.meta_ai_prompt_edit.setVisible("aiprompt" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiprompt", True))
        self.lbl_ai_prompt_cap.setVisible("aiprompt" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiprompt", True))
        self.meta_ai_negative_prompt_edit.setVisible("ainegprompt" in active_fields and self._is_metadata_enabled_for_kind(kind, "ainegprompt", True))
        self.lbl_ai_negative_prompt_cap.setVisible("ainegprompt" in active_fields and self._is_metadata_enabled_for_kind(kind, "ainegprompt", True))
        self.meta_ai_params_edit.setVisible("aiparams" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiparams", True))
        self.lbl_ai_params_cap.setVisible("aiparams" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiparams", True))
        self.meta_ai_workflows_edit.setVisible("aiworkflows" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiworkflows", False))
        self.lbl_ai_workflows_cap.setVisible("aiworkflows" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiworkflows", False))
        self.meta_ai_provenance_edit.setVisible("aiprovenance" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiprovenance", False))
        self.lbl_ai_provenance_cap.setVisible("aiprovenance" in active_fields and self._is_metadata_enabled_for_kind(kind, "aiprovenance", False))
        self.meta_ai_character_cards_edit.setVisible("aicharcards" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicharcards", False))
        self.lbl_ai_character_cards_cap.setVisible("aicharcards" in active_fields and self._is_metadata_enabled_for_kind(kind, "aicharcards", False))
        self.meta_ai_raw_paths_edit.setVisible("airawpaths" in active_fields and self._is_metadata_enabled_for_kind(kind, "airawpaths", False))
        self.lbl_ai_raw_paths_cap.setVisible("airawpaths" in active_fields and self._is_metadata_enabled_for_kind(kind, "airawpaths", False))
        self.meta_filename_edit.setVisible(True)
        self.meta_path_lbl.setVisible(True)
        
        self.meta_sep1.setVisible(len(visible_groups) > 1)
        self.meta_sep2.setVisible(len(visible_groups) > 2)
        self.meta_sep3.setVisible(False)
        
        
        description_visible = "description" in active_fields and self._is_metadata_enabled_for_kind(kind, "description", True)
        self.meta_desc.setVisible(description_visible)
        self.lbl_desc_cap.setVisible(description_visible)
        self.generate_description_btn_row.setVisible(description_visible)
        self.generate_description_progress_lbl.setVisible(
            description_visible and bool(self.generate_description_progress_lbl.text().strip())
        )
        self.generate_description_error_edit.setVisible(
            description_visible and bool(self.generate_description_error_edit.toPlainText().strip())
        )
        tags_visible = "tags" in active_fields and self._is_metadata_enabled_for_kind(kind, "tags", True)
        self.meta_tags.setVisible(tags_visible)
        self.lbl_tags_cap.setVisible(tags_visible)
        self.generate_tags_btn_row.setVisible(tags_visible)
        self.generate_tags_progress_lbl.setVisible(tags_visible and bool(self.generate_tags_progress_lbl.text().strip()))
        self.generate_tags_error_edit.setVisible(tags_visible and bool(self.generate_tags_error_edit.toPlainText().strip()))
        self.tag_list_open_btn_row.setVisible(tags_visible)
        self.meta_notes.setVisible("notes" in active_fields and self._is_metadata_enabled_for_kind(kind, "notes", True))
        self.lbl_notes_cap.setVisible("notes" in active_fields and self._is_metadata_enabled_for_kind(kind, "notes", True))
        
        self.meta_desc.setPlainText("")
        self.meta_notes.setPlainText("")
        self._set_tag_editor_text("", self.meta_tags)
        self._set_local_ai_progress_text("", "tags")
        self._set_local_ai_progress_text("", "descriptions")
        self.meta_status_lbl.setText("")
        self._set_metadata_empty_state(True)
        self._sync_tag_list_panel_visibility()

    def _on_splitter_moved(self) -> None:
        """Save splitter state and re-apply card selection if the resize caused a deselect."""
        self._maintain_tag_list_width_on_main_resize()
        self._save_splitter_state()
        self._sync_sidebar_panel_widths()
        self._update_preview_display()
        # Re-apply the full gallery selection via JS so resize doesn't visually collapse it to one card.
        selected_paths = [str(p or "") for p in list(getattr(self, "_current_paths", []) or []) if str(p or "").strip()]
        if selected_paths:
            selected_paths_js = json.dumps(selected_paths)
            self.web.page().runJavaScript(
                f"""
                (function(){{
                  var selected = new Set({selected_paths_js});
                  document.querySelectorAll('.card').forEach(function(card){{
                    var path = card.getAttribute('data-path') || '';
                    card.classList.toggle('selected', selected.has(path));
                  }});
                }})();
                """
            )
        self._schedule_gallery_container_relayout(120)

    def _on_right_splitter_moved(self) -> None:
        self._save_tag_list_panel_width()
        if self.tag_list_panel.isVisible():
            try:
                self.bridge.settings.setValue("ui/tag_list_last_details_width", self._details_panel_width_without_tag_list())
            except Exception:
                pass
        self._sync_sidebar_panel_widths()
        self._update_preview_display()
        self._schedule_gallery_container_relayout(120)

    def _handle_right_splitter_overflow_drag(self, delta_x: int) -> None:
        if delta_x >= 0 or not self.tag_list_panel.isVisible():
            return
        try:
            right_sizes = self._current_right_splitter_sizes()
            if len(right_sizes) < 2:
                return
            min_tag_width = 220
            tag_width = int(right_sizes[0])
            if tag_width > (min_tag_width + 2):
                return

            extra = abs(int(delta_x))
            main_sizes = self._current_splitter_sizes()
            if len(main_sizes) < 3:
                return
            left_width = int(main_sizes[0])
            center_width = int(main_sizes[1])
            right_width = int(main_sizes[2])

            center_shrink = min(max(0, center_width - 120), extra)
            center_width -= center_shrink
            extra -= center_shrink
            if extra > 0:
                left_shrink = min(max(0, left_width - 120), extra)
                left_width -= left_shrink
                extra -= left_shrink

            grown_by = abs(int(delta_x)) - extra
            if grown_by <= 0:
                return

            right_width += grown_by
            self.splitter.setSizes([left_width, center_width, right_width])
            next_details_width = max(240, right_width - min_tag_width)
            self.right_splitter.setSizes([min_tag_width, next_details_width])
            self.bridge.settings.setValue("ui/tag_list_panel_width", min_tag_width)
            self.bridge.settings.setValue("ui/tag_list_last_details_width", next_details_width)
        except Exception:
            pass

    def _maintain_tag_list_width_on_main_resize(self) -> None:
        if not hasattr(self, "right_splitter") or not self.tag_list_panel.isVisible():
            return
        try:
            details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._details_panel_width_without_tag_list(), type=int) or self._details_panel_width_without_tag_list()))
            total_right_width = max(240, int(self.right_panel_host.width() or self._current_splitter_sizes()[2]))
            min_tag_width = 220
            next_tag_width = max(min_tag_width, total_right_width - details_width)
            next_details_width = max(240, total_right_width - next_tag_width)
            self.right_splitter.setSizes([next_tag_width, next_details_width])
            self.bridge.settings.setValue("ui/tag_list_panel_width", int(next_tag_width))
        except Exception:
            pass

    def _on_tree_context_menu(self, pos: QPoint) -> None:
        idx = self.tree.indexAt(pos)
        if not idx.isValid():
            return

        source_idx = self.proxy_model.mapToSource(idx)
        folder_path = self.fs_model.filePath(source_idx)
        if not folder_path:
            return

        menu = QMenu(self)

        name = Path(folder_path).name
        is_hidden = self.bridge.repo.is_path_hidden(folder_path)

        act_hide = None
        act_unhide = None
        if is_hidden:
            act_unhide = menu.addAction("Unhide Folder")
        else:
            act_hide = menu.addAction("Hide Folder")

        is_pinned = self.bridge.is_folder_pinned(folder_path)
        act_pin = None
        act_unpin = None
        if is_pinned:
            act_unpin = menu.addAction("Unpin Folder")
        else:
            act_pin = menu.addAction("Pin Folder")

        act_rename = menu.addAction("Renameâ€¦")
        
        menu.addSeparator()
        act_new_folder = menu.addAction("New Folderâ€¦")
        act_delete = menu.addAction("Delete")
        
        menu.addSeparator()
        act_explorer = menu.addAction("Open in File Explorer")
        act_cut = menu.addAction("Cut")
        act_copy = menu.addAction("Copy")
        act_paste = menu.addAction("Paste")
        
        menu.addSeparator()
        act_select_all = menu.addAction("Select All Files in Folder")
        
        # Disable paste if no files in clipboard
        if not self.bridge.has_files_in_clipboard():
            act_paste.setEnabled(False)

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))

        if chosen == act_hide:
            success = self.bridge.set_folder_hidden(folder_path, True)
            if success:
                self.proxy_model.invalidateFilter()

        if chosen == act_unhide:
            success = self.bridge.set_folder_hidden(folder_path, False)
            if success:
                self.proxy_model.invalidateFilter()

        if chosen == act_pin:
            self.bridge.pin_folder(folder_path)

        if chosen == act_unpin:
            self.bridge.unpin_folder(folder_path)

        if chosen == act_select_all:
             self.web.page().runJavaScript("if(window.selectAll) window.selectAll();")

        if chosen == act_rename:
            cur = Path(folder_path).name
            next_name, ok = _run_themed_text_input_dialog(self, "Rename folder", "New name:", text=cur)
            if ok and next_name and next_name != cur:
                new_path = self.bridge.rename_path(folder_path, next_name)
                if new_path:
                    parent = str(Path(new_path).parent)
                    self.tree.setCurrentIndex(self.proxy_model.mapFromSource(self.fs_model.index(parent)))
                    self._set_selected_folders([parent])

        if chosen == act_explorer:
            self.bridge.open_in_explorer(folder_path)

        if chosen == act_cut:
            self.bridge.cut_to_clipboard([folder_path])

        if chosen == act_copy:
            self.bridge.copy_to_clipboard([folder_path])

        if chosen == act_paste:
            self.bridge.paste_into_folder_async(folder_path)

        if chosen == act_new_folder:
            self._create_folder_at(folder_path)

        if chosen == act_delete:
            self._delete_item(folder_path)

    def _create_folder_at(self, parent_path: str):
        name, ok = _run_themed_text_input_dialog(self, "New Folder", "Folder Name:")
        if ok and name:
            new_path = self.bridge.create_folder(parent_path, name)
            if new_path:
                 # QFileSystemModel auto-updates, but we might want to select it
                 pass

    def _delete_item(self, path_str: str):
        p = Path(path_str)
        
        modifiers = QApplication.keyboardModifiers()
        is_shift_down = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        
        use_recycle = bool(self.bridge.settings.value("gallery/use_recycle_bin", True, type=bool))
        use_retention = bool(self.bridge.settings.value("gallery/use_medialens_retention", False, type=bool))
        
        safe_delete = not is_shift_down and (use_recycle or use_retention)
        
        if safe_delete:
            self.bridge.delete_path(path_str)
        else:
            if p.is_dir():
                reply = _run_themed_question_dialog(
                    self,
                    "Confirm Permanent Delete",
                    f"Are you sure you want to permanently delete the folder and all its contents?\n\n{p.name}",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            else:
                reply = _run_themed_question_dialog(
                    self,
                    "Confirm Permanent Delete",
                    f"Are you sure you want to permanently delete this file?\n\n{p.name}",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.bridge.delete_path_permanent(path_str)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a media folder")
        if folder:
            self._on_load_folder_requested(folder)

    def _open_video_overlay(
        self, path: str, autoplay: bool, loop: bool, muted: bool, width: int, height: int
    ) -> None:
        # Track temp files created by preprocessing so we can delete on close
        if not hasattr(self, "_temp_video_path"):
            self._temp_video_path: str | None = None
        import tempfile, pathlib
        if pathlib.Path(path).parent == pathlib.Path(tempfile.gettempdir()) and path.startswith(
            str(pathlib.Path(tempfile.gettempdir()) / "mmx_fixed_")
        ):
            self._temp_video_path = path
        else:
            self._cleanup_temp_video()

        # Standard lightbox mode: cover entire web view and show backdrop
        self.video_overlay.setGeometry(self.web.rect())
        self.video_overlay.set_mode(is_inplace=False)
        self.video_overlay.open_video(
            VideoRequest(
                path=path,
                autoplay=autoplay,
                loop=loop,
                muted=muted,
                width=int(width),
                height=int(height),
            )
        )

    def _open_video_inplace(self, path: str, x: int, y: int, w: int, h: int, autoplay: bool, loop: bool, muted: bool, native_w: int, native_h: int) -> None:
        if not self.video_overlay:
            return
        
        # Reset stale native size so resizeEvents during set_mode/setGeometry
        # use the full-bounds fallback instead of the previous video's size.
        self.video_overlay._native_size = None

        # The rect from JS is already relative to the web view's viewport.
        # Since video_overlay is a child of self.web, we use parent-relative coords.
        target_rect = QRect(x, y, w, h)
        
        # Define header height to avoid covering search bars/toolbar
        header_height = self._web_header_height()
        
        self.video_overlay.set_mode(is_inplace=True) # In-place mode
        self.video_overlay.setGeometry(target_rect)
        
        if y < header_height:
            self.video_overlay.hide()
        else:
            self.video_overlay.show()
            self.video_overlay.raise_()

        self.video_overlay.open_video(
            VideoRequest(
                path=path,
                autoplay=autoplay,
                loop=loop,
                muted=muted,
                width=int(native_w),
                height=int(native_h),
            )
        )

    def _update_video_inplace_rect(self, x, y, w, h):
        if not self.video_overlay:
            return
            
        # Define header height for clipping
        header_height = self._web_header_height()
        
        # Relative coordinates for child widget
        target_rect = QRect(x, y, w, h)
        self.video_overlay.setGeometry(target_rect)
        
        # If the video top scrolls under the sticky header, hide it.
        # Also hide if it scrolls off the bottom (y > self.web.height() - small_buffer)
        if y < header_height:
            if self.video_overlay.isVisible():
                self.video_overlay.hide()
                self.bridge.videoSuppressed.emit(True)
        else:
            if not self.video_overlay.isVisible() and self.video_overlay.is_inplace_mode():
                 self.video_overlay.show()
                 self.video_overlay.raise_()
                 self.bridge.videoSuppressed.emit(False)

    def _on_video_muted_changed(self, muted: bool) -> None:
        if hasattr(self, "video_overlay"):
            self.video_overlay.set_muted(muted)

    def _on_video_paused_changed(self, paused: bool) -> None:
        if hasattr(self, "video_overlay"):
            if paused:
                self.video_overlay.player.pause()
            else:
                self.video_overlay.player.play()

    def _on_video_preprocessing_status(self, status: str) -> None:
        """Show/clear the preprocessing status in the overlay."""
        if status:
            # Show overlay in loading state before the fixed video is ready
            self.video_overlay.setGeometry(self.web.rect())
            self.video_overlay.show_preprocessing_status(status)
        # When status is empty, open_video will be called shortly which clears it

    def _cleanup_temp_video(self) -> None:
        """Delete any preprocessed temp file from a previous session."""
        if hasattr(self, "_temp_video_path") and self._temp_video_path:
            try:
                Path(self._temp_video_path).unlink(missing_ok=True)
                print(f"Preprocess Cleanup: Deleted {self._temp_video_path}")
            except Exception:
                pass
            self._temp_video_path = None

    def _close_web_lightbox(self) -> None:
        # Ask the web UI to close its lightbox chrome without re-triggering native close.
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_closeLightboxFromNative && window.__mmx_closeLightboxFromNative(); }catch(e){}"
            )
        except Exception:
            pass

    def _close_video_overlay(self) -> None:
        self.video_overlay.close_overlay(notify_web=False)
        overlay = getattr(self, "sidebar_video_overlay", None)
        if overlay is not None:
            overlay.close_overlay(notify_web=False)
        self._sync_sidebar_video_preview_controls()

    def _update_splitter_style(self, accent_color: str) -> None:
        """Update QSplitter handles with light grey idle and accent color hover."""
        if not hasattr(self, "splitter"):
            return
        
        self._current_accent = accent_color
        self.splitter.setHandleWidth(7)
        if hasattr(self, "center_splitter"):
            self.center_splitter.setHandleWidth(7)
        if hasattr(self, "right_splitter"):
            self.right_splitter.setHandleWidth(7)
        
        # We no longer need stylesheets or manual loops here because 
        # CustomSplitterHandle.paintEvent handles everything natively.
        for i in range(self.splitter.count()):
            h = self.splitter.handle(i)
            if h:
                h.update()
                h.repaint()
        if hasattr(self, "center_splitter"):
            for i in range(self.center_splitter.count()):
                h = self.center_splitter.handle(i)
                if h:
                    h.update()
                    h.repaint()
        if hasattr(self, "right_splitter"):
            for i in range(self.right_splitter.count()):
                h = self.right_splitter.handle(i)
                if h:
                    h.update()
                    h.repaint()

    def _on_accent_changed(self, accent_color: str) -> None:
        """Called when the bridge emits accentColorChanged."""
        self._current_accent = accent_color
        self._update_native_styles(accent_color)
        self._update_splitter_style(accent_color)
        self._apply_compare_panel_theme(accent_color)
        if hasattr(self, "compare_panel"):
            self.compare_panel.update()
            self.compare_panel.repaint()
        QTimer.singleShot(0, lambda: self._apply_compare_panel_theme(accent_color))
        
        # Update tooltip theme
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.update_style(QColor(accent_color), Theme.get_is_light())
        
        # Belt and suspenders: force update web layer via injection
        js = f"document.documentElement.style.setProperty('--accent', '{accent_color}');"
        if hasattr(self, "webview") and self.webview.page():
            self.webview.page().runJavaScript(js)
        try:
            refresh_widgets: list[QWidget] = [
                self,
                self.left_panel,
                self.right_panel,
                self.scroll_area,
                self.scroll_container,
                self.bottom_panel,
            ]
            for widget in refresh_widgets:
                if widget is None:
                    continue
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
                widget.repaint()
            for sep in self.findChildren(NativeSeparator):
                sep.update()
                sep.repaint()
            if hasattr(self, "splitter"):
                self.splitter.update()
            if hasattr(self, "center_splitter"):
                self.center_splitter.update()
        except Exception:
            pass

    def _on_update_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        if not hasattr(self, "native_tooltip"):
            return
        
        # Store for tree hover sync
        self.bridge._last_drag_count = count
        
        op = "Copy" if is_copy else "Move"
        icon = "+" if is_copy else "â†’"
        items_text = f"{count} item" if count == 1 else f"{count} items"
        
        target_text = f" to <b>{target_folder}</b>" if target_folder else ""
        
        html = f"<div style='white-space: nowrap;'>{icon} {op} {items_text}{target_text}</div>"
        self.native_tooltip.update_text(html)
        self.native_tooltip.follow_cursor()

    def _set_window_title_bar_theme(self, is_dark: bool, bg_color: QColor | None = None) -> None:
        """Enable immersive dark mode and set custom caption color for the Windows title bar."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            # Immersive Dark Mode
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # Some older win10 builds use 19
            DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
            value = ctypes.c_int(1 if is_dark else 0)
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(value), ctypes.sizeof(value)
            )
            # Try 19 as fallback? Usually unnecessary on modern systems but safe.
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 
                ctypes.byref(value), ctypes.sizeof(value)
            )

            # Windows 11+ Title Bar Colors
            if bg_color:
                DWMWA_CAPTION_COLOR = 35
                DWMWA_TEXT_COLOR = 36
                
                # Background
                bg_ref = (bg_color.blue() << 16) | (bg_color.green() << 8) | bg_color.red()
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(bg_ref)),
                    ctypes.sizeof(ctypes.c_int(bg_ref))
                )
                
                # Text (Contrast)
                fg_ref = 0x00000000 if not is_dark else 0x00FFFFFF
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR,
                    ctypes.byref(ctypes.c_int(fg_ref)),
                    ctypes.sizeof(ctypes.c_int(fg_ref))
                )
        except Exception:
            pass

    def _update_native_styles(self, accent_str: str) -> None:
        """Apply neutral native surfaces and reserve accent for interaction states."""
        accent = QColor(accent_str)
        sb_bg_str = Theme.get_sidebar_bg(accent)
        sb_bg = QColor(sb_bg_str)
        scrollbar_style = self._get_native_scrollbar_style(accent)
        text = Theme.get_text_color()
        text_muted = Theme.get_text_muted()
        is_light = Theme.get_is_light()
        combo_arrow_svg = (
            (Path(__file__).with_name("web") / "icons" / "chevron-down-light.svg")
            if is_light
            else (Path(__file__).with_name("web") / "icons" / "chevron-down-dark.svg")
        ).as_posix()
        meta_switch_on_svg = (
            Path(__file__).with_name("web") / "icons" / ("black-toggle-on.svg" if is_light else "white-toggle-on.svg")
        ).as_posix()
        meta_switch_off_svg = (
            Path(__file__).with_name("web") / "icons" / ("black-toggle-off.svg" if is_light else "white-toggle-off.svg")
        ).as_posix()
        combo_bg = "#ffffff" if is_light else Theme.mix(Theme.get_control_bg(accent), "#000000", 0.12)
        combo_selected_text = Theme.mix(text, accent, 0.76)
        combo_hover_bg = Theme.mix(combo_bg, "#000000" if is_light else "#ffffff", 0.04 if is_light else 0.07)
        combo_hover_text = text if is_light else "#ffffff"
        close_hover_bg = Theme.get_btn_save_hover(accent)
        
        # Only touch the native title bar after the top-level window is visible.
        # Forcing winId() during construction can create an early transient HWND
        # on Windows, which shows up as a blank startup window before the real UI.
        if self.isVisible():
            self._set_window_title_bar_theme(not is_light, sb_bg)
        
        # Native Tooltip Style
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.update_style(accent, is_light)
        
        # Theme-aware Window Icon
        icon_path = Path(__file__).with_name("web") / "MediaLens-Logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Loading Screen
        load_fg = "rgba(0,0,0,200)" if is_light else "rgba(255,255,255,200)"
        load_bg = "rgba(0,0,0,25)" if is_light else "rgba(255,255,255,25)"
        if self.web_loading_label is not None:
            self.web_loading_label.setStyleSheet(f"color: {load_fg}; font-size: 13px;")
        if self.web_loading_bar is not None:
            self.web_loading_bar.setStyleSheet(
                f"QProgressBar{{background: {load_bg}; border-radius:"
                " 5px;}}"
                f"QProgressBar::chunk{{background: {accent_str}; border-radius: 5px;}}"
            )
        
        # Left Panel (Folders)
        self.left_panel.setStyleSheet(f"""
            QWidget {{ background-color: {sb_bg_str}; color: {text}; }}
            QTreeView {{
                background-color: {sb_bg_str};
                border: none;
                color: {text};
                show-decoration-selected: 0;
                selection-background-color: transparent;
            }}
            QTreeView::item:selected {{
                background: transparent;
            }}
            QTreeView::item:selected:active {{
                background: transparent;
            }}
            QTreeView::item:selected:!active {{
                background: transparent;
            }}
            QListWidget {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 8px;
                color: {text};
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {Theme.get_accent_soft(accent)};
                border: 1px solid {accent_str};
                color: {text};
            }}
            QListWidget::item:hover {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
            }}
            QListWidget#pinnedFoldersList {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                outline: 0;
            }}
            QListWidget#pinnedFoldersList::item {{
                padding: 0px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
                outline: 0;
            }}
            QListWidget#pinnedFoldersList::item:selected {{
                background-color: {Theme.get_accent_soft(accent)};
                border: 1px solid {accent_str};
            }}
            QListWidget#pinnedFoldersList::item:selected:active {{
                background-color: {Theme.get_accent_soft(accent)};
                border: 1px solid {accent_str};
                outline: none;
            }}
            QListWidget#pinnedFoldersList::item:selected:!active {{
                background-color: {Theme.get_accent_soft(accent)};
                border: 1px solid {accent_str};
                outline: none;
            }}
            QListWidget#pinnedFoldersList::item:hover {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
            }}
            QWidget#pinnedFolderRow, QLabel#pinnedFolderIcon, QLabel#pinnedFolderText, QLabel#pinnedFolderPin {{
                background: transparent;
                border: none;
            }}
            QLabel#pinnedFolderText {{
                color: {text};
                font-weight: normal;
            }}
            QLabel#pinnedFolderText[hidden="true"] {{
                color: {text_muted};
            }}
            QLabel#pinnedFolderText[selected="true"] {{
                font-weight: 700;
            }}
            QPushButton#foldersMenuButton {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 6px;
                color: {text};
                font-weight: 600;
                padding: 0px 6px 2px 6px;
            }}
            QPushButton#foldersMenuButton:hover {{
                background-color: {Theme.get_btn_save_hover(accent)};
                border-color: {accent_str};
            }}
            QLabel {{ color: {text}; font-weight: bold; background: transparent; }}
            {scrollbar_style}
        """)
        if hasattr(self, "pinned_folders_list"):
            self._reload_pinned_folders()
        
        # Right Panel (Tag List + Metadata)
        if hasattr(self, "right_panel_host"):
            self.right_panel_host.setStyleSheet(f"background-color: {sb_bg_str}; border-left: none;")
        if hasattr(self, "tag_list_panel"):
            self.tag_list_panel.setStyleSheet(f"""
                QWidget#tagListPanel {{
                    background-color: {sb_bg_str};
                    border-right: 1px solid {Theme.get_border(accent)};
                }}
                QLabel#tagListTitleLabel, QLabel#activeTagListNameLabel, QLabel#tagListSortLabel {{
                    color: {text};
                    font-weight: 700;
                    background: transparent;
                }}
                QLabel#tagListEmptyLabel {{
                    color: {text_muted};
                    background: transparent;
                }}
                QPushButton#tagListCloseButton {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    color: {text};
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton#tagListCloseButton:hover {{
                    background-color: {close_hover_bg};
                    color: {text};
                    border-color: {accent_str};
                }}
                QComboBox#tagListSelect, QComboBox#tagListSortSelect {{
                    background-color: {combo_bg};
                    color: {text};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 4px;
                    min-height: 34px;
                    padding: 0px 32px 0px 12px;
                }}
                QComboBox#tagListSelect:hover, QComboBox#tagListSortSelect:hover,
                QComboBox#tagListSelect:focus, QComboBox#tagListSortSelect:focus {{
                    border-color: {accent_str};
                }}
                QComboBox#tagListSelect:on, QComboBox#tagListSortSelect:on {{
                    border-color: {accent_str};
                    border-bottom-color: transparent;
                    border-radius: 4px 4px 0px 0px;
                }}
                QComboBox#tagListSelect::drop-down, QComboBox#tagListSortSelect::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 28px;
                    border: none;
                    background: transparent;
                }}
                QComboBox#tagListSelect::down-arrow, QComboBox#tagListSortSelect::down-arrow {{
                    image: url("{combo_arrow_svg}");
                    width: 12px;
                    height: 12px;
                }}
                QComboBox#tagListSelect QAbstractItemView, QComboBox#tagListSortSelect QAbstractItemView {{
                    background-color: {combo_bg};
                    color: {text};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-top: none;
                    border-radius: 0px 0px 4px 4px;
                    outline: 0;
                    selection-background-color: transparent;
                    selection-color: {combo_selected_text};
                    show-decoration-selected: 0;
                    padding: 2px 0px;
                }}
                QComboBox#tagListSelect QAbstractItemView {{
                    border: 1px solid {accent_str};
                    border-top: none;
                }}
                QListView#tagListSelectPopup, QListView#tagListSortSelectPopup {{
                    background-color: {combo_bg};
                    color: {text};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-top: none;
                    border-radius: 0px 0px 4px 4px;
                    outline: 0;
                    padding: 2px 0px;
                    show-decoration-selected: 0;
                }}
                QListView#tagListSelectPopup {{
                    border-color: {accent_str};
                    border-top: none;
                }}
                QListView#tagListSelectPopup::item, QListView#tagListSortSelectPopup::item {{
                    padding: 5px 12px;
                    border: none;
                    margin: 0px;
                    min-height: 0px;
                }}
                QListView#tagListSelectPopup::item:hover, QListView#tagListSortSelectPopup::item:hover {{
                    background-color: {combo_hover_bg};
                    color: {combo_hover_text};
                }}
                QListView#tagListSelectPopup::item:selected, QListView#tagListSortSelectPopup::item:selected {{
                    background-color: {combo_bg};
                    color: {combo_selected_text};
                    border: none;
                    font-weight: 700;
                }}
                QPushButton#btnCreateTagList, QPushButton#btnAddTagListTag, QPushButton#btnImportTagListTags, QPushButton#btnClearTagScopeFilter {{
                    background-color: {Theme.get_btn_save_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton#btnCreateTagList:hover, QPushButton#btnAddTagListTag:hover, QPushButton#btnImportTagListTags:hover, QPushButton#btnClearTagScopeFilter:hover {{
                    background-color: {Theme.get_btn_save_hover(accent)};
                    color: {"#000" if is_light else "#fff"};
                    border-color: {accent_str};
                }}
                QListWidget#tagListRows {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 8px;
                    color: {text};
                    padding: 4px;
                }}
                QListWidget#tagListRows::item {{
                    border: none;
                    padding: 2px;
                }}
                QListWidget#tagListRows::item:selected {{
                    background-color: {Theme.get_accent_soft(accent)};
                    border: 1px solid {accent_str};
                    border-radius: 8px;
                }}
                QWidget#tagListTagRow {{
                    background: transparent;
                }}
                {scrollbar_style}
            """)
            self._apply_tag_list_theme()

        # Metadata - Mirroring Left Panel Background precisely
        self.right_panel.setStyleSheet(f"background-color: {sb_bg_str}; border-left: none;")
        right_palette = self.right_panel.palette()
        right_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg_str))
        right_palette.setColor(QPalette.ColorRole.Base, QColor(sb_bg_str))
        self.right_panel.setAutoFillBackground(True)
        self.right_panel.setPalette(right_palette)
        if hasattr(self, "bottom_panel"):
            self.bottom_panel.setStyleSheet(f"""
                QWidget#bottomPanel {{
                    background-color: {sb_bg_str};
                    border-top: 1px solid {Theme.get_border(accent)};
                }}
                QLabel#bottomPanelHeader {{
                    color: {text};
                    font-weight: bold;
                    background: transparent;
                    font-size: 14px;
                    qproperty-alignment: AlignCenter;
                }}
                QWidget#comparePanel {{
                    background: transparent;
                }}
                QFrame#compareSlotCard {{
                    background-color: transparent;
                    border: none;
                    border-radius: 10px;
                }}
                QFrame#compareSlotCard[empty="true"] {{
                    border: none;
                }}
                QLabel#compareSlotName {{
                    color: {text};
                    font-weight: 600;
                }}
                QLabel#compareSlotThumb {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 10px;
                    color: {text_muted};
                    padding: 12px;
                    margin-top: 2px;
                    margin-bottom: 2px;
                }}
                QLabel#compareSlotMeta {{
                    color: {text_muted};
                }}
                QLabel#compareSlotReasons {{
                    color: {Theme.mix(QColor(text), accent, 0.7)};
                    font-weight: 700;
                }}
                QLabel#compareSlotBest {{
                    color: {Theme.mix(QColor(text), accent, 0.78)};
                    font-weight: 700;
                }}
                QWidget#compareRevealViewer {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 10px;
                }}
                QCheckBox {{
                    color: {text_muted};
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                }}
                QPushButton {{
                    background-color: {Theme.get_input_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
                QPushButton:hover {{
                    border-color: {accent.name()};
                }}
                QPushButton#bottomPanelGroupNavButton {{
                    min-height: 22px;
                    max-height: 22px;
                    padding: 0px 12px;
                }}
                {scrollbar_style}
            """)
            if hasattr(self, "bottom_panel_header"):
                self.bottom_panel_header.setStyleSheet(
                    f"color: {text}; font-weight: 700; font-size: 14px; background: transparent;"
                )
            if hasattr(self, "compare_panel"):
                self._apply_compare_panel_theme(accent_str)
        
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ background-color: {sb_bg_str}; border: none; }}
            QWidget#rightPanelScrollContainer {{ background-color: {sb_bg_str}; }}
            {scrollbar_style}
        """)
        if hasattr(self, "bulk_scroll_area"):
            self.bulk_scroll_area.setStyleSheet(f"""
                QScrollArea {{ background-color: {sb_bg_str}; border: none; }}
                QWidget#bulkTagEditorScrollContainer {{ background-color: {sb_bg_str}; }}
                {scrollbar_style}
            """)
        try:
            viewport = self.scroll_area.viewport()
            viewport.setStyleSheet(f"background-color: {sb_bg_str};")
            viewport_palette = viewport.palette()
            viewport_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg_str))
            viewport_palette.setColor(QPalette.ColorRole.Base, QColor(sb_bg_str))
            viewport.setAutoFillBackground(True)
            viewport.setPalette(viewport_palette)
            viewport.update()
            viewport.repaint()
        except Exception:
            pass
        try:
            if hasattr(self, "bulk_scroll_area"):
                bulk_viewport = self.bulk_scroll_area.viewport()
                bulk_viewport.setStyleSheet(f"background-color: {sb_bg_str};")
                bulk_viewport_palette = bulk_viewport.palette()
                bulk_viewport_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg_str))
                bulk_viewport_palette.setColor(QPalette.ColorRole.Base, QColor(sb_bg_str))
                bulk_viewport.setAutoFillBackground(True)
                bulk_viewport.setPalette(bulk_viewport_palette)
                bulk_viewport.update()
                bulk_viewport.repaint()
        except Exception:
            pass

        self.scroll_container.setStyleSheet(f"""
            QWidget#rightPanelScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
            QLabel {{
                color: {text};
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QLabel[detailCaption="true"] {{
                font-weight: 700;
            }}
            QLabel#previewHeaderLabel, QLabel#detailsHeaderLabel {{
                font-weight: 800;
                font-size: 14px;
            }}
            QLabel#metaGroupLabel {{
                font-weight: 800;
                font-size: 14px;
                margin-top: 12px;
                margin-bottom: 4px;
            }}
            QLabel#metaOriginalFileDateLabel, QLabel#metaFileCreatedDateLabel, QLabel#metaFileModifiedDateLabel {{
                color: {text};
                padding: 4px;
                min-height: 18px;
            }}
            QLabel#metaSwitchValueLabel {{
                color: {text};
                font-weight: 600;
                padding: 2px 0px;
            }}
            QLabel#metaFieldNoteLabel {{
                color: {text_muted};
                font-size: 11px;
                padding: 0px 0px 2px 0px;
            }}
            QWidget#metaSwitchRow {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QCheckBox#metaSwitch {{
                background: transparent;
                spacing: 0px;
                padding: 0px;
                min-width: 44px;
                max-width: 44px;
                min-height: 24px;
                max-height: 24px;
            }}
            QCheckBox#metaSwitch::indicator {{
                width: 44px;
                height: 24px;
                border: none;
                background: transparent;
                image: url('{meta_switch_off_svg}');
            }}
            QCheckBox#metaSwitch::indicator:hover {{
                background: transparent;
            }}
            QCheckBox#metaSwitch::indicator:checked {{
                background: transparent;
                image: url('{meta_switch_on_svg}');
            }}
            QLabel#previewImageLabel {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 8px;
                padding: 6px;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {Theme.get_input_bg(accent)};
                border: 1px solid {Theme.get_input_border(accent)};
                border-radius: 4px;
                padding: 4px;
                color: {text};
            }}
            QPlainTextEdit#metaStatusLabel {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                color: {text_muted};
                font-weight: 500;
                selection-background-color: {Theme.get_accent_soft(accent)};
            }}
            QLabel#localAiProgressLabel {{
                color: {text_muted};
                background: transparent;
                border: none;
                padding: 2px 0px 6px 0px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPlainTextEdit#localAiErrorText {{
                color: {text_muted};
                background: transparent;
                border: none;
                padding: 2px 0px 6px 0px;
                font-size: 11px;
                font-weight: 500;
                selection-background-color: {Theme.get_accent_soft(accent)};
            }}
            QPushButton#btnClosePreview {{
                background-color: {Theme.get_control_bg(accent)};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                color: {text};
                padding: 0px;
                margin: 0px;
            }}
            
            QPushButton#btnShowPreviewInline {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
                color: {text};
                font-size: 14px;
                font-weight: bold;
            }}

            QPushButton#btnClosePreview:hover {{
                background-color: {close_hover_bg};
                color: {text};
                border-color: {accent_str};
            }}
            QPushButton#btnShowPreviewInline:hover {{
                background-color: {Theme.get_control_bg(accent)};
                color: {text};
            }}
            QPushButton#btnPreviewOverlayPlay {{
                background-color: {"rgba(255, 255, 255, 115)" if is_light else "rgba(0, 0, 0, 115)"};
                border: 1px solid {"white" if is_light else "black"};
                border-radius: 26px;
                padding-left: 2px;
            }}
            QPushButton#btnPreviewOverlayPlay:hover {{
                background-color: {"rgba(255, 255, 255, 115)" if is_light else "rgba(0, 0, 0, 115)"};
            }}
            QPushButton#btnPreviewOverlayPlay:pressed {{
                background-color: {"rgba(255, 255, 255, 115)" if is_light else "rgba(0, 0, 0, 115)"};
            }}
            QPushButton#btnSaveMeta, QPushButton#btnUseOcr, QPushButton#btnGenerateTags, QPushButton#btnGenerateDescription, QPushButton#btnImportExif, QPushButton#btnMergeHiddenMeta, QPushButton#btnSaveToExif, QPushButton#btnOpenTagList, QPushButton#metaEmptySelectAllButton {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#btnSaveMeta:hover, QPushButton#btnUseOcr:hover, QPushButton#btnGenerateTags:hover, QPushButton#btnGenerateDescription:hover, QPushButton#btnImportExif:hover, QPushButton#btnMergeHiddenMeta:hover, QPushButton#btnSaveToExif:hover, QPushButton#btnOpenTagList:hover, QPushButton#metaEmptySelectAllButton:hover {{
                background-color: {Theme.get_btn_save_hover(accent)};
                color: {"#000" if is_light else "#fff"};
                border-color: {accent_str};
            }}
            QPushButton#btnClearBulkTags {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#btnClearBulkTags:hover {{
                background-color: {Theme.get_btn_save_hover(accent)};
                color: {"#000" if is_light else "#fff"};
                border-color: {accent_str};
            }}
        """)
        if hasattr(self, "bulk_scroll_container"):
            bulk_editor_style = f"""
                QWidget#bulkTagEditorPanel {{
                    background-color: {sb_bg_str};
                    color: {text};
                }}
                QWidget#bulkEditorModeRow {{
                    background: transparent;
                }}
                QWidget#bulkTagEditorScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
                QWidget#bulkCaptionEditorScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
                QLabel {{
                    color: {text};
                    background: transparent;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }}
                QLabel#bulkTagEditorHeaderLabel {{
                    color: {text};
                    font-weight: 700;
                    font-size: 16px;
                }}
                QPushButton#bulkEditorModeButton {{
                    background-color: {Theme.get_btn_save_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton#bulkEditorModeButton:checked {{
                    background-color: {Theme.mix(Theme.get_btn_save_bg(accent), accent, 0.24)};
                    border-color: {accent_str};
                    color: {"#000" if is_light else "#fff"};
                }}
                QPushButton#bulkEditorModeButton:hover {{
                    background-color: {Theme.get_btn_save_hover(accent)};
                    color: {"#000" if is_light else "#fff"};
                    border-color: {accent_str};
                }}
                QLabel#bulkTagEditorTagsLabel, QLabel#bulkTagEditorSelectedFilesLabel {{
                    color: {text};
                    font-weight: 700;
                }}
                QLabel#bulkTagEditorSelectionLabel {{
                    color: {text_muted};
                    font-weight: 500;
                }}
                QToolButton#bulkTagEditorSectionToggle {{
                    background: transparent;
                    border: none;
                    color: {text};
                    font-weight: 700;
                    padding: 2px 0px;
                    text-align: left;
                }}
                QToolButton#bulkTagEditorSectionToggle:hover {{
                    color: {Theme.mix(text, accent, 0.76)};
                }}
                QPlainTextEdit#metaStatusLabel, QPlainTextEdit#bulkTagEditorStatusLabel {{
                    background: transparent;
                    border: none;
                    color: {text_muted};
                    font-weight: 500;
                    padding: 0px;
                    margin: 0px;
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QLineEdit#bulkTagEditorTagsEdit, QPlainTextEdit#bulkSelectedFileTagsEdit, QPlainTextEdit#bulkTagEditorCommonTagsText, QPlainTextEdit#bulkTagEditorUncommonTagsText {{
                    background-color: {Theme.mix(Theme.get_input_bg(accent), QColor("#ffffff" if is_light else "#000000"), 0.1)};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 4px;
                    padding: 4px;
                    color: {text};
                }}
                QPlainTextEdit#bulkSelectedFileTagsEdit {{
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QListWidget#bulkSelectedFilesList {{
                    background-color: {Theme.mix(Theme.get_control_bg(accent), QColor("#000000" if is_light else "#ffffff"), 0.06)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 8px;
                    padding: 6px;
                }}
                QListWidget#bulkSelectedFilesList::item {{
                    background: transparent;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                    outline: 0;
                }}
                QListWidget#bulkSelectedFilesList::item:selected {{
                    background: transparent;
                    border: none;
                }}
                QWidget#bulkSelectedFileRow {{
                    background-color: {Theme.mix(Theme.get_control_bg(accent), QColor("#ffffff" if is_light else "#000000"), 0.2)};
                    border: 1px solid {Theme.mix(Theme.get_border(accent), accent, 0.42)};
                    border-radius: 8px;
                }}
                QLabel#bulkSelectedFileName {{
                    color: {text};
                    font-weight: 700;
                }}
                QLabel#bulkSelectedFileThumb {{
                    background-color: {Theme.mix(Theme.get_input_bg(accent), QColor("#ffffff" if is_light else "#000000"), 0.16)};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 6px;
                }}
                QPlainTextEdit#bulkTagEditorCommonTagsText, QPlainTextEdit#bulkTagEditorUncommonTagsText {{
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QPushButton#bulkBtnSelectAllGallery, QPushButton#bulkBtnClearTags, QPushButton#bulkBtnRunLocalAI, QPushButton#bulkBtnSaveMeta, QPushButton#bulkBtnSaveToExif, QPushButton#bulkBtnOpenTagList {{
                    background-color: {Theme.get_btn_save_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton#bulkBtnOpenTagList {{
                    font-weight: 700;
                }}
                QPushButton#bulkBtnSelectAllGallery:hover, QPushButton#bulkBtnClearTags:hover, QPushButton#bulkBtnRunLocalAI:hover, QPushButton#bulkBtnSaveMeta:hover, QPushButton#bulkBtnSaveToExif:hover, QPushButton#bulkBtnOpenTagList:hover {{
                    background-color: {Theme.get_btn_save_hover(accent)};
                    color: {"#000" if is_light else "#fff"};
                    border-color: {accent_str};
                }}
                {scrollbar_style}
            """
            if hasattr(self, "bulk_editor_panel"):
                self.bulk_editor_panel.setStyleSheet(bulk_editor_style)
            self.bulk_scroll_container.setStyleSheet(bulk_editor_style)
            if hasattr(self, "bulk_caption_scroll_container"):
                self.bulk_caption_scroll_container.setStyleSheet(bulk_editor_style)
        self._update_preview_play_button_icon()
        self._apply_tag_list_theme()
        
        self._update_app_style(accent)

    def _add_sep(self, obj_name: str) -> NativeSeparator:
        """Create a 1 physical-pixel robust separator widget."""
        sep = NativeSeparator()
        sep.setObjectName(obj_name)
        return sep


    def showEvent(self, event) -> None:
        """Trigger native style update when window actually becomes visible to ensure valid winId for DWM."""
        super().showEvent(event)
        try:
            accent = getattr(self, "_current_accent", Theme.ACCENT_DEFAULT)
            self._update_native_styles(accent)
        except Exception:
            pass
        try:
            if self._pending_tree_sync_path:
                QTimer.singleShot(0, self._apply_pending_tree_sync)
        except Exception:
            pass

    def _update_app_style(self, accent: QColor) -> None:
        """Update global application styles like tinted native menus."""
        sb_bg = Theme.get_sidebar_bg(accent)
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        tooltip_bg = Theme.get_bg(accent)
        tooltip_border = Theme.get_input_border(accent)
        highlight_bg = Theme.get_accent_soft(accent)
        menu_qss = f"""
            QMenuBar {{
                background-color: {sb_bg};
                color: {text};
                border-bottom: 1px solid {border};
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 4px 10px;
            }}
            QMenuBar::item:selected {{
                background: {highlight_bg};
            }}
            QMenu {{
                background-color: {sb_bg};
                color: {text};
                border: 1px solid {border};
                padding: 4px 0;
            }}
            QMenu::item {{
                padding: 4px 24px 4px 14px;
            }}
            QMenu::item:selected {{
                background-color: {highlight_bg};
            }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 0;
            }}
            QWidget#menuBarControls {{
                background: transparent;
            }}
            QPushButton#menuBarIconButton, QPushButton#menuBarSettingsButton {{
                min-width: 26px;
                max-width: 26px;
                min-height: 24px;
                max-height: 24px;
                padding: 0;
                border: 1px solid {border};
                border-radius: 6px;
                background-color: {Theme.get_control_bg(accent)};
                color: {text};
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton#menuBarIconButton:hover, QPushButton#menuBarSettingsButton:hover {{
                background-color: {highlight_bg};
                border-color: {accent.name()};
            }}
            QToolTip {{
                background-color: {tooltip_bg};
                color: {text};
                border: 1px solid {tooltip_border};
                padding: 4px 6px;
            }}
        """
        QApplication.instance().setStyleSheet(menu_qss)
        tooltip_palette = QApplication.instance().palette()
        tooltip_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tooltip_bg))
        tooltip_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(text))
        QToolTip.setPalette(tooltip_palette)
        try:
            menu_bar = self.menuBar()
            if menu_bar is not None:
                menu_bar.setStyleSheet(menu_qss)
                menu_bar_palette = menu_bar.palette()
                menu_bar_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg))
                menu_bar_palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
                menu_bar_palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
                menu_bar.setAutoFillBackground(True)
                menu_bar.setPalette(menu_bar_palette)
                menu_bar.style().unpolish(menu_bar)
                menu_bar.style().polish(menu_bar)
                menu_bar.update()
                menu_bar.repaint()
                corner = menu_bar.cornerWidget(Qt.Corner.TopRightCorner)
                if corner is not None:
                    corner.setStyleSheet(menu_qss)
                    corner.update()
            for menu in self.findChildren(QMenu):
                menu.setStyleSheet(menu_qss)
                menu_palette = menu.palette()
                menu_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg))
                menu_palette.setColor(QPalette.ColorRole.Base, QColor(sb_bg))
                menu_palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
                menu_palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
                menu.setPalette(menu_palette)
                menu.style().unpolish(menu)
                menu.style().polish(menu)
                menu.update()
                menu.repaint()
        except Exception:
            pass
        self._sync_close_button_icons()
        self._apply_preview_image_label_style()
        self._sync_menu_bar_controls()

    def _web_header_height(self) -> int:
        return 112 if bool(self.bridge.settings.value("ui/show_top_panel", True, type=bool)) else 0

    def _get_native_scrollbar_style(self, accent: QColor) -> str:
        """Generate neutral native scrollbars with accent reserved for content states."""
        track = Theme.get_scrollbar_track(accent)
        is_light = Theme.get_is_light()
        
        # We use physical SVG files for maximum compatibility with Qt's QSS engine,
        # which often fails to render SVG data URIs.
        base_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "scrollbar_arrows").replace("\\", "/")
        mode = "light" if is_light else "dark"
        
        up_path = f"{base_svg_path}/{mode}_up.svg"
        dn_path = f"{base_svg_path}/{mode}_down.svg"
        lt_path = f"{base_svg_path}/{mode}_left.svg"
        rt_path = f"{base_svg_path}/{mode}_right.svg"

        thumb_bg = Theme.get_scrollbar_thumb(accent)
        thumb_hover_bg = Theme.get_scrollbar_thumb_hover(accent)
        
        return f"""
            QScrollBar:vertical {{
                background: {track};
                width: 12px;
                margin: 12px 0 12px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {thumb_bg};
                min-height: 20px;
                border-radius: 10px;
                border: 2px solid {track};
            }}
            QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{
                background: {thumb_hover_bg};
            }}
            QScrollBar::add-line:vertical {{
                background: {track};
                height: 12px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:vertical {{
                background: {track};
                height: 12px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }}
            QScrollBar::up-arrow:vertical {{
                image: url("{up_path}");
                width: 8px;
                height: 8px;
            }}
            QScrollBar::down-arrow:vertical {{
                image: url("{dn_path}");
                width: 8px;
                height: 8px;
            }}
            
            QScrollBar:horizontal {{
                background: {track};
                height: 12px;
                margin: 0 12px 0 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: {thumb_bg};
                min-width: 20px;
                border-radius: 10px;
                border: 2px solid {track};
            }}
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:horizontal:pressed {{
                background: {thumb_hover_bg};
            }}
            QScrollBar::add-line:horizontal {{
                background: {track};
                width: 12px;
                subcontrol-position: right;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:horizontal {{
                background: {track};
                width: 12px;
                subcontrol-position: left;
                subcontrol-origin: margin;
            }}
            QScrollBar::left-arrow:horizontal {{
                image: url("{lt_path}");
                width: 8px;
                height: 8px;
            }}
            QScrollBar::right-arrow:horizontal {{
                image: url("{rt_path}");
                width: 8px;
                height: 8px;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: none;
            }}
        """

    def _on_video_prev(self) -> None:
        try:
            self.web.page().runJavaScript("try{ window.lightboxPrev && window.lightboxPrev(); }catch(e){}")
        except Exception:
            pass

    def _apply_compare_panel_theme(self, accent_color: str) -> None:
        if not hasattr(self, "compare_panel") or not hasattr(self, "bottom_panel_header"):
            return
        accent = QColor(accent_color)
        is_light = Theme.get_is_light()
        text = Theme.get_text_color()
        text_muted = Theme.get_text_muted()
        compare_accent = Theme.mix(text, accent, 0.76)
        thumb_bg = Theme.get_control_bg(accent)
        thumb_border = Theme.get_border(accent)
        btn_border = Theme.get_input_border(accent)
        close_btn_bg = "#eceef2" if is_light else "#2f2f2f"
        close_btn_hover_bg = Theme.get_btn_save_hover(accent)
        close_btn_text = text if is_light else "#f2f2f2"
        close_btn_hover_text = text if is_light else "#ffffff"

        header_font = QFont(self.bottom_panel_header.font())
        header_font.setBold(True)
        self.bottom_panel_header.setFont(header_font)
        header_palette = QPalette(self.bottom_panel_header.palette())
        header_palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
        self.bottom_panel_header.setPalette(header_palette)
        self.bottom_panel_close_btn.setStyleSheet(
            f"""
            QPushButton#bottomPanelCloseButton {{
                background-color: {close_btn_bg};
                color: {close_btn_text};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 0px;
            }}
            QPushButton#bottomPanelCloseButton:hover {{
                background-color: {close_btn_hover_bg};
                color: {close_btn_hover_text};
                border-color: {accent_color};
            }}
            """
        )

        self.compare_panel.apply_theme_styles(text, text_muted, compare_accent, accent_color, thumb_bg, thumb_border)
        try:
            self.bottom_panel.style().unpolish(self.bottom_panel)
            self.bottom_panel.style().polish(self.bottom_panel)
            self.bottom_panel.update()
            self.bottom_panel_close_btn.style().unpolish(self.bottom_panel_close_btn)
            self.bottom_panel_close_btn.style().polish(self.bottom_panel_close_btn)
            self.bottom_panel_close_btn.update()
            self.compare_panel.style().unpolish(self.compare_panel)
            self.compare_panel.style().polish(self.compare_panel)
            self.compare_panel.update()
        except Exception:
            pass

    def _on_video_next(self) -> None:
        try:
            self.web.page().runJavaScript("try{ window.lightboxNext && window.lightboxNext(); }catch(e){}")
        except Exception:
            pass

    def _set_web_loading(self, on: bool) -> None:
        try:
            if self.web is None or self.web_loading is None:
                return
            if on:
                self._web_loading_shown_ms = int(__import__("time").time() * 1000)
                self.web_loading.setGeometry(self.web.rect())
                self.web_loading.setVisible(True)
                self.web_loading.raise_()
                if self.video_overlay is not None and self.video_overlay.isVisible():
                    self.video_overlay.raise_()
                return

            # off: enforce minimum display time to avoid flashing
            now = int(__import__("time").time() * 1000)
            shown = self._web_loading_shown_ms or now
            remaining = self._web_loading_min_ms - (now - shown)
            if remaining > 0:
                from PySide6.QtCore import QTimer

                QTimer.singleShot(int(remaining), lambda: self._set_web_loading(False))
                return

            self.web_loading.setVisible(False)
        except Exception:
            pass

    def _on_web_load_progress(self, pct: int) -> None:
        try:
            if self.web_loading_bar is not None:
                self.web_loading_bar.setValue(int(pct))
        except Exception:
            pass

    def _toggle_panel_setting(self, qkey: str) -> None:
        try:
            cur = bool(self.bridge.settings.value(qkey, True, type=bool))
            new = not cur
            if not new:
                if qkey == "ui/show_bottom_panel":
                    self._save_bottom_panel_height()
                else:
                    self._save_main_panel_widths()
            self.bridge.settings.setValue(qkey, new)
            self.bridge.uiFlagChanged.emit(qkey.replace("/", "."), new)
            if qkey == "ui/show_bottom_panel":
                self.bridge.compareStateChanged.emit(self.bridge.get_compare_state())
        except Exception:
            pass

    def _save_splitter_state(self) -> None:
        try:
            self._save_main_panel_widths()
            self._save_bottom_panel_height()
            self._save_tag_list_panel_width()
            if hasattr(self, "left_sections_splitter"):
                self.bridge.settings.setValue("ui/left_sections_splitter_state_v3", self.left_sections_splitter.saveState())
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self._save_splitter_state()
        try:
            self.bridge.cancel_local_ai_captioning()
        except Exception:
            pass
        super().closeEvent(event)

    def open_settings(self) -> None:
        try:
            if self._settings_dialog is None:
                self._settings_dialog = SettingsDialog(self)
            self._settings_dialog.open_dialog()
        except Exception:
            pass

    def open_local_ai_setup(self, focus_kind: str = "", show_advanced: bool = False) -> None:
        try:
            reopen_settings = bool(self._settings_dialog is not None and self._settings_dialog.isVisible())
            if self._local_ai_setup_dialog is None:
                self._local_ai_setup_dialog = LocalAiSetupDialog(self, focus_kind)
                self._local_ai_setup_dialog.finished.connect(self._on_local_ai_setup_finished)
            else:
                self._local_ai_setup_dialog.focus_kind = str(focus_kind or "")
                self._local_ai_setup_dialog.refresh_statuses()
            self._reopen_settings_after_local_ai_setup = reopen_settings
            if reopen_settings and self._settings_dialog is not None:
                self._settings_dialog.hide()
            if hasattr(self._local_ai_setup_dialog, "_set_advanced_visible"):
                self._local_ai_setup_dialog._set_advanced_visible(bool(show_advanced))
            self._local_ai_setup_dialog.show()
            self._local_ai_setup_dialog.raise_()
            self._local_ai_setup_dialog.activateWindow()
        except Exception as exc:
            try:
                self.bridge._log(f"Failed to open local AI setup dialog: {exc}")
            except Exception:
                pass

    def _on_local_ai_setup_finished(self, _result: int) -> None:
        try:
            if bool(getattr(self, "_reopen_settings_after_local_ai_setup", False)):
                self._reopen_settings_after_local_ai_setup = False
                if self._settings_dialog is None:
                    self._settings_dialog = SettingsDialog(self)
                self._settings_dialog.open_ai_page()
        except Exception:
            pass

    def maybe_show_local_ai_setup_onboarding(self) -> None:
        key = "ai_caption/setup_dialog_seen_version"
        seen_version = str(self.bridge.settings.value(key, "", type=str) or "")
        if seen_version == __version__:
            return
        self.bridge.settings.setValue(key, __version__)
        if self.bridge.settings.value("ai_caption/setup_dialog_skip_startup", False, type=bool):
            return
        if self._all_local_ai_models_installed():
            return
        self.open_local_ai_setup()

    def _all_local_ai_models_installed(self) -> bool:
        if not hasattr(self.bridge, "get_local_ai_model_status"):
            return False
        try:
            from app.mediamanager.ai_captioning.model_registry import MODEL_SPECS

            seen: set[str] = set()
            for spec in MODEL_SPECS:
                if spec.settings_key in seen:
                    continue
                seen.add(spec.settings_key)
                status = dict(self.bridge.get_local_ai_model_status(spec.id, spec.kind) or {})
                if status.get("state") != "installed":
                    return False
            return bool(seen)
        except Exception:
            return False

    def _selected_local_ai_model_status(self, kind: str) -> dict:
        if not hasattr(self.bridge, "get_local_ai_model_status"):
            return {"state": "error", "message": "Local AI setup is not available in this build."}
        try:
            from app.mediamanager.ai_captioning.local_captioning import CAPTION_MODEL_ID, TAG_MODEL_ID

            setting_key = "ai_caption/tag_model_id" if kind == "tagger" else "ai_caption/caption_model_id"
            default_model_id = TAG_MODEL_ID if kind == "tagger" else CAPTION_MODEL_ID
            model_id = str(self.bridge.settings.value(setting_key, default_model_id, type=str) or default_model_id)
            return dict(self.bridge.get_local_ai_model_status(model_id, kind) or {})
        except Exception as exc:
            return {"state": "error", "message": str(exc) or "Could not read local AI model status."}

    def _ensure_local_ai_model_ready(self, kind: str) -> bool:
        status = self._selected_local_ai_model_status(kind)
        if bool(status.get("installed")) and str(status.get("state") or "") == "installed":
            return True
        label = str(status.get("label") or "selected local AI model")
        state = str(status.get("state") or "").strip()
        if state == "installing":
            message = f"{label} is still installing. Check Local AI Models for progress."
        else:
            message = f"{label} needs to be installed before this can run."
        self.meta_status_lbl.setText(message)
        self.open_local_ai_setup(kind)
        return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize:
            watched_viewports = {
                getattr(getattr(self, "scroll_area", None), "viewport", lambda: None)(),
                getattr(getattr(self, "bulk_scroll_area", None), "viewport", lambda: None)(),
            }
            if watched in watched_viewports:
                self._queue_sidebar_panel_width_sync()
        if watched is getattr(self, "btn_preview_overlay_play", None):
            if event.type() == QEvent.Type.Enter:
                self._set_preview_play_button_hovered(True)
            elif event.type() in {QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease}:
                self._set_preview_play_button_hovered(False)
        if event.type() == QEvent.Type.MouseButtonDblClick:
            preview_widgets = {
                getattr(self, "preview_image_lbl", None),
                getattr(self, "sidebar_video_overlay", None),
                getattr(getattr(self, "sidebar_video_overlay", None), "video_view", None),
            }
            if watched in preview_widgets:
                if hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
                    if self._selected_video_path():
                        self._open_selected_video_lightbox()
                        return True
        if event.type() == QEvent.Type.MouseButtonPress:
            # 1. Ignore ALL mouse buttons if a native popup/menu is active.
            # This protects against "Select All Files in Folder" from the tree context menu.
            if QApplication.activePopupWidget() is not None:
                return False

            # 2. Ignore right-clicks for deselection logic (prevents context menu bugs)
            if hasattr(event, "button") and event.button() == Qt.MouseButton.RightButton:
                return False

            # 3. Ignore clicks on menus themselves
            if isinstance(watched, QMenu):
                return False

            # Use a more robust geometric check instead of recursive object parent lookup.
            # This is safer and avoids potential crashes in transient widget states.
            from PySide6.QtGui import QCursor
            rel_pos = self.web.mapFromGlobal(QCursor.pos())
            is_web = self.web.rect().contains(rel_pos)
            
            if not is_web:
                # ONLY dismiss menus if the click is outside the web area.
                self._dismiss_web_menus()
                
                # Deselect web items, UNLESS the click was in the full right-side host
                # (Details, Bulk Tag Editor, or Tag List).
                is_right_panel = False
                if hasattr(self, "right_panel_host") and self.right_panel_host.isVisible():
                    rp_pos = self.right_panel_host.mapFromGlobal(QCursor.pos())
                    is_right_panel = self.right_panel_host.rect().contains(rp_pos)

                is_bottom_panel = False
                if hasattr(self, "bottom_panel") and self.bottom_panel.isVisible():
                    bp_pos = self.bottom_panel.mapFromGlobal(QCursor.pos())
                    is_bottom_panel = self.bottom_panel.rect().contains(bp_pos)

                if not is_right_panel and not is_bottom_panel:
                    # Double check: is a popup active? (Already checked above, but keep for safety)
                    if QApplication.activePopupWidget() is None:
                        self._deselect_web_items()
                    
        return False # Accept the event and let others handle it

    def _dismiss_web_menus(self) -> None:
        """Tell the web gallery to hide its custom context menu."""
        try:
            self.web.page().runJavaScript("window.hideCtx && window.hideCtx();")
        except Exception:
            pass

    @staticmethod
    def _make_detail_label_copyable(widget: QLabel) -> None:
        widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        widget.setCursor(Qt.CursorShape.IBeamCursor)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    @staticmethod
    def _configure_progress_status_label(widget: QLabel) -> None:
        widget.setWordWrap(True)
        widget.setIndent(0)
        widget.setMargin(0)
        widget.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    @staticmethod
    def _configure_local_ai_error_widget(widget: QPlainTextEdit) -> None:
        widget.setReadOnly(True)
        widget.setUndoRedoEnabled(False)
        widget.setFrameShape(QFrame.Shape.NoFrame)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        widget.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        widget.setMaximumHeight(88)
        widget.setMinimumHeight(24)
        widget.setCursor(Qt.CursorShape.IBeamCursor)
        widget.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    @staticmethod
    def _configure_status_text_widget(widget: QPlainTextEdit) -> None:
        widget.setReadOnly(True)
        widget.setUndoRedoEnabled(False)
        widget.setFrameShape(QFrame.Shape.NoFrame)
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        widget.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        widget.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        widget.setMaximumHeight(72)
        widget.setMinimumHeight(40)
        widget.setCursor(Qt.CursorShape.IBeamCursor)
        widget.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    def _deselect_web_items(self) -> None:
        """Tell the web gallery to deselect any currently selected media items."""
        try:
            self.web.page().runJavaScript("window.deselectAll && window.deselectAll();")
        except Exception:
            pass

    def toggle_devtools(self) -> None:
        if self._devtools is None:
            self._devtools = QWebEngineView()
            self._devtools.setWindowTitle("MediaLens DevTools")
            self._devtools.resize(1100, 700)
            self.web.page().setDevToolsPage(self._devtools.page())
            self._devtools.show()
        else:
            self._devtools.close()
            self._devtools = None

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_sidebar_panel_widths()
        # Keep overlays pinned to the web view.
        if self.web is not None and self.web_loading is not None:
            self.web_loading.setGeometry(self.web.rect())
            if self.web_loading.isVisible():
                self.web_loading.raise_()

        if self.web is not None and self.video_overlay is not None and self.video_overlay.isVisible():
            # In inplace mode, the geometry is set by JS, so we don't want to reset it here.
            # Only reset if it's in full overlay mode.
            if not self.video_overlay.is_inplace_mode():
                self.video_overlay.setGeometry(self.web.rect())
            self.video_overlay.raise_()
        if hasattr(self, "preview_image_lbl"):
            self._update_preview_display()
        self._position_sidebar_preview_play_button()
        self._schedule_gallery_container_relayout(120)

    def about(self) -> None:
        st = self.bridge.get_tools_status()
        ff = "âœ“" if st.get("ffmpeg") else "Ã—"
        fp = "âœ“" if st.get("ffprobe") else "Ã—"
        
        try:
            from PySide6.QtMultimedia import QMediaFormat
            backend = "Qt6 Default (FFmpeg)"
        except ImportError:
            backend = "Unknown"

        info = (
            "# MediaLens\n\n"
            f"**Version**: {__version__}\n\n"
            "**Author**: Glen Bland\n\n"
            "A premium Windows native media manager built with PySide6.\n\n"
            "### System Diagnostics\n"
            f"- **Platform**: {sys.platform}\n"
            f"- **Multimedia**: {backend}\n"
            f"- **ffmpeg**: {ff} ({st.get('ffmpeg_path', 'not found')})\n"
            f"- **ffprobe**: {fp} ({st.get('ffprobe_path', 'not found')})\n"
            f"- **Thumbnails**: {st.get('thumb_dir')}"
        )

        self._show_themed_dialog("About MediaLens", info, is_markdown=True)

    def _show_markdown_dialog(self, title: str, file_name: str) -> None:
        """Helper to show a markdown file in a scrollable dialog."""
        try:
            content = self._read_markdown_file(file_name)
            if content is None:
                QMessageBox.warning(self, title, f"File not found: {file_name}")
                return
            self._show_themed_dialog(title, content, is_markdown=True)
        except Exception as e:
            QMessageBox.critical(self, title, f"Error loading {file_name}: {e}")

    def _read_markdown_file(self, file_name: str) -> str | None:
        """Read a bundled markdown asset from dev or packaged builds."""
        if getattr(sys, 'frozen', False):
            path = Path(sys._MEIPASS) / file_name
        else:
            candidates = [
                Path(__file__).parents[2] / file_name,
                Path(__file__).parent / file_name,
            ]
            path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def _show_themed_dialog(self, title: str, content: str, is_markdown: bool = False) -> None:
        """Helper to show content in a scrollable, themed dialog."""
        accent_q = QColor(self._current_accent)
        bg = Theme.get_bg(accent_q)
        content_bg = Theme.get_control_bg(accent_q)
        fg = Theme.get_text_color()
        border = Theme.get_border(accent_q)
        btn_bg = Theme.get_btn_save_bg(accent_q)
        btn_hover = Theme.get_btn_save_hover(accent_q)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(700, 600)
        
        # Apply theme to dialog and its components
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QTextEdit, QPlainTextEdit {{
                background-color: {content_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 20px;
                font-size: 11pt;
                line-height: 1.4;
                selection-background-color: {accent_q.name()};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 8px 24px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        view = QTextEdit()
        view.setReadOnly(True)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.viewport().setAutoFillBackground(False)
        if is_markdown:
            view.setMarkdown(content)
        else:
            view.setPlainText(content)
        
        # Standardize scrollbar styles to match the rest of the app
        sb_track = Theme.get_scrollbar_track(accent_q)
        sb_thumb = Theme.get_scrollbar_thumb(accent_q)
        sb_hover = Theme.get_scrollbar_thumb_hover(accent_q)
        
        view.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: {sb_track};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {sb_thumb};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {sb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        layout.addWidget(view)
        
        btn_box = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)
        btn_box.addStretch()
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)
        
        dialog.exec()

    def show_tos(self) -> None:
        self._show_markdown_dialog("Terms of Service", "TOS.md")

    def show_whats_new(self) -> None:
        try:
            changelog = self._read_markdown_file("CHANGELOG.md")
            if changelog is None:
                QMessageBox.warning(self, "What's New", "File not found: CHANGELOG.md")
                return

            self._show_themed_dialog("What's New", changelog.strip(), is_markdown=True)
        except Exception as e:
            QMessageBox.critical(self, "What's New", f"Error loading changelog: {e}")

    def open_crash_report_folder(self) -> None:
        folder = _debugging_logs_dir()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
        except Exception:
            QMessageBox.information(self, "Debugging Logs", f"Debugging logs folder:\n{folder}")

    def _create_debugging_log_bundle(self) -> Path | None:
        debug_dir = _debugging_logs_dir()
        report = _write_crash_report("diagnostic")
        if report is None:
            return None

        lines: list[str] = []
        if getattr(self.bridge, "log_path", None) and Path(self.bridge.log_path).exists():
            with open(self.bridge.log_path, "r", encoding="utf-8", errors="replace") as handle:
                tail = handle.readlines()[-120:]
            lines.append("")
            lines.append("Recent sanitized app.log tail:")
            lines.extend(_sanitize_diagnostic_text(line.rstrip("\n")) for line in tail)
        with open(report, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + ("\n" if lines else ""))

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bundle_path = debug_dir / f"medialens-debugging-logs-{stamp}.zip"
        include_files: list[tuple[Path, str]] = []
        for candidate in (
            report,
            debug_dir / "app.log",
            debug_dir / "faulthandler.log",
        ):
            if candidate.exists() and candidate.is_file():
                include_files.append((candidate, candidate.name))

        crash_dir = _crash_reports_dir()
        if crash_dir.exists():
            crash_logs = sorted(
                (p for p in crash_dir.glob("*.log") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:10]
            for idx, crash_log in enumerate(crash_logs, start=1):
                include_files.append((crash_log, f"crash-reports/crash-report-{idx:02d}.log"))

        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "README.txt",
                "\n".join(
                    [
                        "MediaLens debugging log bundle",
                        f"Version: {__version__}",
                        "Private media files, thumbnails, recycle-bin contents, settings, and databases are not included.",
                        "Path-like values are redacted where practical before export.",
                        "",
                    ]
                ),
            )
            seen_names: set[str] = set()
            for source, arcname in include_files:
                if arcname in seen_names:
                    continue
                seen_names.add(arcname)
                try:
                    text = source.read_text(encoding="utf-8", errors="replace")
                    zf.writestr(arcname, _sanitize_diagnostic_text(text))
                except Exception:
                    continue
        return bundle_path

    def create_diagnostic_report(self) -> None:
        try:
            bundle_path = self._create_debugging_log_bundle()
            if bundle_path is None:
                QMessageBox.warning(self, "Debugging Logs", "Unable to create diagnostic report.")
                return
            QMessageBox.information(
                self,
                "Debugging Logs",
                f"Debugging log bundle created:\n{bundle_path}\n\nThis bundle excludes databases, settings, thumbnails, and recycle-bin files.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Debugging Logs", f"Debugging log bundle could not be completed:\n{exc}")

    def _debug_log_upload_config(self) -> tuple[str, str]:
        url = str(os.environ.get("MEDIALENS_DEBUG_UPLOAD_URL", "") or "").strip()
        token = str(os.environ.get("MEDIALENS_DEBUG_UPLOAD_TOKEN", "") or "").strip()
        try:
            if not url:
                url = str(self.bridge.settings.value("support/debug_upload_url", "", type=str) or "").strip()
            if not token:
                token = str(self.bridge.settings.value("support/debug_upload_token", "", type=str) or "").strip()
        except Exception:
            pass
        return url, token

    def _prompt_debug_log_submission(self) -> tuple[str, str] | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Submit Debugging Logs")
        dialog.resize(520, 360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        intro = QLabel(
            "MediaLens will create and submit a sanitized debugging log bundle. "
            "It excludes media files, thumbnails, recycle-bin files, settings, and databases."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        contact_label = QLabel("Contact email (optional)")
        layout.addWidget(contact_label)
        contact_edit = QLineEdit(dialog)
        contact_edit.setPlaceholderText("you@example.com")
        layout.addWidget(contact_edit)

        note_label = QLabel("What happened? (optional)")
        layout.addWidget(note_label)
        note_edit = QPlainTextEdit(dialog)
        note_edit.setPlaceholderText("Briefly describe what you were doing and what went wrong.")
        note_edit.setMaximumHeight(110)
        layout.addWidget(note_edit)

        consent = QCheckBox("I consent to submit this debugging log bundle to MediaLens support.", dialog)
        layout.addWidget(consent)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel", dialog)
        submit_btn = QPushButton("Submit", dialog)
        submit_btn.setEnabled(False)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(submit_btn)
        layout.addLayout(btn_row)

        consent.toggled.connect(submit_btn.setEnabled)
        cancel_btn.clicked.connect(dialog.reject)
        submit_btn.clicked.connect(dialog.accept)

        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return None
        return contact_edit.text().strip(), note_edit.toPlainText().strip()

    def submit_debugging_logs(self) -> None:
        upload_url, upload_token = self._debug_log_upload_config()
        if not upload_url:
            try:
                bundle_path = self._create_debugging_log_bundle()
            except Exception as exc:
                QMessageBox.warning(self, "Debugging Logs", f"Unable to create debugging log bundle:\n{exc}")
                return
            if bundle_path is None:
                QMessageBox.warning(self, "Debugging Logs", "Unable to create debugging log bundle.")
                return
            msg = (
                "Debug log upload is not configured yet.\n\n"
                f"A local bundle was created here:\n{bundle_path}\n\n"
                "After the DreamHost upload endpoint is deployed, set "
                "MEDIALENS_DEBUG_UPLOAD_URL or the hidden setting support/debug_upload_url."
            )
            QMessageBox.information(self, "Submit Debugging Logs", msg)
            return

        prompt = self._prompt_debug_log_submission()
        if prompt is None:
            return
        contact, note = prompt

        try:
            bundle_path = self._create_debugging_log_bundle()
            if bundle_path is None:
                QMessageBox.warning(self, "Submit Debugging Logs", "Unable to create debugging log bundle.")
                return
        except Exception as exc:
            QMessageBox.warning(self, "Submit Debugging Logs", f"Unable to create debugging log bundle:\n{exc}")
            return

        QMessageBox.information(self, "Submit Debugging Logs", "Submitting debugging logs in the background.")
        threading.Thread(
            target=self._upload_debugging_log_bundle,
            args=(bundle_path, upload_url, upload_token, contact, note),
            daemon=True,
        ).start()

    def _upload_debugging_log_bundle(self, bundle_path: Path, upload_url: str, upload_token: str, contact: str, note: str) -> None:
        try:
            max_bytes = 25 * 1024 * 1024
            size = bundle_path.stat().st_size
            if size > max_bytes:
                raise ValueError(f"Bundle is too large to upload ({size} bytes).")

            boundary = f"----MediaLens{uuid.uuid4().hex}"
            parts: list[bytes] = []

            def add_field(name: str, value: str) -> None:
                parts.append(
                    (
                        f"--{boundary}\r\n"
                        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                        f"{value}\r\n"
                    ).encode("utf-8")
                )

            add_field("app_version", __version__)
            add_field("contact", _sanitize_diagnostic_text(contact))
            add_field("note", _sanitize_diagnostic_text(note))

            file_bytes = bundle_path.read_bytes()
            parts.append(
                (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="debug_bundle"; '
                    f'filename="{bundle_path.name}"\r\n'
                    "Content-Type: application/zip\r\n\r\n"
                ).encode("utf-8")
                + file_bytes
                + b"\r\n"
            )
            parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            body = b"".join(parts)

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": f"MediaLens/{__version__}",
            }
            if upload_token:
                headers["Authorization"] = f"Bearer {upload_token}"
            request = urllib.request.Request(upload_url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=45) as response:
                response_text = response.read(4096).decode("utf-8", errors="replace").strip()
                status = int(getattr(response, "status", 200) or 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"Upload failed with HTTP {status}: {response_text}")
            self.debugLogUploadFinished.emit(True, response_text or "Debugging logs submitted.")
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            self.debugLogUploadFinished.emit(False, f"Upload failed with HTTP {exc.code}: {detail}")
        except Exception as exc:
            self.debugLogUploadFinished.emit(False, f"Upload failed: {exc}")

    def _on_debug_log_upload_finished(self, ok: bool, message: str) -> None:
        if ok:
            QMessageBox.information(self, "Submit Debugging Logs", message)
        else:
            QMessageBox.warning(self, "Submit Debugging Logs", message)

    def _on_update_available(self, version: str, manual: bool) -> None:
        if version:
            answer = QMessageBox.question(
                self,
                "Update Available",
                (
                    f"MediaLens {version} is available.\n\n"
                    f"You are currently using {__version__}.\n\n"
                    "Download and install the update now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    setup_path = _download_update_installer_with_dialog(QApplication.instance(), version)
                    if setup_path is not None:
                        _launch_update_installer(setup_path)
                        QApplication.quit()
                except Exception as exc:
                    QMessageBox.warning(self, "Update Error", f"Unable to download or launch the update installer:\n{exc}")
        elif manual:
            QMessageBox.information(self, "Check for Updates", f"You are using the latest version.\n\nCurrent version: {__version__}")

    def _on_update_error(self, message: str) -> None:
        QMessageBox.warning(self, "Update Error", message)




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
