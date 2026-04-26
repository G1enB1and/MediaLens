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

class WindowAppLifecycleMixin:
    def _library_backup_options_dialog(self, *, importing: bool, manifest: dict | None = None) -> tuple[bool, bool, bool, bool, bool]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Import Library Backup" if importing else "Export Library Backup")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Choose optional data to restore." if importing else "Choose what to include.")
        title.setWordWrap(True)
        layout.addWidget(title)

        includes = dict((manifest or {}).get("includes") or {})
        settings_available = not importing or bool(includes.get("settings"))
        thumbs_available = not importing or bool(includes.get("thumbs"))
        local_ai_models_available = not importing or bool(includes.get("local_ai_models"))
        ai_runtimes_available = not importing or any(
            bool(includes.get(key)) for key in ("ai_runtimes", "python_runtime", "python_bootstrap")
        )

        settings_cb = QCheckBox("App settings")
        settings_cb.setChecked(True)
        settings_cb.setEnabled(settings_available)
        if importing and not settings_available:
            settings_cb.setToolTip("This backup does not include app settings.")
        layout.addWidget(settings_cb)

        thumbs_cb = QCheckBox("Thumbnails")
        thumbs_cb.setChecked(False)
        thumbs_cb.setEnabled(thumbs_available)
        if importing and not thumbs_available:
            thumbs_cb.setToolTip("This backup does not include thumbnails.")
        layout.addWidget(thumbs_cb)

        local_ai_models_cb = QCheckBox("Downloaded local AI models")
        local_ai_models_cb.setChecked(False)
        local_ai_models_cb.setEnabled(local_ai_models_available)
        if importing and not local_ai_models_available:
            local_ai_models_cb.setToolTip("This backup does not include downloaded local AI models.")
        layout.addWidget(local_ai_models_cb)

        ai_runtimes_cb = QCheckBox("Local AI runtime environments")
        ai_runtimes_cb.setChecked(False)
        ai_runtimes_cb.setEnabled(ai_runtimes_available)
        if importing and not ai_runtimes_available:
            ai_runtimes_cb.setToolTip("This backup does not include local AI runtime environments.")
        layout.addWidget(ai_runtimes_cb)

        if importing:
            note = QLabel("The current database and MediaLens retention system will be overwritten. A local backup of the existing supported files is created first.")
        else:
            note = QLabel("The database and full MediaLens retention system are always included. Legacy MediaManagerX files and debug logs are excluded. AI models and runtimes can be large.")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QWidget(dialog)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 8, 0, 0)
        buttons_layout.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        ok_btn = QPushButton("Import" if importing else "Export")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(ok_btn)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False, False, False, False, False
        return (
            True,
            settings_cb.isChecked() and settings_available,
            thumbs_cb.isChecked() and thumbs_available,
            local_ai_models_cb.isChecked() and local_ai_models_available,
            ai_runtimes_cb.isChecked() and ai_runtimes_available,
        )

    def export_library_backup(self) -> None:
        try:
            ok, include_settings, include_thumbs, include_local_ai_models, include_ai_runtimes = self._library_backup_options_dialog(importing=False)
            if not ok:
                return
            default_name = f"MediaLens-Library-Backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            target, _selected_filter = QFileDialog.getSaveFileName(
                self,
                "Export Library Backup",
                str(Path.home() / default_name),
                "MediaLens Library Backup (*.zip)",
            )
            if not target:
                return
            if not target.lower().endswith(".zip"):
                target += ".zip"

            from native.mediamanagerx_app.library_backup import LibraryBackupOptions, create_library_backup

            try:
                self.bridge.settings.sync()
            except Exception:
                pass
            result = create_library_backup(
                target,
                options=LibraryBackupOptions(
                    include_settings=include_settings,
                    include_thumbs=include_thumbs,
                    include_local_ai_models=include_local_ai_models,
                    include_ai_runtimes=include_ai_runtimes,
                ),
            )
            included = [name.replace("_", " ") for name, enabled in result.included.items() if enabled]
            QMessageBox.information(
                self,
                "Export Library Backup",
                "Library backup created:\n"
                f"{result.archive_path}\n\n"
                f"Included: {', '.join(included) if included else 'manifest only'}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Export Library Backup", f"Unable to create library backup:\n{exc}")

    def import_library_backup(self) -> None:
        try:
            source, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "Import Library Backup",
                str(Path.home()),
                "MediaLens Library Backup (*.zip)",
            )
            if not source:
                return

            from native.mediamanagerx_app.library_backup import (
                LibraryRestoreOptions,
                read_library_backup_manifest,
                restore_library_backup,
            )

            manifest = read_library_backup_manifest(source)
            ok, include_settings, include_thumbs, include_local_ai_models, include_ai_runtimes = self._library_backup_options_dialog(importing=True, manifest=manifest)
            if not ok:
                return
            answer = QMessageBox.question(
                self,
                "Import Library Backup",
                "Importing this backup will overwrite the current MediaLens database and retention data. "
                "A local backup of the current supported files will be created first.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

            try:
                self.bridge._scan_abort = True
                self.bridge._local_ai_shutting_down = True
                self.bridge.settings.sync()
                self.bridge.conn.close_all()
            except Exception:
                pass

            result = restore_library_backup(
                source,
                options=LibraryRestoreOptions(
                    include_settings=include_settings,
                    include_thumbs=include_thumbs,
                    include_local_ai_models=include_local_ai_models,
                    include_ai_runtimes=include_ai_runtimes,
                    backup_existing=True,
                ),
            )
            restored = [name.replace("_", " ") for name, enabled in result.restored.items() if enabled]
            backup_text = f"\n\nPrevious supported files were backed up to:\n{result.existing_backup_dir}" if result.existing_backup_dir else ""
            QMessageBox.information(
                self,
                "Import Library Backup",
                "Library backup imported. MediaLens will close now so the restored database and settings load cleanly.\n\n"
                f"Restored: {', '.join(restored) if restored else 'nothing'}"
                f"{backup_text}",
            )
            QApplication.quit()
        except Exception as exc:
            QMessageBox.warning(self, "Import Library Backup", f"Unable to import library backup:\n{exc}")

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
        close_icon_name = "close-dark.svg" if is_light else "close.svg"
        close_icon_path = (Path(__file__).with_name("web") / "icons" / close_icon_name).as_posix()

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
                image: url('{close_icon_path}');
            }}
            QPushButton#bottomPanelCloseButton:hover {{
                background-color: {close_btn_hover_bg};
                color: {close_btn_hover_text};
                border-color: {accent_color};
                image: url('{close_icon_path}');
            }}
            """
        )
        self.bottom_panel_close_btn.setText("")
        self.bottom_panel_close_btn.setIcon(QIcon())

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
            self._set_panel_setting(qkey, not cur)
        except Exception:
            pass

    def _set_panel_setting(self, qkey: str, value: bool) -> None:
        try:
            new = bool(value)
            if not new:
                if qkey == "ui/show_bottom_panel":
                    self._save_bottom_panel_height()
                else:
                    self._save_main_panel_widths()
            signal_key = qkey.replace("/", ".")
            self.bridge.settings.setValue(qkey, new)
            self._apply_ui_flag(signal_key, new)
            self.bridge.uiFlagChanged.emit(signal_key, new)
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
        except Exception as exc:
            try:
                self.bridge._log(f"Failed to open settings dialog: {exc}")
            except Exception:
                pass
            QMessageBox.warning(self, "Settings Error", f"Unable to open settings:\n{exc}")

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


__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
