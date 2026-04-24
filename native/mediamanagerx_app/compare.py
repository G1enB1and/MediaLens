from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *

class CompareRevealViewer(QWidget):
    _CONTENT_PADDING = 7

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("compareRevealViewer")
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMinimumHeight(0)
        self._left_path = ""
        self._right_path = ""
        self._left_image: QImage | None = None
        self._right_image: QImage | None = None
        self._zoom = 1.0
        self._pan = QPoint(0, 0)
        self._slider_ratio = 0.5
        self._slider_drag_offset_x = 0
        self._drag_mode = ""
        self._drag_start_pos = QPoint()
        self._pan_start = QPoint()
        self._isolate_slot = ""
        self._auto_center_on_pair = True
        self._frame_bg = QColor("#121212")
        self._frame_border = QColor(Theme.get_border(QColor(Theme.ACCENT_DEFAULT)))

    def set_frame_style(self, bg_color: str, border_color: str) -> None:
        self._frame_bg = QColor(str(bg_color or "#121212"))
        self._frame_border = QColor(str(border_color or Theme.get_border(QColor(Theme.ACCENT_DEFAULT))))
        self.update()

    def _load_image(self, path: str) -> QImage | None:
        image = _read_image_with_svg_support(path)
        if image is None or image.isNull():
            return None
        return image

    def set_images(self, left_path: str, right_path: str) -> None:
        had_left = self._left_image is not None and not self._left_image.isNull()
        had_right = self._right_image is not None and not self._right_image.isNull()
        left_path = str(left_path or "")
        right_path = str(right_path or "")
        if left_path != self._left_path:
            self._left_path = left_path
            self._left_image = self._load_image(left_path)
        if right_path != self._right_path:
            self._right_path = right_path
            self._right_image = self._load_image(right_path)
        has_left = self._left_image is not None and not self._left_image.isNull()
        has_right = self._right_image is not None and not self._right_image.isNull()
        if has_left and not has_right:
            self._slider_ratio = 1.0
            self._auto_center_on_pair = True
        elif has_right and not has_left:
            self._slider_ratio = 0.0
            self._auto_center_on_pair = True
        elif has_left and has_right:
            if (had_left != had_right) and self._auto_center_on_pair:
                self._slider_ratio = 0.5
                self._auto_center_on_pair = False
        self.update()

    def set_isolated_slot(self, slot_name: str) -> None:
        slot = str(slot_name or "").strip().lower()
        if slot not in {"left", "right", ""}:
            slot = ""
        if slot != self._isolate_slot:
            self._isolate_slot = slot
            self.update()

    def _canvas_size(self) -> QSize:
        widths = [
            image.width()
            for image in (self._left_image, self._right_image)
            if image is not None and not image.isNull()
        ]
        heights = [
            image.height()
            for image in (self._left_image, self._right_image)
            if image is not None and not image.isNull()
        ]
        return QSize(max(widths, default=1), max(heights, default=1))

    def _content_rect(self) -> QRect:
        padding = max(0, int(self._CONTENT_PADDING))
        return self.rect().adjusted(padding, padding, -padding, -padding)

    def has_different_aspect_ratios(self) -> bool:
        left_image = self._left_image
        right_image = self._right_image
        if (
            left_image is None
            or left_image.isNull()
            or right_image is None
            or right_image.isNull()
        ):
            return False
        tolerance_px = 2.0
        scaled_right_height = right_image.height() * (left_image.width() / max(1, right_image.width()))
        scaled_right_width = right_image.width() * (left_image.height() / max(1, right_image.height()))
        scaled_left_height = left_image.height() * (right_image.width() / max(1, left_image.width()))
        scaled_left_width = left_image.width() * (right_image.height() / max(1, left_image.height()))
        return not (
            abs(left_image.height() - scaled_right_height) <= tolerance_px
            or abs(left_image.width() - scaled_right_width) <= tolerance_px
            or abs(right_image.height() - scaled_left_height) <= tolerance_px
            or abs(right_image.width() - scaled_left_width) <= tolerance_px
        )

    def upscale_match_message(self) -> str:
        left_image = self._left_image
        right_image = self._right_image
        if (
            left_image is None
            or left_image.isNull()
            or right_image is None
            or right_image.isNull()
        ):
            return ""
        left_area = left_image.width() * left_image.height()
        right_area = right_image.width() * right_image.height()
        if left_area <= 0 or right_area <= 0 or left_area == right_area:
            return ""
        return "Upscaled Left to match" if left_area < right_area else "Upscaled Right to match"

    def _fit_scale(self) -> float:
        canvas = self._canvas_size()
        content_rect = self._content_rect()
        if canvas.width() <= 0 or canvas.height() <= 0 or content_rect.width() <= 0 or content_rect.height() <= 0:
            return 1.0
        return min(content_rect.width() / canvas.width(), content_rect.height() / canvas.height())

    def _scaled_canvas_rect(self, scale: float) -> QRect:
        canvas = self._canvas_size()
        content_rect = self._content_rect()
        scaled_w = max(1, round(canvas.width() * scale))
        scaled_h = max(1, round(canvas.height() * scale))
        left = round(content_rect.x() + (content_rect.width() - scaled_w) / 2 + self._pan.x())
        top = round(content_rect.y() + (content_rect.height() - scaled_h) / 2 + self._pan.y())
        return QRect(left, top, scaled_w, scaled_h)

    def _draw_image(self, painter: QPainter, image: QImage | None, canvas_rect: QRect, clip_rect: QRect | None) -> None:
        if image is None or image.isNull():
            return
        target_size = image.size().scaled(
            canvas_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        draw_w = max(1, target_size.width())
        draw_h = max(1, target_size.height())
        draw_x = canvas_rect.x() + round((canvas_rect.width() - draw_w) / 2)
        draw_y = canvas_rect.y() + round((canvas_rect.height() - draw_h) / 2)
        target_rect = QRect(draw_x, draw_y, draw_w, draw_h)
        painter.save()
        if clip_rect is not None:
            painter.setClipRect(clip_rect, Qt.ClipOperation.IntersectClip)
        painter.drawImage(target_rect, image)
        painter.restore()

    def _clamp_pan(self) -> None:
        scale = self._fit_scale() * self._zoom
        canvas_rect = self._scaled_canvas_rect(scale)
        content_rect = self._content_rect()
        max_x = max(0, round((canvas_rect.width() - content_rect.width()) / 2))
        max_y = max(0, round((canvas_rect.height() - content_rect.height()) / 2))
        if canvas_rect.width() <= content_rect.width():
            self._pan.setX(0)
        else:
            self._pan.setX(max(-max_x, min(max_x, self._pan.x())))
        if canvas_rect.height() <= content_rect.height():
            self._pan.setY(0)
        else:
            self._pan.setY(max(-max_y, min(max_y, self._pan.y())))

    def _slider_hit_test(self, point: QPoint) -> bool:
        available_left = self._left_image is not None and not self._left_image.isNull()
        available_right = self._right_image is not None and not self._right_image.isNull()
        if not available_left or not available_right or self._isolate_slot in {"left", "right"}:
            return False
        content_rect = self._content_rect()
        if content_rect.width() <= 0 or content_rect.height() <= 0:
            return False
        slider_x = content_rect.left() + round(content_rect.width() * self._slider_ratio)
        return abs(point.x() - slider_x) <= 16 and content_rect.adjusted(-10, -10, 10, 10).contains(point)

    def _sync_hover_cursor(self, point: QPoint | None = None) -> None:
        if self._drag_mode == "slider":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            return
        target_point = point if point is not None else self.mapFromGlobal(QCursor.pos())
        self.setCursor(Qt.CursorShape.PointingHandCursor if self._slider_hit_test(target_point) else Qt.CursorShape.ArrowCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        frame_rect = QRectF(0.5, 0.5, max(0.0, self.width() - 1.0), max(0.0, self.height() - 1.0))
        frame_radius = 10.0
        frame_path = QPainterPath()
        frame_path.addRoundedRect(frame_rect, frame_radius, frame_radius)
        painter.fillPath(frame_path, self._frame_bg)
        content_rect = self._content_rect()
        content_rect_f = QRectF(
            content_rect.x() + 0.5,
            content_rect.y() + 0.5,
            max(0.0, content_rect.width() - 1.0),
            max(0.0, content_rect.height() - 1.0),
        )
        content_radius = 8.0
        content_path = QPainterPath()
        content_path.addRoundedRect(content_rect_f, content_radius, content_radius)
        painter.save()
        painter.setClipPath(content_path)

        available_left = self._left_image is not None and not self._left_image.isNull()
        available_right = self._right_image is not None and not self._right_image.isNull()
        if not available_left and not available_right:
            painter.setPen(QColor("#8a8a8a"))
            painter.drawText(self._content_rect(), Qt.AlignmentFlag.AlignCenter, "Drop or browse two images to compare")
            painter.restore()
            border_pen = QPen(self._frame_border)
            border_pen.setWidth(1)
            border_pen.setCosmetic(True)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(frame_rect, frame_radius, frame_radius)
            return

        scale = self._fit_scale() * self._zoom
        canvas_rect = self._scaled_canvas_rect(scale)
        slider_x = content_rect.left() + round(content_rect.width() * self._slider_ratio)
        left_clip = QRect(self.rect().left(), self.rect().top(), max(0, slider_x - self.rect().left()), self.rect().height())
        right_clip = QRect(slider_x, self.rect().top(), max(0, self.rect().right() - slider_x + 1), self.rect().height())

        isolate_left = self._isolate_slot == "left" and available_left
        isolate_right = self._isolate_slot == "right" and available_right
        painter.save()
        painter.setClipRect(canvas_rect, Qt.ClipOperation.IntersectClip)
        if isolate_left:
            self._draw_image(painter, self._left_image, canvas_rect, None)
        elif isolate_right:
            self._draw_image(painter, self._right_image, canvas_rect, None)
        else:
            self._draw_image(painter, self._left_image, canvas_rect, left_clip)
            self._draw_image(painter, self._right_image, canvas_rect, right_clip)
        painter.restore()
        painter.restore()

        if not isolate_left and not isolate_right and available_left and available_right:
            painter.save()
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(slider_x, content_rect.top(), slider_x, content_rect.bottom())
            handle_rect = QRect(slider_x - 8, round(content_rect.center().y() - 28), 16, 56)
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(handle_rect, 8, 8)
            painter.restore()

        border_pen = QPen(self._frame_border)
        border_pen.setWidth(1)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame_rect, frame_radius, frame_radius)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        old_scale = self._fit_scale() * self._zoom
        old_rect = self._scaled_canvas_rect(old_scale)
        scene_x = (event.position().x() - old_rect.left()) / max(old_scale, 0.0001)
        scene_y = (event.position().y() - old_rect.top()) / max(old_scale, 0.0001)
        step = 1.15 if delta > 0 else (1 / 1.15)
        self._zoom = max(1.0, min(12.0, self._zoom * step))
        if self._zoom <= 1.001:
            self._zoom = 1.0
            self._pan = QPoint(0, 0)
        else:
            new_scale = self._fit_scale() * self._zoom
            content_rect = self._content_rect()
            base_left = content_rect.x() + (content_rect.width() - self._canvas_size().width() * new_scale) / 2
            base_top = content_rect.y() + (content_rect.height() - self._canvas_size().height() * new_scale) / 2
            self._pan = QPoint(
                round(event.position().x() - base_left - scene_x * new_scale),
                round(event.position().y() - base_top - scene_y * new_scale),
            )
            self._clamp_pan()
        self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        if self._slider_hit_test(event.position().toPoint()):
            self._drag_mode = "slider"
            content_rect = self._content_rect()
            slider_x = content_rect.left() + round(content_rect.width() * self._slider_ratio)
            self._slider_drag_offset_x = int(round(event.position().x() - slider_x))
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._zoom > 1.0:
            self._drag_mode = "pan"
            self._drag_start_pos = event.position().toPoint()
            self._pan_start = QPoint(self._pan)
        else:
            self._drag_mode = ""
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_mode == "slider":
            content_rect = self._content_rect()
            if content_rect.width() > 0:
                drag_x = event.position().x() - float(self._slider_drag_offset_x)
                self._slider_ratio = max(0.0, min(1.0, (drag_x - content_rect.left()) / content_rect.width()))
                self.update()
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            event.accept()
            return
        if self._drag_mode == "pan":
            delta = event.position().toPoint() - self._drag_start_pos
            self._pan = self._pan_start + delta
            self._clamp_pan()
            self.update()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        self._sync_hover_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_mode = ""
        self._slider_drag_offset_x = 0
        self._sync_hover_cursor(event.position().toPoint())
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        self._clamp_pan()
        self._sync_hover_cursor()
        super().resizeEvent(event)

    def leaveEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)


class CompareSlotCard(QFrame):
    slotPathDropped = Signal(str, str)
    slotSwapRequested = Signal(str, str)
    browseRequested = Signal(str)
    clearRequested = Signal(str)
    isolateRequested = Signal(str)
    isolateReleased = Signal()
    swapStarted = Signal()
    keepToggled = Signal(str, bool)
    deleteToggled = Signal(str, bool)
    bestRequested = Signal(str, bool)
    deleteRequested = Signal(str, str)

    def __init__(self, slot_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.slot_name = str(slot_name)
        self.setObjectName("compareSlotCard")
        self.setAcceptDrops(True)
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self._entry: dict = {}
        self._full_name_text: str = "Drop image here"
        self._drag_start_pos: QPoint | None = None
        self._thumb_source_pixmap: QPixmap | None = None
        self._thumb_border_color: str = Theme.get_border(QColor(Theme.ACCENT_DEFAULT))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        self.header_row = QWidget()
        self.header_row.setObjectName("compareSlotHeader")
        header_layout = QHBoxLayout(self.header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.name_label = QLabel("Drop image here")
        self.name_label.setObjectName("compareSlotName")
        self.name_label.setContentsMargins(0, 0, 0, 0)
        self.name_label.setMinimumHeight(0)
        self.name_label.setMinimumWidth(0)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.name_label, 1)

        self.clear_btn = QPushButton("X")
        self.clear_btn.setObjectName("compareSlotClearButton")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFixedSize(22, 22)
        self.clear_btn.clicked.connect(lambda: self.clearRequested.emit(self.slot_name))
        header_layout.addWidget(self.clear_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.thumb_frame = QFrame()
        self.thumb_frame.setObjectName("compareSlotThumbCard")
        self.thumb_frame.setMinimumHeight(0)
        self.thumb_frame.setCursor(Qt.CursorShape.ArrowCursor)
        thumb_layout = QVBoxLayout(self.thumb_frame)
        thumb_layout.setContentsMargins(6, 4, 6, 4)
        thumb_layout.setSpacing(0)

        thumb_layout.addWidget(self.header_row)

        self.thumb_wrap = QWidget()
        self.thumb_wrap.setMinimumHeight(0)
        self.thumb_wrap.setCursor(Qt.CursorShape.ArrowCursor)
        thumb_wrap_layout = QVBoxLayout(self.thumb_wrap)
        thumb_wrap_layout.setContentsMargins(0, 5, 0, 5)
        thumb_wrap_layout.setSpacing(0)

        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("compareSlotThumb")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setMinimumSize(0, 50)
        self.thumb_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.thumb_label.setCursor(Qt.CursorShape.ArrowCursor)
        thumb_wrap_layout.addWidget(self.thumb_label, 1)
        thumb_layout.addWidget(self.thumb_wrap, 1)

        self.meta_label = QLabel("Browse or drag an image from the gallery")
        self.meta_label.setObjectName("compareSlotMeta")
        self.meta_label.setWordWrap(True)
        self.meta_label.setContentsMargins(0, 0, 0, 0)
        self.meta_label.setMinimumHeight(0)
        thumb_layout.addWidget(self.meta_label)
        layout.addWidget(self.thumb_frame, 1)

        self.reasons_label = QLabel("")
        self.reasons_label.setObjectName("compareSlotReasons")
        self.reasons_label.setWordWrap(True)
        layout.addWidget(self.reasons_label)

        self.best_label = QLabel("")
        self.best_label.setObjectName("compareSlotBest")
        self.best_label.setWordWrap(True)
        layout.addWidget(self.best_label)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(10)

        self.keep_toggle = QCheckBox("Keep")
        self.keep_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keep_toggle.clicked.connect(self._emit_keep_changed)
        controls.addWidget(self.keep_toggle)

        self.delete_toggle = QCheckBox("Delete")
        self.delete_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_toggle.clicked.connect(self._emit_delete_changed)
        controls.addWidget(self.delete_toggle)

        self.best_toggle = QCheckBox("Best Overall")
        self.best_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.best_toggle.clicked.connect(self._emit_best_changed)
        controls.addWidget(self.best_toggle)

        self.identical_label = QLabel("Identical")
        self.identical_label.setVisible(False)
        controls.addWidget(self.identical_label)

        layout.addLayout(controls)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)

        self.browse_btn = QPushButton("Browseâ€¦")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(lambda: self.browseRequested.emit(self.slot_name))
        self.browse_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        actions.addWidget(self.browse_btn, 1)

        self.delete_btn = QPushButton("")
        self.delete_btn.setObjectName("compareSlotDeleteButton")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(32, 30)
        self.delete_btn.setToolTip("Delete this file")
        self.delete_btn.clicked.connect(self._emit_delete_clicked)
        actions.addWidget(self.delete_btn, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(actions)

        self._render_entry({})

    def _update_name_elision(self) -> None:
        metrics = QFontMetrics(self.name_label.font())
        available_width = max(24, self.name_label.width())
        elided = metrics.elidedText(self._full_name_text, Qt.TextElideMode.ElideRight, available_width)
        if self.name_label.text() != elided:
            self.name_label.setText(elided)
        self.name_label.setToolTip(self._full_name_text if elided != self._full_name_text else "")

    def _set_name_text(self, text: str) -> None:
        self._full_name_text = str(text or "")
        self._update_name_elision()

    def apply_theme_styles(self, text: str, text_muted: str, accent_hex: str, accent_raw: str, thumb_bg: str, border: str) -> None:
        accent_color = QColor(accent_raw)
        is_light = Theme.get_is_light()
        btn_base = Theme.get_input_bg(accent_color)
        btn_hover = Theme.get_btn_save_hover(accent_color)
        btn_border = Theme.get_input_border(accent_color)
        btn_border_hover = Theme.mix(Theme.get_border(accent_color), accent_color, 0.28)
        btn_text = Theme.mix(text, QColor("#000000" if Theme.get_is_light() else "#ffffff"), 0.0)
        close_btn_bg = "#eceef2" if is_light else "#2f2f2f"
        close_btn_hover_bg = "#e4e8ee" if is_light else "#3a3a3a"
        close_btn_disabled_bg = "#f1f3f6" if is_light else "#262626"
        close_btn_text = text if is_light else "#f2f2f2"
        close_btn_hover_text = text if is_light else "#ffffff"
        close_btn_disabled_text = text_muted if is_light else "#9a9a9a"
        check_svg = (Path(__file__).with_name("web") / "scrollbar_arrows" / "check.svg").as_posix()
        trash_svg_name = "trashcan.svg" if is_light else "trashcan-white.svg"
        trash_svg = (Path(__file__).with_name("web") / "icons" / trash_svg_name).as_posix()
        trash_red_svg = (Path(__file__).with_name("web") / "icons" / "trashcan-red.svg").as_posix()
        trash_disabled_svg = (Path(__file__).with_name("web") / "icons" / "trashcan-gray.svg").as_posix()

        name_font = QFont(self.name_label.font())
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        self._update_name_elision()

        reason_font = QFont(self.reasons_label.font())
        reason_font.setBold(True)
        self.reasons_label.setFont(reason_font)
        self.best_label.setFont(reason_font)

        self.name_label.setStyleSheet(
            f"color: {text}; font-weight: 600; margin: 0px; padding: 0px; border: none; background: transparent;"
        )
        self.header_row.setStyleSheet("background: transparent; border: none;")
        self.clear_btn.setStyleSheet(
            f"""
            QPushButton#compareSlotClearButton {{
                background-color: {close_btn_bg};
                color: {close_btn_text};
                border: 1px solid {btn_border};
                border-radius: 4px;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton#compareSlotClearButton:hover {{
                background-color: {close_btn_hover_bg};
                color: {close_btn_hover_text};
                border-color: {accent_raw};
            }}
            QPushButton#compareSlotClearButton:disabled {{
                background-color: {close_btn_disabled_bg};
                color: {close_btn_disabled_text};
                border-color: {btn_border};
            }}
            """
        )
        self.meta_label.setStyleSheet(
            f"color: {text_muted}; margin: 0px; padding: 0px; border: none; background: transparent;"
        )
        self.reasons_label.setStyleSheet(f"color: {accent_hex}; font-weight: 700;")
        self.best_label.setStyleSheet(f"color: {accent_hex}; font-weight: 700;")
        self._thumb_border_color = border
        self.thumb_frame.setStyleSheet(
            f"background-color: {thumb_bg}; border: 1px solid {border}; border-radius: 10px;"
        )
        self.thumb_wrap.setStyleSheet("background: transparent; border: none;")
        self.thumb_label.setStyleSheet(
            f"background: transparent; color: {text_muted}; border: none; padding: 0px; margin: 0px;"
        )
        button_qss = (
            f"QPushButton {{ background-color: {btn_base}; color: {btn_text}; border: 1px solid {btn_border}; "
            f"border-radius: 8px; padding: 6px 10px; }}"
            f"QPushButton:hover {{ background-color: {btn_hover}; border-color: {btn_border_hover}; }}"
        )
        for button in (self.browse_btn,):
            button.setStyleSheet(button_qss)
        self.delete_btn.setStyleSheet(
            f"""
            QPushButton#compareSlotDeleteButton {{
                background-color: {btn_base};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 6px;
                image: url('{trash_svg}');
            }}
            QPushButton#compareSlotDeleteButton:hover {{
                background-color: {close_btn_hover_bg};
                border-color: #d45a5a;
                padding: 6px;
                image: url('{trash_red_svg}');
            }}
            QPushButton#compareSlotDeleteButton:disabled {{
                background-color: {close_btn_disabled_bg};
                border-color: {btn_border};
                padding: 6px;
                image: url('{trash_disabled_svg}');
            }}
            """
        )
        self._update_thumb_pixmap()
        self.browse_btn.setMinimumWidth(0)
        self.browse_btn.setMaximumWidth(16777215)

        checkbox_qss = (
            f"QCheckBox {{ color: {text_muted}; spacing: 6px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 4px; "
            f"border: 1px solid {btn_border}; background-color: {btn_base}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {accent_raw}; border-color: {accent_raw}; image: url('{check_svg}'); }}"
            f"QCheckBox::indicator:hover {{ border-color: {btn_border_hover}; }}"
        )
        self.keep_toggle.setStyleSheet(checkbox_qss)
        self.delete_toggle.setStyleSheet(checkbox_qss)
        self.best_toggle.setStyleSheet(checkbox_qss)
        self.identical_label.setStyleSheet(f"color: {accent_hex}; font-weight: 700;")
        for widget in (
            self.name_label,
            self.meta_label,
            self.reasons_label,
            self.best_label,
            self.clear_btn,
            self.delete_btn,
            self.thumb_frame,
            self.thumb_label,
            self.keep_toggle,
            self.delete_toggle,
            self.best_toggle,
            self.identical_label,
            self.browse_btn,
            self,
        ):
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception:
                pass

    def _emit_keep_changed(self, checked: bool) -> None:
        path = str(self._entry.get("path") or "")
        if path:
            self.keepToggled.emit(path, bool(checked))

    def _emit_delete_changed(self, checked: bool) -> None:
        path = str(self._entry.get("path") or "")
        if path:
            self.deleteToggled.emit(path, bool(checked))

    def _emit_best_changed(self, checked: bool) -> None:
        path = str(self._entry.get("path") or "")
        if not path:
            return
        self.bestRequested.emit(path, bool(checked))

    def _emit_delete_clicked(self) -> None:
        path = str(self._entry.get("path") or "")
        if path:
            self.deleteRequested.emit(self.slot_name, path)

    def _load_thumb(self, path: str) -> QPixmap | None:
        clean = str(path or "").strip()
        if not clean:
            return None
        reader = QImageReader(clean)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            return None
        return QPixmap.fromImage(image)

    def _update_thumb_pixmap(self) -> None:
        if self._thumb_source_pixmap is None or self._thumb_source_pixmap.isNull():
            self.thumb_label.setPixmap(QPixmap())
            return
        available = self.thumb_label.size()
        if available.width() <= 0 or available.height() <= 0:
            self.thumb_label.setPixmap(self._thumb_source_pixmap)
            return
        self.thumb_label.setPixmap(
            _rounded_preview_pixmap(self._thumb_source_pixmap, available, self._thumb_border_color)
        )

    def _render_entry(self, entry: dict) -> None:
        self._entry = dict(entry or {})
        path = str(self._entry.get("path") or "")
        has_entry = bool(path)
        self.setProperty("empty", not has_entry)
        self.clear_btn.setEnabled(has_entry)
        self.clear_btn.setVisible(has_entry)
        thumb_cursor = Qt.CursorShape.PointingHandCursor if has_entry else Qt.CursorShape.ArrowCursor
        self.thumb_frame.setCursor(thumb_cursor)
        self.thumb_wrap.setCursor(thumb_cursor)
        self.thumb_label.setCursor(thumb_cursor)
        self.style().unpolish(self)
        self.style().polish(self)
        if not has_entry:
            self._set_name_text("Drop image here")
            self._thumb_source_pixmap = None
            self.thumb_label.setPixmap(QPixmap())
            self.thumb_label.setText("Left" if self.slot_name == "left" else "Right")
            self.meta_label.setText("Browse or drag an image from the gallery")
            self.reasons_label.setText("")
            self.best_label.setText("")
            self.keep_toggle.blockSignals(True)
            self.keep_toggle.setChecked(False)
            self.keep_toggle.blockSignals(False)
            self.delete_toggle.blockSignals(True)
            self.delete_toggle.setChecked(False)
            self.delete_toggle.blockSignals(False)
            self.best_toggle.blockSignals(True)
            self.best_toggle.setChecked(False)
            self.best_toggle.blockSignals(False)
            self.best_toggle.setVisible(True)
            self.identical_label.setVisible(False)
            self.delete_btn.setEnabled(False)
            return

        self._set_name_text(str(self._entry.get("name") or Path(path).name))
        self._thumb_source_pixmap = self._load_thumb(path)
        self.thumb_label.setText("")
        self._update_thumb_pixmap()
        self.meta_label.setText(
            "\n".join(
                [
                    part for part in [
                        str(self._entry.get("resolution_text") or ""),
                        " â€¢ ".join(
                            [
                                part for part in [
                                    str(self._entry.get("file_size_text") or ""),
                                    str(self._entry.get("modified_time_text") or ""),
                                ]
                                if part
                            ]
                        ),
                    ]
                    if part
                ]
            )
        )
        reasons = list(self._entry.get("duplicate_category_reasons") or [])[:5]
        self.reasons_label.setText("\n".join(reasons))
        compare_best_in_pair = bool(self._entry.get("compare_best_in_pair"))
        compare_marked_best = bool(self._entry.get("compare_marked_best"))
        compare_best_reason = str(self._entry.get("compare_best_reason") or "").strip()
        is_identical_pair = bool(self._entry.get("compare_identical_pair"))
        self.best_toggle.setVisible(not is_identical_pair)
        self.identical_label.setVisible(is_identical_pair)
        if is_identical_pair:
            self.best_label.setText("")
        elif compare_best_in_pair and compare_marked_best:
            self.best_label.setText("\u2605 Best Overall")
        elif compare_best_in_pair:
            self.best_label.setText(f"\u2605 Wins this comparison: {compare_best_reason}" if compare_best_reason else "\u2605 Best in Comparison")
        elif compare_marked_best:
            self.best_label.setText("\u2605 Best Overall")
        else:
            self.best_label.setText("")
        self.keep_toggle.blockSignals(True)
        self.keep_toggle.setChecked(bool(self._entry.get("compare_keep_checked")))
        self.keep_toggle.blockSignals(False)
        self.delete_toggle.blockSignals(True)
        self.delete_toggle.setChecked(bool(self._entry.get("compare_delete_checked")))
        self.delete_toggle.blockSignals(False)
        self.best_toggle.blockSignals(True)
        self.best_toggle.setChecked(bool(self._entry.get("compare_marked_best")))
        self.best_toggle.blockSignals(False)
        self.delete_btn.setEnabled(True)

    def set_entry(self, entry: dict) -> None:
        self._render_entry(entry)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-medialens-compare-slot"):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-medialens-compare-slot"):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasFormat("application/x-medialens-compare-slot"):
            source_slot = bytes(event.mimeData().data("application/x-medialens-compare-slot")).decode("utf-8", errors="ignore")
            if source_slot and source_slot != self.slot_name:
                self.slotSwapRequested.emit(source_slot, self.slot_name)
                event.acceptProposedAction()
                return
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local = url.toLocalFile()
                if local:
                    self.slotPathDropped.emit(self.slot_name, local)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if str(self._entry.get("path") or ""):
                self._drag_start_pos = event.position().toPoint()
            self.isolateRequested.emit(self.slot_name)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_start_pos is not None
            and str(self._entry.get("path") or "")
            and (event.position().toPoint() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance()
        ):
            self.swapStarted.emit()
            mime = QMimeData()
            mime.setData("application/x-medialens-compare-slot", self.slot_name.encode("utf-8"))
            mime.setUrls([QUrl.fromLocalFile(str(self._entry.get("path") or ""))])
            drag = QDrag(self)
            drag.setMimeData(mime)
            thumb = self.thumb_label.pixmap()
            if thumb is not None and not thumb.isNull():
                drag.setPixmap(thumb)
            drag.exec(Qt.DropAction.MoveAction)
            self._drag_start_pos = None
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start_pos = None
        self.isolateReleased.emit()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        self._update_thumb_pixmap()
        self._update_name_elision()
        super().resizeEvent(event)


class ElidedInfoLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self._full_text: str = ""
        self.setWordWrap(False)
        self.setText(text)

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = str(text or "")
        self._apply_elision()
        self.updateGeometry()

    def minimumSizeHint(self) -> QSize:
        metrics = QFontMetrics(self.font())
        margins = self.contentsMargins()
        line_count = max(1, len(self._full_text.splitlines()) or 1)
        height = metrics.lineSpacing() * line_count + margins.top() + margins.bottom()
        return QSize(0, height)

    def sizeHint(self) -> QSize:
        return self.minimumSizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_elision()

    def _apply_elision(self) -> None:
        metrics = QFontMetrics(self.font())
        available_width = self.contentsRect().width()
        full_lines = self._full_text.splitlines() or [""]
        if available_width <= 0:
            display_text = "\n".join(full_lines)
        else:
            display_text = "\n".join(
                metrics.elidedText(line, Qt.TextElideMode.ElideRight, available_width)
                for line in full_lines
            )
        super().setText(display_text)
        full_text = "\n".join(full_lines).strip()
        self.setToolTip(full_text if full_text and display_text != "\n".join(full_lines) else "")


class ComparePanel(QWidget):
    def __init__(self, bridge: "Bridge", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self.setObjectName("comparePanel")
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.left_slot = CompareSlotCard("left")
        self.viewer = CompareRevealViewer()
        self.right_slot = CompareSlotCard("right")
        self._viewer_hint_text = "Zoom to cursor location with mouse scroll wheel"
        self._viewer_upscale_text = ""
        self._viewer_aspect_text = ""
        self.viewer_hint = ElidedInfoLabel("Zoom to cursor location with mouse scroll wheel")
        self.viewer_hint.setObjectName("compareViewerHint")
        self.viewer_hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.viewer_hint.setMinimumWidth(0)
        self.viewer_hint.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.viewer_upscale_warning = ElidedInfoLabel("")
        self.viewer_upscale_warning.setObjectName("compareViewerUpscaleWarning")
        self.viewer_upscale_warning.setMinimumWidth(0)
        self.viewer_upscale_warning.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.viewer_upscale_warning.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.viewer_upscale_warning.setVisible(False)
        self.viewer_aspect_warning = ElidedInfoLabel("")
        self.viewer_aspect_warning.setObjectName("compareViewerAspectWarning")
        self.viewer_aspect_warning.setMinimumWidth(0)
        self.viewer_aspect_warning.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.viewer_aspect_warning.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.viewer_aspect_warning.setVisible(False)
        self.left_scroll = QScrollArea()
        self.right_scroll = QScrollArea()
        self.viewer_wrap = QWidget()
        self.viewer_footer = QWidget()
        self.viewer_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.viewer_footer.setMinimumHeight(54)
        footer_layout = QVBoxLayout(self.viewer_footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(4)
        footer_layout.addWidget(self.viewer_hint, 0)
        footer_layout.addWidget(self.viewer_upscale_warning, 0)
        footer_layout.addWidget(self.viewer_aspect_warning, 0)
        viewer_layout = QVBoxLayout(self.viewer_wrap)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(8)
        viewer_layout.addWidget(self.viewer, 1)
        viewer_layout.addWidget(self.viewer_footer, 0)
        for scroll, slot in ((self.left_scroll, self.left_slot), (self.right_scroll, self.right_slot)):
            scroll.setWidget(slot)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setMinimumHeight(0)
            scroll.setMinimumWidth(0)
            scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.viewer_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(self.left_scroll, 0)
        layout.addWidget(self.viewer_wrap, 1)
        layout.addWidget(self.right_scroll, 0)

        for slot in (self.left_slot, self.right_slot):
            slot.slotPathDropped.connect(self.bridge.set_compare_path)
            slot.slotSwapRequested.connect(self.bridge.swap_compare_slots)
            slot.browseRequested.connect(self._browse_for_slot)
            slot.clearRequested.connect(self.bridge.clear_compare_slot)
            slot.deleteRequested.connect(self._delete_compare_path)
            slot.isolateRequested.connect(self.viewer.set_isolated_slot)
            slot.isolateReleased.connect(lambda: self.viewer.set_isolated_slot(""))
            slot.swapStarted.connect(lambda: self.viewer.set_isolated_slot(""))
            slot.keepToggled.connect(self._set_compare_keep_path)
            slot.deleteToggled.connect(self._set_compare_delete_path)
            slot.bestRequested.connect(self._set_compare_best_path)

        self.bridge.compareStateChanged.connect(self._apply_compare_state)
        self.bridge.accentColorChanged.connect(self._on_accent_changed)
        self._apply_compare_state(self.bridge.get_compare_state())
        self._on_accent_changed(str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))

    @staticmethod
    def _entry_dims(entry: dict) -> tuple[int, int]:
        width = int(entry.get("width") or 0)
        height = int(entry.get("height") or 0)
        return width, height

    def _compare_upscale_message_from_entries(self, left_entry: dict, right_entry: dict) -> str:
        left_w, left_h = self._entry_dims(left_entry)
        right_w, right_h = self._entry_dims(right_entry)
        if left_w <= 0 or left_h <= 0 or right_w <= 0 or right_h <= 0:
            return self.viewer.upscale_match_message()
        left_area = left_w * left_h
        right_area = right_w * right_h
        if left_area <= 0 or right_area <= 0 or left_area == right_area:
            return ""
        return "Upscaled Left to match" if left_area < right_area else "Upscaled Right to match"

    def _has_different_aspect_ratios_from_entries(self, left_entry: dict, right_entry: dict) -> bool:
        left_w, left_h = self._entry_dims(left_entry)
        right_w, right_h = self._entry_dims(right_entry)
        if left_w <= 0 or left_h <= 0 or right_w <= 0 or right_h <= 0:
            return self.viewer.has_different_aspect_ratios()
        tolerance_px = 2.0
        scaled_right_height = right_h * (left_w / max(1, right_w))
        scaled_right_width = right_w * (left_h / max(1, right_h))
        scaled_left_height = left_h * (right_w / max(1, left_w))
        scaled_left_width = left_w * (right_h / max(1, left_h))
        return not (
            abs(left_h - scaled_right_height) <= tolerance_px
            or abs(left_w - scaled_right_width) <= tolerance_px
            or abs(right_h - scaled_left_height) <= tolerance_px
            or abs(right_w - scaled_left_width) <= tolerance_px
        )

    def _update_viewer_footer_labels(self) -> None:
        self.viewer_hint.setText(self._viewer_hint_text)
        self.viewer_upscale_warning.setText(self._viewer_upscale_text)
        self.viewer_aspect_warning.setText(self._viewer_aspect_text)
        try:
            self.viewer_footer.updateGeometry()
            self.viewer_footer.adjustSize()
        except Exception:
            pass

    def apply_theme_styles(self, text: str, text_muted: str, accent_hex: str, accent_raw: str, thumb_bg: str, border: str) -> None:
        for slot in (self.left_slot, self.right_slot):
            slot.apply_theme_styles(text, text_muted, accent_hex, accent_raw, thumb_bg, border)
        scrollbar_style = (
            "QScrollArea { background: transparent; border: none; }"
            "QWidget { background: transparent; }"
        )
        self.left_scroll.setStyleSheet(scrollbar_style)
        self.right_scroll.setStyleSheet(scrollbar_style)
        self.viewer.set_frame_style(thumb_bg, border)
        self.viewer.setStyleSheet("background: transparent; border: none;")
        self.viewer_hint.setStyleSheet(
            f"color: {text_muted}; background: transparent; border: none;"
        )
        warning_style = f"color: {accent_hex}; font-weight: 700; background: transparent; border: none;"
        self.viewer_upscale_warning.setStyleSheet(warning_style)
        self.viewer_aspect_warning.setStyleSheet(warning_style)
        self._update_viewer_footer_labels()
        try:
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        except Exception:
            pass

    @Slot(str)
    def _on_accent_changed(self, accent_color: str) -> None:
        accent = QColor(str(accent_color or Theme.ACCENT_DEFAULT))
        text = Theme.get_text_color()
        text_muted = Theme.get_text_muted()
        accent_text = Theme.mix(text, accent, 0.76)
        thumb_bg = Theme.get_control_bg(accent)
        thumb_border = Theme.get_border(accent)
        self.apply_theme_styles(text, text_muted, accent_text, accent.name(), thumb_bg, thumb_border)
        for widget in (self.left_slot, self.right_slot, self.viewer):
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
                widget.repaint()
            except Exception:
                pass

    def _browse_for_slot(self, slot_name: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose image to compare",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg *.tif *.tiff *.avif *.heic *.heif)",
        )
        if path:
            self.bridge.set_compare_path(slot_name, path)

    def _delete_compare_path(self, slot_name: str, path: str) -> None:
        if self.bridge.delete_path(path):
            self.bridge.clear_compare_slot(slot_name)

    def _set_compare_keep_path(self, path: str, checked: bool) -> None:
        self.bridge.set_compare_keep_path(path, checked)
        self.bridge.compareKeepPathChanged.emit(str(path or ""), bool(checked))

    def _set_compare_delete_path(self, path: str, checked: bool) -> None:
        self.bridge.set_compare_delete_path(path, checked)
        self.bridge.compareDeletePathChanged.emit(str(path or ""), bool(checked))

    def _set_compare_best_path(self, path: str, checked: bool) -> None:
        def _apply_best_toggle_selection(chosen_path: str) -> None:
            target = str(chosen_path or "")
            for slot in (self.left_slot, self.right_slot):
                slot_path = str(getattr(slot, "_entry", {}).get("path") or "")
                slot.best_toggle.blockSignals(True)
                slot.best_toggle.setChecked(bool(target) and slot_path == target)
                slot.best_toggle.blockSignals(False)
                slot.best_toggle.update()
                slot.best_toggle.repaint()

        if checked:
            chosen = str(path or "")
            _apply_best_toggle_selection(chosen)
            self.bridge.set_compare_best_path(path)
            self.bridge.compareBestPathChanged.emit(chosen, True)
        else:
            current_best = str(self.bridge.get_compare_state().get("best_path") or "")
            if current_best == str(path or ""):
                _apply_best_toggle_selection("")
                self.bridge.clear_compare_best_path()
                self.bridge.compareBestPathChanged.emit(str(path or ""), False)

    @Slot("QVariantMap")
    def _apply_compare_state(self, state: dict) -> None:
        payload = dict(state or {})
        left_entry = dict(payload.get("left") or {})
        right_entry = dict(payload.get("right") or {})
        has_viewer_image = bool(str(left_entry.get("path") or "").strip() or str(right_entry.get("path") or "").strip())
        self.left_slot.set_entry(left_entry)
        self.right_slot.set_entry(right_entry)
        self.viewer.set_images(str(left_entry.get("path") or ""), str(right_entry.get("path") or ""))
        self._viewer_upscale_text = self._compare_upscale_message_from_entries(left_entry, right_entry)
        self._viewer_aspect_text = "Different Aspect Ratios" if self._has_different_aspect_ratios_from_entries(left_entry, right_entry) else ""
        try:
            self.bridge._log(
                "Compare warnings: "
                f"left_path='{left_entry.get('path')}' "
                f"right_path='{right_entry.get('path')}' "
                f"left={left_entry.get('width')}x{left_entry.get('height')} "
                f"right={right_entry.get('width')}x{right_entry.get('height')} "
                f"upscale='{self._viewer_upscale_text}' "
                f"aspect='{self._viewer_aspect_text}' "
                f"has_viewer_image={has_viewer_image}"
            )
        except Exception:
            pass
        self._update_viewer_footer_labels()
        self.viewer_hint.setVisible(has_viewer_image)
        self.viewer_upscale_warning.setVisible(bool(self._viewer_upscale_text))
        self.viewer_aspect_warning.setVisible(bool(self._viewer_aspect_text))
        self.viewer_footer.setVisible(
            bool(has_viewer_image)
            or bool(self._viewer_upscale_text)
            or bool(self._viewer_aspect_text)
        )
        try:
            self.bridge._log(
                "Compare warning widgets: "
                f"hint={self.viewer_hint.isVisible()} "
                f"upscale={self.viewer_upscale_warning.isVisible()} "
                f"aspect={self.viewer_aspect_warning.isVisible()} "
                f"footer={self.viewer_footer.isVisible()}"
            )
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_viewer_footer_labels()




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
