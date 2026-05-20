from __future__ import annotations

import ctypes
import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPalette, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QSplitter,
    QFrame,
    QStyledItemDelegate,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from native.mediamanagerx_app.theme_dialogs import Theme


class _HistoryFilterComboDelegate(QStyledItemDelegate):
    def __init__(self, bridge, combo: QComboBox, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.combo = combo

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), option.fontMetrics.height() + 12))
        return size

    def paint(self, painter: QPainter, option, index) -> None:
        accent = QColor(str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))
        is_light = Theme.get_is_light()
        text_color = QColor(Theme.get_text_color())
        muted = QColor(Theme.get_text_muted())
        combo_bg = QColor("#ffffff" if is_light else Theme.mix(Theme.get_control_bg(accent), "#000000", 0.12))
        hover_bg = QColor(Theme.mix(combo_bg.name(), "#000000" if is_light else "#ffffff", 0.04 if is_light else 0.07))
        selected_text = QColor(Theme.mix(Theme.get_text_color(), accent, 0.76))
        is_current = index.row() == self.combo.currentIndex()
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(option.rect, hover_bg if is_hover and not is_current else combo_bg)

        font = option.font
        font.setBold(is_current)
        painter.setFont(font)
        painter.setPen(selected_text if is_current else (text_color if index.flags() & Qt.ItemFlag.ItemIsEnabled else muted))
        text_rect = option.rect.adjusted(12, 4, -12, -4)
        text = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
            Qt.TextElideMode.ElideRight,
            max(0, text_rect.width()),
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()


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
        self.filter_combo.setObjectName("historyFilterCombo")
        self.filter_combo.setMinimumWidth(126)
        self.filter_combo.setToolTip("Filter action history by action type")
        self.filter_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        filter_view = QListView(self.filter_combo)
        filter_view.setObjectName("historyFilterComboPopup")
        filter_view.setFrameShape(QFrame.Shape.NoFrame)
        filter_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        filter_view.setUniformItemSizes(True)
        filter_view.setMouseTracking(True)
        filter_view.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        filter_view.setStyleSheet("""
            QListView#historyFilterComboPopup {
                outline: 0;
                border: none;
            }
            QListView#historyFilterComboPopup::item,
            QListView#historyFilterComboPopup::item:selected,
            QListView#historyFilterComboPopup::item:hover,
            QListView#historyFilterComboPopup::item:focus {
                border: none;
                outline: 0;
                background: transparent;
            }
        """)
        self.filter_combo.setView(filter_view)
        self.filter_combo.setItemDelegate(_HistoryFilterComboDelegate(self.bridge, self.filter_combo, filter_view))
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
        self.search_edit.setToolTip("Search action history by file name or path")
        self.undo_btn = QPushButton("Undo Latest")
        self.undo_btn.setToolTip("Undo the most recent undoable action in history")
        self.redo_btn = QPushButton("Redo Latest")
        self.redo_btn.setToolTip("Redo the most recent action that was undone")
        self._sync_button_cursor(self.undo_btn)
        self._sync_button_cursor(self.redo_btn)
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
        self.details_summary = QLabel("")
        self.details_summary.setObjectName("historyDetailsSummary")
        self.details_summary.setWordWrap(True)
        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_meta)
        details_layout.addWidget(self.details_summary)

        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["Item", "Change", "Status", "Action"])
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(42)
        item_header = self.items_table.horizontalHeader()
        item_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        item_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        item_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        item_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.items_table.setColumnWidth(3, 180)
        details_layout.addWidget(self.items_table, 1)
        splitter.addWidget(details)
        splitter.setSizes([340, 240])
        root.addWidget(splitter, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.delete_all_btn = QPushButton("Delete All Action History")
        self.delete_all_btn.setObjectName("historyDeleteAllButton")
        self.delete_all_btn.setToolTip("Permanently remove all action history entries")
        self._sync_button_cursor(self.delete_all_btn)
        trash_icon = Path(__file__).with_name("web") / "icons" / "trash-red.svg"
        if trash_icon.exists():
            self.delete_all_btn.setIcon(QIcon(str(trash_icon)))
        footer.addWidget(self.delete_all_btn)
        root.addLayout(footer)

        self.filter_combo.currentIndexChanged.connect(self.refresh)
        self.search_edit.textChanged.connect(self._schedule_refresh)
        self.undo_btn.clicked.connect(self._undo)
        self.redo_btn.clicked.connect(self._redo)
        self.delete_all_btn.clicked.connect(self._delete_all_history)
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
        is_light = Theme.get_is_light()
        selection_text = Theme.get_contrast_text(accent)
        combo_bg = "#ffffff" if is_light else Theme.mix(control_bg, "#000000", 0.12)
        combo_arrow_svg = (
            Path(__file__).with_name("web")
            / "icons"
            / ("chevron-down-dark.svg" if is_light else "chevron-down-light.svg")
        ).as_posix()
        danger = "#dc2626" if is_light else "#f87171"
        danger_bg = Theme.mix(bg, danger, 0.10 if is_light else 0.18)
        danger_hover = Theme.mix(bg, danger, 0.18 if is_light else 0.26)
        disabled_bg = Theme.mix(control_bg, "#000000" if is_light else "#ffffff", 0.08 if is_light else 0.06)
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
            QLabel#historyDetailsSummary {{
                color: {text};
                background-color: {input_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 10px;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QLineEdit:focus {{
                border-color: {accent_str};
            }}
            QComboBox#historyFilterCombo {{
                background-color: {combo_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                min-height: 34px;
                padding: 0px 32px 0px 10px;
            }}
            QComboBox#historyFilterCombo:hover, QComboBox#historyFilterCombo:focus {{
                border-color: {accent_str};
            }}
            QComboBox#historyFilterCombo:on {{
                border-color: {accent_str};
                border-bottom-color: transparent;
                border-radius: 6px 6px 0px 0px;
            }}
            QComboBox#historyFilterCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                background: transparent;
            }}
            QComboBox#historyFilterCombo::down-arrow {{
                image: url("{combo_arrow_svg}");
                width: 12px;
                height: 12px;
            }}
            QComboBox#historyFilterCombo QAbstractItemView {{
                background-color: {combo_bg};
                color: {text};
                border: 1px solid {border};
                border-top: none;
                border-radius: 0px 0px 6px 6px;
                selection-background-color: {accent_str};
                selection-color: {selection_text};
                outline: 0;
                padding: 4px;
            }}
            QPushButton {{
                background-color: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; border-color: {accent_str}; color: {text}; }}
            QPushButton:disabled {{ color: {muted}; border-color: {border}; background-color: {disabled_bg}; }}
            QPushButton#historyDeleteAllButton {{
                background-color: {danger_bg};
                color: {danger};
                border-color: {danger};
                padding: 6px 12px;
            }}
            QPushButton#historyDeleteAllButton:hover {{
                background-color: {danger_hover};
                border-color: {danger};
                color: {danger};
            }}
            QPushButton#historyDeleteAllButton:disabled {{
                background-color: {disabled_bg};
                color: {muted};
                border-color: {border};
            }}
            QWidget#historyItemActionCell {{
                background: transparent;
            }}
            QPushButton#historyItemActionButton {{
                min-height: 22px;
                padding: 2px 10px;
                border-radius: 5px;
            }}
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
        self.delete_all_btn.setEnabled(bool(self._entries))
        self._sync_button_cursor(self.undo_btn)
        self._sync_button_cursor(self.redo_btn)
        self._sync_button_cursor(self.delete_all_btn)

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
            self.details_summary.setText("")
            self.items_table.setRowCount(0)
            return
        self.details_title.setText(str(entry.get("summary") or "Action"))
        items = list(self.bridge.list_action_history_items(int(entry_id)) or [])
        counts = self._item_state_counts(items)
        detail_parts = [
            self._format_time(str(entry.get("timestamp_utc") or ""), long=True),
            self._status_text(entry),
            self._counts_text(counts),
        ]
        self.details_meta.setText(" | ".join(part for part in detail_parts if part))
        self.details_summary.setText(self._entry_detail_text(entry, items))
        self.items_table.setRowCount(0)
        for row_idx, item in enumerate(items):
            self.items_table.insertRow(row_idx)
            self.items_table.setRowHeight(row_idx, 42)
            name = Path(str(item.get("new_path") or item.get("old_path") or "")).name
            values = [
                name,
                self._item_change_text(entry, item),
                self._item_state_text(item),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                self.items_table.setItem(row_idx, col, cell)
            action_widget = self._item_action_widget(item, entry)
            self.items_table.setCellWidget(row_idx, 3, action_widget)

    def _item_action_widget(self, item: dict, entry: dict) -> QWidget:
        box = QWidget()
        box.setObjectName("historyItemActionCell")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)
        state = str(item.get("current_state") or "")
        undo = QPushButton("Undo")
        redo = QPushButton("Redo")
        undo.setObjectName("historyItemActionButton")
        redo.setObjectName("historyItemActionButton")
        undo.setFixedHeight(30)
        redo.setFixedHeight(30)
        undo.setMinimumWidth(74)
        redo.setMinimumWidth(74)
        undo.setToolTip("Undo this item from the selected action")
        redo.setToolTip("Redo this item from the selected action")
        entry_undo_state = str(entry.get("undo_state") or "")
        undo.setEnabled(state == "applied" and entry_undo_state != "not_undoable")
        redo.setEnabled(state == "undone")
        self._sync_button_cursor(undo)
        self._sync_button_cursor(redo)
        undo.clicked.connect(lambda _checked=False, item_id=int(item.get("id") or 0): self._undo_item(item_id))
        redo.clicked.connect(lambda _checked=False, item_id=int(item.get("id") or 0): self._redo_item(item_id))
        layout.addWidget(undo)
        layout.addWidget(redo)
        return box

    @staticmethod
    def _sync_button_cursor(button: QPushButton) -> None:
        button.setCursor(
            Qt.CursorShape.PointingHandCursor
            if button.isEnabled()
            else Qt.CursorShape.ForbiddenCursor
        )

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
            ("applied", "current"),
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

    def _delete_all_history(self) -> None:
        if not self._entries:
            return
        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle("Delete All Action History")
        confirm.setText("Delete all action history?")
        confirm.setInformativeText("This removes the undo and redo history for previous actions.")
        delete_btn = confirm.addButton("Delete All", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = confirm.addButton(QMessageBox.StandardButton.Cancel)
        confirm.setDefaultButton(cancel_btn)
        confirm.exec()
        if confirm.clickedButton() is not delete_btn:
            return
        try:
            self.bridge.delete_all_action_history()
        except Exception:
            return
        self._selected_entry_id = 0
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

    def _entry_detail_text(self, entry: dict, items: list[dict]) -> str:
        action_type = str(entry.get("action_type") or "")
        if not items:
            return "This history entry records a system action and does not contain individual file changes."
        if len(items) == 1:
            return self._single_item_detail_text(entry, items[0])
        counts = self._item_state_counts(items)
        item_label = "item" if len(items) == 1 else "items"
        status = self._plain_entry_state(entry, counts)
        sample_changes = [self._item_change_text(entry, item) for item in items[:3]]
        change_text = "; ".join(change for change in sample_changes if change)
        if len(items) > 3:
            change_text = f"{change_text}; and {len(items) - 3} more" if change_text else f"{len(items) - 3} more changes"
        action_label = {
            "delete": "deleted",
            "move": "moved",
            "copy": "copied",
            "rename": "renamed",
            "create_folder": "created",
            "metadata": "edited",
            "hidden": "changed visibility for",
            "rotate": "rotated",
            "undo": "undid",
            "redo": "redid",
        }.get(action_type, "changed")
        return f"This action {action_label} {len(items)} {item_label}. {status}. {change_text}"

    def _single_item_detail_text(self, entry: dict, item: dict) -> str:
        name = self._item_name(item)
        change = self._item_change_text(entry, item)
        state = self._plain_item_state(item)
        action = self._available_action_text(entry, item)
        return f"{name}: {change}. {state}. {action}"

    def _item_change_text(self, entry: dict, item: dict) -> str:
        action_type = str(entry.get("action_type") or "")
        old_path = str(item.get("old_path") or "")
        new_path = str(item.get("new_path") or "")
        name = self._item_name(item)
        if action_type == "metadata":
            return self._metadata_change_text(entry, item)
        if action_type == "hidden":
            return self._hidden_change_text(item)
        if action_type == "rotate":
            return self._rotate_change_text(item)
        if action_type == "delete":
            return f"Deleted from {self._parent_text(old_path)}"
        if action_type == "move":
            return f"Moved from {self._parent_text(old_path)} to {self._parent_text(new_path)}"
        if action_type == "copy":
            return f"Copied from {self._parent_text(old_path)} to {self._parent_text(new_path)}"
        if action_type == "rename":
            return f"Renamed from {Path(old_path).name or old_path} to {Path(new_path).name or new_path}"
        if action_type == "create_folder":
            return f"Created folder at {new_path or name}"
        if action_type == "undo":
            return str(entry.get("summary") or "Undid an earlier action")
        if action_type == "redo":
            return str(entry.get("summary") or "Redid an earlier action")
        return str(item.get("notes") or entry.get("summary") or "Changed")

    def _metadata_change_text(self, entry: dict, item: dict) -> str:
        payload = self._metadata_payload(item)
        old = dict(payload.get("old") or {})
        new = dict(payload.get("new") or {})
        scope = self._metadata_scope(entry)
        changes = self._metadata_change_phrases(old, new, scope=scope)
        if not changes:
            if scope == "description":
                return "Description was edited"
            if scope == "tags":
                return "Tags were edited"
            if scope == "ocr":
                return "OCR text was edited"
            notes = str(item.get("notes") or "").strip()
            return f"Edited {notes}" if notes else "Edited metadata"
        return "; ".join(changes[:3]) + (f"; and {len(changes) - 3} more" if len(changes) > 3 else "")

    @staticmethod
    def _metadata_scope(entry: dict) -> str:
        summary = str(entry.get("summary") or "").strip().casefold()
        if "description" in summary:
            return "description"
        if "tag" in summary:
            return "tags"
        if "text ocr" in summary or "ocr text" in summary:
            return "ocr"
        return "all"

    def _metadata_change_phrases(self, old: dict, new: dict, *, scope: str = "all") -> list[str]:
        phrases: list[str] = []
        if scope == "description":
            old_description, new_description = self._description_values(old, new)
            if self._compare_value(old_description) != self._compare_value(new_description):
                return [f"Description changed from {self._format_value(old_description)} to {self._format_value(new_description)}"]
        if scope in {"all", "tags"} and self._compare_value(old.get("tags")) != self._compare_value(new.get("tags")):
            phrases.append(f"Tags changed from {self._format_value(old.get('tags'))} to {self._format_value(new.get('tags'))}")
        metadata_labels = (
            ("title", "Title"),
            ("description", "Description"),
            ("notes", "Notes"),
            ("embedded_tags", "Embedded tags"),
            ("embedded_comments", "Embedded comments"),
            ("ai_prompt", "AI prompt"),
            ("ai_negative_prompt", "Negative prompt"),
            ("ai_params", "AI parameters"),
        )
        old_metadata = dict(old.get("metadata") or {})
        new_metadata = dict(new.get("metadata") or {})
        for key, label in metadata_labels:
            if scope == "description" and key != "description":
                continue
            if scope in {"tags", "ocr"}:
                continue
            if self._compare_value(old_metadata.get(key)) != self._compare_value(new_metadata.get(key)):
                phrases.append(f"{label} changed from {self._format_value(old_metadata.get(key))} to {self._format_value(new_metadata.get(key))}")
        media_labels = (
            ("detected_text", "OCR text"),
            ("user_confirmed_text_detected", "Text detected"),
            ("exif_date_taken", "EXIF date"),
            ("metadata_date", "Metadata date"),
        )
        old_media = dict(old.get("media") or {})
        new_media = dict(new.get("media") or {})
        for key, label in media_labels:
            if scope == "ocr" and key != "detected_text":
                continue
            if scope in {"description", "tags"}:
                continue
            if self._compare_value(old_media.get(key)) != self._compare_value(new_media.get(key)):
                phrases.append(f"{label} changed from {self._format_value(old_media.get(key))} to {self._format_value(new_media.get(key))}")
        if scope == "description":
            old_ai = dict(old.get("ai") or {})
            new_ai = dict(new.get("ai") or {})
            if self._compare_value(old_ai.get("description")) != self._compare_value(new_ai.get("description")):
                phrases.append(f"Description changed from {self._format_value(old_ai.get('description'))} to {self._format_value(new_ai.get('description'))}")
        elif scope == "all" and self._compare_value(old.get("ai")) != self._compare_value(new.get("ai")):
            phrases.append("AI metadata changed")
        return phrases

    @staticmethod
    def _description_values(old: dict, new: dict) -> tuple[object, object]:
        old_visible = dict(old.get("visible") or {})
        new_visible = dict(new.get("visible") or {})
        if "description" in old_visible or "description" in new_visible:
            return old_visible.get("description"), new_visible.get("description")
        old_metadata = dict(old.get("metadata") or {})
        new_metadata = dict(new.get("metadata") or {})
        if ActionHistoryDialog._compare_value(old_metadata.get("description")) != ActionHistoryDialog._compare_value(new_metadata.get("description")):
            return old_metadata.get("description"), new_metadata.get("description")
        old_ai = dict(old.get("ai") or {})
        new_ai = dict(new.get("ai") or {})
        return old_ai.get("description"), new_ai.get("description")

    def _hidden_change_text(self, item: dict) -> str:
        payload = self._metadata_payload(item)
        old_hidden = bool(payload.get("old_hidden"))
        new_hidden = bool(payload.get("new_hidden"))
        if old_hidden == new_hidden:
            return "Visibility was checked"
        return "Changed visibility from hidden to visible" if old_hidden else "Changed visibility from visible to hidden"

    def _rotate_change_text(self, item: dict) -> str:
        payload = self._metadata_payload(item)
        degrees = int(payload.get("degrees") or 0)
        return f"Rotated {degrees} degrees" if degrees else "Rotated media"

    @staticmethod
    def _metadata_payload(item: dict) -> dict:
        try:
            payload = json.loads(str(item.get("metadata_json") or "{}"))
            return dict(payload or {})
        except Exception:
            return {}

    @staticmethod
    def _item_name(item: dict) -> str:
        path = str(item.get("new_path") or item.get("old_path") or "")
        return Path(path).name or path or "Item"

    @staticmethod
    def _parent_text(path: str) -> str:
        if not path:
            return "unknown location"
        try:
            return str(Path(path).parent)
        except Exception:
            return path

    @staticmethod
    def _compare_value(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            return [ActionHistoryDialog._compare_value(item) for item in value if ActionHistoryDialog._compare_value(item) != ""]
        if isinstance(value, dict):
            return {
                str(key): normalized
                for key, item in value.items()
                if (normalized := ActionHistoryDialog._compare_value(item)) != ""
            }
        return value

    @staticmethod
    def _format_value(value) -> str:
        if value is None or value == "" or value == []:
            return "blank"
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) if value else "blank"
        text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return "blank"
        text = " ".join(text.split())
        if len(text) > 140:
            text = f"{text[:137]}..."
        return f'"{text}"'

    def _plain_entry_state(self, entry: dict, counts: dict[str, int]) -> str:
        undo_state = str(entry.get("undo_state") or "")
        if undo_state == "redoable":
            return "This action is currently undone and can be redone"
        if undo_state == "partially_undone":
            return "Some items are still current and some have already been undone"
        if undo_state == "undoable":
            return "This action is still current and can be undone"
        if int(counts.get("failed") or 0):
            return "This action has failed items"
        return "This action cannot be undone"

    def _plain_item_state(self, item: dict) -> str:
        state = str(item.get("current_state") or "")
        if state == "applied":
            return "This change is still current"
        if state == "undone":
            return "This change has been undone"
        if state == "unavailable":
            note = str(item.get("notes") or "").strip()
            return note or "This change cannot currently be undone or redone"
        if state == "failed":
            note = str(item.get("notes") or "").strip()
            return note or "This change failed"
        return state.replace("_", " ").title() or "State unknown"

    def _available_action_text(self, entry: dict, item: dict) -> str:
        state = str(item.get("current_state") or "")
        entry_undo_state = str(entry.get("undo_state") or "")
        if state == "applied" and entry_undo_state != "not_undoable":
            return "This change can be undone"
        if state == "undone":
            return "This change can be redone"
        return "No item action is currently available"

    def _status_text(self, entry: dict) -> str:
        status = str(entry.get("status") or "success").replace("_", " ").title()
        undo_state_raw = str(entry.get("undo_state") or "")
        undo_state = {
            "undoable": "Can undo",
            "redoable": "Can redo",
            "partially_undone": "Partially undone",
            "not_undoable": "Cannot undo",
        }.get(undo_state_raw, undo_state_raw.replace("_", " ").title())
        return f"{status} | {undo_state}" if undo_state else status

    def _item_state_text(self, item: dict) -> str:
        state_raw = str(item.get("current_state") or "")
        note = str(item.get("notes") or "").strip()
        if state_raw == "unavailable" and note:
            return "Unavailable"
        if state_raw == "failed" and note:
            return "Failed"
        return {
            "applied": "Current",
            "undone": "Undone",
            "unavailable": "Unavailable",
            "failed": "Failed",
        }.get(state_raw, state_raw.replace("_", " ").title())

    def _format_time(self, value: str, *, long: bool = False) -> str:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %I:%M:%S %p") if long else dt.strftime("%m/%d %I:%M %p")
        except Exception:
            return value
