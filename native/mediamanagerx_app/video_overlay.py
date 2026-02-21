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

        self.btn_prev = QPushButton("⏮", self.controls)
        self.btn_toggle_play = QPushButton("⏵", self.controls)
        self.btn_next = QPushButton("⏭", self.controls)
        self.btn_mute = QPushButton("🔊", self.controls)
        self.lbl_time = QLabel("0:00 / 0:00", self.controls)
        self.lbl_dbg = QLabel("", self.controls)
        self.slider = QSlider(Qt.Orientation.Horizontal, self.controls)
        self.btn_close = QPushButton("✕", self.controls)

        self.btn_close.setToolTip("Close (Esc)")
        self.btn_prev.setToolTip("Previous (←)")
        self.btn_next.setToolTip("Next (→)")
        self.btn_toggle_play.setToolTip("Play/Pause (Space)")
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
            " }"
            "QPushButton:hover {"
            " background: rgba(255,255,255,22);"
            " border-radius: 10px;"
            " }"
        )
        for b in (self.btn_prev, self.btn_toggle_play, self.btn_next, self.btn_mute, self.btn_close):
            b.setStyleSheet(btn_css)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

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

        self.btn_toggle_play.clicked.connect(self._toggle_playback)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.btn_close.clicked.connect(self.close_overlay)
        self.btn_mute.clicked.connect(self._toggle_mute)

        self.slider.sliderPressed.connect(self._on_seek_start)
        self.slider.sliderReleased.connect(self._on_seek_commit)

        c_layout = QHBoxLayout(self.controls)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(10)
        c_layout.addWidget(self.btn_prev)
        c_layout.addWidget(self.btn_toggle_play)
        c_layout.addWidget(self.btn_next)
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
        QShortcut(QKeySequence("Space"), self, activated=self._toggle_playback)

        self._loop = False
        self._current_source = ""
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if (obj is self or obj is self.backdrop or obj is self.video_view) and event.type() == QEvent.Type.MouseButtonPress:
            self.close_overlay()
            return True
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self._show_controls()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.close_overlay()
        super().mousePressEvent(event)

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
        if event.key() == Qt.Key.Key_Space:
            self._toggle_playback()
            event.accept()
            return
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
        w = max(1, int(vw * scale))
        h = max(1, int(vh * scale))

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
        print(f"Video Overlay Opening: {path} ({req.width}x{req.height})")
        
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
        
        # Explicit cleanup for new session
        self.video_view.set_image(None)
        self.lbl_dbg.setText("")
        self._current_source = path

        try:
            self.player.stop()
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
        self._first_frame_received = False
        self._auto_pause_needed = not req.autoplay
        self.player.play()
        
        # We'll pause in _on_frame once the first frame actually arrives.
        # But we still need a safety timeout in case the video is broken.
        if self._auto_pause_needed:
             QTimer.singleShot(2000, self._safety_auto_pause)

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
                    print(f"[VideoOverlay] Radioactive frame blocked: {msg}")
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
            print(f"[VideoOverlay] Frame processing error: {type(e).__name__}: {e}")
            self.lbl_dbg.setText(f"Frame error: {type(e).__name__}")
            self.lbl_dbg.setVisible(True)
            self.video_view.set_image(None)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        # Show UI error for unplayable media; all other status transitions are silent.
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.lbl_dbg.setText("Error: Could not load media")
            self.lbl_dbg.setVisible(True)

        # Fallback looping when setLoops() isn't available (older Qt builds).
        if self._loop and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.lbl_dbg.setText(f"Player Error: {error_string}")
        self.lbl_dbg.setVisible(True)
        print(f"Video Overlay Player Error: {error_string} (code {error})")

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

    def _toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _update_controls_ui(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_toggle_play.setText("⏸")
            self.btn_toggle_play.setToolTip("Pause (Space)")
        else:
            self.btn_toggle_play.setText("⏵")
            self.btn_toggle_play.setToolTip("Play (Space)")

    def _toggle_mute(self) -> None:
        m = not self.audio.isMuted()
        self.audio.setMuted(m)
        self.btn_mute.setText("🔇" if m else "🔊")
        self._show_controls()

    def _show_controls(self) -> None:
        self.controls.setVisible(True)
        self.controls.raise_()
        self._hide_timer.start()

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

    def _hide_controls(self) -> None:
        # Don't hide while seeking.
        if self._seeking:
            self._hide_timer.start()
            return
        self.controls.setVisible(False)
