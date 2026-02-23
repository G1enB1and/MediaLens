from __future__ import annotations

import sys
import os
import hashlib
import subprocess
import shutil
import random
import threading
import time
import re
import json
from pathlib import Path

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
)
from PySide6.QtGui import QAction, QColor, QImageReader, QIcon, QPainter
from PySide6.QtGui import QMouseEvent, QPen
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
    QTreeView,
    QFileIconProvider,
    QFileSystemModel,
    QDialog,
    QPushButton,
    QHBoxLayout,
    QProgressBar,
    QMenu,
    QInputDialog,
    QTextEdit,
    QLineEdit,
    QFrame,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from native.mediamanagerx_app.video_overlay import LightboxVideoOverlay, VideoRequest
from PySide6.QtCore import QSortFilterProxyModel, QModelIndex


import ctypes
from ctypes import wintypes


class Theme:
    """Centralized theme system for dynamic accent tinting."""
    @staticmethod
    def mix(base_hex: str, accent_color: QColor, strength: float) -> str:
        """Mix a base hex color with an accent QColor."""
        base = QColor(base_hex)
        r = int(base.red() + (accent_color.red() - base.red()) * strength)
        g = int(base.green() + (accent_color.green() - base.green()) * strength)
        b = int(base.blue() + (accent_color.blue() - base.blue()) * strength)
        return QColor(r, g, b).name()

    # Base Palette (Used as starting point for tinting)
    BASE_BG_DARK = "#111111"
    BASE_SIDEBAR_BG_DARK = "#191919"
    BASE_BORDER_DARK = "#2d2d2d"

    BASE_BG_LIGHT = "#f5f5f5"
    BASE_SIDEBAR_BG_LIGHT = "#eeeeee"
    BASE_BORDER_LIGHT = "#d5d5d5"
    
    @staticmethod
    def get_is_light() -> bool:
        settings = QSettings("G1enB1and", "MediaManagerX")
        return settings.value("ui/theme_mode", "dark") == "light"

    @staticmethod
    def get_bg(accent: QColor) -> str:
        base = Theme.BASE_BG_LIGHT if Theme.get_is_light() else Theme.BASE_BG_DARK
        return Theme.mix(base, accent, 0.04)

    @staticmethod
    def get_sidebar_bg(accent: QColor) -> str:
        base = Theme.BASE_SIDEBAR_BG_LIGHT if Theme.get_is_light() else Theme.BASE_SIDEBAR_BG_DARK
        return Theme.mix(base, accent, 0.08)

    @staticmethod
    def get_border(accent: QColor) -> str:
        base = Theme.BASE_BORDER_LIGHT if Theme.get_is_light() else Theme.BASE_BORDER_DARK
        return Theme.mix(base, accent, 0.15)

    @staticmethod
    def get_scrollbar_track(accent: QColor) -> str:
        base = Theme.BASE_SIDEBAR_BG_LIGHT if Theme.get_is_light() else Theme.BASE_SIDEBAR_BG_DARK
        return Theme.mix(base, accent, 0.05)

    @staticmethod
    def get_scrollbar_thumb(accent: QColor) -> str:
        base = "#e0e0e0" if Theme.get_is_light() else "#333333"
        return Theme.mix(base, accent, 0.20)

    @staticmethod
    def get_scrollbar_thumb_hover(accent: QColor) -> str:
        base = "#d0d0d0" if Theme.get_is_light() else "#444444"
        return Theme.mix(base, accent, 0.30)

    @staticmethod
    def get_splitter_idle(accent: QColor) -> str:
        base = "#cccccc" if Theme.get_is_light() else "#444444"
        return Theme.mix(base, accent, 0.12)

    # UI constants
    @staticmethod
    def get_text_color() -> str:
        return "#202124" if Theme.get_is_light() else "#ccc"

    @staticmethod
    def get_text_muted() -> str:
        return "#5f6368" if Theme.get_is_light() else "#bbb"

    @staticmethod
    def get_btn_save_bg(accent: QColor) -> str:
        """Matched to .tb-page:hover (faint tinted ghost style)"""
        sb_bg = Theme.get_sidebar_bg(accent)
        # Use a slightly stronger tint than sidebar bg (8%)
        return Theme.mix(sb_bg, accent, 0.12)

    @staticmethod
    def get_btn_save_hover(accent: QColor) -> str:
        """Matched to active pagination page (accent-themed)"""
        if Theme.get_is_light():
            # Match CSS: color-mix(in srgb, var(--accent), white 60%)
            return Theme.mix("#ffffff", accent, 0.40)
        else:
            # Match CSS: var(--accent) but slightly muted/balanced if 'pure' is unreadable
            return Theme.mix(Theme.get_sidebar_bg(accent), accent, 0.85)

    ACCENT_DEFAULT = "#8ab4f8"


class CustomSplitterHandle(QSplitterHandle):
    """Custom handle that paints itself to ensure hover colors work on all platforms."""
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._hovered = False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            accent_str = getattr(self.window(), "_current_accent", Theme.ACCENT_DEFAULT)
        except Exception:
            accent_str = Theme.ACCENT_DEFAULT
        accent_q = QColor(accent_str)
        
        if self._hovered:
            color = accent_q
        else:
            color = QColor(Theme.get_splitter_idle(accent_q))
            
        painter.fillRect(self.rect(), color)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovered = False
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
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            # Let the customContextMenuRequested signal fire, but avoid changing
            # currentIndex/selection.
            event.accept()
            self.customContextMenuRequested.emit(event.position().toPoint())
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)


class RootFilterProxyModel(QSortFilterProxyModel):
    """Filters a QFileSystemModel to only show a specific root folder and its children.
    
    Siblings of the root folder are hidden.
    """
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root_path: str = ""
        self._fallback_icon: QIcon | None = None

    def setRootPath(self, path: str) -> None:
        # We NO LONGER use .resolve() here. QFileSystemModel reports the "apparent"
        # path within the tree. If we resolve, symlinks pointing outside the
        # root will be filtered out.
        self._root_path = str(Path(path).absolute())
        self.invalidate()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if not isinstance(source_model, QFileSystemModel):
            return True
            
        # Get the path of the item being checked
        idx = source_model.index(source_row, 0, source_parent)
        path_str = source_model.filePath(idx)
        if not path_str:
            return True # Allow it to load
            
        try:
            # Normalize for robust comparison (lowercase posix)
            p_str = Path(path_str).as_posix().lower()
            r_str = Path(self._root_path).as_posix().lower()
            
            # Case 1: Root itself
            if p_str == r_str:
                return True
                
            # Case 2: p is an ancestor of r (so we can drill down)
            # We use a trailing slash to avoid matching partial folder names (e.g. /my vs /media)
            # but we handle the drive root case where as_posix() already includes the slash.
            p_prefix = p_str if p_str.endswith("/") else p_str + "/"
            if r_str.startswith(p_prefix):
                return True
                
            # Case 3: p is a descendant of r
            r_prefix = r_str if r_str.endswith("/") else r_str + "/"
            if p_str.startswith(r_prefix):
                return True
                
            return False
        except Exception:
            return True

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        # Prevent "customized" folder icons (which sometimes fail to load or are empty)
        # by forcing the standard folder icon for all directories.
        if role == Qt.ItemDataRole.DecorationRole:
            source_idx = self.mapToSource(index)
            source_model = self.sourceModel()
            if isinstance(source_model, QFileSystemModel) and source_model.isDir(source_idx):
                if not self._fallback_icon:
                    provider = QFileIconProvider()
                    self._fallback_icon = provider.icon(QFileIconProvider.IconType.Folder)
                return self._fallback_icon
                
        return super().data(index, role)


class Bridge(QObject):
    selectedFolderChanged = Signal(str)
    openVideoRequested = Signal(str, bool, bool, bool, int, int)  # path, autoplay, loop, muted, w, h
    videoPreprocessingStatus = Signal(str)  # status message (empty = done)
    closeVideoRequested = Signal()

    uiFlagChanged = Signal(str, bool)  # key, value
    metadataRequested = Signal(list)
    loadFolderRequested = Signal(str)

    accentColorChanged = Signal(str)
    # Async file ops (so WebEngine UI doesn't freeze during rename)
    fileOpFinished = Signal(str, bool, str, str)  # op, ok, old_path, new_path

    # Media scanning signals
    scanStarted = Signal(str)
    scanFinished = Signal(str, int)  # folder, count
    selectionChanged = Signal(list)  # list of folder paths
    scanProgress = Signal(str, int)  # file_path, percentage

    def __init__(self) -> None:
        super().__init__()
        print("Bridge: Initializing...")
        self._selected_folders: list[str] = []
        self._scan_abort = False
        self._scan_lock = threading.Lock()
        
        appdata = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        self._thumb_dir = appdata / "thumbs"
        self._thumb_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Database
        from app.mediamanager.db.connect import connect_db
        self.db_path = appdata / "mediamanagerx.db"
        print(f"DEBUG: DB Path = {self.db_path}")
        self.conn = connect_db(str(self.db_path))

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

            if "embedded_ai_prompt" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_ai_prompt TEXT")
            if "embedded_ai_params" not in cols:
                cursor.execute("ALTER TABLE media_metadata ADD COLUMN embedded_ai_params TEXT")
            self.conn.commit()
        except Exception as e:
            print(f"Migration Error: {e}")

        self.settings = QSettings("G1enB1and", "MediaManagerX")
        self._session_shuffle_seed = random.getrandbits(32)
        
        # Hybrid Fast-Load Cache
        self._disk_cache: dict[str, Path] = {}
        self._disk_cache_key: str = "" # Hash of selected folders list

        print(f"Bridge: Initialized (Session Seed: {self._session_shuffle_seed})")

    @Slot(str)
    def debug_log(self, msg: str) -> None:
        """Helper to print logs from the JavaScript side to the terminal."""
        print(f"JS Debug: {msg}")

    def _thumb_key(self, path: Path) -> str:
        # Stable across runs; normalize separators + lowercase for Windows.
        s = str(path).replace("\\", "/").lower().encode("utf-8")
        return hashlib.sha1(s).hexdigest()

    def _video_poster_path(self, video_path: Path) -> Path:
        return self._thumb_dir / f"{self._thumb_key(video_path)}.jpg"

    def _ffmpeg_bin(self) -> str | None:
        return shutil.which("ffmpeg")

    def _ffprobe_bin(self) -> str | None:
        return shutil.which("ffprobe")

    def _ensure_video_poster(self, video_path: Path) -> Path | None:
        """Generate a poster jpg for a video using ffmpeg (if missing)."""

        out = self._video_poster_path(video_path)
        if out.exists():
            return out

        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            return None

        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            # Grab a representative frame; avoid black frame at t=0.
            # NOTE: avoid shell-style quoting in -vf; Windows builds can treat
            # quotes literally. Also escape the comma inside min().
            vf = "thumbnail,scale=min(640\\,iw):-2"

            cmd = [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "0.5",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                vf,
                "-q:v",
                "4",
                str(out),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                return None
            return out if out.exists() else None

        except Exception:
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
                # RIFF....WEBPVP8X
                if header[0:4] == b"RIFF" and header[8:12] == b"WEBP" and header[12:16] == b"VP8X":
                    flags = header[20]
                    return bool(flags & 2)  # Bit 1 is Animation
            except Exception:
                pass
        return False

    def set_selected_folders(self, folders: list[str]) -> None:
        if folders == self._selected_folders:
            return
        self._selected_folders = folders
        try:
            # Save the primary selection for restoration on next launch
            primary = folders[0] if folders else ""
            self.settings.setValue("gallery/last_folder", primary)
        except Exception:
            pass
        # Database handles persistence; next scan will pick up any changes.
        self.selectionChanged.emit(self._selected_folders)

    @Slot(result=list)
    def get_selected_folders(self) -> list:
        return self._selected_folders

    def _randomize_enabled(self) -> bool:
        try:
            return bool(self.settings.value("gallery/randomize", False, type=bool))
        except Exception:
            return False

    def _restore_last_enabled(self) -> bool:
        try:
            return bool(self.settings.value("gallery/restore_last", False, type=bool))
        except Exception:
            return False

    def _hide_dot_enabled(self) -> bool:
        try:
            return bool(self.settings.value("gallery/hide_dot", True, type=bool))
        except Exception:
            return True

    def _start_folder_setting(self) -> str:
        try:
            return str(self.settings.value("gallery/start_folder", "", type=str) or "")
        except Exception:
            return ""

    def _last_folder(self) -> str:
        try:
            return str(self.settings.value("gallery/last_folder", "", type=str) or "")
        except Exception:
            return ""

    def _scan_media_paths(self, folders: list[str]) -> list[dict]:
        """Query the database for media items under the specified folders.
        
        This replaces the old in-memory scan/cache. Results are now pulled
        directly from the persistent database based on the current folders list.
        """
        from app.mediamanager.db.media_repo import list_media_in_scope
        
        # list_media_in_scope handles recursion and normalization.
        return list_media_in_scope(self.conn, folders)

    def _do_full_scan(self, paths: list[Path], conn: sqlite3.Connection) -> int:
        from app.mediamanager.db.media_repo import upsert_media_item, get_media_by_path
        from app.mediamanager.utils.hashing import calculate_file_hash
        from datetime import datetime, timezone

        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        total_items = len(paths)

        # ── Actual Scan with Smart Hashing ────────────────────────────────────
        count = 0
        skips = 0
        for i, p in enumerate(paths):
            if self._scan_abort:
                break
            
            # Update progress
            percent = int((i / total_items) * 100) if total_items > 0 else 100
            self.scanProgress.emit(p.name, percent)

            try:
                stat = p.stat()
                media_type = "image" if p.suffix.lower() in image_exts else "video"
                
                # Smart Check: Can we skip hashing?
                skip_hash = False
                existing = get_media_by_path(conn, str(p))
                if existing:
                    db_mtime = existing.get("modified_time")
                    curr_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
                    if existing["file_size"] == stat.st_size and db_mtime == curr_mtime:
                        skip_hash = True
                
                if skip_hash:
                    skips += 1
                else:
                    h = calculate_file_hash(p)
                    upsert_media_item(conn, str(p), media_type, h)
                
                count += 1
            except Exception as e:
                print(f"Bridge Scan Error: {e} for {p}")

        return count

    @Slot(list, str)
    def start_scan(self, folders: list, search_query: str = "") -> None:
        """Asynchronously scan folders for media items."""
        self._scan_abort = True  # Signal previous thread to stop
        
        # Use existing disk cache if available to avoid redundant walk
        disk_paths = list(self._disk_cache.values())
        
        def _work():
            time.sleep(0.1)
            self._scan_abort = False
            primary = folders[0] if folders else ""
            self.scanStarted.emit(primary)
            
            from app.mediamanager.db.connect import connect_db
            scan_conn = connect_db(str(self.db_path))
            try:
                # If we don't have disk_paths yet (unlikely if called via flow), 
                # we'd need to walk. But refreshFromBridge ensures we have them.
                paths_to_scan = disk_paths
                if not paths_to_scan:
                    # Emergency fallback: pop cache manually or skip
                    pass

                self._do_full_scan(paths_to_scan, scan_conn)
                
                # Use the same reconciliation logic as list_media to get the final count
                candidates = self._get_reconciled_candidates(folders, "all", search_query)
                self.scanFinished.emit(primary, len(candidates))
            finally:
                scan_conn.close()

        threading.Thread(target=_work, daemon=True).start()

    @Slot(list, result=int)
    def count_media(self, folders: list) -> int:
        """Return total number of discoverable media items under folders."""
        try:
            return len(self._scan_media_paths(folders))
        except Exception:
            return 0

    @Slot(str, result=str)
    def get_video_poster(self, video_path: str) -> str:
        """Return a file:// URL for a cached/generated poster image for a video."""

        try:
            p = Path(video_path)
            out = self._ensure_video_poster(p)
            if not out:
                return ""
            return QUrl.fromLocalFile(str(out)).toString()
        except Exception:
            return ""

    @Slot(str, result=dict)
    def debug_video_poster(self, video_path: str) -> dict:
        """Attempt poster generation and return debug info for troubleshooting."""

        p = Path(video_path)
        out = self._video_poster_path(p)
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            return {"ok": False, "error": "ffmpeg not found", "out": str(out)}

        vf = "thumbnail,scale=min(640\\,iw):-2"
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0.5",
            "-i",
            str(p),
            "-frames:v",
            "1",
            "-vf",
            vf,
            "-q:v",
            "4",
            str(out),
        ]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "ok": bool(out.exists()) and r.returncode == 0,
                "returncode": r.returncode,
                "stderr": (r.stderr or "").strip()[:2000],
                "stdout": (r.stdout or "").strip()[:2000],
                "cmd": cmd,
                "out": str(out),
            }
        except Exception as e:
            return {"ok": False, "error": repr(e), "cmd": cmd, "out": str(out)}

    @Slot(result=dict)
    def get_tools_status(self) -> dict:
        return {
            "ffmpeg": bool(self._ffmpeg_bin()),
            "ffmpeg_path": self._ffmpeg_bin() or "",
            "ffprobe": bool(self._ffprobe_bin()),
            "ffprobe_path": self._ffprobe_bin() or "",
            "thumb_dir": str(self._thumb_dir),
        }

    @Slot(result=dict)
    def get_settings(self) -> dict:
        try:
            return {
                "gallery.randomize": self._randomize_enabled(),
                "gallery.restore_last": self._restore_last_enabled(),
                "gallery.hide_dot": self._hide_dot_enabled(),
                "gallery.start_folder": self._start_folder_setting(),
                "ui.accent_color": str(self.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8"),
                "ui.show_left_panel": bool(self.settings.value("ui/show_left_panel", True, type=bool)),
                "ui.show_right_panel": bool(self.settings.value("ui/show_right_panel", True, type=bool)),
                "ui.theme_mode": str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"),
                "ui.enable_glassmorphism": bool(self.settings.value("ui/enable_glassmorphism", True, type=bool)),
                "metadata.display.res": bool(self.settings.value("metadata/display/res", True, type=bool)),
                "metadata.display.size": bool(self.settings.value("metadata/display/size", True, type=bool)),
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
                "metadata.display.aiprompt": bool(self.settings.value("metadata/display/aiprompt", True, type=bool)),
                "metadata.display.aiparams": bool(self.settings.value("metadata/display/aiparams", True, type=bool)),
            }
        except Exception:
            return {
                "gallery.randomize": False,
                "gallery.restore_last": False,
                "gallery.hide_dot": True,
                "gallery.start_folder": "",
                "ui.accent_color": "#8ab4f8",
                "ui.show_left_panel": True,
                "ui.show_right_panel": True,
                "ui.theme_mode": "dark",
            }

    @Slot(str, bool, result=bool)
    def set_setting_bool(self, key: str, value: bool) -> bool:
        try:
            if key not in (
                "gallery.randomize",
                "gallery.restore_last",
                "gallery.hide_dot",
                "ui.show_left_panel",
                "ui.show_right_panel",
            ) and not key.startswith("metadata.display."):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))

            # Any setting that impacts list results/order should invalidate cache.
            if key in ("gallery.randomize", "gallery.hide_dot"):
                self._media_cache.clear()

            # UI flags should apply immediately.
            if key.startswith("ui.") or key.startswith("metadata.display."):
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))

            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            if key not in ("gallery.start_folder", "ui.accent_color", "ui.theme_mode"):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, str(value or ""))
            if key == "ui.accent_color":
                self.accentColorChanged.emit(str(value or "#8ab4f8"))
            elif key == "ui.theme_mode":
                # Emit flag change for UI consistency if needed
                self.uiFlagChanged.emit(key, value == "light")
            return True
        except Exception:
            return False

    @Slot(str)
    def load_folder_now(self, path: str) -> None:
        """Trigger immediate loading of the specified folder."""
        self.loadFolderRequested.emit(str(path))

    @Slot(result=str)
    def pick_folder(self) -> str:
        # UI-driven folder picker for the web settings modal.
        try:
            # Lazy import to avoid QtWidgets circulars.
            from PySide6.QtWidgets import QFileDialog

            folder = QFileDialog.getExistingDirectory(None, "Choose folder")
            return str(folder) if folder else ""
        except Exception:
            return ""

    def _unique_path(self, target: Path) -> Path:
        if not target.exists():
            return target

        suffix = target.suffix
        stem = target.stem
        parent = target.parent
        i = 2
        while True:
            cand = parent / f"{stem} ({i}){suffix}"
            if not cand.exists():
                return cand
            i += 1

    def _hide_by_renaming_dot(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        name = p.name
        if name.startswith("."):
            return str(p)
        target = p.with_name(f".{name}")
        target = self._unique_path(target)
        p.rename(target)
        return str(target)

    @Slot(str, result=str)
    def hide_by_renaming_dot(self, path: str) -> str:
        """(Sync) Hide by dot-rename."""
        try:
            return self._hide_by_renaming_dot(path)
        except Exception:
            return ""

    @Slot(str, result=bool)
    def hide_by_renaming_dot_async(self, path: str) -> bool:
        """Async hide to avoid freezing WebEngine UI."""

        old = str(path)

        def work() -> None:
            ok = False
            newp = ""
            try:
                newp = self._hide_by_renaming_dot(old)
                ok = bool(newp)
            except Exception:
                ok = False
            self.fileOpFinished.emit("hide", ok, old, newp)

        threading.Thread(target=work, daemon=True).start()
        return True

    def _unhide_by_renaming_dot(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        name = p.name
        if not name.startswith("."):
            return str(p)
        target = p.with_name(name[1:])
        target = self._unique_path(target)
        p.rename(target)
        return str(target)

    @Slot(str, result=str)
    def unhide_by_renaming_dot(self, path: str) -> str:
        try:
            return self._unhide_by_renaming_dot(path)
        except Exception:
            return ""

    @Slot(str, result=bool)
    def unhide_by_renaming_dot_async(self, path: str) -> bool:
        old = str(path)

        def work() -> None:
            ok = False
            newp = ""
            try:
                newp = self._unhide_by_renaming_dot(old)
                ok = bool(newp)
            except Exception:
                ok = False
            self.fileOpFinished.emit("unhide", ok, old, newp)

        threading.Thread(target=work, daemon=True).start()
        return True

    def _rename_path(self, path: str, new_name: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""
        new_name = (new_name or "").strip()
        if not new_name:
            return ""
        target = p.with_name(new_name)
        target = self._unique_path(target)
        p.rename(target)
        return str(target)

    @Slot(str, str, result=str)
    def rename_path(self, path: str, new_name: str) -> str:
        try:
            return self._rename_path(path, new_name)
        except Exception:
            return ""

    @Slot(str, str, result=bool)
    def rename_path_async(self, path: str, new_name: str) -> bool:
        old = str(path)
        newn = str(new_name)

        def work() -> None:
            ok = False
            newp = ""
            try:
                newp = self._rename_path(old, newn)
                ok = bool(newp)
                if ok:
                    # Update the DB so the renamed file keeps its metadata and stays visible after refresh
                    from app.mediamanager.db.media_repo import rename_media_path
                    try:
                        rename_media_path(self.conn, old, newp)
                    except Exception as db_err:
                        print(f"Bridge Rename DB Update Error: {db_err}")
            except Exception:
                ok = False
            self.fileOpFinished.emit("rename", ok, old, newp)

        threading.Thread(target=work, daemon=True).start()
        return True

    @Slot(str, result=str)
    def path_to_url(self, path: str) -> str:
        try:
            return QUrl.fromLocalFile(str(path)).toString()
        except Exception:
            return ""

    @Slot(list, result=bool)
    def show_metadata(self, paths: list) -> bool:
        try:
            self.metadataRequested.emit(paths)
            return True
        except Exception:
            return False

    @Slot(str)
    def open_in_explorer(self, path: str) -> None:
        """Open Windows Explorer with the specified file selected or folder opened."""
        try:
            print(f"Explorer Request: {path}")
            # Ensure path is absolute and uses Windows backslashes
            p_obj = Path(path).absolute()
            p = str(p_obj).replace("/", "\\")
            
            if not p_obj.exists():
                print(f"Explorer Error: Path does not exist: {p}")
                return
            
            if p_obj.is_dir():
                # Use os.startfile for directories (safest way to open a folder in Explorer)
                import os
                os.startfile(p)
            else:
                # Use a string command with shell=True for the complex /select syntax.
                # Quotes are critical here.
                cmd = f'explorer.exe /select,"{p}"'
                print(f"Explorer Executing: {cmd}")
                subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Explorer Exception: {e}")
            pass

    def _build_dropfiles_w(self, abs_paths: list[str]) -> bytes:
        """Construct the Windows DROPFILES header + null-terminated UTF-16 strings."""
        # struct DROPFILES { DWORD pFiles; POINT pt; BOOL fNC; BOOL fWide; }
        # pFiles = 20 (offset to the first file)
        # pt = (0,0) (point of drop)
        # fNC = 0 (false)
        # fWide = 1 (true, UTF-16)
        import struct
        header = struct.pack("IiiII", 20, 0, 0, 0, 1)
        # Files are null-terminated, list ends with double null.
        files_data = b"".join([p.encode("utf-16-le") + b"\x00\x00" for p in abs_paths]) + b"\x00\x00"
        return header + files_data

    @Slot(list)
    def copy_to_clipboard(self, paths: list[str]) -> None:
        """Copy file paths to the system clipboard with Windows Explorer compatibility."""
        try:
            clipboard = QApplication.clipboard()
            mime = QMimeData()
            
            abs_paths = [str(Path(p).resolve()) for p in paths]
            urls = [QUrl.fromLocalFile(p) for p in abs_paths]
            mime.setUrls(urls)
            mime.setText("\n".join(abs_paths))

            # Preferred DropEffect: 5 = Copy
            mime.setData("Preferred DropEffect", b'\x05\x00\x00\x00')
            
            # FileNameW: DROPFILES structure is required for Explorer to see it as a file transfer
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            
            clipboard.setMimeData(mime)
        except Exception:
            pass

    @Slot(list)
    def cut_to_clipboard(self, paths: list[str]) -> None:
        """Cut file paths to the system clipboard (sets Preferred DropEffect)."""
        try:
            clipboard = QApplication.clipboard()
            mime = QMimeData()
            
            abs_paths = [str(Path(p).resolve()) for p in paths]
            urls = [QUrl.fromLocalFile(p) for p in abs_paths]
            mime.setUrls(urls)
            mime.setText("\n".join(abs_paths))

            # Preferred DropEffect: 2 = Move
            mime.setData("Preferred DropEffect", b'\x02\x00\x00\x00')
            
            mime.setData("FileNameW", self._build_dropfiles_w(abs_paths))
            
            clipboard.setMimeData(mime)
        except Exception:
            pass

    @Slot(result=bool)
    def has_files_in_clipboard(self) -> bool:
        """Check if there are files (URLs) in the system clipboard."""
        try:
            clipboard = QApplication.clipboard()
            return clipboard.mimeData().hasUrls()
        except Exception:
            return False

    @Slot(str, result=bool)
    def delete_path(self, path_str: str) -> bool:
        """Delete a file or folder from the filesystem."""
        try:
            p = Path(path_str)
            if not p.exists():
                return False
            
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            
            # Also remove from database
            normalized = normalize_windows_path(path_str)
            self.conn.execute("DELETE FROM media_items WHERE path = ?", (normalized,))
            self.conn.commit()
            return True
        except Exception:
            return False

    @Slot(str, str, result=str)
    def create_folder(self, parent_path: str, name: str) -> str:
        """Create a new folder inside the parent path."""
        try:
            p = Path(parent_path) / name
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        except Exception:
            return ""

    @Slot(str)
    def paste_into_folder_async(self, target_folder: str) -> None:
        """Paste files from clipboard into the target folder asynchronously."""
        target_dir = Path(target_folder)
        if not target_dir.exists() or not target_dir.is_dir():
             self.fileOpFinished.emit("paste", False, "", "")
             return

        # Must access clipboard on main thread
        try:
            clipboard = QApplication.clipboard()
            mime = clipboard.mimeData()
            if not mime.hasUrls():
                self.fileOpFinished.emit("paste", False, "", "")
                return

            is_move = False
            if mime.hasFormat("Preferred DropEffect"):
                data = mime.data("Preferred DropEffect")
                if len(data) >= 1 and data[0] == 2:
                    is_move = True

            src_paths = [Path(url.toLocalFile()) for url in mime.urls() if url.toLocalFile()]
        except Exception:
            self.fileOpFinished.emit("paste", False, "", "")
            return

        def work() -> None:
            try:
                for src in src_paths:
                    if not src.exists(): continue
                    
                    dst = target_dir / src.name
                    # Avoid overwriting
                    count = 1
                    while dst.exists():
                        dst = target_dir / f"{src.stem} ({count}){src.suffix}"
                        count += 1
                    
                    if is_move:
                        shutil.move(str(src), str(dst))
                    else:
                        if src.is_dir():
                            shutil.copytree(str(src), str(dst))
                        else:
                            shutil.copy2(str(src), str(dst))
                
                self.fileOpFinished.emit("paste", True, "", str(target_dir))
            except Exception:
                self.fileOpFinished.emit("paste", False, "", "")

        threading.Thread(target=work, daemon=True).start()

    # reshuffle_gallery removed intentionally (kept randomize-per-session without UI clutter)

    @Slot(str, result=float)
    def get_video_duration_seconds(self, video_path: str) -> float:
        """Return duration seconds using ffprobe (0 on failure)."""
        print(f"Duration Request: {video_path}")
        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe:
                print("Duration Error: ffprobe not found")
                return 0.0

            cmd = [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            s = (r.stdout or "").strip()
            dur = float(s) if s else 0.0
            print(f"Duration Success: {dur}s")
            return dur
        except Exception as e:
            print(f"Duration Error: {e}")
            return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int, bool]:
        """
        Return (display_width, display_height, is_malformed) for the first video stream.

        is_malformed is True when either display dimension is odd after SAR adjustment.
        Odd-dimensioned NV12 frames from H.264 HW-decoded sources crash Qt's swscaler
        (coded_width=0 in the bitstream causes an impossible scale conversion). Videos
        flagged here are transparently preprocessed to MJPEG/MKV before playback.
        """
        ffprobe = self._ffprobe_bin()
        if not ffprobe:
            return (0, 0, False)

        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,sample_aspect_ratio:stream_tags=rotate",
            "-of", "json",
            str(video_path)
        ]
        try:
            import json
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            data = json.loads(r.stdout)
            streams = data.get("streams", [])
            if not streams:
                return (0, 0, False)

            s = streams[0]
            w_raw = int(s.get("width", 0))
            h_raw = int(s.get("height", 0))

            w = w_raw
            h = h_raw

            # Apply SAR so the display size matches what the user sees.
            sar = s.get("sample_aspect_ratio", "1:1")
            parsed_sar = 1.0
            if sar and ":" in sar and sar != "1:1":
                try:
                    num, den = sar.split(":", 1)
                    parsed_sar = float(num) / float(den)
                except Exception:
                    pass

            w = max(2, int(w_raw * parsed_sar))
            h = max(2, h_raw)

            # Swap dimensions for rotated videos (portrait-encoded landscape, etc.).
            tags = s.get("tags", {})
            rotate = tags.get("rotate", "0")
            if rotate in ("90", "270", "-90", "-270"):
                w, h = h, w

            # Flag odd dimensions: these indicate a malformed codec header that will
            # cause the Qt/FFmpeg HW decoder to crash during format conversion.
            is_malformed = (w % 2 != 0 or h % 2 != 0)

            return (w, h, is_malformed)
        except subprocess.TimeoutExpired:
            print(f"[Bridge] Probe timeout: {video_path}")
            return (0, 0, False)
        except Exception as e:
            print(f"[Bridge] Probe error for {video_path}: {e}")
            return (0, 0, False)

    @Slot(str, bool, bool, bool, result=bool)
    def open_native_video(self, video_path: str, autoplay: bool, loop: bool, muted: bool) -> bool:
        """Open the native video overlay for the given file.

        If the video has odd display dimensions (a sign of a malformed codec header
        that crashes Qt's HW decoder), it is transparently preprocessed to an
        MJPEG/MKV copy with corrected even dimensions before playback begins.
        """
        try:
            w, h, is_malformed = self._probe_video_size(video_path)
            if is_malformed:
                # Odd dimensions signal a malformed H.264 codec header.
                # Route through async ffmpeg preprocessing before playing.
                print(f"[Bridge] Malformed video detected ({w}x{h}), preprocessing: {Path(video_path).name}")
                self.videoPreprocessingStatus.emit("Preparing video...")

                def preprocess_and_open():
                    try:
                        fixed_path = self._preprocess_to_even_dims(video_path, w, h)
                    except Exception as e:
                        print(f"[Bridge] Preprocess exception: {e}")
                        fixed_path = None

                    if fixed_path:
                        pw, ph, _ = self._probe_video_size(fixed_path)
                        self.videoPreprocessingStatus.emit("")  # Clear loading indicator
                        self.openVideoRequested.emit(
                            str(fixed_path), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph)
                        )
                    else:
                        print(f"[Bridge] Preprocess failed for {Path(video_path).name}")
                        self.videoPreprocessingStatus.emit("Error: Could not prepare video.")

                threading.Thread(target=preprocess_and_open, daemon=True).start()
            else:
                self.openVideoRequested.emit(
                    str(video_path), bool(autoplay), bool(loop), bool(muted), int(w), int(h)
                )
            return True
        except Exception as e:
            print(f"[Bridge] open_native_video error: {e}")
            return False

    def _preprocess_to_even_dims(self, video_path: str, w: int, h: int) -> str | None:
        """Use ffmpeg to create a corrected copy with even dimensions in the system temp dir.

        Outputs MJPEG in MKV so Qt software-decodes it (delivers BGRA frames, not NV12),
        completely avoiding the swscaler crash that affects H.264 HW-decoded NV12 frames.
        """
        import tempfile
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            print("Preprocess Error: ffmpeg not found")
            return None

        # Round down to nearest even dimensions (explicit safety)
        even_w = w if w % 2 == 0 else w - 1
        even_h = h if h % 2 == 0 else h - 1
        if even_w <= 0 or even_h <= 0:
            return None

        # Always output .mkv (supports MJPEG + any audio codec)
        tmp = tempfile.NamedTemporaryFile(
            prefix="mmx_fixed_", suffix=".mkv", delete=False
        )
        tmp.close()
        out_path = tmp.name

        # Use MJPEG codec:
        # - Qt decodes in software -> receives BGRA/RGB frames, NOT NV12
        # - Avoids D3D11 HW decode and the swscaler 450x797->0x797 crash
        # - scale + setsar=1 ensures clean even dimensions with no SAR adjustment
        # - format=yuv420p avoids the "deprecated pixel format yuvj420p" warning
        #   that MJPEG emits by default (yuvj420p is a deprecated full-range alias)
        vf = f"scale={even_w}:{even_h},setsar=1,format=yuv420p"
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "mjpeg", "-q:v", "3",
            "-c:a", "copy",
            out_path,
        ]
        print(f"Preprocess CMD: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode != 0 or not Path(out_path).exists():
                print(f"Preprocess ffmpeg error: {r.stderr[:500]}")
                return None
            return out_path
        except subprocess.TimeoutExpired:
            print("Preprocess Error: ffmpeg timed out")
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
        """Fetch persistent metadata and tags for a media path."""
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.metadata_repo import get_media_metadata
        from app.mediamanager.db.tags_repo import list_media_tags
        
        try:
            m = get_media_by_path(self.conn, path)
            if not m:
                return {}
            
            meta = get_media_metadata(self.conn, m["id"]) or {}
            tags = list_media_tags(self.conn, m["id"])
            
            return {
                "title": meta.get("title") or "",
                "description": meta.get("description") or "",
                "notes": meta.get("notes") or "",
                "embedded_tags": meta.get("embedded_tags") or "",
                "embedded_comments": meta.get("embedded_comments") or "",
                "embedded_ai_prompt": meta.get("embedded_ai_prompt") or "",
                "embedded_ai_params": meta.get("embedded_ai_params") or "",
                "tags": tags
            }
        except Exception as e:
            print(f"Bridge Get Metadata Error: {e}")
            return {}

    @Slot(str, str, str, str, str, str, str, str)
    def update_media_metadata(self, path: str, title: str, description: str, notes: str, 
                              embedded_tags: str = "", embedded_comments: str = "",
                              embedded_ai_prompt: str = "", embedded_ai_params: str = "") -> None:
        """Update persistent metadata for a media path."""
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.metadata_repo import upsert_media_metadata
        
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                upsert_media_metadata(self.conn, m["id"], title, description, notes, 
                                      embedded_tags, embedded_comments, 
                                      embedded_ai_prompt, embedded_ai_params)
        except Exception as e:
            print(f"Bridge Update Metadata Error: {e}")

    @Slot(str, list)
    def set_media_tags(self, path: str, tags: list) -> None:
        """Update the set of tags for a media path (replaces existing)."""
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import set_media_tags
        
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                set_media_tags(self.conn, m["id"], tags)
        except Exception as e:
            print(f"Bridge Set Tags Error: {e}")

    @Slot(str, list)
    def attach_media_tags(self, path: str, tags: list) -> None:
        """Append tags to a media path (additive)."""
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import attach_tags
        
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                attach_tags(self.conn, m["id"], tags)
        except Exception as e:
            print(f"Bridge Attach Tags Error: {e}")

    @Slot(str)
    def clear_media_tags(self, path: str) -> None:
        """Remove all tags from a media path."""
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.tags_repo import clear_all_media_tags
        
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                clear_all_media_tags(self.conn, m["id"])
        except Exception as e:
            print(f"Bridge Clear Tags Error: {e}")

    @Slot(list, int, int, str, str, str, result=list)
    def list_media(
        self,
        folders: list,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "name_asc",
        filter_type: str = "all",
        search_query: str = "",
    ) -> list[dict]:
        """Return gallery entries for the selected folders, always in sync with disk."""
        try:
            candidates = self._get_reconciled_candidates(folders, filter_type, search_query)
            
            # --- Sort ---
            image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
            
            if self._randomize_enabled() and sort_by == "name_asc":
                random.Random(self._session_shuffle_seed).shuffle(candidates)
            elif sort_by == "name_desc":
                candidates.sort(key=lambda r: r["path"].lower(), reverse=True)
            elif sort_by == "date_desc":
                candidates.sort(key=lambda r: r.get("modified_time") or "", reverse=True)
            elif sort_by == "date_asc":
                candidates.sort(key=lambda r: r.get("modified_time") or "")
            elif sort_by == "size_desc":
                candidates.sort(key=lambda r: r.get("file_size") or 0, reverse=True)
            elif sort_by == "size_asc":
                candidates.sort(key=lambda r: r.get("file_size") or 0)
            elif sort_by == "name_asc":
                candidates.sort(key=lambda r: r["path"].lower())

            # --- Paginate ---
            start = max(0, int(offset))
            end = start + max(0, int(limit))
            page = candidates[start:end]

            out: list[dict] = []
            for r in page:
                real = r.get("_real_path")
                p = real if isinstance(real, Path) else Path(r["path"])
                out.append({
                    "path": str(p),
                    "url": QUrl.fromLocalFile(str(p)).toString(),
                    "media_type": r["media_type"],
                    "is_animated": self._is_animated(p),
                })
            return out
        except Exception as e:
            print(f"Bridge list_media error: {e}")
            import traceback
            traceback.print_exc()
            return []


    @Slot(list, str, str, result=int)
    def count_media(self, folders: list, filter_type: str = "all", search_query: str = "") -> int:
        """Return total number of discoverable media items under folders, filtered."""
        try:
            candidates = self._get_reconciled_candidates(folders, filter_type, search_query)
            return len(candidates)
        except Exception as e:
            print(f"Bridge count_media error: {e}")
            return 0

    def _get_reconciled_candidates(self, folders: list, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_scope
        from app.mediamanager.utils.pathing import normalize_windows_path

        ALL_MEDIA_EXTS = {
            ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
            ".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv",
        }
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        video_exts = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}

        if not folders:
            return []

        # ── 1. Walk disk (Recursive) ──────────────────────────────────────────
        # Use session-level cache to avoid repeated walks.
        current_key = hashlib.sha1(",".join(sorted(folders)).encode()).hexdigest()
        
        if self._disk_cache and self._disk_cache_key == current_key:
            disk_files = self._disk_cache
        else:
            disk_files: dict[str, Path] = {}
            for folder in folders:
                folder_path = Path(folder)
                if not folder_path.is_dir():
                    continue
                try:
                    for root_dir, _, files in os.walk(str(folder_path), followlinks=True):
                        curr_root = Path(root_dir)
                        for f in files:
                            p = curr_root / f
                            if p.suffix.lower() in ALL_MEDIA_EXTS:
                                norm = normalize_windows_path(str(p))
                                disk_files[norm] = p
                except Exception:
                    pass
            # Update cache
            self._disk_cache = disk_files
            self._disk_cache_key = current_key

        # ── 2. Query DB candidates ────────────────────────────────────────────
        db_candidates = list_media_in_scope(self.conn, folders)

        # ── 3. Filter to only files that actually exist on disk ───────────────
        surviving: list[dict] = []
        covered_norms: set[str] = set()
        for r in db_candidates:
            norm = normalize_windows_path(r["path"])
            if norm in disk_files:
                surviving.append(r)
                covered_norms.add(norm)
            elif Path(r["path"]).exists():
                surviving.append(r)
                covered_norms.add(norm)

        # ── 4. Synthesize entries for on-disk files missing from DB ───────────
        for norm, p_obj in disk_files.items():
            if norm not in covered_norms:
                ext = p_obj.suffix.lower()
                mtype = "image" if ext in image_exts else "video"
                surviving.append({
                    "id": -1,
                    "path": norm,
                    "media_type": mtype,
                    "file_size": None,
                    "modified_time": None,
                    "_real_path": p_obj,
                })
        
        # ── 5. Filtering (Type & Search) ──────────────────────────────────────
        candidates = surviving
        
        # Type filtering
        if filter_type == "image":
            candidates = [r for r in candidates if r["path"].lower().endswith(tuple(image_exts)) and not self._is_animated(Path(r["path"]))]
        elif filter_type == "video":
            candidates = [r for r in candidates if r["path"].lower().endswith(tuple(video_exts))]
        elif filter_type == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        
        # Search filtering (multi-field match)
        if search_query:
            q = search_query.strip().lower()
            if q:
                def _matches(r):
                    # Path/Filename (always present)
                    if q in r["path"].lower(): return True
                    # Database metadata
                    if r.get("title") and q in r["title"].lower(): return True
                    if r.get("description") and q in r["description"].lower(): return True
                    if r.get("notes") and q in r["notes"].lower(): return True
                    if r.get("tags") and q in r["tags"].lower(): return True
                    return False
                
                candidates = [r for r in candidates if _matches(r)]

        return candidates


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MediaManagerX")
        self.resize(1200, 800)

        # Set window icon
        icon_path = Path(__file__).with_name("web") / "favicon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.bridge = Bridge()
        self.bridge.openVideoRequested.connect(self._open_video_overlay)
        self.bridge.closeVideoRequested.connect(self._close_video_overlay)
        self.bridge.videoPreprocessingStatus.connect(self._on_video_preprocessing_status)
        self.bridge.uiFlagChanged.connect(self._apply_ui_flag)
        self.bridge.metadataRequested.connect(self._show_metadata_for_path)
        self.bridge.loadFolderRequested.connect(self._on_load_folder_requested)
        self.bridge.accentColorChanged.connect(self._on_accent_changed)
        self._current_accent = Theme.ACCENT_DEFAULT

        self._build_menu()
        self._build_layout()
        
        # Monitor top menu interactions to dismiss web context menu
        for m in (self.menuBar().findChildren(QMenu)):
             m.aboutToShow.connect(self._dismiss_web_menus)
             
        # Global listener to dismiss web menus when any native part of the app is clicked
        QApplication.instance().installEventFilter(self)

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

        toggle_left = QAction("Toggle Left Panel", self)
        toggle_left.triggered.connect(lambda: self._toggle_panel_setting("ui/show_left_panel"))
        view_menu.addAction(toggle_left)

        toggle_right = QAction("Toggle Right Panel", self)
        toggle_right.triggered.connect(lambda: self._toggle_panel_setting("ui/show_right_panel"))
        view_menu.addAction(toggle_right)

        view_menu.addSeparator()

        devtools_action = QAction("Toggle &DevTools", self)
        devtools_action.setShortcut("F12")
        devtools_action.triggered.connect(self.toggle_devtools)
        view_menu.addAction(devtools_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

        for m in (file_menu, edit_menu, view_menu, help_menu):
            m.aboutToShow.connect(self._dismiss_web_menus)

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
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        left_layout.addWidget(QLabel("Folders"))

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
            p = Path.home() / "Pictures"
            if p.exists():
                default_root = p

        if default_root is None:
            default_root = Path.home()

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath(str(default_root))

        # Use a proxy model to show the root folder itself at the top.
        self.proxy_model = RootFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.fs_model)
        self.proxy_model.setRootPath(str(default_root))

        self.tree = FolderTreeView()
        self.tree.setModel(self.proxy_model)
        
        # Set the tree root to the PARENT of our desired root folder
        # root_parent needs to be loaded by fs_model for visibility.
        root_parent = default_root.parent
        parent_idx = self.fs_model.setRootPath(str(root_parent))
        
        proxy_parent_idx = self.proxy_model.mapFromSource(parent_idx)
        self.tree.setRootIndex(proxy_parent_idx)

        # Expand the root folder by default
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(str(default_root)))
        if root_idx.isValid():
            self.tree.expand(root_idx)
        
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

        left_layout.addWidget(self.tree, 1)

        self._set_selected_folders([str(default_root)])

        # Apply UI flags from settings
        try:
            show_left = bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool))
            self._apply_ui_flag("ui.show_left_panel", show_left)
        except Exception:
            pass

        # Center: embedded WebEngine UI scaffold
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.web = QWebEngineView()
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
        self.web_loading_label.setStyleSheet("color: rgba(255,255,255,200); font-size: 13px;")
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
            "QProgressBar{background: rgba(255,255,255,25); border-radius: 5px;}"
            f"QProgressBar::chunk{{background: {accent}; border-radius: 5px;}}"
        )
        center_layout_loading.addWidget(self.web_loading_bar, 0, Qt.AlignmentFlag.AlignHCenter)

        wl_layout.addStretch(1)
        wl_layout.addWidget(loading_center, 0, Qt.AlignmentFlag.AlignCenter)
        wl_layout.addStretch(1)

        # Right: Metadata Panel
        self.right_panel = QWidget()
        self.right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(6)

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
        right_layout.addWidget(self.meta_size_lbl)

        self.meta_res_lbl = QLabel("")
        self.meta_res_lbl.setObjectName("metaResLabel")
        right_layout.addWidget(self.meta_res_lbl)

        self.meta_camera_lbl = QLabel("")
        self.meta_camera_lbl.setObjectName("metaCameraLabel")
        right_layout.addWidget(self.meta_camera_lbl)

        self.meta_location_lbl = QLabel("")
        self.meta_location_lbl.setObjectName("metaLocationLabel")
        right_layout.addWidget(self.meta_location_lbl)

        self.meta_iso_lbl = QLabel("")
        self.meta_iso_lbl.setObjectName("metaISOLabel")
        right_layout.addWidget(self.meta_iso_lbl)

        self.meta_shutter_lbl = QLabel("")
        self.meta_shutter_lbl.setObjectName("metaShutterLabel")
        right_layout.addWidget(self.meta_shutter_lbl)

        self.meta_aperture_lbl = QLabel("")
        self.meta_aperture_lbl.setObjectName("metaApertureLabel")
        right_layout.addWidget(self.meta_aperture_lbl)

        self.meta_software_lbl = QLabel("")
        self.meta_software_lbl.setObjectName("metaSoftwareLabel")
        right_layout.addWidget(self.meta_software_lbl)

        self.meta_lens_lbl = QLabel("")
        self.meta_lens_lbl.setObjectName("metaLensLabel")
        right_layout.addWidget(self.meta_lens_lbl)

        self.meta_dpi_lbl = QLabel("")
        self.meta_dpi_lbl.setObjectName("metaDPILabel")
        right_layout.addWidget(self.meta_dpi_lbl)

        self.meta_embedded_tags_lbl = QLabel("")
        self.meta_embedded_tags_lbl.setObjectName("metaEmbeddedTagsLabel")
        self.meta_embedded_tags_lbl.setWordWrap(True)
        right_layout.addWidget(self.meta_embedded_tags_lbl)

        self.lbl_embedded_comments_cap = QLabel("Embedded-Comments:")
        self.lbl_embedded_comments_cap.setObjectName("metaEmbeddedCommentsCaption")
        right_layout.addWidget(self.lbl_embedded_comments_cap)
        self.meta_embedded_comments_lbl = QTextEdit()
        self.meta_embedded_comments_lbl.setObjectName("metaEmbeddedCommentsEdit")
        self.meta_embedded_comments_lbl.setPlaceholderText("Embedded comments...")
        self.meta_embedded_comments_lbl.setMaximumHeight(70)
        right_layout.addWidget(self.meta_embedded_comments_lbl)

        self.lbl_embedded_ai_prompt_cap = QLabel("Embedded-AI-Prompt:")
        self.lbl_embedded_ai_prompt_cap.setObjectName("metaEmbeddedAIPromptCaption")
        right_layout.addWidget(self.lbl_embedded_ai_prompt_cap)
        self.meta_embedded_ai_prompt_lbl = QTextEdit()
        self.meta_embedded_ai_prompt_lbl.setObjectName("metaEmbeddedAIPromptEdit")
        self.meta_embedded_ai_prompt_lbl.setPlaceholderText("AI prompt...")
        self.meta_embedded_ai_prompt_lbl.setMaximumHeight(70)
        right_layout.addWidget(self.meta_embedded_ai_prompt_lbl)

        self.lbl_embedded_ai_params_cap = QLabel("Embedded-AI-Params:")
        self.lbl_embedded_ai_params_cap.setObjectName("metaEmbeddedAIParamsCaption")
        right_layout.addWidget(self.lbl_embedded_ai_params_cap)
        self.meta_embedded_ai_params_lbl = QTextEdit()
        self.meta_embedded_ai_params_lbl.setObjectName("metaEmbeddedAIParamsEdit")
        self.meta_embedded_ai_params_lbl.setPlaceholderText("AI parameters...")
        self.meta_embedded_ai_params_lbl.setMaximumHeight(70)
        right_layout.addWidget(self.meta_embedded_ai_params_lbl)

        self.meta_sep = QWidget()
        self.meta_sep.setFixedHeight(1)
        self.meta_sep.setObjectName("metaSeparator")
        right_layout.addWidget(self.meta_sep)

        # --- Editable metadata ---
        self.lbl_desc_cap = QLabel("Description:")
        right_layout.addWidget(self.lbl_desc_cap)
        self.meta_desc = QTextEdit()
        self.meta_desc.setPlaceholderText("Add a description...")
        self.meta_desc.setMaximumHeight(90)
        right_layout.addWidget(self.meta_desc)

        self.lbl_tags_cap = QLabel("Tags (comma separated):")
        right_layout.addWidget(self.lbl_tags_cap)
        self.meta_tags = QLineEdit()
        self.meta_tags.setPlaceholderText("tag1, tag2...")
        self.meta_tags.editingFinished.connect(self._save_native_tags)
        right_layout.addWidget(self.meta_tags)

        self.lbl_notes_cap = QLabel("Notes:")
        right_layout.addWidget(self.lbl_notes_cap)
        self.meta_notes = QTextEdit()
        self.meta_notes.setPlaceholderText("Personal notes...")
        self.meta_notes.setMaximumHeight(90)
        right_layout.addWidget(self.meta_notes)

        right_layout.addStretch(1)

        self.btn_clear_bulk_tags = QPushButton("Clear All Tags")
        self.btn_clear_bulk_tags.setObjectName("btnClearBulkTags")
        self.btn_clear_bulk_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bulk_tags.clicked.connect(self._clear_bulk_tags)
        self.btn_clear_bulk_tags.setStyleSheet("QPushButton { color: #f28b82; }") # Subtle red
        right_layout.addWidget(self.btn_clear_bulk_tags)
        self.btn_clear_bulk_tags.setVisible(False)

        self.btn_save_meta = QPushButton("Save Changes")
        self.btn_save_meta.setObjectName("btnSaveMeta")
        self.btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_meta.clicked.connect(self._save_native_metadata)
        right_layout.addWidget(self.btn_save_meta)

        # AI/EXIF Actions
        action_layout = QHBoxLayout()
        self.btn_import_exif = QPushButton("Import Metadata")
        self.btn_import_exif.setToolTip("Append tags/comments from file to database")
        self.btn_import_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_exif.clicked.connect(self._import_exif_to_db)
        action_layout.addWidget(self.btn_import_exif)

        self.btn_save_to_exif = QPushButton("Embed Data in File")
        self.btn_save_to_exif.setToolTip("Write tags and comments from these fields into the file's embedded metadata")
        self.btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_to_exif.clicked.connect(self._save_to_exif_cmd)
        action_layout.addWidget(self.btn_save_to_exif)
        right_layout.addLayout(action_layout)

        self.meta_status_lbl = QLabel("")
        self.meta_status_lbl.setObjectName("metaStatusLabel")
        self.meta_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.meta_status_lbl)

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

        # Prevent white flash while the first HTML/CSS loads.
        try:
            self.web.page().setBackgroundColor(QColor(Theme.get_bg(accent_q)))
        except Exception:
            pass

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

        splitter.addWidget(self.left_panel)
        splitter.addWidget(center)

        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setObjectName("mainSplitter")
        splitter.setMouseTracking(True)
        splitter.setHandleWidth(7)

        # Apply persistent widths
        state = self.bridge.settings.value("ui/splitter_state")
        if state:
            splitter.restoreState(state)
        else:
            # Side panels fixed (0 stretch), Gallery expands (1 stretch)
            # Default to 200px left, 300px right sidebars if no saved state
            splitter.setSizes([200, 800])

        splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())

        self.setCentralWidget(splitter)

        # Apply initial style
        self._update_splitter_style(accent_val)

        # Apply right panel flag from settings
        try:
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            self._apply_ui_flag("ui.show_right_panel", show_right)
        except Exception:
            pass

        # Initial clear/hide based on default settings
        # Must be at the very end to ensure all UI attributes (meta_desc, etc.) are initialized.
        self._clear_metadata_panel()

    def _set_selected_folders(self, folder_paths: list[str]) -> None:
        self.bridge.set_selected_folders(folder_paths)

    def _on_load_folder_requested(self, folder_path: str) -> None:
        if not folder_path:
            return
        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            QMessageBox.warning(self, "Invalid Folder", f"The folder does not exist:\n{folder_path}")
            return
            
        # Use apparent path (Path(p).absolute()) NOT resolved path.
        path_str = str(p.absolute())
        # Update the proxy model's local filtering root
        self.proxy_model.setRootPath(path_str)
        
        # The tree needs to show the root folder, so we set the tree-root to the parent
        root_parent = p.parent
        parent_idx = self.fs_model.setRootPath(str(root_parent))
        
        self.tree.setRootIndex(self.proxy_model.mapFromSource(parent_idx))
        
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(path_str))
        self.tree.setCurrentIndex(root_idx)
        if root_idx.isValid():
            self.tree.expand(root_idx)
            
        self._set_selected_folders([path_str])

    def _on_directory_loaded(self, path: str) -> None:
        """Triggered when QFileSystemModel finishes loading a directory's contents."""
        # Refresh the proxy so newly loaded icons appear.
        self.proxy_model.invalidate()

    def _on_tree_selection(self, *_args) -> None:
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
            self._set_selected_folders(paths)

    def _apply_ui_flag(self, key: str, value: bool) -> None:
        try:
            if key == "ui.show_left_panel":
                self.left_panel.setVisible(bool(value))
            elif key == "ui.show_right_panel":
                self.right_panel.setVisible(bool(value))
            elif key == "ui.theme_mode":
                self._update_native_styles(self._current_accent)
                self._update_splitter_style(self._current_accent)
            elif key.startswith("metadata.display."):
                # Refresh current metadata display to apply visibility
                if hasattr(self, "_current_paths") and self._current_paths:
                    self._show_metadata_for_path(self._current_paths)
                else:
                    self._clear_metadata_panel()
        except Exception:
            pass

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
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

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
            
            # We don't have direct edits for these in the UI yet (they are labels),
            # but they might have been changed by 'Import Metadata'. 
            e_tags = self.meta_embedded_tags_lbl.text().replace("Embedded-Tags: ", "")
            e_notes = self.meta_embedded_comments_lbl.toPlainText()
            e_prompt = self.meta_embedded_ai_prompt_lbl.toPlainText()
            e_params = self.meta_embedded_ai_params_lbl.toPlainText()

            try:
                self.bridge.update_media_metadata(path, "", desc, notes, e_tags, e_notes, e_prompt, e_params)
                self.bridge.set_media_tags(path, tags)
            except Exception:
                pass
        else:
            # Bulk mode: Append tags to all
            if tags:
                for p in paths:
                    try:
                        self.bridge.attach_media_tags(p, tags)
                    except Exception:
                        pass

        # --- Show confirmation then auto-clear after 3s ---
        self.meta_status_lbl.setText(f"✓ {'Tags' if is_bulk else 'Changes'} saved")
        QTimer.singleShot(3000, lambda: self.meta_status_lbl.setText(""))

    def _harvest_universal_metadata(self, img) -> dict:
        """Systematically extract tags/comments from XMP, IPTC, and all EXIF IFDs."""
        from PIL import ExifTags, IptcImagePlugin
        res = {"tags": [], "comment": "", "ai_prompt": "", "ai_params": ""}

        def add_comment(val):
            if val and str(val).strip():
                c = str(val).strip()
                if not res["comment"]: res["comment"] = c
                elif c not in res["comment"]: res["comment"] = f"{res['comment']}\n{c}"

        def add_tags(val):
            if not val: return
            if isinstance(val, str):
                parts = [t.strip() for t in val.replace(";", ",").split(",") if t.strip()]
                for p in parts:
                    if p not in res["tags"]: res["tags"].append(p)
            elif isinstance(val, (list, tuple)):
                for v in val: add_tags(v)

        # 1. Standard Info & PNG Text
        if hasattr(img, "info"):
            for k, v in img.info.items():
                if k in ("parameters", "comment", "Description", "UserComment"):
                    # Check for prompt/params split (often in Automatic1111)
                    if k == "parameters" and "\nNegative prompt:" in str(v):
                        parts = v.split("\n", 1)
                        res["ai_prompt"] = parts[0].strip()
                        res["ai_params"] = parts[1].strip()
                    else:
                        add_comment(v)
                elif k in ("Subject", "Keywords"):
                    add_tags(v)
                elif k == "Civitai metadata" and isinstance(v, str):
                    try:
                        data = json.loads(v)
                        if "tags" in data: add_tags(data["tags"])
                        # Might have resources or other info
                    except: pass
                elif k == "xmp" and isinstance(v, (bytes, str)):
                    txt = v.decode(errors="replace") if isinstance(v, bytes) else v
                    subj_match = re.search(r"<dc:subject>(.*?)</dc:subject>", txt, re.DOTALL)
                    if subj_match:
                        tags = re.findall(r"<rdf:li>(.*?)</rdf:li>", subj_match.group(1))
                        add_tags(tags)
                    desc_match = re.search(r"<dc:description>(.*?)</dc:description>", txt, re.DOTALL)
                    if desc_match:
                        descs = re.findall(r"<rdf:li>(.*?)</rdf:li>", desc_match.group(1))
                        for d in descs: add_comment(d)
                    # UserComment in XMP
                    uc_match = re.search(r"<exif:UserComment>(.*?)</exif:UserComment>", txt, re.DOTALL)
                    if uc_match: add_comment(uc_match.group(1))

        # 2. IPTC
        try:
            iptc = IptcImagePlugin.getiptcinfo(img)
            if iptc:
                for k, v in iptc.items():
                    if k == (2, 120): # Caption
                        add_comment(v.decode(errors="replace") if isinstance(v, bytes) else v)
                    elif k == (2, 25): # Keywords
                        words = v if isinstance(v, list) else [v]
                        for w in words:
                            add_tags(w.decode(errors="replace") if isinstance(w, bytes) else w)
        except: pass

        # 3. EXIF (Root & Sub-IFDs)
        exif = img.getexif()
        if exif:
            def scan_ifd(ifd_obj):
                if not ifd_obj: return
                for tid, val in ifd_obj.items():
                    name = ExifTags.TAGS.get(tid, tid)
                    
                    # Robust Decoding of UserComment (Tag 37510)
                    if tid == 37510:
                        if isinstance(val, (bytes, bytearray)):
                            try:
                                # Standard suggests first 8 bytes are encoding
                                prefix = val[:8].upper()
                                raw_val = val[8:]
                                if b"UNICODE" in prefix:
                                    val = raw_val.decode("utf-16le", errors="replace").rstrip("\x00")
                                elif b"ASCII" in prefix:
                                    val = raw_val.decode("ascii", errors="replace").rstrip("\x00")
                                else:
                                    val = val.decode(errors="replace").rstrip("\x00")
                            except: pass
                        add_comment(val)
                        continue

                    # Handle Windows UTF-16 tags (XP*)
                    if tid in (0x9c9b, 0x9c9c, 0x9c9d, 0x9c9e, 0x9c9f) or str(name).startswith("XP"):
                        if isinstance(val, (bytes, bytearray)):
                            try:
                                val = val.decode("utf-16le", errors="replace").rstrip("\x00")
                            except: pass
                    
                    if tid == 0x9c9c or name in ("Comment", "XPComment", "ImageDescription", "XPTitle"):
                        add_comment(val)
                    elif tid == 0x9c9e or name in ("XPKeywords", "Subject", "XPSubject"):
                        add_tags(val)

            scan_ifd(exif)
            for ifd_id in [ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo, ExifTags.IFD.Interop]:
                try: scan_ifd(exif.get_ifd(ifd_id))
                except: pass

        return res

    @Slot()
    def _import_exif_to_db(self) -> None:
        """Import EXIF/PNG-info data and append to DB tags/notes."""
        if not self._current_path: return
        p = Path(self._current_path)
        if not p.exists(): return

        try:
            from PIL import Image
            with Image.open(str(p)) as img:
                res = self._harvest_universal_metadata(img)

            if not res["comment"] and not res["tags"] and not res["ai_prompt"]:
                self.meta_status_lbl.setText("No new metadata found in file.")
                return

            # Update UI main fields (Tags are appended, Notes/Comments show in Embedded labels)
            
            if res["tags"]:
                curr_tags = self.meta_tags.text().strip()
                all_tags = set([t.strip() for t in curr_tags.split(",") if t.strip()])
                all_tags.update(res["tags"])
                self.meta_tags.setText(", ".join(sorted(list(all_tags))))

            # AI Prompt/Params are always updated in DB but also fields
            if res["ai_prompt"]:
                self.meta_embedded_ai_prompt_lbl.setPlainText(res['ai_prompt'])
            if res["ai_params"]:
                self.meta_embedded_ai_params_lbl.setPlainText(res['ai_params'])
            
            # Sync the Comments field too (so it updates in real-time)
            if res["comment"]:
                self.meta_embedded_comments_lbl.setPlainText(res['comment'])

            # Auto-save to DB
            self.btn_save_meta.click()
            self.meta_status_lbl.setText("Metadata imported & saved to DB.")
        except Exception as e:
            self.meta_status_lbl.setText(f"Harvest Error: {e}")

    @Slot()
    def _save_to_exif_cmd(self) -> None:
        """Embed tags, comments, and AI data from the UI fields into the file's metadata."""
        if not self._current_path: return
        p = Path(self._current_path)
        if not p.exists(): return

        ext = p.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            self.meta_status_lbl.setText("Embed not supported for this file type.")
            return

        try:
            from PIL import Image, PngImagePlugin, ExifTags
            import tempfile
            import os

            # Read values from the UI fields
            comments = self.meta_embedded_comments_lbl.toPlainText().strip()
            ai_prompt = self.meta_embedded_ai_prompt_lbl.toPlainText().strip()
            ai_params = self.meta_embedded_ai_params_lbl.toPlainText().strip()
            tags_raw = self.meta_embedded_tags_lbl.text().replace("Embedded-Tags: ", "").strip()

            # Build a combined comment / parameters text
            combined_text = comments
            if ai_prompt:
                combined_text = ai_prompt
                if ai_params:
                    combined_text += f"\n{ai_params}"

            with Image.open(str(p)) as img:
                if ext == ".png":
                    pnginfo = PngImagePlugin.PngInfo()
                    # Preserve existing tEXt chunks (except ones we'll overwrite)
                    overwrite_keys = {"parameters", "comment", "Keywords", "Subject"}
                    for k, v in img.info.items():
                        if isinstance(k, str) and isinstance(v, str) and k not in overwrite_keys:
                            try: pnginfo.add_text(k, v)
                            except: pass
                    if combined_text:
                        pnginfo.add_text("parameters" if ai_prompt else "comment", combined_text)
                    if tags_raw:
                        pnginfo.add_text("Keywords", tags_raw)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "PNG", pnginfo=pnginfo)
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e

                elif ext in (".jpg", ".jpeg"):
                    exif = img.getexif()
                    # Write ImageDescription (tag 270)
                    if combined_text:
                        exif[270] = combined_text
                    # Write XPKeywords (tag 0x9C9E) as UTF-16LE bytes
                    if tags_raw:
                        exif[0x9C9E] = tags_raw.encode("utf-16le")
                    exif_bytes = exif.tobytes()

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "JPEG", exif=exif_bytes, quality="keep")
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e

                elif ext == ".webp":
                    exif = img.getexif()
                    if combined_text:
                        exif[270] = combined_text
                    exif_bytes = exif.tobytes()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webp", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "WEBP", exif=exif_bytes)
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e

            self.meta_status_lbl.setText("✓ Data embedded in file successfully.")
            QTimer.singleShot(4000, lambda: self.meta_status_lbl.setText(""))
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
        self._current_paths = paths # Store list for bulk save
        self._current_path = paths[0] if not is_bulk else None

        # Toggle UI for bulk mode
        self.lbl_fn_cap.setVisible(not is_bulk)
        self.meta_filename_edit.setVisible(not is_bulk)
        self.meta_path_lbl.setVisible(not is_bulk)
        self.meta_sep.setVisible(not is_bulk)

        show_res = self._is_metadata_enabled("res", True)
        show_size = self._is_metadata_enabled("size", True)
        show_camera = self._is_metadata_enabled("camera", False)
        show_location = self._is_metadata_enabled("location", False)
        show_iso = self._is_metadata_enabled("iso", False)
        show_shutter = self._is_metadata_enabled("shutter", False)
        show_aperture = self._is_metadata_enabled("aperture", False)
        show_software = self._is_metadata_enabled("software", False)
        show_lens = self._is_metadata_enabled("lens", False)
        show_dpi = self._is_metadata_enabled("dpi", False)
        show_embedded_tags = self._is_metadata_enabled("embeddedtags", True)
        show_embedded_comments = self._is_metadata_enabled("embeddedcomments", True)
        show_ai_prompt = self._is_metadata_enabled("aiprompt", True)
        show_ai_params = self._is_metadata_enabled("aiparams", True)

        self.meta_res_lbl.setVisible(not is_bulk and show_res)
        self.meta_size_lbl.setVisible(not is_bulk and show_size)
        self.meta_camera_lbl.setVisible(not is_bulk and show_camera)
        self.meta_location_lbl.setVisible(not is_bulk and show_location)
        self.meta_iso_lbl.setVisible(not is_bulk and show_iso)
        self.meta_shutter_lbl.setVisible(not is_bulk and show_shutter)
        self.meta_aperture_lbl.setVisible(not is_bulk and show_aperture)
        self.meta_software_lbl.setVisible(not is_bulk and show_software)
        self.meta_lens_lbl.setVisible(not is_bulk and show_lens)
        self.meta_dpi_lbl.setVisible(not is_bulk and show_dpi)
        self.meta_embedded_tags_lbl.setVisible(not is_bulk and show_embedded_tags)
        self.meta_embedded_comments_lbl.setVisible(not is_bulk and show_embedded_comments)
        self.lbl_embedded_comments_cap.setVisible(not is_bulk and show_embedded_comments)
        self.meta_embedded_ai_prompt_lbl.setVisible(not is_bulk and show_ai_prompt)
        self.lbl_embedded_ai_prompt_cap.setVisible(not is_bulk and show_ai_prompt)
        self.meta_embedded_ai_params_lbl.setVisible(not is_bulk and show_ai_params)
        self.lbl_embedded_ai_params_cap.setVisible(not is_bulk and show_ai_params)

        # Set default text prefixes so they show even if blank
        self.meta_res_lbl.setText("Resolution: ")
        self.meta_size_lbl.setText("File Size: ")
        self.meta_camera_lbl.setText("Camera: ")
        self.meta_location_lbl.setText("Location: ")
        self.meta_iso_lbl.setText("ISO: ")
        self.meta_shutter_lbl.setText("Shutter: ")
        self.meta_aperture_lbl.setText("Aperture: ")
        self.meta_software_lbl.setText("Software: ")
        self.meta_lens_lbl.setText("Lens: ")
        self.meta_dpi_lbl.setText("DPI: ")
        self.meta_embedded_tags_lbl.setText("Embedded-Tags: ")
        # Clear the three editable QTextEdits (not prefixed labels anymore)
        self.meta_embedded_comments_lbl.setPlainText("")
        self.meta_embedded_ai_prompt_lbl.setPlainText("")
        self.meta_embedded_ai_params_lbl.setPlainText("")

        self.lbl_desc_cap.setVisible(not is_bulk)
        self.meta_desc.setVisible(not is_bulk)
        self.lbl_notes_cap.setVisible(not is_bulk)
        self.meta_notes.setVisible(not is_bulk)
        
        # Tags stay visible
        self.lbl_tags_cap.setVisible(True)
        self.meta_tags.setVisible(True)
        self.btn_clear_bulk_tags.setVisible(is_bulk)
        
        self.meta_filename_edit.blockSignals(True)
        self.meta_desc.blockSignals(True)
        self.meta_tags.blockSignals(True)
        self.meta_notes.blockSignals(True)

        if not is_bulk:
            path = paths[0]
            p = Path(path)
            self.meta_filename_edit.setText(p.name)
            self.meta_path_lbl.setText(f"Folder: {p.parent}")

            # 1. Database Metadata (Load FIRST)
            try:
                data = self.bridge.get_media_metadata(path)
                self.meta_desc.setPlainText(data.get("description", ""))
                self.meta_notes.setPlainText(data.get("notes", ""))
                
                # Populate labels with DB values if non-empty
                db_tags = data.get('embedded_tags', '')
                if db_tags: self.meta_embedded_tags_lbl.setText(f"Embedded-Tags: {db_tags}")
                
                db_comm = data.get('embedded_comments', '')
                if db_comm: self.meta_embedded_comments_lbl.setPlainText(db_comm)
                
                db_prompt = data.get('embedded_ai_prompt', '')
                if db_prompt: self.meta_embedded_ai_prompt_lbl.setPlainText(db_prompt)
                
                db_params = data.get('embedded_ai_params', '')
                if db_params: self.meta_embedded_ai_params_lbl.setPlainText(db_params)
                
                self.meta_tags.setText(", ".join(data.get("tags", [])))
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

            # 3. Real-time Harvest (Update/Enrich Labels)
            ext = p.suffix.lower()
            if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
                try:
                    reader = QImageReader(str(p))
                    sz = reader.size()
                    if sz.isValid():
                        self.meta_res_lbl.setText(f"Resolution: {sz.width()} × {sz.height()} px")
                    else:
                        self.meta_res_lbl.setText("Resolution: ")
                except Exception:
                    self.meta_res_lbl.setText("Resolution: ")

                # Additional info via Pillow
                try:
                    from PIL import Image
                    with Image.open(str(p)) as img:
                        # DPI
                        if hasattr(img, "info"):
                            dpi = img.info.get("dpi")
                            if dpi:
                                self.meta_dpi_lbl.setText(f"DPI: {dpi[0]} × {dpi[1]}")

                        # Real-time Harvest for Tags/Comments labels (Automatic Refresh)
                        harvested = self._harvest_universal_metadata(img)
                        if harvested["tags"]:
                            self.meta_embedded_tags_lbl.setText(f"Embedded-Tags: {', '.join(harvested['tags'])}")
                        if harvested["comment"]:
                            self.meta_embedded_comments_lbl.setPlainText(harvested['comment'])
                        if harvested["ai_prompt"]:
                            self.meta_embedded_ai_prompt_lbl.setPlainText(harvested['ai_prompt'])
                        if harvested["ai_params"]:
                            self.meta_embedded_ai_params_lbl.setPlainText(harvested['ai_params'])
                        
                        # Technical EXIF
                        exif = img.getexif()
                        if exif:
                            from PIL import ExifTags
                            # Root IFD
                            model = exif.get(ExifTags.Base.Model)
                            if model: self.meta_camera_lbl.setText(f"Camera: {model}")
                            soft = exif.get(ExifTags.Base.Software)
                            if soft: self.meta_software_lbl.setText(f"Software: {soft}")
                            
                            # Sub-IFDs
                            try:
                                sub = exif.get_ifd(ExifTags.IFD.Exif)
                                if sub:
                                    iso = sub.get(ExifTags.Base.ISOSpeedRatings)
                                    if iso: self.meta_iso_lbl.setText(f"ISO: {iso}")
                                    
                                    shutter = sub.get(ExifTags.Base.ExposureTime)
                                    if shutter:
                                        if shutter < 1:
                                            self.meta_shutter_lbl.setText(f"Shutter: 1/{int(1/shutter)}s")
                                        else:
                                            self.meta_shutter_lbl.setText(f"Shutter: {shutter}s")
                                            
                                    aperture = sub.get(ExifTags.Base.FNumber)
                                    if aperture: self.meta_aperture_lbl.setText(f"Aperture: ƒ/{aperture}")
                                    
                                    lens = sub.get(0xA434) # LensModel
                                    if lens: self.meta_lens_lbl.setText(f"Lens: {lens}")
                            except: pass
                            
                            try:
                                gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
                                if gps:
                                    lat = gps.get(2) # Latitude
                                    lon = gps.get(4) # Longitude
                                    if lat and lon:
                                        self.meta_location_lbl.setText(f"Location: {lat}, {lon}")
                            except: pass

                except Exception as e:
                    print(f"Metadata Read Error for {p.name}: {e}")
            else:
                self.meta_res_lbl.setText("Resolution: ")
        
            self.btn_save_meta.setText("Save Changes")
        else:
            # Bulk mode
            self.meta_tags.setText("")
            self.meta_tags.setPlaceholderText("Add tags to all selected...")
            self.btn_save_meta.setText(f"Add Tags to {len(paths)} Items")

        self.meta_filename_edit.blockSignals(False)
        self.meta_desc.blockSignals(False)
        self.meta_tags.blockSignals(False)
        self.meta_notes.blockSignals(False)

    def _clear_embedded_labels(self):
        self.meta_camera_lbl.setText("Camera: ")
        self.meta_location_lbl.setText("Location: ")
        self.meta_iso_lbl.setText("ISO: ")
        self.meta_shutter_lbl.setText("Shutter: ")
        self.meta_aperture_lbl.setText("Aperture: ")
        self.meta_software_lbl.setText("Software: ")
        self.meta_lens_lbl.setText("Lens: ")
        self.meta_dpi_lbl.setText("DPI: ")
        self.meta_embedded_tags_lbl.setText("Embedded-Tags: ")
        self.meta_embedded_comments_lbl.setPlainText("")
        self.meta_embedded_ai_prompt_lbl.setPlainText("")
        self.meta_embedded_ai_params_lbl.setPlainText("")

    def _is_metadata_enabled(self, key: str, default: bool = True) -> bool:
        """Read metadata visibility setting with robust boolean conversion."""
        try:
            qkey = f"metadata/display/{key}"
            # Ensure we have the latest from disk
            self.bridge.settings.sync()
            val = self.bridge.settings.value(qkey)
            if val is None:
                return default
            # Handle PySide6/Qt behavior on different platforms
            if isinstance(val, str):
                return val.lower() in ("true", "1")
            return bool(val)
        except Exception:
            return default

    def _clear_metadata_panel(self):
        """Reset all labels and hide/show them based on current settings."""
        self._current_path = None
        self._current_paths = []
        
        self.meta_filename_edit.setText("")
        self.meta_path_lbl.setText("Folder: ")
        self.meta_size_lbl.setText("File Size: ")
        self.meta_res_lbl.setText("Resolution: ")
        self._clear_embedded_labels()
        
        # UI visibility logic
        self.meta_res_lbl.setVisible(self._is_metadata_enabled("res", True))
        self.meta_size_lbl.setVisible(self._is_metadata_enabled("size", True))
        self.meta_camera_lbl.setVisible(self._is_metadata_enabled("camera", False))
        self.meta_location_lbl.setVisible(self._is_metadata_enabled("location", False))
        self.meta_iso_lbl.setVisible(self._is_metadata_enabled("iso", False))
        self.meta_shutter_lbl.setVisible(self._is_metadata_enabled("shutter", False))
        self.meta_aperture_lbl.setVisible(self._is_metadata_enabled("aperture", False))
        self.meta_software_lbl.setVisible(self._is_metadata_enabled("software", False))
        self.meta_lens_lbl.setVisible(self._is_metadata_enabled("lens", False))
        self.meta_dpi_lbl.setVisible(self._is_metadata_enabled("dpi", False))
        self.meta_embedded_tags_lbl.setVisible(self._is_metadata_enabled("embeddedtags", True))
        self.meta_embedded_comments_lbl.setVisible(self._is_metadata_enabled("embeddedcomments", True))
        self.lbl_embedded_comments_cap.setVisible(self._is_metadata_enabled("embeddedcomments", True))
        self.meta_embedded_ai_prompt_lbl.setVisible(self._is_metadata_enabled("aiprompt", True))
        self.lbl_embedded_ai_prompt_cap.setVisible(self._is_metadata_enabled("aiprompt", True))
        self.meta_embedded_ai_params_lbl.setVisible(self._is_metadata_enabled("aiparams", True))
        self.lbl_embedded_ai_params_cap.setVisible(self._is_metadata_enabled("aiparams", True))
        
        self.meta_filename_edit.setVisible(True)
        self.meta_path_lbl.setVisible(True)
        self.meta_sep.setVisible(True)
        
        self.meta_desc.setPlainText("")
        self.meta_notes.setPlainText("")
        self.meta_tags.setText("")
        self.meta_status_lbl.setText("")

    def _on_splitter_moved(self) -> None:
        """Save splitter state and re-apply card selection if the resize caused a deselect."""
        self._save_splitter_state()
        # Re-apply card selection via JS so resize doesn't visually deselect the last item
        if hasattr(self, "_current_path") and self._current_path:
            escaped = self._current_path.replace("\\", "\\\\").replace('"', '\\"')
            self.web.page().runJavaScript(
                f'(function(){{'  
                f'  var c = document.querySelector(\'.card[data-path="{escaped}"]\')'  
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
        is_hidden = name.startswith(".")

        act_hide = None
        act_unhide = None
        if is_hidden:
            act_unhide = menu.addAction("Unhide Folder")
        else:
            act_hide = menu.addAction("Hide Folder")

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
            new_path = self.bridge.hide_by_renaming_dot(folder_path)
            if new_path:
                parent = str(Path(folder_path).parent)
                self.tree.setCurrentIndex(self.proxy_model.mapFromSource(self.fs_model.index(parent)))
                self._set_selected_folders([parent])

        if chosen == act_unhide:
            new_path = self.bridge.unhide_by_renaming_dot(folder_path)
            if new_path:
                parent = str(Path(new_path).parent)
                self.tree.setCurrentIndex(self.proxy_model.mapFromSource(self.fs_model.index(parent)))
                self._set_selected_folders([parent])

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
        if p.is_dir():
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the folder and all its contents?\n\n{p.name}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.bridge.delete_path(path_str)

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

        self.video_overlay.setGeometry(self.web.rect())
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

    def _update_splitter_style(self, accent_color: str) -> None:
        """Update QSplitter handles with light grey idle and accent color hover."""
        if not hasattr(self, "splitter"):
            return
        
        self._current_accent = accent_color
        self.splitter.setHandleWidth(5)
        
        # We no longer need stylesheets or manual loops here because 
        # CustomSplitterHandle.paintEvent handles everything natively.
        for i in range(self.splitter.count()):
            h = self.splitter.handle(i)
            if h:
                h.update()

    def _on_accent_changed(self, accent_color: str) -> None:
        """Called when the bridge emits accentColorChanged."""
        self._current_accent = accent_color
        self._update_native_styles(accent_color)
        self._update_splitter_style(accent_color)
        
        # Belt and suspenders: force update web layer via injection
        js = f"document.documentElement.style.setProperty('--accent', '{accent_color}');"
        if hasattr(self, "webview") and self.webview.page():
            self.webview.page().runJavaScript(js)

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
        """Apply tinted styles to sidebars, metadata, and global native elements."""
        accent = QColor(accent_str)
        sb_bg_str = Theme.get_sidebar_bg(accent)
        sb_bg = QColor(sb_bg_str)
        scrollbar_style = self._get_native_scrollbar_style(accent)
        text = Theme.get_text_color()
        text_muted = Theme.get_text_muted()
        is_light = Theme.get_is_light()
        
        # Windows Title Bar
        self._set_window_title_bar_theme(not is_light, sb_bg)
        
        # Theme-aware Window Icon
        icon_name = "favicon-black.png" if is_light else "favicon.png"
        icon_path = Path(__file__).with_name("web") / icon_name
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Loading Screen
        load_fg = "rgba(0,0,0,200)" if is_light else "rgba(255,255,255,200)"
        load_bg = "rgba(0,0,0,25)" if is_light else "rgba(255,255,255,25)"
        self.web_loading_label.setStyleSheet(f"color: {load_fg}; font-size: 13px;")
        self.web_loading_bar.setStyleSheet(
            f"QProgressBar{{background: {load_bg}; border-radius: 5px;}}"
            f"QProgressBar::chunk{{background: {accent_str}; border-radius: 5px;}}"
        )
        
        # Left Panel (Folders)
        self.left_panel.setStyleSheet(f"""
            QWidget {{ background-color: {sb_bg_str}; color: {text}; }}
            QTreeView {{ background-color: {sb_bg_str}; border: none; color: {text}; }}
            QLabel {{ color: {text}; font-weight: bold; background: transparent; }}
            {scrollbar_style}
        """)
        
        # Right Panel (Metadata)
        self.right_panel.setStyleSheet(f"""
            QWidget#rightPanel {{ background-color: {sb_bg_str}; color: {text}; border-left: 1px solid {Theme.get_border(accent)}; }}
            QLabel {{ color: {text}; background: transparent; }}
            QLineEdit, QTextEdit {{
                background-color: rgba(255,255,255,10);
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px;
                color: {text};
            }}
            QPushButton#btnSaveMeta {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#btnSaveMeta:hover {{
                background-color: {Theme.get_btn_save_hover(accent)};
                color: {"#000" if is_light else "#fff"};
                border-color: {accent_str};
            }}
            QWidget#metaSeparator {{
                background-color: {text};
                height: 1px;
                max-height: 1px;
                min-height: 1px;
                border: none;
                margin: 4px 0;
            }}
            {scrollbar_style}
        """)
        
        self._update_app_style(accent)

    def showEvent(self, event) -> None:
        """Trigger native style update when window actually becomes visible to ensure valid winId for DWM."""
        super().showEvent(event)
        try:
            accent = getattr(self, "_current_accent", Theme.ACCENT_DEFAULT)
            self._update_native_styles(accent)
        except Exception:
            pass

    def _update_app_style(self, accent: QColor) -> None:
        """Update global application styles like tinted native menus."""
        sb_bg = Theme.get_sidebar_bg(accent)
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        is_light = Theme.get_is_light()
        highlight_bg = "rgba(0, 0, 0, 0.05)" if is_light else "rgba(255, 255, 255, 0.05)"
        
        QApplication.instance().setStyleSheet(f"""
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
        """)

    def _get_native_scrollbar_style(self, accent: QColor) -> str:
        """Generate a QSS string for tinted native scrollbars."""
        track = Theme.get_scrollbar_track(accent)
        thumb = Theme.get_scrollbar_thumb(accent)
        hover = Theme.mix(thumb, accent, 0.1)
        
        return f"""
            QScrollBar:vertical {{
                background: {track};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {thumb};
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {track};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {thumb};
                min-width: 20px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """

    def _on_video_prev(self) -> None:
        try:
            self.web.page().runJavaScript("try{ window.lightboxPrev && window.lightboxPrev(); }catch(e){}")
        except Exception:
            pass

    def _on_video_next(self) -> None:
        try:
            self.web.page().runJavaScript("try{ window.lightboxNext && window.lightboxNext(); }catch(e){}")
        except Exception:
            pass

    def _set_web_loading(self, on: bool) -> None:
        try:
            if on:
                self._web_loading_shown_ms = int(__import__("time").time() * 1000)
                self.web_loading.setGeometry(self.web.rect())
                self.web_loading.setVisible(True)
                self.web_loading.raise_()
                if self.video_overlay.isVisible():
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
            self.web_loading_bar.setValue(int(pct))
        except Exception:
            pass

    def _toggle_panel_setting(self, qkey: str) -> None:
        try:
            cur = bool(self.bridge.settings.value(qkey, True, type=bool))
            new = not cur
            self.bridge.settings.setValue(qkey, new)
            self.bridge.uiFlagChanged.emit(qkey.replace("/", "."), new)
            # Save state after toggle to remember relative widths
            self._save_splitter_state()
        except Exception:
            pass

    def _save_splitter_state(self) -> None:
        try:
            self.bridge.settings.setValue("ui/splitter_state", self.splitter.saveState())
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self._save_splitter_state()
        super().closeEvent(event)

    def open_settings(self) -> None:
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_openSettings && window.__mmx_openSettings(); }catch(e){}"
            )
        except Exception:
            pass

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Only handle MouseButtonPress to avoid duplicate triggers on release.
        if event.type() == QEvent.Type.MouseButtonPress:
            # Use a more robust geometric check instead of recursive object parent lookup.
            # This is safer and avoids potential crashes in transient widget states.
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QWidget
            rel_pos = self.web.mapFromGlobal(QCursor.pos())
            is_web = self.web.rect().contains(rel_pos)
            
            if not is_web:
                # ONLY dismiss if the click is truly outside the web area.
                # This prevents the native filter from eating clicks destined for the context menu.
                self._dismiss_web_menus()
                self._deselect_web_items()
        return super().eventFilter(watched, event)

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
            self._devtools.setWindowTitle("MediaManagerX DevTools")
            self._devtools.resize(1100, 700)
            self.web.page().setDevToolsPage(self._devtools.page())
            self._devtools.show()
        else:
            self._devtools.close()
            self._devtools = None

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # Keep overlays pinned to the web view.
        if hasattr(self, "web_loading"):
            self.web_loading.setGeometry(self.web.rect())
            if self.web_loading.isVisible():
                self.web_loading.raise_()

        if hasattr(self, "video_overlay") and self.video_overlay.isVisible():
            self.video_overlay.setGeometry(self.web.rect())
            self.video_overlay.raise_()

    def about(self) -> None:
        st = self.bridge.get_tools_status()
        ff = "✓" if st.get("ffmpeg") else "×"
        fp = "✓" if st.get("ffprobe") else "×"
        
        # Get active Qt Multimedia backendinfo
        # In Qt 6, we can sometimes probe which service is active
        try:
            from PySide6.QtMultimedia import QMediaFormat
            backend = "Qt6 Default"
        except ImportError:
            backend = "Unknown"

        info = (
            "MediaManagerX\n\n"
            "Windows native app (PySide6)\n\n"
            "System Info:\n"
            f"• Platform: {sys.platform}\n"
            f"• Multimedia: {backend}\n\n"
            "Diagnostics:\n"
            f"• ffmpeg: {ff} ({st.get('ffmpeg_path', 'not found')})\n"
            f"• ffprobe: {fp} ({st.get('ffprobe_path', 'not found')})\n"
            f"• Thumbnails: {st.get('thumb_dir')}"
        )

        QMessageBox.information(self, "About MediaManagerX", info)


def main() -> None:
    app = QApplication(sys.argv)
    
    # Global styling is now handled dynamically in MainWindow
    app.setStyleSheet("")

    # Ensure QStandardPaths.AppDataLocation resolves to a stable, app-specific dir.
    app.setOrganizationName("G1enB1and")
    app.setApplicationName("MediaManagerX")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
