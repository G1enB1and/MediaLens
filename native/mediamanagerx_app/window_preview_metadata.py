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

class WindowPreviewMetadataMixin:
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
        self._preview_svg_path = ""
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
            svg_path = str(getattr(self, "_preview_svg_path", "") or "")
            scaled = QPixmap()
            if svg_path:
                svg_size = QSize(available_w, target_h)
                rendered = _render_svg_image(svg_path, svg_size)
                if rendered is not None and not rendered.isNull():
                    scaled = QPixmap.fromImage(rendered)
            if scaled.isNull():
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

    def _set_preview_pixmap(self, pixmap: QPixmap | None, placeholder: str = "No preview", bg_hint: str = "", svg_path: str = "") -> None:
        self._clear_preview_media()
        self._preview_bg_hint = str(bg_hint or "")
        self._preview_svg_path = str(svg_path or "")
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
        self._preview_svg_path = ""
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
        svg_path = str(preview_path) if Path(preview_path).suffix.lower() == ".svg" else ""
        img = _read_image_with_svg_support(preview_path)
        if img is None or img.isNull():
            self._set_preview_pixmap(None)
            return
        self._set_preview_pixmap(QPixmap.fromImage(img), bg_hint=_thumbnail_bg_hint(preview_path), svg_path=svg_path)
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
            if hasattr(self, "_set_bulk_select_all_pending"):
                self._set_bulk_select_all_pending(False, "")
            self._metadata_applied_revision = active_revision
            self._schedule_tag_list_refresh("rows", request_revision=active_revision)
            return
        file_paths = self._current_file_paths(raw_paths)
        self._current_paths = raw_paths
        if not file_paths:
            self._current_path = None
            self._clear_metadata_panel()
            if hasattr(self, "_set_bulk_select_all_pending"):
                self._set_bulk_select_all_pending(False, "")
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
            if hasattr(self, "_set_bulk_select_all_pending"):
                self._set_bulk_select_all_pending(False, "")
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
        """Reset all metadata fields and show the no-selection empty state."""
        self._set_active_right_workspace("details")
        self._current_path = None
        self._current_paths = []
        kind = getattr(self, "_current_metadata_kind", "image")
        self._setup_metadata_layout(kind)
        self._refresh_preview_for_path(None)

        signal_widgets = [
            self.meta_filename_edit,
            self.meta_desc,
            self.meta_tags,
            self.meta_notes,
            self.meta_exif_date_taken_edit,
            self.meta_metadata_date_edit,
            self.meta_detected_text_edit,
            self.meta_text_detected_toggle,
            self.meta_ai_generated_toggle,
            self.meta_embedded_tags_edit,
            self.meta_embedded_comments_edit,
            self.meta_embedded_metadata_edit,
            self.meta_ai_status_edit,
            self.meta_ai_source_edit,
            self.meta_ai_families_edit,
            self.meta_ai_detection_reasons_edit,
            self.meta_ai_loras_edit,
            self.meta_ai_model_edit,
            self.meta_ai_checkpoint_edit,
            self.meta_ai_sampler_edit,
            self.meta_ai_scheduler_edit,
            self.meta_ai_cfg_edit,
            self.meta_ai_steps_edit,
            self.meta_ai_seed_edit,
            self.meta_ai_upscaler_edit,
            self.meta_ai_denoise_edit,
            self.meta_ai_prompt_edit,
            self.meta_ai_negative_prompt_edit,
            self.meta_ai_params_edit,
            self.meta_ai_workflows_edit,
            self.meta_ai_provenance_edit,
            self.meta_ai_character_cards_edit,
            self.meta_ai_raw_paths_edit,
        ]
        previous_signal_state: list[tuple[QObject, bool]] = []
        for widget in signal_widgets:
            try:
                previous_signal_state.append((widget, widget.blockSignals(True)))
            except Exception:
                pass

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
        self.meta_desc.setPlainText("")
        self.meta_tags.setPlainText("")
        self.meta_notes.setPlainText("")
        self.generate_description_progress_lbl.setText("")
        self.generate_description_error_edit.setPlainText("")
        self.generate_tags_progress_lbl.setText("")
        self.generate_tags_error_edit.setPlainText("")
        self._clear_embedded_labels()

        self._current_ai_meta = {}
        self._current_user_confirmed_text_detected = None
        self._current_auto_text_detected = None
        self._ai_generated_override_dirty = False
        self._text_detected_override_dirty = False
        self._current_video_width = 0
        self._current_video_height = 0
        self._current_video_duration_ms = 0
        self._update_override_note_labels(auto_text_detected=None, auto_ai_detected=None)

        for widget, was_blocked in previous_signal_state:
            try:
                widget.blockSignals(was_blocked)
            except Exception:
                pass

        self._set_metadata_empty_state(True)
        self._sync_tag_list_panel_visibility(refresh_contents=False)


__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
