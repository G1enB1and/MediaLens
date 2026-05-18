from __future__ import annotations

import ctypes
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native.mediamanagerx_app.theme_dialogs import Theme


class ActionHistoryDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.bridge = main_window.bridge
        self.setWindowTitle("Action History")
        self.setMinimumSize(980, 620)
        self._entries: list[dict] = []
        self._selected_entry_id = 0
        self._validation_completed = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh)
        self._build_ui()
        self._apply_theme()
        QTimer.singleShot(0, self._apply_title_bar_theme)
        try:
            self.bridge.actionHistoryChanged.connect(self._schedule_refresh)
        except Exception:
            pass
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        for label, value in (
            ("All", "all"),
            ("Delete", "delete"),
            ("Move", "move"),
            ("Copy", "copy"),
            ("Rename", "rename"),
            ("Create", "create_folder"),
            ("Metadata", "metadata"),
            ("Hidden", "hidden"),
            ("Rotate", "rotate"),
            ("Undo", "undo"),
            ("Redo", "redo"),
        ):
            self.filter_combo.addItem(label, value)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search file or path")
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        toolbar.addWidget(self.filter_combo)
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(self.undo_btn)
        toolbar.addWidget(self.redo_btn)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.entries_table = QTableWidget(0, 5)
        self.entries_table.setHorizontalHeaderLabels(["Time", "Action", "Items", "Path", "Status"])
        self.entries_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entries_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.entries_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.entries_table.verticalHeader().setVisible(False)
        header = self.entries_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self.entries_table)

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 8, 0, 0)
        self.details_title = QLabel("Select an action")
        self.details_title.setObjectName("historyDetailsTitle")
        self.details_meta = QLabel("")
        self.details_meta.setObjectName("historyDetailsMeta")
        self.details_meta.setWordWrap(True)
        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_meta)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["Item", "From", "To", "State", "Action"])
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        item_header = self.items_table.horizontalHeader()
        item_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        item_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        item_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        item_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        item_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        details_layout.addWidget(self.items_table, 1)
        splitter.addWidget(details)
        splitter.setSizes([340, 240])
        root.addWidget(splitter, 1)

        self.filter_combo.currentIndexChanged.connect(self.refresh)
        self.search_edit.textChanged.connect(self._schedule_refresh)
        self.undo_btn.clicked.connect(self._undo)
        self.redo_btn.clicked.connect(self._redo)
        self.entries_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _apply_theme(self) -> None:
        accent = QColor(str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))
        bg = Theme.get_bg(accent)
        control_bg = Theme.get_control_bg(accent)
        hover_bg = Theme.get_btn_save_hover(accent)
        input_bg = Theme.get_input_bg(accent)
        scrollbar_track = Theme.get_scrollbar_track(accent)
        scrollbar_thumb = Theme.get_scrollbar_thumb(accent)
        scrollbar_thumb_hover = Theme.get_scrollbar_thumb_hover(accent)
        text = Theme.get_text_color()
        muted = Theme.get_text_muted()
        border = Theme.get_border(accent)
        accent_str = accent.name()
        selection_text = Theme.get_contrast_text(accent)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg))
        palette.setColor(QPalette.ColorRole.Base, QColor(control_bg))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(input_bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(text))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
        palette.setColor(QPalette.ColorRole.Button, QColor(control_bg))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(selection_text))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"""
            ActionHistoryDialog, QDialog {{ background-color: {bg}; color: {text}; }}
            QWidget {{ background-color: {bg}; color: {text}; }}
            QLabel {{ color: {text}; background: transparent; }}
            QLabel#historyDetailsTitle {{ font-size: 16px; font-weight: bold; }}
            QLabel#historyDetailsMeta {{ color: {muted}; }}
            QLineEdit, QComboBox {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {accent_str};
            }}
            QComboBox QAbstractItemView {{
                background-color: {control_bg};
                color: {text};
                border: 1px solid {border};
                selection-background-color: {accent_str};
                selection-color: {selection_text};
            }}
            QPushButton {{
                background-color: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; border-color: {accent_str}; color: {text}; }}
            QPushButton:disabled {{ color: {muted}; border-color: {border}; background-color: transparent; }}
            QSplitter::handle {{
                background-color: {border};
            }}
            QSplitter::handle:hover {{
                background-color: {accent_str};
            }}
            QTableWidget {{
                background-color: {control_bg};
                alternate-background-color: {input_bg};
                color: {text};
                gridline-color: {border};
                border: 1px solid {border};
                border-radius: 6px;
                selection-background-color: {accent_str};
                selection-color: {selection_text};
                outline: 0;
            }}
            QTableWidget::item {{
                background-color: transparent;
                color: {text};
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {accent_str};
                color: {selection_text};
            }}
            QTableCornerButton::section {{
                background-color: {bg};
                border: none;
                border-bottom: 1px solid {border};
                border-right: 1px solid {border};
            }}
            QHeaderView::section {{
                background-color: {bg};
                color: {text};
                border: none;
                border-bottom: 1px solid {border};
                padding: 6px;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {scrollbar_track};
                border: none;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {scrollbar_thumb};
                border-radius: 4px;
                min-height: 24px;
                min-width: 24px;
            }}
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
                background: {scrollbar_thumb_hover};
            }}
        """)
        for table in (self.entries_table, self.items_table):
            table.setAlternatingRowColors(True)
            table.viewport().setAutoFillBackground(True)
            table.viewport().setPalette(palette)
        self._apply_title_bar_theme()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_title_bar_theme()

    def _apply_title_bar_theme(self) -> None:
        if sys.platform != "win32" or not self.isVisible():
            return
        try:
            is_dark = not Theme.get_is_light()
            bg_color = QColor(Theme.get_bg(QColor(str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))))
            hwnd = int(self.winId())
            value = ctypes.c_int(1 if is_dark else 0)
            for attribute in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attribute,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )

            bg_ref = (bg_color.blue() << 16) | (bg_color.green() << 8) | bg_color.red()
            fg_ref = 0x00000000 if not is_dark else 0x00FFFFFF
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                35,
                ctypes.byref(ctypes.c_int(bg_ref)),
                ctypes.sizeof(ctypes.c_int(bg_ref)),
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                36,
                ctypes.byref(ctypes.c_int(fg_ref)),
                ctypes.sizeof(ctypes.c_int(fg_ref)),
            )
        except Exception:
            pass

    def _schedule_refresh(self) -> None:
        self._refresh_timer.start(150)

    def refresh(self) -> None:
        if not self._validation_completed:
            self._validation_completed = True
            try:
                self.bridge.validate_action_history(150)
            except Exception:
                pass
        action_type = str(self.filter_combo.currentData() or "all")
        search = self.search_edit.text().strip()
        self._entries = list(self.bridge.list_action_history(action_type, search, 300) or [])
        self.entries_table.setRowCount(0)
        for row_idx, entry in enumerate(self._entries):
            self.entries_table.insertRow(row_idx)
            values = [
                self._format_time(str(entry.get("timestamp_utc") or "")),
                str(entry.get("summary") or ""),
                str(entry.get("item_count") or 0),
                self._entry_path_summary(entry),
                self._status_text(entry),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, int(entry.get("id") or 0))
                self.entries_table.setItem(row_idx, col, item)
        self._sync_buttons()
        self._restore_selection()

    def _restore_selection(self) -> None:
        if not self._selected_entry_id and self.entries_table.rowCount() > 0:
            self.entries_table.selectRow(0)
            return
        for row in range(self.entries_table.rowCount()):
            item = self.entries_table.item(row, 0)
            if item and int(item.data(Qt.ItemDataRole.UserRole) or 0) == self._selected_entry_id:
                self.entries_table.selectRow(row)
                return
        self._load_details(0)

    def _sync_buttons(self) -> None:
        state = self.bridge.get_action_history_state()
        self.undo_btn.setEnabled(bool(state.get("can_undo")))
        self.redo_btn.setEnabled(bool(state.get("can_redo")))

    def _on_selection_changed(self) -> None:
        rows = self.entries_table.selectionModel().selectedRows()
        entry_id = 0
        if rows:
            item = self.entries_table.item(rows[0].row(), 0)
            entry_id = int(item.data(Qt.ItemDataRole.UserRole) or 0) if item else 0
        self._selected_entry_id = entry_id
        self._load_details(entry_id)

    def _load_details(self, entry_id: int) -> None:
        entry = next((row for row in self._entries if int(row.get("id") or 0) == int(entry_id)), None)
        if not entry:
            self.details_title.setText("Select an action")
            self.details_meta.setText("")
            self.items_table.setRowCount(0)
            return
        self.details_title.setText(str(entry.get("summary") or "Action"))
        items = list(self.bridge.list_action_history_items(int(entry_id)) or [])
        counts = self._item_state_counts(items)
        detail_parts = [
            self._format_time(str(entry.get("timestamp_utc") or ""), long=True),
            f"Status: {self._status_text(entry)}",
            self._counts_text(counts),
            f"Transaction: {entry.get('transaction_id')}",
        ]
        self.details_meta.setText(" | ".join(part for part in detail_parts if part))
        self.items_table.setRowCount(0)
        for row_idx, item in enumerate(items):
            self.items_table.insertRow(row_idx)
            name = Path(str(item.get("new_path") or item.get("old_path") or "")).name
            values = [
                name,
                str(item.get("old_path") or ""),
                str(item.get("new_path") or ""),
                self._item_state_text(item),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                self.items_table.setItem(row_idx, col, cell)
            action_widget = self._item_action_widget(item, entry)
            self.items_table.setCellWidget(row_idx, 4, action_widget)

    def _item_action_widget(self, item: dict, entry: dict) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        state = str(item.get("current_state") or "")
        undo = QPushButton("Undo")
        redo = QPushButton("Redo")
        entry_undo_state = str(entry.get("undo_state") or "")
        undo.setEnabled(state == "applied" and entry_undo_state != "not_undoable")
        redo.setEnabled(state == "undone")
        undo.clicked.connect(lambda _checked=False, item_id=int(item.get("id") or 0): self._undo_item(item_id))
        redo.clicked.connect(lambda _checked=False, item_id=int(item.get("id") or 0): self._redo_item(item_id))
        layout.addWidget(undo)
        layout.addWidget(redo)
        return box

    def _item_state_counts(self, items: list[dict]) -> dict[str, int]:
        counts = {"applied": 0, "undone": 0, "unavailable": 0, "failed": 0}
        for item in items:
            state = str(item.get("current_state") or "")
            if state in counts:
                counts[state] += 1
        return counts

    def _counts_text(self, counts: dict[str, int]) -> str:
        parts = []
        for key, label in (
            ("applied", "active"),
            ("undone", "undone"),
            ("unavailable", "unavailable"),
            ("failed", "failed"),
        ):
            value = int(counts.get(key) or 0)
            if value:
                parts.append(f"{value} {label}")
        return ", ".join(parts)

    def _undo(self) -> None:
        if self.bridge.undo_last_action():
            self._refresh_main_window()
            self.refresh()

    def _redo(self) -> None:
        if self.bridge.redo_last_action():
            self._refresh_main_window()
            self.refresh()

    def _undo_item(self, item_id: int) -> None:
        if self.bridge.undo_history_item(int(item_id)):
            self._refresh_main_window()
            self.refresh()

    def _redo_item(self, item_id: int) -> None:
        if self.bridge.redo_history_item(int(item_id)):
            self._refresh_main_window()
            self.refresh()

    def _refresh_main_window(self) -> None:
        if hasattr(self.main_window, "_refresh_current_folder"):
            self.main_window._refresh_current_folder()

    def _entry_path_summary(self, entry: dict) -> str:
        old_path = str(entry.get("first_old_path") or "")
        new_path = str(entry.get("first_new_path") or "")
        if old_path and new_path:
            return f"{Path(old_path).parent} -> {Path(new_path).parent}"
        return old_path or new_path

    def _status_text(self, entry: dict) -> str:
        status = str(entry.get("status") or "success").replace("_", " ").title()
        undo_state_raw = str(entry.get("undo_state") or "")
        undo_state = {
            "undoable": "Undoable",
            "redoable": "Redoable",
            "partially_undone": "Partially Undoable",
            "not_undoable": "Not Undoable",
        }.get(undo_state_raw, undo_state_raw.replace("_", " ").title())
        return f"{status} | {undo_state}" if undo_state else status

    def _item_state_text(self, item: dict) -> str:
        state_raw = str(item.get("current_state") or "")
        source_raw = str(item.get("last_change_source") or "")
        state = {
            "applied": "Active",
            "undone": "Undone",
            "unavailable": "Unavailable",
            "failed": "Failed",
        }.get(state_raw, state_raw.replace("_", " ").title())
        source = {
            "original_action": "Original action",
            "group_undo": "Group undo",
            "group_redo": "Group redo",
            "individual_undo": "Individual undo",
            "individual_redo": "Individual redo",
            "external_change": "External change",
        }.get(source_raw, source_raw.replace("_", " ").title())
        notes = str(item.get("notes") or "").strip()
        label = f"{state} | {source}" if source else state
        return f"{label} | {notes}" if notes else label

    def _format_time(self, value: str, *, long: bool = False) -> str:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %I:%M:%S %p") if long else dt.strftime("%m/%d %I:%M %p")
        except Exception:
            return value
