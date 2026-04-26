from __future__ import annotations
# Source of Truth: \VERSION
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION"), "r") as f:
        __version__ = f.read().strip()
except Exception:
    __version__ = "v1.2.1"


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
import zipfile
import base64
import urllib.error
import urllib.request
import uuid
import tempfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from math import gcd
from packaging.version import Version
from pathlib import Path

APP_NAME = "MediaLens"
LEGACY_APP_NAME = "MediaManagerX"
LEGACY_APP_ORGANIZATION = "G1enB1and"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/G1enB1and/MediaLens/main/VERSION"
UPDATE_RELEASE_API_URL = "https://api.github.com/repos/G1enB1and/MediaLens/releases/latest"
UPDATE_INSTALLER_URL = "https://github.com/G1enB1and/MediaLens/releases/latest/download/MediaLens_Setup.exe"
LOCAL_AI_PYTHON_VERSION = "3.12.10"
LOCAL_AI_PYTHON_PACKAGE_NAME = f"python.{LOCAL_AI_PYTHON_VERSION}.nupkg"
LOCAL_AI_PYTHON_PACKAGE_URL = f"https://api.nuget.org/v3-flatcontainer/python/{LOCAL_AI_PYTHON_VERSION}/{LOCAL_AI_PYTHON_PACKAGE_NAME}"
LOCAL_AI_PYTHON_PACKAGE_SHA512 = "u9pNz2iKlCEbYtUJaKkbOPMF0LjR7NkCafdKhvigpPzrt8oWKgdTpHaR6z3wyWQAm9PYGUxv0Zr66NX9AeHMDw=="
LOCAL_AI_TORCH_INDEX_URL_CU124 = "https://download.pytorch.org/whl/cu124"
LOCAL_AI_TORCH_VERSION_CU124 = "2.6.0+cu124"
LOCAL_AI_TORCHVISION_VERSION_CU124 = "0.21.0+cu124"
LOCAL_AI_ORT_GPU_VERSION = "1.20.1"
LOCAL_AI_STATUS_CACHE_TTL_SECONDS = 20.0


def _append_env_flag(name: str, flag: str) -> None:
    current = str(os.environ.get(name, "") or "").strip()
    parts = [part for part in current.split() if part]
    if flag in parts:
        return
    parts.append(flag)
    os.environ[name] = " ".join(parts)


def _configure_windows_webengine_runtime() -> dict[str, object]:
    runtime = {
        "enabled": False,
        "reason": "",
        "qt_opengl": str(os.environ.get("QT_OPENGL", "") or ""),
        "chromium_flags": str(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") or ""),
        "use_custom_page": True,
    }
    if os.name != "nt":
        return runtime

    safe_mode = str(os.environ.get("MEDIALENS_WEBENGINE_SAFE_MODE", "") or "").strip().lower()
    if safe_mode in {"0", "false", "no", "off"}:
        runtime["reason"] = "disabled-by-env"
        return runtime

    frozen_build = bool(getattr(sys, "frozen", False))
    if safe_mode not in {"1", "true", "yes", "on"} and not frozen_build:
        runtime["reason"] = "dev-default"
        return runtime

    # Some installed Windows systems keep the WebEngine surface interactive
    # but fail to paint it reliably. Prefer software paths in frozen builds,
    # while still allowing an env override for troubleshooting.
    os.environ.setdefault("QT_OPENGL", "software")
    for flag in (
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-direct-composition",
    ):
        _append_env_flag("QTWEBENGINE_CHROMIUM_FLAGS", flag)

    runtime["enabled"] = True
    runtime["reason"] = "forced-by-env" if safe_mode in {"1", "true", "yes", "on"} else "frozen-default"
    runtime["qt_opengl"] = str(os.environ.get("QT_OPENGL", "") or "")
    runtime["chromium_flags"] = str(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") or "")

    custom_page = str(os.environ.get("MEDIALENS_WEBENGINE_CUSTOM_PAGE", "") or "").strip().lower()
    if custom_page in {"1", "true", "yes", "on"}:
        runtime["use_custom_page"] = True
    elif custom_page in {"0", "false", "no", "off"} or frozen_build:
        # Replacing QWebEngineView's default page during startup has caused
        # native COM/OLE aborts on some installed Windows systems. The custom
        # page only adds console diagnostics, so keep the safer default page in
        # frozen builds unless explicitly requested for troubleshooting.
        runtime["use_custom_page"] = False
    return runtime


_WINDOWS_WEBENGINE_RUNTIME = _configure_windows_webengine_runtime()


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
    - DirectWrite legacy bitmap font probe failures for old Windows font
      aliases such as 8514oem / Fixedsys / Modern / MS Sans Serif / MS Serif.
      These are emitted during Qt font fallback probing and are harmless when
      text rendering in the UI otherwise looks normal.
    """
    _SUPPRESS = (
        b"deprecated pixel format used",
        b"Could not parse stylesheet of object QProgressBar",
        b"Could not update timestamps for skipped samples.",
        b"qt.qpa.fonts: DirectWrite: CreateFontFaceFromHDC() failed",
        b'QFontDef(Family="8514oem"',
        b'QFontDef(Family="Fixedsys"',
        b'QFontDef(Family="Modern"',
        b'QFontDef(Family="MS Sans Serif"',
        b'QFontDef(Family="MS Serif"',
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
    QEventLoop,
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
    QKeySequence,
    QMovie,
    QPainter,
    QPainterPath,
    QPalette,
    QCursor,
    QPixmap,
    QGuiApplication,
    QTextOption,
    QMouseEvent,
    QPen,
    QDragEnterEvent,
    QDragMoveEvent,
    QDragLeaveEvent,
    QDropEvent,
    QEnterEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QSplitterHandle,
    QSpacerItem,
    QWidget,
    QBoxLayout,
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
    QProgressDialog,
    QTextEdit,
    QToolTip,
    QToolButton,
    QLineEdit,
    QComboBox,
    QFrame,
    QScrollArea,
    QCheckBox,
    QGridLayout,
    QAbstractItemView,
    QStackedWidget,
    QListView,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QProxyStyle,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtSvg import QSvgRenderer
from native.mediamanagerx_app import review_groups
from native.mediamanagerx_app.video_overlay import LightboxVideoOverlay, VideoRequest
from native.mediamanagerx_app.settings_dialog import LocalAiSetupDialog, SettingsDialog
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
_THUMBNAIL_BG_HINT_CACHE: dict[tuple[str, int, int], str] = {}




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
