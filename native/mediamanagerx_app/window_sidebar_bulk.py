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

class WindowSidebarBulkMixin:
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
                was_visible = bool(self.bottom_panel.isVisible())
                if not bool(value):
                    self._save_bottom_panel_height()
                self.bottom_panel.setVisible(bool(value))
                QTimer.singleShot(0, self._restore_center_splitter_sizes)
                if bool(value) and not was_visible:
                    QTimer.singleShot(0, self._seed_compare_from_first_review_group)
                    QTimer.singleShot(50, self._refresh_compare_nav_buttons)
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
            current_mode = self._current_bulk_editor_mode()
            if current_mode == "ocr" and hasattr(self, "bulk_ocr_scroll_area") and hasattr(self, "bulk_ocr_right_layout"):
                scroll_area = self.bulk_ocr_scroll_area
                layout = self.bulk_ocr_right_layout
            elif current_mode == "captions" and hasattr(self, "bulk_caption_scroll_area") and hasattr(self, "bulk_caption_right_layout"):
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
        if hasattr(self, "bulk_ocr_right_layout"):
            self.bulk_ocr_right_layout.activate()

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
            getattr(self, "btn_use_ocr_gemma", None),
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
            getattr(self, "bulk_ocr_btn_select_all_gallery", None),
            getattr(self, "bulk_ocr_btn_run_fast", None),
            getattr(self, "bulk_ocr_btn_run_ai", None),
            getattr(self, "bulk_ocr_btn_save", None),
            getattr(self, "bulk_ocr_btn_clear", None),
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
            getattr(self, "ocr_button_row", None),
            getattr(self, "bulk_ocr_bottom_buttons", None),
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
            getattr(self, "ocr_progress_lbl", None),
            getattr(self, "ocr_error_edit", None),
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
            self.lbl_group_general,
            self.lbl_group_camera,
            self.lbl_group_ai,
            self.meta_sep1,
            self.meta_sep2,
            self.meta_sep3,
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
        self.meta_empty_state_lbl.setText("Select file(s) to view details.")
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
        if mode == "captions":
            return "captions"
        if mode == "ocr":
            return "ocr"
        return "tags"

    def _set_active_bulk_editor_mode(self, mode: str) -> None:
        raw_mode = str(mode or "").strip().lower()
        next_mode = "captions" if raw_mode == "captions" else ("ocr" if raw_mode == "ocr" else "tags")
        if next_mode != "ocr" and hasattr(self, "_is_ocr_review_panel_visible") and self._is_ocr_review_panel_visible():
            self._close_ocr_review_panel()
        if next_mode != "tags" and hasattr(self, "_is_tag_list_panel_visible") and self._is_tag_list_panel_visible():
            self._close_tag_list_panel()
        self._bulk_editor_mode = next_mode
        if hasattr(self, "bulk_mode_tags_btn"):
            self.bulk_mode_tags_btn.blockSignals(True)
            self.bulk_mode_tags_btn.setChecked(next_mode == "tags")
            self.bulk_mode_tags_btn.blockSignals(False)
        if hasattr(self, "bulk_mode_captions_btn"):
            self.bulk_mode_captions_btn.blockSignals(True)
            self.bulk_mode_captions_btn.setChecked(next_mode == "captions")
            self.bulk_mode_captions_btn.blockSignals(False)
        if hasattr(self, "bulk_mode_ocr_btn"):
            self.bulk_mode_ocr_btn.blockSignals(True)
            self.bulk_mode_ocr_btn.setChecked(next_mode == "ocr")
            self.bulk_mode_ocr_btn.blockSignals(False)
        if hasattr(self, "bulk_pages_stack"):
            if next_mode == "captions":
                target = getattr(self, "bulk_captions_page", None)
            elif next_mode == "ocr":
                target = getattr(self, "bulk_ocr_page", None)
            else:
                target = getattr(self, "bulk_tags_page", None)
            if target is not None:
                self.bulk_pages_stack.setCurrentWidget(target)
        if self._is_bulk_editor_active():
            selection_count = len(self._current_file_paths())
            if next_mode == "captions":
                self._configure_bulk_caption_editor(selection_count)
            elif next_mode == "ocr":
                self._configure_bulk_ocr_editor(selection_count)
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

    def _configure_bulk_ocr_editor(self, selection_count: int) -> None:
        self._set_active_right_workspace("bulk")
        self._set_active_bulk_editor_mode("ocr") if self._current_bulk_editor_mode() != "ocr" else None
        self.bulk_ocr_selection_lbl.setText(f"<span style=\"font-weight:700;\">{selection_count}</span> files selected")
        self.bulk_ocr_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_ocr_btn_run_fast.setProperty("baseText", f"Fast OCR for All ({selection_count} Files)")
        self.bulk_ocr_btn_run_ai.setProperty("baseText", f"AI OCR for All ({selection_count} Files)")
        self.bulk_ocr_btn_save.setProperty("baseText", f"Save OCR Text to DB for {selection_count} Items")
        self.bulk_ocr_btn_clear.setProperty("baseText", f"Clear OCR Text for {selection_count} Items")
        self._refresh_bulk_ocr_editor_summary()
        self._sync_sidebar_panel_widths()

    def _set_bulk_select_all_pending(self, pending: bool, message: str = "") -> None:
        self._bulk_select_all_pending = bool(pending)
        widgets = [
            getattr(self, "bulk_btn_select_all_gallery", None),
            getattr(self, "bulk_caption_btn_select_all_gallery", None),
            getattr(self, "bulk_ocr_btn_select_all_gallery", None),
        ]
        for widget in widgets:
            if widget is not None:
                widget.setEnabled(not bool(pending))
        if self._current_bulk_editor_mode() == "captions":
            label = getattr(self, "bulk_caption_status_lbl", None)
        elif self._current_bulk_editor_mode() == "ocr":
            label = getattr(self, "bulk_ocr_status_lbl", None)
        else:
            label = getattr(self, "bulk_status_lbl", None)
        if label is not None:
            label.setText(str(message or ""))
            try:
                label.repaint()
            except Exception:
                pass
        for widget in widgets:
            if widget is not None:
                try:
                    widget.repaint()
                except Exception:
                    pass

    def _select_all_visible_gallery_items(self, _checked: bool = False) -> None:
        self._set_bulk_select_all_pending(True, "Selecting files...")
        try:
            self.web.page().runJavaScript(
                "try{ if(window.__mmx_selectAllVisible){ window.__mmx_selectAllVisible(); } else if(window.selectAll){ window.selectAll(); } }catch(e){}"
            )
        except Exception:
            self._set_bulk_select_all_pending(False, "")

    def _jump_review_group(self, direction: int) -> None:
        step = -1 if int(direction or 0) < 0 else 1
        try:
            self.web.page().runJavaScript(
                f"try{{ window.__mmx_jumpReviewGroup && window.__mmx_jumpReviewGroup({step}); }}catch(e){{}}"
            )
            QTimer.singleShot(50, self._refresh_compare_nav_buttons)
            QTimer.singleShot(200, self._refresh_compare_nav_buttons)
        except Exception:
            pass

    def _jump_review_image(self, slot_name: str, direction: int) -> None:
        slot = "right" if str(slot_name or "").strip().lower() == "right" else "left"
        step = -1 if int(direction or 0) < 0 else 1
        try:
            self.web.page().runJavaScript(
                f"try{{ window.__mmx_jumpReviewImage && window.__mmx_jumpReviewImage('{slot}', {step}); }}catch(e){{}}"
            )
            QTimer.singleShot(50, self._refresh_compare_nav_buttons)
            QTimer.singleShot(200, self._refresh_compare_nav_buttons)
        except Exception:
            pass

    def _seed_compare_from_first_review_group(self) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool)):
                return
            self.web.page().runJavaScript(
                "try{ window.__mmx_seedCompareFromCurrentReviewGroup ? window.__mmx_seedCompareFromCurrentReviewGroup() : (window.__mmx_seedCompareFromFirstReviewGroup && window.__mmx_seedCompareFromFirstReviewGroup()); }catch(e){}"
            )
        except Exception:
            pass

    def _schedule_startup_compare_seed(self) -> None:
        try:
            if getattr(self, "_startup_compare_seed_scheduled", False):
                return
            self._startup_compare_seed_scheduled = True
            if not bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool)):
                return
            for delay_ms in (300, 900, 1800, 3200):
                QTimer.singleShot(delay_ms, self._seed_compare_from_first_review_group_if_empty)
        except Exception:
            pass

    def _seed_compare_from_first_review_group_if_empty(self) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool)):
                return
            state = self.bridge.get_compare_state()
            left_path = str((state.get("left") or {}).get("path") or "")
            right_path = str((state.get("right") or {}).get("path") or "")
            if left_path or right_path:
                return
            self._seed_compare_from_first_review_group()
            QTimer.singleShot(120, self._refresh_compare_nav_buttons)
        except Exception:
            pass

    def _refresh_compare_nav_buttons(self) -> None:
        if not hasattr(self, "web"):
            return

        def _apply(state) -> None:
            if isinstance(state, str):
                try:
                    parsed = json.loads(state)
                except Exception:
                    parsed = {}
                self._apply_compare_nav_state(parsed if isinstance(parsed, dict) else {})
                return
            self._apply_compare_nav_state(state if isinstance(state, dict) else {})

        try:
            self.web.page().runJavaScript(
                "(() => { try { return JSON.stringify(window.__mmx_getReviewCompareNavState ? window.__mmx_getReviewCompareNavState() : {}); } catch (e) { return '{}'; } })()",
                _apply,
            )
        except Exception:
            self._apply_compare_nav_state({})

    def _apply_compare_nav_state(self, state: dict) -> None:
        if not state:
            for attr in ("bottom_panel_prev_group_btn", "bottom_panel_next_group_btn"):
                button = getattr(self, attr, None)
                if button is not None:
                    button.setEnabled(True)
                    button.setCursor(Qt.CursorShape.PointingHandCursor)
            for attr, tip in (
                ("bottom_panel_left_prev_image_btn", "The left slot is already at the first available image in this group."),
                ("bottom_panel_left_next_image_btn", "You're on the last image in the group for the left slot."),
                ("bottom_panel_right_prev_image_btn", "The right slot is already at the first available image in this group."),
                ("bottom_panel_right_next_image_btn", "You're on the last image in the group for the right slot."),
            ):
                button = getattr(self, attr, None)
                if button is not None:
                    button.setEnabled(False)
                    button.setCursor(Qt.CursorShape.ForbiddenCursor)
                    button.setToolTip(tip)
            return
        pairs = (
            ("bottom_panel_prev_group_btn", "previousGroup", "Jump to Previous Group", "You're on the first group."),
            ("bottom_panel_next_group_btn", "nextGroup", "Jump to Next Group", "You're on the last group."),
            ("bottom_panel_left_prev_image_btn", "leftPrevious", "Load the previous image into the left comparison slot", "The left slot is already at the first available image in this group."),
            ("bottom_panel_left_next_image_btn", "leftNext", "Load the next image into the left comparison slot", "You're on the last image in the group for the left slot."),
            ("bottom_panel_right_prev_image_btn", "rightPrevious", "Load the previous image into the right comparison slot", "The right slot is already at the first available image in this group."),
            ("bottom_panel_right_next_image_btn", "rightNext", "Load the next image into the right comparison slot", "You're on the last image in the group for the right slot."),
        )
        for attr, key, enabled_tip, disabled_tip in pairs:
            button = getattr(self, attr, None)
            if button is None:
                continue
            enabled = bool(state.get(key))
            button.setEnabled(enabled)
            button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor)
            button.setToolTip(enabled_tip if enabled else disabled_tip)

    def _open_bulk_tag_editor_from_menu(self, _checked: bool = False) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
                self.bridge.settings.setValue("ui/show_right_panel", True)
                self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        except Exception:
            pass
        self._set_tag_list_panel_requested_visible(True)
        self._set_active_bulk_editor_mode("tags")
        self._set_active_right_workspace("bulk")
        self._set_bulk_select_all_pending(True, "Selecting files...")
        QTimer.singleShot(0, self._select_all_visible_gallery_items)

    def _open_bulk_caption_editor_from_menu(self, _checked: bool = False) -> None:
        try:
            if not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
                self.bridge.settings.setValue("ui/show_right_panel", True)
                self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        except Exception:
            pass
        self._set_active_bulk_editor_mode("captions")
        self._set_active_right_workspace("bulk")
        self._set_bulk_select_all_pending(True, "Selecting files...")
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
        self.bulk_caption_status_lbl.setText(f"Descriptions saved for {updated} items")
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
        self.bulk_caption_status_lbl.setText(f"Descriptions cleared for {len(paths)} items")
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
        if (
            hasattr(self, "tag_list_panel")
            and self._is_tag_list_panel_visible()
            and not bool(getattr(self, "_bulk_select_all_pending", False))
        ):
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
            if self._current_bulk_editor_mode() == "ocr" and hasattr(self, "bulk_ocr_status_lbl"):
                return self.bulk_ocr_status_lbl
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
            if p.suffix.lower() == ".svg":
                preview_path = p
            else:
                try:
                    preview_path = self.bridge._local_ai_source_path(p)
                except Exception:
                    preview_path = p
            target_size = max(72, int(content_height or BulkSelectedFileRow._TAG_CONTENT_HEIGHT))
            if Path(preview_path).suffix.lower() == ".svg":
                image = _render_svg_image(preview_path, QSize(target_size, target_size))
            else:
                image = _read_image_with_svg_support(preview_path)
            if image is None or image.isNull():
                return None
            return QPixmap.fromImage(image).scaled(
                target_size,
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception:
            return None

    def _bulk_selected_file_thumbnail_bg_hint(self, path: str) -> str:
        try:
            return _thumbnail_bg_hint(path)
        except Exception:
            return ""

    def _toggle_bulk_tag_section(self, toggle: QToolButton, widget: QWidget, checked: bool) -> None:
        if toggle is not None:
            label = str(toggle.property("sectionLabel") or toggle.text() or "")
            self._set_bulk_tag_section_toggle(toggle, label, bool(checked))
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
            self.bulk_status_lbl.setText(f"Saved tags for {Path(clean_path).name}")
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
            self.bulk_caption_status_lbl.setText(f"Saved description for {Path(clean_path).name}")
            QTimer.singleShot(2500, lambda: self.bulk_caption_status_lbl.setText(""))

    def _save_bulk_selected_file_ocr_text(self, _path: str, _text: str) -> None:
        # OCR row edits are committed by the confirm button so accidental focus changes
        # do not mark text as user-confirmed.
        return

    def _save_bulk_ocr_text_to_db(self) -> None:
        paths = self._current_file_paths()
        if not paths or not hasattr(self, "bulk_ocr_selected_files_list"):
            return
        updated = 0
        for i in range(self.bulk_ocr_selected_files_list.count()):
            item = self.bulk_ocr_selected_files_list.item(i)
            row = self.bulk_ocr_selected_files_list.itemWidget(item)
            if not self._is_valid_bulk_selected_file_row(row):
                continue
            clean_path = str(getattr(row, "_path", "") or "").strip()
            if not clean_path:
                continue
            try:
                self.bridge.update_media_detected_text(clean_path, row.tags_edit.toPlainText())
                updated += 1
            except Exception:
                pass
        self._bulk_ocr_status(f"OCR text saved for {updated} item{'s' if updated != 1 else ''}")

    def _clear_bulk_ocr_text(self) -> None:
        paths = self._current_file_paths()
        if not paths:
            return
        updated = 0
        for path in paths:
            try:
                self.bridge.update_media_detected_text(str(path), "")
                self._set_bulk_ocr_row_text(str(path), "")
                updated += 1
            except Exception:
                pass
        self._bulk_ocr_status(f"OCR text cleared for {updated} item{'s' if updated != 1 else ''}")

    def _bulk_ai_ocr_source(self) -> str:
        return "gemma4"

    def _bulk_ocr_status(self, text: str) -> None:
        label = getattr(self, "bulk_ocr_status_lbl", None)
        if label is not None:
            label.setText(str(text or ""))

    def _bulk_ocr_row_for_path(self, path: str):
        target = str(path or "").casefold()
        list_widget = getattr(self, "bulk_ocr_selected_files_list", None)
        if not target or list_widget is None:
            return None
        for i in range(list_widget.count()):
            row = list_widget.itemWidget(list_widget.item(i))
            if self._is_valid_bulk_selected_file_row(row) and str(getattr(row, "_path", "") or "").casefold() == target:
                return row
        return None

    def _set_bulk_ocr_row_text(self, path: str, text: str) -> None:
        row = self._bulk_ocr_row_for_path(path)
        if not self._is_valid_bulk_selected_file_row(row):
            return
        try:
            row.tags_edit.blockSignals(True)
            row.tags_edit.setPlainText(str(text or ""))
            row.tags_edit.blockSignals(False)
        except RuntimeError:
            pass

    def _handle_bulk_ocr_row_action(self, path: str, action_key: str) -> None:
        clean_path = str(path or "").strip()
        action = str(action_key or "").strip().lower()
        if not clean_path:
            return
        if action == "no_text":
            if hasattr(self.bridge, "mark_ocr_no_text_for_path") and self.bridge.mark_ocr_no_text_for_path(clean_path):
                self._set_bulk_ocr_row_text(clean_path, "")
                self._bulk_ocr_status(f"Marked no text for {Path(clean_path).name}")
            return
        if action == "confirm_text":
            row = self._bulk_ocr_row_for_path(clean_path)
            text = row.tags_edit.toPlainText() if self._is_valid_bulk_selected_file_row(row) else ""
            if not str(text or "").strip():
                self._bulk_ocr_status("No text to confirm.")
                return
            if hasattr(self.bridge, "keep_user_ocr_text_for_path") and self.bridge.keep_user_ocr_text_for_path(clean_path, str(text or "")):
                self._set_bulk_ocr_row_text(clean_path, str(text or ""))
                self._bulk_ocr_status(f"Confirmed OCR text for {Path(clean_path).name}")
            return
        if action == "fast_ocr":
            self._run_bulk_ocr_for_paths("paddle_fast", [clean_path])
            return
        if action == "ai_ocr":
            self._run_bulk_ocr_for_paths(self._bulk_ai_ocr_source(), [clean_path])

    def _run_bulk_ocr_for_paths(self, source: str, paths: list[str] | None = None) -> None:
        clean_paths = self._current_file_paths(paths)
        if not clean_paths or not hasattr(self.bridge, "run_manual_ocr_with_source"):
            return
        source_key = str(source or "paddle_fast").strip() or "paddle_fast"
        pending = getattr(self, "_bulk_ocr_pending", None)
        if not isinstance(pending, dict):
            pending = {}
            self._bulk_ocr_pending = pending
        for path in clean_paths:
            pending[str(path)] = source_key
            self.bridge.run_manual_ocr_with_source(str(path), source_key)
        label = "AI OCR" if source_key == self._bulk_ai_ocr_source() else "Fast OCR"
        self._bulk_ocr_status(f"Running {label} for {len(clean_paths)} file{'s' if len(clean_paths) != 1 else ''}...")

    def _handle_bulk_manual_ocr_finished(self, path: str, text: str, error: str) -> bool:
        pending = getattr(self, "_bulk_ocr_pending", None)
        clean_path = str(path or "").strip()
        if str(getattr(self, "_ocr_review_path", "") or "").casefold() == clean_path.casefold():
            if error:
                self._ocr_review_status(f"OCR failed for {Path(clean_path).name}: {error}")
            else:
                self._refresh_ocr_review_for_path(clean_path)
                self._ocr_review_status(f"OCR text updated for {Path(clean_path).name}" if str(text or "").strip() else f"No OCR text found for {Path(clean_path).name}")
        if not isinstance(pending, dict) or clean_path not in pending:
            return False
        pending.pop(clean_path, None)
        if error:
            self._bulk_ocr_status(f"OCR failed for {Path(clean_path).name}: {error}")
            return True
        clean_text = str(text or "").strip()
        self._set_bulk_ocr_row_text(clean_path, clean_text)
        if clean_text:
            self._bulk_ocr_status(f"OCR text updated for {Path(clean_path).name}")
        else:
            self._bulk_ocr_status(f"No OCR text found for {Path(clean_path).name}")
        return True

    def _open_ocr_review_for_current_file(self) -> None:
        path = str(getattr(self, "_current_path", "") or "").strip()
        if not path:
            paths = self._current_file_paths()
            path = paths[0] if paths else ""
        self._open_ocr_review_panel_for_path(path)

    def _open_ocr_review_panel_for_path(self, path: str) -> None:
        clean_path = str(path or "").strip()
        if not clean_path:
            return
        try:
            if not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
                self.bridge.settings.setValue("ui/show_right_panel", True)
                self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        except Exception:
            pass
        if hasattr(self, "center_workspace_stack") and hasattr(self, "ocr_review_panel"):
            self.center_workspace_stack.setCurrentWidget(self.ocr_review_panel)
            self._schedule_gallery_container_relayout(120)
            QTimer.singleShot(0, self._update_ocr_review_image_display)
        self._refresh_ocr_review_for_path(clean_path)

    def _close_ocr_review_panel(self) -> None:
        try:
            if hasattr(self, "center_workspace_stack") and hasattr(self, "gallery_workspace"):
                self._set_center_gallery_visible()
            self._schedule_gallery_container_relayout(0)
        except Exception:
            pass

    def _ocr_review_status(self, text: str) -> None:
        label = getattr(self, "ocr_review_status_lbl", None)
        if label is not None:
            label.setText(str(text or ""))

    def _ocr_review_selected_paths(self) -> list[str]:
        paths = self._current_file_paths()
        current = str(getattr(self, "_ocr_review_path", "") or "").strip()
        if current and current not in paths and Path(current).is_file():
            paths.insert(0, current)
        return paths

    def _move_ocr_review_image(self, delta: int) -> None:
        paths = self._ocr_review_selected_paths()
        current = str(getattr(self, "_ocr_review_path", "") or "").strip()
        if not paths:
            return
        try:
            idx = next(i for i, item in enumerate(paths) if str(item).casefold() == current.casefold())
        except StopIteration:
            idx = 0
        next_idx = max(0, min(len(paths) - 1, idx + int(delta or 0)))
        self._refresh_ocr_review_for_path(paths[next_idx])

    def _ocr_review_media_record(self, path: str) -> dict | None:
        try:
            from app.mediamanager.db.media_repo import get_media_by_path

            media = get_media_by_path(self.bridge.conn, str(path or ""))
            return dict(media) if media else None
        except Exception:
            return None

    def _ocr_review_results_for_path(self, path: str) -> tuple[dict | None, list[dict]]:
        media = self._ocr_review_media_record(path)
        if not media:
            return None, []
        try:
            from app.mediamanager.db.ocr_repo import get_ocr_results

            return media, list(get_ocr_results(self.bridge.conn, int(media.get("id") or 0)) or [])
        except Exception:
            return media, []

    def _ocr_review_source_key(self, source_key: str) -> str:
        key = str(source_key or "").strip()
        return self._bulk_ai_ocr_source() if key == "ai" else key

    def _latest_ocr_review_text(self, results: list[dict], source_key: str) -> str:
        source = self._ocr_review_source_key(source_key)
        for item in list(results or []):
            if str(item.get("source") or "") == source:
                return str(item.get("text") or "")
        return ""

    def _set_ocr_review_winner_state(self, media: dict | None) -> None:
        winner_source = ""
        if media:
            try:
                from app.mediamanager.db.ocr_repo import get_ocr_winner

                winner = get_ocr_winner(self.bridge.conn, int(media.get("id") or 0)) or {}
                winner_source = str(winner.get("source") or "").strip()
            except Exception:
                winner_source = ""
        fields = getattr(self, "ocr_review_fields", {}) or {}
        keep_buttons = getattr(self, "ocr_review_keep_buttons", {}) or {}
        for key in ("paddle_fast", "ai", "user"):
            selected = bool(winner_source and winner_source == self._ocr_review_source_key(key))
            for widget in (fields.get(key), keep_buttons.get(key)):
                if widget is None:
                    continue
                widget.setProperty("ocrWinner", selected)
                try:
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
                except Exception:
                    pass
                widget.update()

    def _refresh_ocr_review_for_path(self, path: str) -> None:
        clean_path = str(path or "").strip()
        if not clean_path:
            return
        self._ocr_review_path = clean_path
        if hasattr(self, "ocr_review_filename_lbl"):
            self.ocr_review_filename_lbl.setText(Path(clean_path).name)
        self._refresh_ocr_review_image(clean_path)
        media, results = self._ocr_review_results_for_path(clean_path)
        fields = getattr(self, "ocr_review_fields", {}) or {}
        for key in ("paddle_fast", "ai", "user"):
            edit = fields.get(key)
            if edit is None:
                continue
            edit.blockSignals(True)
            edit.setPlainText(self._latest_ocr_review_text(results, key))
            edit.blockSignals(False)
        self._set_ocr_review_winner_state(media)
        self._sync_ocr_review_nav_buttons()
        self._ocr_review_status("")

    def _refresh_ocr_review_image(self, path: str) -> None:
        label = getattr(self, "ocr_review_image_lbl", None)
        if label is None:
            return
        clean_path = str(path or "").strip()
        pixmap = QPixmap()
        try:
            source = Path(clean_path)
            if source.suffix.lower() in VIDEO_EXTS and hasattr(self.bridge, "_manual_ocr_source_path"):
                source = self.bridge._manual_ocr_source_path(source)
            img = _read_image_with_svg_support(source)
            if img is not None and not img.isNull():
                pixmap = QPixmap.fromImage(img)
        except Exception:
            pixmap = QPixmap()
        self._ocr_review_source_pixmap = pixmap
        self._update_ocr_review_image_display()

    def _update_ocr_review_image_display(self) -> None:
        label = getattr(self, "ocr_review_image_lbl", None)
        pixmap = getattr(self, "_ocr_review_source_pixmap", QPixmap())
        if label is None:
            return
        if pixmap is None or pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("No preview")
            return
        target = label.size()
        if target.width() <= 10 or target.height() <= 10:
            target = QSize(420, 520)
        scaled = pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setText("")
        label.setPixmap(scaled)

    def _sync_ocr_review_nav_buttons(self) -> None:
        paths = self._ocr_review_selected_paths()
        current = str(getattr(self, "_ocr_review_path", "") or "").strip()
        try:
            idx = next(i for i, item in enumerate(paths) if str(item).casefold() == current.casefold())
        except StopIteration:
            idx = -1
        for button, enabled in (
            (getattr(self, "ocr_review_prev_btn", None), idx > 0),
            (getattr(self, "ocr_review_next_btn", None), idx >= 0 and idx < len(paths) - 1),
        ):
            if button is None:
                continue
            button.setEnabled(bool(enabled))
            button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor)

    def _keep_ocr_review_source(self, source_key: str) -> None:
        path = str(getattr(self, "_ocr_review_path", "") or "").strip()
        if not path:
            return
        media, _results = self._ocr_review_results_for_path(path)
        if not media:
            self._ocr_review_status("No media record found.")
            return
        key = str(source_key or "").strip()
        edit = (getattr(self, "ocr_review_fields", {}) or {}).get(key)
        text = edit.toPlainText() if edit is not None else ""
        if not str(text or "").strip():
            self._ocr_review_status("No OCR text available to keep.")
            return
        ok = False
        if key == "user":
            ok = bool(self.bridge.keep_user_ocr_text_for_path(path, text))
        else:
            try:
                from app.mediamanager.db.ocr_repo import add_ocr_result

                add_ocr_result(
                    self.bridge.conn,
                    int(media.get("id") or 0),
                    source=self._ocr_review_source_key(key),
                    text=str(text or ""),
                    confidence=1.0,
                    engine_version="manual_review",
                    preprocess_profile="review_edit",
                    select_as_winner=True,
                    selected_by="user",
                )
                self.bridge.galleryScopeChanged.emit()
                ok = True
            except Exception as exc:
                try:
                    self.bridge._log(f"Keep edited OCR review source failed: {exc}")
                except Exception:
                    pass
                ok = False
        if ok:
            self._set_bulk_ocr_row_text(path, self.bridge.get_media_metadata(path).get("detected_text", ""))
            self._refresh_ocr_review_for_path(path)
            self._ocr_review_status(f"Kept OCR text for {Path(path).name}")
        else:
            self._ocr_review_status("No OCR text available to keep.")

    def _generate_ocr_review_source(self, source_key: str) -> None:
        path = str(getattr(self, "_ocr_review_path", "") or "").strip()
        if not path:
            return
        key = str(source_key or "").strip()
        if key == "user":
            return
        self._run_bulk_ocr_for_paths(self._ocr_review_source_key(key), [path])
        self._ocr_review_status(f"Running {'AI OCR' if key == 'ai' else 'Fast OCR'} for {Path(path).name}...")

    @staticmethod
    def _bulk_selected_file_tags_text(tags: list[str]) -> str:
        clean = [str(tag or "").strip() for tag in list(tags or []) if str(tag or "").strip()]
        return ", ".join(clean)

    def _bulk_selected_file_payloads(self, paths: list[str]) -> dict[str, tuple[list[str], dict]]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        normalized_by_key: dict[str, str] = {}
        key_by_normalized: dict[str, str] = {}
        for path in paths:
            normalized = normalize_windows_path(path)
            key = normalized.lower()
            normalized_by_key[key] = normalized
            key_by_normalized[key] = key
        result: dict[str, tuple[list[str], dict]] = {
            key: ([], {}) for key in normalized_by_key
        }
        tag_keys: dict[str, set[str]] = {key: set() for key in normalized_by_key}
        if not normalized_by_key:
            return result

        def chunks(values: list[str], size: int = 700):
            for start in range(0, len(values), size):
                yield values[start:start + size]

        normalized_paths = list(key_by_normalized.keys())
        try:
            for batch in chunks(normalized_paths):
                placeholders = ",".join("?" for _ in batch)
                rows = self.bridge.conn.execute(
                    f"""
                    SELECT mi.path, t.name
                    FROM media_items mi
                    JOIN media_tags mt ON mt.media_id = mi.id
                    JOIN tags t ON t.id = mt.tag_id
                    WHERE LOWER(mi.path) IN ({placeholders})
                    ORDER BY mi.path COLLATE NOCASE, t.name COLLATE NOCASE
                    """,
                    batch,
                ).fetchall()
                for media_path, tag_name in rows:
                    key = str(media_path or "").lower()
                    if key not in result:
                        continue
                    tags, metadata = result[key]
                    clean_tag = str(tag_name or "").strip()
                    tag_key = clean_tag.casefold()
                    if clean_tag and tag_key not in tag_keys.setdefault(key, set()):
                        tags.append(clean_tag)
                        tag_keys[key].add(tag_key)
                    result[key] = (tags, metadata)
        except Exception:
            pass

        try:
            for batch in chunks(normalized_paths):
                placeholders = ",".join("?" for _ in batch)
                rows = self.bridge.conn.execute(
                    f"""
                    SELECT mi.path, mm.title, mm.description, mm.notes, mm.embedded_tags,
                           mm.embedded_comments, mm.ai_prompt, mm.ai_negative_prompt, mm.ai_params,
                           mm.embedded_metadata_summary, mi.detected_text
                    FROM media_items mi
                    LEFT JOIN media_metadata mm ON mm.media_id = mi.id
                    WHERE LOWER(mi.path) IN ({placeholders})
                    """,
                    batch,
                ).fetchall()
                for row in rows:
                    key = str(row[0] or "").lower()
                    if key not in result:
                        continue
                    tags, _metadata = result[key]
                    result[key] = (
                        tags,
                        {
                            "title": row[1] or "",
                            "description": row[2] or "",
                            "notes": row[3] or "",
                            "embedded_tags": row[4] or "",
                            "embedded_comments": row[5] or "",
                            "ai_prompt": row[6] or "",
                            "ai_negative_prompt": row[7] or "",
                            "ai_params": row[8] or "",
                            "embedded_metadata_summary": row[9] or "",
                            "detected_text": row[10] or "",
                        },
                    )
        except Exception:
            pass
        return result

    def _refresh_bulk_selected_files_list(
        self,
        list_widget: QListWidget,
        *,
        content_height: int,
        value_getter,
        edit_handler,
        placeholder_text: str,
        generate_handler=None,
        generate_button_text: str = "",
        action_handler=None,
        action_buttons: list[dict] | None = None,
        thumbnail_action_handler=None,
        thumbnail_button_text: str = "",
    ) -> None:
        if list_widget is None:
            return
        list_widget.setUpdatesEnabled(False)
        try:
            self._detach_bulk_selected_file_rows(list_widget)
            list_widget.clear()
            paths = self._current_file_paths()
            payloads = self._bulk_selected_file_payloads(paths)
            try:
                from app.mediamanager.utils.pathing import normalize_windows_path
            except Exception:
                normalize_windows_path = lambda value: str(value or "")
            row_parent = list_widget.viewport() or list_widget
            for path in paths:
                tags, metadata = payloads.get(str(normalize_windows_path(path)).lower(), ([], {}))
                item = QListWidgetItem()
                row = BulkSelectedFileRow(
                    path,
                    None,
                    Path(path).name,
                    str(value_getter(tags, metadata) or ""),
                    row_parent,
                    content_height=content_height,
                    placeholder_text=placeholder_text,
                    generate_button_text=generate_button_text,
                    action_buttons=action_buttons,
                    thumbnail_button_text=thumbnail_button_text,
                )
                item.setSizeHint(QSize(0, row.item_height()))
                row.tagsEdited.connect(edit_handler)
                if generate_handler is not None:
                    row.generateRequested.connect(generate_handler)
                if action_handler is not None:
                    row.actionRequested.connect(action_handler)
                if thumbnail_action_handler is not None:
                    row.thumbnailActionRequested.connect(thumbnail_action_handler)
                list_widget.addItem(item)
                list_widget.setItemWidget(item, row)
            list_widget.doItemsLayout()
        finally:
            list_widget.setUpdatesEnabled(True)
        QTimer.singleShot(0, lambda: self._load_visible_bulk_selected_file_thumbnails(list_widget, content_height))

    @staticmethod
    def _is_valid_bulk_selected_file_row(row) -> bool:
        if not isinstance(row, BulkSelectedFileRow):
            return False
        try:
            import shiboken6

            return bool(shiboken6.isValid(row))
        except Exception:
            return True

    def _detach_bulk_selected_file_rows(self, list_widget: QListWidget) -> None:
        try:
            for i in range(list_widget.count()):
                row = list_widget.itemWidget(list_widget.item(i))
                if not self._is_valid_bulk_selected_file_row(row):
                    continue
                row.blockSignals(True)
                try:
                    row.tags_edit.blockSignals(True)
                    row.tags_edit.editingFinished.disconnect()
                except Exception:
                    pass
        except RuntimeError:
            pass

    def _refresh_bulk_tag_selected_files_list(self) -> None:
        self._refresh_bulk_selected_files_list(
            getattr(self, "bulk_selected_files_list", None),
            content_height=BulkSelectedFileRow._TAG_CONTENT_HEIGHT,
            value_getter=lambda tags, metadata: self._bulk_selected_file_tags_text(tags),
            edit_handler=self._save_bulk_selected_file_tags,
            placeholder_text="Tags for this file",
            generate_handler=self._run_local_ai_tags_for_path,
            generate_button_text="Generate Tags",
        )
        self._queue_bulk_selected_files_layout_sync()

    def _refresh_bulk_caption_selected_files_list(self) -> None:
        self._refresh_bulk_selected_files_list(
            getattr(self, "bulk_caption_selected_files_list", None),
            content_height=BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT,
            value_getter=lambda tags, metadata: str(metadata.get("description") or ""),
            edit_handler=self._save_bulk_selected_file_description,
            placeholder_text="Description for this file",
            generate_handler=self._run_local_ai_description_for_path,
            generate_button_text="Generate Description",
        )
        self._queue_bulk_caption_selected_files_layout_sync()

    def _bulk_ocr_action_buttons(self) -> list[dict]:
        icons_dir = Path(__file__).with_name("web") / "icons"
        return [
            {
                "key": "no_text",
                "label": "",
                "icon": str(icons_dir / "text-disabled.svg"),
                "icon_size": QSize(52, 24),
                "tooltip": "Mark this file as no text detected",
            },
            {
                "key": "fast_ocr",
                "label": "Fast OCR",
                "tooltip": "Run fast OCR for this file",
            },
            {
                "key": "ai_ocr",
                "label": "AI OCR",
                "tooltip": "Run AI OCR for this file",
            },
            {
                "key": "confirm_text",
                "label": "",
                "icon": str(icons_dir / "check-green.svg"),
                "tooltip": "Confirm this OCR text and protect it from future OCR replacement",
            },
        ]

    def _refresh_bulk_ocr_selected_files_list(self) -> None:
        self._refresh_bulk_selected_files_list(
            getattr(self, "bulk_ocr_selected_files_list", None),
            content_height=BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT,
            value_getter=lambda tags, metadata: str(metadata.get("detected_text") or ""),
            edit_handler=self._save_bulk_selected_file_ocr_text,
            placeholder_text="Detected text for this file",
            action_handler=self._handle_bulk_ocr_row_action,
            action_buttons=self._bulk_ocr_action_buttons(),
            thumbnail_action_handler=self._open_ocr_review_panel_for_path,
            thumbnail_button_text="Review",
        )
        self._queue_bulk_ocr_selected_files_layout_sync()

    def _queue_bulk_selected_files_layout_sync(self) -> None:
        if not hasattr(self, "bulk_selected_files_list"):
            return
        QTimer.singleShot(0, self._sync_bulk_selected_files_layout)

    def _load_visible_bulk_selected_file_thumbnails(
        self,
        list_widget: QListWidget,
        content_height: int,
        *,
        max_per_pass: int = 8,
    ) -> None:
        if list_widget is None or list_widget.count() <= 0:
            return
        viewport = list_widget.viewport()
        if viewport is None:
            return
        visible_rect = viewport.rect().adjusted(0, -int(content_height) * 2, 0, int(content_height) * 2)
        loaded = 0
        pending_more = False
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is None:
                continue
            if not list_widget.visualItemRect(item).intersects(visible_rect):
                continue
            row = list_widget.itemWidget(item)
            if not self._is_valid_bulk_selected_file_row(row):
                continue
            if bool(getattr(row, "_thumbnail_loaded", False)):
                continue
            if loaded >= int(max_per_pass):
                pending_more = True
                break
            path = str(getattr(row, "_path", "") or "").strip()
            thumbnail = self._bulk_selected_file_thumbnail(path, content_height)
            bg_hint = self._bulk_selected_file_thumbnail_bg_hint(path)
            try:
                row.set_thumbnail(thumbnail, bg_hint)
            except RuntimeError:
                pass
            loaded += 1
        if pending_more:
            QTimer.singleShot(16, lambda: self._load_visible_bulk_selected_file_thumbnails(list_widget, content_height, max_per_pass=max_per_pass))

    def _bulk_selected_row_editor_width(self, list_widget: QListWidget, row: BulkSelectedFileRow) -> tuple[int, bool]:
        viewport = list_widget.viewport()
        viewport_width = max(0, viewport.width() if viewport is not None else 0)
        try:
            root_margins = row._root_layout.contentsMargins()
            row_margins = row._content_row.contentsMargins()
            thumb_width = int(getattr(row, "_content_height", BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT))
            spacing = max(0, int(row._content_row.spacing()))
        except RuntimeError:
            return BulkSelectedFileRow._MIN_EDITOR_WIDTH, False
        normal_width = max(
            BulkSelectedFileRow._MIN_EDITOR_WIDTH,
            viewport_width
            - root_margins.left()
            - root_margins.right()
            - row_margins.left()
            - row_margins.right()
            - thumb_width
            - spacing
            - BulkSelectedFileRow._RIGHT_GUTTER
            - 4,
        )
        stacked_threshold = max(BulkSelectedFileRow._STACKED_EDITOR_THRESHOLD, row.minimum_unstacked_editor_width())
        if normal_width >= stacked_threshold:
            return normal_width, False
        stacked_width = max(
            BulkSelectedFileRow._MIN_EDITOR_WIDTH,
            viewport_width
            - root_margins.left()
            - root_margins.right()
            - row_margins.left()
            - row_margins.right()
            - BulkSelectedFileRow._RIGHT_GUTTER
            - 4,
        )
        return stacked_width, True

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
        if not self._is_valid_bulk_selected_file_row(first_row):
            return
        host_width, stacked = self._bulk_selected_row_editor_width(list_widget, first_row)
        list_widget.doItemsLayout()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            row = list_widget.itemWidget(item)
            if self._is_valid_bulk_selected_file_row(row):
                try:
                    row.set_shared_editor_widths(host_width, stacked)
                    item.setSizeHint(QSize(0, row.item_height()))
                    row.updateGeometry()
                    row.update()
                except RuntimeError:
                    pass
        viewport.update()
        QTimer.singleShot(
            0,
            lambda: self._load_visible_bulk_selected_file_thumbnails(
                list_widget,
                BulkSelectedFileRow._TAG_CONTENT_HEIGHT,
            ),
        )

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
        if not self._is_valid_bulk_selected_file_row(first_row):
            return
        host_width, stacked = self._bulk_selected_row_editor_width(list_widget, first_row)
        list_widget.doItemsLayout()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            row = list_widget.itemWidget(item)
            if self._is_valid_bulk_selected_file_row(row):
                try:
                    row.set_shared_editor_widths(host_width, stacked)
                    item.setSizeHint(QSize(0, row.item_height()))
                    row.updateGeometry()
                    row.update()
                except RuntimeError:
                    pass
        viewport.update()
        QTimer.singleShot(
            0,
            lambda: self._load_visible_bulk_selected_file_thumbnails(
                list_widget,
                BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT,
            ),
        )

    def _queue_bulk_ocr_selected_files_layout_sync(self) -> None:
        if not hasattr(self, "bulk_ocr_selected_files_list"):
            return
        QTimer.singleShot(0, self._sync_bulk_ocr_selected_files_layout)

    def _sync_bulk_ocr_selected_files_layout(self) -> None:
        if not hasattr(self, "bulk_ocr_selected_files_list"):
            return
        list_widget = self.bulk_ocr_selected_files_list
        viewport = list_widget.viewport()
        if viewport is None:
            return
        viewport_width = max(0, viewport.width())
        if viewport_width <= 0 or list_widget.count() <= 0:
            return
        first_row = list_widget.itemWidget(list_widget.item(0))
        if not self._is_valid_bulk_selected_file_row(first_row):
            return
        host_width, stacked = self._bulk_selected_row_editor_width(list_widget, first_row)
        list_widget.doItemsLayout()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            row = list_widget.itemWidget(item)
            if self._is_valid_bulk_selected_file_row(row):
                try:
                    row.set_shared_editor_widths(host_width, stacked)
                    item.setSizeHint(QSize(0, row.item_height()))
                    row.updateGeometry()
                    row.update()
                except RuntimeError:
                    pass
        viewport.update()
        QTimer.singleShot(
            0,
            lambda: self._load_visible_bulk_selected_file_thumbnails(
                list_widget,
                BulkSelectedFileRow._CAPTION_CONTENT_HEIGHT,
            ),
        )

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

    def _refresh_bulk_ocr_editor_summary(self) -> None:
        if not hasattr(self, "bulk_ocr_selected_files_list"):
            return
        self._refresh_bulk_ocr_selected_files_list()

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
            row = TagListTagRow(self.tag_list_rows, item, entry, self.tag_list_rows.viewport() or self.tag_list_rows)
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
        if not hasattr(self, "tag_list_panel") or not self._is_tag_list_panel_visible():
            return
        if not str(getattr(self.bridge, "_current_gallery_tag_scope_search", "") or "").strip():
            self._active_tag_scope_name = ""
        self._invalidate_tag_list_scope_counts_cache()
        self._refresh_tag_list_panel()

    def _refresh_tag_list_rows_state(self) -> None:
        if not hasattr(self, "tag_list_panel") or not self._is_tag_list_panel_visible():
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
            self.bulk_status_lbl.setText(f"Added '{tag_name}' to {len(paths)} selected files")
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
        self.meta_status_lbl.setText(f"Added '{tag_name}'")
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
            self.bulk_status_lbl.setText(f"Removed '{tag_name}' from {len(paths)} selected files")
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
        self.meta_status_lbl.setText(f"Removed '{tag_name}'")
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




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
