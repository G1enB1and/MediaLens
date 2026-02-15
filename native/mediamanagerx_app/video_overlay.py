from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt, QUrl, QRect, QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtGui import QImage, QPainter
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink, QVideoFrame
from PySide6.QtMultimedia import QVideoFrameFormat
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
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

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Do NOT paint black behind the video; let the overlay backdrop show.
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)

        if not self._img or self._img.isNull():
            return

        # Fit while preserving aspect ratio.
        target = self.rect()
        src = self._img.size()
        scaled = src.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatio)
        
        # Center within the widget
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        
        target_rect = QRect(x, y, scaled.width(), scaled.height())
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

        # Optional close callback (set by owner)
        self.on_close = None

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
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
        # Glassy dark control bar
        self.controls.setStyleSheet(
            "background: rgba(20,20,26,190);"
            "border: 1px solid rgba(255,255,255,30);"
            "border-radius: 14px;"
        )
        self.controls.setVisible(False)

        self.btn_play = QPushButton("⏵", self.controls)
        self.btn_pause = QPushButton("⏸", self.controls)
        self.btn_mute = QPushButton("🔊", self.controls)
        self.lbl_time = QLabel("0:00 / 0:00", self.controls)
        self.lbl_dbg = QLabel("", self.controls)
        self.slider = QSlider(Qt.Orientation.Horizontal, self.controls)
        self.btn_close = QPushButton("✕", self.controls)

        self.btn_close.setToolTip("Close (Esc)")
        self.btn_play.setToolTip("Play")
        self.btn_pause.setToolTip("Pause")
        self.btn_mute.setToolTip("Mute")

        self.slider.setRange(0, 0)
        self.slider.setSingleStep(1000)
        self.slider.setPageStep(5000)

        btn_css = (
            "QPushButton {"
            " color: rgba(255,255,255,230);"
            " background: transparent;"
            " border: none;"
            " padding: 6px 10px;"
            " font-size: 16px;"
            " cursor: pointer;"
            " }"
            "QPushButton:hover {"
            " background: rgba(255,255,255,22);"
            " border-radius: 10px;"
            " }"
        )
        for b in (self.btn_play, self.btn_pause, self.btn_mute, self.btn_close):
            b.setStyleSheet(btn_css)

        self.lbl_time.setStyleSheet("color: rgba(255,255,255,170); font-size: 12px;")
        # Debug label hidden by default
        self.lbl_dbg.setStyleSheet("color: rgba(255,80,80,220); font-size: 11px;")
        self.lbl_dbg.setVisible(False)

        self.slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,28); border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: rgba(138,180,248,200); border-radius: 2px; }"
            "QSlider::add-page:horizontal { background: rgba(255,255,255,20); border-radius: 2px; }"
            "QSlider::handle:horizontal { width: 10px; margin: -5px 0; border-radius: 5px; background: rgba(255,255,255,200); }"
            "min-width: 320px;"
        )

        self.btn_play.clicked.connect(self.player.play)
        self.btn_pause.clicked.connect(self.player.pause)
        self.btn_close.clicked.connect(self.close_overlay)
        self.btn_mute.clicked.connect(self._toggle_mute)

        self.slider.sliderPressed.connect(self._on_seek_start)
        self.slider.sliderReleased.connect(self._on_seek_commit)

        c_layout = QHBoxLayout(self.controls)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(10)
        c_layout.addWidget(self.btn_play)
        c_layout.addWidget(self.btn_pause)
        c_layout.addWidget(self.btn_mute)
        c_layout.addWidget(self.slider, 1)
        c_layout.addWidget(self.lbl_time)
        c_layout.addWidget(self.lbl_dbg)
        c_layout.addWidget(self.btn_close)

        # No layout: we position children manually in resizeEvent.
        self.backdrop.setGeometry(self.rect())
        self.video_view.setGeometry(self.rect())

        # Put the video surface above the backdrop using stacking
        self.backdrop.lower()
        self.video_view.raise_()
        self.controls.raise_()

        # Track seek state
        self._seeking = False

        # Auto-hide controls (we'll keep them visible longer; some Windows video
        # surfaces don't reliably emit mouse move events)
        self._hide_timer = QTimer(self)
        self._hide_timer.setInterval(2000)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_controls)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(lambda _s: self._show_controls())

        # Track native video size (for aspect-ratio correct viewport)
        self._native_size: QSize | None = None

        # Clicking backdrop closes
        self.backdrop.installEventFilter(self)

        # Show controls when mouse moves over the video surface
        self.video_view.installEventFilter(self)
        self.controls.installEventFilter(self)

        # ESC closes reliably
        QShortcut(QKeySequence("Escape"), self, activated=self.close_overlay)

        # Track looping
        self._loop = False
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if obj is self.backdrop and event.type() == QEvent.Type.MouseButtonPress:
            self.close_overlay()
            return True
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self._show_controls()
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        self._show_controls()
        super().mouseMoveEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._show_controls()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hide_timer.start()
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            self.close_overlay()
            event.accept()
            return
        super().keyPressEvent(event)

    def _compute_video_rect(self) -> QRect:
        # Removed internal padding (pad=0) to maximize fill space.
        pad = 0
        bounds = self.rect().adjusted(pad, pad, -pad, -pad)

        if not self._native_size or self._native_size.width() <= 0 or self._native_size.height() <= 0:
            return bounds

        vw = float(self._native_size.width())
        vh = float(self._native_size.height())
        target_w = bounds.width()
        target_h = bounds.height()

        # Fit rect preserving aspect ratio
        scale = min(target_w / vw, target_h / vh)
        w = int(vw * scale)
        h = int(vh * scale)

        x = bounds.x() + (bounds.width() - w) // 2
        y = bounds.y() + (bounds.height() - h) // 2
        return QRect(x, y, w, h)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.backdrop.setGeometry(self.rect())

        r = self._compute_video_rect()
        self.video_view.setGeometry(r)

        # Controls bottom overlay (centered)
        self.controls.adjustSize()
        x = r.center().x() - (self.controls.width() // 2)
        y = r.bottom() - self.controls.height() - 12
        self.controls.move(max(r.left() + 12, x), max(r.top() + 12, y))

        # Keep stacking order consistent
        self.backdrop.lower()
        self.video_view.raise_()
        self.controls.raise_()

    def open_video(self, req: VideoRequest) -> None:
        path = str(Path(req.path))
        self._loop = bool(req.loop)
        self.audio.setMuted(bool(req.muted))
        self.btn_mute.setText("🔇" if req.muted else "🔊")

        if req.width > 0 and req.height > 0:
            self._native_size = QSize(int(req.width), int(req.height))
        else:
            self._native_size = None

        # Looping support varies by Qt version.
        if hasattr(self.player, "setLoops"):
            try:
                self.player.setLoops(-1 if req.loop else 1)  # type: ignore[attr-defined]
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

        # Force controls visible on open; auto-hide after a while.
        self._show_controls()
        QTimer.singleShot(0, self.controls.raise_)

        # Kick the backend so we get the first frame even for non-autoplay.
        self.player.play()
        if not req.autoplay:
            QTimer.singleShot(50, self.player.pause)

        self._show_controls()

    def close_overlay(self) -> None:
        was_visible = self.isVisible()
        try:
            self.player.stop()
        except Exception:
            pass
        self.setVisible(False)
        # Only notify the web layer if we were actually open; avoids closing
        # image lightboxes when we "stop video" during navigation.
        if was_visible and callable(self.on_close):
            try:
                self.on_close()
            except Exception:
                pass

    def _on_frame(self, frame: QVideoFrame) -> None:
        """Convert QVideoFrame to QImage for painting."""

        try:
            pf = frame.pixelFormat()
            w = frame.width()
            h = frame.height()

            # Best case
            img = None
            if hasattr(frame, "toImage"):
                img = frame.toImage()  # type: ignore[attr-defined]
            if img is not None and not img.isNull():
                self.lbl_dbg.setText("")
                self.video_view.set_image(img)
                return

            # Fallback: map raw bytes for common packed RGB formats
            if not frame.map(QVideoFrame.MapMode.ReadOnly):
                self.lbl_dbg.setText(f"no-map pf={int(pf)}")
                self.video_view.set_image(None)
                return

            try:
                bpl = frame.bytesPerLine(0)
                ptr = frame.bits(0)

                qfmt = None
                if pf == QVideoFrameFormat.PixelFormat.Format_BGRA8888:
                    qfmt = QImage.Format.Format_ARGB32
                elif pf == QVideoFrameFormat.PixelFormat.Format_RGBA8888:
                    qfmt = QImage.Format.Format_RGBA8888
                elif pf == QVideoFrameFormat.PixelFormat.Format_ARGB8888:
                    qfmt = QImage.Format.Format_ARGB32

                if qfmt is None:
                    self.lbl_dbg.setText(f"unsupported pf={int(pf)} {w}x{h}")
                    self.video_view.set_image(None)
                    return

                img2 = QImage(ptr, w, h, bpl, qfmt)
                self.lbl_dbg.setText("")
                self.video_view.set_image(img2.copy())
            finally:
                frame.unmap()
        except Exception as e:
            self.lbl_dbg.setText(f"frame err: {type(e).__name__}")
            self.video_view.set_image(None)

    def _on_media_status(self, status) -> None:
        # Fallback looping if setLoops isn't available.
        if not self._loop:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

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

    def _toggle_mute(self) -> None:
        m = not self.audio.isMuted()
        self.audio.setMuted(m)
        self.btn_mute.setText("🔇" if m else "🔊")
        self._show_controls()

    def _show_controls(self) -> None:
        self.controls.setVisible(True)
        self.controls.raise_()
        self._hide_timer.start()

    def _hide_controls(self) -> None:
        # Don't hide while seeking.
        if self._seeking:
            self._hide_timer.start()
            return
        self.controls.setVisible(False)
