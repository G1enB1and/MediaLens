from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import os
from PySide6.QtCore import QEvent, QTimer, Qt, QUrl, QRect, QSize, QPoint, QByteArray
from PySide6.QtGui import QKeySequence, QShortcut, QRegion, QPainterPath, QPixmap, QColor
from PySide6.QtGui import QImage, QPainter, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink, QVideoFrame
from PySide6.QtMultimedia import QVideoFrameFormat
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class VideoRequest:
    path: str
    autoplay: bool
    loop: bool
    muted: bool
    width: int = 0
    height: int = 0


def _settings_ini_path() -> str:
    base = os.getenv("APPDATA")
    if base:
        return str(Path(base) / "MediaLens" / "settings.ini")
    return str(Path.home() / "AppData" / "Roaming" / "MediaLens" / "settings.ini")


class VideoFrameWidget(QWidget):
    """Paints video frames from a QVideoSink.

    This avoids QVideoWidget native-surface stacking issues on Windows.
    """

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._img: QImage | None = None

    def set_image(self, img: QImage | None) -> None:
        self._img = img
        self.update()

    def mousePressEvent(self, event) -> None: # type: ignore[override]
        # Consume the click so it doesn't propagate to the poster/web UI
        event.accept()

    def mouseReleaseEvent(self, event) -> None: # type: ignore[override]
        event.accept()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Do NOT paint black behind the video; let the overlay backdrop show.
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)

        if not self._img or self._img.isNull():
            return

        # Smooth Rounding: Use a clip path for anti-aliased corners
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 8, 8)
        p.setClipPath(path)

        # Fit while preserving aspect ratio.
        target = self.rect()
        src = self._img.size()
        scaled = src.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatio)
        
        # Center within the widget
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        
        target_rect = QRect(x, y, scaled.width(), scaled.height())
        if not target_rect.isEmpty():
            p.drawImage(target_rect, self._img)


class LightboxVideoOverlay(QWidget):
    """Native video overlay that sits above the WebEngine view.

    Rationale: QtWebEngine video codec support can be unreliable on Windows.
    We render the *lightbox chrome* in the web UI, but render the video itself
    with QtMultimedia so playback works.

    This widget is designed to cover the WebEngine viewport.

    Signals are kept minimal: callers can observe close to sync the web layer.
    """

    # Caller can connect to this to close the web lightbox chrome.
    # (We avoid importing Signal here to keep this file simple; use callback pattern.)

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setVisible(False)

        # Optional close/nav callbacks (set by owner)
        self.on_close = None
        self.on_prev = None
        self.on_next = None
        self.on_log = None

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setMuted(True)
        self.player.setAudioOutput(self.audio)

        self.backdrop = QFrame(self)
        self.backdrop.setStyleSheet("background: rgba(0,0,0,190);")

        # Use QVideoSink + custom painter to avoid QVideoWidget stacking/input
        # issues on Windows (where controls may never appear).
        self.video_sink = QVideoSink(self)
        self.video_sink.videoFrameChanged.connect(self._on_frame)
        self.player.setVideoOutput(self.video_sink)

        self.video_view = VideoFrameWidget(parent=self)
        self.video_view.setMouseTracking(True)
        self.video_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Controls overlay as sibling above video_view
        self.controls = QWidget(self)
        self.controls.setStyleSheet("background: transparent; border: none;")
        self.controls.setVisible(False)

        # Glassy dark background only for the bottom control bar
        self.controls_bg = QFrame(self.controls)
        self.controls_bg.lower()

        self.btn_prev = QPushButton("", self.controls)
        self.btn_toggle_play = QPushButton("", self.controls)
        self.btn_next = QPushButton("", self.controls)
        self.btn_prev.setVisible(False) # Hide as not requested
        self.btn_next.setVisible(False) # Hide as not requested
        self.btn_mute = QPushButton("", self.controls)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal, self.controls)

        # Create a pill background for volume controls
        self.vol_pill = QFrame(self.controls)
        self.vol_pill.setStyleSheet(
            "background: rgba(40, 40, 45, 180);"
            "border-radius: 20px;" # Pill shape
        )
        self.vol_pill.lower()
        self.vol_pill.setVisible(False)
        
        self.lbl_time = QLabel("0:00 / 0:00", self.controls)
        self.lbl_dbg = QLabel("", self.controls)
        self.slider = QSlider(Qt.Orientation.Horizontal, self.controls)

        self.btn_prev.setToolTip("Previous (←)")
        self.btn_next.setToolTip("Next (→)")
        self.btn_toggle_play.setToolTip("Play/Pause (Space)")
        self.btn_mute.setToolTip("Mute")

        self.slider.setRange(0, 0)
        self.slider.setSingleStep(1000)
        self.slider.setPageStep(5000)

        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.setToolTip("Volume")

        btn_css = (
            "QPushButton {"
            " color: rgba(255,255,255,230);"
            " background: transparent;"
            " border: none;"
            " padding: 6px 10px;"
            " font-size: 16px;"
            " }"
            "QPushButton:hover {"
            " background: rgba(255,255,255,22);"
            " border-radius: 10px;"
            " }"
        )
        for b in (self.btn_prev, self.btn_next, self.btn_mute):
            b.setStyleSheet(btn_css)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Icons are loaded dynamically in set_mode
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "icons")
        self.icon_play = QIcon(os.path.join(icon_dir, "play.svg"))
        self.icon_pause = QIcon(os.path.join(icon_dir, "pause.svg"))
        self.icon_prev = QIcon(os.path.join(icon_dir, "prev.svg"))
        self.icon_next = QIcon(os.path.join(icon_dir, "next.svg"))
        self.icon_mute_on = QIcon(os.path.join(icon_dir, "mute_on.svg"))
        self.icon_mute_off = QIcon(os.path.join(icon_dir, "mute_off.svg"))

        self.btn_prev.setIcon(self.icon_prev)
        self.btn_next.setIcon(self.icon_next)
        self.btn_mute.setIcon(self.icon_mute_on)

        for b in (self.btn_prev, self.btn_next, self.btn_mute):
            b.setIconSize(QSize(22, 22))
        self.btn_toggle_play.clicked.connect(self._on_toggle_play_clicked)
        self.btn_toggle_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_play.installEventFilter(self)
        self.btn_toggle_play.setFixedSize(52, 52)
        self.btn_toggle_play.setIconSize(QSize(24, 24))
        self.btn_toggle_play.setIcon(self.icon_play)
        # Style will be set in set_mode

        self.lbl_time.setStyleSheet("color: rgba(255,255,255,170); font-size: 12px;")
        # Debug label hidden by default
        self.lbl_dbg.setStyleSheet("color: rgba(255,80,80,220); font-size: 11px;")
        self.lbl_dbg.setVisible(False)

        self.slider.setParent(self.controls)
        self.vol_slider.setParent(self.controls)
        
        self._is_inplace = False
        self._apply_theme()

        self.btn_prev.clicked.connect(self._on_prev_clicked)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.btn_mute.clicked.connect(self._toggle_mute)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)

        # Wire up volume slider hover visibility
        self.btn_mute.installEventFilter(self)
        self.vol_slider.installEventFilter(self)
        self.vol_slider.setVisible(False)

        self.slider.sliderPressed.connect(self._on_seek_start)
        self.slider.sliderReleased.connect(self._on_seek_commit)

        # Stacking order: backdrop (bottom), video_view, controls (top)
        self.backdrop.lower()
        self.video_view.raise_()
        self.controls.raise_()

        # We will use manual positioning in resizeEvent to achieve perfect centering
        # of the play button and bottom anchoring of the seek bar.
        # So we don't need the QVBoxLayout for the entire controls widget.
        self.btn_prev.setParent(self.controls)
        self.btn_toggle_play.setParent(self.controls)
        self.btn_next.setParent(self.controls)
        self.btn_mute.setParent(self.controls)
        self.slider.setParent(self.controls)
        self.vol_slider.setParent(self.controls)
        self.lbl_time.setParent(self.controls)
        self.lbl_dbg.setParent(self.controls)

        # No layout: we position children manually in resizeEvent.
        self.backdrop.setGeometry(self.rect())
        self.video_view.setGeometry(self.rect())

        # Put the video surface above the backdrop using stacking
        self.backdrop.lower()
        self.video_view.raise_()
        self.controls.raise_()

        # Track seek state
        self._seeking = False

        # Auto-hide controls
        self._hide_timer = QTimer(self)
        self._hide_timer.setInterval(1000)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_controls)

        # Volume slider visibility timer
        self._vol_hide_timer = QTimer(self)
        self._vol_hide_timer.setInterval(300)
        self._vol_hide_timer.setSingleShot(True)
        self._vol_hide_timer.timeout.connect(self._hide_volume_slider)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # Track native video size (for aspect-ratio correct viewport)
        self._native_size: QSize | None = None

        # Clicking backdrop closes
        self.backdrop.installEventFilter(self)

        # Show controls when mouse moves over the video surface
        self.video_view.installEventFilter(self)
        self.controls.installEventFilter(self)

        # Shortcuts
        QShortcut(QKeySequence("Escape"), self, activated=self.close_overlay)
        QShortcut(QKeySequence("Space"), self, activated=self._on_toggle_play_clicked)

        self._loop = False
        self._current_source = ""
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def _log(self, message: str) -> None:
        try:
            if callable(self.on_log):
                self.on_log(message)
        except Exception:
            pass
        try:
            print(message)
        except Exception:
            pass

    def _is_light(self) -> bool:
        from PySide6.QtCore import QSettings
        settings = QSettings(_settings_ini_path(), QSettings.Format.IniFormat)
        val = settings.value("ui/theme_mode", "dark")
        return str(val).lower() == "light"

    def _apply_theme(self) -> None:
        from PySide6.QtCore import QSettings
        settings = QSettings(_settings_ini_path(), QSettings.Format.IniFormat)
        accent_hex = str(settings.value("ui/accent_color", "#8ab4f8"))
        if not accent_hex.startswith("#"):
            accent_hex = "#8ab4f8"
        try:
            r = int(accent_hex[1:3], 16)
            g = int(accent_hex[3:5], 16)
            b = int(accent_hex[5:7], 16)
        except ValueError:
            r, g, b = 138, 180, 248 # fallback
        bg = f"rgba({r}, {g}, {b}, 200)"
        
        self.slider_css_full_width = (
            "QSlider::groove:horizontal { height: 6px; background: rgba(255, 255, 255, 40); border: 0; margin: 0; }\n"
            f"QSlider::sub-page:horizontal {{ background: {bg}; border: 0; margin: 0; }}\n"
            "QSlider::add-page:horizontal { background: rgba(0, 0, 0, 80); border: 0; margin: 0; }\n"
            "QSlider::handle:horizontal { width: 4px; background: white; border-radius: 2px; margin: 0; }"
        )
        is_light = self._is_light()
        groove_bg = "rgba(0,0,0,40)" if is_light else "rgba(255,255,255,35)"
        add_page_bg = "rgba(0,0,0,20)" if is_light else "rgba(255,255,255,25)"
        handle_bg = "white" # High contrast white handle

        self.vol_slider_css = (
            f"QSlider::groove:horizontal {{ height: 4px; background: {groove_bg}; border-radius: 2px; }}\n"
            f"QSlider::sub-page:horizontal {{ background: {bg}; border-radius: 2px; }}\n"
            f"QSlider::add-page:horizontal {{ background: {add_page_bg}; border-radius: 2px; }}\n"
            f"QSlider::handle:horizontal {{ width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: {handle_bg}; }}"
        )
        
        self.slider.setStyleSheet(self.slider_css_full_width + "border: 0; padding: 0; margin: 0;")
        self.vol_slider.setStyleSheet(self.vol_slider_css + "min-width: 80px;")
        
        # Transparent background for containers
        self.controls.setStyleSheet("background: transparent; border: none;")
        self.controls_bg.setStyleSheet("background: transparent; border: none;")

    def set_mode(self, is_inplace: bool) -> None:
        """Toggles between standard Lightbox mode and In-Place gallery mode."""
        self._is_inplace = is_inplace
        self.backdrop.setVisible(not is_inplace)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.video_view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Show/Hide specific buttons for mini mode
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.lbl_time.setVisible(not is_inplace)
        self.slider.setVisible(True)

        is_light = self._is_light()
        btn_bg = "rgba(255, 255, 255, 115)" if is_light else "rgba(0, 0, 0, 115)"
        icon_color = "black" if is_light else "white"
        border = "rgba(0, 0, 0, 40)" if is_light else "rgba(255, 255, 255, 40)"

        is_light = self._is_light()
        icon_color_hex = "white" # Always white for shadowed look
        icon_color_qss = "white"
        
        btn_bg = "rgba(255, 255, 255, 115)" if is_light else "rgba(0, 0, 0, 115)"
        btn_border_inner = "white" if is_light else "black"
        
        # Programmatically update icons with drop shadows
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "icons")
        from PySide6.QtGui import QColor

        def load_shadowed(name: str) -> QIcon:
            path = os.path.join(icon_dir, f"{name}.svg")
            if not os.path.exists(path): return QIcon()
            # 1. Load original white icon
            base_pixmap = QPixmap(path)
            if base_pixmap.isNull(): return QIcon()
            
            # 2. Create larger canvas for centered glow (6px padding on all sides)
            size = base_pixmap.size()
            shadowed = QPixmap(size.width() + 12, size.height() + 12)
            shadowed.fill(Qt.GlobalColor.transparent)
            
            p = QPainter(shadowed)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Prepare shadow mask (solid black)
            shadow_mask = QPixmap(base_pixmap.size())
            shadow_mask.fill(Qt.GlobalColor.transparent)
            p2 = QPainter(shadow_mask)
            p2.drawPixmap(0,0, base_pixmap)
            p2.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p2.fillRect(shadow_mask.rect(), QColor(0, 0, 0, 255))
            p2.end()
            
            # 3. Draw multi-layered symmetrical halo (no offset)
            # Centered at (6,6) relative to (0,0)
            glow_layers = [
                (6, 6, 0.45), # Center core
                (5.5, 6, 0.3), (6.5, 6, 0.3), (6, 5.5, 0.3), (6, 6.5, 0.3),
                (5, 6, 0.2), (7, 6, 0.2), (6, 5, 0.2), (6, 7, 0.2),
                (5, 5, 0.15), (7, 7, 0.15), (5, 7, 0.15), (7, 5, 0.15),
                (4.5, 6, 0.1), (7.5, 6, 0.1), (6, 4.5, 0.1), (6, 7.5, 0.1)
            ]
            for dx, dy, opacity in glow_layers:
                p.setOpacity(opacity)
                p.drawPixmap(dx, dy, shadow_mask)
            
            # 4. Draw original white icon at 6,6
            p.setOpacity(1.0)
            p.drawPixmap(6, 6, base_pixmap)
            p.end()
            return QIcon(shadowed)

        self.icon_play = load_shadowed("play")
        self.icon_pause = load_shadowed("pause")
        self.icon_mute_on = load_shadowed("mute_on")
        self.icon_mute_off = load_shadowed("mute_off")
        
        # Update current icons
        self.btn_mute.setIcon(self.icon_mute_on if self.audio.isMuted() else self.icon_mute_off)
        self._update_controls_ui(self.player.playbackState()) # Refreshes play/pause icon

        btn_qss = (
            "QPushButton {"
            f"  background: {btn_bg};"
            f"  border: 1px solid {btn_border_inner};"
            "  border-radius: 26px;"
            f"  color: {icon_color_qss};"
            "  padding: 0;"
            "}"
        )
        
        self.mute_qss_standalone = (
            "QPushButton {"
            f"  background: {btn_bg};"
            f"  border: 1px solid {btn_border_inner};"
            "  border-radius: 18px;"
            f"  color: {icon_color_qss};"
            "  padding: 0;"
            "}"
        )
        self.mute_qss_pill = (
            "QPushButton {"
            "  background: transparent;" # Blend with pill
            f"  border: 1px solid {btn_border_inner};"
            "  border-radius: 18px;"
            f"  color: {icon_color_qss};"
            "  padding: 0;"
            "}"
        )
        
        pill_bg = btn_bg 
        pill_border = f"1px solid {btn_border_inner}"
        self.vol_pill.setStyleSheet(f"background: {pill_bg}; border: {pill_border}; border-radius: 20px;")

        if is_inplace:
            self.controls_bg.setStyleSheet("background: transparent; border: none;")
            self.btn_toggle_play.setStyleSheet(btn_qss)
            self.btn_toggle_play.setFixedSize(52, 52)
            self.btn_mute.setStyleSheet(self.mute_qss_standalone)
            self.btn_mute.setFixedSize(36, 36)
            self.slider.setVisible(True)
            self._apply_theme()
            self.controls.setMinimumHeight(0)
            self.controls.setMaximumHeight(16777215)
        else:
            self.controls_bg.setStyleSheet(
                "background: rgba(20,20,26,190);"
                "border-top: 1px solid rgba(255,255,255,30);"
            )
            self.btn_toggle_play.setStyleSheet(btn_qss) 
            self.btn_mute.setStyleSheet(self.mute_qss_standalone)
            self._apply_theme()
            self.slider.setVisible(True)
            self.lbl_time.setVisible(True)
            self.controls.setMinimumHeight(0)
            self.controls.setMaximumHeight(16777215)
        
        self.resizeEvent(None)
        self._show_controls()

    def is_inplace_mode(self) -> bool:
        return self._is_inplace

    def _update_mask(self):
        pass

    def set_muted(self, muted: bool) -> None:
        self.audio.setMuted(muted)
        self.btn_mute.setIcon(self.icon_mute_off if muted else self.icon_mute_on)

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if (obj is self or obj is self.backdrop or obj is self.video_view) and event.type() == QEvent.Type.MouseButtonPress:
            if not self._is_inplace:
                self.close_overlay()
                return True
        
        if obj is self.btn_toggle_play:
            if event.type() == QEvent.Type.Enter:
                self.btn_toggle_play.setFixedSize(58, 58)
                self.btn_toggle_play.setStyleSheet(self.btn_toggle_play.styleSheet().replace("border-radius: 26px;", "border-radius: 29px;"))
                self.resizeEvent(None)
                return False
            if event.type() == QEvent.Type.Leave:
                self.btn_toggle_play.setFixedSize(52, 52)
                self.btn_toggle_play.setStyleSheet(self.btn_toggle_play.styleSheet().replace("border-radius: 29px;", "border-radius: 26px;"))
                self.resizeEvent(None)
                return False

        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            if obj is self.video_view or obj is self.controls:
                self._show_controls()
            
            if obj is self.btn_mute or obj is self.vol_slider:
                self._show_volume_slider()
        
        if event.type() == QEvent.Type.Leave:
            if obj is self.btn_mute or obj is self.vol_slider:
                self._vol_hide_timer.start()
        
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and not self._is_inplace:
            self.close_overlay()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        self._show_controls()
        super().mouseMoveEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        # No delay on enter, but we wait for movement to really show?
        # User said "appear instantly with any movement over the image or video".
        # So we don't show on enter, we show on move.
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        # Hide immediately when leaving the video player area,
        # unless we are over a specific control.
        if not self._is_over_any_control():
            self._hide_controls_immediate()
            self._hide_volume_slider_immediate()
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Space:
            self._on_toggle_play_clicked()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.close_overlay()
            event.accept()
            return
        super().keyPressEvent(event)

    def _compute_video_rect(self) -> QRect:
        pad = 0
        bounds = self.rect().adjusted(pad, pad, -pad, -pad)

        # In inplace mode the overlay widget is already sized to the gallery card,
        # which has the correct aspect-ratio from DB metadata.  Just fill the whole
        # card — doing a second aspect-ratio fit here would produce the wrong size
        # whenever _native_size is stale between sessions (race condition).
        if self._is_inplace:
            return bounds

        if not self._native_size or self._native_size.width() <= 0 or self._native_size.height() <= 0:
            return bounds

        vw = float(self._native_size.width())
        vh = float(self._native_size.height())
        target_w = bounds.width()
        target_h = bounds.height()

        # Fit rect preserving aspect ratio (lightbox mode only)
        scale = min(target_w / vw, target_h / vh)
        w = max(1, int(vw * scale))
        h = max(1, int(vh * scale))

        x = bounds.x() + (bounds.width() - w) // 2
        y = bounds.y() + (bounds.height() - h) // 2
        return QRect(x, y, w, h)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        if event:
            super().resizeEvent(event)
        
        self.backdrop.setGeometry(self.rect())
        r = self._compute_video_rect()
        self.video_view.setGeometry(r)

        # The controls container always covers the entire video area now
        # to allow centering the play button and top-left alignment of volume.
        self.controls.setGeometry(r)
        
        cw = self.controls.width()
        ch = self.controls.height()
        
        # 1. Play/Pause Toggle: Perfect Center
        pw, ph = self.btn_toggle_play.width(), self.btn_toggle_play.height()
        self.btn_toggle_play.setGeometry((cw - pw) // 2, (ch - ph) // 2, pw, ph)
        
        # 2. Volume Controls: Top-Left with 25px margin
        margin = 25
        mw, mh = self.btn_mute.width(), self.btn_mute.height()
        vw_vol, vh_vol = self.vol_slider.width(), self.vol_slider.height()
        
        # Position speaker icon (perfectly flush left with pill's 2px inner padding)
        self.btn_mute.setGeometry(margin + 2, margin + (40 - mh) // 2, mw, mh)
        
        # Position pill behind them
        pill_w = mw + 10 + (vw_vol + 10 if self.vol_slider.isVisible() else 0)
        pill_h = 40
        self.vol_pill.setGeometry(margin, margin, pill_w, pill_h)
        self.vol_pill.lower()
        
        # Position volume slider relative to mute
        self.vol_slider.setGeometry(margin + mw + 10, margin + (pill_h - vh_vol) // 2, vw_vol, vh_vol)
        
        # 3. Track Bar: Bottom, 0 margin, full width
        seek_h = 6 
        self.slider.setGeometry(0, ch - seek_h, cw, seek_h)
        
        # 4. Time Label: Positioned above the track bar on the right
        time_w = 85
        time_h = 20
        self.lbl_time.setGeometry(cw - time_w - 10, ch - seek_h - time_h - 10, time_w, time_h)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # 5. Controls Background: We'll use a subtle gradient or transparent
        self.controls_bg.setGeometry(self.controls.rect())
        self.controls_bg.lower()

        self._update_mask()


        # Keep stacking order consistent
        self.backdrop.lower()
        self.video_view.raise_()
        self.controls.raise_()

    def open_video(self, req: VideoRequest) -> None:
        path = str(Path(req.path))
        self._log(f"Video Overlay Opening: {path} ({req.width}x{req.height})")
        
        self._loop = bool(req.loop)
        self.audio.setMuted(bool(req.muted))
        self.btn_mute.setIcon(self.icon_mute_off if req.muted else self.icon_mute_on)

        if req.width > 0 and req.height > 0:
            self._native_size = QSize(int(req.width), int(req.height))
        else:
            self._native_size = None

        # Reset preprocessing status label
        self.lbl_dbg.setVisible(False)

        # Sync volume slider
        self.vol_slider.setValue(int(self.audio.volume() * 100))

        try:
            self.player.stop()
            self.player.positionChanged.disconnect()
            self.player.durationChanged.disconnect()
            self.player.playbackStateChanged.disconnect()
            self.player.errorOccurred.disconnect()
            self.player.mediaStatusChanged.disconnect()
            self.player.deleteLater()
            self.audio.deleteLater()
        except Exception:
            pass

        # Completely recreate the QMediaPlayer and QAudioOutput instances to flush
        # Qt's internal FFmpeg demuxer cache, ensuring rotated files are read freshly
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_sink)
        
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        
        self.audio.setVolume(self.vol_slider.value() / 100.0)
        self.audio.setMuted(bool(req.muted))
        
        # Looping support varies by Qt version.
        if hasattr(self.player, "setLoops"):
            try:
                self.player.setLoops(-1 if req.loop else 1)
            except Exception:
                pass

        self.player.setSource(QUrl.fromLocalFile(path))
        self.setVisible(True)
        self.video_view.setVisible(True)
        self.backdrop.setVisible(True)
        self.raise_()
        self.video_view.raise_()
        self.controls.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.video_view.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

        # Force controls visible on open.
        self._show_controls()
        QTimer.singleShot(0, self.controls.raise_)
        
        if self._is_inplace:
            self.backdrop.hide()

        # Kick the backend so we get the first frame even for non-autoplay.
        self._first_frame_received = False
        self._auto_pause_needed = not req.autoplay
        self.player.play()
        
        # We'll pause in _on_frame once the first frame actually arrives.
        # But we still need a safety timeout in case the video is broken.
        if self._auto_pause_needed:
             QTimer.singleShot(2000, self._safety_auto_pause)

        self._playback_started_emitted = False
        self._show_controls()

    def _safety_auto_pause(self) -> None:
        """Fallback pause if no frame arrived within timeout."""
        if hasattr(self, "_auto_pause_needed") and self._auto_pause_needed:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            self._auto_pause_needed = False

    def show_preprocessing_status(self, message: str) -> None:
        """Show the overlay with a status message while preprocessing is running."""
        self.video_view.set_image(None)
        self.lbl_dbg.setText(message)
        self.lbl_dbg.setVisible(True)
        self.setVisible(True)
        self.video_view.setVisible(True)
        self.backdrop.setVisible(True)
        self.raise_()
        self._show_controls()

    def close_overlay(self, notify_web: bool = True) -> None:
        was_visible = self.isVisible()
        try:
            self.player.stop()
            self.player.setSource(QUrl())
        except Exception:
            pass
        self.setVisible(False)
        # Only notify the web layer if we were actually open and requested; 
        # avoids closing image lightboxes when we "stop video" during navigation.
        if was_visible and notify_web and callable(self.on_close):
            try:
                self.on_close()
            except Exception:
                pass

    def _on_frame(self, frame: QVideoFrame) -> None:
        """
        Convert each QVideoFrame into a QImage for painting on the VideoFrameWidget.

        Frame rendering pipeline:
          1. Safety gate: reject frames that would crash the Qt/FFmpeg backend.
          2. Primary path: frame.toImage() — Qt's built-in conversion (fast, coloured).
          3. Fallback path: manual frame.map() + QImage construction from raw bytes.
             Used when toImage() returns null (e.g. for unusual pixel formats).
          4. On success: push the QImage to the VideoFrameWidget for painting.
        """
        # Ignore frames while the media pipeline is not in a valid playing state.
        st = self.player.mediaStatus()
        if st in (
            QMediaPlayer.MediaStatus.NoMedia,
            QMediaPlayer.MediaStatus.LoadingMedia,
            QMediaPlayer.MediaStatus.StalledMedia,
        ):
            return

        if not frame.isValid():
            return

        try:
            pf = frame.pixelFormat()
            raw_w = int(frame.width())
            raw_h = int(frame.height())

            # ── Safety gate ─────────────────────────────────────────────────────────
            # NV12 frames with odd or zero dimensions trigger a swscaler crash deep
            # inside Qt's FFmpeg backend — both toImage() AND map() are unsafe.
            #
            # Root cause: the source MP4 has a malformed codec header (coded_width=0
            # even though the container reports the correct display width). Qt's
            # D3D11 HW decoder reads the coded width, causing swscaler to attempt an
            # impossible "450×797 → 0×797" conversion.
            #
            # Prevention: Bridge._probe_video_size() detects odd dims at open time
            # and routes the video through _preprocess_to_even_dims(), which re-encodes
            # to MJPEG/MKV (software-decoded, no NV12 in the frame pipeline). This
            # guard therefore should never fire for normal usage, but remains as a
            # last-resort safety net.
            is_radioactive = False
            if pf.name == "Format_NV12" and (raw_h % 2 != 0 or raw_w % 2 != 0):
                is_radioactive = True
            if raw_w <= 0 or raw_h <= 0:
                is_radioactive = True

            if is_radioactive:
                # Update UI once, then keep returning silently.
                if not self.lbl_dbg.isVisible():
                    msg = f"Incompatible frame format ({pf.name} {raw_w}×{raw_h})"
                    self._log(f"[VideoOverlay] Radioactive frame blocked: {msg}")
                    self.lbl_dbg.setText(msg)
                    self.lbl_dbg.setVisible(True)
                return

            # ── Working dimensions ───────────────────────────────────────────────────
            # Start from what the frame reports, then apply fallbacks for edge cases.
            w = raw_w
            h = raw_h
            img = None

            # If the frame reports zero dimensions (can happen transiently during
            # pipeline setup), fall back to the probed size from open_video.
            if w <= 0 or h <= 0:
                if hasattr(self, "_native_size") and self._native_size:
                    if w <= 0:
                        w = self._native_size.width()
                    if h <= 0:
                        h = self._native_size.height()
                if w <= 0 or h <= 0:
                    return  # Nothing we can do without a size.

            # NV12 chroma subsampling requires even dimensions; clamp to nearest even.
            if pf.name == "Format_NV12":
                if w % 2 != 0:
                    w -= 1
                if h % 2 != 0:
                    h -= 1

            self._frame_count = getattr(self, "_frame_count", 0) + 1

            # ── Primary path: built-in conversion ───────────────────────────────────
            # frame.toImage() asks Qt's FFmpeg backend to convert the frame to a
            # QImage in a display-ready format (usually ARGB32 or RGB32). This is
            # the fast, full-colour path used for the vast majority of videos.
            if hasattr(frame, "toImage"):
                try:
                    img = frame.toImage()  # type: ignore[attr-defined]
                    if img is not None and img.isNull():
                        img = None  # Treat null images as failure; fall through to map.
                except Exception:
                    img = None

            # ── Fallback path: manual map ────────────────────────────────────────────
            # Used when toImage() returns null (e.g. exotic pixel formats that Qt
            # doesn't convert natively). We manually map the frame's memory and
            # construct a QImage from plane 0 directly.
            #
            # For planar formats (NV12, YUV420P, …) plane 0 is always the luma (Y)
            # channel, so the fallback produces a greyscale-only image. For packed
            # BGRA/RGBA formats it produces a full-colour image.
            if img is None or img.isNull():
                if frame.map(QVideoFrame.MapMode.ReadOnly):
                    try:
                        stride = frame.bytesPerLine(0)
                        real_w = w
                        real_h = h
                        # If stride is narrower than our computed width, trust the stride.
                        if stride > 0 and real_w > stride:
                            real_w = stride

                        if real_w > 0 and real_h > 0:
                            # Choose the QImage pixel format that best matches the frame.
                            qfmt = {
                                QVideoFrameFormat.PixelFormat.Format_BGRA8888: QImage.Format.Format_ARGB32,
                                QVideoFrameFormat.PixelFormat.Format_RGBA8888: QImage.Format.Format_RGBA8888,
                                QVideoFrameFormat.PixelFormat.Format_ARGB8888: QImage.Format.Format_ARGB32,
                                QVideoFrameFormat.PixelFormat.Format_RGBX8888: QImage.Format.Format_RGB32,
                            }.get(pf, QImage.Format.Format_Grayscale8)  # Y-plane fallback

                            bits = frame.bits(0)
                            if bits:
                                # QImage does NOT take ownership of the bits pointer;
                                # .copy() makes a safe owned copy.
                                img = QImage(bits, real_w, real_h, stride, qfmt).copy()
                    except Exception:
                        pass
                    finally:
                        frame.unmap()

            # ── Render ───────────────────────────────────────────────────────────────
            if img is not None and not img.isNull():
                self.lbl_dbg.setText("")
                self.lbl_dbg.setVisible(False)
                self.video_view.set_image(img)
                
                # Signal success to Bridge so JS can hide placeholder
                if not getattr(self, "_playback_started_emitted", False):
                    # We need to find the bridge. Usually it's in the window.
                    win = self.window()
                    if hasattr(win, "bridge"):
                        win.bridge.videoPlaybackStarted.emit()
                        self._playback_started_emitted = True

                # Auto-pause after the first valid frame if the caller requested it
                # (i.e. the video was opened in a non-autoplay state; we play briefly
                # just to get a poster frame, then pause).
                if hasattr(self, "_auto_pause_needed") and self._auto_pause_needed:
                    self.player.pause()
                    self._auto_pause_needed = False
                return

            # All conversion attempts failed — clear the frame widget.
            self.video_view.set_image(None)
            if not self.lbl_dbg.text():
                self.lbl_dbg.setText(f"Unsupported format: {pf.name}")
                self.lbl_dbg.setVisible(True)

        except Exception as e:
            self._log(f"[VideoOverlay] Frame processing error: {type(e).__name__}: {e}")
            self.lbl_dbg.setText(f"Frame error: {type(e).__name__}")
            self.lbl_dbg.setVisible(True)
            self.video_view.set_image(None)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        # Show UI error for unplayable media; all other status transitions are silent.
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.lbl_dbg.setText("Error: Could not load media")
            self.lbl_dbg.setVisible(True)
            self._log(f"Video Overlay InvalidMedia: source={self.player.source().toString()}")

        # Fallback looping when setLoops() isn't available (older Qt builds).
        if self._loop and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.lbl_dbg.setText(f"Player Error: {error_string}")
        self.lbl_dbg.setVisible(True)
        self._log(f"Video Overlay Player Error: {error_string} (code {error}) source={self.player.source().toString()}")

    def _format_ms(self, ms: int) -> str:
        s = max(0, int(ms // 1000))
        m = s // 60
        s = s % 60
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    # Note: we intentionally do NOT rely on videoSizeChanged here; we probe the
    # file's metadata (width/height) via ffprobe in the bridge and pass it in
    # with the open request.

    def _on_duration(self, dur: int) -> None:
        self.slider.setRange(0, max(0, int(dur)))
        self._on_position(self.player.position())

    def _on_position(self, pos: int) -> None:
        if not self._seeking:
            self.slider.setValue(int(pos))
        self.lbl_time.setText(
            f"{self._format_ms(int(pos))} / {self._format_ms(int(self.player.duration()))}"
        )

    def _on_seek_start(self) -> None:
        self._seeking = True
        self._show_controls()

    def _on_seek_commit(self) -> None:
        try:
            self.player.setPosition(int(self.slider.value()))
        except Exception:
            pass
        self._seeking = False
        self._show_controls()

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self._update_controls_ui(state)
        self._show_controls()
        # Ensure we don't hide if we just paused
        if state != QMediaPlayer.PlaybackState.PlayingState:
            self._hide_timer.stop()
            self.controls.setVisible(True)

    def _on_toggle_play_clicked(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            if self._is_inplace:
                # User wants pause/stop to hide the player in mini mode
                self.close_overlay()
        else:
            self.player.play()

    def _update_controls_ui(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_toggle_play.setIcon(self.icon_pause)
            self.btn_toggle_play.setIconSize(QSize(28, 28))
            self.btn_toggle_play.setToolTip("Pause (Space)")
        else:
            self.btn_toggle_play.setIcon(self.icon_play)
            self.btn_toggle_play.setIconSize(QSize(24, 24))
            self.btn_toggle_play.setToolTip("Play (Space)")

    def _on_volume_changed(self, val: int) -> None:
        self.audio.setVolume(val / 100.0)
        self.audio.setMuted(val == 0)
        self._update_mute_icon(val == 0)

    def _update_mute_icon(self, muted: bool) -> None:
        self.btn_mute.setIcon(self.icon_mute_off if muted else self.icon_mute_on)

    def _toggle_mute(self) -> None:
        m = not self.audio.isMuted()
        self.audio.setMuted(m)
        self._update_mute_icon(m)
        if not m and self.vol_slider.value() == 0:
            self.vol_slider.setValue(50)
        self._show_controls()

    def _show_controls(self) -> None:
        if not self.controls.isVisible():
            self._show_controls_actual()
            
        # If playing, manage the hide timer
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            if self._is_over_any_control() or self._seeking:
                self._hide_timer.stop()
            else:
                self._hide_timer.start()
        else:
            self._hide_timer.stop()

    def _is_over_any_control(self) -> bool:
        """Returns True if the mouse is directly over any interactive child widget."""
        # Note: we exclude the volume slider from general show persistence unless explicitly visible
        controls = [self.btn_toggle_play, self.btn_mute, self.slider]
        if self.vol_slider.isVisible():
            controls.append(self.vol_slider)
        for child in controls:
            if child.isVisible() and child.underMouse():
                return True
        return False

    def _show_controls_actual(self) -> None:
        self.controls.setVisible(True)
        self.controls.raise_()
        
        # Initial show: if playing, start the hide timer unless we happen to be over a control
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            if not self._is_over_any_control():
                self._hide_timer.start()
        else:
            self._hide_timer.stop()

    def _hide_controls(self) -> None:
        # This is called when the mouse leaves or the timer expires.
        # We only hide if NOT hovering over any specific control.
        if self._is_over_any_control() or self._seeking:
            self._hide_timer.start()
            return
        self._hide_controls_actual()

    def _hide_controls_actual(self) -> None:
        self.controls.setVisible(False)

    def _hide_controls_immediate(self) -> None:
        self._hide_timer.stop()
        self.controls.setVisible(False)

    def _show_volume_slider(self) -> None:
        self.btn_mute.setStyleSheet(self.mute_qss_pill) # Make transparent inside pill
        self.vol_slider.setVisible(True)
        self.vol_pill.setVisible(True)
        self._vol_hide_timer.stop()
        self.resizeEvent(None) # Trigger pill resize

    def _hide_volume_slider(self) -> None:
        if not self.btn_mute.underMouse() and not self.vol_slider.underMouse():
            self._hide_volume_slider_immediate()

    def _hide_volume_slider_immediate(self) -> None:
        self.btn_mute.setStyleSheet(self.mute_qss_standalone) # Revert to standalone style
        self.vol_slider.setVisible(False)
        self.vol_pill.setVisible(False)
        self.resizeEvent(None)


    def _on_prev_clicked(self) -> None:
        if callable(self.on_prev):
            try:
                self.on_prev()
            except Exception:
                pass

    def _on_next_clicked(self) -> None:
        if callable(self.on_next):
            try:
                self.on_next()
            except Exception:
                pass

