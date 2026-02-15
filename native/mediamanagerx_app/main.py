from __future__ import annotations

import sys
import hashlib
import subprocess
import shutil
import random
import threading
import time
from pathlib import Path

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
)
from PySide6.QtGui import QAction, QColor, QImageReader, QIcon
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
    QVBoxLayout,
    QTreeView,
    QFileSystemModel,
    QDialog,
    QPushButton,
    QHBoxLayout,
    QProgressBar,
    QMenu,
    QInputDialog,
    QTextEdit,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from native.mediamanagerx_app.video_overlay import LightboxVideoOverlay, VideoRequest


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


class Bridge(QObject):
    selectedFolderChanged = Signal(str)
    openVideoRequested = Signal(str, bool, bool, bool, int, int)
    closeVideoRequested = Signal()

    uiFlagChanged = Signal(str, bool)  # key, value
    metadataRequested = Signal(str)

    # Async file ops (so WebEngine UI doesn't freeze during rename)
    fileOpFinished = Signal(str, bool, str, str)  # op, ok, old_path, new_path

    def __init__(self) -> None:
        super().__init__()
        self._selected_folder: str = ""
        self._media_cache: dict[str, list[Path]] = {}
        appdata = Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        self._thumb_dir = appdata / "thumbs"
        self._thumb_dir.mkdir(parents=True, exist_ok=True)

        self.settings = QSettings("G1enB1and", "MediaManagerX")
        # Per-run seed so "randomize" changes every time you launch the app,
        # while remaining stable for pagination within a session.
        self._session_shuffle_seed = random.getrandbits(32)

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

    def set_selected_folder(self, folder: str) -> None:
        folder = folder or ""
        if folder == self._selected_folder:
            return
        self._selected_folder = folder
        try:
            self.settings.setValue("gallery/last_folder", self._selected_folder)
        except Exception:
            pass
        # Simple cache invalidation: folder change => new scan.
        self._media_cache.clear()
        self.selectedFolderChanged.emit(self._selected_folder)

    @Slot(result=str)
    def get_selected_folder(self) -> str:
        return self._selected_folder

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

    def _scan_media_paths(self, folder: str) -> list[Path]:
        cache_key = f"{folder}|rand={int(self._randomize_enabled())}"
        cached = self._media_cache.get(cache_key)
        if cached is not None:
            return cached

        root = Path(folder)
        if not root.exists() or not root.is_dir():
            self._media_cache[cache_key] = []
            return []

        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        exts = image_exts | video_exts

        candidates: list[Path] = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in exts:
                continue

            if self._hide_dot_enabled():
                # Skip any file under a dot-prefixed directory, or dot files.
                rel_parts = p.relative_to(root).parts
                if any(part.startswith(".") for part in rel_parts):
                    continue

            candidates.append(p)

        candidates.sort(key=lambda p: str(p).lower())

        if self._randomize_enabled():
            # Stable ordering within a session (and doesn't reshuffle when items
            # are added/removed): sort by per-item hash keyed by session seed.
            base = int(hashlib.sha1(folder.encode("utf-8")).hexdigest(), 16) % (2**32)
            seed = (base ^ int(self._session_shuffle_seed)) % (2**32)

            def _rank(p: Path) -> str:
                # Use as_posix() to avoid backslash escaping issues on Windows.
                s = f"{seed}:{p.as_posix().lower()}".encode("utf-8")
                return hashlib.sha1(s).hexdigest()

            candidates.sort(key=_rank)

        self._media_cache[cache_key] = candidates
        return candidates

    @Slot(str, result=int)
    def count_media(self, folder: str) -> int:
        """Return total number of discoverable media items under folder."""

        try:
            return len(self._scan_media_paths(folder))
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
            ):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))

            # Any setting that impacts list results/order should invalidate cache.
            if key in ("gallery.randomize", "gallery.hide_dot"):
                self._media_cache.clear()

            # UI flags should apply immediately.
            if key.startswith("ui."):
                self.uiFlagChanged.emit(key, bool(value))

            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            if key not in ("gallery.start_folder", "ui.accent_color"):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, str(value or ""))
            # (Future) if key affects UI, we can emit a signal.
            return True
        except Exception:
            return False

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
        self._media_cache.clear()
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
        self._media_cache.clear()
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
        self._media_cache.clear()
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

    @Slot(str, result=bool)
    def show_metadata(self, path: str) -> bool:
        try:
            self.metadataRequested.emit(str(path))
            return True
        except Exception:
            return False

    # reshuffle_gallery removed intentionally (kept randomize-per-session without UI clutter)

    @Slot(str, result=float)
    def get_video_duration_seconds(self, video_path: str) -> float:
        """Return duration seconds using ffprobe (0 on failure)."""

        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe:
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
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int]:
        """Return (width,height) from ffprobe, or (0,0) if unknown."""

        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe:
                return (0, 0)
            cmd = [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(video_path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            s = (r.stdout or "").strip()
            if not s or "x" not in s:
                return (0, 0)
            w_s, h_s = s.split("x", 1)
            return (int(w_s), int(h_s))
        except Exception:
            return (0, 0)

    @Slot(str, bool, bool, bool, result=bool)
    def open_native_video(self, video_path: str, autoplay: bool, loop: bool, muted: bool) -> bool:
        """Ask the native layer to open a video player."""

        try:
            w, h = self._probe_video_size(video_path)
            self.openVideoRequested.emit(
                str(video_path), bool(autoplay), bool(loop), bool(muted), int(w), int(h)
            )
            return True
        except Exception:
            return False

    @Slot(result=bool)
    def close_native_video(self) -> bool:
        try:
            self.closeVideoRequested.emit()
            return True
        except Exception:
            return False

    @Slot(str, int, int, result=list)
    def list_media(self, folder: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Return a list of media entries under folder.

        Each entry is a dict:
          {"path": <fs-path>, "url": <file://...>, "media_type": "image"|"video"}
        """

        try:
            image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

            candidates = self._scan_media_paths(folder)
            start = max(0, int(offset))
            end = start + max(0, int(limit))
            page = candidates[start:end]

            out: list[dict] = []
            for p in page:
                media_type = "image" if p.suffix.lower() in image_exts else "video"
                out.append(
                    {
                        "path": str(p),
                        "url": QUrl.fromLocalFile(str(p)).toString(),
                        "media_type": media_type,
                    }
                )

            return out
        except Exception:
            return []


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
        self.bridge.uiFlagChanged.connect(self._apply_ui_flag)
        self.bridge.metadataRequested.connect(self._show_metadata_for_path)

        self._build_menu()
        self._build_layout()

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

    def _build_layout(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter

        # Left: folder tree (native) — functional first, styling later
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)

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

        self.tree = FolderTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(str(default_root)))
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setExpandsOnDoubleClick(True)

        # Hide columns: keep only name
        for col in range(1, self.fs_model.columnCount()):
            self.tree.hideColumn(col)

        self.tree.selectionModel().selectionChanged.connect(self._on_tree_selection)

        # Context menu: hide folder
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        left_layout.addWidget(self.tree, 1)

        self._set_selected_folder(str(default_root))

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

        # Right: metadata panel placeholder
        meta = QWidget()
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(8, 8, 8, 8)
        meta_layout.setSpacing(8)
        meta_layout.addWidget(QLabel("Metadata"))
        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setText("(Metadata panel scaffold)\n\nSelect a file to show details here.")
        meta_layout.addWidget(self.meta_text, 1)

        # Native loading overlay shown while the WebEngine page itself is loading.
        self.web_loading = QWidget(self.web)
        self.web_loading.setStyleSheet("background: #0f1115;")
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

        self._devtools: QWebEngineView | None = None
        self.video_overlay = LightboxVideoOverlay(parent=self.web)
        self.video_overlay.setGeometry(self.web.rect())
        # When native overlay closes, also close the web lightbox chrome.
        self.video_overlay.on_close = self._close_web_lightbox
        self.video_overlay.raise_()

        # Prevent white flash while the first HTML/CSS loads.
        try:
            self.web.page().setBackgroundColor(QColor("#0f1115"))
        except Exception:
            pass

        channel = QWebChannel(self.web.page())
        channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(channel)

        index_path = Path(__file__).with_name("web") / "index.html"

        # Web loading signals (with minimum on-screen time to avoid flashing)
        self._web_loading_shown_ms: int | None = None
        self._web_loading_min_ms = 1000
        self.web.loadStarted.connect(lambda: self._set_web_loading(True))
        self.web.loadProgress.connect(self._on_web_load_progress)
        self.web.loadFinished.connect(lambda _ok: self._set_web_loading(False))

        self.web.setUrl(QUrl.fromLocalFile(str(index_path.resolve())))

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(meta)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)

        self.setCentralWidget(splitter)

        # Apply right panel flag from settings
        try:
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            self._apply_ui_flag("ui.show_right_panel", show_right)
        except Exception:
            pass

    def _set_selected_folder(self, folder_path: str) -> None:
        self.bridge.set_selected_folder(folder_path)

    def _on_tree_selection(self, *_args) -> None:
        idx = self.tree.currentIndex()
        if not idx.isValid():
            return
        path = self.fs_model.filePath(idx)
        if path:
            self._set_selected_folder(path)

    def _apply_ui_flag(self, key: str, value: bool) -> None:
        if key == "ui.show_left_panel":
            try:
                w = self.splitter.widget(0)
                if w:
                    w.setVisible(bool(value))
            except Exception:
                pass

        if key == "ui.show_right_panel":
            try:
                w = self.splitter.widget(2)
                if w:
                    w.setVisible(bool(value))
            except Exception:
                pass

    def _show_metadata_for_path(self, path: str) -> None:
        try:
            p = Path(path)
            if not p.exists() or not p.is_file():
                return

            st = p.stat()

            lines = [
                f"Name: {p.name}",
                f"Path: {p}",
                f"Size: {st.st_size:,} bytes",
                f"Modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))}",
            ]

            # Try to add dimensions without fully decoding
            try:
                reader = QImageReader(str(p))
                sz = reader.size()
                if sz.isValid() and sz.width() > 0 and sz.height() > 0:
                    lines.append(f"Resolution: {sz.width()} x {sz.height()}")
            except Exception:
                pass

            # Video duration/resolution via ffprobe if it's a video
            if p.suffix.lower() in {'.mp4', '.webm', '.mov', '.mkv'}:
                try:
                    w, h = self.bridge._probe_video_size(str(p))
                    if w and h:
                        lines.append(f"Video size: {w} x {h}")
                    dur = self.bridge.get_video_duration_seconds(str(p))
                    if dur:
                        lines.append(f"Duration: {dur:.2f}s")
                except Exception:
                    pass

            self.meta_text.setText("\n".join(lines))

            # Auto-open right panel
            self.bridge.settings.setValue("ui/show_right_panel", True)
            self._apply_ui_flag("ui.show_right_panel", True)
        except Exception:
            pass

    def _on_tree_context_menu(self, pos: QPoint) -> None:
        idx = self.tree.indexAt(pos)
        if not idx.isValid():
            return

        folder_path = self.fs_model.filePath(idx)
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

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))

        if chosen == act_hide:
            new_path = self.bridge.hide_by_renaming_dot(folder_path)
            if new_path:
                parent = str(Path(folder_path).parent)
                self.tree.setCurrentIndex(self.fs_model.index(parent))
                self._set_selected_folder(parent)

        if chosen == act_unhide:
            new_path = self.bridge.unhide_by_renaming_dot(folder_path)
            if new_path:
                parent = str(Path(new_path).parent)
                self.tree.setCurrentIndex(self.fs_model.index(parent))
                self._set_selected_folder(parent)

        if chosen == act_rename:
            cur = Path(folder_path).name
            next_name, ok = QInputDialog.getText(self, "Rename folder", "New name:", text=cur)
            if ok and next_name and next_name != cur:
                new_path = self.bridge.rename_path(folder_path, next_name)
                if new_path:
                    parent = str(Path(new_path).parent)
                    self.tree.setCurrentIndex(self.fs_model.index(parent))
                    self._set_selected_folder(parent)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a media folder")
        if folder:
            folder_path = str(Path(folder))
            # Update the tree root and select the chosen folder.
            self.tree.setRootIndex(self.fs_model.index(folder_path))
            self.tree.setCurrentIndex(self.fs_model.index(folder_path))
            self._set_selected_folder(folder_path)

    def _open_video_overlay(
        self, path: str, autoplay: bool, loop: bool, muted: bool, width: int, height: int
    ) -> None:
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

    def _close_web_lightbox(self) -> None:
        # Ask the web UI to close its lightbox chrome without re-triggering native close.
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_closeLightboxFromNative && window.__mmx_closeLightboxFromNative(); }catch(e){}"
            )
        except Exception:
            pass

    def _close_video_overlay(self) -> None:
        self.video_overlay.close_overlay()

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
        except Exception:
            pass

    def open_settings(self) -> None:
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_openSettings && window.__mmx_openSettings(); }catch(e){}"
            )
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
        QMessageBox.information(
            self,
            "About MediaManagerX",
            "MediaManagerX\n\nWindows native app (PySide6) — UI shell in progress.",
        )


def main() -> None:
    app = QApplication(sys.argv)
    # Ensure QStandardPaths.AppDataLocation resolves to a stable, app-specific dir.
    app.setOrganizationName("G1enB1and")
    app.setApplicationName("MediaManagerX")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
