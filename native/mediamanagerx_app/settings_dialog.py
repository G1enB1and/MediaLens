from __future__ import annotations

import ctypes
import html
import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QRect, QSignalBlocker, QSize, Qt, Signal, QTimer
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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
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
                    ("textdetected", "Text Detected", True),
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
                    ("textdetected", "Text Detected", True),
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
                    ("textdetected", "Text Detected", True),
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
                    ("textdetected", "Text Detected", True),
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


class GeneralSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("General"))
        layout.addWidget(_description("Startup, file handling, and update behavior."))

        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        startup_layout.setSpacing(10)
        self.randomize_toggle = QCheckBox("Randomize gallery order")
        self.restore_last_toggle = QCheckBox("Restore previous folder on launch")
        self.show_hidden_toggle = QCheckBox("Show hidden files and folders")
        self.include_nested_files_toggle = QCheckBox("Include nested files in gallery")
        self.show_folders_in_gallery_toggle = QCheckBox("Show folders in gallery")
        startup_layout.addWidget(self.randomize_toggle)
        startup_layout.addWidget(self.restore_last_toggle)
        startup_layout.addWidget(self.show_hidden_toggle)
        startup_layout.addWidget(self.include_nested_files_toggle)
        startup_layout.addWidget(self.show_folders_in_gallery_toggle)

        startup_layout.addWidget(QLabel("Starting folder"))
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        self.start_folder_edit = QLineEdit()
        self.start_folder_browse_btn = QPushButton("Browse...")
        self.load_now_btn = QPushButton("Load Now")
        folder_row.addWidget(self.start_folder_edit, 1)
        folder_row.addWidget(self.start_folder_browse_btn)
        folder_row.addWidget(self.load_now_btn)
        startup_layout.addLayout(folder_row)
        layout.addWidget(startup_group)

        retention_group = QGroupBox("Delete Retention")
        retention_layout = QVBoxLayout(retention_group)
        retention_layout.setSpacing(10)

        self.use_recycle_bin_toggle = QCheckBox("Use System Recycle Bin for deletes (Shift+Del for permanent)")
        self.use_medialens_retention_toggle = QCheckBox("Use MediaLens separate retention system")

        retention_layout.addWidget(self.use_recycle_bin_toggle)
        retention_layout.addWidget(self.use_medialens_retention_toggle)

        self.retention_days_layout = QHBoxLayout()
        self.retention_days_layout.setContentsMargins(24, 0, 0, 0)
        self.retention_days_label = QLabel("Keep for")
        self.retention_days_input = QSpinBox()
        self.retention_days_input.setRange(1, 3650)
        self.retention_days_input.setSuffix(" days")
        self.retention_days_wrapper = ToolTipWrapper(self.retention_days_input)
        self.retention_days_layout.addWidget(self.retention_days_label)
        self.retention_days_layout.addWidget(self.retention_days_wrapper)
        self.retention_days_layout.addStretch(1)
        retention_layout.addLayout(self.retention_days_layout)

        self.retention_actions_layout = QHBoxLayout()
        self.retention_actions_layout.setContentsMargins(24, 0, 0, 0)
        self.retention_view_btn = QPushButton("View")
        self.retention_restore_all_btn = QPushButton("Restore All")
        self.retention_empty_now_btn = QPushButton("Empty Now")
        self.retention_view_wrapper = ToolTipWrapper(self.retention_view_btn)
        self.retention_restore_wrapper = ToolTipWrapper(self.retention_restore_all_btn)
        self.retention_empty_wrapper = ToolTipWrapper(self.retention_empty_now_btn)
        self.retention_actions_layout.addWidget(self.retention_view_wrapper)
        self.retention_actions_layout.addWidget(self.retention_restore_wrapper)
        self.retention_actions_layout.addWidget(self.retention_empty_wrapper)
        self.retention_actions_layout.addStretch(1)
        retention_layout.addLayout(self.retention_actions_layout)
        
        layout.addWidget(retention_group)

        updates_group = QGroupBox("Updates")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setSpacing(10)
        self.auto_update_toggle = QCheckBox("Check for updates on launch")
        updates_layout.addWidget(self.auto_update_toggle)
        update_row = QHBoxLayout()
        update_row.setContentsMargins(0, 0, 0, 0)
        self.check_updates_btn = QPushButton("Check for Updates")
        self.version_label = QLabel("")
        self.version_label.setWordWrap(True)
        update_row.addWidget(self.check_updates_btn)
        update_row.addWidget(self.version_label, 1)
        updates_layout.addLayout(update_row)
        layout.addWidget(updates_group)
        layout.addStretch(1)

        self.randomize_toggle.toggled.connect(self._on_randomize_changed)
        self.restore_last_toggle.toggled.connect(self._on_restore_last_changed)
        self.show_hidden_toggle.toggled.connect(self._on_show_hidden_changed)
        self.include_nested_files_toggle.toggled.connect(self._on_include_nested_files_changed)
        self.show_folders_in_gallery_toggle.toggled.connect(self._on_show_folders_in_gallery_changed)
        self.use_recycle_bin_toggle.toggled.connect(self._on_recycle_bin_changed)
        self.use_medialens_retention_toggle.toggled.connect(self._on_medialens_retention_changed)
        self.retention_days_input.valueChanged.connect(lambda val: self.dialog.set_setting_str("gallery.medialens_retention_days", str(val)))
        self.retention_view_btn.clicked.connect(self._view_recycle_bin)
        self.retention_restore_all_btn.clicked.connect(self._restore_all_recycle_bin)
        self.retention_empty_now_btn.clicked.connect(self._empty_recycle_bin)
        self.start_folder_browse_btn.clicked.connect(self._browse_start_folder)
        self.start_folder_edit.editingFinished.connect(self._commit_start_folder)
        self.load_now_btn.clicked.connect(self._load_start_folder_now)
        self.auto_update_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("updates.check_on_launch", checked))
        self.check_updates_btn.clicked.connect(self._check_for_updates)
        self.bridge.updateAvailable.connect(self._on_update_available)
        self.bridge.updateError.connect(self._on_update_error)

    def _sync_start_folder_enabled(self) -> None:
        enabled = not self.restore_last_toggle.isChecked()
        self.start_folder_edit.setEnabled(enabled)
        self.start_folder_browse_btn.setEnabled(enabled)

    def _sync_retention_enabled(self) -> None:
        enabled = self.use_medialens_retention_toggle.isChecked()
        self.retention_days_label.setEnabled(enabled)
        self.retention_days_wrapper.sync_state(enabled, "Enable First")
        self.retention_view_wrapper.sync_state(enabled, "Enable First")
        self.retention_restore_wrapper.sync_state(enabled, "Enable First")
        self.retention_empty_wrapper.sync_state(enabled, "Enable First")

    def _on_recycle_bin_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.use_recycle_bin", checked)
        if checked:
            with QSignalBlocker(self.use_medialens_retention_toggle):
                self.use_medialens_retention_toggle.setChecked(False)
            self.dialog.set_setting_bool("gallery.use_medialens_retention", False)
            self._sync_retention_enabled()

    def _on_medialens_retention_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.use_medialens_retention", checked)
        if checked:
            with QSignalBlocker(self.use_recycle_bin_toggle):
                self.use_recycle_bin_toggle.setChecked(False)
            self.dialog.set_setting_bool("gallery.use_recycle_bin", False)
        self._sync_retention_enabled()

    def _view_recycle_bin(self) -> None:
        if hasattr(self.main_window, "show_recycle_bin_viewer"):
            self.dialog.close() # Close settings when opening recycle bin
            self.main_window.show_recycle_bin_viewer()

    def _restore_all_recycle_bin(self) -> None:
        if hasattr(self.bridge, "restore_all_recycle_bin"):
            reply = QMessageBox.question(self, "Restore All", "Are you sure you want to restore all files from the MediaLens format recycle bin to their original locations?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.bridge.restore_all_recycle_bin()

    def _empty_recycle_bin(self) -> None:
        if hasattr(self.bridge, "empty_recycle_bin"):
            reply = QMessageBox.question(self, "Empty Now", "Are you sure you want to permanently delete all files in the MediaLens recycle bin?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.bridge.empty_recycle_bin()

    def _on_randomize_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.randomize", checked)
        self.main_window._refresh_current_folder()

    def _on_restore_last_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.restore_last", checked)
        self._sync_start_folder_enabled()

    def _on_show_hidden_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.show_hidden", checked)
        self.main_window._refresh_current_folder()

    def _on_include_nested_files_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.include_nested_files", checked)
        self.main_window._refresh_current_folder()

    def _on_show_folders_in_gallery_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.show_folders", checked)
        self.main_window._refresh_current_folder()

    def _browse_start_folder(self) -> None:
        folder = self.bridge.pick_folder()
        if folder:
            self.start_folder_edit.setText(folder)
            self._commit_start_folder()

    def _commit_start_folder(self) -> None:
        self.dialog.set_setting_str("gallery.start_folder", self.start_folder_edit.text().strip())

    def _load_start_folder_now(self) -> None:
        path = self.start_folder_edit.text().strip()
        if path:
            self.bridge.load_folder_now(path)

    def _check_for_updates(self) -> None:
        self.version_label.setText("Checking for updates...")
        self.bridge.check_for_updates(manual=True)

    def _on_update_available(self, version: str, manual: bool) -> None:
        if version:
            self.version_label.setText(f"Update available: {version}")
        elif manual:
            self.version_label.setText("You are using the latest version.")

    def _on_update_error(self, message: str) -> None:
        self.version_label.setText(f"Update error: {message}")

    def refresh(self) -> None:
        state = self.bridge.get_settings()
        with QSignalBlocker(self.randomize_toggle):
            self.randomize_toggle.setChecked(bool(state.get("gallery.randomize", False)))
        with QSignalBlocker(self.restore_last_toggle):
            self.restore_last_toggle.setChecked(bool(state.get("gallery.restore_last", False)))
        with QSignalBlocker(self.show_hidden_toggle):
            self.show_hidden_toggle.setChecked(bool(state.get("gallery.show_hidden", False)))
        with QSignalBlocker(self.include_nested_files_toggle):
            self.include_nested_files_toggle.setChecked(bool(state.get("gallery.include_nested_files", True)))
        with QSignalBlocker(self.show_folders_in_gallery_toggle):
            self.show_folders_in_gallery_toggle.setChecked(bool(state.get("gallery.show_folders", True)))
        with QSignalBlocker(self.use_recycle_bin_toggle):
            self.use_recycle_bin_toggle.setChecked(bool(self.settings.value("gallery/use_recycle_bin", True, type=bool)))
        with QSignalBlocker(self.use_medialens_retention_toggle):
            self.use_medialens_retention_toggle.setChecked(bool(self.settings.value("gallery/use_medialens_retention", False, type=bool)))
        with QSignalBlocker(self.retention_days_input):
            try:
                val = int(self.settings.value("gallery/medialens_retention_days", 30))
            except (TypeError, ValueError):
                val = 30
            self.retention_days_input.setValue(val)
        with QSignalBlocker(self.auto_update_toggle):
            self.auto_update_toggle.setChecked(bool(state.get("updates.check_on_launch", True)))
        with QSignalBlocker(self.start_folder_edit):
            self.start_folder_edit.setText(str(state.get("gallery.start_folder", "") or ""))
        self._sync_start_folder_enabled()
        self._sync_retention_enabled()
        self.version_label.setText(f"Current version: {self.bridge.get_app_version()}")


class AppearanceSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Appearance"))
        layout.addWidget(_description("Theme, accent color, and launch presentation."))

        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        self.theme_dark = QRadioButton("Dark")
        self.theme_light = QRadioButton("Light")
        self.theme_buttons = QButtonGroup(self)
        self.theme_buttons.addButton(self.theme_dark)
        self.theme_buttons.addButton(self.theme_light)
        theme_layout.addWidget(self.theme_dark)
        theme_layout.addWidget(self.theme_light)
        layout.addWidget(theme_group)

        accent_group = QGroupBox("Accent Color")
        accent_layout = QHBoxLayout(accent_group)
        self.accent_swatch = QPushButton()
        self.accent_swatch.setObjectName("accentSwatchButton")
        self.accent_swatch.setFixedSize(28, 28)
        self.accent_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accent_swatch.setToolTip("Choose Accent Color")
        self.accent_hex_input = QLineEdit()
        self.accent_hex_input.setObjectName("accentHexInput")
        self.accent_hex_input.setMaxLength(7)
        self.accent_hex_input.setPlaceholderText("#RRGGBB")
        self.accent_hex_input.setFixedWidth(110)
        accent_layout.addWidget(self.accent_swatch)
        accent_layout.addWidget(self.accent_hex_input)
        accent_layout.addStretch(1)
        layout.addWidget(accent_group)

        self.show_splash_toggle = QCheckBox("Show splash screen on launch")
        layout.addWidget(self.show_splash_toggle)
        layout.addStretch(1)

        self.theme_dark.toggled.connect(lambda checked: checked and self.dialog.set_setting_str("ui.theme_mode", "dark"))
        self.theme_light.toggled.connect(lambda checked: checked and self.dialog.set_setting_str("ui.theme_mode", "light"))
        self.accent_swatch.clicked.connect(self._choose_accent)
        self.accent_hex_input.editingFinished.connect(self._apply_hex_input)
        self.show_splash_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("ui.show_splash_screen", checked))
        self.bridge.accentColorChanged.connect(lambda _value: self.refresh())

    def _choose_accent(self) -> None:
        Theme = _theme_api()
        current = QColor(str(self.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))
        chosen = QColorDialog.getColor(current, self, "Choose Accent Color")
        if chosen.isValid():
            self.dialog.set_setting_str("ui.accent_color", chosen.name())
            self.refresh()

    def _apply_hex_input(self) -> None:
        raw = self.accent_hex_input.text().strip()
        if not raw:
            self.refresh()
            return
        if not raw.startswith("#"):
            raw = f"#{raw}"
        color = QColor(raw)
        if not color.isValid():
            self.refresh()
            return
        self.dialog.set_setting_str("ui.accent_color", color.name())
        self.refresh()

    def refresh(self) -> None:
        theme_mode = str(self.settings.value("ui/theme_mode", "dark", type=str) or "dark")
        Theme = _theme_api()
        accent = str(self.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
        splash = bool(self.settings.value("ui/show_splash_screen", True, type=bool))
        with QSignalBlocker(self.theme_dark):
            self.theme_dark.setChecked(theme_mode != "light")
        with QSignalBlocker(self.theme_light):
            self.theme_light.setChecked(theme_mode == "light")
        with QSignalBlocker(self.show_splash_toggle):
            self.show_splash_toggle.setChecked(splash)
        border = Theme.get_border(QColor(accent))
        self.accent_swatch.setStyleSheet(
            f"QPushButton#accentSwatchButton {{ background: {accent}; border: 1px solid {border}; border-radius: 4px; padding: 0; }}"
            f"QPushButton#accentSwatchButton:hover {{ border-color: {accent}; }}"
        )
        with QSignalBlocker(self.accent_hex_input):
            self.accent_hex_input.setText(accent.upper())


class PlayerSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Player"))
        layout.addWidget(_description("Playback defaults for videos and animated GIFs."))

        self.mute_default_toggle = QCheckBox("Mute video by default")
        self.autoplay_gallery_toggle = QCheckBox("Autoplay animated GIFs in gallery")
        self.autoplay_preview_toggle = QCheckBox("Autoplay animated GIFs in details preview")
        layout.addWidget(self.mute_default_toggle)
        layout.addWidget(self.autoplay_gallery_toggle)
        layout.addWidget(self.autoplay_preview_toggle)

        loop_group = QGroupBox("Video looping")
        loop_layout = QVBoxLayout(loop_group)
        self.loop_all = QRadioButton("Loop all videos")
        self.loop_none = QRadioButton("Do not loop videos")
        self.loop_short = QRadioButton("Loop videos under cutoff")
        self.loop_buttons = QButtonGroup(self)
        self.loop_buttons.addButton(self.loop_all)
        self.loop_buttons.addButton(self.loop_none)
        self.loop_buttons.addButton(self.loop_short)
        loop_layout.addWidget(self.loop_all)
        loop_layout.addWidget(self.loop_none)
        loop_layout.addWidget(self.loop_short)
        layout.addWidget(loop_group)

        cutoff_group = QGroupBox("Video length loop cutoff")
        cutoff_form = QFormLayout(cutoff_group)
        self.loop_cutoff = QSpinBox()
        self.loop_cutoff.setRange(1, 86400)
        self.loop_cutoff.setSuffix(" sec")
        cutoff_form.addRow("Seconds", self.loop_cutoff)
        layout.addWidget(cutoff_group)
        layout.addStretch(1)

        self.mute_default_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("gallery.mute_video_by_default", checked))
        self.autoplay_gallery_toggle.toggled.connect(self._on_autoplay_gallery_changed)
        self.autoplay_preview_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("player.autoplay_preview_animated_gifs", checked))
        self.loop_all.toggled.connect(lambda checked: checked and self._set_loop_mode("all"))
        self.loop_none.toggled.connect(lambda checked: checked and self._set_loop_mode("none"))
        self.loop_short.toggled.connect(lambda checked: checked and self._set_loop_mode("short"))
        self.loop_cutoff.valueChanged.connect(lambda value: self.dialog.set_setting_str("player.video_loop_cutoff_seconds", str(int(value))))

    def _on_autoplay_gallery_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("player.autoplay_gallery_animated_gifs", checked)
        self.main_window._refresh_current_folder()

    def _set_loop_mode(self, mode: str) -> None:
        self.dialog.set_setting_str("player.video_loop_mode", mode)
        self.loop_cutoff.setEnabled(mode == "short")

    def refresh(self) -> None:
        state = self.bridge.get_settings()
        with QSignalBlocker(self.mute_default_toggle):
            self.mute_default_toggle.setChecked(bool(state.get("gallery.mute_video_by_default", True)))
        with QSignalBlocker(self.autoplay_gallery_toggle):
            self.autoplay_gallery_toggle.setChecked(bool(state.get("player.autoplay_gallery_animated_gifs", True)))
        with QSignalBlocker(self.autoplay_preview_toggle):
            self.autoplay_preview_toggle.setChecked(bool(state.get("player.autoplay_preview_animated_gifs", True)))
        loop_mode = str(state.get("player.video_loop_mode", "short") or "short")
        with QSignalBlocker(self.loop_all):
            self.loop_all.setChecked(loop_mode == "all")
        with QSignalBlocker(self.loop_none):
            self.loop_none.setChecked(loop_mode == "none")
        with QSignalBlocker(self.loop_short):
            self.loop_short.setChecked(loop_mode == "short")
        with QSignalBlocker(self.loop_cutoff):
            self.loop_cutoff.setValue(int(state.get("player.video_loop_cutoff_seconds", 90) or 90))
        self.loop_cutoff.setEnabled(loop_mode == "short")


class ScannersSettingsPage(SettingsPage):
    SCANNERS = [
        ("text_detection", "Text Detection", "Finds whether images/videos likely contain visible text."),
        ("ocr_text", "OCR for Text Detected Files", "Reads actual text only from files already marked as Text Detected."),
    ]

    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self._widgets: dict[str, dict[str, QWidget]] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Scanners"))
        layout.addWidget(_description("Control optional background scanners. The main file scanner is intentionally not configurable here."))

        for key, title, description in self.SCANNERS:
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            group_layout.setSpacing(10)

            desc_label = _description(description)
            enable_toggle = QCheckBox("Run this scanner in the background")

            schedule_row = QHBoxLayout()
            schedule_row.setContentsMargins(0, 0, 0, 0)
            schedule_label = QLabel("Run every")
            interval = QSpinBox()
            interval.setRange(1, 24 * 30)
            interval.setSuffix(" hours")
            schedule_row.addWidget(schedule_label)
            schedule_row.addWidget(interval)
            schedule_row.addStretch(1)

            action_row = QHBoxLayout()
            action_row.setContentsMargins(0, 0, 0, 0)
            run_btn = QPushButton("Run Now")
            status_label = QLabel("Status: Idle")
            status_label.setWordWrap(True)
            action_row.addWidget(run_btn)
            action_row.addWidget(status_label, 1)

            last_run_label = QLabel("Last run: Never")
            last_run_label.setWordWrap(True)

            group_layout.addWidget(desc_label)
            group_layout.addWidget(enable_toggle)
            group_layout.addLayout(schedule_row)
            group_layout.addLayout(action_row)
            group_layout.addWidget(last_run_label)
            layout.addWidget(group)

            self._widgets[key] = {
                "enable": enable_toggle,
                "interval": interval,
                "run": run_btn,
                "status": status_label,
                "last_run": last_run_label,
            }
            enable_toggle.toggled.connect(lambda checked, scanner_key=key: self._set_enabled(scanner_key, checked))
            interval.valueChanged.connect(lambda value, scanner_key=key: self._set_interval(scanner_key, int(value)))
            run_btn.clicked.connect(lambda _checked=False, scanner_key=key: self._run_now(scanner_key))

        layout.addStretch(1)
        if hasattr(self.bridge, "scannerStatusChanged"):
            self.bridge.scannerStatusChanged.connect(self._on_scanner_status_changed)

    @staticmethod
    def _format_last_run(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return "Never"
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone()
            return dt.strftime("%Y-%m-%d %I:%M %p").lstrip("0")
        except Exception:
            return text

    def _set_enabled(self, scanner_key: str, checked: bool) -> None:
        self.dialog.set_setting_bool(f"scanners.{scanner_key}.enabled", checked)
        self._sync_enabled_state(scanner_key)

    def _set_interval(self, scanner_key: str, value: int) -> None:
        self.dialog.set_setting_str(f"scanners.{scanner_key}.interval_hours", str(max(1, int(value))))

    def _run_now(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        status = widgets.get("status")
        if isinstance(status, QLabel):
            status.setText("Status: Starting...")
        try:
            if hasattr(self.bridge, "run_scanner_now"):
                self.bridge.run_scanner_now(scanner_key)
        except Exception:
            if isinstance(status, QLabel):
                status.setText("Status: Error starting scanner")

    def _sync_enabled_state(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        enable = widgets.get("enable")
        enabled = bool(enable.isChecked()) if isinstance(enable, QCheckBox) else True
        for child_key in ("interval", "run"):
            widget = widgets.get(child_key)
            if widget is not None:
                widget.setEnabled(enabled)

    def _apply_status(self, scanner_key: str, payload: dict) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        if not widgets:
            return
        enabled = bool(payload.get("enabled", True))
        interval_value = int(payload.get("interval_hours") or 24)
        enable = widgets.get("enable")
        interval = widgets.get("interval")
        status = widgets.get("status")
        last_run = widgets.get("last_run")
        if isinstance(enable, QCheckBox):
            with QSignalBlocker(enable):
                enable.setChecked(enabled)
        if isinstance(interval, QSpinBox):
            with QSignalBlocker(interval):
                interval.setValue(max(1, interval_value))
        if isinstance(status, QLabel):
            status.setText(f"Status: {payload.get('status') or 'Idle'}")
        if isinstance(last_run, QLabel):
            last_run.setText(f"Last run: {self._format_last_run(payload.get('last_run_utc'))}")
        self._sync_enabled_state(scanner_key)

    def _on_scanner_status_changed(self, scanner_key: str, payload: dict) -> None:
        self._apply_status(str(scanner_key or ""), dict(payload or {}))

    def refresh(self) -> None:
        try:
            status = self.bridge.get_scanner_status() if hasattr(self.bridge, "get_scanner_status") else {}
        except Exception:
            status = {}
        for scanner_key, _title, _description in self.SCANNERS:
            payload = dict((status or {}).get(scanner_key) or {})
            if not payload:
                default_enabled = scanner_key != "ocr_text"
                payload = {
                    "enabled": bool(self.settings.value(f"scanners/{scanner_key}/enabled", default_enabled, type=bool)),
                    "interval_hours": int(self.settings.value(f"scanners/{scanner_key}/interval_hours", 24, type=int) or 24),
                    "last_run_utc": str(self.settings.value(f"scanners/{scanner_key}/last_run_utc", "", type=str) or ""),
                    "status": str(self.settings.value(f"scanners/{scanner_key}/status", "Idle", type=str) or "Idle"),
                }
            self._apply_status(scanner_key, payload)


class MetadataSettingsPage(SettingsPage):
    MODE_TITLES = [("image", "Images"), ("gif", "Animated GIFs"), ("video", "Videos"), ("svg", "SVGs")]

    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self._loading = False
        self._current_mode = "image"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Metadata"))
        layout.addWidget(_description("Control which metadata groups and fields appear in the details panel. Drag to reorder groups and fields."))

        file_type_group = QGroupBox("File Type")
        file_type_layout = QVBoxLayout(file_type_group)
        self.mode_tabs = QTabBar()
        self.mode_tabs.setObjectName("settingsModeTabs")
        self.mode_tabs.setExpanding(False)
        self.mode_tabs.setDrawBase(False)
        for _mode, title in self.MODE_TITLES:
            self.mode_tabs.addTab(title)
        file_type_layout.addWidget(self.mode_tabs)
        layout.addWidget(file_type_group)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)
        layout.addLayout(content_layout, 1)

        groups_box = QGroupBox("Groups")
        groups_layout = QVBoxLayout(groups_box)
        self.group_list = ReorderListWidget()
        groups_layout.addWidget(self.group_list)
        content_layout.addWidget(groups_box, 1)

        fields_box = QGroupBox("Selected Group")
        fields_layout = QVBoxLayout(fields_box)
        self.group_name_label = QLabel("Select a group")
        self.group_name_label.setObjectName("settingsFieldTitle")
        self.group_enabled_toggle = QCheckBox("Show this group in the details panel")
        self.field_list = ReorderListWidget()
        fields_layout.addWidget(self.group_name_label)
        fields_layout.addWidget(self.group_enabled_toggle)
        fields_layout.addWidget(QLabel("Fields"))
        fields_layout.addWidget(self.field_list, 1)
        content_layout.addWidget(fields_box, 2)

        self.mode_tabs.currentChanged.connect(self._on_mode_changed)
        self.group_list.currentItemChanged.connect(self._on_group_selected)
        self.group_list.itemChanged.connect(self._on_group_item_changed)
        self.group_list.orderChanged.connect(self._save_group_order)
        self.group_enabled_toggle.toggled.connect(self._commit_group_options)
        self.field_list.itemChanged.connect(self._on_field_item_changed)
        self.field_list.orderChanged.connect(self._save_field_order)

    def _config(self) -> dict:
        return METADATA_SETTINGS_CONFIG.get(self._current_mode, METADATA_SETTINGS_CONFIG["image"])

    def _group_order_key(self) -> str:
        return f"metadata.layout.{self._current_mode}.group_order"

    def _field_order_key(self, group_key: str) -> str:
        return f"metadata.layout.{self._current_mode}.field_order.{group_key}"

    def _group_enabled_key(self, group_key: str) -> str:
        return f"metadata.display.{self._current_mode}.groups.{group_key}"

    def _field_enabled_key(self, field_key: str) -> str:
        return f"metadata.display.{self._current_mode}.{field_key}"

    def _selected_group_key(self) -> str:
        item = self.group_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""

    def _ordered_group_keys(self) -> list[str]:
        defaults = list(self._config()["group_order"])
        raw = self.settings.value(self._group_order_key().replace(".", "/"), "[]", type=str)
        return _json_list(raw, defaults)

    def _ordered_field_keys(self, group_key: str) -> list[str]:
        defaults = [field_key for field_key, _label, _default in self._config()["groups"][group_key]["fields"]]
        raw = self.settings.value(self._field_order_key(group_key).replace(".", "/"), "[]", type=str)
        return _json_list(raw, defaults)

    def _resolve_field_enabled(self, field_key: str, default_enabled: bool) -> bool:
        qkey = self._field_enabled_key(field_key).replace(".", "/")
        if self.settings.contains(qkey):
            return bool(self.settings.value(qkey, default_enabled, type=bool))
        if field_key == "originalfiledate":
            fallback = self._field_enabled_key("filecreateddate").replace(".", "/")
            if self.settings.contains(fallback):
                return bool(self.settings.value(fallback, False, type=bool))
            legacy = "metadata/display/filecreateddate"
            if self.settings.contains(legacy):
                return bool(self.settings.value(legacy, False, type=bool))
        return bool(default_enabled)

    def _populate_groups(self) -> None:
        selected_key = self._selected_group_key()
        self._loading = True
        try:
            self.group_list.clear()
            for group_key in self._ordered_group_keys():
                group_cfg = self._config()["groups"].get(group_key)
                if not group_cfg:
                    continue
                item = QListWidgetItem(group_cfg["label"])
                item.setData(Qt.ItemDataRole.UserRole, group_key)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                enabled = bool(self.settings.value(self._group_enabled_key(group_key).replace(".", "/"), True, type=bool))
                item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
                self.group_list.addItem(item)
            if self.group_list.count():
                row = 0
                if selected_key:
                    for index in range(self.group_list.count()):
                        if str(self.group_list.item(index).data(Qt.ItemDataRole.UserRole) or "") == selected_key:
                            row = index
                            break
                self.group_list.setCurrentRow(row)
        finally:
            self._loading = False
        self._populate_fields(self._selected_group_key())

    def _populate_fields(self, group_key: str) -> None:
        self._loading = True
        try:
            self.field_list.clear()
            enabled = bool(group_key)
            self.group_enabled_toggle.setEnabled(enabled)
            self.field_list.setEnabled(enabled)
            if not group_key:
                self.group_name_label.setText("Select a group")
                return
            group_cfg = self._config()["groups"].get(group_key)
            if not group_cfg:
                self.group_name_label.setText("Select a group")
                self.group_enabled_toggle.setChecked(False)
                return
            self.group_name_label.setText(group_cfg["label"])
            self.group_enabled_toggle.setChecked(bool(self.settings.value(self._group_enabled_key(group_key).replace(".", "/"), True, type=bool)))
            field_map = {field_key: (label_text, default_enabled) for field_key, label_text, default_enabled in group_cfg["fields"]}
            for field_key in self._ordered_field_keys(group_key):
                if field_key not in field_map:
                    continue
                label_text, default_enabled = field_map[field_key]
                item = QListWidgetItem(label_text)
                item.setData(Qt.ItemDataRole.UserRole, field_key)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if self._resolve_field_enabled(field_key, default_enabled) else Qt.CheckState.Unchecked)
                self.field_list.addItem(item)
        finally:
            self._loading = False

    def _on_mode_changed(self, index: int) -> None:
        if 0 <= index < len(self.MODE_TITLES):
            self._current_mode = self.MODE_TITLES[index][0]
            self.dialog.set_setting_str("metadata.layout.active_mode", self._current_mode)
            self._populate_groups()

    def _on_group_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        group_key = str(current.data(Qt.ItemDataRole.UserRole) or "") if current else ""
        self._populate_fields(group_key)

    def _on_group_item_changed(self, item: QListWidgetItem) -> None:
        if self._loading:
            return
        group_key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        self.dialog.set_setting_bool(self._group_enabled_key(group_key), item.checkState() == Qt.CheckState.Checked)
        if group_key == self._selected_group_key():
            self._populate_fields(group_key)

    def _commit_group_options(self) -> None:
        if self._loading:
            return
        group_key = self._selected_group_key()
        if not group_key:
            return
        self.dialog.set_setting_bool(self._group_enabled_key(group_key), self.group_enabled_toggle.isChecked())
        current = self.group_list.currentItem()
        if current is not None:
            with QSignalBlocker(self.group_list):
                current.setCheckState(Qt.CheckState.Checked if self.group_enabled_toggle.isChecked() else Qt.CheckState.Unchecked)

    def _save_group_order(self) -> None:
        if self._loading:
            return
        order = [str(self.group_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.group_list.count())]
        self.dialog.set_setting_str(self._group_order_key(), json.dumps(order))

    def _on_field_item_changed(self, item: QListWidgetItem) -> None:
        if self._loading:
            return
        field_key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        self.dialog.set_setting_bool(self._field_enabled_key(field_key), item.checkState() == Qt.CheckState.Checked)

    def _save_field_order(self) -> None:
        if self._loading:
            return
        group_key = self._selected_group_key()
        if not group_key:
            return
        order = [str(self.field_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.field_list.count())]
        self.dialog.set_setting_str(self._field_order_key(group_key), json.dumps(order))

    def refresh(self) -> None:
        active_mode = str(self.settings.value("metadata/layout/active_mode", "image", type=str) or "image")
        valid_modes = [mode for mode, _title in self.MODE_TITLES]
        if active_mode not in valid_modes:
            active_mode = "image"
        self._current_mode = active_mode
        with QSignalBlocker(self.mode_tabs):
            self.mode_tabs.setCurrentIndex(valid_modes.index(active_mode))
        self._populate_groups()


class DuplicateSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self._loading = False
        self._folder_priority_syncing = False
        self._saved_preferred_folder_order: list[str] = [DUPLICATE_PREFERRED_FOLDERS_SENTINEL]
        self._folder_icon_provider = QFileIconProvider()
        self._folder_icon = self._folder_icon_provider.icon(QFileIconProvider.IconType.Folder)
        self._folder_icon_pixmap = self._folder_icon.pixmap(QSize(16, 16))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Similar File Rules"))

        self.rules_scroll = QScrollArea()
        self.rules_scroll.setObjectName("settingsPageScroll")
        self.rules_scroll.setWidgetResizable(True)
        self.rules_scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.rules_scroll, 1)

        self.rules_page = QWidget()
        self.rules_page.setObjectName("settingsScrollPage")
        rules_layout = QVBoxLayout(self.rules_page)
        rules_layout.setContentsMargins(0, 0, 15, 6)
        rules_layout.setSpacing(12)

        rules_group = QGroupBox("Preference Rules")
        rules_form = QFormLayout(rules_group)
        self.rule_combos: dict[str, QComboBox] = {}
        for key, label_text, options, _default in DUPLICATE_RULE_POLICIES:
            combo = QComboBox()
            for option_value, option_label in options:
                combo.addItem(option_label, option_value)
            combo.currentIndexChanged.connect(lambda _index, setting_key=key, widget=combo: self._on_rule_changed(setting_key, widget))
            rules_form.addRow(label_text, combo)
            self.rule_combos[key] = combo
        rules_layout.addWidget(rules_group)

        format_group = QGroupBox("Prefered File Format Order (Drag and Drop to Sort)")
        format_layout = QVBoxLayout(format_group)
        self.format_list = ReorderListWidget()
        self.format_list.setMinimumHeight(260)
        self.format_list.orderChanged.connect(self._save_format_order)
        format_layout.addWidget(self.format_list)
        rules_layout.addWidget(format_group, 1)

        folders_group = QGroupBox("Folder Priorities")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(10)
        self.use_preferred_folders_toggle = QCheckBox("Use Preferred Folders")
        self.use_preferred_folders_toggle.toggled.connect(self._on_preferred_folders_toggled)
        folders_layout.addWidget(self.use_preferred_folders_toggle)
        self.folder_priority_panel = QWidget()
        folder_priority_panel_layout = QVBoxLayout(self.folder_priority_panel)
        folder_priority_panel_layout.setContentsMargins(0, 0, 0, 0)
        folder_priority_panel_layout.setSpacing(8)
        folder_priority_panel_layout.addWidget(
            _description("Drag and Drop from Available folders on the left into your preferred order on the right")
        )
        lists_row = QHBoxLayout()
        lists_row.setContentsMargins(0, 0, 0, 0)
        lists_row.setSpacing(12)

        available_layout = QVBoxLayout()
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.setSpacing(6)
        available_layout.addWidget(QLabel("Available Folders"))
        self.available_folders_tree = FolderSourceTreeWidget()
        self.available_folders_tree.setMinimumHeight(260)
        available_layout.addWidget(self.available_folders_tree)
        lists_row.addLayout(available_layout, 1)

        prioritized_layout = QVBoxLayout()
        prioritized_layout.setContentsMargins(0, 0, 0, 0)
        prioritized_layout.setSpacing(6)
        prioritized_layout.addWidget(QLabel("Prioritized Folder Order"))
        self.prioritized_folders_list = PrioritizedFolderListWidget()
        self.prioritized_folders_list.setMinimumHeight(260)
        self.prioritized_folders_list.setItemDelegate(PrioritizedFolderItemDelegate(self, self.prioritized_folders_list))
        self.prioritized_folders_list.orderChanged.connect(self._sync_folder_priority_lists)
        self.prioritized_folders_list.removeRequested.connect(self._remove_prioritized_folder)
        prioritized_layout.addWidget(self.prioritized_folders_list)
        lists_row.addLayout(prioritized_layout, 1)

        folder_priority_panel_layout.addLayout(lists_row)
        folders_layout.addWidget(self.folder_priority_panel)
        rules_layout.addWidget(folders_group, 1)

        priorities_group = QGroupBox("Rule Priority Order (Drag and Drop to Sort)")
        priorities_layout = QVBoxLayout(priorities_group)
        self.priority_list = ReorderListWidget()
        self.priority_list.setMinimumHeight(260)
        self.priority_list.orderChanged.connect(self._save_priority_order)
        priorities_layout.addWidget(self.priority_list)
        rules_layout.addWidget(priorities_group)

        merge_group = QGroupBox("Metadata Merge")
        merge_layout = QVBoxLayout(merge_group)
        self.merge_before_delete_toggle = QCheckBox("Merge metadata before deleting duplicates")
        merge_layout.addWidget(self.merge_before_delete_toggle)
        merge_grid = QGridLayout()
        self.merge_toggles: dict[str, QCheckBox] = {}
        for index, (key, label_text, _default) in enumerate(DUPLICATE_MERGE_FIELDS):
            checkbox = QCheckBox(label_text)
            checkbox.toggled.connect(lambda checked, setting_key=key: self._on_merge_toggle_changed(setting_key, checked))
            merge_grid.addWidget(checkbox, index // 2, index % 2)
            self.merge_toggles[key] = checkbox
        merge_layout.addLayout(merge_grid)
        rules_layout.addWidget(merge_group)

        reset_group = QGroupBox("Reset Group Exclusions")
        reset_layout = QVBoxLayout(reset_group)
        reset_copy = QLabel(
            "When you click X on files in duplicate or similar groups MediaLens remembers that file should not "
            "be included in that group on future rescans. If you think you may have made mistakes excluding "
            "actual duplicates you can reset those exclusions below."
        )
        reset_copy.setWordWrap(True)
        reset_copy.setObjectName("settingsDescription")
        reset_layout.addWidget(reset_copy)
        self.reset_group_exclusions_btn = QPushButton("Reset Group Exclusions")
        self.reset_group_exclusions_btn.clicked.connect(self._reset_group_exclusions)
        reset_layout.addWidget(self.reset_group_exclusions_btn, 0, Qt.AlignmentFlag.AlignLeft)
        rules_layout.addWidget(reset_group)
        rules_layout.addStretch(1)
        self.rules_scroll.setWidget(self.rules_page)
        self.merge_before_delete_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("duplicate.rules.merge_before_delete", checked))

    def _on_rule_changed(self, key: str, combo: QComboBox) -> None:
        if not self._loading:
            self.dialog.set_setting_str(key, str(combo.currentData() or ""))

    def _save_format_order(self) -> None:
        if self._loading:
            return
        order = [str(self.format_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.format_list.count())]
        self.dialog.set_setting_str("duplicate.rules.format_order", json.dumps(order))

    def _save_priority_order(self) -> None:
        if self._loading:
            return
        order = [str(self.priority_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.priority_list.count())]
        self.dialog.set_setting_str("duplicate.priorities.order", json.dumps(order))

    def _preferred_folder_order(self) -> list[str]:
        order: list[str] = []
        for index in range(self.prioritized_folders_list.count()):
            value = str(self.prioritized_folders_list.item(index).data(Qt.ItemDataRole.UserRole) or "").strip()
            if value:
                order.append(value)
        if DUPLICATE_PREFERRED_FOLDERS_SENTINEL not in order:
            order.append(DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        return order

    @staticmethod
    def _normalize_folder_priority_order(raw: object) -> list[str]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        if isinstance(raw, list):
            parsed = raw
        else:
            try:
                parsed = json.loads(str(raw or "[]"))
            except Exception:
                parsed = []
        order: list[str] = []
        seen: set[str] = set()
        for item in parsed if isinstance(parsed, list) else []:
            text = str(item or "").strip()
            if not text:
                continue
            if text == DUPLICATE_PREFERRED_FOLDERS_SENTINEL:
                key = "__sentinel__"
                normalized = DUPLICATE_PREFERRED_FOLDERS_SENTINEL
            else:
                normalized = normalize_windows_path(text).rstrip("/")
                if not normalized:
                    continue
                key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            order.append(normalized)
        if DUPLICATE_PREFERRED_FOLDERS_SENTINEL not in order:
            order.append(DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        return order

    @staticmethod
    def _folder_item_text(folder_path: str) -> str:
        return folder_path if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else folder_path.replace("/", "\\")

    def _configure_prioritized_folder_item(self, item: QListWidgetItem, folder_path: str, *, centered: bool = False, extra_top_space: int = 0) -> None:
        item.setText(self._folder_item_text(folder_path))
        item.setIcon(QIcon() if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else self._folder_icon)
        item.setData(Qt.ItemDataRole.UserRole, folder_path)
        item.setToolTip("" if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else self._folder_item_text(folder_path))
        item.setData(FOLDER_PRIORITY_ROLE_CENTERED, bool(centered))
        item.setData(FOLDER_PRIORITY_ROLE_SENTINEL, folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        item.setData(FOLDER_PRIORITY_ROLE_EXTRA_TOP, int(extra_top_space))
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )

    def _add_folder_list_item(self, target: QListWidget, folder_path: str, *, centered: bool = False, extra_top_space: int = 0) -> None:
        item = QListWidgetItem()
        self._configure_prioritized_folder_item(item, folder_path, centered=centered, extra_top_space=extra_top_space)
        target.addItem(item)

    def _rebuild_prioritized_folder_row_widgets(self) -> None:
        count = self.prioritized_folders_list.count()
        sentinel_only = count == 1 and str(self.prioritized_folders_list.item(0).data(Qt.ItemDataRole.UserRole) or "") == DUPLICATE_PREFERRED_FOLDERS_SENTINEL
        viewport_height = max(0, self.prioritized_folders_list.viewport().height())
        for index in range(count):
            item = self.prioritized_folders_list.item(index)
            folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
            is_sentinel = folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL
            centered = sentinel_only and is_sentinel
            extra_top_space = 34 if is_sentinel and not centered and index == 0 else 0
            self._configure_prioritized_folder_item(item, folder_path, centered=centered, extra_top_space=extra_top_space)
            item.setSizeHint(QSize(0, max(96, viewport_height - 8) if centered else (74 if is_sentinel and index == 0 else (40 if is_sentinel else 32))))
        self.prioritized_folders_list.viewport().update()

    def _remove_prioritized_folder(self, folder_path: str) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL:
            return
        for index in range(self.prioritized_folders_list.count()):
            item = self.prioritized_folders_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole) or "") != folder_path:
                continue
            self.prioritized_folders_list.takeItem(index)
            self._sync_folder_priority_lists()
            return

    def _scope_folder_paths(self) -> list[str]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        selected_folders = list(getattr(self.bridge, "_selected_folders", []) or [])
        scope_folders: list[str] = []
        seen: set[str] = set()

        for raw_path in selected_folders:
            normalized = normalize_windows_path(str(raw_path or "")).rstrip("/")
            if normalized and normalized.casefold() not in seen:
                seen.add(normalized.casefold())
                scope_folders.append(normalized)

        for raw_root in selected_folders:
            root = Path(str(raw_root or "").strip())
            if not root.exists() or not root.is_dir():
                continue
            try:
                for child in root.rglob("*"):
                    if not child.is_dir():
                        continue
                    normalized = normalize_windows_path(str(child)).rstrip("/")
                    key = normalized.casefold()
                    if not normalized or key in seen:
                        continue
                    seen.add(key)
                    scope_folders.append(normalized)
            except Exception:
                continue
        return sorted(scope_folders, key=str.casefold)

    def _populate_available_folder_tree(self, scope_folders: list[str]) -> None:
        from app.mediamanager.utils.pathing import normalize_windows_path

        self.available_folders_tree.clear()
        selected_roots = []
        seen_roots: set[str] = set()
        for raw_root in list(getattr(self.bridge, "_selected_folders", []) or []):
            normalized = normalize_windows_path(str(raw_root or "")).rstrip("/")
            if not normalized or normalized.casefold() in seen_roots:
                continue
            seen_roots.add(normalized.casefold())
            selected_roots.append(normalized)

        children_by_parent: dict[str, list[str]] = {}
        for folder_path in scope_folders:
            parent = normalize_windows_path(str(Path(folder_path).parent)).rstrip("/")
            children_by_parent.setdefault(parent, []).append(folder_path)

        def add_node(parent_item: QTreeWidgetItem | None, folder_path: str) -> None:
            label = Path(folder_path).name or folder_path
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, folder_path)
            item.setToolTip(0, self._folder_item_text(folder_path))
            item.setIcon(0, self._folder_icon)
            if parent_item is None:
                self.available_folders_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            for child_path in sorted(children_by_parent.get(folder_path, []), key=str.casefold):
                add_node(item, child_path)

        for root_path in selected_roots:
            add_node(None, root_path)
        self.available_folders_tree.expandAll()

    def _save_preferred_folder_order(self) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        self._saved_preferred_folder_order = self._normalize_folder_priority_order(self._preferred_folder_order())
        raw_value = json.dumps(self._saved_preferred_folder_order)
        self.bridge.settings.setValue("duplicate/rules/preferred_folders_order", raw_value)
        self.bridge.settings.sync()
        try:
            self.bridge.uiFlagChanged.emit("duplicate.rules.preferred_folders_order", True)
        except Exception:
            pass

    def _apply_preferred_folder_sentinel_style(self) -> None:
        self._rebuild_prioritized_folder_row_widgets()

    def _schedule_preferred_folder_layout_refresh(self) -> None:
        QTimer.singleShot(0, self._apply_preferred_folder_sentinel_style)

    def _sync_folder_priority_lists(self) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        self._folder_priority_syncing = True
        try:
            scope_folders = self._scope_folder_paths()
            self._populate_available_folder_tree(scope_folders)
            current_order = self._preferred_folder_order()
            source_order = current_order if current_order else self._saved_preferred_folder_order
            normalized_order = self._normalize_folder_priority_order(source_order)
            self._saved_preferred_folder_order = list(normalized_order)

            self.prioritized_folders_list.clear()
            for path in self._saved_preferred_folder_order:
                self._add_folder_list_item(self.prioritized_folders_list, path)
            self._apply_preferred_folder_sentinel_style()
        finally:
            self._folder_priority_syncing = False
        self._save_preferred_folder_order()

    def _on_preferred_folders_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        self.folder_priority_panel.setVisible(bool(checked))
        self.bridge.settings.setValue("duplicate/rules/preferred_folders_enabled", bool(checked))
        self.bridge.settings.sync()
        try:
            self.bridge.uiFlagChanged.emit("duplicate.rules.preferred_folders_enabled", bool(checked))
        except Exception:
            pass
        if checked:
            self._sync_folder_priority_lists()
            self._schedule_preferred_folder_layout_refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "prioritized_folders_list"):
            self._schedule_preferred_folder_layout_refresh()

    def _on_merge_toggle_changed(self, key: str, checked: bool) -> None:
        if self._loading:
            return
        all_key = "duplicate.rules.merge.all"
        if key == all_key:
            self.dialog.set_setting_bool(all_key, checked)
            if checked:
                for setting_key, toggle in self.merge_toggles.items():
                    if setting_key == all_key:
                        continue
                    with QSignalBlocker(toggle):
                        toggle.setChecked(True)
                    self.dialog.set_setting_bool(setting_key, True)
            return

        self.dialog.set_setting_bool(key, checked)
        if not checked:
            all_toggle = self.merge_toggles.get(all_key)
            if all_toggle is not None and all_toggle.isChecked():
                with QSignalBlocker(all_toggle):
                    all_toggle.setChecked(False)
                self.dialog.set_setting_bool(all_key, False)

    def _reset_group_exclusions(self) -> None:
        self.dialog.reset_review_group_exclusions()

    def refresh(self) -> None:
        self._loading = True
        try:
            for key, _label, options, default_value in DUPLICATE_RULE_POLICIES:
                combo = self.rule_combos[key]
                current_value = str(self.settings.value(key.replace(".", "/"), default_value, type=str) or default_value)
                values = [option_value for option_value, _option_label in options]
                combo.setCurrentIndex(values.index(current_value) if current_value in values else values.index(default_value))
            self.format_list.clear()
            for format_name in _json_list(self.settings.value("duplicate/rules/format_order", "[]", type=str), DUPLICATE_FORMAT_ORDER_DEFAULT):
                item = QListWidgetItem(format_name)
                item.setData(Qt.ItemDataRole.UserRole, format_name)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                self.format_list.addItem(item)
            self.priority_list.clear()
            for label_text in _json_list(self.settings.value("duplicate/priorities/order", "[]", type=str), DUPLICATE_PRIORITY_ORDER_DEFAULT):
                item = QListWidgetItem(label_text)
                item.setData(Qt.ItemDataRole.UserRole, label_text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                self.priority_list.addItem(item)
            preferred_enabled = bool(self.settings.value("duplicate/rules/preferred_folders_enabled", False, type=bool))
            with QSignalBlocker(self.use_preferred_folders_toggle):
                self.use_preferred_folders_toggle.setChecked(preferred_enabled)
            self.folder_priority_panel.setVisible(preferred_enabled)
            self.available_folders_tree.clear()
            self.prioritized_folders_list.clear()
            self._saved_preferred_folder_order = self._normalize_folder_priority_order(
                self.settings.value("duplicate/rules/preferred_folders_order", "[]", type=str)
            )
            for folder_path in self._saved_preferred_folder_order:
                self._add_folder_list_item(self.prioritized_folders_list, folder_path)
            self._sync_folder_priority_lists()
            with QSignalBlocker(self.merge_before_delete_toggle):
                self.merge_before_delete_toggle.setChecked(bool(self.settings.value("duplicate/rules/merge_before_delete", False, type=bool)))
            for key, _label, default_value in DUPLICATE_MERGE_FIELDS:
                with QSignalBlocker(self.merge_toggles[key]):
                    self.merge_toggles[key].setChecked(bool(self.settings.value(key.replace(".", "/"), default_value, type=bool)))
        finally:
            self._loading = False
        self._sync_folder_priority_lists()
        self._schedule_preferred_folder_layout_refresh()


class AISettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        from app.mediamanager.ai_captioning.local_captioning import (
            CAPTION_MODEL_ID,
            DEFAULT_BAD_WORDS,
            DEFAULT_CAPTION_PROMPT,
            DEFAULT_CAPTION_START,
            TAG_MODEL_ID,
        )
        from app.mediamanager.ai_captioning.model_registry import MODEL_SPECS
        models_dir_default = self.bridge._local_ai_models_dir_default() if hasattr(self.bridge, "_local_ai_models_dir_default") else ""

        self.defaults = {
            "models_dir": models_dir_default,
            "tag_model_id": TAG_MODEL_ID,
            "caption_model_id": CAPTION_MODEL_ID,
            "tag_prompt": "",
            "caption_prompt": DEFAULT_CAPTION_PROMPT,
            "caption_start": DEFAULT_CAPTION_START,
            "bad_words": DEFAULT_BAD_WORDS,
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("AI"))
        layout.addWidget(_description("Local AI tagging and captioning writes directly to MediaLens database tags and descriptions."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        models_group = QGroupBox("Models")
        models_form = QFormLayout(models_group)
        models_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        models_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        content_layout.addWidget(models_group)

        models_row = QWidget()
        models_layout = QHBoxLayout(models_row)
        models_layout.setContentsMargins(0, 0, 0, 0)
        models_layout.setSpacing(6)
        self.models_dir_edit = QLineEdit()
        self.models_dir_edit.setClearButtonEnabled(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_models_dir)
        models_layout.addWidget(self.models_dir_edit, 1)
        models_layout.addWidget(browse_btn)
        models_form.addRow("Models Folder", models_row)

        self.device_combo = QComboBox()
        self.device_combo.addItem("GPU", "gpu")
        self.device_combo.addItem("CPU", "cpu")
        models_form.addRow("Device", self.device_combo)

        self.gpu_index_spin = QSpinBox()
        self.gpu_index_spin.setRange(0, 9)
        models_form.addRow("GPU Index", self.gpu_index_spin)

        self.load_4bit_toggle = QCheckBox("Load In 4-bit")
        models_form.addRow("", self.load_4bit_toggle)

        tags_group = QGroupBox("Tags")
        tags_form = QFormLayout(tags_group)
        tags_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        tags_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tags_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        tags_form.setVerticalSpacing(5)
        tags_form.setHorizontalSpacing(12)
        content_layout.addWidget(tags_group)

        self.tag_model_combo = QComboBox()
        for spec in MODEL_SPECS:
            if spec.kind == "tagger":
                self.tag_model_combo.addItem(spec.label, spec.id)
        tags_form.addRow("Tag Model", self.tag_model_combo)

        self.tag_model_description_label = QLabel("")
        self.tag_model_description_label.setWordWrap(True)
        self.tag_model_description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.tag_model_description_label.setMinimumHeight(22)
        self.tag_model_description_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tag_model_status_label = QLabel("")
        self.tag_model_status_label.setObjectName("aiSettingsModelStatus")
        self.tag_model_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.tag_model_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.tag_model_install_btn = QPushButton("Install Model")
        self.tag_model_install_btn.clicked.connect(lambda: self._install_selected_ai_model("tagger"))
        tag_model_status_row = QWidget()
        tag_model_status_layout = QHBoxLayout(tag_model_status_row)
        tag_model_status_layout.setContentsMargins(0, 0, 0, 0)
        tag_model_status_layout.setSpacing(8)
        tag_model_status_layout.addWidget(self.tag_model_status_label, 1)
        tag_model_status_layout.addWidget(self.tag_model_install_btn)
        tags_form.addRow("Description", self.tag_model_description_label)
        tags_form.addRow("Status", tag_model_status_row)

        self.tag_write_mode_combo = QComboBox()
        self.tag_write_mode_combo.addItem("Union Merge", "union")
        self.tag_write_mode_combo.addItem("Replace Tags", "replace")
        self.tag_write_mode_combo.addItem("Append Tags", "append")
        self.tag_write_mode_combo.addItem("Only If Empty", "skip_existing")
        self.tag_write_mode_combo.setItemData(0, "Append without duplicates", Qt.ItemDataRole.ToolTipRole)
        self.tag_write_mode_combo.setToolTip("Append without duplicates")
        tags_form.addRow("Tag Write Rule", self.tag_write_mode_combo)

        self.tag_prompt_edit = QTextEdit()
        self.tag_prompt_edit.setMinimumHeight(90)
        self.tag_prompt_edit.setPlaceholderText("Tag prompt and rules.")
        tags_form.addRow("Tag Prompt", self.tag_prompt_edit)

        self.tags_to_exclude_edit = QLineEdit()
        self.tags_to_exclude_edit.setPlaceholderText("Comma-separated tags to exclude")
        tags_form.addRow("Exclude Tags", self.tags_to_exclude_edit)

        self.tag_min_probability_edit = QLineEdit()
        tags_form.addRow("Tag Min Probability", self.tag_min_probability_edit)

        self.tag_max_tags_spin = QSpinBox()
        self.tag_max_tags_spin.setRange(1, 500)
        tags_form.addRow("Number of Tags", self.tag_max_tags_spin)

        descriptions_group = QGroupBox("Descriptions")
        descriptions_form = QFormLayout(descriptions_group)
        descriptions_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        descriptions_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        descriptions_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        descriptions_form.setVerticalSpacing(5)
        descriptions_form.setHorizontalSpacing(12)
        content_layout.addWidget(descriptions_group)

        self.caption_model_combo = QComboBox()
        for spec in MODEL_SPECS:
            if spec.kind == "captioner":
                self.caption_model_combo.addItem(spec.label, spec.id)
        descriptions_form.addRow("Description Model", self.caption_model_combo)

        self.caption_model_description_label = QLabel("")
        self.caption_model_description_label.setWordWrap(True)
        self.caption_model_description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.caption_model_description_label.setMinimumHeight(22)
        self.caption_model_description_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.caption_model_status_label = QLabel("")
        self.caption_model_status_label.setObjectName("aiSettingsModelStatus")
        self.caption_model_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.caption_model_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.caption_model_install_btn = QPushButton("Install Model")
        self.caption_model_install_btn.clicked.connect(lambda: self._install_selected_ai_model("captioner"))
        caption_model_status_row = QWidget()
        caption_model_status_layout = QHBoxLayout(caption_model_status_row)
        caption_model_status_layout.setContentsMargins(0, 0, 0, 0)
        caption_model_status_layout.setSpacing(8)
        caption_model_status_layout.addWidget(self.caption_model_status_label, 1)
        caption_model_status_layout.addWidget(self.caption_model_install_btn)
        descriptions_form.addRow("Description", self.caption_model_description_label)
        descriptions_form.addRow("Status", caption_model_status_row)

        self.description_write_mode_combo = QComboBox()
        self.description_write_mode_combo.addItem("Overwrite Description", "overwrite")
        self.description_write_mode_combo.addItem("Append Description", "append")
        self.description_write_mode_combo.addItem("Only If Empty", "skip_existing")
        descriptions_form.addRow("Description Rule", self.description_write_mode_combo)

        self.caption_prompt_edit = QTextEdit()
        self.caption_prompt_edit.setMinimumHeight(120)
        self.caption_prompt_edit.setPlaceholderText("Prompt. Use {tags} to insert tags and {starter} to place the starter.")
        descriptions_form.addRow("Description Prompt", self.caption_prompt_edit)

        self.caption_start_edit = QLineEdit()
        descriptions_form.addRow("Start Description With", self.caption_start_edit)

        self.bad_words_edit = QLineEdit()
        descriptions_form.addRow("Discourage", self.bad_words_edit)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2048)
        descriptions_form.addRow("Maximum Tokens", self.max_tokens_spin)

        save_btn = QPushButton("Save AI Settings")
        save_btn.clicked.connect(self._save)
        content_layout.addWidget(save_btn)
        content_layout.addStretch(1)

        for widget in (
            self.models_dir_edit,
            self.caption_start_edit,
            self.bad_words_edit,
            self.tags_to_exclude_edit,
            self.tag_min_probability_edit,
        ):
            widget.editingFinished.connect(self._save)
        for combo in (
            self.tag_model_combo,
            self.caption_model_combo,
            self.tag_write_mode_combo,
            self.description_write_mode_combo,
            self.device_combo,
        ):
            combo.currentIndexChanged.connect(self._save)
        self.tag_model_combo.currentIndexChanged.connect(lambda _index: self._refresh_ai_model_statuses())
        self.caption_model_combo.currentIndexChanged.connect(lambda _index: self._refresh_ai_model_statuses())
        if hasattr(self.bridge, "localAiModelInstallStatus"):
            self.bridge.localAiModelInstallStatus.connect(self._on_local_ai_model_install_status)
        self.tag_prompt_edit.textChanged.connect(self._save)
        self.caption_prompt_edit.textChanged.connect(self._save)
        self.tag_max_tags_spin.valueChanged.connect(self._save)
        self.gpu_index_spin.valueChanged.connect(self._save)
        self.load_4bit_toggle.toggled.connect(self._save)
        self.max_tokens_spin.valueChanged.connect(self._save)
        self.refresh()

    def _setting(self, key: str, default, value_type=None):
        qkey = key.replace(".", "/")
        if value_type is None:
            return self.settings.value(qkey, default)
        return self.settings.value(qkey, default, type=value_type)

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _selected_ai_model_id(self, kind: str) -> str:
        combo = self.tag_model_combo if kind == "tagger" else self.caption_model_combo
        return str(combo.currentData() or "")

    def _apply_ai_model_status(self, kind: str, status: dict) -> None:
        description_label = self.tag_model_description_label if kind == "tagger" else self.caption_model_description_label
        status_label = self.tag_model_status_label if kind == "tagger" else self.caption_model_status_label
        button = self.tag_model_install_btn if kind == "tagger" else self.caption_model_install_btn
        state = str(status.get("state") or "").strip()
        description = str(status.get("description") or "").strip()
        message = str(status.get("message") or "").strip()
        Theme = _theme_api()
        is_light = Theme.get_is_light()
        ok_color = "#238636" if is_light else "#7ee787"
        bad_color = "#c62828" if is_light else "#ff7b72"
        if state == "installed":
            status_text = f'<span style="color:{ok_color};">✓</span> Installed'
        elif state == "installing":
            status_text = "Installing..."
        elif state == "not_installed":
            status_text = f'<span style="color:{bad_color};">✕</span> Not installed'
        elif state == "error":
            clean_error = html.escape(message) if message else "Error"
            status_text = f'<span style="color:{bad_color};">✕</span> {clean_error}'
        else:
            status_text = html.escape(message or "Status unavailable")
        description_label.setText(description or "No description available.")
        status_label.setText(status_text)
        status_label.setProperty("installState", state or "unknown")
        status_label.style().unpolish(status_label)
        status_label.style().polish(status_label)
        button.setVisible(state in {"not_installed", "error", "installing"})
        button.setEnabled(state in {"not_installed", "error"})
        button.setText("Installing..." if state == "installing" else "Install Model")

    def _refresh_ai_model_statuses(self) -> None:
        if bool(getattr(self, "_loading", False)):
            return
        for kind in ("tagger", "captioner"):
            model_id = self._selected_ai_model_id(kind)
            if not model_id:
                continue
            if hasattr(self.bridge, "get_local_ai_model_status"):
                try:
                    self._apply_ai_model_status(kind, dict(self.bridge.get_local_ai_model_status(model_id, kind) or {}))
                except Exception as exc:
                    self._apply_ai_model_status(kind, {"state": "error", "message": str(exc) or "Could not read model status."})

    def _install_selected_ai_model(self, kind: str) -> None:
        model_id = self._selected_ai_model_id(kind)
        if not model_id or not hasattr(self.bridge, "install_local_ai_model"):
            return
        status = dict(self.bridge.get_local_ai_model_status(model_id, kind) or {}) if hasattr(self.bridge, "get_local_ai_model_status") else {}
        label = str(status.get("label") or "this model")
        size = str(status.get("estimated_size") or "").strip()
        message = f"Install {label} local AI support?"
        if size:
            message = f"{message}\n\nEstimated size: {size}"
        message = f"{message}\n\nThis downloads packages and model files from the internet as needed."
        reply = QMessageBox.question(self, "Install AI Model", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        started = bool(self.bridge.install_local_ai_model(model_id, kind))
        if not started:
            self._refresh_ai_model_statuses()

    def _on_local_ai_model_install_status(self, status_key: str, payload: dict) -> None:
        payload = dict(payload or {})
        for kind in ("tagger", "captioner"):
            current = {}
            if hasattr(self.bridge, "get_local_ai_model_status"):
                try:
                    current = dict(self.bridge.get_local_ai_model_status(self._selected_ai_model_id(kind), kind) or {})
                except Exception:
                    current = {}
            if str(current.get("settings_key") or "") == str(status_key or ""):
                self._apply_ai_model_status(kind, payload)

    def _browse_models_dir(self) -> None:
        current = self.models_dir_edit.text().strip() or self.defaults["models_dir"]
        selected = QFileDialog.getExistingDirectory(self, "Select Local AI Models Folder", current)
        if selected:
            self.models_dir_edit.setText(selected)
            self._save()

    def _save(self) -> None:
        if bool(getattr(self, "_loading", False)):
            return
        s = self.settings
        s.setValue("ai_caption/models_dir", self.models_dir_edit.text().strip() or self.defaults["models_dir"])
        s.setValue("ai_caption/tag_model_id", self.tag_model_combo.currentData() or self.defaults["tag_model_id"])
        s.setValue("ai_caption/caption_model_id", self.caption_model_combo.currentData() or self.defaults["caption_model_id"])
        s.setValue("ai_caption/tag_write_mode", self.tag_write_mode_combo.currentData() or "union")
        s.setValue("ai_caption/description_write_mode", self.description_write_mode_combo.currentData() or "overwrite")
        s.setValue("ai_caption/tag_prompt", self.tag_prompt_edit.toPlainText().strip())
        s.setValue("ai_caption/caption_prompt", self.caption_prompt_edit.toPlainText().strip() or self.defaults["caption_prompt"])
        s.setValue("ai_caption/caption_start", self.caption_start_edit.text())
        s.setValue("ai_caption/bad_words", self.bad_words_edit.text())
        s.setValue("ai_caption/tags_to_exclude", self.tags_to_exclude_edit.text())
        try:
            min_probability = float(self.tag_min_probability_edit.text().strip())
        except Exception:
            min_probability = 0.35
        s.setValue("ai_caption/tag_min_probability", max(0.0, min(1.0, min_probability)))
        s.setValue("ai_caption/tag_max_tags", self.tag_max_tags_spin.value())
        s.setValue("ai_caption/device", self.device_combo.currentData() or "gpu")
        s.setValue("ai_caption/gpu_index", self.gpu_index_spin.value())
        s.setValue("ai_caption/load_in_4_bit", self.load_4bit_toggle.isChecked())
        s.setValue("ai_caption/max_new_tokens", self.max_tokens_spin.value())
        s.setValue("ai_caption/min_new_tokens", 1)
        s.setValue("ai_caption/num_beams", 1)
        s.setValue("ai_caption/length_penalty", 1.0)
        s.setValue("ai_caption/do_sample", False)
        s.setValue("ai_caption/temperature", 1.0)
        s.setValue("ai_caption/top_k", 50)
        s.setValue("ai_caption/top_p", 1.0)
        s.setValue("ai_caption/repetition_penalty", 1.0)
        s.setValue("ai_caption/no_repeat_ngram_size", 3)
        s.sync()

    def refresh(self) -> None:
        self._loading = True
        try:
            self.models_dir_edit.setText(str(self._setting("ai_caption.models_dir", self.defaults["models_dir"], str) or self.defaults["models_dir"]))
            self._set_combo_data(self.tag_model_combo, str(self._setting("ai_caption.tag_model_id", self.defaults["tag_model_id"], str) or self.defaults["tag_model_id"]))
            self._set_combo_data(self.caption_model_combo, str(self._setting("ai_caption.caption_model_id", self.defaults["caption_model_id"], str) or self.defaults["caption_model_id"]))
            self._set_combo_data(self.tag_write_mode_combo, str(self._setting("ai_caption.tag_write_mode", "union", str) or "union"))
            self._set_combo_data(self.description_write_mode_combo, str(self._setting("ai_caption.description_write_mode", "overwrite", str) or "overwrite"))
            self.tag_prompt_edit.setPlainText(str(self._setting("ai_caption.tag_prompt", self.defaults["tag_prompt"], str) or self.defaults["tag_prompt"]))
            self.caption_prompt_edit.setPlainText(str(self._setting("ai_caption.caption_prompt", self.defaults["caption_prompt"], str) or self.defaults["caption_prompt"]))
            self.caption_start_edit.setText(str(self._setting("ai_caption.caption_start", self.defaults["caption_start"], str) or self.defaults["caption_start"]))
            self.bad_words_edit.setText(str(self._setting("ai_caption.bad_words", self.defaults["bad_words"], str) or self.defaults["bad_words"]))
            self.tags_to_exclude_edit.setText(str(self._setting("ai_caption.tags_to_exclude", "", str) or ""))
            self.tag_min_probability_edit.setText(str(self._setting("ai_caption.tag_min_probability", 0.35, float) or 0.35))
            self.tag_max_tags_spin.setValue(int(self._setting("ai_caption.tag_max_tags", 75, int) or 75))
            self._set_combo_data(self.device_combo, str(self._setting("ai_caption.device", "gpu", str) or "gpu"))
            self.gpu_index_spin.setValue(int(self._setting("ai_caption.gpu_index", 0, int) or 0))
            self.load_4bit_toggle.setChecked(bool(self._setting("ai_caption.load_in_4_bit", False, bool)))
            self.max_tokens_spin.setValue(int(self._setting("ai_caption.max_new_tokens", 200, int) or 200))
        finally:
            self._loading = False
        self._refresh_ai_model_statuses()


class LocalAiSetupDialog(QDialog):
    def __init__(self, main_window: QWidget, focus_kind: str = "") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.bridge = main_window.bridge
        self.focus_kind = str(focus_kind or "").strip()
        self.setWindowTitle("Local AI Models")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(760, 540)
        self.setModal(False)
        self._rows: dict[str, dict[str, object]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Local AI Models")
        title.setObjectName("localAiSetupTitle")
        title_font = title.font()
        title_font.setPointSize(max(title_font.pointSize() + 4, 14))
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        intro = QLabel("Install the local AI models you want to use.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.rows_layout = QVBoxLayout(content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_statuses)
        self.close_btn = QPushButton("Close")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        buttons.addWidget(self.refresh_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

        if hasattr(self.bridge, "localAiModelInstallStatus"):
            self.bridge.localAiModelInstallStatus.connect(self._on_install_status)
        if hasattr(self.bridge, "accentColorChanged"):
            self.bridge.accentColorChanged.connect(lambda _value: self._apply_theme())

        self._build_rows()
        self.refresh_statuses()
        self._apply_theme()

    def _unique_model_specs(self):
        from app.mediamanager.ai_captioning.model_registry import MODEL_SPECS

        rows: dict[str, dict[str, object]] = {}
        for spec in MODEL_SPECS:
            row = rows.setdefault(
                spec.settings_key,
                {
                    "spec": spec,
                    "kinds": set(),
                },
            )
            row["kinds"].add(spec.kind)
        return rows

    @staticmethod
    def _capabilities_label(kinds: set[str]) -> str:
        labels = []
        if "tagger" in kinds:
            labels.append("tags")
        if "captioner" in kinds:
            labels.append("descriptions")
        return ", ".join(labels) if labels else "local AI"

    def _build_rows(self) -> None:
        for status_key, item in self._unique_model_specs().items():
            spec = item["spec"]
            kinds = item["kinds"]
            frame = QFrame()
            frame.setObjectName("localAiModelRow")
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            layout = QGridLayout(frame)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setHorizontalSpacing(20)
            layout.setVerticalSpacing(0)

            details_panel = QWidget()
            details_layout = QVBoxLayout(details_panel)
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(0)
            name = QLabel(spec.label)
            name.setObjectName("localAiModelName")
            name_font = name.font()
            name_font.setBold(True)
            name.setFont(name_font)
            details_layout.addWidget(name)

            metadata = QWidget()
            metadata_layout = QVBoxLayout(metadata)
            metadata_layout.setContentsMargins(0, 8, 0, 0)
            metadata_layout.setSpacing(3)
            detail_rows = (
                ("Use", self._capabilities_label(kinds)),
                ("Description", str(spec.description or "")),
                ("Size", str(spec.estimated_size or "")),
            )
            for label, value in detail_rows:
                detail = QLabel(f"<b>{html.escape(label)}:</b> {html.escape(value)}")
                detail.setObjectName("localAiModelDetails")
                detail.setTextFormat(Qt.TextFormat.RichText)
                detail.setWordWrap(True)
                detail.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                metadata_layout.addWidget(detail)
            details_layout.addWidget(metadata)
            layout.addWidget(details_panel, 0, 0)

            actions_panel = QWidget()
            actions_layout = QVBoxLayout(actions_panel)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(8)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

            status_badge = QLabel("Checking")
            status_badge.setObjectName("localAiStatusBadge")
            status_badge.setTextFormat(Qt.TextFormat.RichText)
            badge_font = status_badge.font()
            badge_font.setBold(True)
            status_badge.setFont(badge_font)
            status_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_badge.setMinimumWidth(178)
            actions_layout.addWidget(status_badge)

            install_btn = QPushButton("Install")
            install_btn.setObjectName("localAiInstallButton")
            install_btn.setFixedHeight(28)
            install_btn.setMinimumWidth(178)
            install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            install_btn.clicked.connect(lambda _checked=False, s=spec: self._install_model(s))
            actions_layout.addWidget(install_btn)

            uninstall_btn = QPushButton("Uninstall")
            uninstall_btn.setObjectName("localAiUninstallButton")
            uninstall_btn.setFixedHeight(28)
            uninstall_btn.setMinimumWidth(178)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.clicked.connect(lambda _checked=False, s=spec: self._uninstall_model(s))
            actions_layout.addWidget(uninstall_btn)
            actions_layout.addStretch(1)

            layout.addWidget(actions_panel, 0, 1)
            layout.setColumnStretch(0, 1)
            layout.setColumnMinimumWidth(1, 178)

            self.rows_layout.addWidget(frame)
            self._rows[status_key] = {
                "spec": spec,
                "badge": status_badge,
                "button": install_btn,
                "uninstall_button": uninstall_btn,
                "frame": frame,
            }
        self.rows_layout.addStretch(1)

    def refresh_statuses(self) -> None:
        for status_key, row in self._rows.items():
            spec = row["spec"]
            status = self._status_for_spec(spec)
            self._apply_status(status_key, status)

    def _status_for_spec(self, spec) -> dict:
        if not hasattr(self.bridge, "get_local_ai_model_status"):
            return {"state": "error", "message": "Local AI status is not available in this build."}
        try:
            return dict(self.bridge.get_local_ai_model_status(spec.id, spec.kind) or {})
        except Exception as exc:
            return {"state": "error", "message": str(exc) or "Could not read model status."}

    def _apply_status(self, status_key: str, status: dict) -> None:
        row = self._rows.get(status_key)
        if not row:
            return
        badge = row["badge"]
        button = row["button"]
        uninstall_button = row["uninstall_button"]
        frame = row["frame"]
        state = str(status.get("state") or "").strip()
        Theme = _theme_api()
        is_light = Theme.get_is_light()
        ok_color = "#238636" if is_light else "#7ee787"
        bad_color = "#c62828" if is_light else "#ff7b72"
        if state == "installed":
            badge.setText(f'<span style="color:{ok_color};">✓</span> Installed')
        elif state == "installing":
            badge.setText("Installing")
        elif state == "error":
            badge.setText(f'<span style="color:{bad_color};">✕</span> Error')
        elif state == "not_installed":
            badge.setText(f'<span style="color:{bad_color};">✕</span> Not installed')
        else:
            badge.setText("Unknown")
        frame.setProperty("installState", state or "unknown")
        badge.setProperty("installState", state or "unknown")
        frame.style().unpolish(frame)
        frame.style().polish(frame)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        badge.setVisible(state in {"installed", "error"})
        button.setVisible(state in {"not_installed", "error", "installing"})
        button.setEnabled(state in {"not_installed", "error"})
        button.setText("Installing..." if state == "installing" else "Install")
        uninstall_button.setVisible(state == "installed")
        uninstall_button.setEnabled(state == "installed")

    def _install_model(self, spec) -> None:
        if not hasattr(self.bridge, "install_local_ai_model"):
            self._apply_status(spec.settings_key, {"state": "error", "message": "Model installation is not available in this build."})
            return
        self.bridge.install_local_ai_model(spec.id, spec.kind)
        self.refresh_statuses()

    def _uninstall_model(self, spec) -> None:
        if not hasattr(self.bridge, "uninstall_local_ai_model"):
            self._apply_status(spec.settings_key, {"state": "error", "message": "Model uninstall is not available in this build."})
            return
        reply = QMessageBox.question(
            self,
            "Uninstall AI Model",
            f"Uninstall {spec.label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.bridge.uninstall_local_ai_model(spec.id, spec.kind)
        self.refresh_statuses()

    def _on_install_status(self, status_key: str, payload: dict) -> None:
        self._apply_status(str(status_key or ""), dict(payload or {}))

    def _apply_theme(self) -> None:
        Theme = _theme_api()
        accent = QColor(str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))
        if not accent.isValid():
            accent = QColor(Theme.ACCENT_DEFAULT)
        Theme.set_theme_mode(str(self.bridge.settings.value("ui/theme_mode", "dark", type=str) or "dark"))
        bg = Theme.get_bg(accent)
        control_bg = Theme.get_control_bg(accent)
        sidebar_bg = Theme.get_sidebar_bg(accent)
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        muted = Theme.get_text_muted()
        hover = Theme.get_btn_save_hover(accent)
        accent_soft = Theme.get_accent_soft(accent)
        accent_str = accent.name()
        missing_fg = "#7c1f11" if Theme.get_is_light() else "#ffd1c7"
        error_fg = "#8a111a" if Theme.get_is_light() else "#ffd0d4"
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
            }}
            QLabel#localAiSetupTitle {{
                color: {text};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea QWidget {{
                background: transparent;
            }}
            QFrame#localAiModelRow {{
                background-color: {sidebar_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame#localAiModelRow[installState="not_installed"] {{
                border-color: {missing_fg};
            }}
            QFrame#localAiModelRow[installState="error"] {{
                border-color: {error_fg};
            }}
            QLabel#localAiStatusBadge {{
                color: {text};
                background: transparent;
                border: none;
                padding: 0;
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#localAiStatusBadge[installState="error"] {{
                color: {error_fg};
            }}
            QPushButton {{
                background-color: {Theme.get_btn_save_bg(accent)};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 3px 10px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border-color: {accent_str};
            }}
            QPushButton:pressed {{
                background-color: {Theme.mix(hover, accent, 0.12)};
                border-color: {accent_str};
            }}
            QPushButton:disabled {{
                color: {muted};
                background-color: {control_bg};
                border-color: {border};
            }}
            QPushButton#localAiInstallButton {{
                background-color: {accent_soft};
                border-color: {accent_str};
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton#localAiInstallButton:hover, QPushButton#localAiUninstallButton:hover {{
                background-color: {hover};
                border-color: {accent_str};
            }}
            QPushButton#localAiUninstallButton {{
                background-color: {Theme.get_btn_save_bg(accent)};
                border-color: {border};
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QScrollBar:vertical {{
                background: {Theme.get_scrollbar_track(accent)};
                width: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.get_scrollbar_thumb(accent)};
                border-radius: 5px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.get_scrollbar_thumb_hover(accent)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)


def _theme_api():
    from native.mediamanagerx_app.main import Theme

    return Theme


class SettingsDialog(QDialog):
    def __init__(self, main_window: QWidget) -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.bridge = main_window.bridge
        self.settings = self.bridge.settings
        self.setWindowTitle("Settings")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(980, 720)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        self.category_container = QWidget()
        category_shell_layout = QVBoxLayout(self.category_container)
        category_shell_layout.setContentsMargins(3, 0, 0, 0)
        category_shell_layout.setSpacing(0)

        self.category_frame = QWidget()
        self.category_frame.setObjectName("settingsCategoryFrame")
        self.category_frame.setFixedWidth(240)
        category_frame_layout = QVBoxLayout(self.category_frame)
        category_frame_layout.setContentsMargins(6, 6, 6, 6)
        category_frame_layout.setSpacing(0)

        self.category_list = QListWidget()
        self.category_list.setObjectName("settingsCategoryList")
        self.category_list.setAlternatingRowColors(False)
        self.category_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.category_list.setSpacing(3)
        category_frame_layout.addWidget(self.category_list)
        category_shell_layout.addWidget(self.category_frame)
        body.addWidget(self.category_container)

        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)

        self._page_defs = [
            ("General", GeneralSettingsPage(self)),
            ("Appearance", AppearanceSettingsPage(self)),
            ("Player", PlayerSettingsPage(self)),
            ("Scanners", ScannersSettingsPage(self)),
            ("Metadata", MetadataSettingsPage(self)),
            ("Similar File Rules", DuplicateSettingsPage(self)),
            ("AI", AISettingsPage(self)),
        ]
        for title, page in self._page_defs:
            self.category_list.addItem(title)
            self.pages.addWidget(page)

        self.category_list.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.category_list.setCurrentRow(0)
        self.bridge.accentColorChanged.connect(lambda _value: self.refresh_from_settings())
        self.bridge.uiFlagChanged.connect(self._on_ui_flag_changed)
        self._apply_theme()

    def showEvent(self, event) -> None:
        self.refresh_from_settings()
        super().showEvent(event)
        self._apply_native_title_bar_theme()

    def open_dialog(self) -> None:
        if self.isVisible():
            self.refresh_from_settings()
            self.raise_()
            self.activateWindow()
            return
        self.open()
        self.raise_()
        self.activateWindow()

    def refresh_from_settings(self) -> None:
        current_row = max(self.category_list.currentRow(), 0)
        self._apply_theme()
        for _title, page in self._page_defs:
            page.refresh()
        if self.category_list.count():
            self.category_list.setCurrentRow(current_row)

    def _on_ui_flag_changed(self, key: str, _value: bool) -> None:
        if key == "ui.theme_mode":
            self.refresh_from_settings()
            self._apply_native_title_bar_theme()

    def _apply_native_title_bar_theme(self) -> None:
        if sys.platform != "win32" or not self.isVisible():
            return
        try:
            Theme = _theme_api()
            hwnd = int(self.winId())
            is_light = Theme.get_is_light()
            bg_color = QColor("#ffffff" if is_light else Theme.BASE_SIDEBAR_BG_DARK)
            mode_value = ctypes.c_int(0 if is_light else 1)
            for attr in (20, 19):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(mode_value), ctypes.sizeof(mode_value)
                )
            bg_ref = (bg_color.blue() << 16) | (bg_color.green() << 8) | bg_color.red()
            bg_value = ctypes.c_int(bg_ref)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(bg_value), ctypes.sizeof(bg_value)
            )
            text_value = ctypes.c_int(0x00000000 if is_light else 0x00FFFFFF)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(text_value), ctypes.sizeof(text_value)
            )
        except Exception:
            pass

    def _apply_theme(self) -> None:
        Theme = _theme_api()
        accent = QColor(str(self.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT))
        if not hasattr(self, "_proxy_style"):
            self._proxy_style = SettingsProxyStyle(self.style())
            self.setStyle(self._proxy_style)
        bg = Theme.get_bg(accent)
        sidebar_bg = Theme.get_sidebar_bg(accent)
        control_bg = Theme.get_control_bg(accent)
        border = Theme.get_border(accent)
        text = Theme.get_text_color()
        muted = Theme.get_text_muted()
        hover = Theme.get_btn_save_hover(accent)
        accent_soft = Theme.get_accent_soft(accent)
        accent_str = accent.name()
        self._proxy_style.update_colors(accent, control_bg, border, text, Theme.get_is_light())
        selection_text = "#000000" if SettingsProxyStyle._contrast_ratio(accent, QColor("#000000")) >= SettingsProxyStyle._contrast_ratio(accent, QColor("#ffffff")) else "#ffffff"
        category_hover = Theme.mix(sidebar_bg, accent, 0.10 if Theme.get_is_light() else 0.14)
        popup_bg = "#ffffff" if Theme.get_is_light() else Theme.mix(control_bg, "#000000", 0.24)
        popup_border = "#cfd5dd" if Theme.get_is_light() else Theme.mix(border, "#000000", 0.20)
        popup_hover = Theme.mix(popup_bg, accent, 0.12 if Theme.get_is_light() else 0.16)
        close_bg = Theme.get_btn_save_bg(accent)
        close_hover = Theme.get_btn_save_hover(accent)
        installed_bg = Theme.mix(control_bg, QColor("#2f8f46"), 0.20 if Theme.get_is_light() else 0.24)
        installed_fg = "#145523" if Theme.get_is_light() else "#bdf5ca"
        missing_bg = Theme.mix(control_bg, QColor("#c9563d"), 0.22 if Theme.get_is_light() else 0.26)
        missing_fg = "#7c1f11" if Theme.get_is_light() else "#ffd1c7"
        installing_bg = Theme.mix(control_bg, accent, 0.22 if Theme.get_is_light() else 0.26)
        error_bg = Theme.mix(control_bg, QColor("#d33f49"), 0.24 if Theme.get_is_light() else 0.28)
        error_fg = "#8a111a" if Theme.get_is_light() else "#ffd0d4"
        
        for btn in self.findChildren(QPushButton):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
            }}
            QLabel:disabled {{
                color: {muted};
            }}
            QLabel#settingsSectionTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {text};
            }}
            QLabel#settingsDescription {{
                color: {muted};
            }}
            QLabel#aiSettingsModelStatus {{
                font-size: 13px;
                font-weight: 700;
                color: {text};
                border: none;
                padding: 0;
                background: transparent;
            }}
            QLabel#aiSettingsModelStatus[installState="installing"] {{
                color: {accent_str};
            }}
            QLabel#settingsFieldTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {text};
            }}
            QListWidget {{
                color: {text};
                outline: none;
            }}
            QWidget#settingsCategoryFrame {{
                background-color: {sidebar_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QListWidget#settingsCategoryList {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
            }}
            QListWidget#settingsCategoryList::item {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px 14px;
                margin: 1px 0;
                color: {text};
            }}
            QListWidget#settingsCategoryList::item:hover {{
                background: {category_hover};
            }}
            QListWidget#settingsCategoryList::item:selected {{
                background: {accent_soft};
                border: 1px solid {accent_str};
                color: {text};
            }}
            QListWidget#settingsReorderList, QTreeWidget#settingsReorderList {{
                background-color: {control_bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
            }}
            QListWidget#settingsReorderList::item, QTreeWidget#settingsReorderList::item {{
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 6px 10px;
                margin: 0;
                color: {text};
            }}
            QListWidget#settingsReorderList::item:hover, QTreeWidget#settingsReorderList::item:hover {{
                background: {category_hover};
            }}
            QListWidget#settingsReorderList::item:selected, QTreeWidget#settingsReorderList::item:selected {{
                background: {accent_soft};
                border: 1px solid {accent_str};
                color: {text};
            }}
            QTreeWidget#settingsReorderList {{
                outline: none;
            }}
            QLabel#folderPriorityRowLabel {{
                color: {text};
                background: transparent;
            }}
            QFrame#folderPriorityDivider {{
                color: {border};
                background: {border};
                min-height: 2px;
                max-height: 2px;
                border: none;
            }}
            QPushButton#folderPriorityRemoveButton {{
                background: transparent;
                color: {muted};
                border: 1px solid transparent;
                border-radius: 5px;
                padding: 0;
                font-weight: 700;
            }}
            QPushButton#folderPriorityRemoveButton:hover {{
                background: {category_hover};
                color: {text};
                border-color: {border};
            }}
            QGroupBox {{
                margin-top: 10px;
                padding-top: 8px;
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QScrollArea#settingsPageScroll, QWidget#settingsScrollPage {{
                background-color: {bg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: {muted};
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QListWidget#qt_spinbox_lineedit {{
                background-color: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 5px 8px;
                selection-background-color: {accent_str};
                selection-color: {selection_text};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {accent_str};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {popup_bg};
                color: {text};
                border: 1px solid {popup_border};
                border-radius: 8px;
                padding: 6px;
                margin-top: 6px;
                selection-background-color: {accent_soft};
                selection-color: {text};
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 24px;
                padding: 6px 10px;
                margin: 2px 0;
                border-radius: 6px;
                background: transparent;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: {popup_hover};
            }}
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
            QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
                background-color: transparent;
                color: {muted};
                border: 1px solid {border};
            }}
            QCheckBox, QRadioButton {{
                color: {text};
                spacing: 8px;
            }}
            QTabBar::tab {{
                background: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-bottom: none;
                padding: 7px 12px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {accent_soft};
                border-color: {accent_str};
            }}
            QTabBar#settingsModeTabs::tab {{
                background: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 8px 12px 10px 12px;
                margin-right: 6px;
                min-height: 18px;
            }}
            QTabBar#settingsModeTabs::tab:selected {{
                background: {accent_soft};
                border-color: {accent_str};
            }}
            QScrollBar:vertical {{
                background: {bg};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.get_scrollbar_thumb(accent)};
                min-height: 28px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.get_scrollbar_thumb_hover(accent)};
            }}
            QScrollBar:horizontal {{
                background: {bg};
                height: 12px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {Theme.get_scrollbar_thumb(accent)};
                min-width: 28px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {Theme.get_scrollbar_thumb_hover(accent)};
            }}
            QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
                border: none;
            }}
            QDialogButtonBox QPushButton {{
                min-width: 88px;
            }}
            """
        )
        for widget in self.findChildren(QLineEdit):
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Highlight, accent)
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(selection_text))
            widget.setPalette(palette)

    def set_setting_bool(self, key: str, value: bool) -> None:
        try:
            self.bridge.set_setting_bool(key, bool(value))
        except Exception:
            pass
        self.settings.setValue(key.replace(".", "/"), bool(value))
        self.settings.sync()

    def set_setting_str(self, key: str, value: str) -> None:
        try:
            self.bridge.set_setting_str(key, str(value or ""))
        except Exception:
            pass
        self.settings.setValue(key.replace(".", "/"), str(value or ""))
        self.settings.sync()

    def reset_review_group_exclusions(self) -> bool:
        try:
            if hasattr(self.bridge, "reset_review_group_exclusions") and self.bridge.reset_review_group_exclusions():
                return True
        except Exception:
            pass
        try:
            from app.mediamanager.db.media_repo import clear_review_pair_exclusions

            clear_review_pair_exclusions(self.bridge.conn)
            return True
        except Exception:
            return False
