from __future__ import annotations
# Source of Truth: \VERSION
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION"), "r") as f:
        __version__ = f.read().strip()
except Exception:
    __version__ = "v1.1.10"


import sys
import os
import faulthandler
import hashlib
import subprocess
import shutil
import random
import threading
import time
import re
import json
import html
import shlex
import traceback
from collections import Counter
from datetime import datetime, timezone
from math import gcd
from packaging.version import Version
from pathlib import Path

def send_to_recycle_bin(path: str) -> bool:
    try:
        import send2trash
        send2trash.send2trash(str(Path(path).resolve()))
        return True
    except Exception:
        return False



def _install_stderr_filter() -> None:
    """Suppress noisy C-level FFmpeg log lines written directly to stderr fd 2.

    FFmpeg's av_log (used by libswscale, etc.) writes directly to the C file
    descriptor 2, bypassing Python's sys.stderr entirely. The only reliable way
    to filter it is to redirect fd 2 to a pipe and relay output on a thread,
    dropping lines that match known noise patterns.

    Known suppressions:
    - "deprecated pixel format used, make sure you did set range correctly"
      Fired once per swscale context when a video uses the legacy `yuvj420p`
      full-range pixel format (common in MJPEG and some H.264 files). It is
      informational only \u2014 playback is unaffected.
    """
    _SUPPRESS = (
        b"deprecated pixel format used",
        b"Could not parse stylesheet of object QProgressBar",
        b"Could not update timestamps for skipped samples.",
    )

    try:
        read_fd, write_fd = os.pipe()
        real_stderr_fd = os.dup(2)      # Save the original stderr fd
        os.dup2(write_fd, 2)            # All C-level stderr now goes to the pipe
        os.close(write_fd)

        def _relay() -> None:
            buf = b""
            with (
                os.fdopen(read_fd, "rb", buffering=0) as pipe_in,
                os.fdopen(real_stderr_fd, "wb", buffering=0) as real_out,
            ):
                while True:
                    chunk = pipe_in.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    # Process complete lines; hold back any partial trailing line.
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if not any(s in line for s in _SUPPRESS):
                            real_out.write(line + b"\n")
                            real_out.flush()
                # Flush any remaining partial line.
                if buf and not any(s in buf for s in _SUPPRESS):
                    real_out.write(buf)
                    real_out.flush()

        t = threading.Thread(target=_relay, daemon=True, name="stderr-filter")
        t.start()
    except Exception:
        # If anything goes wrong, leave stderr untouched rather than breaking logging.
        pass


_install_stderr_filter()


from PySide6.QtCore import (
    QObject,
    Qt,
    Signal,
    Slot,
    QUrl,
    QDir,
    QStandardPaths,
    QSize,
    QSettings,
    QPoint,
    QMimeData,
    QEvent,
    QTimer,
    QMetaObject,
    QRect,
    QRectF,
    QItemSelectionModel,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDrag,
    QFont,
    QFontMetrics,
    QImage,
    QImageReader,
    QIcon,
    QMovie,
    QPainter,
    QPainterPath,
    QPalette,
    QCursor,
    QPixmap,
    QMouseEvent,
    QPen,
    QDragEnterEvent,
    QDragMoveEvent,
    QDragLeaveEvent,
    QDropEvent,
    QEnterEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QSplitterHandle,
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QTreeView,
    QFileIconProvider,
    QFileSystemModel,
    QDialog,
    QPushButton,
    QHBoxLayout,
    QProgressBar,
    QSplashScreen,
    QMenu,
    QInputDialog,
    QPlainTextEdit,
    QTextEdit,
    QLineEdit,
    QFrame,
    QScrollArea,
    QCheckBox,
    QGridLayout,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtSvg import QSvgRenderer
from native.mediamanagerx_app.video_overlay import LightboxVideoOverlay, VideoRequest
from native.mediamanagerx_app.settings_dialog import SettingsDialog
from PySide6.QtCore import QSortFilterProxyModel, QModelIndex


import ctypes
from ctypes import wintypes


_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS: dict[str, object] = {}
if os.name == "nt":
    try:
        _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS["creationflags"] = subprocess.CREATE_NO_WINDOW
    except AttributeError:
        pass


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif", ".svg"}
RASTER_IMAGE_EXTS = IMAGE_EXTS - {".svg"}
VIDEO_EXTS = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}
_SVG_THUMBNAIL_BG_HINT_CACHE: dict[tuple[str, int, int], str] = {}


def _render_svg_image(path: str | Path) -> QImage | None:
    clean = str(path or "").strip()
    if not clean:
        return None
    renderer = QSvgRenderer(clean)
    if not renderer.isValid():
        return None
    size = renderer.defaultSize()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        size = QSize(512, 512)
    max_dim = max(size.width(), size.height())
    if max_dim > 4096:
        scale = 4096.0 / max_dim
        size = QSize(max(1, int(size.width() * scale)), max(1, int(size.height() * scale)))
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image if not image.isNull() else None


def _read_image_with_svg_support(path: str | Path, *, auto_transform: bool = True) -> QImage | None:
    clean = str(path or "").strip()
    if not clean:
        return None
    reader = QImageReader(clean)
    reader.setAutoTransform(auto_transform)
    image = reader.read()
    if not image.isNull():
        return image
    if Path(clean).suffix.lower() == ".svg":
        return _render_svg_image(clean)
    return None


def _image_size_with_svg_support(path: str | Path) -> QSize:
    clean = str(path or "").strip()
    if not clean:
        return QSize()
    reader = QImageReader(clean)
    size = reader.size()
    if size.isValid():
        return size
    if Path(clean).suffix.lower() == ".svg":
        renderer = QSvgRenderer(clean)
        if renderer.isValid():
            return renderer.defaultSize()
    return QSize()


def _srgb_channel_to_linear(channel: int) -> float:
    value = max(0.0, min(255.0, float(channel))) / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _image_visible_luminance(image: QImage | None) -> float | None:
    if image is None or image.isNull():
        return None
    sample = image
    if sample.width() > 96 or sample.height() > 96:
        sample = sample.scaled(
            96,
            96,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if sample.isNull():
        return None
    weighted_luminance = 0.0
    total_alpha = 0.0
    for y in range(sample.height()):
        for x in range(sample.width()):
            color = sample.pixelColor(x, y)
            alpha = color.alphaF()
            if alpha <= 0.01:
                continue
            luminance = (
                0.2126 * _srgb_channel_to_linear(color.red())
                + 0.7152 * _srgb_channel_to_linear(color.green())
                + 0.0722 * _srgb_channel_to_linear(color.blue())
            )
            weighted_luminance += luminance * alpha
            total_alpha += alpha
    if total_alpha <= 0.0:
        return None
    return weighted_luminance / total_alpha


def _svg_thumbnail_bg_hint(path: str | Path) -> str:
    clean = str(path or "").strip()
    if not clean or Path(clean).suffix.lower() != ".svg":
        return ""
    try:
        stat = Path(clean).stat()
        cache_key = (clean, int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        cache_key = (clean, 0, 0)
    cached = _SVG_THUMBNAIL_BG_HINT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    luminance = _image_visible_luminance(_render_svg_image(clean))
    # Only force contrast backgrounds for mostly dark or mostly light SVG art.
    if luminance is None:
        hint = ""
    elif luminance <= 0.35:
        hint = "light"
    elif luminance >= 0.75:
        hint = "dark"
    else:
        hint = ""
    if len(_SVG_THUMBNAIL_BG_HINT_CACHE) > 512:
        _SVG_THUMBNAIL_BG_HINT_CACHE.clear()
    _SVG_THUMBNAIL_BG_HINT_CACHE[cache_key] = hint
    return hint
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS["startupinfo"] = startupinfo
    except AttributeError:
        pass


def _dpi_awareness_context_handle(value: int):
    mask = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
    return ctypes.c_void_p(value & mask)


def _describe_windows_dpi_awareness() -> str:
    if os.name != "nt":
        return "non-windows"

    user32 = getattr(ctypes.windll, "user32", None)
    if user32 is not None:
        try:
            get_thread_context = user32.GetThreadDpiAwarenessContext
            get_thread_context.restype = wintypes.HANDLE
            are_equal = user32.AreDpiAwarenessContextsEqual
            are_equal.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            are_equal.restype = wintypes.BOOL
            current = get_thread_context()
            known_contexts = (
                ("unaware", -1),
                ("system", -2),
                ("permonitor", -3),
                ("permonitorv2", -4),
                ("unawaregdiscaled", -5),
            )
            for name, raw_value in known_contexts:
                if are_equal(current, _dpi_awareness_context_handle(raw_value)):
                    return name
        except Exception:
            pass

    shcore = getattr(ctypes.windll, "shcore", None)
    if shcore is not None:
        try:
            awareness = ctypes.c_int(-1)
            get_process_awareness = shcore.GetProcessDpiAwareness
            get_process_awareness.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_int)]
            get_process_awareness.restype = ctypes.c_long
            result = get_process_awareness(None, ctypes.byref(awareness))
            if result == 0:
                return {
                    0: "unaware",
                    1: "system",
                    2: "permonitor",
                }.get(int(awareness.value), f"unknown({awareness.value})")
        except Exception:
            pass

    return "unknown"


def _describe_qt_dpi_policy() -> str:
    try:
        policy = QApplication.highDpiScaleFactorRoundingPolicy()
        names = {
            Qt.HighDpiScaleFactorRoundingPolicy.Round: "Round",
            Qt.HighDpiScaleFactorRoundingPolicy.Ceil: "Ceil",
            Qt.HighDpiScaleFactorRoundingPolicy.Floor: "Floor",
            Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor: "RoundPreferFloor",
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough: "PassThrough",
        }
        return names.get(policy, str(policy))
    except Exception:
        return "unknown"


def _format_dpi_state(app: QApplication | None = None) -> str:
    if app is None:
        try:
            app = QApplication.instance()
        except Exception:
            app = None

    awareness = _describe_windows_dpi_awareness()
    qt_policy = _describe_qt_dpi_policy()
    screen_parts: list[str] = []
    if app is not None:
        for screen in app.screens():
            try:
                geometry = screen.geometry()
                screen_parts.append(
                    f"{screen.name()}: dpr={screen.devicePixelRatio():.2f}, "
                    f"logical={screen.logicalDotsPerInch():.2f}, "
                    f"physical={screen.physicalDotsPerInch():.2f}, "
                    f"geom={geometry.width()}x{geometry.height()}@{geometry.x()},{geometry.y()}"
                )
            except Exception:
                continue
    screens_text = "; ".join(screen_parts) if screen_parts else "none"
    return (
        "DPI: "
        f"windows_awareness={awareness}, "
        f"qt_rounding_policy={qt_policy}, "
        f"screens=[{screens_text}]"
    )


def _log_dpi_state(app: QApplication, log) -> None:
    try:
        log(_format_dpi_state(app))
    except Exception:
        pass


def _run_hidden_subprocess(cmd: list[str], **kwargs):
    if _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS:
        kwargs = {**_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS, **kwargs}
    return subprocess.run(cmd, **kwargs)


_FAULT_HANDLER_STREAM = None


def _appdata_runtime_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / "AppData" / "Roaming"
    out = root / "G1enB1and" / "MediaManagerX"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_crash_report(kind: str, exc_type=None, exc_value=None, exc_tb=None) -> Path | None:
    try:
        report_dir = _appdata_runtime_dir() / "crash-reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_path = report_dir / f"{kind}-{stamp}.log"
        lines = [
            f"Version: {__version__}",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Python: {sys.version}",
            f"Executable: {sys.executable}",
            f"Frozen: {bool(getattr(sys, 'frozen', False))}",
            f"CWD: {os.getcwd()}",
            _format_dpi_state(),
        ]
        if exc_type is not None:
            lines.extend([
                "",
                "Traceback:",
                "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip(),
            ])
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return report_path
    except Exception:
        return None


def _install_crash_reporting() -> None:
    global _FAULT_HANDLER_STREAM
    try:
        faulthandler_log = _appdata_runtime_dir() / "faulthandler.log"
        _FAULT_HANDLER_STREAM = open(faulthandler_log, "a", encoding="utf-8")
        faulthandler.enable(_FAULT_HANDLER_STREAM)
    except Exception:
        pass

    def _handle_exception(exc_type, exc_value, exc_tb):
        report = _write_crash_report("python-crash", exc_type, exc_value, exc_tb)
        try:
            print("Unhandled exception:", file=sys.stderr)
            traceback.print_exception(exc_type, exc_value, exc_tb)
            if report:
                print(f"Crash report written to: {report}", file=sys.stderr)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def _handle_thread_exception(args):
        _handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = _handle_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception


_install_crash_reporting()


class Theme:
    """Centralized theme system with neutral surfaces and restrained accent usage."""
    _theme_mode_override: str | None = None

    @staticmethod
    def mix(base_hex: str, accent_color: QColor | str, strength: float) -> str:
        """Mix a base hex color with an accent QColor (or hex string)."""
        base = QColor(base_hex)
        acc = QColor(accent_color) if isinstance(accent_color, str) else accent_color
        r = int(base.red() + (acc.red() - base.red()) * strength)
        g = int(base.green() + (acc.green() - base.green()) * strength)
        b = int(base.blue() + (acc.blue() - base.blue()) * strength)
        return QColor(r, g, b).name()

    BASE_BG_DARK = "#1e1e1e"
    BASE_SIDEBAR_BG_DARK = "#252526"
    BASE_CONTROL_BG_DARK = "#2d2d30"
    BASE_BORDER_DARK = "#3b3b40"

    BASE_BG_LIGHT = "#f4f5f7"
    BASE_SIDEBAR_BG_LIGHT = "#fbfbfc"
    BASE_CONTROL_BG_LIGHT = "#ffffff"
    BASE_BORDER_LIGHT = "#d9dde3"

    @staticmethod
    def set_theme_mode(mode: str | None) -> None:
        clean = str(mode or "").strip().lower()
        if clean not in {"light", "dark"}:
            Theme._theme_mode_override = None
            return
        Theme._theme_mode_override = clean
    
    @staticmethod
    def get_is_light() -> bool:
        if Theme._theme_mode_override in {"light", "dark"}:
            return Theme._theme_mode_override == "light"
        settings = QSettings("G1enB1and", "MediaManagerX")
        val = settings.value("ui/theme_mode", "dark")
        # Ensure we handle both string and potential type-wrapped values cleanly
        return str(val).lower() == "light"

    @staticmethod
    def get_bg(accent: QColor) -> str:
        return Theme.BASE_BG_LIGHT if Theme.get_is_light() else Theme.BASE_BG_DARK

    @staticmethod
    def get_sidebar_bg(accent: QColor) -> str:
        return Theme.BASE_SIDEBAR_BG_LIGHT if Theme.get_is_light() else Theme.BASE_SIDEBAR_BG_DARK

    @staticmethod
    def get_control_bg(accent: QColor) -> str:
        return Theme.BASE_CONTROL_BG_LIGHT if Theme.get_is_light() else Theme.BASE_CONTROL_BG_DARK

    @staticmethod
    def get_border(accent: QColor) -> str:
        return Theme.BASE_BORDER_LIGHT if Theme.get_is_light() else Theme.BASE_BORDER_DARK

    @staticmethod
    def get_scrollbar_track(accent: QColor) -> str:
        return "#181818" if not Theme.get_is_light() else "#f1f2f4"

    @staticmethod
    def get_scrollbar_thumb(accent: QColor) -> str:
        return "#c3c8d1" if Theme.get_is_light() else "#4a4a50"

    @staticmethod
    def get_scrollbar_thumb_hover(accent: QColor) -> str:
        return "#aeb5bf" if Theme.get_is_light() else "#5a5a61"

    @staticmethod
    def get_splitter_idle(accent: QColor) -> str:
        return "#c8ccd3" if Theme.get_is_light() else "#4a4a50"

    @staticmethod
    def get_accent_soft(accent: QColor) -> str:
        base = Theme.get_control_bg(accent)
        strength = 0.18 if Theme.get_is_light() else 0.16
        return Theme.mix(base, accent, strength)

    # UI constants
    @staticmethod
    def get_text_color() -> str:
        return "#1f2329" if Theme.get_is_light() else "#f2f2f3"

    @staticmethod
    def get_text_muted() -> str:
        return "#60656f" if Theme.get_is_light() else "#b4b7bd"

    @staticmethod
    def get_btn_save_bg(accent: QColor) -> str:
        return Theme.get_control_bg(accent)

    @staticmethod
    def get_btn_save_hover(accent: QColor) -> str:
        return Theme.get_accent_soft(accent)

    @staticmethod
    def get_input_bg(accent: QColor) -> str:
        return Theme.get_control_bg(accent)

    @staticmethod
    def get_input_border(accent: QColor) -> str:
        return Theme.get_border(accent)

    ACCENT_DEFAULT = "#8ab4f8"


def _rounded_preview_pixmap(source: QPixmap, target: QSize, border_color: str, radius: float = 10.0) -> QPixmap:
    scaled = source.scaled(
        target,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        return scaled
    result = QPixmap(scaled.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    draw_rect = QRectF(0.5, 0.5, max(0.0, result.width() - 1.0), max(0.0, result.height() - 1.0))
    path = QPainterPath()
    path.addRoundedRect(draw_rect, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.setClipping(False)
    pen = QPen(QColor(border_color))
    pen.setWidth(1)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(draw_rect, radius, radius)
    painter.end()
    return result


class FileConflictDialog(QDialog):
    def __init__(self, existing_path: Path, incoming_path: Path, bridge, parent=None):
        super().__init__(parent)
        self.existing_path = existing_path
        self.incoming_path = incoming_path
        self.bridge = bridge
        self.result_action = "keep_both"
        self.apply_to_all = False
        
        self.setWindowTitle("File Conflict")
        self.setMinimumWidth(600)
        
        # Get theme colors
        accent_str = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT))
        accent_q = QColor(accent_str)
        is_light = Theme.get_is_light()
        
        bg_color = Theme.get_bg(accent_q)
        fg_color = Theme.get_text_color()
        muted_color = Theme.get_text_muted()
        border_color = Theme.get_border(accent_q)
        btn_bg = Theme.get_btn_save_bg(accent_q)
        btn_hover = Theme.get_btn_save_hover(accent_q)
        input_bg = Theme.get_input_bg(accent_q)
        
        # Physical SVG for checkbox (data URIs are unreliable in Qt QSS)
        check_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "scrollbar_arrows", "check.svg").replace("\\", "/")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {fg_color};
            }}
            QLabel {{
                color: {fg_color};
                font-size: 10pt;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {accent_str};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px;
            }}
            QCheckBox {{
                color: {muted_color};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                background-color: #fff;
                border: 1px solid {"#888" if is_light else border_color};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_str};
                image: url("{check_path}");
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Style refinements for light mode
        other_btn_style = ""
        replace_btn_style = f"background-color: {accent_str}; color: #fff; border: 1px solid {border_color};"
        other_hover_style = f"background-color: {Theme.mix(btn_bg, accent_q, 0.4)}; border: 1px solid {accent_str};"
        replace_hover_bg = Theme.mix("#ffffff", accent_q, 0.9)
        
        if is_light:
            darker_border = Theme.mix(border_color, QColor("#000000"), 0.4)
            other_btn_bg = Theme.get_control_bg(accent_q)
            replace_btn_bg = Theme.get_accent_soft(accent_q)
            other_btn_style = f"background-color: {other_btn_bg}; color: #000; border: 1px solid {darker_border};"
            replace_btn_style = f"background-color: {replace_btn_bg}; color: #000; border: 1px solid {darker_border};"
            
            # Hover styles stay restrained and only introduce a soft accent.
            other_hover_bg = Theme.mix(other_btn_bg, accent_q, 0.12)
            other_hover_style = f"background-color: {other_hover_bg}; border: 1px solid {accent_str};"
            
            replace_hover_bg = Theme.mix(replace_btn_bg, accent_q, 0.08)
            replace_hover_style = f"background-color: {replace_hover_bg}; color: #000; border: 1px solid {accent_str};"
        else:
            replace_hover_style = f"background-color: {replace_hover_bg}; border: 1px solid {accent_str};"
        
        header = QLabel("<h3>A file with this name already exists.</h3>")
        header.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(header)
        
        # Grid for side-by-side comparison
        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setRowStretch(2, 1) # Allow name label row to expand
        layout.addLayout(grid)
        
        def create_card(title_text, path, col):
            # Title
            title = QLabel(f"<b>{title_text}</b>")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(title, 0, col)
            
            # Thumbnail
            thumb = QLabel()
            thumb.setFixedSize(240, 180)
            thumb.setStyleSheet(f"background: #000; border: 2px solid {border_color}; border-radius: 8px;")
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_thumb(thumb, path)
            grid.addWidget(thumb, 1, col, Qt.AlignmentFlag.AlignCenter)
            
            # Name
            name_label = QLabel(path.name)
            name_label.setWordWrap(True)
            name_label.setFixedWidth(240)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Ensure it can grow vertically without clipping
            name_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
            name_label.setContentsMargins(0, 5, 0, 5)
            grid.addWidget(name_label, 2, col, Qt.AlignmentFlag.AlignCenter)
            
            # Stats (Size, Date)
            try:
                stat = path.stat()
                size_str = self._format_size(stat.st_size)
                date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
                stats = QLabel(f"<span style='color: {muted_color};'>{size_str} • {date_str}</span>")
                stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(stats, 3, col, Qt.AlignmentFlag.AlignCenter)
            except: pass
            
            # Rename components
            rename_btn = QPushButton("Rename Item")
            rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rename_input = QLineEdit(path.name)
            rename_input.hide()
            grid.addWidget(rename_btn, 4, col)
            grid.addWidget(rename_input, 4, col)
            
            if is_light:
                rename_btn.setStyleSheet(f"""
                    QPushButton {{ {other_btn_style} }}
                    QPushButton:hover {{ {other_hover_style} }}
                """)
            
            def show_rename():
                rename_btn.hide()
                rename_input.show()
                rename_input.setFocus()
            rename_btn.clicked.connect(show_rename)
            
            return rename_input

        self.existing_rename_input = create_card("Existing File", existing_path, 0)
        self.incoming_rename_input = create_card("Incoming File", incoming_path, 1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        keep_both_btn = QPushButton("Keep Both")
        replace_btn = QPushButton("Replace")
        skip_btn = QPushButton("Skip")
        
        for b in (keep_both_btn, replace_btn, skip_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_light and b != replace_btn:
                b.setStyleSheet(f"QPushButton {{ {other_btn_style} }}")
        
        keep_both_btn.clicked.connect(lambda: self._finish("keep_both"))
        replace_btn.clicked.connect(lambda: self._finish("replace"))
        skip_btn.clicked.connect(lambda: self._finish("skip"))
        
        replace_btn.setStyleSheet(f"""
            QPushButton {{ 
                {replace_btn_style}
            }}
            QPushButton:hover {{ 
                {replace_hover_style}
            }}
        """)
        
        # Consistent style for other buttons in light mode
        if is_light:
            for b in (skip_btn, keep_both_btn):
                b.setStyleSheet(f"""
                    QPushButton {{ {other_btn_style} }}
                    QPushButton:hover {{ {other_hover_style} }}
                """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(skip_btn)
        btn_layout.addWidget(keep_both_btn)
        btn_layout.addWidget(replace_btn)
        layout.addLayout(btn_layout)
        
        # Apply to all
        self.apply_all_cb = QCheckBox("Apply to all remaining conflicts")
        self.apply_all_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.apply_all_cb)

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _set_thumb(self, label, path: Path):
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            img = _read_image_with_svg_support(path)
            
            # Fallback for AVIF or other formats Qt can't read natively
            if (img is None or img.isNull()) and ext == ".avif":
                poster = self.bridge._ensure_video_poster(path)
                if poster and poster.exists():
                    img = QImageReader(str(poster)).read()

            if img is not None and not img.isNull():
                pix = QPixmap.fromImage(img).scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pix)
            else:
                label.setText("Image Corrupt")
        else:
            # Try to get poster for video or AVIF that failed direct read
            poster = self.bridge._ensure_video_poster(path)
            if poster and poster.exists():
                img = QImageReader(str(poster)).read()
                if not img.isNull():
                    pix = QPixmap.fromImage(img).scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(pix)
                else:
                    label.setText("Thumb Fail")
            else:
                is_vid = path.suffix.lower() in VIDEO_EXTS
                label.setText("Video" if is_vid else "File")

    @property
    def new_existing_name(self):
        return self.existing_rename_input.text()

    @property
    def new_incoming_name(self):
        return self.incoming_rename_input.text()

    def _finish(self, action):
        self.result_action = action
        self.apply_to_all = self.apply_all_cb.isChecked()
        self.accept()


class CustomSplitterHandle(QSplitterHandle):
    """Custom handle that paints itself to ensure hover colors work on all platforms."""
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        accent_str = str(self.parent().window().bridge.settings.value("ui/accent_color", "#8ab4f8"))
        accent = QColor(accent_str)
        track = QColor(Theme.get_bg(accent))
        idle = QColor(Theme.get_splitter_idle(accent))
        color = accent if self.underMouse() else idle

        painter.fillRect(self.rect(), track)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        mid_x = self.rect().center().x()
        mid_y = self.rect().center().y()
        if self.orientation() == Qt.Orientation.Horizontal:
            painter.drawLine(mid_x, self.rect().top(), mid_x, self.rect().bottom())
        else:
            painter.drawLine(self.rect().left(), mid_y, self.rect().right(), mid_y)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.update()
        super().leaveEvent(event)


class CustomSplitter(QSplitter):
    """Splitter that uses CustomSplitterHandle."""
    def createHandle(self) -> QSplitterHandle:
        return CustomSplitterHandle(self.orientation(), self)


class FolderTreeView(QTreeView):
    """Tree view that does NOT change selection on right-click.

    Windows Explorer behavior: right-click opens context menu without changing
    the active selection (unless explicitly choosing/selecting).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            idx = self.indexAt(event.position().toPoint())
            if idx.isValid() and not self.selectionModel().isSelected(idx):
                # Only if not already selected, we might want to select just this one?
                # Explorer actually selects on right-click if nothing is selected.
                pass
            # Don't call super() if we want to block the default selection behavior
            # BUT we need it for the context menu to know WHERE we clicked.
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            source_idx = self.model().mapToSource(idx)
            fs_model = self.model().sourceModel()
            if fs_model.isDir(source_idx):
                target_folder = fs_model.filePath(source_idx)
                
                # Check modifier keys for Copy vs Move
                is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                
                # Update tooltip via bridge
                main_win = self.window()
                bridge = getattr(main_win, "bridge", None)
                if bridge:
                    # Count items from side-channel or mime
                    count = len(bridge.drag_paths) if bridge.drag_paths else 1
                    bridge.update_drag_tooltip(count, is_copy, Path(target_folder).name)
                
                self.setExpanded(idx, True)
                event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
                event.accept()
                return
        
        # If not over a folder, hide tooltip target
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            count = len(bridge.drag_paths) if bridge.drag_paths else 1
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            bridge.update_drag_tooltip(count, is_copy, "")
            
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        mime = event.mimeData()
        idx = self.indexAt(event.position().toPoint())
        
        # Determine target folder
        target_path = ""
        if idx.isValid():
            # Handle proxy model mapping
            model = self.model()
            if isinstance(model, QSortFilterProxyModel):
                source_idx = model.mapToSource(idx)
                fs_model = model.sourceModel()
                if isinstance(fs_model, QFileSystemModel):
                    if fs_model.isDir(source_idx):
                        target_path = fs_model.filePath(source_idx)
                    else:
                        target_path = fs_model.filePath(source_idx.parent())
            elif isinstance(model, QFileSystemModel):
                if model.isDir(idx):
                    target_path = model.filePath(idx)
                else:
                    target_path = model.filePath(idx.parent())

        if not target_path:
            event.ignore()
            return

        # Gather source paths
        src_paths = []
        
        # Priority 0: Side-channel from Bridge (Reliable for internal Gallery -> Tree)
        if bridge and hasattr(bridge, "drag_paths") and bridge.drag_paths:
            src_paths = list(bridge.drag_paths)
        
        # Priority 1: fallback to MIME data for tree-to-tree or external drops
        if not src_paths:
            if mime.hasUrls():
                src_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]

        if not src_paths:
            event.ignore()
            return

        # Filter out if moving to THE SAME folder
        src_paths = [p for p in src_paths if os.path.dirname(p).replace("\\", "/").lower() != target_path.replace("\\", "/").lower()]

        if not src_paths:
            event.ignore()
            return

        # Determine if COPY or MOVE
        is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        op_type = "copy" if is_copy else "move"
        
        if bridge:
            # Perform operation
            paths_obj = [Path(p) for p in src_paths]
            bridge._process_file_op(op_type, paths_obj, Path(target_path))
            event.acceptProposedAction()
        else:
            event.ignore()


class CollectionListWidget(QListWidget):
    """Flat collection list with right-click context menu and gallery drop support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if self.viewport() is not None:
            self.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        self.setCursor(Qt.CursorShape.PointingHandCursor if item else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or bool(getattr(self.window().bridge, "drag_paths", [])):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        item = self.itemAt(event.position().toPoint())
        if item and bridge:
            count = len(bridge.drag_paths) if bridge.drag_paths else max(1, len(event.mimeData().urls()))
            bridge.update_drag_tooltip(count, True, item.text())
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        if bridge:
            bridge.update_drag_tooltip(len(bridge.drag_paths) or 1, True, "")
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        item = self.itemAt(event.position().toPoint())
        if not item or not bridge:
            event.ignore()
            return

        src_paths = list(bridge.drag_paths) if bridge.drag_paths else []
        if not src_paths and event.mimeData().hasUrls():
            src_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        if not src_paths:
            event.ignore()
            return

        collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if collection_id <= 0:
            event.ignore()
            return

        if bridge.add_paths_to_collection(collection_id, src_paths) > 0:
            event.acceptProposedAction()
            return
        event.ignore()


class PinnedFolderListWidget(QListWidget):
    """Flat pinned-folder list with drag-and-drop support for folders only."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        self.setCursor(Qt.CursorShape.PointingHandCursor if item else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    @staticmethod
    def _extract_folder_paths(mime: QMimeData, bridge: "Bridge | None") -> list[str]:
        raw_paths: list[str] = []
        if bridge and bridge.drag_paths:
            raw_paths = list(bridge.drag_paths)
        elif mime.hasUrls():
            raw_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]

        folders: list[str] = []
        seen: set[str] = set()
        for raw_path in raw_paths:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                p = Path(path_str)
                if not p.exists() or not p.is_dir():
                    continue
                normalized = str(p.absolute())
            except Exception:
                continue
            key = normalized.replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            folders.append(normalized)
        return folders

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if folders:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if folders:
            if bridge:
                bridge.update_drag_tooltip(len(folders), True, "Pinned Folders")
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if not folders or not bridge:
            event.ignore()
            return

        if bridge.pin_folders(folders) > 0:
            event.acceptProposedAction()
            return
        event.ignore()


class RootFilterProxyModel(QSortFilterProxyModel):
    """Filters a QFileSystemModel to only show a specific root folder and its children.
    
    Siblings of the root folder are hidden.
    """
    def __init__(self, bridge: Bridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self._root_path = ""
        self._fallback_icon: QIcon | None = None

    def setRootPath(self, path: str) -> None:
        self._root_path = str(Path(path).absolute()).replace("\\", "/").lower()
        self.invalidateFilter()

    def _has_visible_child_dirs(self, raw_path: str) -> bool:
        path_str = str(raw_path or "").strip()
        if not path_str:
            return False
        try:
            root = Path(path_str)
            if not root.exists() or not root.is_dir():
                return False
            show_hidden = self.bridge._show_hidden_enabled()
            for child in root.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    if not show_hidden and self.bridge.repo.is_path_hidden(str(child)):
                        continue
                    return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._root_path:
            return True
            
        fs_model = self.sourceModel()
        source_index = fs_model.index(source_row, 0, source_parent)
        raw_path = fs_model.filePath(source_index)
        
        # Consistent normalization for all path checks
        from app.mediamanager.utils.pathing import normalize_windows_path
        normalized_path = normalize_windows_path(raw_path)
        
        # Hidden logic: if show_hidden is False, skip database-marked hidden paths
        # This check must come before the root path inclusion logic.
        if not self.bridge._show_hidden_enabled():
            if self.bridge.repo.is_path_hidden(raw_path):
                return False

        root = normalize_windows_path(self._root_path).rstrip("/")
        norm_path = normalized_path.rstrip("/")

        # Show the root path itself
        if norm_path == root:
            return True
            
        # Show children/descendants of the root path
        if normalized_path.startswith(root + "/"):
            return True
            
        # Show ancestors of the root path (so we can reach it from the top)
        if (root + "/").startswith(norm_path + "/"):
            return True
            
        # Special case: show Windows drives if they are ancestors
        if len(norm_path) == 2 and norm_path[1] == ":" and root.startswith(norm_path):
            return True

        return False

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        if not parent.isValid():
            return super().hasChildren(parent)

        source_model = self.sourceModel()
        if not isinstance(source_model, QFileSystemModel):
            return super().hasChildren(parent)

        source_index = self.mapToSource(parent)
        if not source_index.isValid() or not source_model.isDir(source_index):
            return False

        raw_path = source_model.filePath(source_index)
        return self._has_visible_child_dirs(raw_path)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        source_idx = self.mapToSource(index)
        source_model = self.sourceModel()
        is_directory = isinstance(source_model, QFileSystemModel) and source_model.isDir(source_idx)

        # Prevent "customized" folder icons (which sometimes fail to load or are empty)
        # by forcing the standard folder icon for all directories.
        if role == Qt.ItemDataRole.DecorationRole and is_directory:
            if not self._fallback_icon:
                provider = QFileIconProvider()
                self._fallback_icon = provider.icon(QFileIconProvider.IconType.Folder)
            return self._fallback_icon.pixmap(QSize(16, 16))
                
        return super().data(index, role)


class AccentSelectionTreeDelegate(QStyledItemDelegate):
    """Paint selected tree rows with accent-colored bold text without tinting the folder icon."""

    def __init__(self, bridge: "Bridge", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge

    def paint(self, painter: QPainter, option, index) -> None:
        from PySide6.QtWidgets import QStyleOptionViewItem
        from app.mediamanager.utils.pathing import normalize_windows_path

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        tree = self.parent()
        is_active_index = bool(tree is not None and hasattr(tree, "currentIndex") and tree.currentIndex() == index)
        is_selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        active_folder_path = ""
        try:
            selected_folders = getattr(self.bridge, "_selected_folders", []) or []
            if selected_folders:
                active_folder_path = normalize_windows_path(str(selected_folders[0] or "")).rstrip("/")
        except Exception:
            active_folder_path = ""
        item_path = ""
        try:
            model = index.model()
            if hasattr(model, "mapToSource") and hasattr(model, "sourceModel"):
                source_idx = model.mapToSource(index)
                source_model = model.sourceModel()
                if hasattr(source_model, "filePath"):
                    item_path = normalize_windows_path(str(source_model.filePath(source_idx) or "")).rstrip("/")
            elif hasattr(model, "filePath"):
                item_path = normalize_windows_path(str(model.filePath(index) or "")).rstrip("/")
        except Exception:
            item_path = ""
        is_active_path = bool(active_folder_path and item_path and item_path == active_folder_path)

        if is_selected or is_active_index or is_active_path:
            accent_str = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
            accent = QColor(accent_str)
            
            # Mix 24% foreground text color into the accent color for better readability in both light and dark extremes
            text_color = Theme.get_text_color()
            accent = QColor(Theme.mix(text_color, accent, 0.76))

            opt.font.setBold(True)
            opt.palette.setColor(opt.palette.ColorRole.Highlight, Qt.GlobalColor.transparent)
            opt.palette.setColor(opt.palette.ColorRole.Text, accent)
            opt.palette.setColor(opt.palette.ColorRole.WindowText, accent)
            opt.palette.setColor(opt.palette.ColorRole.HighlightedText, accent)
            if is_active_index or is_active_path:
                opt.state |= QStyle.StateFlag.State_Selected
            opt.state &= ~QStyle.StateFlag.State_HasFocus

        super().paint(painter, opt, index)


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
        layout.setContentsMargins(10, 0, 10, 10)
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

        self.best_toggle = QCheckBox("Best Overall")
        self.best_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.best_toggle.clicked.connect(self._emit_best_changed)
        controls.addWidget(self.best_toggle)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._emit_delete_clicked)
        self.delete_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        controls.addWidget(self.delete_btn, 1)

        layout.addLayout(controls)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(lambda: self.browseRequested.emit(self.slot_name))
        self.browse_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.browse_btn)

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
        for button in (self.browse_btn, self.delete_btn):
            button.setStyleSheet(button_qss)
        self._update_thumb_pixmap()
        self.browse_btn.setMinimumWidth(0)
        self.browse_btn.setMaximumWidth(16777215)
        self.delete_btn.setMinimumWidth(0)
        self.delete_btn.setMaximumWidth(16777215)

        checkbox_qss = (
            f"QCheckBox {{ color: {text_muted}; spacing: 6px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 4px; "
            f"border: 1px solid {btn_border}; background-color: {btn_base}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {accent_raw}; border-color: {accent_raw}; image: url('{check_svg}'); }}"
            f"QCheckBox::indicator:hover {{ border-color: {btn_border_hover}; }}"
        )
        self.keep_toggle.setStyleSheet(checkbox_qss)
        self.best_toggle.setStyleSheet(checkbox_qss)
        for widget in (
            self.name_label,
            self.meta_label,
            self.reasons_label,
            self.best_label,
            self.clear_btn,
            self.thumb_frame,
            self.thumb_label,
            self.keep_toggle,
            self.best_toggle,
            self.browse_btn,
            self.delete_btn,
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
            self.best_toggle.blockSignals(True)
            self.best_toggle.setChecked(False)
            self.best_toggle.blockSignals(False)
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
                        " • ".join(
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
        if self._entry.get("compare_best_in_pair"):
            self.best_label.setText("\u2605 Best in Comparison")
        elif self._entry.get("compare_marked_best"):
            self.best_label.setText("\u2605 Best Overall")
        else:
            self.best_label.setText("")
        self.keep_toggle.blockSignals(True)
        self.keep_toggle.setChecked(bool(self._entry.get("compare_keep_checked")))
        self.keep_toggle.blockSignals(False)
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
            slot.isolateRequested.connect(self.viewer.set_isolated_slot)
            slot.isolateReleased.connect(lambda: self.viewer.set_isolated_slot(""))
            slot.swapStarted.connect(lambda: self.viewer.set_isolated_slot(""))
            slot.keepToggled.connect(self._set_compare_keep_path)
            slot.bestRequested.connect(self._set_compare_best_path)
            slot.deleteRequested.connect(self._delete_compare_path)

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


class Bridge(QObject):
    selectedFolderChanged = Signal(str)
    openVideoRequested = Signal(str, bool, bool, bool, int, int)  # path, autoplay, loop, muted, w, h
    openVideoInPlaceRequested = Signal(str, int, int, int, int, bool, bool, bool, int, int) # path, x, y, w, h, autoplay, loop, muted, pw, ph
    updateVideoRectRequested = Signal(int, int, int, int)
    videoPreprocessingStatus = Signal(str)  # status message (empty = done)
    videoPlaybackStarted = Signal() # Signal that native player has received first frame
    videoSuppressed = Signal(bool) # Signal when video is hidden/suppressed (e.g. by header)
    closeVideoRequested = Signal()
    videoMutedChanged = Signal(bool)
    videoPausedChanged = Signal(bool)

    uiFlagChanged = Signal(str, bool)  # key, value
    compareStateChanged = Signal("QVariantMap")
    compareSelectionStateChanged = Signal(str, list)
    compareKeepPathChanged = Signal(str, bool)
    compareBestPathChanged = Signal(str, bool)
    metadataRequested = Signal(list)
    loadFolderRequested = Signal(str)
    startNativeDragRequested = Signal(list, str, int, int)
    navigateToFolderRequested = Signal(str)
    navigateBackRequested = Signal()
    navigateForwardRequested = Signal()
    navigateUpRequested = Signal()
    refreshFolderRequested = Signal()
    openSettingsDialogRequested = Signal()

    accentColorChanged = Signal(str)
    # Async file ops (so WebEngine UI doesn't freeze during rename)
    fileOpFinished = Signal(str, bool, str, str)  # op, ok, old_path, new_path

    # Media scanning signals
    scanStarted = Signal(str)
    scanFinished = Signal(str, int)  # folder, count
    selectionChanged = Signal(list)  # list of folder paths
    scanProgress = Signal(str, int)  # file_path, percentage
    navigationStateChanged = Signal(bool, bool, bool, str)  # can_back, can_forward, can_up, current_path
    childFoldersListed = Signal(str, list)  # request_id, folders
    mediaCounted = Signal(str, int)  # request_id, count
    mediaListed = Signal(str, list)  # request_id, items
    textProcessingStarted = Signal(str, int)  # stage label, total items
    textProcessingProgress = Signal(str, int, int)  # stage label, current, total
    textProcessingFinished = Signal()
    progressToastsRevealRequested = Signal()
    
    # Update Signals
    updateAvailable = Signal(str, bool)  # version, manual
    updateDownloadProgress = Signal(int)
    updateError = Signal(str)
    
    dragOverFolder = Signal(str)
    collectionsChanged = Signal()
    pinnedFoldersChanged = Signal(list)
    # Native Tooltip Controls
    updateTooltipRequested = Signal(int, bool, str) # count, isCopy, targetFolder
    hideTooltipRequested = Signal()
    conflictDialogRequested = Signal(str, str)
    nativeDragFinished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        print("Bridge: Initializing...")
        self._selected_folders: list[str] = []
        self._active_collection_id: int | None = None
        self._active_collection_name: str = ""
        self._scan_abort = False
        self._scan_lock = threading.Lock()
        self.drag_paths: list[str] = []
        self.drag_target_folder: str = ""
        self._last_dlg_res = None
        self._can_nav_back = False
        self._can_nav_forward = False
        
        appdata = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        self._thumb_dir = appdata / "thumbs"
        self._thumb_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Logging
        self.log_path = appdata / "app.log"
        def _log(msg):
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.ctime()}] {msg}\n")
            except Exception: pass
        self._log = _log
        self._log(f"Bridge: Initializing (Version: {__version__})...")
        
        # Initialize Database
        from app.mediamanager.db.connect import connect_db
        self.db_path = appdata / "mediamanagerx.db"
        self._log(f"DB Path = {self.db_path}")
        self.conn = connect_db(str(self.db_path))
        from app.mediamanager.db.repository import MediaRepository
        self.repo = MediaRepository(self.conn)

        # Migration for AI EXIF fields -> Embedded
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(media_metadata)")
            cols = [c[1] for c in cursor.fetchall()]
            if "exif_tags" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN exif_tags TO embedded_tags")
            elif "embedded_tags" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_tags TEXT")

            if "exif_comments" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN exif_comments TO embedded_comments")
            elif "embedded_comments" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_comments TEXT")

            if "embedded_metadata_parser_version" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_parser_version TEXT")

            if "embedded_metadata_json" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_json TEXT NOT NULL DEFAULT '{}'")

            if "embedded_metadata_summary" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_metadata_summary TEXT")

            if "embedded_ai_prompt" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_prompt TO ai_prompt")
            elif "ai_prompt" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_prompt TEXT")

            if "ai_negative_prompt" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_negative_prompt TEXT")

            if "embedded_ai_params" in cols:
                cursor.execute("ALTER TABLE media_metadata RENAME COLUMN embedded_ai_params TO ai_params")
            elif "ai_params" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN ai_params TEXT")
            self.conn.commit()
        except Exception as e:
            print(f"Migration Error: {e}")

        self.settings = QSettings("G1enB1and", "MediaManagerX")
        Theme.set_theme_mode(str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"))
        self.nam = QNetworkAccessManager(self)
        self.nam.setRedirectPolicy(QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self._update_reply = None
        self._download_reply = None
        self._session_shuffle_seed = random.getrandbits(32)
        
        # Hybrid Fast-Load Cache
        self._disk_cache: dict[str, Path] = {}
        self._disk_cache_key: str = "" # Hash of selected folders list
        self._last_full_scan_key: str = ""
        self._text_processing_generation: int = 0
        self._text_processing_paused: bool = False
        self._text_processing_active: bool = False
        self._text_processing_scope_key: tuple = ("none",)
        self._text_processing_thread: threading.Thread | None = None
        self._compare_paths: dict[str, str] = {"left": "", "right": ""}
        self._compare_keep_paths: set[str] = set()
        self._compare_best_path: str = ""
        self._compare_selection_revision: int = 0
        self._compare_state_emit_pending: bool = False
        self._settings_modal_bottom_restore: bool | None = None

        # Connect blocking signal for cross-thread dialogs
        self.conflictDialogRequested.connect(self._invoke_conflict_dialog, Qt.BlockingQueuedConnection)
        self._last_dlg_res = {"action": "skip", "apply_all": False, "new_existing": "", "new_incoming": ""}

        print(f"Bridge: Initialized (Session Seed: {self._session_shuffle_seed})")

    @Slot(str)
    def debug_log(self, msg: str) -> None:
        """Helper to print logs from the JavaScript side to the terminal."""
        print(f"JS Debug: {msg}")

    def _thumb_key(self, path: Path) -> str:
        s = str(path).replace("\\", "/").lower().encode("utf-8")
        return hashlib.sha1(s).hexdigest()

    def _video_poster_path(self, video_path: Path) -> Path:
        return self._thumb_dir / f"{self._thumb_key(video_path)}.jpg"

    def _video_needs_ascii_runtime_path(self, video_path: Path) -> bool:
        try:
            raw = str(video_path)
        except Exception:
            return False
        return any(ord(ch) > 127 for ch in raw)

    def _video_runtime_alias_path(self, video_path: Path) -> Path:
        runtime_dir = _appdata_runtime_dir() / "video-runtime-aliases"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        suffix = video_path.suffix or ".bin"
        return runtime_dir / f"{self._thumb_key(video_path)}{suffix.lower()}"

    def _video_runtime_path(self, video_path: str | Path) -> str:
        path_obj = Path(video_path)
        if not self._video_needs_ascii_runtime_path(path_obj):
            return str(path_obj)

        alias_path = self._video_runtime_alias_path(path_obj)
        try:
            src_stat = path_obj.stat()
        except Exception:
            return str(path_obj)

        try:
            if alias_path.exists():
                alias_stat = alias_path.stat()
                if alias_stat.st_size == src_stat.st_size and alias_stat.st_mtime >= (src_stat.st_mtime - 1):
                    return str(alias_path)
                alias_path.unlink(missing_ok=True)
        except Exception:
            pass

        try:
            shutil.copy2(str(path_obj), str(alias_path))
            self._log(f"Using ASCII-safe runtime alias for video path: {path_obj.name}")
            return str(alias_path)
        except Exception as exc:
            try:
                self._log(f"Failed to create ASCII-safe runtime alias for '{path_obj.name}': {exc}")
            except Exception:
                pass
            return str(path_obj)

    def _ffmpeg_bin(self) -> str | None:
        return shutil.which("ffmpeg")

    def _ffprobe_bin(self) -> str | None:
        return shutil.which("ffprobe")

    def _ensure_video_poster(self, video_path: Path) -> Path | None:
        """Generate a poster jpg for a video or image using ffmpeg (if missing)."""
        out = self._video_poster_path(video_path)
        if out.exists():
            return out
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            return None
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            ext = video_path.suffix.lower()
            is_vid = ext in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}
            runtime_path = self._video_runtime_path(video_path) if is_vid else str(video_path)
            # For images, don't use -ss as it can fail for 0-duration files
            vf = "thumbnail,scale=min(640\\,iw):-2" if is_vid else "scale=min(640\\,iw):-2"
            
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            if is_vid:
                cmd += ["-ss", "0.5"]
            cmd += ["-i", runtime_path, "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out)]
            
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                return None
            return out if out.exists() else None
        except Exception as e:
            return None
        
    def _is_animated(self, path: Path) -> bool:
        """Check if image is animated (GIF or animated WebP)."""
        suffix = path.suffix.lower()
        if suffix == ".gif":
            return True
        if suffix == ".webp":
            try:
                with open(path, "rb") as f:
                    header = f.read(32)
                if header[0:4] == b"RIFF" and header[8:12] == b"WEBP" and header[12:16] == b"VP8X":
                    flags = header[20]
                    return bool(flags & 2)
            except Exception:
                pass
        return False

    @Slot(list)
    def set_selected_folders(self, folders: list[str]) -> None:
        if folders == self._selected_folders:
            return
        self._selected_folders = folders
        if folders:
            self._active_collection_id = None
            self._active_collection_name = ""
        try:
            # Persistent settings
            settings = QSettings("G1enB1and", "MediaManagerX")
            primary = folders[0] if folders else ""
            settings.setValue("gallery/last_folder", primary)
        except Exception:
            pass
        self.selectionChanged.emit(self._selected_folders)

    def _pinned_folders_setting_key(self) -> str:
        return "folders/pinned"

    def _normalize_pinned_folder_paths(self, folders: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                resolved = str(path_obj.absolute())
            except Exception:
                resolved = path_str
            key = resolved.replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(resolved)
        return normalized

    def _read_pinned_folders(self) -> list[str]:
        raw_value = self.settings.value(self._pinned_folders_setting_key(), "[]", type=str)
        try:
            parsed = json.loads(str(raw_value or "[]"))
        except Exception:
            parsed = []
        if not isinstance(parsed, list):
            parsed = []
        normalized = self._normalize_pinned_folder_paths(parsed)
        if normalized != parsed:
            try:
                self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
            except Exception:
                pass
        return normalized

    def _write_pinned_folders(self, folders: list[str]) -> None:
        normalized = self._normalize_pinned_folder_paths(folders)
        self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
        self.settings.sync()
        self.pinnedFoldersChanged.emit(normalized)

    @Slot(result=list)
    def list_pinned_folders(self) -> list:
        return self._read_pinned_folders()

    @Slot(str, result=bool)
    def is_folder_pinned(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        return any(path.replace("\\", "/").lower() == target_key for path in self._read_pinned_folders())

    @Slot(str, result=bool)
    def pin_folder(self, folder_path: str) -> bool:
        return self.pin_folders([folder_path]) > 0

    @Slot(list, result=int)
    def pin_folders(self, folders: list[str]) -> int:
        existing = self._read_pinned_folders()
        existing_keys = {path.replace("\\", "/").lower() for path in existing}
        added_count = 0
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                if not path_obj.exists() or not path_obj.is_dir():
                    continue
                normalized = str(path_obj.absolute())
            except Exception:
                continue
            key = normalized.replace("\\", "/").lower()
            if key in existing_keys:
                continue
            existing.append(normalized)
            existing_keys.add(key)
            added_count += 1
        if added_count:
            self._write_pinned_folders(existing)
        return added_count

    @Slot(str, result=bool)
    def unpin_folder(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        existing = self._read_pinned_folders()
        remaining = [path for path in existing if path.replace("\\", "/").lower() != target_key]
        if remaining == existing:
            return False
        self._write_pinned_folders(remaining)
        return True

    @Slot(list)
    def set_drag_paths(self, paths: list[str]) -> None:
        """Called from JS to register the actual files being dragged."""
        self.drag_paths = [str(p) for p in paths]
        if not self.drag_paths:
            self.drag_target_folder = ""

    @Slot(str)
    def set_drag_target_folder(self, folder_path: str) -> None:
        self.drag_target_folder = str(folder_path or "")

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

    @Slot(result=list)
    def get_selected_folders(self) -> list:
        return self._selected_folders

    @Slot(result="QVariantMap")
    def get_navigation_state(self) -> dict:
        current_path = self._selected_folders[0] if self._selected_folders else ""
        can_up = False
        if current_path:
            try:
                parent = Path(current_path).parent
                can_up = str(parent) != str(Path(current_path))
            except Exception:
                can_up = False
        return {
            "canBack": self._can_nav_back,
            "canForward": self._can_nav_forward,
            "canUp": can_up,
            "currentPath": current_path,
        }

    def emit_navigation_state(self) -> None:
        state = self.get_navigation_state()
        self.navigationStateChanged.emit(
            bool(state.get("canBack")),
            bool(state.get("canForward")),
            bool(state.get("canUp")),
            str(state.get("currentPath", "")),
        )

    def _list_child_folders_impl(self, folder_path: str) -> list:
        try:
            root = Path(str(folder_path or ""))
            if not root.exists() or not root.is_dir():
                return []
            children: list[dict] = []
            for child in root.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    children.append({
                        "name": child.name or str(child),
                        "path": str(child),
                    })
                except Exception:
                    continue
            children.sort(key=lambda item: str(item.get("name", "")).lower())
            return children
        except Exception:
            return []

    @Slot(str, result=list)
    def list_child_folders(self, folder_path: str) -> list:
        return self._list_child_folders_impl(folder_path)

    @Slot(str, str)
    def list_child_folders_async(self, request_id: str, folder_path: str) -> None:
        req = str(request_id or "")
        path = str(folder_path or "")

        def work() -> None:
            items = self._list_child_folders_impl(path)
            self.childFoldersListed.emit(req, items)

        threading.Thread(target=work, daemon=True).start()

    @Slot(int, result=bool)
    def set_active_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import get_collection
        try:
            collection = get_collection(self.conn, int(collection_id))
            if not collection:
                return False
            self._active_collection_id = int(collection["id"])
            self._active_collection_name = str(collection["name"])
            self._selected_folders = []
            self.selectionChanged.emit([])
            return True
        except Exception:
            return False

    @Slot(result=dict)
    def get_active_collection(self) -> dict:
        if self._active_collection_id is None:
            return {}
        return {"id": self._active_collection_id, "name": self._active_collection_name}

    @Slot(result=list)
    def list_collections(self) -> list:
        from app.mediamanager.db.collections_repo import list_collections
        try:
            return list_collections(self.conn)
        except Exception:
            return []

    @Slot(str, result=dict)
    def create_collection(self, name: str) -> dict:
        from app.mediamanager.db.collections_repo import create_collection
        try:
            created = create_collection(self.conn, name)
            self.collectionsChanged.emit()
            return created
        except Exception:
            return {}

    @Slot(int, str, result=bool)
    def rename_collection(self, collection_id: int, name: str) -> bool:
        from app.mediamanager.db.collections_repo import rename_collection, get_collection
        try:
            ok = rename_collection(self.conn, int(collection_id), name)
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                collection = get_collection(self.conn, int(collection_id))
                self._active_collection_name = str(collection["name"]) if collection else ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, result=bool)
    def delete_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import delete_collection
        try:
            ok = delete_collection(self.conn, int(collection_id))
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                self._active_collection_id = None
                self._active_collection_name = ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, list, result=int)
    def add_paths_to_collection(self, collection_id: int, paths: list[str]) -> int:
        from app.mediamanager.db.collections_repo import add_media_paths_to_collection
        try:
            added = add_media_paths_to_collection(self.conn, int(collection_id), paths)
            self.collectionsChanged.emit()
            if added and self._active_collection_id == int(collection_id):
                self.selectionChanged.emit([])
            return int(added)
        except Exception:
            return 0

    @Slot(list, result=bool)
    def add_paths_to_collection_interactive(self, paths: list[str]) -> bool:
        from app.mediamanager.db.collections_repo import create_collection, list_collections
        clean_paths = [str(path or "").strip() for path in paths if str(path or "").strip()]
        if not clean_paths:
            return False
        try:
            collections = list_collections(self.conn)
            options = ["New collection..."] + [str(collection["name"]) for collection in collections]
            choice, ok = QInputDialog.getItem(
                None,
                "Add to Collection",
                "Collection:",
                options,
                0,
                False,
            )
            if not ok or not choice:
                return False

            if choice == "New collection...":
                name, created_ok = QInputDialog.getText(None, "New Collection", "Collection Name:")
                if not created_ok or not name.strip():
                    return False
                created = create_collection(self.conn, name)
                collection_id = int(created["id"])
            else:
                selected = next((c for c in collections if str(c["name"]) == choice), None)
                if not selected:
                    return False
                collection_id = int(selected["id"])

            added = self.add_paths_to_collection(collection_id, clean_paths)
            return added > 0
        except Exception:
            return False

    def _randomize_enabled(self) -> bool:
        return bool(self.settings.value("gallery/randomize", False, type=bool))

    def _restore_last_enabled(self) -> bool:
        return bool(self.settings.value("gallery/restore_last", False, type=bool))

    def _show_hidden_enabled(self) -> bool:
        return bool(self.settings.value("gallery/show_hidden", False, type=bool))

    def _preview_above_details_enabled(self) -> bool:
        return bool(self.settings.value("ui/preview_above_details", True, type=bool))

    def _start_folder_setting(self) -> str:
        return str(self.settings.value("gallery/start_folder", "", type=str) or "")

    def _last_folder(self) -> str:
        return str(self.settings.value("gallery/last_folder", "", type=str) or "")

    def _gallery_view_mode(self) -> str:
        mode = str(self.settings.value("gallery/view_mode", "masonry", type=str) or "masonry")
        allowed = {
            "masonry",
            "grid_small",
            "grid_medium",
            "grid_large",
            "grid_xlarge",
            "list",
            "content",
            "details",
            "duplicates",
            "similar",
            "similar_only",
        }
        return mode if mode in allowed else "masonry"

    def _gallery_group_by(self) -> str:
        value = str(self.settings.value("gallery/group_by", "none", type=str) or "none")
        allowed = {"none", "date", "duplicates", "similar", "similar_only"}
        return value if value in allowed else "none"

    def _gallery_similarity_threshold(self) -> str:
        value = str(self.settings.value("gallery/similarity_threshold", "low", type=str) or "low")
        allowed = {"very_low", "low", "medium", "high", "very_high"}
        return value if value in allowed else "low"

    def _duplicates_mode_active(self) -> bool:
        return self._gallery_view_mode() == "duplicates" or self._gallery_group_by() == "duplicates"

    def _similar_mode_active(self) -> bool:
        return self._gallery_view_mode() == "similar" or self._gallery_group_by() == "similar"

    def _similar_only_mode_active(self) -> bool:
        return self._gallery_view_mode() == "similar_only" or self._gallery_group_by() == "similar_only"

    def _review_group_mode(self) -> str | None:
        if self._similar_only_mode_active():
            return "similar_only"
        if self._similar_mode_active():
            return "similar"
        if self._duplicates_mode_active():
            return "duplicates"
        return None

    @staticmethod
    def _folder_depth_for_duplicate(entry: dict) -> int:
        try:
            parent = Path(str(entry.get("path", ""))).parent
            parts = [part for part in parent.parts if part not in ("\\", "/")]
            return len(parts)
        except Exception:
            return 0

    @staticmethod
    def _duplicate_metadata_score(entry: dict) -> tuple[int, int]:
        tags = [tag.strip() for tag in str(entry.get("tags") or "").split(",") if tag.strip()]
        filled_fields = sum(
            1
            for key in ("title", "description", "notes", "collection_names", "ai_prompt", "ai_loras", "model_name")
            if str(entry.get(key) or "").strip()
        )
        return (len(set(tags)), filled_fields)

    @staticmethod
    def _split_distinct_text_blocks(values: list[str]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for raw in values:
            text = str(raw or "").replace("\r\n", "\n").strip()
            if not text:
                continue
            blocks = re.split(r"\n\s*\n+", text)
            for block in blocks:
                normalized = block.strip()
                if not normalized:
                    continue
                key = normalized.casefold()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(normalized)
        return merged

    @classmethod
    def _merge_duplicate_text_field(cls, values: list[str]) -> str:
        return "\n\n".join(cls._split_distinct_text_blocks(values))

    @staticmethod
    def _merge_duplicate_scalar_field(values: list[str]) -> str:
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            return value
        return ""

    @staticmethod
    def _duplicate_score(entry: dict) -> tuple:
        color_rank = 1 if str(entry.get("color_variant") or "") == "color" else 0
        folder_depth = Bridge._folder_depth_for_duplicate(entry)
        tag_count, filled_fields = Bridge._duplicate_metadata_score(entry)
        file_size = int(entry.get("file_size") or 0)
        modified_time = int(entry.get("preferred_date") or 0)
        return (
            color_rank,
            folder_depth,
            tag_count,
            filled_fields,
            file_size,
            modified_time,
            str(entry.get("path", "")).lower(),
        )

    def _sort_duplicate_group(self, entries: list[dict]) -> list[dict]:
        ranked = [dict(entry) for entry in entries]
        self._annotate_group_color_variants(ranked)
        ranked.sort(key=self._duplicate_score, reverse=True)
        metadata_scores = [self._duplicate_metadata_score(entry) for entry in ranked]
        folder_depths = [self._folder_depth_for_duplicate(entry) for entry in ranked]
        file_sizes = [int(entry.get("file_size") or 0) for entry in ranked]
        modified_times = [int(entry.get("preferred_date") or 0) for entry in ranked]
        color_modes = [str(entry.get("color_variant") or "") for entry in ranked]
        best_metadata = max(metadata_scores, default=(0, 0))
        best_folder_depth = max(folder_depths, default=0)
        largest_file_size = max(file_sizes, default=0)
        smallest_file_size = min(file_sizes, default=0)
        best_modified = max(modified_times, default=0)
        has_color_variants = "color" in color_modes and "grayscale" in color_modes
        unique_best_metadata = metadata_scores.count(best_metadata) == 1 and best_metadata > (0, 0)
        unique_best_folder = folder_depths.count(best_folder_depth) == 1 and best_folder_depth > 1
        unique_largest_file = file_sizes.count(largest_file_size) == 1 and largest_file_size > smallest_file_size
        unique_smallest_file = file_sizes.count(smallest_file_size) == 1 and largest_file_size > smallest_file_size
        unique_best_modified = modified_times.count(best_modified) == 1 and best_modified > 0
        for index, entry in enumerate(ranked):
            entry["duplicate_keep_suggestion"] = index == 0
            entry["duplicate_group_position"] = index
            entry["duplicate_folder_depth"] = self._folder_depth_for_duplicate(entry)
            reasons: list[str] = []
            if has_color_variants:
                if str(entry.get("color_variant") or "") == "color":
                    reasons.append("Color version")
                elif str(entry.get("color_variant") or "") == "grayscale":
                    reasons.append("Grayscale version")
            if unique_best_metadata and self._duplicate_metadata_score(entry) == best_metadata:
                reasons.append("Most metadata")
            if unique_best_folder and self._folder_depth_for_duplicate(entry) == best_folder_depth:
                reasons.append("Best folder organization")
            if unique_largest_file and int(entry.get("file_size") or 0) == largest_file_size:
                reasons.append("Largest file size")
            if unique_smallest_file and int(entry.get("file_size") or 0) == smallest_file_size:
                reasons.append("Smallest file size")
            if unique_best_modified and int(entry.get("preferred_date") or 0) == best_modified:
                reasons.append("Newest edit")
            entry["duplicate_category_reasons"] = reasons
            entry["duplicate_best_reason"] = " • ".join(reasons)
            entry["duplicate_is_overall_best"] = index == 0
        return ranked

    def _rank_duplicate_group(self, entries: list[dict], extra_positive_categories: list[dict] | None = None) -> list[dict]:
        ranked = [dict(entry) for entry in entries]
        self._annotate_group_color_variants(ranked)

        crop_policy = str(self.settings.value("duplicate/rules/crop_policy", "prefer_full", type=str) or "prefer_full")
        color_policy = str(self.settings.value("duplicate/rules/color_policy", "prefer_color", type=str) or "prefer_color")
        file_size_policy = str(self.settings.value("duplicate/rules/file_size_policy", "prefer_largest", type=str) or "prefer_largest")
        format_order_raw = str(self.settings.value("duplicate/rules/format_order", "[]", type=str) or "[]")
        priorities_raw = str(self.settings.value("duplicate/priorities/order", "[]", type=str) or "[]")
        try:
            format_order = [str(item).strip().upper() for item in json.loads(format_order_raw or "[]") if str(item).strip()]
        except Exception:
            format_order = []
        if not format_order:
            format_order = ["PNG", "WEBP", "JPEG", "RAW", "TIFF", "BMP", "GIF", "HEIC", "AVIF"]
        try:
            configured_priorities = [str(item).strip() for item in json.loads(priorities_raw or "[]") if str(item).strip()]
        except Exception:
            configured_priorities = []
        if not configured_priorities:
            configured_priorities = [
                "File Size",
                "Resolution",
                "File Format",
                "Compression",
                "Color / Grey Preference",
                "Text / No Text Preference",
                "Cropped / Full Preference",
            ]

        def _normalized_aspect_ratio(entry: dict) -> tuple[int, int] | None:
            width = int(entry.get("width") or 0)
            height = int(entry.get("height") or 0)
            if width <= 0 or height <= 0 or entry.get("media_type") != "image":
                return None
            divisor = gcd(width, height)
            if divisor <= 0:
                return None
            return (width // divisor, height // divisor)

        def _display_file_format(entry: dict) -> str:
            suffix = Path(str(entry.get("path") or "")).suffix.lower()
            if suffix in {".jpg", ".jpeg", ".jpe", ".jfif"}:
                return "JPEG"
            if suffix in {".png"}:
                return "PNG"
            if suffix in {".webp"}:
                return "WEBP"
            if suffix in {".tif", ".tiff"}:
                return "TIFF"
            if suffix in {".bmp"}:
                return "BMP"
            if suffix in {".gif"}:
                return "GIF"
            if suffix in {".heic", ".heif"}:
                return "HEIC"
            if suffix in {".avif"}:
                return "AVIF"
            if suffix in {".raw", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".rw2", ".raf", ".srw"}:
                return "RAW"
            return suffix.lstrip(".").upper() or "UNKNOWN"

        def _format_score(entry: dict) -> int:
            fmt = str(entry.get("duplicate_file_format") or "")
            try:
                idx = format_order.index(fmt)
            except ValueError:
                idx = len(format_order)
            return len(format_order) - idx

        def _original_timestamp(entry: dict) -> int:
            for key in ("exif_date_taken", "metadata_date"):
                raw_value = entry.get(key)
                value = raw_value if isinstance(raw_value, int) else self._iso_to_ns(raw_value)
                if value > 0:
                    return value
            value = self._original_file_date_ns(entry)
            if value > 0:
                return value
            raw_value = entry.get("file_created_time")
            value = raw_value if isinstance(raw_value, int) else self._iso_to_ns(raw_value)
            if value > 0:
                return value
            return 0

        def _modified_timestamp(entry: dict) -> int:
            raw_value = entry.get("modified_time")
            return raw_value if isinstance(raw_value, int) else self._iso_to_ns(raw_value)

        for entry in ranked:
            entry["duplicate_folder_depth"] = self._folder_depth_for_duplicate(entry)
            entry["duplicate_file_format"] = _display_file_format(entry)
            original_time = _original_timestamp(entry)
            modified_time = _modified_timestamp(entry)
            entry["duplicate_original_timestamp"] = original_time
            entry["duplicate_modified_timestamp"] = modified_time
            entry["duplicate_is_edit_variant"] = (
                original_time > 0
                and modified_time > 0
                and modified_time > original_time + (5 * 60 * 1_000_000_000)
            )
            entry["duplicate_crop_variant"] = ""
            entry["duplicate_size_variant"] = ""

        color_modes = [str(entry.get("color_variant") or "") for entry in ranked]
        has_color_variants = "color" in color_modes and "grayscale" in color_modes
        positive_reasons: list[list[str]] = [[] for _ in ranked]
        informative_reasons: list[list[str]] = [[] for _ in ranked]
        candidate_indices = list(range(len(ranked)))

        if has_color_variants:
            for idx, entry in enumerate(ranked):
                mode = str(entry.get("color_variant") or "")
                if mode == "color":
                    informative_reasons[idx].append("Color version")
                elif mode == "grayscale":
                    informative_reasons[idx].append("Grayscale version")
            if color_policy == "prefer_color":
                preferred = [idx for idx, entry in enumerate(ranked) if str(entry.get("color_variant") or "") == "color"]
                if preferred:
                    candidate_indices = preferred
            elif color_policy == "prefer_bw":
                preferred = [idx for idx, entry in enumerate(ranked) if str(entry.get("color_variant") or "") == "grayscale"]
                if preferred:
                    candidate_indices = preferred

        aspect_ratios = [_normalized_aspect_ratio(entry) for entry in ranked]
        image_areas = [int(entry.get("width") or 0) * int(entry.get("height") or 0) for entry in ranked]
        valid_ratio_indices = [idx for idx, ratio in enumerate(aspect_ratios) if ratio is not None and image_areas[idx] > 0]
        distinct_ratios = {aspect_ratios[idx] for idx in valid_ratio_indices}
        if len(distinct_ratios) > 1:
            full_frame_idx = max(valid_ratio_indices, key=lambda idx: image_areas[idx], default=-1)
            full_frame_area = image_areas[full_frame_idx] if full_frame_idx >= 0 else 0
            full_frame_ratio = aspect_ratios[full_frame_idx] if full_frame_idx >= 0 else None
            unique_full_frame = full_frame_idx >= 0 and image_areas.count(full_frame_area) == 1
            cropped_candidates = [
                idx for idx in valid_ratio_indices
                if idx != full_frame_idx
                and aspect_ratios[idx] != full_frame_ratio
                and image_areas[idx] < full_frame_area
            ]
            if unique_full_frame:
                ranked[full_frame_idx]["duplicate_crop_variant"] = "full"
                informative_reasons[full_frame_idx].append("Full frame")
            for idx in cropped_candidates:
                ranked[idx]["duplicate_crop_variant"] = "cropped"
                informative_reasons[idx].append("Cropped version")
            if crop_policy == "prefer_full" and unique_full_frame:
                candidate_indices = [idx for idx in candidate_indices if idx == full_frame_idx] or candidate_indices
            elif crop_policy == "prefer_cropped" and cropped_candidates:
                preferred_cropped = [idx for idx in candidate_indices if idx in cropped_candidates]
                if preferred_cropped:
                    candidate_indices = preferred_cropped

        edited_indices = [idx for idx, entry in enumerate(ranked) if entry.get("duplicate_is_edit_variant")]
        if edited_indices:
            edited_modified_times = [int(ranked[idx].get("duplicate_modified_timestamp") or 0) for idx in edited_indices]
            newest_edit_time = max(edited_modified_times, default=0)
            if newest_edit_time > 0 and edited_modified_times.count(newest_edit_time) == 1:
                informative_reasons[edited_indices[edited_modified_times.index(newest_edit_time)]].append("Newer edit")
            original_indices = [
                idx for idx, entry in enumerate(ranked)
                if int(entry.get("duplicate_original_timestamp") or 0) > 0 and not entry.get("duplicate_is_edit_variant")
            ]
            if len(original_indices) == 1:
                informative_reasons[original_indices[0]].append("Original")

        file_sizes = [int(entry.get("file_size") or 0) for entry in ranked]
        largest_file_size = max(file_sizes, default=0)
        smallest_file_size = min(file_sizes, default=0)
        if largest_file_size > smallest_file_size and file_sizes.count(largest_file_size) == 1:
            ranked[file_sizes.index(largest_file_size)]["duplicate_size_variant"] = "largest"
            informative_reasons[file_sizes.index(largest_file_size)].append("Largest file size")
        if largest_file_size > smallest_file_size and file_sizes.count(smallest_file_size) == 1:
            ranked[file_sizes.index(smallest_file_size)]["duplicate_size_variant"] = "smallest"
            informative_reasons[file_sizes.index(smallest_file_size)].append("Smallest file size")
        if file_size_policy == "prefer_smallest":
            preferred_small = [idx for idx in candidate_indices if int(ranked[idx].get("file_size") or 0) == smallest_file_size]
            if preferred_small and largest_file_size > smallest_file_size:
                candidate_indices = preferred_small

        format_scores = [_format_score(entry) for entry in ranked]
        best_format_score = max(format_scores, default=0)
        if best_format_score > 0 and format_scores.count(best_format_score) == 1:
            fmt_idx = format_scores.index(best_format_score)
            informative_reasons[fmt_idx].append(f"Preferred format ({ranked[fmt_idx].get('duplicate_file_format')})")

        priority_category_defs: dict[str, dict] = {
            "File Size": {
                "label": "Smallest file size" if file_size_policy == "prefer_smallest" else "Largest file size",
                "value": (lambda entry: -int(entry.get("file_size") or 0)) if file_size_policy == "prefer_smallest" else (lambda entry: int(entry.get("file_size") or 0)),
                "enabled": lambda values: max(values, default=0) > min(values, default=0),
            },
            "Resolution": {
                "label": "Highest resolution",
                "value": lambda entry: int(entry.get("width") or 0) * int(entry.get("height") or 0),
                "enabled": lambda values: max(values, default=0) > min(values, default=0),
            },
            "File Format": {
                "label": "Preferred format",
                "value": lambda entry: _format_score(entry),
                "enabled": lambda values: max(values, default=0) > min(values, default=0) and max(values, default=0) > 0,
            },
            "Compression": {
                "label": "Compression",
                "value": lambda entry: 0,
                "enabled": lambda values: False,
            },
            "Color / Grey Preference": {
                "label": "Black & White version" if color_policy == "prefer_bw" else "Color version",
                "value": (
                    (lambda entry: 1 if str(entry.get("color_variant") or "") == "grayscale" else 0)
                    if color_policy == "prefer_bw"
                    else (lambda entry: 1 if str(entry.get("color_variant") or "") == "color" else 0)
                ),
                "enabled": lambda values: max(values, default=0) > min(values, default=0),
            },
            "Text / No Text Preference": {
                "label": "Text preference",
                "value": lambda entry: 0,
                "enabled": lambda values: False,
            },
            "Cropped / Full Preference": {
                "label": "Cropped version" if crop_policy == "prefer_cropped" else "Full frame",
                "value": (
                    (lambda entry: 1 if str(entry.get("duplicate_crop_variant") or "") == "cropped" else 0)
                    if crop_policy == "prefer_cropped"
                    else (lambda entry: 1 if str(entry.get("duplicate_crop_variant") or "") == "full" else 0)
                ),
                "enabled": lambda values: max(values, default=0) > min(values, default=0),
            },
        }
        positive_categories = [priority_category_defs[name] for name in configured_priorities if name in priority_category_defs]
        if extra_positive_categories:
            resolution_idx = next((i for i, cat in enumerate(positive_categories) if cat["label"] == "Highest resolution"), len(positive_categories))
            positive_categories[resolution_idx:resolution_idx] = list(extra_positive_categories)
        positive_categories.extend([
            {
                "label": "Most metadata",
                "value": lambda entry: self._duplicate_metadata_score(entry),
                "enabled": lambda values: max(values, default=(0, 0)) > (0, 0),
            },
            {
                "label": "Best folder organization",
                "value": lambda entry: int(entry.get("duplicate_folder_depth") or 0),
                "enabled": lambda values: max(values, default=0) > 1,
            },
            {
                "label": "Newer edit",
                "value": lambda entry: (entry.get("duplicate_modified_timestamp") or 0) if entry.get("duplicate_is_edit_variant") else 0,
                "enabled": lambda values: max(values, default=0) > min(values, default=0) and max(values, default=0) > 0,
            },
        ])

        while len(candidate_indices) > 1:
            round_winners: set[int] = set()
            for category in positive_categories:
                values = [category["value"](ranked[idx]) for idx in candidate_indices]
                if not values or not category["enabled"](values):
                    continue
                best_value = max(values)
                winners = [idx for idx in candidate_indices if category["value"](ranked[idx]) == best_value]
                if len(winners) != 1:
                    continue
                winner = winners[0]
                if category["label"] not in positive_reasons[winner]:
                    positive_reasons[winner].append(category["label"])
                round_winners.add(winner)
            if not round_winners:
                break
            survivors = [idx for idx in candidate_indices if idx in round_winners]
            if len(survivors) == len(candidate_indices):
                break
            candidate_indices = survivors

        def final_score(idx: int) -> tuple:
            entry = ranked[idx]
            priority_scores: list[int] = []
            for name in configured_priorities:
                if name == "File Size":
                    priority_scores.append(-int(entry.get("file_size") or 0) if file_size_policy == "prefer_smallest" else int(entry.get("file_size") or 0))
                elif name == "Resolution":
                    priority_scores.append(int(entry.get("width") or 0) * int(entry.get("height") or 0))
                elif name == "File Format":
                    priority_scores.append(_format_score(entry))
                elif name == "Compression":
                    priority_scores.append(0)
                elif name == "Color / Grey Preference":
                    if color_policy == "prefer_bw":
                        priority_scores.append(1 if str(entry.get("color_variant") or "") == "grayscale" else 0)
                    elif color_policy == "prefer_color":
                        priority_scores.append(1 if str(entry.get("color_variant") or "") == "color" else 0)
                    else:
                        priority_scores.append(0)
                elif name == "Text / No Text Preference":
                    priority_scores.append(0)
                elif name == "Cropped / Full Preference":
                    if crop_policy == "prefer_cropped":
                        priority_scores.append(1 if str(entry.get("duplicate_crop_variant") or "") == "cropped" else 0)
                    elif crop_policy == "prefer_full":
                        priority_scores.append(1 if str(entry.get("duplicate_crop_variant") or "") == "full" else 0)
                    else:
                        priority_scores.append(0)
            file_size = int(entry.get("file_size") or 0)
            file_size_fallback = -file_size if file_size_policy == "prefer_smallest" else file_size
            area = int(entry.get("width") or 0) * int(entry.get("height") or 0)
            folder_depth = int(entry.get("duplicate_folder_depth") or 0)
            tag_count, filled_fields = self._duplicate_metadata_score(entry)
            preferred_raw = entry.get("preferred_date")
            modified_time = preferred_raw if isinstance(preferred_raw, int) else self._preferred_date_ns(entry)
            return (
                len(positive_reasons[idx]),
                *priority_scores,
                file_size_fallback,
                area,
                _format_score(entry),
                folder_depth,
                tag_count,
                filled_fields,
                modified_time,
                str(entry.get("path", "")).lower(),
            )

        contenders = candidate_indices or list(range(len(ranked)))
        best_idx = max(contenders, key=final_score, default=0)
        order = sorted(range(len(ranked)), key=final_score, reverse=True)
        sorted_ranked = [ranked[idx] for idx in order]

        for position, original_idx in enumerate(order):
            entry = sorted_ranked[position]
            reasons = positive_reasons[original_idx] + [
                reason for reason in informative_reasons[original_idx]
                if reason not in positive_reasons[original_idx]
            ]
            entry["duplicate_keep_suggestion"] = original_idx == best_idx
            entry["duplicate_group_position"] = position
            entry["duplicate_category_reasons"] = reasons
            entry["duplicate_best_reason"] = " • ".join(reasons)
            entry["duplicate_is_overall_best"] = original_idx == best_idx
        return sorted_ranked

    def _build_duplicate_entries(self, entries: list[dict], sort_by: str) -> list[dict]:
        media_entries = [dict(entry) for entry in entries if not entry.get("is_folder")]
        counts = Counter(
            str(entry.get("content_hash") or "").strip()
            for entry in media_entries
            if str(entry.get("content_hash") or "").strip()
        )
        duplicate_groups: dict[str, list[dict]] = {}
        for entry in media_entries:
            group_key = str(entry.get("content_hash") or "").strip()
            if counts.get(group_key, 0) < 2:
                continue
            duplicate_groups.setdefault(group_key, []).append(entry)

        if not duplicate_groups:
            return []

        group_rows: list[tuple[tuple, list[dict]]] = []
        for group_key, group_entries in duplicate_groups.items():
            sorted_group = self._rank_duplicate_group(group_entries)
            kept_size = int(sorted_group[0].get("file_size") or 0) if sorted_group else 0
            total_size = sum(int(entry.get("file_size") or 0) for entry in sorted_group)
            savings = max(0, total_size - kept_size)
            for entry in sorted_group:
                entry["duplicate_group_key"] = group_key
                entry["duplicate_group_size"] = len(sorted_group)
                entry["duplicate_space_savings"] = savings
            best = sorted_group[0]
            name = Path(str(best.get("path", ""))).name.lower()
            if sort_by == "name_desc":
                order_key = (name, len(sorted_group), savings)
            elif sort_by == "date_asc":
                order_key = (best.get("preferred_date") or self._preferred_date_ns(best) or 0, -len(sorted_group), -savings, name)
            elif sort_by == "date_desc":
                order_key = (-(best.get("preferred_date") or self._preferred_date_ns(best) or 0), -len(sorted_group), -savings, name)
            elif sort_by == "size_asc":
                order_key = (savings, -len(sorted_group), name)
            else:
                order_key = (-savings, -len(sorted_group), name)
            group_rows.append((order_key, sorted_group))

        reverse = sort_by == "name_desc"
        group_rows.sort(key=lambda row: row[0], reverse=reverse)

        flattened: list[dict] = []
        for _, group in group_rows:
            flattened.extend(group)
        return flattened

    def _build_similar_entries(self, entries: list[dict], sort_by: str, *, include_exact: bool, threshold: int, bucket_prefix: int) -> list[dict]:
        from app.mediamanager.utils.hashing import phash_distance

        candidates = [
            dict(entry)
            for entry in entries
            if not entry.get("is_folder") and (str(entry.get("content_hash") or "").strip() or str(entry.get("phash") or "").strip())
        ]
        if not include_exact:
            unique_candidates: list[dict] = []
            exact_groups: dict[str, list[dict]] = {}
            for entry in candidates:
                content_hash = str(entry.get("content_hash") or "").strip()
                if content_hash:
                    exact_groups.setdefault(content_hash, []).append(entry)
                else:
                    unique_candidates.append(entry)
            for grouped_entries in exact_groups.values():
                if len(grouped_entries) == 1:
                    unique_candidates.append(grouped_entries[0])
                else:
                    unique_candidates.append(self._rank_duplicate_group(grouped_entries)[0])
            candidates = unique_candidates
        if len(candidates) < 2:
            return []

        parents = list(range(len(candidates)))

        def find(idx: int) -> int:
            while parents[idx] != idx:
                parents[idx] = parents[parents[idx]]
                idx = parents[idx]
            return idx

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        buckets: dict[str, list[int]] = {}
        hash_groups: dict[str, list[int]] = {}
        for index, entry in enumerate(candidates):
            phash = str(entry.get("phash") or "")
            bucket = phash[:bucket_prefix] if bucket_prefix > 0 else "*"
            buckets.setdefault(bucket, []).append(index)
            content_hash = str(entry.get("content_hash") or "").strip()
            if include_exact and content_hash:
                hash_groups.setdefault(content_hash, []).append(index)

        for group_items in hash_groups.values():
            if len(group_items) < 2:
                continue
            anchor = group_items[0]
            for other in group_items[1:]:
                union(anchor, other)

        for bucket_items in buckets.values():
            for pos, left_idx in enumerate(bucket_items):
                if candidates[left_idx].get("media_type") != "image":
                    continue
                left_hash = candidates[left_idx].get("phash") or ""
                if not left_hash:
                    continue
                for right_idx in bucket_items[pos + 1:]:
                    if candidates[right_idx].get("media_type") != "image":
                        continue
                    right_hash = candidates[right_idx].get("phash") or ""
                    if not right_hash:
                        continue
                    distance = phash_distance(left_hash, right_hash)
                    if distance <= threshold and (include_exact or distance > 0):
                        union(left_idx, right_idx)

        groups: dict[int, list[dict]] = {}
        for index, entry in enumerate(candidates):
            groups.setdefault(find(index), []).append(entry)

        similar_groups = [group for group in groups.values() if len(group) > 1]
        if not similar_groups:
            return []

        group_rows: list[tuple[tuple, list[dict]]] = []
        for group_index, group_entries in enumerate(similar_groups, start=1):
            sorted_group = self._rank_duplicate_group(
                group_entries,
                extra_positive_categories=[
                    {
                        "label": "Highest resolution",
                        "value": lambda entry: int(entry.get("width") or 0) * int(entry.get("height") or 0),
                        "enabled": lambda values: max(values, default=0) > min(values, default=0),
                    },
                ],
            )
            areas = [int(entry.get("width") or 0) * int(entry.get("height") or 0) for entry in sorted_group]
            max_area = max(areas)
            min_area = min(areas)
            unique_highest_area = areas.count(max_area) == 1 and max_area > min_area
            unique_lowest_area = areas.count(min_area) == 1 and max_area > min_area
            for entry in sorted_group:
                area = int(entry.get("width") or 0) * int(entry.get("height") or 0)
                reasons = list(entry.get("duplicate_category_reasons") or [])
                if unique_lowest_area and area == min_area:
                    reasons.append("Downscaled copy")
                entry["duplicate_category_reasons"] = list(dict.fromkeys(reasons))
                entry["duplicate_best_reason"] = " • ".join(entry["duplicate_category_reasons"])
                entry["review_group_mode"] = "similar" if include_exact else "similar_only"
                entry["similar_group_distance_threshold"] = threshold
                entry["similar_group_key"] = f"similar-{group_index}"
                entry["duplicate_group_key"] = entry["similar_group_key"]
                entry["duplicate_group_size"] = len(sorted_group)
            best = sorted_group[0]
            name = Path(str(best.get("path", ""))).name.lower()
            area_score = int(best.get("width") or 0) * int(best.get("height") or 0)
            order_key = (-area_score, -len(sorted_group), name)
            if sort_by == "name_desc":
                order_key = (name, -area_score, -len(sorted_group))
            group_rows.append((order_key, sorted_group))

        group_rows.sort(key=lambda row: row[0], reverse=(sort_by == "name_desc"))
        flattened: list[dict] = []
        for _, group in group_rows:
            flattened.extend(group)
        return flattened

    def _annotate_group_color_variants(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import classify_image_color_mode

        cache = getattr(self, "_color_variant_cache", None)
        if cache is None:
            cache = {}
            self._color_variant_cache = cache

        for entry in entries:
            if entry.get("is_folder") or entry.get("media_type") != "image" or str(entry.get("color_variant") or "").strip():
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            cached = cache.get(path)
            if cached is None:
                try:
                    p = Path(path)
                    cached = classify_image_color_mode(p) if p.exists() and p.is_file() else ""
                except Exception:
                    cached = ""
                cache[path] = cached
            if cached:
                entry["color_variant"] = cached

    def _backfill_scope_phashes(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import calculate_image_phash

        updates: list[tuple[str, str]] = []
        for entry in entries:
            if entry.get("is_folder") or entry.get("media_type") != "image" or str(entry.get("phash") or "").strip():
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                phash = calculate_image_phash(p)
            except Exception:
                phash = ""
            if not phash:
                continue
            entry["phash"] = phash
            updates.append((phash, path))
        if not updates:
            return
        try:
            self.conn.executemany("UPDATE media_items SET phash = ? WHERE path = ?", updates)
            self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"pHash backfill failed: {exc}")
            except Exception:
                pass

    @staticmethod
    def _text_stage_label(stage_key: str) -> str:
        if stage_key == "waiting":
            return "Detecting Text (Waiting for Scan)"
        return "Detecting Text"

    def _text_processing_should_continue(self, generation: int | None = None) -> bool:
        if generation is None:
            return not self._text_processing_paused
        return generation == self._text_processing_generation and not self._text_processing_paused

    def _cancel_text_processing(self) -> None:
        self._text_processing_generation += 1
        self._text_processing_paused = False
        self._text_processing_active = False
        self._text_processing_scope_key = ("none",)
        self._text_processing_thread = None

    def _current_text_scope_key(self, folders: list[str] | None = None, collection_id: int | None = None) -> tuple:
        if folders:
            return ("folders", tuple(sorted(str(folder or "") for folder in folders if str(folder or "").strip())))
        if collection_id is not None:
            return ("collection", int(collection_id))
        if self._selected_folders:
            return ("folders", tuple(sorted(str(folder or "") for folder in self._selected_folders if str(folder or "").strip())))
        if self._active_collection_id is not None:
            return ("collection", int(self._active_collection_id))
        return ("none",)

    def _collect_text_scope_entries(self, folders: list[str] | None = None, collection_id: int | None = None) -> list[dict]:
        if folders:
            return self._get_reconciled_candidates(folders, "all", "")
        if collection_id is not None:
            return self._get_collection_candidates(collection_id, "all", "")
        if self._selected_folders:
            return self._get_reconciled_candidates(self._selected_folders, "all", "")
        if self._active_collection_id is not None:
            return self._get_collection_candidates(self._active_collection_id, "all", "")
        return []

    def _ensure_background_text_processing(
        self,
        folders: list[str] | None = None,
        collection_id: int | None = None,
        *,
        allow_concurrent_scan: bool = False,
    ) -> None:
        scope_key = self._current_text_scope_key(folders, collection_id)
        if scope_key == ("none",):
            return
        if self._text_processing_active and not self._text_processing_paused and self._text_processing_scope_key == scope_key:
            return

        self._text_processing_generation += 1
        generation = self._text_processing_generation
        self._text_processing_paused = False
        self._text_processing_active = True
        self._text_processing_scope_key = scope_key
        if self._scan_lock.locked() and not allow_concurrent_scan:
            self.textProcessingStarted.emit(self._text_stage_label("waiting"), 0)

        resolved_folders = list(folders) if folders else (list(self._selected_folders) if self._selected_folders else [])
        resolved_collection_id = collection_id if collection_id is not None else self._active_collection_id

        def work() -> None:
            try:
                if allow_concurrent_scan:
                    if not self._text_processing_should_continue(generation):
                        return
                    entries = self._collect_text_scope_entries(resolved_folders, resolved_collection_id)
                    if not entries:
                        return
                    self._backfill_scope_text_detection(entries, generation)
                else:
                    with self._scan_lock:
                        if not self._text_processing_should_continue(generation):
                            return
                        entries = self._collect_text_scope_entries(resolved_folders, resolved_collection_id)
                        if not entries:
                            return
                        self._backfill_scope_text_detection(entries, generation)
            except Exception as exc:
                try:
                    self._log(f"Background text processing failed: {exc}")
                except Exception:
                    pass
            finally:
                if generation == self._text_processing_generation:
                    self._text_processing_active = False
                    self._text_processing_thread = None

        thread = threading.Thread(target=work, daemon=True, name="text-processing")
        self._text_processing_thread = thread
        thread.start()

    @Slot()
    def resume_text_processing(self) -> None:
        self._ensure_background_text_processing(allow_concurrent_scan=True)

    @Slot()
    def pause_text_processing(self) -> None:
        self._text_processing_paused = True

    @Slot()
    def reveal_progress_toasts(self) -> None:
        self.progressToastsRevealRequested.emit()

    def _backfill_scope_text_detection(self, entries: list[dict], generation: int | None = None) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_DETECTION_VERSION, detect_text_presence
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and not (
                entry.get("text_detected") is not None
                and int(entry.get("text_detection_version") or 0) >= TEXT_DETECTION_VERSION
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("detected"), total_eligible)
        updates: list[tuple[int, float, int, str]] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder"):
                continue
            if (
                entry.get("text_detected") is not None
                and int(entry.get("text_detection_version") or 0) >= TEXT_DETECTION_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("detected"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_detected, text_score = detect_text_presence(analysis_path, source_path=path)
            except Exception:
                text_detected, text_score = False, 0.0
            entry["text_detected"] = bool(text_detected)
            entry["text_detection_score"] = float(text_score or 0.0)
            entry["text_detection_version"] = TEXT_DETECTION_VERSION
            updates.append((1 if text_detected else 0, float(text_score or 0.0), TEXT_DETECTION_VERSION, path))
        try:
            if updates:
                self.conn.executemany(
                    "UPDATE media_items SET text_detected = ?, text_detection_score = ?, text_detection_version = ? WHERE path = ?",
                    updates,
                )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text detection backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible and completed:
                self.textProcessingFinished.emit()
        return completed

    def _backfill_scope_text_more_likely(self, entries: list[dict], generation: int | None = None) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_MORE_LIKELY_VERSION, verify_text_presence_opencv
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and bool(entry.get("text_detected"))
            and not (
                entry.get("text_more_likely") is not None
                and int(entry.get("text_more_likely_version") or 0) >= TEXT_MORE_LIKELY_VERSION
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("more_likely"), total_eligible)
        updates: list[tuple[int, float, int, str]] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder") or not bool(entry.get("text_detected")):
                continue
            if (
                entry.get("text_more_likely") is not None
                and int(entry.get("text_more_likely_version") or 0) >= TEXT_MORE_LIKELY_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("more_likely"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_more_likely, score = verify_text_presence_opencv(analysis_path)
            except Exception:
                text_more_likely, score = False, 0.0
            entry["text_more_likely"] = bool(text_more_likely)
            entry["text_more_likely_score"] = float(score or 0.0)
            entry["text_more_likely_version"] = TEXT_MORE_LIKELY_VERSION
            updates.append((1 if text_more_likely else 0, float(score or 0.0), TEXT_MORE_LIKELY_VERSION, path))
        try:
            if updates:
                self.conn.executemany(
                    "UPDATE media_items SET text_more_likely = ?, text_more_likely_score = ?, text_more_likely_version = ? WHERE path = ?",
                    updates,
                )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text more likely backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible:
                self.textProcessingFinished.emit()
        return completed

    def _backfill_scope_text_verification(self, entries: list[dict], generation: int | None = None) -> bool:
        from app.mediamanager.utils.text_detection import TEXT_VERIFICATION_VERSION, verify_text_presence_windows_ocr
        from app.mediamanager.db.media_repo import add_media_item

        eligible = [
            entry for entry in entries
            if not entry.get("is_folder")
            and bool(entry.get("text_more_likely"))
            and not (
                entry.get("text_verified") is not None
                and int(entry.get("text_verification_version") or 0) >= TEXT_VERIFICATION_VERSION
            )
        ]
        total_eligible = len(eligible)
        if total_eligible:
            self.textProcessingStarted.emit(self._text_stage_label("verified"), total_eligible)
        updates: list[tuple[int, float, int, str]] = []
        processed = 0
        completed = True
        for entry in entries:
            if not self._text_processing_should_continue(generation):
                completed = False
                break
            if entry.get("is_folder") or not bool(entry.get("text_more_likely")):
                continue
            if (
                entry.get("text_verified") is not None
                and int(entry.get("text_verification_version") or 0) >= TEXT_VERIFICATION_VERSION
            ):
                continue
            processed += 1
            self.textProcessingProgress.emit(self._text_stage_label("verified"), processed, total_eligible)
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                if int(entry.get("id") or -1) < 0:
                    media_type = str(entry.get("media_type") or "")
                    real_path = str(entry.get("_real_path") or path)
                    media_id = add_media_item(self.conn, real_path, media_type)
                    entry["id"] = media_id
                media_type = str(entry.get("media_type") or "")
                analysis_path = p
                if media_type == "video":
                    poster = self._ensure_video_poster(p)
                    if not poster or not poster.exists():
                        continue
                    analysis_path = poster
                elif media_type != "image":
                    continue
                text_verified, verify_score = verify_text_presence_windows_ocr(analysis_path)
            except Exception:
                text_verified, verify_score = False, 0.0
            entry["text_verified"] = bool(text_verified)
            entry["text_verification_score"] = float(verify_score or 0.0)
            entry["text_verification_version"] = TEXT_VERIFICATION_VERSION
            updates.append((1 if text_verified else 0, float(verify_score or 0.0), TEXT_VERIFICATION_VERSION, path))
        try:
            if updates:
                self.conn.executemany(
                    "UPDATE media_items SET text_verified = ?, text_verification_score = ?, text_verification_version = ? WHERE path = ?",
                    updates,
                )
                self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"text verification backfill failed: {exc}")
            except Exception:
                pass
        finally:
            if total_eligible:
                self.textProcessingFinished.emit()
        return completed

    def _backfill_scope_content_hashes(self, entries: list[dict]) -> None:
        from app.mediamanager.utils.hashing import calculate_file_hash

        updates: list[tuple[str, str]] = []
        for entry in entries:
            if entry.get("is_folder") or str(entry.get("content_hash") or "").strip():
                continue
            path = str(entry.get("path") or "").strip()
            if not path:
                continue
            try:
                p = Path(path)
                if not p.exists() or not p.is_file():
                    continue
                content_hash = calculate_file_hash(p)
            except Exception:
                content_hash = ""
            if not content_hash:
                continue
            entry["content_hash"] = content_hash
            updates.append((content_hash, path))
        if not updates:
            return
        try:
            self.conn.executemany("UPDATE media_items SET content_hash = ? WHERE path = ?", updates)
            self.conn.commit()
        except Exception as exc:
            try:
                self._log(f"content hash backfill failed: {exc}")
            except Exception:
                pass

    def _similarity_config(self) -> tuple[int, int]:
        level = self._gallery_similarity_threshold()
        mapping = {
            "very_low": (5, 2),
            "low": (9, 2),
            "medium": (12, 2),
            "high": (15, 1),
            "very_high": (18, 1),
        }
        return mapping.get(level, (12, 2))

    def _gallery_group_date_granularity(self) -> str:
        value = str(self.settings.value("gallery/group_date_granularity", "day", type=str) or "day")
        allowed = {"day", "month", "year"}
        return value if value in allowed else "day"

    def _mute_video_by_default_enabled(self) -> bool:
        return bool(self.settings.value("gallery/mute_video_by_default", True, type=bool))

    def _autoplay_gallery_animated_gifs_enabled(self) -> bool:
        if self.settings.contains("player/autoplay_gallery_animated_gifs"):
            return bool(self.settings.value("player/autoplay_gallery_animated_gifs", True, type=bool))
        return bool(self.settings.value("player/autoplay_animated_gifs", True, type=bool))

    def _autoplay_preview_animated_gifs_enabled(self) -> bool:
        if self.settings.contains("player/autoplay_preview_animated_gifs"):
            return bool(self.settings.value("player/autoplay_preview_animated_gifs", True, type=bool))
        return bool(self.settings.value("player/autoplay_animated_gifs", True, type=bool))

    def _video_loop_mode(self) -> str:
        value = str(self.settings.value("player/video_loop_mode", "short", type=str) or "short").strip().lower()
        return value if value in {"all", "none", "short"} else "short"

    def _video_loop_cutoff_seconds(self) -> int:
        raw = self.settings.value("player/video_loop_cutoff_seconds", "90", type=str)
        try:
            seconds = int(str(raw or "90").strip())
        except Exception:
            seconds = 90
        return max(1, seconds)

    def _should_loop_video(self, duration_ms: int) -> bool:
        mode = self._video_loop_mode()
        if mode == "all":
            return True
        if mode == "none":
            return False
        duration_ms = int(duration_ms or 0)
        cutoff_ms = self._video_loop_cutoff_seconds() * 1000
        return 0 < duration_ms < cutoff_ms

    @Slot(result=dict)
    def get_settings(self) -> dict:
        try:
            data = {
                "gallery.randomize": self._randomize_enabled(),
                "gallery.restore_last": self._restore_last_enabled(),
                "gallery.show_hidden": self._show_hidden_enabled(),
                "gallery.use_recycle_bin": bool(self.settings.value("gallery/use_recycle_bin", True, type=bool)),
                "gallery.mute_video_by_default": self._mute_video_by_default_enabled(),
                "player.autoplay_gallery_animated_gifs": self._autoplay_gallery_animated_gifs_enabled(),
                "player.autoplay_preview_animated_gifs": self._autoplay_preview_animated_gifs_enabled(),
                "player.video_loop_mode": self._video_loop_mode(),
                "player.video_loop_cutoff_seconds": self._video_loop_cutoff_seconds(),
                "gallery.start_folder": self._start_folder_setting(),
                "gallery.view_mode": self._gallery_view_mode(),
                "gallery.group_by": self._gallery_group_by(),
                "gallery.group_date_granularity": self._gallery_group_date_granularity(),
                "gallery.similarity_threshold": self._gallery_similarity_threshold(),
                "duplicate.settings.active_tab": str(self.settings.value("duplicate/settings/active_tab", "rules", type=str) or "rules"),
                "ui.accent_color": str(self.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8"),
                "ui.show_top_panel": bool(self.settings.value("ui/show_top_panel", True, type=bool)),
                "ui.show_left_panel": bool(self.settings.value("ui/show_left_panel", True, type=bool)),
                "ui.show_right_panel": bool(self.settings.value("ui/show_right_panel", True, type=bool)),
                "ui.show_bottom_panel": bool(self.settings.value("ui/show_bottom_panel", True, type=bool)),
                "ui.show_dismissed_progress_toasts": bool(self.settings.value("ui/show_dismissed_progress_toasts", False, type=bool)),
                "ui.show_splash_screen": bool(self.settings.value("ui/show_splash_screen", True, type=bool)),
                "ui.preview_above_details": self._preview_above_details_enabled(),
                "ui.theme_mode": str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"),
                "metadata.display.res": bool(self.settings.value("metadata/display/res", True, type=bool)),
                "metadata.display.size": bool(self.settings.value("metadata/display/size", True, type=bool)),
                "metadata.display.exifdatetaken": bool(self.settings.value("metadata/display/exifdatetaken", False, type=bool)),
                "metadata.display.metadatadate": bool(self.settings.value("metadata/display/metadatadate", False, type=bool)),
                "metadata.display.originalfiledate": bool(self.settings.value("metadata/display/originalfiledate", self.settings.value("metadata/display/filecreateddate", False, type=bool), type=bool)),
                "metadata.display.filecreateddate": bool(self.settings.value("metadata/display/filecreateddate", False, type=bool)),
                "metadata.display.filemodifieddate": bool(self.settings.value("metadata/display/filemodifieddate", False, type=bool)),
                "metadata.display.description": bool(self.settings.value("metadata/display/description", True, type=bool)),
                "metadata.display.tags": bool(self.settings.value("metadata/display/tags", True, type=bool)),
                "metadata.display.notes": bool(self.settings.value("metadata/display/notes", True, type=bool)),
                "metadata.display.camera": bool(self.settings.value("metadata/display/camera", False, type=bool)),
                "metadata.display.location": bool(self.settings.value("metadata/display/location", False, type=bool)),
                "metadata.display.iso": bool(self.settings.value("metadata/display/iso", False, type=bool)),
                "metadata.display.shutter": bool(self.settings.value("metadata/display/shutter", False, type=bool)),
                "metadata.display.aperture": bool(self.settings.value("metadata/display/aperture", False, type=bool)),
                "metadata.display.software": bool(self.settings.value("metadata/display/software", False, type=bool)),
                "metadata.display.lens": bool(self.settings.value("metadata/display/lens", False, type=bool)),
                "metadata.display.dpi": bool(self.settings.value("metadata/display/dpi", False, type=bool)),
                "metadata.display.embeddedtags": bool(self.settings.value("metadata/display/embeddedtags", True, type=bool)),
                "metadata.display.embeddedcomments": bool(self.settings.value("metadata/display/embeddedcomments", True, type=bool)),
                "metadata.display.embeddedmetadata": bool(self.settings.value("metadata/display/embeddedmetadata", True, type=bool)),
                "metadata.display.aistatus": bool(self.settings.value("metadata/display/aistatus", True, type=bool)),
                "metadata.display.aisource": bool(self.settings.value("metadata/display/aisource", True, type=bool)),
                "metadata.display.aifamilies": bool(self.settings.value("metadata/display/aifamilies", True, type=bool)),
                "metadata.display.aidetectionreasons": bool(self.settings.value("metadata/display/aidetectionreasons", False, type=bool)),
                "metadata.display.ailoras": bool(self.settings.value("metadata/display/ailoras", True, type=bool)),
                "metadata.display.aimodel": bool(self.settings.value("metadata/display/aimodel", True, type=bool)),
                "metadata.display.aicheckpoint": bool(self.settings.value("metadata/display/aicheckpoint", False, type=bool)),
                "metadata.display.aisampler": bool(self.settings.value("metadata/display/aisampler", True, type=bool)),
                "metadata.display.aischeduler": bool(self.settings.value("metadata/display/aischeduler", True, type=bool)),
                "metadata.display.aicfg": bool(self.settings.value("metadata/display/aicfg", True, type=bool)),
                "metadata.display.aisteps": bool(self.settings.value("metadata/display/aisteps", True, type=bool)),
                "metadata.display.aiseed": bool(self.settings.value("metadata/display/aiseed", True, type=bool)),
                "metadata.display.aiupscaler": bool(self.settings.value("metadata/display/aiupscaler", False, type=bool)),
                "metadata.display.aidenoise": bool(self.settings.value("metadata/display/aidenoise", False, type=bool)),
                "metadata.display.aiprompt": bool(self.settings.value("metadata/display/aiprompt", True, type=bool)),
                "metadata.display.ainegprompt": bool(self.settings.value("metadata/display/ainegprompt", True, type=bool)),
                "metadata.display.aiparams": bool(self.settings.value("metadata/display/aiparams", True, type=bool)),
                "metadata.display.aiworkflows": bool(self.settings.value("metadata/display/aiworkflows", False, type=bool)),
                "metadata.display.aiprovenance": bool(self.settings.value("metadata/display/aiprovenance", False, type=bool)),
                "metadata.display.aicharcards": bool(self.settings.value("metadata/display/aicharcards", False, type=bool)),
                "metadata.display.airawpaths": bool(self.settings.value("metadata/display/airawpaths", False, type=bool)),
                "metadata.display.order": self.settings.value("metadata/display/order", "[]", type=str),
                "updates.check_on_launch": bool(self.settings.value("updates/check_on_launch", True, type=bool)),
            }
            for qkey in self.settings.allKeys():
                if qkey.startswith("metadata/display/") or qkey.startswith("metadata/layout/") or qkey.startswith("duplicate/"):
                    data[qkey.replace("/", ".")] = self._coerce_setting_value(self.settings.value(qkey))
            return data
        except Exception:
            return {
                "gallery.randomize": False,
                "gallery.restore_last": False,
                "gallery.show_hidden": False,
                "gallery.use_recycle_bin": True,
                "gallery.mute_video_by_default": True,
                "player.autoplay_gallery_animated_gifs": True,
                "player.autoplay_preview_animated_gifs": True,
                "player.video_loop_mode": "short",
                "player.video_loop_cutoff_seconds": 90,
                "gallery.start_folder": "",
                "gallery.view_mode": "masonry",
                "gallery.group_by": "none",
                "gallery.group_date_granularity": "day",
                "gallery.similarity_threshold": "low",
                "duplicate.settings.active_tab": "rules",
                "ui.accent_color": "#8ab4f8",
                "ui.show_top_panel": True,
                "ui.show_left_panel": True,
                "ui.show_right_panel": True,
                "ui.show_bottom_panel": True,
                "ui.show_dismissed_progress_toasts": False,
                "ui.show_splash_screen": True,
                "ui.preview_above_details": True,
                "ui.theme_mode": "dark",
            }

    def _normalize_compare_slot_name(self, slot_name: str) -> str:
        return "right" if str(slot_name or "").strip().lower() == "right" else "left"

    def _ensure_compare_media_record(self, path: str) -> dict:
        from app.mediamanager.db.media_repo import add_media_item, get_media_by_path

        clean = str(path or "").strip()
        if not clean:
            return {}
        media = get_media_by_path(self.conn, clean)
        if media:
            return media
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return {}
        media_type = "image" if p.suffix.lower() in (IMAGE_EXTS | {".tif", ".tiff", ".heic", ".heif"}) else "video"
        add_media_item(self.conn, clean, media_type)
        return get_media_by_path(self.conn, clean) or {}

    def _build_compare_entry(self, path: str) -> dict:
        clean = str(path or "").strip()
        if not clean:
            return {}
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return {}
        media = dict(self._ensure_compare_media_record(clean) or {})
        try:
            stat = p.stat()
        except Exception:
            stat = None
        width = int(media.get("width") or 0)
        height = int(media.get("height") or 0)
        if width <= 0 or height <= 0:
            try:
                reader = QImageReader(clean)
                reader.setAutoTransform(True)
                size = reader.size()
                if size.isValid():
                    width = max(width, size.width())
                    height = max(height, size.height())
            except Exception:
                pass
        file_size = int(media.get("file_size") or 0)
        if file_size <= 0 and stat is not None:
            file_size = int(stat.st_size)
        modified_time = self._iso_to_ns(media.get("modified_time"))
        file_created_time = self._iso_to_ns(media.get("file_created_time"))
        original_file_date = self._iso_to_ns(media.get("original_file_date"))
        if modified_time <= 0 and stat is not None:
            modified_time = int(stat.st_mtime_ns)
        if file_created_time <= 0 and stat is not None:
            file_created_time = int(stat.st_ctime_ns)
        if original_file_date <= 0:
            original_file_date = self._normalized_file_date_ns(file_created_time, modified_time)
        entry = {
            "path": clean,
            "name": p.name,
            "media_type": str(media.get("media_type") or "image"),
            "file_size": file_size,
            "width": width,
            "height": height,
            "modified_time": modified_time,
            "file_created_time": file_created_time,
            "original_file_date": original_file_date,
            "exif_date_taken": media.get("exif_date_taken") or "",
            "metadata_date": media.get("metadata_date") or "",
            "preferred_date": 0,
            "text_detected": media.get("text_detected"),
        }
        entry["preferred_date"] = self._preferred_date_ns(entry)
        entry["file_size_text"] = self._format_file_size(file_size)
        entry["resolution_text"] = f"{width} x {height}" if width > 0 and height > 0 else ""
        entry["modified_time_text"] = self._format_compare_datetime(modified_time)
        return entry

    def _format_file_size(self, file_size: int) -> str:
        size = float(file_size or 0)
        if size <= 0:
            return ""
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        return f"{size:.1f} {units[unit_index]}" if unit_index else f"{int(size)} B"

    def _format_compare_datetime(self, value_ns: int) -> str:
        try:
            if int(value_ns or 0) <= 0:
                return ""
            dt = datetime.fromtimestamp(int(value_ns) / 1_000_000_000, tz=timezone.utc).astimezone()
            return dt.strftime("%Y-%m-%d %I:%M %p").lstrip("0")
        except Exception:
            return ""

    def _build_compare_payload(self) -> dict:
        slot_entries: dict[str, dict] = {}
        ranked_entries: list[dict] = []
        for slot_name in ("left", "right"):
            entry = self._build_compare_entry(self._compare_paths.get(slot_name, ""))
            slot_entries[slot_name] = entry
            if entry:
                ranked_entries.append(dict(entry))
        ranked = self._rank_duplicate_group(ranked_entries) if ranked_entries else []
        ranked_by_path = {str(entry.get("path") or ""): entry for entry in ranked}
        comparison_best_path = next((str(entry.get("path") or "") for entry in ranked if entry.get("duplicate_is_overall_best")), "")
        active_paths = {str(entry.get("path") or "") for entry in slot_entries.values() if entry}
        self._compare_keep_paths = {path for path in self._compare_keep_paths if path in active_paths}
        payload = {
            "visible": bool(self.settings.value("ui/show_bottom_panel", True, type=bool)),
            "left": {},
            "right": {},
            "best_path": self._compare_best_path,
            "comparison_best_path": comparison_best_path,
            "keep_paths": list(self._compare_keep_paths),
            "selection_revision": int(self._compare_selection_revision),
        }
        for slot_name, base_entry in slot_entries.items():
            path = str(base_entry.get("path") or "")
            entry = dict(ranked_by_path.get(path) or base_entry or {})
            if entry:
                entry["compare_keep_checked"] = path in self._compare_keep_paths
                entry["compare_marked_best"] = bool(self._compare_best_path) and path == self._compare_best_path
                entry["compare_best_in_pair"] = path == comparison_best_path
            payload[slot_name] = entry
        return payload

    def _emit_compare_state_changed(self) -> None:
        if self._compare_state_emit_pending:
            return
        self._compare_state_emit_pending = True

        def _emit() -> None:
            self._compare_state_emit_pending = False
            state = self.get_compare_state()
            self.compareStateChanged.emit(state)

        QTimer.singleShot(0, _emit)

    @Slot(result="QVariantMap")
    def get_compare_state(self) -> dict:
        return self._build_compare_payload()

    @Slot()
    def open_compare_panel(self) -> None:
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str)
    def clear_compare_slot(self, slot_name: str) -> None:
        slot = self._normalize_compare_slot_name(slot_name)
        self._compare_paths[slot] = ""
        self._emit_compare_state_changed()

    @Slot(str, str)
    def set_compare_path(self, slot_name: str, path: str) -> None:
        slot = self._normalize_compare_slot_name(slot_name)
        clean = str(path or "").strip()
        if not clean:
            return
        p = Path(clean)
        if not p.exists() or not p.is_file():
            return
        self._compare_paths[slot] = str(p.absolute())
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str, str)
    def swap_compare_slots(self, source_slot: str, target_slot: str) -> None:
        src = self._normalize_compare_slot_name(source_slot)
        dst = self._normalize_compare_slot_name(target_slot)
        if src == dst:
            return
        self._compare_paths[src], self._compare_paths[dst] = self._compare_paths.get(dst, ""), self._compare_paths.get(src, "")
        self._emit_compare_state_changed()

    @Slot(list)
    def compare_paths(self, paths: list[str]) -> None:
        clean = [str(Path(path).absolute()) for path in (paths or []) if str(path or "").strip()]
        if not clean:
            return
        self._compare_paths["left"] = clean[0]
        if len(clean) > 1:
            self._compare_paths["right"] = clean[1]
        self.set_setting_bool("ui.show_bottom_panel", True)
        self._emit_compare_state_changed()

    @Slot(str)
    def compare_path_auto(self, path: str) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        slot = "left" if not self._compare_paths.get("left") else "right" if not self._compare_paths.get("right") else "right"
        self.set_compare_path(slot, clean)

    @Slot()
    def settings_modal_opened(self) -> None:
        if self._settings_modal_bottom_restore is not None:
            return
        was_visible = bool(self.settings.value("ui/show_bottom_panel", True, type=bool))
        self._settings_modal_bottom_restore = was_visible
        if was_visible:
            self.set_setting_bool("ui.show_bottom_panel", False)

    @Slot()
    def settings_modal_closed(self) -> None:
        restore = self._settings_modal_bottom_restore
        self._settings_modal_bottom_restore = None
        if restore:
            self.set_setting_bool("ui.show_bottom_panel", True)

    @Slot(str, bool)
    def set_compare_keep_path(self, path: str, checked: bool) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        before = clean in self._compare_keep_paths
        if checked:
            self._compare_keep_paths.add(clean)
        else:
            self._compare_keep_paths.discard(clean)
        after = clean in self._compare_keep_paths
        if before == after:
            return
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot(str, list)
    def set_compare_selection_state(self, best_path: str, keep_paths: list) -> None:
        clean_best_path = str(best_path or "").strip()
        clean_keep_paths = {
            str(path or "").strip()
            for path in (keep_paths or [])
            if str(path or "").strip()
        }
        changed = False
        if self._compare_best_path != clean_best_path:
            self._compare_best_path = clean_best_path
            changed = True
        if self._compare_keep_paths != clean_keep_paths:
            self._compare_keep_paths = clean_keep_paths
            changed = True
        if changed:
            self._compare_selection_revision += 1
            self._emit_compare_state_changed()

    @Slot(str)
    def set_compare_best_path(self, path: str) -> None:
        clean = str(path or "").strip()
        if not clean:
            return
        if self._compare_best_path == clean:
            return
        self._compare_best_path = clean
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot()
    def clear_compare_best_path(self) -> None:
        if not self._compare_best_path:
            return
        self._compare_best_path = ""
        self._compare_selection_revision += 1
        self._emit_compare_state_changed()

    @Slot(result=str)
    def get_app_version(self) -> str:
        return __version__

    @Slot(bool)
    def check_for_updates(self, manual: bool = False):
        """Check GitHub for a newer version in the VERSION file."""
        url = "https://raw.githubusercontent.com/G1enB1and/MediaLens/main/VERSION"
        request = QNetworkRequest(QUrl(url))
        self._update_reply = self.nam.get(request)
        
        def _on_finished():
            if self._update_reply.error() == QNetworkReply.NetworkError.NoError:
                remote_version = bytes(self._update_reply.readAll()).decode().strip()
                try:
                    is_newer = remote_version and Version(remote_version) > Version(__version__)
                except Exception:
                    is_newer = False

                if is_newer:
                    self.updateAvailable.emit(remote_version, manual)
                elif manual:
                    self.updateAvailable.emit("", True)
            elif manual:
                self.updateError.emit(f"Failed to check for updates: {self._update_reply.errorString()}")
            self._update_reply.deleteLater()
            self._update_reply = None

        self._update_reply.finished.connect(_on_finished)

    @Slot()
    def download_and_install_update(self):
        """Download latest installer and launch it."""
        url = "https://github.com/G1enB1and/MediaLens/releases/latest/download/MediaLens_Setup.exe"
        request = QNetworkRequest(QUrl(url))
        self._download_reply = self.nam.get(request)
        
        def _on_progress(received, total):
            if total > 0:
                pct = int((received / total) * 100)
                self.updateDownloadProgress.emit(pct)

        def _on_finished():
            if self._download_reply.error() == QNetworkReply.NetworkError.NoError:
                data = self._download_reply.readAll()
                temp_dir = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
                setup_path = os.path.join(temp_dir, "MediaLens_Setup_New.exe")
                try:
                    with open(setup_path, "wb") as f:
                        f.write(data)
                    subprocess.Popen([setup_path, "/SILENT", "/SP-", "/NOICONS"])
                    QApplication.quit()
                except Exception as e:
                    self.updateError.emit(f"Failed to save or launch installer: {e}")
            else:
                self.updateError.emit(f"Download failed: {self._download_reply.errorString()}")
            self._download_reply.deleteLater()
            self._download_reply = None

        self._download_reply.downloadProgress.connect(_on_progress)
        self._download_reply.finished.connect(_on_finished)

    @Slot(result=bool)
    def should_check_on_launch(self) -> bool:
        return self.settings.value("updates.check_on_launch", True, type=bool)

    @staticmethod
    def _coerce_setting_value(value):
        if isinstance(value, str):
            low = value.lower()
            if low in ("true", "false"):
                return low == "true"
        return value

    @Slot(str, bool, result=bool)
    def set_setting_bool(self, key: str, value: bool) -> bool:
        try:
            allowed = (
                "gallery.randomize", 
                "gallery.restore_last", 
                "gallery.show_hidden",
                "gallery.use_recycle_bin",
                "gallery.mute_video_by_default",
                "player.autoplay_gallery_animated_gifs",
                "player.autoplay_preview_animated_gifs",
                "ui.show_top_panel",
                "ui.show_left_panel", 
                "ui.show_right_panel", 
                "ui.show_bottom_panel",
                "ui.show_dismissed_progress_toasts",
                "ui.show_splash_screen",
                "ui.preview_above_details",
                "updates.check_on_launch"
            )
            if key not in allowed and key != "duplicate.rules.merge_before_delete" and not key.startswith("metadata.display.") and not key.startswith("duplicate.rules.merge"):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))
            if key.startswith("ui.") or key.startswith("metadata.display.") or key in {"gallery.show_hidden", "gallery.mute_video_by_default", "player.autoplay_gallery_animated_gifs", "player.autoplay_preview_animated_gifs"}:
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
            if key == "ui.show_bottom_panel":
                self._emit_compare_state_changed()
            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            if key not in ("gallery.start_folder", "gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold", "ui.accent_color", "ui.theme_mode", "metadata.display.order", "duplicate.settings.active_tab", "player.video_loop_mode", "player.video_loop_cutoff_seconds") and not key.startswith("metadata.layout.") and not key.startswith("duplicate.rules.") and key != "duplicate.priorities.order":
                return False
            if key == "gallery.view_mode":
                allowed = {"masonry", "grid_small", "grid_medium", "grid_large", "grid_xlarge", "list", "content", "details", "duplicates", "similar", "similar_only"}
                if value not in allowed:
                    return False
            elif key == "gallery.group_by":
                if value not in {"none", "date", "duplicates", "similar", "similar_only"}:
                    return False
            elif key == "gallery.group_date_granularity":
                if value not in {"day", "month", "year"}:
                    return False
            elif key == "gallery.similarity_threshold":
                if value not in {"very_low", "low", "medium", "high", "very_high"}:
                    return False
            elif key == "duplicate.settings.active_tab":
                if value not in {"rules", "priorities"}:
                    return False
            elif key == "player.video_loop_mode":
                if value not in {"all", "none", "short"}:
                    return False
            elif key == "player.video_loop_cutoff_seconds":
                try:
                    value = str(max(1, int(str(value or "90").strip())))
                except Exception:
                    return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, str(value or ""))
            if key == "ui.accent_color":
                self.settings.sync()
                self.accentColorChanged.emit(str(value or "#8ab4f8"))
            elif key == "ui.theme_mode":
                Theme.set_theme_mode(value)
                self.settings.sync()
                self.uiFlagChanged.emit(key, value == "light")
                current_accent = str(self.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
                self.accentColorChanged.emit(current_accent)
            elif key in ("gallery.view_mode", "gallery.group_by", "gallery.group_date_granularity", "gallery.similarity_threshold"):
                self.settings.sync()
                self.uiFlagChanged.emit(key, True)
            elif key == "metadata.display.order" or key.startswith("metadata.layout."):
                self.settings.sync()
                self.uiFlagChanged.emit(key, True)
            return True
        except Exception:
            return False

    @Slot(str)
    def load_folder_now(self, path: str) -> None:
        self.loadFolderRequested.emit(str(path))

    @Slot(list, str, int, int)
    def start_native_drag(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> None:
        clean_paths = [str(p) for p in (paths or []) if p]
        if not clean_paths:
            return
        self.set_drag_paths(clean_paths)
        self.startNativeDragRequested.emit(clean_paths, str(preview_path or ""), int(preview_width or 0), int(preview_height or 0))

    @Slot(str)
    def navigate_to_folder(self, path: str) -> None:
        self.navigateToFolderRequested.emit(str(path))

    @Slot()
    def navigate_back(self) -> None:
        self.navigateBackRequested.emit()

    @Slot()
    def navigate_forward(self) -> None:
        self.navigateForwardRequested.emit()

    @Slot()
    def navigate_up(self) -> None:
        self.navigateUpRequested.emit()

    @Slot()
    def refresh_current_folder(self) -> None:
        self.refreshFolderRequested.emit()

    @Slot()
    def open_settings_dialog(self) -> None:
        self.openSettingsDialogRequested.emit()

    @Slot(result=str)
    def pick_folder(self) -> str:
        try:
            from PySide6.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(None, "Choose folder")
            return str(folder) if folder else ""
        except Exception:
            return ""

    def _unique_path(self, target: Path) -> Path:
        if not target.exists(): return target
        suffix, stem, parent, i = target.suffix, target.stem, target.parent, 2
        while True:
            cand = parent / f"{stem} ({i}){suffix}"
            if not cand.exists(): return cand
            i += 1

    def _hide_by_renaming_dot(self, path: str) -> str:
        """DEPRECATED: Use set_media_hidden instead."""
        p = Path(path)
        if not p.exists() or p.name.startswith("."): return str(p)
        target = self._unique_path(p.with_name(f".{p.name}"))
        p.rename(target)
        return str(target)

    @Slot(str, bool, result=bool)
    def set_media_hidden(self, path: str, hidden: bool) -> bool:
        success = self.repo.set_media_hidden(path, hidden)
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(str, bool, result=bool)
    def set_folder_hidden(self, path: str, hidden: bool) -> bool:
        success = self.repo.set_folder_hidden(path, hidden)
        self.fileOpFinished.emit("hide" if hidden else "unhide", success, path, path)
        return success

    @Slot(int, bool, result=bool)
    def set_collection_hidden(self, collection_id: int, hidden: bool) -> bool:
        success = self.repo.set_collection_hidden(collection_id, hidden)
        if success:
            # Emit a signal that collections updated if we have one
            # self.collectionsUpdated.emit()
            pass
        return success

    @Slot(result="QVariantMap")
    def get_external_editors(self):
        """Find installation paths for external editors."""
        editors = {"photoshop": None, "affinity": None}
        import winreg
        
        # Check Photoshop via App Paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photoshop.exe") as key:
                editors["photoshop"] = winreg.QueryValue(key, None)
        except Exception:
            pass
            
        # Check Affinity Photo 2 via App Paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Photo.exe") as key:
                editors["affinity"] = winreg.QueryValue(key, None)
        except Exception:
            pass
            
        # Fallback for Affinity
        if not editors["affinity"]:
            affinity_fallbacks = [
                r"C:\Program Files\Affinity\Photo 2\Photo.exe",
                r"C:\Program Files\Affinity\Photo\Photo.exe"
            ]
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                windows_apps = os.path.join(local_appdata, "Microsoft", "WindowsApps")
                affinity_fallbacks.extend([
                    os.path.join(windows_apps, "Affinity.exe"),
                    os.path.join(windows_apps, "AffinityPhoto2.exe"),
                    os.path.join(windows_apps, "AffinityPhoto.exe")
                ])
                
            for fb in affinity_fallbacks:
                if os.path.exists(fb):
                    editors["affinity"] = fb
                    break
                    
        return {k: v for k, v in editors.items() if v}

    @Slot(str, str)
    def open_in_editor(self, editor_key: str, path: str):
        """Open a file in the specified external editor."""
        editors = self.get_external_editors()
        editor_path = editors.get(editor_key)
        if not editor_path or not os.path.exists(path):
            return
            
        try:
            subprocess.Popen([editor_path, path])
        except Exception as e:
            print(f"Failed to open in {editor_key}: {e}")

    @Slot(str, int)
    def rotate_image(self, path: str, degrees: int):
        """Rotate an image or video by degrees and update it in-place."""
        if not os.path.exists(path):
            return
            
        def work():
            try:
                is_video = path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))
                if is_video:
                    import subprocess, json, tempfile
                    
                    # 1. Probe current rotation
                    current_ccw_rot = 0.0
                    try:
                        cmd_probe = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', path]
                        res = _run_hidden_subprocess(cmd_probe, capture_output=True, text=True)
                        data = json.loads(res.stdout)
                        for st in data.get('streams', []):
                            if st.get('codec_type') == 'video': # check video stream
                                # Read tags (rare nowadays)
                                tags = st.get('tags', {})
                                if 'rotate' in tags:
                                    current_ccw_rot = float(tags['rotate'])
                                # Read side data (modern standard)
                                for sd in st.get('side_data_list', []):
                                    if 'rotation' in sd:
                                        # FFprobe reports CCW as positive.
                                        current_ccw_rot = float(sd['rotation'])
                                break
                    except Exception as e:
                        print("Warning: Failed to probe rotation:", e)
                    
                    # Frontend degrees: 90 is CCW, -90 is CW. 
                    # new_ccw = current + delta
                    new_ccw_rot = (current_ccw_rot + degrees) % 360
                    if new_ccw_rot < 0:
                        new_ccw_rot += 360
                    
                    # 2. FFmpeg copy and set rotation
                    # For FFmpeg, we set the input's display rotation so it copies that directly to the output.
                    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(path)[1], delete=False) as tmp:
                        tmp_name = tmp.name
                    
                    cmd_ffmpeg = [
                        'ffmpeg', '-y', 
                        '-display_rotation', str(new_ccw_rot),
                        '-i', path,
                        '-c', 'copy',
                        tmp_name
                    ]
                    
                    # hide ffmpeg output
                    _run_hidden_subprocess(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # 3. Replace original file
                    import shutil
                    shutil.move(tmp_name, path)
                else:
                    from PIL import Image
                    with Image.open(path) as img:
                        rotated = img.rotate(degrees, expand=True)
                        exif = img.info.get('exif')
                        if exif:
                            rotated.save(path, exif=exif)
                        else:
                            rotated.save(path)
                
                # If this is a video, delete the cached poster so it regenerates on next view
                if is_video:
                    poster = self._video_poster_path(Path(path))
                    if poster.exists():
                        try: poster.unlink()
                        except Exception: pass
                        
                # Update SQLite so width and height are inverted
                try:
                    from app.mediamanager.utils.pathing import normalize_windows_path
                    if hasattr(self, 'conn') and self.conn:
                        norm = normalize_windows_path(path)
                        # Swap width and height for 90-degree rotations
                        if degrees in (90, -90, 270, -270):
                            self.conn.execute("UPDATE media_items SET width = height, height = width WHERE path = ?", (norm,))
                            self.conn.commit()
                except Exception: pass
                
                # Finally, inform frontend that a file was modified so it can refresh the thumbnail
                self.fileOpFinished.emit("rotate", True, path, path)
            except Exception as e:
                print(f"Failed to rotate media: {e}")

        # Run in background to prevent freezing the UI on large videos
        threading.Thread(target=work, daemon=True).start()

    @Slot(str, result=str)
    def hide_by_renaming_dot(self, path: str) -> str:
        try: return self._hide_by_renaming_dot(path)
        except Exception: return ""

    @Slot(str, result=bool)
    def hide_by_renaming_dot_async(self, path: str) -> bool:
        old = str(path)
        def work():
            newp = ""
            try: newp = self._hide_by_renaming_dot(old)
            except Exception: pass
            self.fileOpFinished.emit("hide", bool(newp), old, newp)
            self._disk_cache = {}
            self._disk_cache_key = ""
        threading.Thread(target=work, daemon=True).start()
        return True

    def _unhide_by_renaming_dot(self, path: str) -> str:
        p = Path(path)
        if not p.exists() or not p.name.startswith("."): return str(p)
        target = self._unique_path(p.with_name(p.name[1:]))
        p.rename(target)
        return str(target)

    @Slot(str, result=str)
    def unhide_by_renaming_dot(self, path: str) -> str:
        try: return self._unhide_by_renaming_dot(path)
        except Exception: return ""

    @Slot(str, result=bool)
    def unhide_by_renaming_dot_async(self, path: str) -> bool:
        old = str(path)
        def work():
            newp = ""
            try: newp = self._unhide_by_renaming_dot(old)
            except Exception: pass
            self.fileOpFinished.emit("unhide", bool(newp), old, newp)
            self._disk_cache = {}
            self._disk_cache_key = ""
        threading.Thread(target=work, daemon=True).start()
        return True

    def _rename_path(self, path: str, new_name: str) -> str:
        p = Path(path)
        if not p.exists() or not new_name.strip(): return ""
        target = self._unique_path(p.with_name(new_name.strip()))
        # Use shutil.move for robustness across drives if necessary, 
        # though usually rename is fine for same folder.
        shutil.move(str(p), str(target))
        return str(target)

    @Slot(str, str, result=str)
    def rename_path(self, path: str, new_name: str) -> str:
        try: return self._rename_path(path, new_name)
        except Exception: return ""

    @Slot(str, str, result=bool)
    def rename_path_async(self, path: str, new_name: str) -> bool:
        old, newn = str(path), str(new_name)
        def work():
            ok, newp = False, ""
            try:
                newp = self._rename_path(old, newn)
                ok = bool(newp)
                if ok:
                    from app.mediamanager.db.media_repo import rename_media_path
                    try: rename_media_path(self.conn, old, newp)
                    except Exception: pass
            except Exception: pass
            self.fileOpFinished.emit("rename", ok, old, newp)
            self._disk_cache = {}
            self._disk_cache_key = ""
        threading.Thread(target=work, daemon=True).start()
        return True

    @Slot(str, result=str)
    def path_to_url(self, path: str) -> str:
        try: return QUrl.fromLocalFile(str(path)).toString()
        except Exception: return ""

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

    @Slot(str, str)
    def _invoke_conflict_dialog(self, dst_str: str, src_str: str):
        """Helper to show dialog on main thread."""
        dst, src = Path(dst_str), Path(src_str)
        # Ensure parent is a QWidget if possible
        parent_win = self.parent() if isinstance(self.parent(), QWidget) else None
        dlg = FileConflictDialog(dst, src, self, parent=parent_win)
        if dlg.exec():
            # Store results so processing thread can pick them up
            self._last_dlg_res = {
                "action": dlg.result_action,
                "apply_all": dlg.apply_to_all,
                "new_existing": dlg.new_existing_name,
                "new_incoming": dlg.new_incoming_name
            }
        else:
            self._last_dlg_res = {"action": "skip"}

    def _process_file_op(self, op_type: str, src_paths: list[Path], target_dir: Path) -> None:
        if not target_dir.exists() or not target_dir.is_dir():
            self.fileOpFinished.emit(op_type, False, "", "")
            return

        def work():
            from app.mediamanager.db.media_repo import rename_media_path, move_directory_in_db, add_media_item
            
            
            is_move = op_type in ("move", "paste_move")
            sticky_action = None
            any_ok = False
            
            try:
                for src in src_paths:
                    if not src.exists():
                        continue
                    
                    dst = target_dir / src.name
                    action = "keep_both"
                    final_dst = dst
                    
                    if dst.exists():
                        if dst.samefile(src):
                            continue
                        
                        if sticky_action:
                            res = {"action": sticky_action, "new_incoming": src.name}
                        else:
                            # Invoke dialog on main thread via signal
                            self._last_dlg_res = None
                            self.conflictDialogRequested.emit(str(dst), str(src))
                            
                            # Busy wait for result (max 10 mins)
                            start_t = time.time()
                            while self._last_dlg_res is None and (time.time() - start_t < 600):
                                time.sleep(0.05)
                            
                            res = self._last_dlg_res or {"action": "skip"}
                            if res.get("apply_all"): sticky_action = res["action"]
                        
                        action = res["action"]
                        if action == "skip":
                            continue
                        elif action == "replace":
                             final_dst = dst
                        elif action == "keep_both":
                             # Use the new name from dialog if provided
                             new_name = res.get("new_incoming", src.name)
                             final_dst = target_dir / new_name
                             if final_dst.exists():
                                 final_dst = self._unique_path(final_dst)
                    
                    # Execute with correct atomic logic
                    try:
                        if is_move:
                            try:
                                # Try atomic os.replace (removes source, overwrites target if exists)
                                os.replace(src, final_dst)
                            except OSError:
                                # Cross-device move fallback
                                shutil.move(src, final_dst)
                            
                            # Double check: ensure source is gone (as requested by user)
                            if src.exists():
                                try:
                                    if src.is_dir(): shutil.rmtree(src)
                                    else: src.unlink()
                                except: pass
                            
                            if src.is_dir(): move_directory_in_db(self.conn, str(src), str(final_dst))
                            else: rename_media_path(self.conn, str(src), str(final_dst))
                        else:
                            # Copy operation
                            if src.is_dir(): shutil.copytree(src, final_dst)
                            else: shutil.copy2(src, final_dst)
                            
                            ext = final_dst.suffix.lower()
                            mtype = "image" if ext in IMAGE_EXTS else "video"
                            add_media_item(self.conn, str(final_dst), mtype)
                        
                        any_ok = True
                    except Exception as e:
                        pass

                op_signal = "paste" if "paste" in op_type else op_type
                self.fileOpFinished.emit(op_signal, any_ok, "", str(target_dir))
            except Exception as e:
                self.fileOpFinished.emit(op_type, False, "", "")
            
            self._disk_cache = {}; self._disk_cache_key = ""

        threading.Thread(target=work, daemon=True).start()

    @Slot(list, str)
    def move_paths_async(self, src_paths: list[str], target_folder: str) -> None:
        self._process_file_op("move", [Path(p) for p in src_paths], Path(target_folder))

    @Slot(list, str)
    def copy_paths_async(self, src_paths: list[str], target_folder: str) -> None:
        self._process_file_op("copy", [Path(p) for p in src_paths], Path(target_folder))

    @Slot(list, result=bool)
    def show_metadata(self, paths: list) -> bool:
        try: self.metadataRequested.emit(paths); return True
        except Exception: return False

    @Slot(str)
    def open_in_explorer(self, path: str) -> None:
        try:
            p_obj = Path(path).absolute()
            p = str(p_obj).replace("/", "\\")
            if not p_obj.exists(): return
            if p_obj.is_dir(): os.startfile(p)
            else: subprocess.Popen(f'explorer.exe /select,"{p}"', shell=True)
        except Exception: pass

    def _build_dropfiles_w(self, abs_paths: list[str]) -> bytes:
        import struct
        header = struct.pack("IiiII", 20, 0, 0, 0, 1)
        files_data = b"".join([p.encode("utf-16-le") + b"\x00\x00" for p in abs_paths]) + b"\x00\x00"
        return header + files_data

    @Slot(list)
    def copy_to_clipboard(self, paths: list[str]) -> None:
        try:
            clipboard, mime = QApplication.clipboard(), QMimeData()
            abs_paths = [str(Path(p).resolve()) for p in paths]
            mime.setUrls([QUrl.fromLocalFile(p) for p in abs_paths])
            mime.setText("\n".join(abs_paths))
            mime.setData("Preferred DropEffect", b'\x05\x00\x00\x00')
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            clipboard.setMimeData(mime)
        except Exception: pass

    @Slot(list)
    def cut_to_clipboard(self, paths: list[str]) -> None:
        try:
            clipboard, mime = QApplication.clipboard(), QMimeData()
            abs_paths = [str(Path(p).resolve()) for p in paths]
            mime.setUrls([QUrl.fromLocalFile(p) for p in abs_paths])
            mime.setText("\n".join(abs_paths))
            mime.setData("Preferred DropEffect", b'\x02\x00\x00\x00')
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            clipboard.setMimeData(mime)
        except Exception: pass

    @Slot(result=bool)
    def has_files_in_clipboard(self) -> bool:
        try: return QApplication.clipboard().mimeData().hasUrls()
        except Exception: return False

    @Slot(str, result=bool)
    def delete_path(self, path_str: str) -> bool:
        try:
            p = Path(path_str)
            if not p.exists():
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False

            self.close_native_video()
            QApplication.processEvents()

            use_recycle = bool(self.settings.value("gallery/use_recycle_bin", True, type=bool))
            if use_recycle:
                deleted = send_to_recycle_bin(path_str)
                if not deleted and p.exists():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()
            else:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

            from app.mediamanager.utils.pathing import normalize_windows_path
            self.conn.execute("DELETE FROM media_items WHERE path = ?", (normalize_windows_path(path_str),))
            self.conn.commit()
            self._disk_cache = {}
            self._disk_cache_key = ""
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(str, result=bool)
    def delete_path_permanent(self, path_str: str) -> bool:
        try:
            p = Path(path_str)
            if not p.exists():
                self.fileOpFinished.emit("delete", False, path_str, "")
                return False

            self.close_native_video()
            QApplication.processEvents()

            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

            from app.mediamanager.utils.pathing import normalize_windows_path
            self.conn.execute("DELETE FROM media_items WHERE path = ?", (normalize_windows_path(path_str),))
            self.conn.commit()
            self._disk_cache = {}
            self._disk_cache_key = ""
            self.fileOpFinished.emit("delete", True, path_str, "")
            return True
        except Exception:
            self.fileOpFinished.emit("delete", False, path_str, "")
            return False

    @Slot(str, str, result=str)
    def create_folder(self, parent_path: str, name: str) -> str:
        try:
            p = Path(parent_path) / name
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        except Exception: return ""

    @Slot(str)
    def paste_into_folder_async(self, target_folder: str) -> None:
        target_dir = Path(target_folder)
        try:
            mime = QApplication.clipboard().mimeData()
            if not mime.hasUrls():
                self.fileOpFinished.emit("paste", False, "", "")
                return
            is_move = bool(mime.hasFormat("Preferred DropEffect") and mime.data("Preferred DropEffect")[0] == 2)
            src_paths = [Path(url.toLocalFile()) for url in mime.urls() if url.toLocalFile()]
            op_type = "paste_move" if is_move else "paste_copy"
            self._process_file_op(op_type, src_paths, target_dir)
        except Exception:
            self.fileOpFinished.emit("paste", False, "", "")

    @Slot(str, result=float)
    def get_video_duration_seconds(self, video_path: str) -> float:
        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe: return 0.0
            runtime_path = self._video_runtime_path(video_path)
            cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", runtime_path]
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, check=True, timeout=5)
            return float((r.stdout or "").strip() or 0.0)
        except Exception: return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int, bool]:
        ffprobe = self._ffprobe_bin()
        if not ffprobe: return (0, 0, False)
        runtime_path = self._video_runtime_path(video_path)
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", runtime_path]
        try:
            import json
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            data = json.loads(r.stdout)
            streams = data.get("streams", [])
            if not streams: return (0, 0, False)
            for s in streams:
                if s.get("codec_type") == "video":
                    w_raw, h_raw = int(s.get("width", 0)), int(s.get("height", 0))
                    sar = s.get("sample_aspect_ratio", "1:1")
                    parsed_sar = 1.0
                    if sar and ":" in sar and sar != "1:1":
                        try: num, den = sar.split(":", 1); parsed_sar = float(num) / float(den)
                        except Exception: pass
                    w, h = max(2, int(w_raw * parsed_sar)), max(2, h_raw)
                    
                    cw_rot = 0
                    tags = s.get("tags", {})
                    if "rotate" in tags:
                        cw_rot = int(tags["rotate"]) % 360
                    for sd in s.get("side_data_list", []):
                        if "rotation" in sd:
                            cw_rot = int(abs(float(sd["rotation"]))) % 360
                    
                    if cw_rot in (90, 270): 
                        w, h = h, w
                        
                    return (w, h, (w % 2 != 0 or h % 2 != 0))
            return (0, 0, False)
        except Exception: return (0, 0, False)

    @Slot(str, bool, bool, bool, int, int, result=bool)
    def open_native_video(self, video_path: str, autoplay: bool, loop: bool, muted: bool, w: int = 0, h: int = 0) -> bool:
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video for non-file path: {video_path}")
                return False
            runtime_path = self._video_runtime_path(video_path)
            if w <= 0 or h <= 0:
                w, h, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (w % 2 != 0 or h % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, w, h)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoRequested.emit(str(fixed), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoRequested.emit(runtime_path, bool(autoplay), bool(loop), bool(muted), int(w), int(h))
            return True
        except Exception:
            return False

    @Slot(str, int, int, int, int, bool, bool, bool, int, int)
    def open_native_video_inplace(self, video_path: str, x: int, y: int, w: int, h: int, autoplay: bool, loop: bool, muted: bool, vw: int = 0, vh: int = 0) -> None:
        if not loop:
            d_s = self.get_video_duration_seconds(video_path)
            if self._should_loop_video(int(float(d_s or 0) * 1000)):
                loop = True
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video_inplace for non-file path: {video_path}")
                return
            runtime_path = self._video_runtime_path(video_path)

            if vw <= 0 or vh <= 0:
                vw, vh, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (vw % 2 != 0 or vh % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, vw, vh)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoInPlaceRequested.emit(str(fixed), int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoInPlaceRequested.emit(runtime_path, int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(vw), int(vh))
        except Exception:
            pass

    @Slot(str, int, int)
    def preload_video(self, video_path: str, w: int = 0, h: int = 0) -> None:
        """Proactively prepare a video for playback in the background."""
        def work():
            try:
                # 1. Probe if dimensions unknown
                nonlocal w, h
                if w <= 0 or h <= 0:
                    w, h, is_malformed = self._probe_video_size(video_path)
                else:
                    is_malformed = (w % 2 != 0 or h % 2 != 0)
                
                # 2. Trigger "safety gate" preprocessing ahead of time if malformed
                if is_malformed:
                    self._preprocess_to_even_dims(video_path, w, h)
                    
                # 3. Future: Warm up QMediaPlayer instance if needed
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    @Slot(int, int, int, int)
    def update_native_video_rect(self, x, y, w, h):
        self.updateVideoRectRequested.emit(x, y, w, h)

    @Slot(bool)
    def set_video_muted(self, muted: bool) -> None:
        self.videoMutedChanged.emit(muted)

    @Slot(bool)
    def set_video_paused(self, paused: bool) -> None:
        self.videoPausedChanged.emit(paused)

    def _preprocess_to_even_dims(self, video_path: str, w: int, h: int) -> str | None:
        import tempfile
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg: return None
        runtime_path = self._video_runtime_path(video_path)
        ew, eh = (w if w % 2 == 0 else w - 1), (h if h % 2 == 0 else h - 1)
        if ew <= 0 or eh <= 0: return None
        tmp = tempfile.NamedTemporaryFile(prefix="mmx_fixed_", suffix=".mkv", delete=False)
        tmp.close()
        out_path = tmp.name
        vf = f"scale={ew}:{eh},setsar=1,format=yuv420p"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", runtime_path, "-vf", vf, "-c:v", "mjpeg", "-q:v", "3", "-c:a", "copy", out_path]
        try:
            if _run_hidden_subprocess(cmd, capture_output=True, timeout=60).returncode == 0:
                return out_path
        except Exception:
            pass
        return None

    @Slot(result=bool)
    def close_native_video(self) -> bool:
        try:
            self.closeVideoRequested.emit()
            return True
        except Exception:
            return False

    @Slot(str, result=dict)
    def get_media_metadata(self, path: str) -> dict:
        image_exts = IMAGE_EXTS
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.ai_metadata_repo import (
            NORMALIZED_SCHEMA_VERSION,
            PARSER_VERSION,
            build_media_ai_ui_fields,
            get_media_ai_metadata,
            summarize_media_ai_metadata,
            summarize_media_ai_tool_metadata,
        )
        from app.mediamanager.db.metadata_repo import get_media_metadata
        from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
        from app.mediamanager.db.tags_repo import list_media_tags
        try:
            m = get_media_by_path(self.conn, path)
            if not m:
                p = Path(path)
                if not p.exists():
                    return {}
                from app.mediamanager.db.media_repo import add_media_item
                media_type = "image" if p.suffix.lower() in image_exts else "video"
                add_media_item(self.conn, path, media_type)
                m = get_media_by_path(self.conn, path)
                if not m:
                    return {}
            p = Path(path)
            if p.exists():
                try:
                    stat = p.stat()
                    if not m.get("file_created_time"):
                        m["file_created_time"] = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    if not m.get("modified_time"):
                        m["modified_time"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    if not m.get("original_file_date"):
                        values = [str(value).strip() for value in (m.get("file_created_time"), m.get("modified_time")) if str(value or "").strip()]
                        m["original_file_date"] = min(values) if values else ""
                except Exception:
                    pass
            meta = get_media_metadata(self.conn, m["id"]) or {}
            ai_meta = get_media_ai_metadata(self.conn, m["id"]) or {}
            needs_reinspect = (
                (ai_meta and (
                    ai_meta.get("parser_version") != PARSER_VERSION
                    or ai_meta.get("normalized_schema_version") != NORMALIZED_SCHEMA_VERSION
                ))
                or meta.get("embedded_metadata_parser_version") != PARSER_VERSION
                or (not ai_meta and not meta)
            )
            if needs_reinspect:
                inspect_and_persist_if_supported(self.conn, m["id"], path, m.get("media_type"))
                meta = get_media_metadata(self.conn, m["id"]) or {}
                ai_meta = get_media_ai_metadata(self.conn, m["id"]) or {}
            ai_ui = build_media_ai_ui_fields(ai_meta)

            description = meta.get("description") or ai_meta.get("description") or ""
            ai_prompt = meta.get("ai_prompt") or ai_meta.get("ai_prompt") or ""
            ai_negative_prompt = meta.get("ai_negative_prompt") or ai_meta.get("ai_negative_prompt") or ""
            ai_params = meta.get("ai_params") or summarize_media_ai_metadata(ai_meta) or ""
            ai_tool_summary = summarize_media_ai_tool_metadata(ai_meta) or ""
            payload = {
                "title": meta.get("title") or "", "description": description, "notes": meta.get("notes") or "",
                "embedded_tags": meta.get("embedded_tags") or "", "embedded_comments": meta.get("embedded_comments") or "",
                "embedded_metadata_summary": meta.get("embedded_metadata_summary") or "",
                "ai_prompt": ai_prompt, "ai_negative_prompt": ai_negative_prompt,
                "ai_params": ai_params, "ai_tool_summary": ai_tool_summary,
                "tags": list_media_tags(self.conn, m["id"]), "has_metadata": bool(meta or ai_meta),
                "media_type": m.get("media_type") or "",
                "width": m.get("width"),
                "height": m.get("height"),
                "duration_ms": m.get("duration_ms"),
                "exif_date_taken": m.get("exif_date_taken") or "",
                "metadata_date": m.get("metadata_date") or "",
                "original_file_date": m.get("original_file_date") or "",
                "file_created_time": m.get("file_created_time") or "",
                "modified_time": m.get("modified_time") or "",
            }
            payload.update(ai_ui)
            return payload
        except Exception: return {}

    @Slot(str, str, str, str, str, str, str, str, str)
    def update_media_metadata(self, path, title, desc, notes, etags="", ecomm="", aip="", ainp="", aiparam="") -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.metadata_repo import upsert_media_metadata
        try:
            m = get_media_by_path(self.conn, path)
            if m: upsert_media_metadata(self.conn, m["id"], title, desc, notes, etags, ecomm, aip, ainp, aiparam)
        except Exception: pass

    @Slot(str, str, str)
    def update_media_dates(self, path: str, exif_date_taken: str, metadata_date: str) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                update_media_dates(
                    self.conn,
                    m["id"],
                    exif_date_taken=exif_date_taken.strip() or None,
                    metadata_date=metadata_date.strip() or None,
                )
        except Exception:
            pass

    @Slot(str, list)
    def set_media_tags(self, path: str, tags: list) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import set_media_tags
        try:
            m = get_media_by_path(self.conn, path)
            if m: set_media_tags(self.conn, m["id"], tags)
        except Exception: pass

    @Slot(str, list)
    def attach_media_tags(self, path: str, tags: list) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import attach_tags
        try:
            m = get_media_by_path(self.conn, path)
            if m: attach_tags(self.conn, m["id"], tags)
        except Exception: pass

    @Slot(str)
    def clear_media_tags(self, path: str) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import clear_all_media_tags
        try:
            m = get_media_by_path(self.conn, path)
            if m: clear_all_media_tags(self.conn, m["id"])
        except Exception: pass

    @Slot(list, result=bool)
    def merge_duplicate_group_metadata(self, paths: list[str]) -> bool:
        from app.mediamanager.db.ai_metadata_repo import (
            build_media_ai_sidebar_fields,
            get_media_ai_metadata,
            replace_media_ai_workflows,
            upsert_media_ai_selected_fields,
        )
        from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates
        from app.mediamanager.db.metadata_repo import get_media_metadata, upsert_media_metadata
        from app.mediamanager.db.tags_repo import attach_tags, list_media_tags

        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if len(clean_paths) < 2:
            return False

        try:
            rows: list[tuple[dict, dict, dict, list[str]]] = []
            for path in clean_paths:
                media = get_media_by_path(self.conn, path)
                if not media:
                    continue
                meta = get_media_metadata(self.conn, media["id"]) or {}
                ai_meta = get_media_ai_metadata(self.conn, media["id"]) or {}
                tags = list_media_tags(self.conn, media["id"])
                rows.append((media, meta, ai_meta, tags))

            if len(rows) < 2:
                return False

            all_enabled = bool(self.settings.value("duplicate/rules/merge/all", False, type=bool))

            def merge_enabled(name: str, default: bool = False) -> bool:
                return all_enabled or bool(self.settings.value(f"duplicate/rules/merge/{name}", default, type=bool))

            ranked_media = self._rank_duplicate_group([dict(media) for media, _, _, _ in rows])
            path_rank = {str(entry.get("path") or ""): idx for idx, entry in enumerate(ranked_media)}
            sorted_rows = sorted(rows, key=lambda row: path_rank.get(str(row[0].get("path") or ""), 10**9))

            def pick_best_text(values: list[str]) -> str:
                for value in values:
                    text = str(value or "").strip()
                    if text:
                        return text
                return ""

            def pick_best_workflows() -> list[dict]:
                for _, _, ai_meta, _ in sorted_rows:
                    workflows = list(ai_meta.get("workflows") or [])
                    if workflows:
                        return workflows
                return []

            merged_tags = sorted({tag.strip() for _, _, _, tags in rows for tag in tags if str(tag).strip()}, key=str.casefold)
            merged_title = self._merge_duplicate_scalar_field([meta.get("title") for _, meta, _, _ in rows])
            merged_desc = self._merge_duplicate_text_field([meta.get("description") or ai_meta.get("description") for _, meta, ai_meta, _ in rows])
            merged_notes = self._merge_duplicate_text_field([meta.get("notes") for _, meta, _, _ in rows])
            merged_embedded_tags = self._merge_duplicate_text_field([meta.get("embedded_tags") for _, meta, _, _ in rows])
            merged_embedded_comments = self._merge_duplicate_text_field([meta.get("embedded_comments") for _, meta, _, _ in rows])
            merged_ai_prompt = self._merge_duplicate_text_field([meta.get("ai_prompt") or ai_meta.get("ai_prompt") for _, meta, ai_meta, _ in rows])
            merged_ai_negative = self._merge_duplicate_text_field([meta.get("ai_negative_prompt") or ai_meta.get("ai_negative_prompt") for _, meta, ai_meta, _ in rows])
            merged_ai_params = pick_best_text([meta.get("ai_params") for _, meta, _, _ in sorted_rows])
            merged_workflows = pick_best_workflows()
            merged_workflow_summary = build_media_ai_sidebar_fields({"workflows": merged_workflows}).get("ai_workflows_summary", "")
            merged_exif_date = self._merge_duplicate_scalar_field([media.get("exif_date_taken") for media, _, _, _ in rows])
            merged_metadata_date = self._merge_duplicate_scalar_field([media.get("metadata_date") for media, _, _, _ in rows])

            write_title = merged_title if all_enabled else None
            write_desc = merged_desc if merge_enabled("description", True) else None
            write_notes = merged_notes if merge_enabled("notes", True) else None
            write_embedded_tags = merged_embedded_tags if merge_enabled("tags", True) else None
            write_embedded_comments = merged_embedded_comments if merge_enabled("comments", True) else None
            write_ai_prompt = merged_ai_prompt if merge_enabled("ai_prompts", True) else None
            write_ai_negative = merged_ai_negative if merge_enabled("ai_prompts", True) else None
            write_ai_params = merged_ai_params if merge_enabled("ai_parameters", True) else None
            should_write_db_meta = any(
                value is not None
                for value in (
                    write_title,
                    write_desc,
                    write_notes,
                    write_embedded_tags,
                    write_embedded_comments,
                    write_ai_prompt,
                    write_ai_negative,
                    write_ai_params,
                )
            )

            for media, _, _, _ in rows:
                if should_write_db_meta:
                    upsert_media_metadata(
                        self.conn,
                        media["id"],
                        write_title,
                        write_desc,
                        write_notes,
                        write_embedded_tags,
                        write_embedded_comments,
                        write_ai_prompt,
                        write_ai_negative,
                        write_ai_params,
                    )
                if merge_enabled("tags", True):
                    attach_tags(self.conn, media["id"], merged_tags)
                if all_enabled:
                    update_media_dates(
                        self.conn,
                        media["id"],
                        exif_date_taken=merged_exif_date or None,
                        metadata_date=merged_metadata_date or None,
                    )
                if merge_enabled("description", True) or merge_enabled("ai_prompts", True):
                    upsert_media_ai_selected_fields(
                        self.conn,
                        media["id"],
                        ai_prompt=write_ai_prompt,
                        ai_negative_prompt=write_ai_negative,
                        description=write_desc,
                    )
                if merge_enabled("workflows", True):
                    replace_media_ai_workflows(self.conn, media["id"], merged_workflows)
                parent_win = self.parent() if isinstance(self.parent(), QWidget) else None
                if parent_win and hasattr(parent_win, "_embed_metadata_payload_to_file"):
                    try:
                        parent_win._embed_metadata_payload_to_file(
                            str(media.get("path") or ""),
                            tags=merged_tags if merge_enabled("tags", True) else [],
                            embedded_tags_text=write_embedded_tags or "",
                            description=write_desc or "",
                            comments=write_embedded_comments or "",
                            ai_prompt=write_ai_prompt or "",
                            ai_negative_prompt=write_ai_negative or "",
                            ai_params=write_ai_params or "",
                            ai_workflows=merged_workflow_summary if merge_enabled("workflows", True) else "",
                            notes=write_notes or "",
                            exif_date_taken_raw=(merged_exif_date or "") if all_enabled else "",
                            metadata_date_raw=(merged_metadata_date or "") if all_enabled else "",
                        )
                    except Exception:
                        pass
            return True
        except Exception as exc:
            try:
                self._log(f"Merge duplicate metadata failed: {exc}")
            except Exception:
                pass
            return False

    @Slot(list, int, int, str, str, str, result=list)
    def list_media(self, folders, limit=100, offset=0, sort_by="none", filter_type="all", search_query="") -> list:
        try:
            try:
                self.conn.commit()
            except Exception:
                pass
            candidates = self._get_gallery_entries(folders, sort_by, filter_type, search_query)
            start, end = max(0, int(offset)), max(0, int(offset)) + max(0, int(limit))
            out = []
            for r in candidates[start:end]:
                if r.get("is_folder"):
                    created_time = int(r.get("file_created_time") or 0)
                    modified_time = int(r.get("modified_time") or 0)
                    original_file_date = int(r.get("original_file_date") or self._normalized_file_date_ns(created_time, modified_time))
                    auto_date = int(r.get("preferred_date") or original_file_date or created_time or modified_time)
                    out.append(
                        {
                            "path": str(r["path"]),
                            "url": "",
                            "media_type": "folder",
                            "is_folder": True,
                            "svg_bg_hint": "",
                            "is_hidden": bool(r.get("is_hidden")),
                            "is_animated": False,
                            "width": None,
                            "height": None,
                            "duration": None,
                            "file_created_time": created_time,
                            "modified_time": modified_time,
                            "original_file_date": original_file_date,
                            "exif_date_taken": None,
                            "metadata_date": None,
                            "auto_date": auto_date,
                            "file_size": None,
                            "content_hash": "",
                            "phash": "",
                            "duplicate_group_key": "",
                            "duplicate_group_size": 0,
                            "duplicate_group_position": -1,
                            "duplicate_keep_suggestion": False,
                            "duplicate_space_savings": 0,
                            "duplicate_category_reasons": [],
                            "duplicate_is_overall_best": False,
                            "color_variant": "",
                            "duplicate_crop_variant": "",
                            "duplicate_size_variant": "",
                            "duplicate_file_format": "",
                            "review_group_mode": "",
                            "text_detected": None,
                            "text_detection_score": 0.0,
                            "text_detection_version": 0,
                            "text_more_likely": None,
                            "text_more_likely_score": 0.0,
                            "text_more_likely_version": 0,
                            "text_verified": None,
                            "text_verification_score": 0.0,
                            "text_verification_version": 0,
                        }
                    )
                    continue
                real = r.get("_real_path")
                p = real if isinstance(real, Path) else Path(r["path"])
                try:
                    stat = p.stat()
                    mtime = int(stat.st_mtime_ns)
                    ctime = int(stat.st_ctime_ns)
                except Exception:
                    mtime = self._iso_to_ns(r.get("modified_time"))
                    ctime = self._iso_to_ns(r.get("file_created_time"))
                original_file_date = self._original_file_date_ns(r)
                auto_date = int(r.get("preferred_date") or self._preferred_date_ns(r))
                    
                out.append({
                    "path": str(p), 
                    "url": f"{QUrl.fromLocalFile(str(p)).toString()}?t={mtime}", 
                    "media_type": r["media_type"], 
                    "is_folder": False,
                    "svg_bg_hint": _svg_thumbnail_bg_hint(p),
                    "is_hidden": bool(r.get("is_hidden")),
                    "is_animated": self._is_animated(p),
                    "width": r.get("width"),
                    "height": r.get("height"),
                    "duration": r.get("duration"),
                    "file_created_time": ctime,
                    "modified_time": mtime,
                    "original_file_date": original_file_date or self._normalized_file_date_ns(ctime, mtime),
                    "exif_date_taken": r.get("exif_date_taken"),
                    "metadata_date": r.get("metadata_date"),
                    "auto_date": auto_date,
                    "file_size": r.get("file_size"),
                    "content_hash": r.get("content_hash") or "",
                    "phash": r.get("phash") or "",
                    "duplicate_group_key": r.get("duplicate_group_key") or "",
                    "duplicate_group_size": int(r.get("duplicate_group_size") or 0),
                    "duplicate_group_position": int(r.get("duplicate_group_position") or 0),
                    "duplicate_keep_suggestion": bool(r.get("duplicate_keep_suggestion")),
                    "duplicate_space_savings": int(r.get("duplicate_space_savings") or 0),
                    "duplicate_category_reasons": list(r.get("duplicate_category_reasons") or []),
                    "duplicate_best_reason": r.get("duplicate_best_reason") or "",
                    "duplicate_is_overall_best": bool(r.get("duplicate_is_overall_best")),
                    "color_variant": r.get("color_variant") or "",
                    "duplicate_crop_variant": r.get("duplicate_crop_variant") or "",
                    "duplicate_size_variant": r.get("duplicate_size_variant") or "",
                    "duplicate_file_format": r.get("duplicate_file_format") or "",
                    "review_group_mode": r.get("review_group_mode") or "",
                    "text_detected": r.get("text_detected"),
                    "text_detection_score": float(r.get("text_detection_score") or 0.0),
                    "text_detection_version": int(r.get("text_detection_version") or 0),
                    "text_more_likely": r.get("text_more_likely"),
                    "text_more_likely_score": float(r.get("text_more_likely_score") or 0.0),
                    "text_more_likely_version": int(r.get("text_more_likely_version") or 0),
                    "text_verified": r.get("text_verified"),
                    "text_verification_score": float(r.get("text_verification_score") or 0.0),
                    "text_verification_version": int(r.get("text_verification_version") or 0),
                })
            return out
        except Exception: return []

    @Slot(str, list, int, int, str, str, str)
    def list_media_async(self, request_id: str, folders, limit=100, offset=0, sort_by="none", filter_type="all", search_query="") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        lim = int(limit or 0)
        off = int(offset or 0)
        sort = str(sort_by or "none")
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            items = self.list_media(folder_list, lim, off, sort, ftype, query)
            self.mediaListed.emit(req, items or [])

        threading.Thread(target=work, daemon=True).start()

    @Slot(list, str, str, result=int)
    def count_media(self, folders: list, filter_type: str = "all", search_query: str = "") -> int:
        try:
            try:
                self.conn.commit()
            except Exception:
                pass
            return len(self._get_gallery_entries(folders, "none", filter_type, search_query))
        except Exception: return 0

    @Slot(str, list, str, str)
    def count_media_async(self, request_id: str, folders: list, filter_type: str = "all", search_query: str = "") -> None:
        req = str(request_id or "")
        folder_list = list(folders or [])
        ftype = str(filter_type or "all")
        query = str(search_query or "")

        def work() -> None:
            count = self.count_media(folder_list, ftype, query)
            self.mediaCounted.emit(req, int(count or 0))

        threading.Thread(target=work, daemon=True).start()

    def _get_reconciled_candidates(self, folders: list, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_scope
        from app.mediamanager.utils.pathing import normalize_windows_path
        ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS
        image_exts = IMAGE_EXTS
        media_filter, _ = self._parse_filter_groups(filter_type)
        if not folders: return []
        current_key = hashlib.sha1(",".join(sorted(folders)).encode()).hexdigest()
        if self._disk_cache and self._disk_cache_key == current_key: disk_files = self._disk_cache
        else:
            disk_files = {}
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.is_dir(): continue
                try:
                    for root_dir, _, files in os.walk(str(folder_path), followlinks=True):
                        curr_root = Path(root_dir)
                        for f in files:
                            p = curr_root / f
                            if p.suffix.lower() in ALL_EXTS: disk_files[normalize_windows_path(str(p))] = p
                except Exception: pass
            self._disk_cache, self._disk_cache_key = disk_files, current_key
        db_candidates = list_media_in_scope(self.conn, folders)
        surviving, covered = [], set()
        show_hidden = self._show_hidden_enabled()
        
        for r in db_candidates:
            norm = normalize_windows_path(r["path"])
            covered.add(norm)
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = disk_files.get(norm) or Path(r["path"])
            if path_obj.exists() and path_obj.is_dir():
                continue
            if norm in disk_files or path_obj.exists():
                if norm in disk_files:
                    r = dict(r)
                    r["_real_path"] = disk_files[norm]
                surviving.append(r)
        
        for norm, p_obj in disk_files.items():
            if norm not in covered:
                # Items only on disk are not hidden yet
                surviving.append({"id": -1, "path": norm, "media_type": ("image" if p_obj.suffix.lower() in image_exts else "video"), "file_size": None, "modified_time": None, "duration": None, "_real_path": p_obj})
        
        candidates = surviving
        if media_filter == "image":
            candidates = [
                r for r in candidates
                if Path(r["path"]).suffix.lower() in image_exts
                and Path(r["path"]).suffix.lower() != ".svg"
                and not self._is_animated(Path(r["path"]))
            ]
        elif media_filter == "svg":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() == ".svg"]
        elif media_filter == "video":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() not in image_exts]
        elif media_filter == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _get_collection_candidates(self, collection_id: int, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_collection
        image_exts = IMAGE_EXTS
        show_hidden = self._show_hidden_enabled()
        media_filter, _ = self._parse_filter_groups(filter_type)
        
        raw_candidates = list_media_in_collection(self.conn, int(collection_id))
        candidates = []
        for r in raw_candidates:
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = Path(r["path"])
            if path_obj.exists() and path_obj.is_file():
                candidates.append(r)
                
        if media_filter == "image":
            candidates = [
                r for r in candidates
                if Path(r["path"]).suffix.lower() in image_exts
                and Path(r["path"]).suffix.lower() != ".svg"
                and not self._is_animated(Path(r["path"]))
            ]
        elif media_filter == "svg":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() == ".svg"]
        elif media_filter == "video":
            candidates = [r for r in candidates if Path(r["path"]).suffix.lower() not in image_exts]
        elif media_filter == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
            
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _matches_media_search(self, row: dict, search_query: str) -> bool:
        from app.mediamanager.search_query import matches_media_search
        return matches_media_search(row, search_query)

    @staticmethod
    def _parse_filter_groups(filter_type: str) -> tuple[str, str]:
        raw = str(filter_type or "all").strip()
        media_filter = "all"
        text_filter = "all"
        if not raw or raw == "all":
            return media_filter, text_filter
        if ":" not in raw:
            if raw in {"text_detected", "text_more_likely", "text_verified"}:
                return media_filter, "text_detected"
            if raw == "no_text_detected":
                return media_filter, "no_text_detected"
            if raw in {"image", "svg", "video", "animated"}:
                return raw, text_filter
            return media_filter, text_filter
        for part in raw.split(";"):
            group, _, value = str(part or "").partition(":")
            group = group.strip().lower()
            value = value.strip().lower()
            if group == "media" and value in {"image", "svg", "video", "animated"}:
                media_filter = value
            elif group == "text":
                if value in {"text_detected", "text_more_likely", "text_verified"}:
                    text_filter = "text_detected"
                elif value == "no_text_detected":
                    text_filter = "no_text_detected"
        return media_filter, text_filter

    @staticmethod
    def _iso_to_ns(value) -> int:
        if value is None:
            return 0
        text = str(value).strip()
        if not text:
            return 0
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                return int(dt.timestamp() * 1_000_000_000)
            return int(dt.astimezone(timezone.utc).timestamp() * 1_000_000_000)
        except Exception:
            return 0

    def _preferred_date_ns(self, row: dict) -> int:
        for key in ("exif_date_taken", "metadata_date"):
            value = self._iso_to_ns(row.get(key))
            if value > 0:
                return value
        original_file_date = self._original_file_date_ns(row)
        if original_file_date > 0:
            return original_file_date
        file_created_value = row.get("file_created_time")
        if isinstance(file_created_value, int):
            if file_created_value > 0:
                return file_created_value
        else:
            value = self._iso_to_ns(file_created_value)
            if value > 0:
                return value
        raw_modified = row.get("modified_time")
        if isinstance(raw_modified, int):
            return raw_modified
        return self._iso_to_ns(raw_modified)

    def _normalized_file_date_ns(self, file_created_value, modified_value) -> int:
        values: list[int] = []
        for raw_value in (file_created_value, modified_value):
            if isinstance(raw_value, int):
                value = raw_value
            else:
                value = self._iso_to_ns(raw_value)
            if value > 0:
                values.append(value)
        return min(values) if values else 0

    def _original_file_date_ns(self, row: dict) -> int:
        raw_value = row.get("original_file_date")
        if isinstance(raw_value, int):
            if raw_value > 0:
                return raw_value
        else:
            value = self._iso_to_ns(raw_value)
            if value > 0:
                return value
        return self._normalized_file_date_ns(row.get("file_created_time"), row.get("modified_time"))

    def _list_folder_entries(self, folders: list[str], search_query: str = "") -> list[dict]:
        if not folders:
            return []

        show_hidden = self._show_hidden_enabled()
        query = (search_query or "").strip().lower()
        seen: set[str] = set()
        entries: list[dict] = []

        for folder in folders:
            root = Path(folder)
            if not root.is_dir():
                continue
            try:
                for child in root.iterdir():
                    if not child.is_dir():
                        continue
                    norm = str(child).lower().replace("\\", "/")
                    if norm in seen:
                        continue
                    is_hidden = self.repo.is_path_hidden(str(child))
                    if not show_hidden and is_hidden:
                        continue
                    if query:
                        haystack = f"{child.name} {child}".lower()
                        if query not in haystack:
                            continue
                    seen.add(norm)
                    try:
                        stat = child.stat()
                        modified_time = int(stat.st_mtime_ns)
                        created_time = int(stat.st_ctime_ns)
                    except Exception:
                        modified_time = 0
                        created_time = 0
                    entries.append(
                        {
                            "path": str(child),
                            "media_type": "folder",
                            "is_folder": True,
                            "is_hidden": is_hidden,
                            "file_size": None,
                            "file_created_time": created_time,
                            "modified_time": modified_time,
                            "original_file_date": self._normalized_file_date_ns(created_time, modified_time),
                            "preferred_date": self._normalized_file_date_ns(created_time, modified_time) or created_time or modified_time,
                            "width": None,
                            "height": None,
                            "duration": None,
                        }
                    )
            except Exception:
                continue

        return entries

    def _sort_gallery_entries(self, entries: list[dict], sort_by: str) -> list[dict]:
        name_key = lambda row: Path(str(row.get("path", ""))).name.lower()
        date_key = lambda row: row.get("preferred_date") or self._preferred_date_ns(row)
        size_key = lambda row: row.get("file_size") or 0
        folders = [row for row in entries if row.get("is_folder")]
        media = [row for row in entries if not row.get("is_folder")]

        if self._randomize_enabled() and sort_by == "none":
            folders.sort(key=name_key)
            random.Random(self._session_shuffle_seed).shuffle(media)
            return folders + media

        if sort_by == "none":
            folders.sort(key=name_key)
            media.sort(key=name_key)
            return folders + media

        if sort_by == "name_desc":
            folders.sort(key=name_key, reverse=True)
            media.sort(key=name_key, reverse=True)
            return folders + media
        if sort_by == "date_desc":
            folders.sort(key=lambda row: (date_key(row), name_key(row)), reverse=True)
            media.sort(key=lambda row: (date_key(row), name_key(row)), reverse=True)
            return folders + media
        if sort_by == "date_asc":
            folders.sort(key=lambda row: (date_key(row), name_key(row)))
            media.sort(key=lambda row: (date_key(row), name_key(row)))
            return folders + media
        if sort_by == "size_desc":
            folders.sort(key=lambda row: (size_key(row), name_key(row)), reverse=True)
            media.sort(key=lambda row: (size_key(row), name_key(row)), reverse=True)
            return folders + media
        if sort_by == "size_asc":
            folders.sort(key=lambda row: (size_key(row), name_key(row)))
            media.sort(key=lambda row: (size_key(row), name_key(row)))
            return folders + media
        folders.sort(key=name_key)
        media.sort(key=name_key)
        return folders + media

    def _get_gallery_entries(self, folders: list[str], sort_by: str = "none", filter_type: str = "all", search_query: str = "") -> list[dict]:
        _, text_filter = self._parse_filter_groups(filter_type)
        if folders:
            entries = self._get_reconciled_candidates(folders, filter_type, search_query)
            if self._gallery_view_mode() not in {"masonry", "duplicates", "similar", "similar_only"} and self._review_group_mode() is None:
                entries = self._list_folder_entries(folders, search_query) + entries
        elif self._active_collection_id is not None:
            entries = self._get_collection_candidates(self._active_collection_id, filter_type, search_query)
        else:
            entries = []
        if text_filter in {"text_detected", "no_text_detected"}:
            self._ensure_background_text_processing(folders if folders else None, self._active_collection_id if not folders else None)
            if text_filter == "no_text_detected":
                entries = [entry for entry in entries if not bool(entry.get("text_detected"))]
            else:
                entries = [entry for entry in entries if bool(entry.get("text_detected"))]
        review_mode = self._review_group_mode()
        if review_mode in {"similar", "similar_only"}:
            self._backfill_scope_content_hashes(entries)
            self._backfill_scope_phashes(entries)
            threshold, bucket_prefix = self._similarity_config()
            return self._build_similar_entries(
                entries,
                sort_by,
                include_exact=(review_mode == "similar"),
                threshold=threshold,
                bucket_prefix=bucket_prefix,
            )
        if review_mode == "duplicates":
            self._backfill_scope_content_hashes(entries)
            return self._build_duplicate_entries(entries, sort_by)
        return self._sort_gallery_entries(entries, sort_by)

    @Slot(list, str)
    def start_scan(self, folders: list, search_query: str = "") -> None:
        if not folders:
            return
        scan_key = hashlib.sha1(",".join(sorted(str(folder) for folder in folders)).encode()).hexdigest()
        if self._last_full_scan_key == scan_key:
            return
        self._cancel_text_processing()
        self._scan_abort = True
        def work():
            try:
                time.sleep(0.1)
                self._scan_abort = False
                primary = folders[0] if folders else ""
                self.scanStarted.emit(primary)
                with self._scan_lock:
                    # Always refresh the reconciled scope first so a newly selected root
                    # cannot accidentally inherit stale paths from a previous disk cache.
                    self._get_reconciled_candidates(folders, "all", search_query)
                    paths = list(self._disk_cache.values())
                    self._do_full_scan(paths, self.conn, emit_progress=True)
                    self._last_full_scan_key = scan_key
                    self.scanFinished.emit(primary, len(self._get_reconciled_candidates(folders, "all", search_query)))
                self._ensure_background_text_processing(list(folders), None)
            except Exception as exc:
                try:
                    self._log(f"Background scan failed: {exc}")
                except Exception:
                    pass
        threading.Thread(target=work, daemon=True).start()

    @Slot(list)
    def start_scan_paths(self, paths: list[str]) -> None:
        clean_paths = [Path(path) for path in paths if str(path or "").strip()]
        if not clean_paths:
            return
        def work():
            try:
                with self._scan_lock:
                    self._do_full_scan(clean_paths, self.conn, emit_progress=False)
            except Exception as exc:
                try:
                    self._log(f"Page scan failed: {exc}")
                except Exception:
                    pass
        threading.Thread(target=work, daemon=True).start()

    def _do_full_scan(self, paths: list[Path], conn, emit_progress: bool = True) -> int:
        from app.mediamanager.db.media_repo import get_media_by_path, upsert_media_item
        from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
        from app.mediamanager.utils.hashing import calculate_file_hash, calculate_image_phash
        from datetime import datetime, timezone
        total, count = len(paths), 0
        for i, p in enumerate(paths):
            if self._scan_abort: break
            if emit_progress:
                self.scanProgress.emit(p.name, int(((i + 1) / total) * 100) if total > 0 else 100)
            try:
                stat = p.stat()
                existing, skip = get_media_by_path(conn, str(p)), False
                media_id = existing["id"] if existing else None
                if existing:
                    curr_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    if existing["file_size"] == stat.st_size and existing.get("modified_time") == curr_mtime:
                        has_required_content_hash = bool(str(existing.get("content_hash") or "").strip())
                        has_required_visual_data = bool(existing.get("width") and existing.get("height"))
                        if p.suffix.lower() in IMAGE_EXTS and p.suffix.lower() != ".svg":
                            has_required_visual_data = has_required_visual_data and bool(str(existing.get("phash") or "").strip())
                        if has_required_content_hash and has_required_visual_data:
                            skip = True
                
                if not skip:
                    width, height, d_ms = None, None, None
                    mtype = "image" if p.suffix.lower() in IMAGE_EXTS else "video"
                    
                    phash = None
                    if mtype == "image":
                        sz = _image_size_with_svg_support(p)
                        if sz.isValid():
                            width, height = sz.width(), sz.height()
                        
                        # Fallback for formats like AVIF that Qt can't read natively
                        if width is None or height is None:
                            w, h, _ = self._probe_video_size(str(p))
                            if w > 0 and h > 0:
                                width, height = w, h
                        phash = calculate_image_phash(p)
                    else:
                        w, h, _ = self._probe_video_size(str(p))
                        if w > 0 and h > 0:
                            width, height = w, h
                        # Capture duration for looping logic
                        d_s = self.get_video_duration_seconds(str(p))
                        if d_s > 0:
                            d_ms = int(d_s * 1000)
                        
                    media_id = upsert_media_item(
                        conn,
                        str(p),
                        mtype,
                        calculate_file_hash(p),
                        phash=phash,
                        width=width,
                        height=height,
                        duration_ms=d_ms,
                    )
                if media_id is not None:
                    inspect_and_persist_if_supported(conn, media_id, str(p), "image" if p.suffix.lower() in IMAGE_EXTS else "video")
                count += 1
            except Exception as exc:
                try:
                    self._log(f"Background scan item failed for {p}: {exc}")
                except Exception:
                    pass
        return count

    @Slot(str, result=str)
    def get_video_poster(self, video_path: str) -> str:
        try:
            p = Path(video_path)
            if not p.exists() or not p.is_file():
                return ""
            out = self._ensure_video_poster(p)
            if out:
                try:
                    mtime = int(out.stat().st_mtime_ns)
                except Exception:
                    import time
                    mtime = int(time.time() * 1000)
                return f"{QUrl.fromLocalFile(str(out)).toString()}?t={mtime}"
            return ""
        except Exception: return ""

    @Slot(result=dict)
    def get_tools_status(self) -> dict:
        return {"ffmpeg": bool(self._ffmpeg_bin()), "ffmpeg_path": self._ffmpeg_bin() or "", "ffprobe": bool(self._ffprobe_bin()), "ffprobe_path": self._ffprobe_bin() or "", "thumb_dir": str(self._thumb_dir)}


class NativeDragTooltip(QWidget):
    """A floating stack with preview image above tooltip text during drag operations."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("nativeDragTooltip")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.preview_label = QLabel(self)
        self.preview_label.setObjectName("nativeDragTooltipPreview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        layout.addWidget(self.preview_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel(self)
        self.text_label.setObjectName("nativeDragTooltipText")
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.update_style(QColor(Theme.ACCENT_DEFAULT), Theme.get_is_light())

    def update_style(self, accent_color: QColor, is_light: bool):
        bg = Theme.get_control_bg(accent_color)
        fg = Theme.get_text_color()
        border = Theme.get_border(accent_color)
        
        self.setStyleSheet(f"""
            #nativeDragTooltipText {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }}
        """)

    def update_text(self, text: str):
        self.text_label.setText(text)
        self.adjustSize()

    def set_preview_pixmap(self, pixmap: QPixmap | None) -> None:
        if pixmap is None or pixmap.isNull():
            self.preview_label.clear()
            self.preview_label.hide()
        else:
            self.preview_label.setPixmap(pixmap)
            self.preview_label.show()
        self.adjustSize()

    def follow_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() + 10, pos.y() - (self.height() // 2))
        if not self.isVisible():
            self.show()


class NativeSeparator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(21)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(Theme.get_border(QColor(Theme.ACCENT_DEFAULT))))
        pen.setWidth(2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        y = self.height() // 2
        painter.drawLine(0, y, self.width(), y)


class GalleryView(QWebEngineView):
    """Gallery view that accepts drag and drop from external file explorers."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def _probe_gallery_folder_target(self, x: int, y: int) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if not bridge:
            return

        script = (
            "(() => {"
            f"  const el = document.elementFromPoint({int(x)}, {int(y)});"
            "  const card = el && el.closest ? el.closest('.folder-card[data-path]') : null;"
            "  return card ? card.getAttribute('data-path') : '';"
            "})()"
        )

        def _apply_target(target_path: str) -> None:
            try:
                bridge.drag_target_folder = str(target_path or "")
                bridge.dragOverFolder.emit(Path(target_path).name if target_path else "")
            except Exception:
                pass

        try:
            self.page().runJavaScript(script, _apply_target)
        except Exception:
            try:
                bridge.drag_target_folder = ""
                bridge.dragOverFolder.emit("")
            except Exception:
                pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        # Determine target folder
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        
        is_file_drag = False
        if bridge and bridge.drag_paths:
            is_file_drag = True
        elif event.mimeData().hasUrls():
            is_file_drag = True
            
        if is_file_drag and bridge:
            try:
                pos = event.position()
                x, y = int(pos.x()), int(pos.y())
            except Exception:
                pos = event.pos()
                x, y = int(pos.x()), int(pos.y())
            self._probe_gallery_folder_target(x, y)
            target_folder = bridge.drag_target_folder or ""
            
            # Count items: side-channel first (internal), then MIME (external)
            count = len(bridge.drag_paths) if bridge.drag_paths else len(event.mimeData().urls())
            if count == 0: count = 1
            
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            
            # Target folder name for display
            target_name = Path(target_folder).name if target_folder else ""
            
            bridge.update_drag_tooltip(count, is_copy, target_name)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.drag_target_folder = ""
            bridge.dragOverFolder.emit("")
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
            
            mime = event.mimeData()
            src_paths = []
            
            # Priority 0: Side-channel from Bridge (Internal Gallery -> Gallery)
            if bridge and bridge.drag_paths:
                src_paths = list(bridge.drag_paths)
            
            # Priority 1: Fallback to MIME data (External drops)
            if not src_paths and mime.hasUrls():
                src_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]
            
            if src_paths:
                if bridge.drag_paths:
                    target_path = bridge.drag_target_folder
                else:
                    target_path = ""
                if not target_path and not bridge.drag_paths:
                    selected = bridge.get_selected_folders()
                    target_path = selected[0] if selected else ""
                
                if target_path:
                    target_path_norm = target_path.replace("\\", "/").lower()

                    # Internal gallery drags dropped back onto the gallery background
                    # should be treated as a cancelled drag, not as a move/copy into
                    # the currently loaded folder.
                    if bridge.drag_paths:
                        if not bridge.drag_target_folder:
                            event.ignore()
                            return

                    # Filter out if moving to THE SAME folder
                    src_paths = [p for p in src_paths if os.path.dirname(p).replace("\\", "/").lower() != target_path_norm]
                    
                    if src_paths:
                        # Determine if COPY or MOVE
                        is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                        op_type = "copy" if is_copy else "move"
                        
                        paths_obj = [Path(p) for p in src_paths]
                        bridge._process_file_op(op_type, paths_obj, Path(target_path))
                        bridge.drag_target_folder = ""
                        bridge.dragOverFolder.emit("")
                        event.acceptProposedAction()
                        return
                if bridge.drag_paths:
                    bridge.drag_target_folder = ""
                    bridge.dragOverFolder.emit("")
                    event.ignore()
                    return
        
        super().dropEvent(event)


class MainWindow(QMainWindow):
    _DEFAULT_LEFT_PANEL_WIDTH = 200
    _DEFAULT_CENTER_WIDTH = 700
    _DEFAULT_RIGHT_PANEL_WIDTH = 300
    _DEFAULT_BOTTOM_PANEL_HEIGHT = 220
    videoSidebarMetadataReady = Signal(str, dict)
    videoSidebarPosterReady = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MediaLens")
        self.resize(1200, 800)

        startup_settings = QSettings("G1enB1and", "MediaManagerX")
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
        self.bridge.openVideoRequested.connect(self._open_video_overlay)
        self.bridge.openVideoInPlaceRequested.connect(self._open_video_inplace)
        self.bridge.updateVideoRectRequested.connect(self._update_video_inplace_rect)
        self.bridge.closeVideoRequested.connect(self._close_video_overlay)
        self.bridge.videoMutedChanged.connect(self._on_video_muted_changed)
        self.bridge.videoPausedChanged.connect(self._on_video_paused_changed)
        self.bridge.videoPreprocessingStatus.connect(self._on_video_preprocessing_status)
        self.bridge.uiFlagChanged.connect(self._apply_ui_flag)
        self.bridge.metadataRequested.connect(self._show_metadata_for_path)
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
        self._current_accent = Theme.ACCENT_DEFAULT
        self._folder_history: list[str] = []
        self._folder_history_index: int = -1
        self._settings_dialog: SettingsDialog | None = None
        self._suppress_tree_selection_history = False
        self._tree_root_path: str = ""
        self._pending_tree_sync_path: str = ""
        self._pending_tree_reroot: bool = False
        self._tree_sync_timer = QTimer(self)
        self._tree_sync_timer.setSingleShot(True)
        self._tree_sync_timer.timeout.connect(self._apply_pending_tree_sync)

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

        # Check for updates on launch if enabled
        if self.bridge.settings.value("updates/check_on_launch", True, type=bool):
            # Short delay to let the UI finish rendering before the network request
            QTimer.singleShot(1500, lambda: self.bridge.check_for_updates(manual=False))

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
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_action)

        pick_action = QAction("Choose &Folder…", self)
        pick_action.triggered.connect(self.choose_folder)
        file_menu.addAction(pick_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")

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

        self.act_show_dismissed_progress_toasts = QAction("Show Hidden Progress Toasts", self)
        self.act_show_dismissed_progress_toasts.triggered.connect(self.bridge.reveal_progress_toasts)
        view_menu.addAction(self.act_show_dismissed_progress_toasts)

        view_menu.addSeparator()

        devtools_action = QAction("Toggle &DevTools", self)
        devtools_action.setShortcut("F12")
        devtools_action.triggered.connect(self.toggle_devtools)
        view_menu.addAction(devtools_action)

        help_menu = menubar.addMenu("&Help")
        
        whats_new_action = QAction("&What's New", self)
        whats_new_action.triggered.connect(self.show_whats_new)
        help_menu.addAction(whats_new_action)
        search_help_action = QAction("&Search Syntax Help", self)
        search_help_action.triggered.connect(self.show_search_syntax_help)
        help_menu.addAction(search_help_action)
        
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

        diagnostics_action = QAction("Create &Diagnostic Report", self)
        diagnostics_action.triggered.connect(self.create_diagnostic_report)
        help_menu.addAction(diagnostics_action)

        crash_logs_action = QAction("Open &Crash Report Folder", self)
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

        self.menu_btn_settings = QPushButton("⚙", container)
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
            button.setText("•")
        button.setIconSize(QSize(18, 18))

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
        return isinstance(f, (QLineEdit, QTextEdit, QPlainTextEdit))

    def _on_copy_shortcut(self) -> None:
        if self._is_input_focused(): return
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
        if use_recycle:
            for p in paths:
                self.bridge.delete_path(p)
        else:
            count = len(paths)
            msg = f"Are you sure you want to permanently delete {count} items?" if count > 1 else f"Are you sure you want to permanently delete '{Path(paths[0]).name}'?"
            ret = QMessageBox.question(self, "Confirm Permanent Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                for p in paths:
                    self.bridge.delete_path_permanent(p)

    def _on_shift_delete_shortcut(self) -> None:
        if self._is_input_focused(): return
        paths = self._get_focused_paths()
        if not paths: return
        
        count = len(paths)
        msg = f"Are you sure you want to permanently delete {count} items?" if count > 1 else f"Are you sure you want to permanently delete '{Path(paths[0]).name}'?"
        ret = QMessageBox.question(self, "Confirm Permanent Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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

        self.left_sections_splitter.addWidget(pinned_section)
        self.left_sections_splitter.addWidget(folders_section)
        self.left_sections_splitter.addWidget(collections_section)
        self.left_sections_splitter.setStretchFactor(0, 0)
        self.left_sections_splitter.setStretchFactor(1, 1)
        self.left_sections_splitter.setStretchFactor(2, 0)
        left_sections_state = self.bridge.settings.value("ui/left_sections_splitter_state_v2")
        if left_sections_state:
            self.left_sections_splitter.restoreState(left_sections_state)
        else:
            self.left_sections_splitter.setSizes([140, 290, 170])
        self.left_sections_splitter.splitterMoved.connect(lambda *args: self._save_splitter_state())

        left_layout.addWidget(self.left_sections_splitter, 1)

        self.bridge.pinnedFoldersChanged.connect(self._reload_pinned_folders)
        self.bridge.collectionsChanged.connect(self._reload_collections)
        self._reload_pinned_folders()
        self._reload_collections()

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

        self.web_loading_label = QLabel("Loading gallery UI…")
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

        # Right: Metadata Panel
        self.right_panel = QWidget(splitter)
        self.right_panel.setObjectName("rightPanel")
        outer_right_layout = QVBoxLayout(self.right_panel)
        outer_right_layout.setContentsMargins(0, 0, 0, 0)
        outer_right_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("metaScrollArea")
        
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
        self.btn_close_preview = QPushButton("×")
        self.btn_close_preview.setObjectName("btnClosePreview")
        self.btn_close_preview.setToolTip("Hide preview image")
        self.btn_close_preview.setFixedSize(QSize(22, 22))
        self.btn_close_preview.clicked.connect(lambda: self.bridge.set_setting_bool("ui.preview_above_details", False))
        preview_header_layout.addWidget(self.btn_close_preview)

        # Toggle ON (Show) button
        self.btn_show_preview_inline = QPushButton("⛶") # Unicode maximize/corners
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

        self.scroll_area.setWidget(self.scroll_container)
        outer_right_layout.addWidget(self.scroll_area)

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

        self.meta_original_file_date_lbl = QLabel("")
        self.meta_original_file_date_lbl.setObjectName("metaOriginalFileDateLabel")

        self.meta_file_created_date_lbl = QLabel("")
        self.meta_file_created_date_lbl.setObjectName("metaFileCreatedDateLabel")

        self.meta_file_modified_date_lbl = QLabel("")
        self.meta_file_modified_date_lbl.setObjectName("metaFileModifiedDateLabel")
        
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

        self.lbl_ai_source_cap = QLabel("AI Tool / Source:")
        self.lbl_ai_source_cap.setObjectName("metaAISourceCaption")
        self.meta_ai_source_edit = QTextEdit()
        self.meta_ai_source_edit.setObjectName("metaAISourceEdit")
        self.meta_ai_source_edit.setReadOnly(True)
        self.meta_ai_source_edit.setPlaceholderText("Tool and source metadata...")
        self.meta_ai_source_edit.setMaximumHeight(60)

        self.lbl_ai_families_cap = QLabel("AI Metadata Families:")
        self.lbl_ai_families_cap.setObjectName("metaAIFamiliesCaption")
        self.meta_ai_families_edit = QLineEdit()
        self.meta_ai_families_edit.setObjectName("metaAIFamiliesEdit")
        self.meta_ai_families_edit.setReadOnly(True)
        self.meta_ai_families_edit.setPlaceholderText("Detected metadata families...")

        self.lbl_ai_detection_reasons_cap = QLabel("AI Detection Reasons:")
        self.lbl_ai_detection_reasons_cap.setObjectName("metaAIDetectionReasonsCaption")
        self.meta_ai_detection_reasons_edit = QTextEdit()
        self.meta_ai_detection_reasons_edit.setObjectName("metaAIDetectionReasonsEdit")
        self.meta_ai_detection_reasons_edit.setReadOnly(True)
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
        self.meta_ai_model_edit.setReadOnly(True)
        self.meta_ai_model_edit.setPlaceholderText("Model...")

        self.lbl_ai_checkpoint_cap = QLabel("AI Checkpoint:")
        self.lbl_ai_checkpoint_cap.setObjectName("metaAICheckpointCaption")
        self.meta_ai_checkpoint_edit = QLineEdit()
        self.meta_ai_checkpoint_edit.setObjectName("metaAICheckpointEdit")
        self.meta_ai_checkpoint_edit.setReadOnly(True)
        self.meta_ai_checkpoint_edit.setPlaceholderText("Checkpoint...")

        self.lbl_ai_sampler_cap = QLabel("AI Sampler:")
        self.lbl_ai_sampler_cap.setObjectName("metaAISamplerCaption")
        self.meta_ai_sampler_edit = QLineEdit()
        self.meta_ai_sampler_edit.setObjectName("metaAISamplerEdit")
        self.meta_ai_sampler_edit.setReadOnly(True)
        self.meta_ai_sampler_edit.setPlaceholderText("Sampler...")

        self.lbl_ai_scheduler_cap = QLabel("AI Scheduler:")
        self.lbl_ai_scheduler_cap.setObjectName("metaAISchedulerCaption")
        self.meta_ai_scheduler_edit = QLineEdit()
        self.meta_ai_scheduler_edit.setObjectName("metaAISchedulerEdit")
        self.meta_ai_scheduler_edit.setReadOnly(True)
        self.meta_ai_scheduler_edit.setPlaceholderText("Scheduler...")

        self.lbl_ai_cfg_cap = QLabel("AI CFG:")
        self.lbl_ai_cfg_cap.setObjectName("metaAICFGCaption")
        self.meta_ai_cfg_edit = QLineEdit()
        self.meta_ai_cfg_edit.setObjectName("metaAICFGEdit")
        self.meta_ai_cfg_edit.setReadOnly(True)
        self.meta_ai_cfg_edit.setPlaceholderText("CFG...")

        self.lbl_ai_steps_cap = QLabel("AI Steps:")
        self.lbl_ai_steps_cap.setObjectName("metaAIStepsCaption")
        self.meta_ai_steps_edit = QLineEdit()
        self.meta_ai_steps_edit.setObjectName("metaAIStepsEdit")
        self.meta_ai_steps_edit.setReadOnly(True)
        self.meta_ai_steps_edit.setPlaceholderText("Steps...")

        self.lbl_ai_seed_cap = QLabel("AI Seed:")
        self.lbl_ai_seed_cap.setObjectName("metaAISeedCaption")
        self.meta_ai_seed_edit = QLineEdit()
        self.meta_ai_seed_edit.setObjectName("metaAISeedEdit")
        self.meta_ai_seed_edit.setReadOnly(True)
        self.meta_ai_seed_edit.setPlaceholderText("Seed...")

        self.lbl_ai_upscaler_cap = QLabel("AI Upscaler:")
        self.lbl_ai_upscaler_cap.setObjectName("metaAIUpscalerCaption")
        self.meta_ai_upscaler_edit = QLineEdit()
        self.meta_ai_upscaler_edit.setObjectName("metaAIUpscalerEdit")
        self.meta_ai_upscaler_edit.setReadOnly(True)
        self.meta_ai_upscaler_edit.setPlaceholderText("Upscaler...")

        self.lbl_ai_denoise_cap = QLabel("AI Denoise:")
        self.lbl_ai_denoise_cap.setObjectName("metaAIDenoiseCaption")
        self.meta_ai_denoise_edit = QLineEdit()
        self.meta_ai_denoise_edit.setObjectName("metaAIDenoiseEdit")
        self.meta_ai_denoise_edit.setReadOnly(True)
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
        self.meta_desc.setMaximumHeight(90)
        self.meta_desc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.lbl_tags_cap = QLabel("Tags (comma separated):")
        self.meta_tags = QLineEdit()
        self.meta_tags.setPlaceholderText("tag1, tag2...")
        self.meta_tags.editingFinished.connect(self._save_native_tags)

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

        self.meta_status_lbl = QLabel("")
        self.meta_status_lbl.setObjectName("metaStatusLabel")
        self.meta_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.meta_status_lbl)
        self._update_sidebar_action_buttons()
        self._update_sidebar_input_widths()

        self._update_native_styles(accent_val)
        self._update_splitter_style(accent_val)

        self._devtools: QWebEngineView | None = None
        self.video_overlay = LightboxVideoOverlay(parent=self.web)
        self.video_overlay.setGeometry(self.web.rect())
        # When native overlay closes, also close the web lightbox chrome.
        self.video_overlay.on_close = self._close_web_lightbox
        self.video_overlay.on_prev = self._on_video_prev
        self.video_overlay.on_next = self._on_video_next
        self.video_overlay.raise_()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        index_path = Path(__file__).with_name("web") / "index.html"

        # Web loading signals (with minimum on-screen time to avoid flashing)
        self._web_loading_shown_ms: int | None = None
        self._web_loading_min_ms = 1000
        self.web.loadStarted.connect(lambda: self._set_web_loading(True))
        self.web.loadProgress.connect(self._on_web_load_progress)
        self.web.loadFinished.connect(lambda _ok: self._set_web_loading(False))

        self.web.setUrl(QUrl.fromLocalFile(str(index_path.resolve())))

        self.bottom_panel = QWidget(center_splitter)
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setMinimumHeight(0)
        self.bottom_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(14, 10, 14, 14)
        bottom_layout.setSpacing(6)

        self.bottom_panel_header_row = QWidget(self.bottom_panel)
        bottom_panel_header_layout = QHBoxLayout(self.bottom_panel_header_row)
        bottom_panel_header_layout.setContentsMargins(0, 0, 0, 0)
        bottom_panel_header_layout.setSpacing(8)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_header = QLabel("Image Comparison")
        self.bottom_panel_header.setObjectName("bottomPanelHeader")
        self.bottom_panel_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addWidget(self.bottom_panel_header, 0, Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_close_btn = QPushButton("X")
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

        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setObjectName("mainSplitter")
        splitter.setMouseTracking(True)
        splitter.setHandleWidth(7)

        self._restore_main_splitter_sizes()
        self._restore_center_splitter_sizes()

        splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())
        center_splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())

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
        self._update_preview_visibility()
        self._clear_metadata_panel()
        QTimer.singleShot(0, self._apply_initial_web_background)

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
            if self.right_panel.isVisible() and sizes[2] > 0:
                self.bridge.settings.setValue("ui/right_panel_width", int(sizes[2]))
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
        try:
            if re_root_tree or not self._tree_root_path:
                self._set_tree_root(path_str)
            self._sync_tree_to_folder(path_str)
        except Exception as exc:
            self.bridge._log(f"Tree sync failed for {path_str}: {exc}")

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
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if not current_path:
            self._update_navigation_state()
            return
        self._navigate_to_folder(current_path, record_history=False, refresh=True)

    def _on_directory_loaded(self, path: str) -> None:
        """Triggered when QFileSystemModel finishes loading a directory's contents."""
        self.bridge._log(f"Tree: Directory loaded: {path}")
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
        if current_path:
            try:
                self._sync_tree_to_folder(current_path)
                self.tree.viewport().update()
            except Exception as exc:
                self.bridge._log(f"Tree current-folder sync failed after directory load: {exc}")

    def _on_tree_selection(self, *_args) -> None:
        if self._suppress_tree_selection_history:
            return
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
        self.tree.expand(root_index)
        self._expand_tree_branch(root_index)

    def _collapse_tree_to_root(self) -> None:
        root_index = self.tree.rootIndex()
        if not root_index.isValid():
            return
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
        self.bridge.set_active_collection(collection_id)

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
            name, ok = QInputDialog.getText(self, "New Collection", "Collection Name:")
            if ok and name.strip():
                created = self.bridge.create_collection(name)
                if created:
                    self._reload_collections()
                    self.bridge.set_active_collection(int(created.get("id", 0) or 0))
                    self._reload_collections()
        elif item and chosen == act_rename:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            current_name = item.text()
            name, ok = QInputDialog.getText(self, "Rename Collection", "Collection Name:", text=current_name)
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
                self.right_panel.setVisible(bool(value))
                QTimer.singleShot(0, self._restore_main_splitter_sizes)
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
                    self._update_sidebar_input_widths()
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
            if key == "ui.show_left_panel" and hasattr(self, "act_toggle_left_panel"):
                self.act_toggle_left_panel.setChecked(bool(value))
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
        margins = self.right_layout.contentsMargins() if hasattr(self, "right_layout") else None
        left = margins.left() if margins else 12
        right = margins.right() if margins else 12
        viewport_w = self.scroll_area.viewport().width()
        return max(90, viewport_w - left - right)

    def _update_sidebar_action_buttons(self) -> None:
        if not hasattr(self, "scroll_area"):
            return
        available_w = self._right_panel_content_width()
        buttons = [
            getattr(self, "btn_clear_bulk_tags", None),
            getattr(self, "btn_save_meta", None),
            getattr(self, "btn_import_exif", None),
            getattr(self, "btn_merge_hidden_meta", None),
            getattr(self, "btn_save_to_exif", None),
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

    def _update_sidebar_input_widths(self) -> None:
        if not hasattr(self, "scroll_container"):
            return
        available_w = self._right_panel_content_width()
        self.preview_image_lbl.setFixedWidth(available_w)
        for widget in self.scroll_container.findChildren(QWidget):
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
        if visible:
            self._clear_preview_media()
            self.preview_image_lbl.setText("")
            for widget in self._metadata_content_widgets():
                widget.setVisible(False)

    def _configure_bulk_tag_editor(self, selection_count: int) -> None:
        if hasattr(self, "preview_header_row"):
             self.preview_header_row.setVisible(False)
        self.preview_image_lbl.setVisible(False)
        self.preview_sep.setVisible(False)
        self.details_header_row.setVisible(False)
        self.lbl_group_general.setVisible(False)
        self.lbl_group_camera.setVisible(False)
        self.lbl_group_ai.setVisible(False)
        self.meta_sep1.setVisible(False)
        self.meta_sep2.setVisible(False)
        self.meta_sep3.setVisible(False)
        self.lbl_fn_cap.setVisible(False)
        self.meta_filename_edit.setVisible(False)
        self.meta_path_lbl.setVisible(False)
        self.btn_import_exif.setVisible(False)
        self.btn_merge_hidden_meta.setVisible(False)
        self.lbl_tags_cap.setText("Tags (comma or semicolon separated):")
        self.lbl_tags_cap.setVisible(True)
        self.meta_tags.setVisible(True)
        self.meta_tags.setPlaceholderText("tag1, tag2, tag3")
        self.btn_save_meta.setVisible(True)
        self.btn_save_meta.setProperty("baseText", f"Save Tags to DB for {selection_count} Items")
        self.btn_clear_bulk_tags.setVisible(True)
        self.btn_clear_bulk_tags.setProperty("baseText", f"Clear Tags from DB for {selection_count} Items")
        self.btn_save_to_exif.setVisible(True)
        self.btn_save_to_exif.setProperty("baseText", f"Embed Tags in {selection_count} Files")
        self.btn_save_to_exif.setToolTip("Write only the entered tags into each selected file's embedded metadata")
        self._update_sidebar_action_buttons()

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
        self._set_preview_pixmap(QPixmap.fromImage(img), bg_hint=_svg_thumbnail_bg_hint(preview_path))
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
        paths = getattr(self, "_current_paths", [])
        if not paths and hasattr(self, "_current_path") and self._current_path:
            paths = [self._current_path]
            
        if not paths:
            return

        is_bulk = len(paths) > 1
        tags_str = self.meta_tags.text()
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
            
            ai_prompt = self.meta_ai_prompt_edit.toPlainText()
            ai_neg_prompt = self.meta_ai_negative_prompt_edit.toPlainText()
            ai_params = self.meta_ai_params_edit.toPlainText()
            exif_date_taken = self._normalize_metadata_datetime(self.meta_exif_date_taken_edit.text())
            metadata_date = self._normalize_metadata_datetime(self.meta_metadata_date_edit.text())

            try:
                # Save Changes is DB-only. Embedded fields are file-only and should not be persisted here.
                self.bridge.update_media_metadata(path, "", desc, notes, "", "", ai_prompt, ai_neg_prompt, ai_params)
                self.bridge.update_media_dates(path, exif_date_taken, metadata_date)
                self.bridge.set_media_tags(path, tags)
            except Exception:
                pass
        else:
            for p in paths:
                try:
                    existing = self.bridge.get_media_metadata(p).get("tags", [])
                    self.bridge.set_media_tags(p, self._merge_tag_lists(existing, tags))
                except Exception:
                    pass

        # --- Show confirmation then auto-clear after 3s ---
        self.meta_status_lbl.setText(f"✓ {'Tags' if is_bulk else 'Changes'} saved")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))

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
                self.meta_original_file_date_lbl.setText(f"Original File Date: {original_file_text}")
            file_created_text = self._format_sidebar_datetime((media or {}).get("file_created_time"))
            if file_created_text:
                self.meta_file_created_date_lbl.setText(f"Windows ctime: {file_created_text}")
            file_modified_text = self._format_sidebar_datetime((media or {}).get("modified_time"))
            if file_modified_text:
                self.meta_file_modified_date_lbl.setText(f"Date Modified: {file_modified_text}")

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
            # No headers – treat whole thing as plain comment
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
            message = f"✓ Tags embedded in {completed} file{'s' if completed != 1 else ''}"
            if skipped:
                message += f" ({skipped} skipped)"
            self.meta_status_lbl.setText(message)
            QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        elif skipped:
            self.meta_status_lbl.setText("No selected files support embedded tags.")

    @Slot()
    def _save_to_exif_cmd(self) -> None:
        """Embed tags and comments from the 'Embedded' UI fields INTO the file."""
        paths = getattr(self, "_current_paths", [])
        if len(paths) > 1:
            self._embed_bulk_tags_to_files(paths, self._normalize_tag_list(self.meta_tags.text()))
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
                    self.meta_original_file_date_lbl.setText(f"Original File Date: {original_file_text}")
                file_created_text = self._format_sidebar_datetime(data.get("file_created_time"))
                if file_created_text:
                    self.meta_file_created_date_lbl.setText(f"Windows ctime: {file_created_text}")
                file_modified_text = self._format_sidebar_datetime(data.get("modified_time"))
                if file_modified_text:
                    self.meta_file_modified_date_lbl.setText(f"Date Modified: {file_modified_text}")
            except Exception:
                pass
            self.meta_status_lbl.setText("✓ Metadata embedded in file")
            QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        except Exception as e:
            self.meta_status_lbl.setText(f"Embed Error: {e}")
    def _clear_bulk_tags(self) -> None:
        """Remove all tags from currently selected files with warning."""
        paths = getattr(self, "_current_paths", [])
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

        self.meta_status_lbl.setText(f"✓ Tags cleared for {len(paths)} items")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))
        
        # Clear the UI text box
        self.meta_tags.setText("")

    def _save_native_tags(self) -> None:
        # We delegate to the main metadata saver to avoid logic duplication
        # (Editing tags triggers a soft save).
        self._save_native_metadata()

    def _show_metadata_for_path(self, paths: list[str]) -> None:
        # Ignore empty lists (e.g. from background clicks that deselect cards).
        if not paths:
            self._clear_metadata_panel()
            return

        is_bulk = len(paths) > 1
        primary_path = paths[0] if paths else None
        is_video = bool(primary_path and Path(primary_path).suffix.lower() in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"})
        self._set_metadata_empty_state(False)
        self._current_paths = paths # Store list for bulk save
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
            self._update_sidebar_input_widths()
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
        self.meta_original_file_date_lbl.setVisible(not is_bulk and show_original_file_date)
        self.meta_file_created_date_lbl.setVisible(not is_bulk and show_file_created_date)
        self.meta_file_modified_date_lbl.setVisible(not is_bulk and show_file_modified_date)
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
        self.meta_original_file_date_lbl.setText("Original File Date: ")
        self.meta_file_created_date_lbl.setText("Windows ctime: ")
        self.meta_file_modified_date_lbl.setText("Date Modified: ")
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
        self.meta_ai_status_edit.setText("")
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
        self.lbl_notes_cap.setVisible(not is_bulk and show_notes)
        self.meta_notes.setVisible(not is_bulk and show_notes)
        
        self.lbl_tags_cap.setVisible(not is_bulk and ("tags" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "tags", True)))
        self.meta_tags.setVisible(not is_bulk and ("tags" in active_fields and self._is_metadata_enabled_for_kind(metadata_kind, "tags", True)))
        self.btn_clear_bulk_tags.setVisible(is_bulk)
        
        self.meta_filename_edit.blockSignals(True)
        self.meta_desc.blockSignals(True)
        self.meta_tags.blockSignals(True)
        self.meta_notes.blockSignals(True)
        self.meta_exif_date_taken_edit.blockSignals(True)
        self.meta_metadata_date_edit.blockSignals(True)

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
                self.meta_desc.setPlainText(data.get("description", ""))
                self.meta_notes.setPlainText(data.get("notes", ""))
                
                db_prompt = data.get('ai_prompt', '')
                if db_prompt: self.meta_ai_prompt_edit.setPlainText(db_prompt)

                db_neg_prompt = data.get('ai_negative_prompt', '')
                if db_neg_prompt: self.meta_ai_negative_prompt_edit.setPlainText(db_neg_prompt)
                
                db_params = data.get('ai_params', '')
                if db_params: self.meta_ai_params_edit.setPlainText(db_params)

                self.meta_ai_status_edit.setText(data.get("ai_status_summary", ""))
                self.meta_ai_source_edit.setPlainText(data.get("ai_source_summary", ""))
                self.meta_ai_families_edit.setText(data.get("ai_families_summary", ""))
                self.meta_ai_detection_reasons_edit.setPlainText(data.get("ai_detection_reasons_summary", ""))
                self.meta_ai_loras_edit.setPlainText(data.get("ai_loras_summary", ""))
                self.meta_ai_model_edit.setText(data.get("ai_model_summary", ""))
                self.meta_ai_checkpoint_edit.setText(data.get("ai_checkpoint_summary", ""))
                self.meta_ai_sampler_edit.setText(data.get("ai_sampler_summary", ""))
                self.meta_ai_scheduler_edit.setText(data.get("ai_scheduler_summary", ""))
                self.meta_ai_cfg_edit.setText(data.get("ai_cfg_summary", ""))
                self.meta_ai_steps_edit.setText(data.get("ai_steps_summary", ""))
                self.meta_ai_seed_edit.setText(data.get("ai_seed_summary", ""))
                self.meta_ai_upscaler_edit.setText(data.get("ai_upscaler_summary", ""))
                self.meta_ai_denoise_edit.setText(data.get("ai_denoise_summary", ""))
                self.meta_ai_workflows_edit.setPlainText(data.get("ai_workflows_summary", ""))
                self.meta_ai_provenance_edit.setPlainText(data.get("ai_provenance_summary", ""))
                self.meta_ai_character_cards_edit.setPlainText(data.get("ai_character_cards_summary", ""))
                self.meta_ai_raw_paths_edit.setPlainText(data.get("ai_raw_paths_summary", ""))
                self.meta_embedded_metadata_edit.setPlainText(data.get("embedded_metadata_summary", ""))
                
                self.meta_tags.setText(", ".join(data.get("tags", [])))
                exif_date_taken = self._format_editable_datetime(data.get("exif_date_taken"))
                if exif_date_taken:
                    self.meta_exif_date_taken_edit.setText(exif_date_taken)
                metadata_date = self._format_editable_datetime(data.get("metadata_date"))
                if metadata_date:
                    self.meta_metadata_date_edit.setText(metadata_date)
                original_file_date = self._format_sidebar_datetime(data.get("original_file_date"))
                if original_file_date:
                    self.meta_original_file_date_lbl.setText(f"Original File Date: {original_file_date}")
                file_created_date = self._format_sidebar_datetime(data.get("file_created_time"))
                if file_created_date:
                    self.meta_file_created_date_lbl.setText(f"Windows ctime: {file_created_date}")
                file_modified_date = self._format_sidebar_datetime(data.get("modified_time"))
                if file_modified_date:
                    self.meta_file_modified_date_lbl.setText(f"Date Modified: {file_modified_date}")
                
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
                    self.meta_original_file_date_lbl.setText(f"Original File Date: {self._format_sidebar_datetime(min(created_iso, modified_iso))}")
                    self.meta_file_created_date_lbl.setText(f"Windows ctime: {self._format_sidebar_datetime(created_iso)}")
                    self.meta_file_modified_date_lbl.setText(f"Date Modified: {self._format_sidebar_datetime(modified_iso)}")
                except Exception:
                    pass
                self.meta_fps_lbl.setText("FPS: ")
                self.meta_codec_lbl.setText("Codec: ")
                self.meta_audio_lbl.setText("Audio: ")
                self._load_video_sidebar_metadata_async(path)
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
            self._update_sidebar_action_buttons()
        else:
            # Bulk mode
            self.meta_tags.setText("")
            self._configure_bulk_tag_editor(len(paths))

        self.meta_filename_edit.blockSignals(False)
        self.meta_desc.blockSignals(False)
        self.meta_tags.blockSignals(False)
        self.meta_notes.blockSignals(False)
        self.meta_exif_date_taken_edit.blockSignals(False)
        self.meta_metadata_date_edit.blockSignals(False)

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
        image_general = ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "description", "tags", "notes", "embeddedtags", "embeddedcomments", "embeddedmetadata"]
        image_camera = ["camera", "location", "iso", "shutter", "aperture", "software", "lens", "dpi"]
        image_ai = [
            "aistatus", "aisource", "aifamilies", "aidetectionreasons", "ailoras", "aimodel", "aicheckpoint",
            "aisampler", "aischeduler", "aicfg", "aisteps", "aiseed", "aiupscaler", "aidenoise",
            "aiprompt", "ainegprompt", "aiparams", "aiworkflows", "aiprovenance", "aicharcards", "airawpaths",
        ]
        if kind == "video":
            return {
                "general": ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "duration", "fps", "codec", "audio", "description", "tags", "notes", "embeddedmetadata"],
                "ai": image_ai,
            }
        if kind == "gif":
            return {
                "general": ["res", "size", "exifdatetaken", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "duration", "fps", "description", "tags", "notes", "embeddedtags", "embeddedcomments", "embeddedmetadata"],
                "ai": image_ai,
            }
        if kind == "svg":
            return {
                "general": ["res", "size", "metadatadate", "originalfiledate", "filecreateddate", "filemodifieddate", "description", "tags", "notes", "embeddedmetadata"],
            }
        return {"general": image_general, "camera": image_camera, "ai": image_ai}

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
            "originalfiledate": [self.meta_original_file_date_lbl],
            "filecreateddate": [self.meta_file_created_date_lbl],
            "filemodifieddate": [self.meta_file_modified_date_lbl],
            "duration": [self.meta_duration_lbl],
            "fps": [self.meta_fps_lbl],
            "codec": [self.meta_codec_lbl],
            "audio": [self.meta_audio_lbl],
            "description": [self.lbl_desc_cap, self.meta_desc],
            "tags": [self.lbl_tags_cap, self.meta_tags],
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
        self.meta_original_file_date_lbl.setText("Original File Date: ")
        self.meta_file_created_date_lbl.setText("Windows ctime: ")
        self.meta_file_modified_date_lbl.setText("Date Modified: ")
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
        self.meta_original_file_date_lbl.setVisible("originalfiledate" in active_fields and self._is_metadata_enabled_for_kind(kind, "originalfiledate", False))
        self.meta_file_created_date_lbl.setVisible("filecreateddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filecreateddate", False))
        self.meta_file_modified_date_lbl.setVisible("filemodifieddate" in active_fields and self._is_metadata_enabled_for_kind(kind, "filemodifieddate", False))
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
        
        
        self.meta_desc.setVisible("description" in active_fields and self._is_metadata_enabled_for_kind(kind, "description", True))
        self.lbl_desc_cap.setVisible("description" in active_fields and self._is_metadata_enabled_for_kind(kind, "description", True))
        self.meta_tags.setVisible("tags" in active_fields and self._is_metadata_enabled_for_kind(kind, "tags", True))
        self.lbl_tags_cap.setVisible("tags" in active_fields and self._is_metadata_enabled_for_kind(kind, "tags", True))
        self.meta_notes.setVisible("notes" in active_fields and self._is_metadata_enabled_for_kind(kind, "notes", True))
        self.lbl_notes_cap.setVisible("notes" in active_fields and self._is_metadata_enabled_for_kind(kind, "notes", True))
        
        self.meta_desc.setPlainText("")
        self.meta_notes.setPlainText("")
        self.meta_tags.setText("")
        self.meta_status_lbl.setText("")
        self._set_metadata_empty_state(True)

    def _on_splitter_moved(self) -> None:
        """Save splitter state and re-apply card selection if the resize caused a deselect."""
        self._save_splitter_state()
        self._update_sidebar_action_buttons()
        self._update_sidebar_input_widths()
        self._update_preview_display()
        # Re-apply card selection via JS so resize doesn't visually deselect the last item
        if hasattr(self, "_current_path") and self._current_path:
            escaped = self._current_path.replace("\\", "\\\\").replace('"', '\\"')
            self.web.page().runJavaScript(
                f'(function(){{'  
                f'  var c = document.querySelector(\'.card[data-path="{escaped}"]\');'  
                f'  if (c) {{ document.querySelectorAll(\'.card.selected\').forEach(function(x){{x.classList.remove(\'selected\')}});'  
                f'    c.classList.add(\'selected\'); }}'
                f'}})();'
            )

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

        act_rename = menu.addAction("Rename…")
        
        menu.addSeparator()
        act_new_folder = menu.addAction("New Folder…")
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
            next_name, ok = QInputDialog.getText(self, "Rename folder", "New name:", text=cur)
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
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            new_path = self.bridge.create_folder(parent_path, name)
            if new_path:
                 # QFileSystemModel auto-updates, but we might want to select it
                 pass

    def _delete_item(self, path_str: str):
        p = Path(path_str)
        
        modifiers = QApplication.keyboardModifiers()
        is_shift_down = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        
        use_recycle = not is_shift_down and bool(self.bridge.settings.value("gallery/use_recycle_bin", True, type=bool))
        
        if use_recycle:
            self.bridge.delete_path(path_str)
        else:
            if p.is_dir():
                reply = QMessageBox.question(
                    self, "Confirm Permanent Delete",
                    f"Are you sure you want to permanently delete the folder and all its contents?\n\n{p.name}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            else:
                reply = QMessageBox.question(
                    self, "Confirm Permanent Delete",
                    f"Are you sure you want to permanently delete this file?\n\n{p.name}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
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
        icon = "+" if is_copy else "→"
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
        
        # Right Panel (Metadata) - Mirroring Left Panel Background precisely
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

        self.scroll_container.setStyleSheet(f"""
            QWidget#rightPanelScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
            QLabel {{
                color: {text};
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QLabel#previewHeaderLabel, QLabel#detailsHeaderLabel {{ font-weight: bold; }}
            QLabel#metaGroupLabel {{ font-weight: bold; margin-top: 12px; margin-bottom: 4px; }}
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
            QPushButton#btnClosePreview, QPushButton#btnShowPreviewInline {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {text_muted};
                font-size: 14px;
                padding: 0px;
                margin: 0px;
            }}
            
            QPushButton#btnShowPreviewInline {{
                padding: 0px;
                margin: 0px;
                color: {text};
                font-size: 14px;
                font-weight: bold;
            }}

            QPushButton#btnClosePreview:hover, QPushButton#btnShowPreviewInline:hover {{
                background-color: {Theme.get_control_bg(accent)};
                color: {text};
            }}
            
            QPushButton#btnClosePreview:hover, QPushButton#btnShowPreviewInline:hover {{
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
            QPushButton#btnSaveMeta, QPushButton#btnImportExif, QPushButton#btnMergeHiddenMeta, QPushButton#btnSaveToExif {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#btnSaveMeta:hover, QPushButton#btnImportExif:hover, QPushButton#btnMergeHiddenMeta:hover, QPushButton#btnSaveToExif:hover {{
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
        self._update_preview_play_button_icon()
        
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
        """
        QApplication.instance().setStyleSheet(menu_qss)
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
        close_btn_hover_bg = "#e4e8ee" if is_light else "#3a3a3a"
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
                font-weight: 700;
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
            if hasattr(self, "left_sections_splitter"):
                self.bridge.settings.setValue("ui/left_sections_splitter_state_v2", self.left_sections_splitter.saveState())
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self._save_splitter_state()
        super().closeEvent(event)

    def open_settings(self) -> None:
        try:
            if self._settings_dialog is None:
                self._settings_dialog = SettingsDialog(self)
            self._settings_dialog.open_dialog()
        except Exception:
            pass

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
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
                
                # Deselect web items, UNLESS the click was in the right metadata/tags panel
                is_right_panel = False
                if self.right_panel.isVisible():
                    rp_pos = self.right_panel.mapFromGlobal(QCursor.pos())
                    is_right_panel = self.right_panel.rect().contains(rp_pos)

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
        self._update_sidebar_action_buttons()
        self._update_sidebar_input_widths()
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

    def about(self) -> None:
        st = self.bridge.get_tools_status()
        ff = "✓" if st.get("ffmpeg") else "×"
        fp = "✓" if st.get("ffprobe") else "×"
        
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
            release_notes = self._read_markdown_file("ReleaseNotes.md")
            changelog = self._read_markdown_file("CHANGELOG.md")
            if release_notes is None and changelog is None:
                QMessageBox.warning(self, "What's New", "Files not found: ReleaseNotes.md, CHANGELOG.md")
                return

            parts: list[str] = []
            if release_notes:
                parts.append(release_notes.strip())
            if changelog:
                if parts:
                    parts.append("---")
                parts.append(changelog.strip())
            self._show_themed_dialog("What's New", "\n\n".join(parts), is_markdown=True)
        except Exception as e:
            QMessageBox.critical(self, "What's New", f"Error loading release notes: {e}")

    def show_search_syntax_help(self) -> None:
        self._show_markdown_dialog("Search Syntax Help", "SEARCH_SYNTAX.md")

    def open_crash_report_folder(self) -> None:
        folder = _appdata_runtime_dir() / "crash-reports"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
        except Exception:
            QMessageBox.information(self, "Crash Reports", f"Crash reports folder:\n{folder}")

    def create_diagnostic_report(self) -> None:
        report = _write_crash_report("diagnostic")
        if report is None:
            QMessageBox.warning(self, "Diagnostic Report", "Unable to create diagnostic report.")
            return
        try:
            lines: list[str] = []
            if getattr(self.bridge, "log_path", None) and Path(self.bridge.log_path).exists():
                with open(self.bridge.log_path, "r", encoding="utf-8", errors="replace") as handle:
                    tail = handle.readlines()[-200:]
                lines.append("")
                lines.append("Recent app.log tail:")
                lines.extend(line.rstrip("\n") for line in tail)
            with open(report, "a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + ("\n" if lines else ""))
            QMessageBox.information(self, "Diagnostic Report", f"Diagnostic report created:\n{report}")
        except Exception as exc:
            QMessageBox.warning(self, "Diagnostic Report", f"Report created but log tail could not be appended:\n{report}\n\n{exc}")

    def _on_update_available(self, version: str, manual: bool) -> None:
        """Handled in web frontend (toast popup)."""
        pass

    def _on_update_error(self, message: str) -> None:
        QMessageBox.warning(self, "Update Error", message)


def _create_startup_splash(app: QApplication, startup_bg: QColor) -> QSplashScreen | None:
    try:
        splash_path = Path(__file__).with_name("web") / "MediaLens-Logo-1024.png"
        if not splash_path.exists():
            return None
        source = QPixmap(str(splash_path))
        if source.isNull():
            return None

        screen = app.primaryScreen()
        target_w = 1024
        target_h = 1024
        if screen is not None:
            available = screen.availableGeometry().size()
            max_w = max(320, min(target_w, int(available.width() * 0.8)))
            max_h = max(320, min(target_h, int(available.height() * 0.8)))
        else:
            max_w = target_w
            max_h = target_h

        scaled = source.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash_pixmap = QPixmap(scaled.size())
        splash_pixmap.fill(Qt.GlobalColor.transparent)
        splash_pixmap.setDevicePixelRatio(scaled.devicePixelRatio())
        painter = QPainter(splash_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        splash = QSplashScreen(splash_pixmap)
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        return splash
    except Exception:
        return None


def main() -> None:
    app = QApplication(sys.argv)

    # Ensure QStandardPaths.AppDataLocation resolves to a stable, app-specific dir.
    app.setOrganizationName("G1enB1and")
    app.setApplicationName("MediaLens")

    startup_settings = QSettings("G1enB1and", "MediaManagerX")
    startup_theme = str(startup_settings.value("ui/theme_mode", "dark", type=str) or "dark")
    startup_accent = str(startup_settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
    show_splash = bool(startup_settings.value("ui/show_splash_screen", True, type=bool))
    Theme.set_theme_mode(startup_theme)
    startup_bg = QColor(Theme.get_bg(QColor(startup_accent)))
    startup_fg = QColor(Theme.get_text_color())
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, startup_bg)
    palette.setColor(QPalette.ColorRole.Base, startup_bg)
    palette.setColor(QPalette.ColorRole.Button, startup_bg)
    palette.setColor(QPalette.ColorRole.WindowText, startup_fg)
    palette.setColor(QPalette.ColorRole.Text, startup_fg)
    app.setPalette(palette)
    app.setStyleSheet(
        f"QWidget {{ background-color: {startup_bg.name()}; color: {startup_fg.name()}; }}"
    )

    splash = _create_startup_splash(app, startup_bg) if show_splash else None
    if splash is not None:
        splash.show()
        app.processEvents()

    win = MainWindow()
    try:
        _log_dpi_state(app, win.bridge._log)
    except Exception:
        pass

    splash_closed = False

    def _finish_splash() -> None:
        nonlocal splash_closed
        if splash is None or splash_closed:
            return
        splash_closed = True
        if win.isVisible():
            splash.finish(win)
        else:
            splash.close()

    if splash is not None:
        try:
            win.web.loadFinished.connect(lambda _ok: _finish_splash())
        except Exception:
            pass
        QTimer.singleShot(4000, _finish_splash)

    win.show()

    if splash is None:
        pass
    elif win.web is None:
        _finish_splash()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

