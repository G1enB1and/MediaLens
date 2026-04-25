from __future__ import annotations

import ctypes
import html
import json
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QRect, QSignalBlocker, QSize, Qt, Signal, QTime, QTimer
from PySide6.QtGui import QColor, QCursor, QDrag, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QFileDialog,
    QFileIconProvider,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProxyStyle,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QStackedWidget,
    QTabBar,
    QTextEdit,
    QTimeEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QToolButton,
)


METADATA_SETTINGS_CONFIG: dict[str, dict] = {
    "image": {
        "groups": {
            "general": {
                "label": "General",
                "fields": [
                    ("res", "Resolution", True),
                    ("size", "File Size", True),
                    ("exifdatetaken", "Date Taken", False),
                    ("metadatadate", "Date Acquired", False),
                    ("originalfiledate", "Original File Date", False),
                    ("filecreateddate", "Windows ctime", False),
                    ("filemodifieddate", "Date Modified", False),
                    ("textdetected", "Text and OCR", True),
                    ("description", "Description", True),
                    ("tags", "Tags", True),
                    ("notes", "Notes", True),
                    ("embeddedtags", "Embedded Tags", True),
                    ("embeddedcomments", "Embedded Comments", True),
                    ("embeddedmetadata", "Embedded Metadata", True),
                ],
            },
            "camera": {
                "label": "Camera",
                "fields": [
                    ("camera", "Camera Model", False),
                    ("location", "Location (GPS)", False),
                    ("iso", "ISO Speed", False),
                    ("shutter", "Shutter Speed", False),
                    ("aperture", "Aperture", False),
                    ("software", "Software / Editor", False),
                    ("lens", "Lens Info", False),
                    ("dpi", "DPI", False),
                ],
            },
            "ai": {
                "label": "AI",
                "fields": [
                    ("aistatus", "AI Detection", True),
                    ("aigenerated", "AI Generated?", True),
                    ("aisource", "AI Tool / Source", True),
                    ("aifamilies", "AI Metadata Families", True),
                    ("aidetectionreasons", "AI Detection Reasons", False),
                    ("ailoras", "AI LoRAs", True),
                    ("aimodel", "AI Model", True),
                    ("aicheckpoint", "AI Checkpoint", False),
                    ("aisampler", "AI Sampler", True),
                    ("aischeduler", "AI Scheduler", True),
                    ("aicfg", "AI CFG", True),
                    ("aisteps", "AI Steps", True),
                    ("aiseed", "AI Seed", True),
                    ("aiupscaler", "AI Upscaler", False),
                    ("aidenoise", "AI Denoise", False),
                    ("aiprompt", "AI Prompt", True),
                    ("ainegprompt", "AI Negative Prompt", True),
                    ("aiparams", "AI Parameters", True),
                    ("aiworkflows", "AI Workflows", False),
                    ("aiprovenance", "AI Provenance", False),
                    ("aicharcards", "AI Character Cards", False),
                    ("airawpaths", "AI Metadata Paths", False),
                ],
            },
        },
        "group_order": ["general", "camera", "ai"],
    },
    "svg": {
        "groups": {
            "general": {
                "label": "General",
                "fields": [
                    ("res", "Resolution", True),
                    ("size", "File Size", True),
                    ("metadatadate", "Date Acquired", False),
                    ("originalfiledate", "Original File Date", False),
                    ("filecreateddate", "Windows ctime", False),
                    ("filemodifieddate", "Date Modified", False),
                    ("textdetected", "Text and OCR", True),
                    ("description", "Description", True),
                    ("tags", "Tags", True),
                    ("notes", "Notes", True),
                    ("embeddedmetadata", "Embedded Metadata", True),
                ],
            },
        },
        "group_order": ["general"],
    },
    "video": {
        "groups": {
            "general": {
                "label": "General",
                "fields": [
                    ("res", "Resolution", True),
                    ("size", "File Size", True),
                    ("exifdatetaken", "Date Taken", False),
                    ("metadatadate", "Date Acquired", False),
                    ("originalfiledate", "Original File Date", False),
                    ("filecreateddate", "Windows ctime", False),
                    ("filemodifieddate", "Date Modified", False),
                    ("textdetected", "Text and OCR", True),
                    ("duration", "Duration", True),
                    ("fps", "Frames Per Second", True),
                    ("codec", "Codec", True),
                    ("audio", "Audio", True),
                    ("description", "Description", True),
                    ("tags", "Tags", True),
                    ("notes", "Notes", True),
                    ("embeddedmetadata", "Embedded Metadata", True),
                ],
            },
            "ai": {
                "label": "AI",
                "fields": [
                    ("aistatus", "AI Detection", True),
                    ("aigenerated", "AI Generated?", True),
                    ("aisource", "AI Tool / Source", True),
                    ("aifamilies", "AI Metadata Families", True),
                    ("aimodel", "AI Model", True),
                    ("aicheckpoint", "AI Checkpoint", False),
                    ("aisampler", "AI Sampler", True),
                    ("aischeduler", "AI Scheduler", True),
                    ("aicfg", "AI CFG", True),
                    ("aisteps", "AI Steps", True),
                    ("aiseed", "AI Seed", True),
                    ("aiprompt", "AI Prompt", True),
                    ("ainegprompt", "AI Negative Prompt", True),
                    ("aiparams", "AI Parameters", True),
                    ("aiworkflows", "AI Workflows", False),
                    ("aiprovenance", "AI Provenance", False),
                    ("airawpaths", "AI Metadata Paths", False),
                ],
            },
        },
        "group_order": ["general", "ai"],
    },
    "gif": {
        "groups": {
            "general": {
                "label": "General",
                "fields": [
                    ("res", "Resolution", True),
                    ("size", "File Size", True),
                    ("exifdatetaken", "Date Taken", False),
                    ("metadatadate", "Date Acquired", False),
                    ("originalfiledate", "Original File Date", False),
                    ("filecreateddate", "Windows ctime", False),
                    ("filemodifieddate", "Date Modified", False),
                    ("textdetected", "Text and OCR", True),
                    ("duration", "Duration", True),
                    ("fps", "Frames Per Second", True),
                    ("description", "Description", True),
                    ("tags", "Tags", True),
                    ("notes", "Notes", True),
                    ("embeddedtags", "Embedded Tags", True),
                    ("embeddedcomments", "Embedded Comments", True),
                    ("embeddedmetadata", "Embedded Metadata", True),
                ],
            },
            "ai": {
                "label": "AI",
                "fields": [
                    ("aistatus", "AI Detection", True),
                    ("aigenerated", "AI Generated?", True),
                    ("aisource", "AI Tool / Source", True),
                    ("aifamilies", "AI Metadata Families", True),
                    ("aidetectionreasons", "AI Detection Reasons", False),
                    ("ailoras", "AI LoRAs", True),
                    ("aimodel", "AI Model", True),
                    ("aicheckpoint", "AI Checkpoint", False),
                    ("aisampler", "AI Sampler", True),
                    ("aischeduler", "AI Scheduler", True),
                    ("aicfg", "AI CFG", True),
                    ("aisteps", "AI Steps", True),
                    ("aiseed", "AI Seed", True),
                    ("aiupscaler", "AI Upscaler", False),
                    ("aidenoise", "AI Denoise", False),
                    ("aiprompt", "AI Prompt", True),
                    ("ainegprompt", "AI Negative Prompt", True),
                    ("aiparams", "AI Parameters", True),
                    ("aiworkflows", "AI Workflows", False),
                    ("aiprovenance", "AI Provenance", False),
                    ("aicharcards", "AI Character Cards", False),
                    ("airawpaths", "AI Metadata Paths", False),
                ],
            },
        },
        "group_order": ["general", "ai"],
    },
}


def _theme_api():
    from native.mediamanagerx_app.main import Theme

    return Theme


class SelectableRichTextView(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setAcceptRichText(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setStyleSheet("background: transparent; border: none; padding: 0;")

    def set_rich_text(self, text: str) -> None:
        self.setHtml(str(text or ""))
        self._update_height()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_height()

    def _update_height(self) -> None:
        document = self.document()
        document.setTextWidth(max(0, self.viewport().width() - 2))
        margins = self.contentsMargins()
        height = int(document.size().height() + margins.top() + margins.bottom() + (self.frameWidth() * 2) + 6)
        self.setFixedHeight(max(24, height))

DUPLICATE_RULE_POLICIES = [
    (
        "duplicate.rules.crop_policy",
        "Crop / Full Composition",
        [("prefer_full", "Prefer Full Composition"), ("prefer_cropped", "Prefer Cropped"), ("keep_each", "Keep Best from Each")],
        "prefer_full",
    ),
    (
        "duplicate.rules.color_policy",
        "Color / Black and White",
        [("prefer_color", "Prefer Color"), ("prefer_bw", "Prefer Black and White"), ("keep_each", "Keep Best from Each")],
        "prefer_color",
    ),
    (
        "duplicate.rules.text_policy",
        "Text / No Text",
        [("prefer_text", "Prefer Text"), ("prefer_no_text", "Prefer No Text"), ("keep_each", "Keep Best from Each")],
        "keep_each",
    ),
    (
        "duplicate.rules.file_size_policy",
        "File Size Variants",
        [("prefer_largest", "Prefer Largest File Size"), ("prefer_smallest", "Prefer Smallest File Size"), ("keep_each", "Keep Best from Each")],
        "prefer_largest",
    ),
]

DUPLICATE_FORMAT_ORDER_DEFAULT = ["PNG", "WebP", "JPEG", "RAW", "TIFF", "BMP", "GIF", "HEIC", "AVIF"]
DUPLICATE_MERGE_FIELDS = [
    ("duplicate.rules.merge.tags", "Tags", True),
    ("duplicate.rules.merge.description", "Description", True),
    ("duplicate.rules.merge.comments", "Comments", True),
    ("duplicate.rules.merge.notes", "Notes", True),
    ("duplicate.rules.merge.ai_prompts", "AI Prompts", True),
    ("duplicate.rules.merge.ai_parameters", "AI Parameters (can only keep 1)", True),
    ("duplicate.rules.merge.workflows", "Workflows (can only keep 1)", True),
    ("duplicate.rules.merge.all", "All", False),
]
DUPLICATE_PREFERRED_FOLDERS_SENTINEL = "All other Folders"
DUPLICATE_PREFERRED_FOLDERS_MIME = "application/x-medialens-folder-priority"
FOLDER_PRIORITY_ROLE_CENTERED = int(Qt.ItemDataRole.UserRole) + 1
FOLDER_PRIORITY_ROLE_SENTINEL = int(Qt.ItemDataRole.UserRole) + 2
FOLDER_PRIORITY_ROLE_EXTRA_TOP = int(Qt.ItemDataRole.UserRole) + 3
DUPLICATE_PRIORITY_ORDER_DEFAULT = [
    "File Size",
    "Resolution",
    "File Format",
    "Preferred Folders",
    "Most metadata",
    "Compression",
    "Color / Grey Preference",
    "Text / No Text Preference",
    "Cropped / Full Preference",
]


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("settingsSectionTitle")
    return label


def _description(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("settingsDescription")
    label.setWordWrap(True)
    return label


def _json_list(raw: object, defaults: list[str]) -> list[str]:
    try:
        values = [str(item).strip() for item in json.loads(str(raw or "[]")) if str(item).strip()]
    except Exception:
        values = []
    for default in defaults:
        if default not in values:
            values.append(default)
    return [item for item in values if item in defaults]


class SettingsProxyStyle(QProxyStyle):
    def __init__(self, base_style) -> None:
        super().__init__(base_style)
        self._accent = QColor("#8ab4f8")
        self._control_bg = QColor("#2d2d30")
        self._border = QColor("#3b3b40")
        self._check_color = QColor("#ffffff")

    def update_colors(self, accent: QColor, control_bg: str, border: str, text: str, is_light: bool) -> None:
        self._accent = QColor(accent)
        self._control_bg = QColor(control_bg)
        self._border = QColor(border)
        self._check_color = QColor("#000000" if self._contrast_ratio(self._accent, QColor("#000000")) >= self._contrast_ratio(self._accent, QColor("#ffffff")) else "#ffffff")
        if not self._check_color.isValid():
            self._check_color = QColor(text)

    @staticmethod
    def _relative_luminance(color: QColor) -> float:
        def _channel(value: int) -> float:
            srgb = value / 255.0
            if srgb <= 0.03928:
                return srgb / 12.92
            return ((srgb + 0.055) / 1.055) ** 2.4

        return (
            0.2126 * _channel(color.red())
            + 0.7152 * _channel(color.green())
            + 0.0722 * _channel(color.blue())
        )

    @classmethod
    def _contrast_ratio(cls, a: QColor, b: QColor) -> float:
        l1 = cls._relative_luminance(a)
        l2 = cls._relative_luminance(b)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def pixelMetric(self, metric, option=None, widget=None) -> int:
        if metric in (
            QStyle.PixelMetric.PM_IndicatorWidth,
            QStyle.PixelMetric.PM_IndicatorHeight,
            QStyle.PixelMetric.PM_ExclusiveIndicatorWidth,
            QStyle.PixelMetric.PM_ExclusiveIndicatorHeight,
        ):
            return 16
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element in (
            QStyle.PrimitiveElement.PE_IndicatorCheckBox,
            QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,
        ):
            self._draw_checkbox(option, painter)
            return
        if element == QStyle.PrimitiveElement.PE_IndicatorRadioButton:
            self._draw_radio(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    def _draw_checkbox(self, option, painter: QPainter) -> None:
        rect = option.rect.adjusted(1, 1, -1, -1)
        if not rect.isValid():
            return
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        checked = bool(option.state & QStyle.StateFlag.State_On)
        partial = bool(option.state & QStyle.StateFlag.State_NoChange)
        bg = QColor(self._accent if checked or partial else self._control_bg)
        border = QColor(self._accent if checked or partial else self._border)
        if hovered and not checked and not partial:
            bg = QColor(self._control_bg).lighter(108)
        if not enabled:
            bg.setAlpha(170)
            border.setAlpha(160)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 4, 4)
        if checked:
            painter.setPen(QPen(self._check_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p1 = QPointF(rect.left() + rect.width() * 0.23, rect.top() + rect.height() * 0.55)
            p2 = QPointF(rect.left() + rect.width() * 0.43, rect.top() + rect.height() * 0.75)
            p3 = QPointF(rect.left() + rect.width() * 0.78, rect.top() + rect.height() * 0.28)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        elif partial:
            painter.setPen(QPen(self._check_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            y = rect.center().y()
            painter.drawLine(QPointF(rect.left() + 4, y), QPointF(rect.right() - 4, y))
        painter.restore()

    def _draw_radio(self, option, painter: QPainter) -> None:
        rect = option.rect.adjusted(1, 1, -1, -1)
        if not rect.isValid():
            return
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        checked = bool(option.state & QStyle.StateFlag.State_On)
        bg = QColor(self._control_bg)
        border = QColor(self._accent if checked else self._border)
        if not enabled:
            bg.setAlpha(170)
            border.setAlpha(160)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(bg)
        painter.drawEllipse(rect)
        if checked:
            dot = rect.adjusted(4, 4, -4, -4)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._accent)
            painter.drawEllipse(dot)
        painter.restore()


class ReorderListWidget(QListWidget):
    orderChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsReorderList")
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setSpacing(0)
        self.model().rowsMoved.connect(lambda *_args: self.orderChanged.emit())

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()


class TransferListWidget(QListWidget):
    itemsChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsReorderList")
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setSpacing(0)
        self.model().rowsInserted.connect(lambda *_args: self.itemsChanged.emit())
        self.model().rowsRemoved.connect(lambda *_args: self.itemsChanged.emit())
        self.model().rowsMoved.connect(lambda *_args: self.itemsChanged.emit())

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.itemsChanged.emit()


class FolderSourceTreeWidget(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsReorderList")
        self.setHeaderHidden(True)
        self.setIndentation(14)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)

    def mimeTypes(self) -> list[str]:
        return [DUPLICATE_PREFERRED_FOLDERS_MIME]

    def mimeData(self, items) -> QMimeData:
        mime = QMimeData()
        paths = [
            str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()
            for item in items or []
            if str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()
        ]
        mime.setData(DUPLICATE_PREFERRED_FOLDERS_MIME, json.dumps(paths).encode("utf-8"))
        return mime


class PrioritizedFolderItemDelegate(QStyledItemDelegate):
    def __init__(self, page: "DuplicateSettingsPage", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = page

    def _remove_rect(self, option: QStyleOptionViewItem, is_sentinel: bool) -> QRect | None:
        if is_sentinel:
            return None
        size = 22
        x = option.rect.right() - 10 - size
        y = option.rect.top() + max(0, (option.rect.height() - size) // 2)
        return QRect(x, y, size, size)

    def remove_rect_for_index(self, option: QStyleOptionViewItem, index) -> QRect | None:
        return self._remove_rect(option, bool(index.data(FOLDER_PRIORITY_ROLE_SENTINEL)))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        style = option.widget.style() if option.widget is not None else self._page.style()
        base_opt = QStyleOptionViewItem(option)
        self.initStyleOption(base_opt, index)
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        is_sentinel = bool(index.data(FOLDER_PRIORITY_ROLE_SENTINEL))
        centered = bool(index.data(FOLDER_PRIORITY_ROLE_CENTERED))
        extra_top = int(index.data(FOLDER_PRIORITY_ROLE_EXTRA_TOP) or 0)
        opt = QStyleOptionViewItem(base_opt)
        opt.text = ""
        if is_sentinel:
            opt.icon = QIcon()
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, option.widget)
        else:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, option.widget)

        painter.save()
        is_light = bool(_theme_api().get_is_light())
        text_color = opt.palette.color(QPalette.ColorRole.HighlightedText if opt.state & QStyle.StateFlag.State_Selected else QPalette.ColorRole.Text)
        muted_color = opt.palette.color(QPalette.ColorRole.Mid)
        divider_color = QColor("#2a2a2a" if is_light else "#d8d8d8")
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(text_color))

        content_rect = option.rect.adjusted(10, 0, -6, 0)
        if centered:
            line_y_top = content_rect.center().y() - 18
            line_y_bottom = content_rect.center().y() + 18
            pen = QPen(divider_color, 2)
            painter.setPen(pen)
            painter.drawLine(content_rect.left(), line_y_top, content_rect.right(), line_y_top)
            painter.drawLine(content_rect.left(), line_y_bottom, content_rect.right(), line_y_bottom)
            painter.setPen(QPen(text_color))
            text_rect = QRect(content_rect.left(), line_y_top + 8, content_rect.width(), line_y_bottom - line_y_top - 16)
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter), text)
            painter.restore()
            return

        row_rect = content_rect.adjusted(0, extra_top, 0, 0)
        if is_sentinel:
            pen = QPen(divider_color, 2)
            painter.setPen(pen)
            top_y = row_rect.top() + 2
            bottom_y = row_rect.bottom() - 2
            painter.drawLine(row_rect.left(), top_y, row_rect.right(), top_y)
            painter.drawLine(row_rect.left(), bottom_y, row_rect.right(), bottom_y)
            painter.setPen(QPen(text_color))
            text_rect = row_rect.adjusted(0, 8, 0, -8)
            painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
            painter.restore()
            return

        remove_rect = self._remove_rect(option, is_sentinel)
        icon_space = 0
        if not base_opt.icon.isNull():
            icon_space = int(base_opt.decorationSize.width()) + 8
        text_rect = row_rect.adjusted(icon_space + 4, 0, -((remove_rect.width() + 12) if remove_rect is not None else 0), 0)
        painter.setPen(QPen(text_color))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
        if remove_rect is not None:
            hover = bool(option.state & QStyle.StateFlag.State_MouseOver) and remove_rect.contains(option.widget.mapFromGlobal(QCursor.pos())) if option.widget is not None else False
            btn_opt = QStyleOptionButton()
            btn_opt.rect = remove_rect
            btn_opt.text = "×"
            btn_opt.state = QStyle.StateFlag.State_Enabled
            if hover:
                btn_opt.state |= QStyle.StateFlag.State_MouseOver
            btn_opt.palette = opt.palette
            if is_light:
                btn_opt.palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
            else:
                btn_opt.palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
            style.drawControl(QStyle.ControlElement.CE_PushButtonBevel, btn_opt, painter, option.widget)
            btn_font = painter.font()
            btn_font.setBold(True)
            btn_font.setPointSizeF(btn_font.pointSizeF() + 1.5)
            painter.setFont(btn_font)
            style.drawControl(QStyle.ControlElement.CE_PushButtonLabel, btn_opt, painter, option.widget)
        painter.restore()


class PrioritizedFolderListWidget(QListWidget):
    orderChanged = Signal()
    removeRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsReorderList")
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setSpacing(0)
        self.model().rowsMoved.connect(lambda *_args: self.orderChanged.emit())

    def _decode_folder_paths(self, mime: QMimeData) -> list[str]:
        if not mime.hasFormat(DUPLICATE_PREFERRED_FOLDERS_MIME):
            return []
        try:
            return [
                str(item).strip()
                for item in json.loads(bytes(mime.data(DUPLICATE_PREFERRED_FOLDERS_MIME)).decode("utf-8"))
                if str(item).strip()
            ]
        except Exception:
            return []

    def _drop_row(self, pos) -> int:
        if self.count() <= 0:
            return 0
        for index in range(self.count()):
            rect = self.visualItemRect(self.item(index))
            if pos.y() < rect.center().y():
                return index
        return self.count()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(DUPLICATE_PREFERRED_FOLDERS_MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(DUPLICATE_PREFERRED_FOLDERS_MIME):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def mimeTypes(self) -> list[str]:
        return [DUPLICATE_PREFERRED_FOLDERS_MIME]

    def mimeData(self, items) -> QMimeData:
        mime = QMimeData()
        paths = [
            str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
            for item in items or []
            if str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        ]
        mime.setData(DUPLICATE_PREFERRED_FOLDERS_MIME, json.dumps(paths).encode("utf-8"))
        mime.setText(", ".join(paths))
        return mime

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        mime = self.mimeData([item])
        drag = QDrag(self)
        drag.setMimeData(mime)
        index = self.indexFromItem(item)
        delegate = self.itemDelegate()
        if index.isValid() and delegate is not None:
            rect = self.visualItemRect(item)
            scale = max(1.5, float(self.devicePixelRatioF()))
            pixmap = QPixmap(int(rect.width() * scale), int(rect.height() * scale))
            pixmap.fill(Qt.GlobalColor.transparent)
            pixmap.setDevicePixelRatio(scale)
            painter = QPainter(pixmap)
            try:
                option = QStyleOptionViewItem()
                option.initFrom(self.viewport())
                option.rect = QRect(0, 0, rect.width(), rect.height())
                option.state |= QStyle.StateFlag.State_Selected
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                bg_rect = option.rect.adjusted(0, 0, -1, -1)
                Theme = _theme_api()
                settings_obj = getattr(self.window(), "settings", None)
                accent_value = (
                    str(settings_obj.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
                    if settings_obj is not None
                    else Theme.ACCENT_DEFAULT
                )
                accent = QColor(accent_value)
                bg_color = QColor(Theme.get_accent_soft(accent))
                border_color = QColor(accent)
                painter.setPen(QPen(border_color, 1))
                painter.setBrush(bg_color)
                painter.drawRoundedRect(bg_rect, 8, 8)
                delegate.paint(painter, option, index)
            finally:
                painter.end()
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event) -> None:
        folder_paths = self._decode_folder_paths(event.mimeData())
        if folder_paths:
            insert_row = self._drop_row(event.position().toPoint())
            existing = [
                str(self.item(index).data(Qt.ItemDataRole.UserRole) or "").strip()
                for index in range(self.count())
            ]
            for folder_path in reversed(folder_paths):
                if folder_path in existing:
                    current_row = existing.index(folder_path)
                    item = self.takeItem(current_row)
                    existing.pop(current_row)
                    if current_row < insert_row:
                        insert_row -= 1
                else:
                    item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, folder_path)
                self.insertItem(insert_row, item)
                insert_row += 1
            event.acceptProposedAction()
            self.orderChanged.emit()
            return
        super().dropEvent(event)
        self.orderChanged.emit()

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        delegate = self.itemDelegate()
        if item is not None and isinstance(delegate, PrioritizedFolderItemDelegate):
            index = self.indexFromItem(item)
            option = QStyleOptionViewItem()
            option.rect = self.visualItemRect(item)
            option.widget = self.viewport()
            remove_rect = delegate.remove_rect_for_index(option, index)
            if remove_rect is not None and remove_rect.contains(event.position().toPoint()):
                self.removeRequested.emit(str(item.data(Qt.ItemDataRole.UserRole) or ""))
                event.accept()
                return
        super().mousePressEvent(event)


class PrioritizedFolderRow(QWidget):
    removeRequested = Signal(str)

    def __init__(self, folder_path: str, label_text: str, removable: bool, centered: bool, icon_pixmap=None, is_sentinel: bool = False, extra_top_space: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._folder_path = str(folder_path or "")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        if centered:
            outer.addStretch(1)
        elif extra_top_space > 0:
            outer.addSpacing(extra_top_space)
        self.top_line = QFrame()
        self.top_line.setObjectName("folderPriorityDivider")
        self.top_line.setFrameShape(QFrame.Shape.HLine)
        self.top_line.setVisible(is_sentinel)
        outer.addWidget(self.top_line)
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(8)
        if centered:
            layout.addStretch(1)
        elif icon_pixmap is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon_pixmap)
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.label = QLabel(label_text)
        self.label.setObjectName("folderPriorityRowLabel")
        self.label.setToolTip(label_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter if centered else (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
        layout.addWidget(self.label, 1 if centered else 0)
        if not centered:
            layout.addStretch(1)
        self.remove_btn = QPushButton("X")
        self.remove_btn.setObjectName("folderPriorityRemoveButton")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setFixedSize(QSize(22, 22))
        self.remove_btn.setVisible(removable)
        self.remove_btn.clicked.connect(lambda: self.removeRequested.emit(self._folder_path))
        layout.addWidget(self.remove_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if centered:
            layout.addStretch(1)
        outer.addLayout(layout)
        self.bottom_line = QFrame()
        self.bottom_line.setObjectName("folderPriorityDivider")
        self.bottom_line.setFrameShape(QFrame.Shape.HLine)
        self.bottom_line.setVisible(is_sentinel)
        outer.addWidget(self.bottom_line)
        if centered:
            outer.addStretch(1)


class ToolTipWrapper(QWidget):
    def __init__(self, widget: QWidget) -> None:
        super().__init__()
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(widget)
        self.wrapped = widget

    def sync_state(self, enabled: bool, tooltip: str = "") -> None:
        self.wrapped.setEnabled(enabled)
        if not enabled:
            self.setToolTip(tooltip)
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setToolTip("")
            self.unsetCursor()


class SettingsPage(QWidget):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self.dialog = dialog
        self.main_window = dialog.main_window
        self.bridge = dialog.bridge
        self.settings = dialog.settings

    def refresh(self) -> None:
        pass




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
