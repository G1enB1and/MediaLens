from __future__ import annotations
# Source of Truth: \VERSION
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION"), "r") as f:
        __version__ = f.read().strip()
except Exception:
    __version__ = "v1.0.12"


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
import html
import shlex
from packaging.version import Version
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
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QImageReader,
    QIcon,
    QPainter,
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
    QMenu,
    QInputDialog,
    QTextEdit,
    QLineEdit,
    QFrame,
    QScrollArea,
    QCheckBox,
    QGridLayout,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from native.mediamanagerx_app.video_overlay import LightboxVideoOverlay, VideoRequest
from PySide6.QtCore import QSortFilterProxyModel, QModelIndex


import ctypes
from ctypes import wintypes


class Theme:
    """Centralized theme system with neutral surfaces and restrained accent usage."""
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
    def get_is_light() -> bool:
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
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            img = reader.read()
            if not img.isNull():
                pix = QPixmap.fromImage(img).scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pix)
            else:
                label.setText("Image Corrupt")
        else:
            # Try to get poster for video
            try:
                # We need to use bridge here, but bridge might be a web channel object.
                # Bridge has its own thumb dir.
                label.setText("Video")
            except:
                label.setText("File")

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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        accent_str = str(self.parent().window().bridge.settings.value("ui/accent_color", "#8ab4f8"))
        accent = QColor(accent_str)
        
        idle = QColor(Theme.get_splitter_idle(accent))
        color = accent if self.underMouse() else idle

        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        pen = QPen(color)
        pen.setWidth(1)
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
            print(f"DEBUG: dropEvent using side-channel: count={len(src_paths)}")
        
        # Priority 1: fallback to MIME data for tree-to-tree or external drops
        if not src_paths:
            print(f"DEBUG: dropEvent falling back to MIME: formats={mime.formats()}")
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

        # Show the root path itself
        if normalized_path == root:
            return True
            
        # Show children/descendants of the root path
        if normalized_path.startswith(root + "/"):
            return True
            
        # Show ancestors of the root path (so we can reach it from the top)
        if (root + "/").startswith(normalized_path + "/"):
            return True
            
        # Special case: show Windows drives if they are ancestors
        if len(normalized_path) == 2 and normalized_path[1] == ":" and root.startswith(normalized_path):
            return True

        return False

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
    openVideoInPlaceRequested = Signal(str, int, int, int, int, bool, bool, bool, int, int) # path, x, y, w, h, autoplay, loop, muted, pw, ph
    updateVideoRectRequested = Signal(int, int, int, int)
    videoPreprocessingStatus = Signal(str)  # status message (empty = done)
    videoPlaybackStarted = Signal() # Signal that native player has received first frame
    videoSuppressed = Signal(bool) # Signal when video is hidden/suppressed (e.g. by header)
    closeVideoRequested = Signal()
    videoMutedChanged = Signal(bool)
    videoPausedChanged = Signal(bool)

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
    
    # Update Signals
    updateAvailable = Signal(str, bool)  # version, manual
    updateDownloadProgress = Signal(int)
    updateError = Signal(str)
    
    dragOverFolder = Signal(str)
    collectionsChanged = Signal()
    # Native Tooltip Controls
    updateTooltipRequested = Signal(int, bool, str) # count, isCopy, targetFolder
    hideTooltipRequested = Signal()
    conflictDialogRequested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        print("Bridge: Initializing...")
        self._selected_folders: list[str] = []
        self._active_collection_id: int | None = None
        self._active_collection_name: str = ""
        self._scan_abort = False
        self._scan_lock = threading.Lock()
        self.drag_paths: list[str] = []
        self._last_dlg_res = None
        
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
        self.nam = QNetworkAccessManager(self)
        self.nam.setRedirectPolicy(QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self._update_reply = None
        self._download_reply = None
        self._session_shuffle_seed = random.getrandbits(32)
        
        # Hybrid Fast-Load Cache
        self._disk_cache: dict[str, Path] = {}
        self._disk_cache_key: str = "" # Hash of selected folders list
        self._last_full_scan_key: str = ""

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
            vf = "thumbnail,scale=min(640\\,iw):-2"
            cmd = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", "0.5", "-i", str(video_path),
                "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out),
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

    @Slot(list)
    def set_drag_paths(self, paths: list[str]) -> None:
        """Called from JS to register the actual files being dragged."""
        self.drag_paths = [str(p) for p in paths]
        print(f"DEBUG: Bridge set_drag_paths: count={len(self.drag_paths)}")

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

    @Slot(result=list)
    def get_selected_folders(self) -> list:
        return self._selected_folders

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
        }
        return mode if mode in allowed else "masonry"

    @Slot(result=dict)
    def get_settings(self) -> dict:
        try:
            data = {
                "gallery.randomize": self._randomize_enabled(),
                "gallery.restore_last": self._last_folder() != "",
                "gallery.show_hidden": self._show_hidden_enabled(),
                "gallery.start_folder": self._start_folder_setting(),
                "gallery.view_mode": self._gallery_view_mode(),
                "ui.accent_color": str(self.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8"),
                "ui.show_left_panel": bool(self.settings.value("ui/show_left_panel", True, type=bool)),
                "ui.show_right_panel": bool(self.settings.value("ui/show_right_panel", True, type=bool)),
                "ui.enable_glassmorphism": bool(self.settings.value("ui/enable_glassmorphism", True, type=bool)),
                "ui.theme_mode": str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark"),
                "metadata.display.res": bool(self.settings.value("metadata/display/res", True, type=bool)),
                "metadata.display.size": bool(self.settings.value("metadata/display/size", True, type=bool)),
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
                if qkey.startswith("metadata/display/") or qkey.startswith("metadata/layout/"):
                    data[qkey.replace("/", ".")] = self._coerce_setting_value(self.settings.value(qkey))
            return data
        except Exception:
            return {
                "gallery.randomize": False,
                "gallery.restore_last": False,
                "gallery.show_hidden": False,
                "gallery.start_folder": "",
                "gallery.view_mode": "masonry",
                "ui.accent_color": "#8ab4f8",
                "ui.show_left_panel": True,
                "ui.show_right_panel": True,
                "ui.enable_glassmorphism": True,
                "ui.theme_mode": "dark",
            }

    @Slot(result=str)
    def get_app_version(self) -> str:
        return __version__

    @Slot(bool)
    def check_for_updates(self, manual: bool = False):
        """Check GitHub for a newer version in the VERSION file."""
        url = "https://raw.githubusercontent.com/G1enB1and/MediaManagerX/main/VERSION"
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
        url = "https://github.com/G1enB1and/MediaManagerX/releases/latest/download/MediaManagerX_Setup.exe"
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
                setup_path = os.path.join(temp_dir, "MediaManagerX_Setup_New.exe")
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
                "ui.show_left_panel", 
                "ui.show_right_panel", 
                "ui.enable_glassmorphism", 
                "updates.check_on_launch"
            )
            if key not in allowed and not key.startswith("metadata.display."):
                return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, bool(value))
            if key.startswith("ui.") or key.startswith("metadata.display.") or key == "gallery.show_hidden":
                self.settings.sync()
                self.uiFlagChanged.emit(key, bool(value))
            return True
        except Exception:
            return False

    @Slot(str, str, result=bool)
    def set_setting_str(self, key: str, value: str) -> bool:
        try:
            if key not in ("gallery.start_folder", "gallery.view_mode", "ui.accent_color", "ui.theme_mode", "metadata.display.order") and not key.startswith("metadata.layout."):
                return False
            if key == "gallery.view_mode":
                allowed = {"masonry", "grid_small", "grid_medium", "grid_large", "grid_xlarge", "list", "content", "details"}
                if value not in allowed:
                    return False
            qkey = key.replace(".", "/")
            self.settings.setValue(qkey, str(value or ""))
            if key == "ui.accent_color":
                self.accentColorChanged.emit(str(value or "#8ab4f8"))
            elif key == "ui.theme_mode":
                self.settings.sync()
                self.uiFlagChanged.emit(key, value == "light")
            elif key == "gallery.view_mode":
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
                        res = subprocess.run(cmd_probe, capture_output=True, text=True)
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
                    subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
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
            print(f"DEBUG: _process_file_op START: op={op_type}, count={len(src_paths)}")
            
            is_move = op_type in ("move", "paste_move")
            sticky_action = None
            any_ok = False
            
            try:
                for src in src_paths:
                    if not src.exists():
                        print(f"DEBUG: Source does not exist: {src}")
                        continue
                    
                    dst = target_dir / src.name
                    action = "keep_both"
                    final_dst = dst
                    
                    if dst.exists() and not dst.samefile(src):
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
                        print(f"DEBUG: {op_type} {src.name} -> {final_dst.name} (action={action})")
                        if is_move:
                            try:
                                # Try atomic os.replace (removes source, overwrites target if exists)
                                os.replace(src, final_dst)
                                print(f"DEBUG: os.replace (MOVE) success")
                            except OSError:
                                # Cross-device move fallback
                                shutil.move(src, final_dst)
                                print(f"DEBUG: shutil.move fallback success")
                            
                            # Double check: ensure source is gone (as requested by user)
                            if src.exists():
                                try:
                                    if src.is_dir(): shutil.rmtree(src)
                                    else: src.unlink()
                                    print(f"DEBUG: Explicit delete success for {src.name}")
                                except: pass
                            
                            if src.is_dir(): move_directory_in_db(self.conn, str(src), str(final_dst))
                            else: rename_media_path(self.conn, str(src), str(final_dst))
                        else:
                            # Copy operation
                            if src.is_dir(): shutil.copytree(src, final_dst)
                            else: shutil.copy2(src, final_dst)
                            
                            ext = final_dst.suffix.lower()
                            mtype = "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"} else "video"
                            add_media_item(self.conn, str(final_dst), mtype)
                        
                        any_ok = True
                    except Exception as e:
                        print(f"DEBUG: Op fail for {src.name}: {e}")

                op_signal = "paste" if "paste" in op_type else op_type
                self.fileOpFinished.emit(op_signal, any_ok, "", str(target_dir))
            except Exception as e:
                print(f"DEBUG: _process_file_op GLOBAL ERROR: {e}")
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
            if not p.exists(): return False
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
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
            cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float((r.stdout or "").strip() or 0.0)
        except Exception: return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int, bool]:
        ffprobe = self._ffprobe_bin()
        if not ffprobe: return (0, 0, False)
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", str(video_path)]
        try:
            import json
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
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
                        else: self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception: self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else: self.openVideoRequested.emit(str(video_path), bool(autoplay), bool(loop), bool(muted), int(w), int(h))
            return True
        except Exception: return False

    @Slot(str, int, int, int, int, bool, bool, bool, int, int)
    def open_native_video_inplace(self, video_path: str, x: int, y: int, w: int, h: int, autoplay: bool, loop: bool, muted: bool, vw: int = 0, vh: int = 0) -> None:
        # If loop is false, double check duration (for previously scanned files without duration metadata)
        if not loop:
            d_s = self.get_video_duration_seconds(video_path)
            if 0 < d_s < 60:
                loop = True
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video_inplace for non-file path: {video_path}")
                return
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
                        else: self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception: self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoInPlaceRequested.emit(str(video_path), int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(vw), int(vh))
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
        ew, eh = (w if w % 2 == 0 else w - 1), (h if h % 2 == 0 else h - 1)
        if ew <= 0 or eh <= 0: return None
        tmp = tempfile.NamedTemporaryFile(prefix="mmx_fixed_", suffix=".mkv", delete=False)
        tmp.close()
        out_path = tmp.name
        vf = f"scale={ew}:{eh},setsar=1,format=yuv420p"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", str(video_path), "-vf", vf, "-c:v", "mjpeg", "-q:v", "3", "-c:a", "copy", out_path]
        try:
            if subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0: return out_path
        except Exception: pass
        return None

    @Slot(result=bool)
    def close_native_video(self) -> bool:
        try: self.closeVideoRequested.emit(); return True
        except Exception: return False

    @Slot(str, result=dict)
    def get_media_metadata(self, path: str) -> dict:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.ai_metadata_repo import (
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
            meta = get_media_metadata(self.conn, m["id"]) or {}
            ai_meta = get_media_ai_metadata(self.conn, m["id"]) or {}
            if not ai_meta:
                inspect_and_persist_if_supported(self.conn, m["id"], path, m.get("media_type"))
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
                "ai_prompt": ai_prompt, "ai_negative_prompt": ai_negative_prompt,
                "ai_params": ai_params, "ai_tool_summary": ai_tool_summary,
                "tags": list_media_tags(self.conn, m["id"]), "has_metadata": bool(meta or ai_meta)
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

    @Slot(list, int, int, str, str, str, result=list)
    def list_media(self, folders, limit=100, offset=0, sort_by="name_asc", filter_type="all", search_query="") -> list:
        try:
            candidates = self._get_gallery_entries(folders, sort_by, filter_type, search_query)
            start, end = max(0, int(offset)), max(0, int(offset)) + max(0, int(limit))
            out = []
            for r in candidates[start:end]:
                if r.get("is_folder"):
                    out.append(
                        {
                            "path": str(r["path"]),
                            "url": "",
                            "media_type": "folder",
                            "is_folder": True,
                            "is_hidden": bool(r.get("is_hidden")),
                            "is_animated": False,
                            "width": None,
                            "height": None,
                            "duration": None,
                            "modified_time": r.get("modified_time"),
                            "file_size": None,
                        }
                    )
                    continue
                real = r.get("_real_path")
                p = real if isinstance(real, Path) else Path(r["path"])
                try:
                    mtime = int(p.stat().st_mtime_ns)
                except Exception:
                    mtime = int(r.get("modified_time") or 0)
                    
                out.append({
                    "path": str(p), 
                    "url": f"{QUrl.fromLocalFile(str(p)).toString()}?t={mtime}", 
                    "media_type": r["media_type"], 
                    "is_folder": False,
                    "is_hidden": bool(r.get("is_hidden")),
                    "is_animated": self._is_animated(p),
                    "width": r.get("width"),
                    "height": r.get("height"),
                    "duration": r.get("duration"),
                    "modified_time": mtime,
                    "file_size": r.get("file_size"),
                })
            return out
        except Exception: return []

    @Slot(list, str, str, result=int)
    def count_media(self, folders: list, filter_type: str = "all", search_query: str = "") -> int:
        try:
            return len(self._get_gallery_entries(folders, "name_asc", filter_type, search_query))
        except Exception: return 0

    def _get_reconciled_candidates(self, folders: list, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_scope
        from app.mediamanager.utils.pathing import normalize_windows_path
        ALL_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
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
        if filter_type == "image": candidates = [r for r in candidates if r["path"].lower().endswith(tuple(image_exts)) and not self._is_animated(Path(r["path"]))]
        elif filter_type == "video": candidates = [r for r in candidates if not r["path"].lower().endswith(tuple(image_exts))]
        elif filter_type == "animated": candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
        
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _get_collection_candidates(self, collection_id: int, filter_type: str = "all", search_query: str = "") -> list[dict]:
        from app.mediamanager.db.media_repo import list_media_in_collection
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        show_hidden = self._show_hidden_enabled()
        
        raw_candidates = list_media_in_collection(self.conn, int(collection_id))
        candidates = []
        for r in raw_candidates:
            if not show_hidden and r.get("is_hidden"):
                continue
            path_obj = Path(r["path"])
            if path_obj.exists() and path_obj.is_file():
                candidates.append(r)
                
        if filter_type == "image":
            candidates = [r for r in candidates if r["path"].lower().endswith(tuple(image_exts)) and not self._is_animated(Path(r["path"]))]
        elif filter_type == "video":
            candidates = [r for r in candidates if not r["path"].lower().endswith(tuple(image_exts))]
        elif filter_type == "animated":
            candidates = [r for r in candidates if self._is_animated(Path(r["path"]))]
            
        if search_query.strip():
            candidates = [r for r in candidates if self._matches_media_search(r, search_query)]
        return candidates

    def _matches_media_search(self, row: dict, search_query: str) -> bool:
        from app.mediamanager.search_query import matches_media_search
        return matches_media_search(row, search_query)

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
                        modified_time = int(child.stat().st_mtime_ns)
                    except Exception:
                        modified_time = 0
                    entries.append(
                        {
                            "path": str(child),
                            "media_type": "folder",
                            "is_folder": True,
                            "is_hidden": is_hidden,
                            "file_size": None,
                            "modified_time": modified_time,
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
        date_key = lambda row: row.get("modified_time") or 0
        size_key = lambda row: row.get("file_size") or 0
        folders = [row for row in entries if row.get("is_folder")]
        media = [row for row in entries if not row.get("is_folder")]

        if self._randomize_enabled() and sort_by == "name_asc":
            folders.sort(key=name_key)
            random.Random(self._session_shuffle_seed).shuffle(media)
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

    def _get_gallery_entries(self, folders: list[str], sort_by: str = "name_asc", filter_type: str = "all", search_query: str = "") -> list[dict]:
        if folders:
            entries = self._get_reconciled_candidates(folders, filter_type, search_query)
            if self._gallery_view_mode() != "masonry":
                entries = self._list_folder_entries(folders, search_query) + entries
        elif self._active_collection_id is not None:
            entries = self._get_collection_candidates(self._active_collection_id, filter_type, search_query)
        else:
            entries = []
        return self._sort_gallery_entries(entries, sort_by)

    @Slot(list, str)
    def start_scan(self, folders: list, search_query: str = "") -> None:
        if not folders:
            return
        scan_key = hashlib.sha1(",".join(sorted(str(folder) for folder in folders)).encode()).hexdigest()
        if self._last_full_scan_key == scan_key:
            return
        self._scan_abort = True
        def work():
            try:
                time.sleep(0.1)
                self._scan_abort = False
                primary = folders[0] if folders else ""
                self.scanStarted.emit(primary)
                from app.mediamanager.db.connect import connect_db
                scan_conn = connect_db(str(self.db_path))
                try:
                    paths = list(self._disk_cache.values())
                    if not paths and folders:
                        self._get_reconciled_candidates(folders, "all", search_query)
                        paths = list(self._disk_cache.values())
                    self._do_full_scan(paths, scan_conn, emit_progress=True)
                    self._last_full_scan_key = scan_key
                    self.scanFinished.emit(primary, len(self._get_reconciled_candidates(folders, "all", search_query)))
                finally:
                    scan_conn.close()
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
                from app.mediamanager.db.connect import connect_db
                scan_conn = connect_db(str(self.db_path))
                try:
                    self._do_full_scan(clean_paths, scan_conn, emit_progress=False)
                finally:
                    scan_conn.close()
            except Exception as exc:
                try:
                    self._log(f"Page scan failed: {exc}")
                except Exception:
                    pass
        threading.Thread(target=work, daemon=True).start()

    def _do_full_scan(self, paths: list[Path], conn, emit_progress: bool = True) -> int:
        from app.mediamanager.db.media_repo import get_media_by_path, upsert_media_item
        from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
        from app.mediamanager.utils.hashing import calculate_file_hash
        from datetime import datetime, timezone
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
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
                        if existing.get("width") and existing.get("height"):
                            skip = True
                
                if not skip:
                    width, height, d_ms = None, None, None
                    mtype = "image" if p.suffix.lower() in image_exts else "video"
                    
                    if mtype == "image":
                        reader = QImageReader(str(p))
                        if reader.canRead():
                            sz = reader.size()
                            if sz.isValid():
                                width, height = sz.width(), sz.height()
                    else:
                        w, h, _ = self._probe_video_size(str(p))
                        if w > 0 and h > 0:
                            width, height = w, h
                        # Capture duration for looping logic
                        d_s = self.get_video_duration_seconds(str(p))
                        if d_s > 0:
                            d_ms = int(d_s * 1000)
                            
                    media_id = upsert_media_item(conn, str(p), mtype, calculate_file_hash(p), width=width, height=height, duration_ms=d_ms)
                if media_id is not None:
                    inspect_and_persist_if_supported(conn, media_id, str(p), "image" if p.suffix.lower() in image_exts else "video")
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


class NativeDragTooltip(QLabel):
    """A floating, frameless tooltip that follows the cursor during drag operations."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("nativeDragTooltip")
        # Standard styling: small padding, less rounding
        self.setStyleSheet("""
            #nativeDragTooltip {
                background: palette(window);
                border: 1px solid palette(highlight);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 10pt;
            }
        """)

    def update_style(self, accent_color: QColor, is_light: bool):
        bg = Theme.get_control_bg(accent_color)
        fg = Theme.get_text_color()
        border = Theme.get_border(accent_color)
        
        self.setStyleSheet(f"""
            #nativeDragTooltip {{
                background-color: {bg} !important;
                color: {fg} !important;
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }}
        """)

    def update_text(self, text: str):
        self.setText(text)
        self.adjustSize()

    def follow_cursor(self):
        pos = QCursor.pos()
        # Offset slightly from the cursor - closer (10,10) helps cover native tooltips
        self.move(pos.x() + 10, pos.y() + 10)
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
        text_color_str = Theme.get_text_color()
        pen = QPen(QColor(text_color_str))
        pen.setWidth(1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        y = self.height() // 2
        painter.drawLine(0, y, self.width(), y)


class GalleryView(QWebEngineView):
    """Gallery view that accepts drag and drop from external file explorers."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

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
            selected = bridge.get_selected_folders()
            target_folder = selected[0] if selected else ""
            
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
                selected = bridge.get_selected_folders()
                target_path = selected[0] if selected else ""
                
                if target_path:
                    # Filter out if moving to THE SAME folder
                    target_path_norm = target_path.replace("\\", "/").lower()
                    src_paths = [p for p in src_paths if os.path.dirname(p).replace("\\", "/").lower() != target_path_norm]
                    
                    if src_paths:
                        # Determine if COPY or MOVE
                        is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                        op_type = "copy" if is_copy else "move"
                        
                        paths_obj = [Path(p) for p in src_paths]
                        bridge._process_file_op(op_type, paths_obj, Path(target_path))
                        event.acceptProposedAction()
                        return
        
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MediaManagerX")
        self.resize(1200, 800)

        # Set window icon
        icon_path = Path(__file__).with_name("web") / "favicon.png"
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
        self.bridge.loadFolderRequested.connect(self._on_load_folder_requested)
        self.bridge.accentColorChanged.connect(self._on_accent_changed)
        self._current_accent = Theme.ACCENT_DEFAULT

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
        bug_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/G1enB1and/MediaManagerX/issues"))
        help_menu.addAction(bug_action)
        
        website_action = QAction("&Project Website", self)
        website_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/G1enB1and/MediaManagerX"))
        help_menu.addAction(website_action)

        help_menu.addSeparator()

        check_updates_action = QAction("Check for &Updates...", self)
        check_updates_action.triggered.connect(lambda: self.bridge.check_for_updates(manual=True))
        help_menu.addAction(check_updates_action)

        for m in (file_menu, edit_menu, view_menu, help_menu):
            m.aboutToShow.connect(self._dismiss_web_menus)

    def _set_gallery_view_mode(self, mode: str) -> None:
        self.bridge.set_setting_str("gallery.view_mode", mode)
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
        return isinstance(f, (QLineEdit, QTextEdit))

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
        
        # Confirmation for multiple or folder deletion
        count = len(paths)
        msg = f"Are you sure you want to delete {count} items?" if count > 1 else f"Are you sure you want to delete '{Path(paths[0]).name}'?"
        ret = QMessageBox.question(self, "Confirm Delete", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            for p in paths:
                self.bridge.delete_path(p)

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
        self.left_panel = QWidget()
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

        folders_section = QWidget()
        folders_layout = QVBoxLayout(folders_section)
        folders_layout.setContentsMargins(0, 0, 0, 0)
        folders_layout.setSpacing(6)
        folders_layout.addWidget(QLabel("Folders"))
        folders_layout.addWidget(self.tree, 1)

        collections_section = QWidget()
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

        self.left_sections_splitter.addWidget(folders_section)
        self.left_sections_splitter.addWidget(collections_section)
        self.left_sections_splitter.setStretchFactor(0, 1)
        self.left_sections_splitter.setStretchFactor(1, 0)
        left_sections_state = self.bridge.settings.value("ui/left_sections_splitter_state")
        if left_sections_state:
            self.left_sections_splitter.restoreState(left_sections_state)
        else:
            self.left_sections_splitter.setSizes([430, 170])
        self.left_sections_splitter.splitterMoved.connect(lambda *args: self._save_splitter_state())

        left_layout.addWidget(self.left_sections_splitter, 1)

        self.bridge.collectionsChanged.connect(self._reload_collections)
        self._reload_collections()

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

        self.web = GalleryView(self)
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
        self.right_panel = QWidget()
        self.right_panel.setObjectName("rightPanel")
        outer_right_layout = QVBoxLayout(self.right_panel)
        outer_right_layout.setContentsMargins(0, 0, 0, 0)
        outer_right_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("metaScrollArea")
        
        self.scroll_container = QWidget()
        self.scroll_container.setObjectName("rightPanelScrollContainer")
        right_layout = QVBoxLayout(self.scroll_container)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(6)

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
        
        self.meta_fields_layout = QVBoxLayout()
        self.meta_fields_layout.setSpacing(6)
        right_layout.addLayout(self.meta_fields_layout)

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
        self.meta_notes = QTextEdit()
        self.meta_notes.setPlaceholderText("Personal notes...")
        self.meta_notes.setMaximumHeight(90)

        right_layout.addStretch(1)

        self.btn_clear_bulk_tags = QPushButton("Clear All Tags")
        self.btn_clear_bulk_tags.setObjectName("btnClearBulkTags")
        self.btn_clear_bulk_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bulk_tags.clicked.connect(self._clear_bulk_tags)
        self.btn_clear_bulk_tags.setStyleSheet("QPushButton { color: #f28b82; }") # Subtle red
        right_layout.addWidget(self.btn_clear_bulk_tags)
        self.btn_clear_bulk_tags.setVisible(False)

        self.btn_save_meta = QPushButton("Save Changes to Database")
        self.btn_save_meta.setObjectName("btnSaveMeta")
        self.btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_meta.clicked.connect(self._save_native_metadata)
        right_layout.addWidget(self.btn_save_meta)

        # AI/EXIF Actions
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        self.btn_import_exif = QPushButton("Import Metadata")
        self.btn_import_exif.setObjectName("btnImportExif")
        self.btn_import_exif.setToolTip("Append tags/comments from file to database")
        self.btn_import_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_exif.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_import_exif.clicked.connect(self._import_exif_to_db)
        action_layout.addWidget(self.btn_import_exif)

        self.btn_merge_hidden_meta = QPushButton("Merge Hidden Metadata Into Visible Comments Field")
        self.btn_merge_hidden_meta.setObjectName("btnMergeHiddenMeta")
        self.btn_merge_hidden_meta.setToolTip("Write combined hidden metadata into the Windows-visible comments field using the existing embed path")
        self.btn_merge_hidden_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_merge_hidden_meta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_merge_hidden_meta.clicked.connect(self._merge_hidden_metadata_into_visible_comments)
        action_layout.addWidget(self.btn_merge_hidden_meta)

        self.btn_save_to_exif = QPushButton("Embed Data in File")
        self.btn_save_to_exif.setObjectName("btnSaveToExif")
        self.btn_save_to_exif.setToolTip("Write tags and comments from these fields into the file's embedded metadata")
        self.btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_to_exif.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
            splitter.setSizes([200, 700, 300])

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
        self._setup_metadata_layout()
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
            if hasattr(self, "collections_list"):
                self.collections_list.blockSignals(True)
                self.collections_list.clearSelection()
                self.collections_list.blockSignals(False)
            self._set_selected_folders(paths)

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
            elif key == "ui.show_left_panel":
                self.left_panel.setVisible(bool(value))
            elif key == "ui.show_right_panel":
                self.right_panel.setVisible(bool(value))
            elif key == "ui.theme_mode":
                self._update_native_styles(self._current_accent)
                self._update_splitter_style(self._current_accent)
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
            
            ai_prompt = self.meta_ai_prompt_edit.toPlainText()
            ai_neg_prompt = self.meta_ai_negative_prompt_edit.toPlainText()
            ai_params = self.meta_ai_params_edit.toPlainText()

            try:
                # Save Changes is DB-only. Embedded fields are file-only and should not be persisted here.
                self.bridge.update_media_metadata(path, "", desc, notes, "", "", ai_prompt, ai_neg_prompt, ai_params)
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
    def _build_png_xmp_packet(comment: str, tags: list[str]) -> str:
        """Build a minimal XMP packet for PNG that Windows/tools can parse.

        Windows Explorer reliably reads PNG tags from XMP dc:subject on many systems.
        For PNG comments, Windows maps System.Comment from exif:UserComment only when
        encoded as an rdf:Alt localized string (not a plain text node).
        """
        safe_comment = html.escape(comment or "", quote=False)
        safe_tags = [html.escape(t, quote=False) for t in (tags or []) if str(t).strip()]
        tag_items = "".join(f"<rdf:li>{t}</rdf:li>" for t in safe_tags)

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

        if not parts:
            return ""

        body = "".join(parts)
        return (
            "<?xpacket begin=\"\ufeff\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?>"
            "<x:xmpmeta xmlns:x=\"adobe:ns:meta/\">"
            "<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\">"
            "<rdf:Description rdf:about=\"\" "
            "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
            "xmlns:exif=\"http://ns.adobe.com/exif/1.0/\">"
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
            from app.mediamanager.metadata.persistence import inspect_and_persist_if_supported
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
                media_type = "image" if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"} else "video"
                add_media_item(self.bridge.conn, path, media_type)
                media = get_media_by_path(self.bridge.conn, path)
            ai_ui = {}
            ai_tool_summary = ""
            if media:
                inspect_and_persist_if_supported(self.bridge.conn, media["id"], path, media.get("media_type"))
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
                ]
            )
            if not visible["comment"] and not visible["tags"] and not res["tool_metadata"] and not has_pipeline_data:
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

    @Slot()
    def _save_to_exif_cmd(self) -> None:
        """Embed tags and comments from the 'Embedded' UI fields INTO the file."""
        if not self._current_path: return
        p = Path(self._current_path)
        if not p.exists(): return

        ext = p.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            self.meta_status_lbl.setText("Embed not supported for this file type.")
            return

        try:
            from PIL import Image, PngImagePlugin
            import tempfile, os

            # Isolation Rule: Only use the 'Embedded' UI boxes for actual embedding
            tags_raw = self.meta_embedded_tags_edit.text().strip()
            comm_raw = self.meta_embedded_comments_edit.toPlainText().strip()
            
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

                    # PNG + Windows Explorer: tags are often read from XMP dc:subject
                    # rather than PNG tEXt or EXIF XP* fields. Emit XMP in addition to
                    # legacy keys for maximum compatibility.
                    parsed_tags = [t.strip() for t in win_tags.split(";") if t.strip()]
                    xmp_packet = self._build_png_xmp_packet(comm_raw, parsed_tags)
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
                    for tag_id in (0x9C9C, 270, 37510, 0x9C9E, 0x9C9F):
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
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webp", dir=p.parent) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        img.save(tmp_path, "WEBP", exif=exif, lossless=True)
                        os.replace(tmp_path, str(p))
                    except Exception as e:
                        if tmp_path.exists(): tmp_path.unlink()
                        raise e

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
        self._current_paths = paths # Store list for bulk save
        self._current_path = paths[0] if not is_bulk else None
        metadata_kind = self._metadata_kind_for_path(paths[0] if paths else None)
        self._current_metadata_kind = metadata_kind
        self._setup_metadata_layout(metadata_kind)

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

        self.meta_res_lbl.setVisible(not is_bulk and show_res)
        self.meta_size_lbl.setVisible(not is_bulk and show_size)
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

        if not is_bulk:
            path = paths[0]
            p = Path(path)
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

                        # Embedded fields should mirror the file (Windows-visible subset), never the DB.
                        try:
                            img.load()
                        except Exception:
                            pass
                        visible = self._harvest_windows_visible_metadata(img)
                        harvested = self._harvest_universal_metadata(img)
                        self.meta_embedded_tags_edit.setText("; ".join(visible.get("tags", [])))
                        self.meta_embedded_comments_edit.setPlainText(visible.get("comment", "") or "")
                        # Also check for separately-stored AI fields from the harvester
                        # (We do NOT overwrite the DB editable fields here, they are populated from DB earlier)
                        
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
                vw, vh, _ = self.bridge._probe_video_size(str(p))
                if vw > 0 and vh > 0:
                    self.meta_res_lbl.setText(f"Resolution: {vw} × {vh} px")
                else:
                    self.meta_res_lbl.setText("Resolution: ")
                video_meta = self._probe_video_details(str(p))
                if video_meta.get("duration"):
                    self.meta_duration_lbl.setText(f"Duration: {video_meta['duration']}")
                if video_meta.get("fps"):
                    self.meta_fps_lbl.setText(f"FPS: {video_meta['fps']}")
                if video_meta.get("codec"):
                    self.meta_codec_lbl.setText(f"Codec: {video_meta['codec']}")
                if video_meta.get("audio"):
                    self.meta_audio_lbl.setText(f"Audio: {video_meta['audio']}")
        
            self.btn_save_meta.setText("Save Changes to Database")
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
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return "image"
        return "video"

    def _metadata_group_fields(self, kind: str) -> dict[str, list[str]]:
        image_general = ["res", "size", "description", "tags", "notes", "embeddedtags", "embeddedcomments"]
        image_camera = ["camera", "location", "iso", "shutter", "aperture", "software", "lens", "dpi"]
        image_ai = [
            "aistatus", "aisource", "aifamilies", "aidetectionreasons", "ailoras", "aimodel", "aicheckpoint",
            "aisampler", "aischeduler", "aicfg", "aisteps", "aiseed", "aiupscaler", "aidenoise",
            "aiprompt", "ainegprompt", "aiparams", "aiworkflows", "aiprovenance", "aicharcards", "airawpaths",
        ]
        if kind == "video":
            return {
                "general": ["res", "size", "duration", "fps", "codec", "audio", "description", "tags", "notes"],
                "ai": image_ai,
            }
        if kind == "gif":
            return {
                "general": ["res", "size", "duration", "fps", "description", "tags", "notes", "embeddedtags", "embeddedcomments"],
                "ai": image_ai,
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
                return self._is_metadata_enabled(key, default)
            if isinstance(val, str):
                return val.lower() in ("true", "1")
            return bool(val)
        except Exception:
            return default

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
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(video_path)]
        try:
            probe = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout or "{}")
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
        sep_widgets = [self.meta_sep1, self.meta_sep2]
        sep_index = 0
        for index, group in enumerate(visible_groups):
            field_order = self._metadata_field_order(kind, group)
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
        
        self.meta_filename_edit.setText("")
        self.meta_path_lbl.setText("Folder: ")
        self.meta_size_lbl.setText("File Size: ")
        self.meta_res_lbl.setText("Resolution: ")
        self.meta_duration_lbl.setText("Duration: ")
        self.meta_fps_lbl.setText("FPS: ")
        self.meta_codec_lbl.setText("Codec: ")
        self.meta_audio_lbl.setText("Audio: ")
        self._clear_embedded_labels()
        
        # UI visibility logic
        visible_groups = [group for group in self._metadata_group_order(kind) if self._is_metadata_group_enabled(kind, group, True)]
        active_fields = {
            field
            for group in visible_groups
            for field in self._metadata_group_fields(kind).get(group, [])
        }
        self.meta_res_lbl.setVisible("res" in active_fields and self._is_metadata_enabled_for_kind(kind, "res", True))
        self.meta_size_lbl.setVisible("size" in active_fields and self._is_metadata_enabled_for_kind(kind, "size", True))
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
        is_hidden = self.bridge.repo.is_path_hidden(folder_path)

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
            success = self.bridge.set_folder_hidden(folder_path, True)
            if success:
                self.proxy_model.invalidateFilter()

        if chosen == act_unhide:
            success = self.bridge.set_folder_hidden(folder_path, False)
            if success:
                self.proxy_model.invalidateFilter()

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
        header_height = 112 # Total height of header + toolbar in JS
        
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
        header_height = 112
        
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

    def _update_splitter_style(self, accent_color: str) -> None:
        """Update QSplitter handles with light grey idle and accent color hover."""
        if not hasattr(self, "splitter"):
            return
        
        self._current_accent = accent_color
        self.splitter.setHandleWidth(1)
        
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
        
        # Update tooltip theme
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.update_style(QColor(accent_color), Theme.get_is_light())
        
        # Belt and suspenders: force update web layer via injection
        js = f"document.documentElement.style.setProperty('--accent', '{accent_color}');"
        if hasattr(self, "webview") and self.webview.page():
            self.webview.page().runJavaScript(js)

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
        
        # Windows Title Bar
        self._set_window_title_bar_theme(not is_light, sb_bg)
        
        # Native Tooltip Style
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.update_style(accent, is_light)
        
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
            f"QProgressBar{{background: {load_bg}; border-radius:"
            " 5px;}}"
            f"QProgressBar::chunk{{background: {accent_str}; border-radius: 5px;}}"
        )
        
        # Left Panel (Folders)
        self.left_panel.setStyleSheet(f"""
            QWidget {{ background-color: {sb_bg_str}; color: {text}; }}
            QTreeView {{ background-color: {sb_bg_str}; border: none; color: {text}; }}
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
            QLabel {{ color: {text}; font-weight: bold; background: transparent; }}
            {scrollbar_style}
        """)
        
        # Right Panel (Metadata) - Mirroring Left Panel Background precisely
        self.right_panel.setStyleSheet(f"background-color: {sb_bg_str}; border-left: 1px solid {Theme.get_border(accent)};")
        
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ background-color: {sb_bg_str}; border: none; }}
            QWidget#rightPanelScrollContainer {{ background-color: {sb_bg_str}; }}
            {scrollbar_style}
        """)

        self.scroll_container.setStyleSheet(f"""
            QWidget#rightPanelScrollContainer {{ background-color: {sb_bg_str}; color: {text}; }}
            QLabel {{ color: {text}; background: transparent; }}
            QLineEdit, QTextEdit {{
                background-color: {Theme.get_input_bg(accent)};
                border: 1px solid {Theme.get_input_border(accent)};
                border-radius: 4px;
                padding: 4px;
                color: {text};
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
                background-color: transparent;
                color: {text};
                border: 1px solid {Theme.get_border(accent)};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QPushButton#btnClearBulkTags:hover {{
                background-color: {Theme.get_btn_save_hover(accent)};
                color: {"#000" if is_light else "#fff"};
                border-color: {accent_str};
            }}
        """)
        
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

    def _update_app_style(self, accent: QColor) -> None:
        """Update global application styles like tinted native menus."""
        sb_bg = Theme.get_sidebar_bg(accent)
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        is_light = Theme.get_is_light()
        highlight_bg = Theme.get_accent_soft(accent)
        
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
            if hasattr(self, "left_sections_splitter"):
                self.bridge.settings.setValue("ui/left_sections_splitter_state", self.left_sections_splitter.saveState())
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
                    
                if not is_right_panel:
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
            # In inplace mode, the geometry is set by JS, so we don't want to reset it here.
            # Only reset if it's in full overlay mode.
            if not self.video_overlay.is_inplace_mode():
                self.video_overlay.setGeometry(self.web.rect())
            self.video_overlay.raise_()

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
            "# MediaManagerX\n\n"
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

        self._show_themed_dialog("About MediaManagerX", info, is_markdown=True)

    def _show_markdown_dialog(self, title: str, file_name: str) -> None:
        """Helper to show a markdown file in a scrollable dialog."""
        try:
            # In a PyInstaller bundle, data files are at sys._MEIPASS root.
            # At dev time, they live in the same directory as main.py.
            if getattr(sys, 'frozen', False):
                path = Path(sys._MEIPASS) / file_name
            else:
                path = Path(__file__).parent / file_name
            if not path.exists():
                QMessageBox.warning(self, title, f"File not found: {file_name}")
                return
            
            content = path.read_text(encoding="utf-8")
            self._show_themed_dialog(title, content, is_markdown=True)
        except Exception as e:
            QMessageBox.critical(self, title, f"Error loading {file_name}: {e}")

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
            QTextEdit {{
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
        self._show_markdown_dialog("What's New", "CHANGELOG.md")

    def show_search_syntax_help(self) -> None:
        self._show_markdown_dialog("Search Syntax Help", "SEARCH_SYNTAX.md")

    def _on_update_available(self, version: str, manual: bool) -> None:
        """Handled in web frontend (toast popup)."""
        pass

    def _on_update_error(self, message: str) -> None:
        QMessageBox.warning(self, "Update Error", message)


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
