import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QMessageBox, QFrame, QSizePolicy
)

APP_NAME = "MediaLens"
LEGACY_APP_NAME = "MediaManagerX"
LEGACY_APP_ORGANIZATION = "G1enB1and"


# Shared with main, keeping it identical
def _appdata_runtime_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / "AppData" / "Roaming"
    out = root / APP_NAME
    legacy_candidates = [
        root / LEGACY_APP_ORGANIZATION / APP_NAME,
        root / LEGACY_APP_ORGANIZATION / LEGACY_APP_NAME,
    ]
    if not out.exists():
        for legacy in legacy_candidates:
            if not legacy.exists():
                continue
            try:
                shutil.move(str(legacy), str(out))
                break
            except Exception:
                try:
                    shutil.copytree(legacy, out, dirs_exist_ok=True)
                    break
                except Exception:
                    pass
    out.mkdir(parents=True, exist_ok=True)
    return out

def get_recycle_bin_dir() -> Path:
    bin_dir = _appdata_runtime_dir() / "RecycleBin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir

def get_recycle_bin_db_path() -> str:
    return str(_appdata_runtime_dir() / "recycle_bin.sqlite")

def init_recycle_bin_db():
    conn = sqlite3.connect(get_recycle_bin_db_path())
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recycle_bin (
            id TEXT PRIMARY KEY,
            original_path TEXT,
            archived_name TEXT,
            deleted_at DATETIME,
            expires_at DATETIME
        )
    ''')
    conn.commit()
    return conn

def auto_purge_recycle_bin():
    conn = init_recycle_bin_db()
    c = conn.cursor()
    c.execute("SELECT id, archived_name FROM recycle_bin WHERE expires_at < ?", (datetime.now().isoformat(),))
    rows = c.fetchall()
    
    bin_dir = get_recycle_bin_dir()
    for row_id, archived_name in rows:
        target_file = bin_dir / archived_name
        if target_file.exists():
            try:
                if target_file.is_dir():
                    shutil.rmtree(target_file)
                else:
                    target_file.unlink()
            except Exception: pass
        c.execute("DELETE FROM recycle_bin WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()

def move_to_recycle_bin(original_path: str, days: int) -> bool:
    try:
        p = Path(original_path)
        if not p.exists(): return False
        
        bin_dir = get_recycle_bin_dir()
        file_id = str(uuid.uuid4())
        archived_name = f"{file_id}_{p.name}"
        target_path = bin_dir / archived_name
        
        # Use shutil move to handle cross-drive moving safely
        shutil.move(str(p.resolve()), str(target_path))
        
        deleted_at = datetime.now()
        expires_at = deleted_at + timedelta(days=days)
        
        conn = init_recycle_bin_db()
        conn.execute('''
            INSERT INTO recycle_bin (id, original_path, archived_name, deleted_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (file_id, str(p.resolve()), archived_name, deleted_at.isoformat(), expires_at.isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def restore_from_recycle_bin(file_id: str) -> bool:
    try:
        conn = init_recycle_bin_db()
        c = conn.cursor()
        c.execute("SELECT original_path, archived_name FROM recycle_bin WHERE id = ?", (file_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        
        orig, arch = row
        bin_dir = get_recycle_bin_dir()
        arch_path = bin_dir / arch
        
        if arch_path.exists():
            orig_p = Path(orig)
            orig_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(arch_path), str(orig_p))
        
        c.execute("DELETE FROM recycle_bin WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def permanent_delete_from_recycle_bin(file_id: str) -> bool:
    try:
        conn = init_recycle_bin_db()
        c = conn.cursor()
        c.execute("SELECT archived_name FROM recycle_bin WHERE id = ?", (file_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
            
        arch = row[0]
        bin_dir = get_recycle_bin_dir()
        arch_path = bin_dir / arch
        
        if arch_path.exists():
            if arch_path.is_dir():
                shutil.rmtree(arch_path)
            else:
                arch_path.unlink()
                
        c.execute("DELETE FROM recycle_bin WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def restore_all() -> int:
    conn = init_recycle_bin_db()
    c = conn.cursor()
    c.execute("SELECT id FROM recycle_bin")
    rows = c.fetchall()
    conn.close()
    
    count = 0
    for r in rows:
        if restore_from_recycle_bin(r[0]):
            count += 1
    return count

def empty_all() -> int:
    conn = init_recycle_bin_db()
    c = conn.cursor()
    c.execute("SELECT id FROM recycle_bin")
    rows = c.fetchall()
    conn.close()
    
    count = 0
    for r in rows:
        if permanent_delete_from_recycle_bin(r[0]):
            count += 1
    return count

# UI Classes
from native.mediamanagerx_app.main import Theme
from PySide6.QtCore import QSettings

def _get_accent() -> QColor:
    s = QSettings(str(_appdata_runtime_dir() / "settings.ini"), QSettings.Format.IniFormat)
    return QColor(str(s.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))

class RecycleBinItemWidget(QFrame):
    restoreClicked = Signal(str)
    deleteClicked = Signal(str)
    
    def __init__(self, file_id, original_path, archived_name, deleted_at, expires_at, parent=None):
        super().__init__(parent)
        self.file_id = file_id
        self.original_path = original_path
        
        accent = _get_accent()
        bg = Theme.get_control_bg(accent)
        border = Theme.get_border(accent)
        self.text_color = Theme.get_text_color()
        self.muted_color = Theme.get_text_muted()
        accent_str = accent.name()
        self.close_bg = Theme.get_btn_save_bg(accent)
        self.close_hover = Theme.get_btn_save_hover(accent)
        self.border_color = border
        
        self.setStyleSheet(f"""
            RecycleBinItemWidget {{
                background-color: {bg};
                border-radius: 8px;
                border: 1px solid {border};
            }}
            RecycleBinItemWidget:hover {{
                border: 1px solid {accent_str};
            }}
        """)
        self.setFixedSize(280, 260)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Image preview
        bin_dir = get_recycle_bin_dir()
        arch_path = bin_dir / archived_name
        
        preview_label = QLabel()
        preview_label.setFixedSize(260, 140)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setStyleSheet("background-color: #1a1a1c; border-radius: 4px;")
        
        if arch_path.exists():
            pix = QPixmap(str(arch_path))
            if not pix.isNull():
                preview_label.setPixmap(pix.scaled(260, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                preview_label.setText("No Preview")
                preview_label.setStyleSheet("color: #60656f; background-color: #1a1a1c;")
        else:
            preview_label.setText("File Missing")
            preview_label.setStyleSheet("color: #d32f2f; background-color: #1a1a1c;")

        layout.addWidget(preview_label)
        
        # Details
        name_label = QLabel(Path(original_path).name)
        name_label.setStyleSheet(f"color: {self.text_color}; font-weight: bold; font-size: 14px; background: transparent;")
        
        path_label = QLabel(str(Path(original_path).parent))
        path_label.setStyleSheet(f"color: {self.muted_color}; font-size: 11px; background: transparent;")
        path_label.setWordWrap(True)
        
        d = datetime.fromisoformat(deleted_at)
        e = datetime.fromisoformat(expires_at)
        time_label = QLabel(f"Deleted: {d.strftime('%Y-%m-%d')} | Expires: {e.strftime('%Y-%m-%d')}")
        time_label.setStyleSheet(f"color: {self.muted_color}; font-size: 11px; background: transparent;")
        
        layout.addWidget(name_label)
        layout.addWidget(path_label)
        layout.addStretch(1)
        layout.addWidget(time_label)
        
        btn_layout = QHBoxLayout()
        restore_btn = QPushButton("Restore")
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {self.close_bg}; color: {self.text_color}; border: 1px solid {self.border_color}; border-radius: 4px; padding: 4px; }}
            QPushButton:hover {{ background-color: {self.close_hover}; border-color: {accent_str}; }}
        """)
        restore_btn.clicked.connect(lambda: self.restoreClicked.emit(self.file_id))
        
        del_btn = QPushButton("Delete Now")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{ background-color: #d32f2f; color: white; border: 1px solid #d32f2f; border-radius: 4px; padding: 4px; }}
            QPushButton:hover {{ background-color: #b71c1c; border-color: white; }}
        """)
        del_btn.clicked.connect(lambda: self.deleteClicked.emit(self.file_id))
        
        btn_layout.addWidget(restore_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

class RecycleBinViewerWindow(QMainWindow):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("MediaLens Recycle Bin")
        self.setMinimumSize(800, 600)
        
        accent = _get_accent()
        bg = Theme.get_bg(accent)
        text = Theme.get_text_color()
        border = Theme.get_border(accent)
        muted = Theme.get_text_muted()
        close_bg = Theme.get_btn_save_bg(accent)
        close_hover = Theme.get_btn_save_hover(accent)
        accent_str = accent.name()
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg}; color: {text}; }}
            QWidget {{ background-color: {bg}; color: {text}; }}
            QPushButton {{
                background-color: {close_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {close_hover};
                border-color: {accent_str};
            }}
            QPushButton:disabled {{
                background-color: transparent;
                color: {muted};
                border: 1px solid {border};
            }}
            QScrollArea {{ border: none; background: transparent; }}
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        
        header_layout = QHBoxLayout()
        title = QLabel("Recycle Bin")
        title.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent;")
        
        self.restore_all_btn = QPushButton("Restore All")
        self.restore_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_all_btn.clicked.connect(self._restore_all)
        self.empty_all_btn = QPushButton("Empty Now")
        self.empty_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_all_btn.setStyleSheet(f"""
            QPushButton {{ background-color: #d32f2f; color: white; border: 1px solid #d32f2f; border-radius: 6px; padding: 6px 12px; }}
            QPushButton:hover {{ background-color: #b71c1c; border-color: white; }}
            QPushButton:disabled {{ background-color: transparent; color: {muted}; border: 1px solid {border}; }}
        """)
        self.empty_all_btn.clicked.connect(self._empty_all)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.restore_all_btn)
        header_layout.addWidget(self.empty_all_btn)
        
        self.central_layout.addLayout(header_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        self.scroll_widget = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.grid_layout = QGridLayout()
        self.grid_widget = QWidget()
        self.grid_widget.setLayout(self.grid_layout)
        self.scroll_layout.addWidget(self.grid_widget)
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.central_layout.addWidget(self.scroll_area)
        
        self.load_items()

    def load_items(self):
        # Clear layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        conn = init_recycle_bin_db()
        c = conn.cursor()
        c.execute("SELECT id, original_path, archived_name, deleted_at, expires_at FROM recycle_bin ORDER BY deleted_at DESC")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            lbl = QLabel("Recycle Bin is empty.")
            lbl.setStyleSheet("color: #b4b7bd; font-size: 16px;")
            self.grid_layout.addWidget(lbl, 0, 0)
            self.restore_all_btn.setEnabled(False)
            self.empty_all_btn.setEnabled(False)
            return

        self.restore_all_btn.setEnabled(True)
        self.empty_all_btn.setEnabled(True)
        
        col_count = 3
        for i, row in enumerate(rows):
            w = RecycleBinItemWidget(*row, parent=self)
            w.restoreClicked.connect(self._restore_item)
            w.deleteClicked.connect(self._delete_item)
            self.grid_layout.addWidget(w, i // col_count, i % col_count)

    def _restore_item(self, file_id):
        if restore_from_recycle_bin(file_id):
            self.load_items()
            if self.main_window:
                self.main_window.bridge._disk_cache = {}
                self.main_window.bridge._disk_cache_key = ""
                self.main_window.bridge.collectionsChanged.emit()
                if hasattr(self.main_window, '_refresh_current_folder'):
                    self.main_window._refresh_current_folder()

    def _delete_item(self, file_id):
        if permanent_delete_from_recycle_bin(file_id):
            self.load_items()

    def _restore_all(self):
        reply = QMessageBox.question(self, "Restore All", "Are you sure you want to restore all files to their original locations?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            restore_all()
            self.load_items()
            if self.main_window:
                self.main_window.bridge._disk_cache = {}
                self.main_window.bridge._disk_cache_key = ""
                self.main_window.bridge.collectionsChanged.emit()
                if hasattr(self.main_window, '_refresh_current_folder'):
                    self.main_window._refresh_current_folder()

    def _empty_all(self):
        reply = QMessageBox.question(self, "Empty Now", "Are you sure you want to permanently delete all files in the MediaLens recycle bin?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            empty_all()
            self.load_items()
