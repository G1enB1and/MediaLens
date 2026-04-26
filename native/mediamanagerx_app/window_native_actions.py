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

class WindowNativeActionsMixin:
    def _on_splitter_moved(self) -> None:
        """Save splitter state and re-apply card selection if the resize caused a deselect."""
        self._maintain_tag_list_width_on_main_resize()
        self._save_splitter_state()
        self._sync_sidebar_panel_widths()
        self._update_preview_display()
        if hasattr(self, "_update_ocr_review_image_display"):
            self._update_ocr_review_image_display()
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
        if self._is_companion_panel_visible():
            try:
                self.bridge.settings.setValue("ui/tag_list_last_details_width", self._details_panel_width_without_tag_list())
            except Exception:
                pass
        self._sync_sidebar_panel_widths()
        self._update_preview_display()
        if hasattr(self, "_update_ocr_review_image_display"):
            self._update_ocr_review_image_display()
        self._schedule_gallery_container_relayout(120)

    def _handle_right_splitter_overflow_drag(self, delta_x: int) -> None:
        if delta_x >= 0 or not self._is_companion_panel_visible():
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
            self.bridge.settings.setValue(self._companion_panel_width_setting_key(), min_tag_width)
            self.bridge.settings.setValue("ui/tag_list_last_details_width", next_details_width)
        except Exception:
            pass

    def _maintain_tag_list_width_on_main_resize(self) -> None:
        if not hasattr(self, "right_splitter") or not self._is_companion_panel_visible():
            return
        try:
            details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._details_panel_width_without_tag_list(), type=int) or self._details_panel_width_without_tag_list()))
            total_right_width = max(240, int(self.right_panel_host.width() or self._current_splitter_sizes()[2]))
            min_tag_width = 220
            next_tag_width = max(min_tag_width, total_right_width - details_width)
            next_details_width = max(240, total_right_width - next_tag_width)
            self.right_splitter.setSizes([next_tag_width, next_details_width])
            self.bridge.settings.setValue(self._companion_panel_width_setting_key(), int(next_tag_width))
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

        if hasattr(self, "bottom_panel_prev_group_btn"):
            self.bottom_panel_prev_group_btn.setIcon(self._native_arrow_icon("left"))
        if hasattr(self, "bottom_panel_next_group_btn"):
            self.bottom_panel_next_group_btn.setIcon(self._native_arrow_icon("right"))
        for attr, direction in (
            ("bottom_panel_left_prev_image_btn", "left"),
            ("bottom_panel_left_next_image_btn", "right"),
            ("bottom_panel_right_prev_image_btn", "left"),
            ("bottom_panel_right_next_image_btn", "right"),
        ):
            button = getattr(self, attr, None)
            if button is not None:
                button.setIcon(self._native_arrow_icon(direction))
        for toggle in (
            getattr(self, "bulk_common_tags_toggle", None),
            getattr(self, "bulk_uncommon_tags_toggle", None),
        ):
            if toggle is not None:
                label = str(toggle.property("sectionLabel") or toggle.text() or "")
                self._set_bulk_tag_section_toggle(toggle, label, toggle.isChecked())
        
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
            companion_style = f"""
                QStackedWidget#rightCompanionStack {{
                    background-color: {sb_bg_str};
                    border-right: 1px solid {Theme.get_border(accent)};
                }}
                QWidget#tagListPanel {{
                    background-color: {sb_bg_str};
                    border-right: none;
                }}
                QWidget#ocrReviewPanel {{
                    background-color: {sb_bg_str};
                    border-right: none;
                }}
                QLabel#tagListTitleLabel, QLabel#activeTagListNameLabel, QLabel#tagListSortLabel, QLabel#ocrReviewTitleLabel, QLabel#ocrReviewFieldLabel, QLabel#ocrReviewFilenameLabel {{
                    color: {text};
                    font-weight: 700;
                    background: transparent;
                }}
                QLabel#ocrReviewTitleLabel {{
                    font-size: 16px;
                    qproperty-alignment: AlignCenter;
                }}
                QLabel#ocrReviewImageLabel {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 8px;
                    color: {text_muted};
                    padding: 8px;
                }}
                QPlainTextEdit#ocrReviewTextEdit {{
                    background-color: {Theme.get_input_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 4px;
                    padding: 4px;
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QPlainTextEdit#bulkTagEditorStatusLabel {{
                    background: transparent;
                    border: none;
                    color: {text_muted};
                    font-weight: 500;
                    padding: 0px;
                    margin: 0px;
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QLabel#tagListEmptyLabel {{
                    color: {text_muted};
                    background: transparent;
                }}
                QPushButton#tagListCloseButton, QPushButton#ocrReviewKeepButton {{
                    background-color: {Theme.get_control_bg(accent)};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    color: {text};
                    padding: 0px;
                    margin: 0px;
                }}
                QPushButton#tagListCloseButton:hover, QPushButton#ocrReviewKeepButton:hover {{
                    background-color: {close_hover_bg};
                    color: {text};
                    border-color: {accent_str};
                }}
                QPushButton#bulkSelectedFileGenerateButton, QPushButton#bulkBtnRunLocalAI {{
                    background-color: {Theme.get_btn_save_bg(accent)};
                    color: {text};
                    border: 1px solid {Theme.get_border(accent)};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton#bulkSelectedFileGenerateButton:hover, QPushButton#bulkBtnRunLocalAI:hover {{
                    background-color: {Theme.get_btn_save_hover(accent)};
                    color: {"#000" if is_light else "#fff"};
                    border-color: {accent_str};
                }}
                QPushButton#bulkSelectedFileGenerateButton:disabled, QPushButton#bulkBtnRunLocalAI:disabled {{
                    background-color: {Theme.get_control_bg(accent)};
                    color: {text_muted};
                    border-color: {Theme.get_border(accent)};
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
            """
            if hasattr(self, "right_companion_stack"):
                self.right_companion_stack.setStyleSheet(companion_style)
            self.tag_list_panel.setStyleSheet(companion_style)
            if hasattr(self, "ocr_review_panel"):
                self.ocr_review_panel.setStyleSheet(companion_style)
            self._apply_tag_list_theme()

        # Metadata - Mirroring Left Panel Background precisely
        self.right_panel.setStyleSheet(f"background-color: {sb_bg_str}; border-left: none;")
        right_palette = self.right_panel.palette()
        right_palette.setColor(QPalette.ColorRole.Window, QColor(sb_bg_str))
        right_palette.setColor(QPalette.ColorRole.Base, QColor(sb_bg_str))
        self.right_panel.setAutoFillBackground(True)
        self.right_panel.setPalette(right_palette)
        if hasattr(self, "bottom_panel"):
            disabled_nav_bg = "#d7dbe2" if is_light else "#303030"
            disabled_nav_text = "#7b828c" if is_light else "#b8b8b8"
            disabled_nav_border = "#b8bec8" if is_light else "#4a4a4a"
            disabled_nav_hover_border = "#a7afbb" if is_light else "#5c5c5c"
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
                QPushButton#bottomPanelGroupNavButton:hover {{
                    border-color: {accent.name()};
                }}
                QPushButton#bottomPanelGroupNavButton:disabled {{
                    background-color: {disabled_nav_bg};
                    color: {disabled_nav_text};
                    border-color: {disabled_nav_border};
                }}
                QPushButton#bottomPanelGroupNavButton:disabled:hover {{
                    background-color: {disabled_nav_bg};
                    color: {disabled_nav_text};
                    border-color: {disabled_nav_hover_border};
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
            QPushButton#btnSaveMeta, QPushButton#btnUseOcr, QPushButton#btnUseOcrGemma, QPushButton#btnGenerateTags, QPushButton#btnGenerateDescription, QPushButton#btnImportExif, QPushButton#btnMergeHiddenMeta, QPushButton#btnSaveToExif, QPushButton#btnOpenTagList, QPushButton#btnOpenOcrReview, QPushButton#metaEmptySelectAllButton {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#btnSaveMeta:hover, QPushButton#btnUseOcr:hover, QPushButton#btnUseOcrGemma:hover, QPushButton#btnGenerateTags:hover, QPushButton#btnGenerateDescription:hover, QPushButton#btnImportExif:hover, QPushButton#btnMergeHiddenMeta:hover, QPushButton#btnSaveToExif:hover, QPushButton#btnOpenTagList:hover, QPushButton#btnOpenOcrReview:hover, QPushButton#metaEmptySelectAllButton:hover {{
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
                QWidget#bulkOcrEditorScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
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
                    padding-top: 7px;
                }}
                QLabel#bulkSelectedFileThumb {{
                    background-color: {Theme.mix(Theme.get_input_bg(accent), QColor("#ffffff" if is_light else "#000000"), 0.16)};
                    border: 1px solid {Theme.get_input_border(accent)};
                    border-radius: 6px;
                }}
                QPlainTextEdit#bulkTagEditorCommonTagsText, QPlainTextEdit#bulkTagEditorUncommonTagsText {{
                    selection-background-color: {Theme.get_accent_soft(accent)};
                }}
                QPushButton#bulkBtnSelectAllGallery, QPushButton#bulkBtnClearTags, QPushButton#bulkBtnRunLocalAI, QPushButton#bulkBtnSaveMeta, QPushButton#bulkBtnSaveToExif, QPushButton#bulkBtnOpenTagList, QPushButton#bulkSelectedFileGenerateButton {{
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
                QPushButton#bulkBtnSelectAllGallery:hover, QPushButton#bulkBtnClearTags:hover, QPushButton#bulkBtnRunLocalAI:hover, QPushButton#bulkBtnSaveMeta:hover, QPushButton#bulkBtnSaveToExif:hover, QPushButton#bulkBtnOpenTagList:hover, QPushButton#bulkSelectedFileGenerateButton:hover {{
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
            if hasattr(self, "bulk_ocr_scroll_container"):
                self.bulk_ocr_scroll_container.setStyleSheet(bulk_editor_style)
        self._update_preview_play_button_icon()
        self._apply_tag_list_theme()
        
        self._update_app_style(accent)



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
