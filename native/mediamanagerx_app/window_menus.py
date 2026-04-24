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

class WindowMenuShortcutMixin:
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
        icon_name = "close-dark.svg" if Theme.get_is_light() else "close.svg"
        icon_path = (Path(__file__).with_name("web") / "icons" / icon_name).as_posix()
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



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
