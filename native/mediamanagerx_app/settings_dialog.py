from __future__ import annotations

import ctypes
import json
import sys

from PySide6.QtCore import QPointF, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProxyStyle,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QStackedWidget,
    QTabBar,
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
    ("duplicate.rules.merge.all", "All (includes more than listed above)", False),
]
DUPLICATE_PRIORITY_ORDER_DEFAULT = [
    "File Size",
    "Resolution",
    "File Format",
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
        self.setSpacing(4)
        self.model().rowsMoved.connect(lambda *_args: self.orderChanged.emit())

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()


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
        self.use_recycle_bin_toggle = QCheckBox("Use Recycle Bin for deletes (Shift+Del for permanent)")
        startup_layout.addWidget(self.randomize_toggle)
        startup_layout.addWidget(self.restore_last_toggle)
        startup_layout.addWidget(self.show_hidden_toggle)
        startup_layout.addWidget(self.use_recycle_bin_toggle)

        startup_layout.addWidget(QLabel("Starting folder"))
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        self.start_folder_edit = QLineEdit()
        self.start_folder_browse_btn = QPushButton("Browse...")
        folder_row.addWidget(self.start_folder_edit, 1)
        folder_row.addWidget(self.start_folder_browse_btn)
        startup_layout.addLayout(folder_row)

        load_row = QHBoxLayout()
        load_row.setContentsMargins(0, 0, 0, 0)
        load_row.addStretch(1)
        self.load_now_btn = QPushButton("Load Now")
        load_row.addWidget(self.load_now_btn)
        startup_layout.addLayout(load_row)
        layout.addWidget(startup_group)

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
        self.use_recycle_bin_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("gallery.use_recycle_bin", checked))
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

    def _on_randomize_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.randomize", checked)
        self.main_window._refresh_current_folder()

    def _on_restore_last_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.restore_last", checked)
        self._sync_start_folder_enabled()

    def _on_show_hidden_changed(self, checked: bool) -> None:
        self.dialog.set_setting_bool("gallery.show_hidden", checked)
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
        with QSignalBlocker(self.use_recycle_bin_toggle):
            self.use_recycle_bin_toggle.setChecked(bool(self.settings.value("gallery/use_recycle_bin", True, type=bool)))
        with QSignalBlocker(self.auto_update_toggle):
            self.auto_update_toggle.setChecked(bool(state.get("updates.check_on_launch", True)))
        with QSignalBlocker(self.start_folder_edit):
            self.start_folder_edit.setText(str(state.get("gallery.start_folder", "") or ""))
        self._sync_start_folder_enabled()
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
    TAB_KEYS = [("rules", "Rules"), ("priorities", "Priorities")]

    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Similar File Rules"))
        layout.addWidget(_description("Configure duplicate scoring, preferred formats, and metadata merge behavior."))

        self.tabs = QTabBar()
        for _key, title in self.TAB_KEYS:
            self.tabs.addTab(title)
        layout.addWidget(self.tabs)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.rules_page = QWidget()
        rules_layout = QVBoxLayout(self.rules_page)
        rules_layout.setContentsMargins(0, 0, 0, 0)
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

        format_group = QGroupBox("Preferred File Format Order")
        format_layout = QVBoxLayout(format_group)
        self.format_list = ReorderListWidget()
        self.format_list.orderChanged.connect(self._save_format_order)
        format_layout.addWidget(self.format_list)
        rules_layout.addWidget(format_group, 1)

        merge_group = QGroupBox("Metadata Merge")
        merge_layout = QVBoxLayout(merge_group)
        self.merge_before_delete_toggle = QCheckBox("Merge metadata before deleting duplicates")
        merge_layout.addWidget(self.merge_before_delete_toggle)
        merge_grid = QGridLayout()
        self.merge_toggles: dict[str, QCheckBox] = {}
        for index, (key, label_text, _default) in enumerate(DUPLICATE_MERGE_FIELDS):
            checkbox = QCheckBox(label_text)
            checkbox.toggled.connect(lambda checked, setting_key=key: self.dialog.set_setting_bool(setting_key, checked))
            merge_grid.addWidget(checkbox, index // 2, index % 2)
            self.merge_toggles[key] = checkbox
        merge_layout.addLayout(merge_grid)
        rules_layout.addWidget(merge_group)

        self.priorities_page = QWidget()
        priorities_layout = QVBoxLayout(self.priorities_page)
        priorities_layout.setContentsMargins(0, 0, 0, 0)
        priorities_layout.setSpacing(12)
        priorities_layout.addWidget(_description("Drag to set the order of importance for duplicate scoring."))
        self.priority_list = ReorderListWidget()
        self.priority_list.orderChanged.connect(self._save_priority_order)
        priorities_layout.addWidget(self.priority_list, 1)

        self.stack.addWidget(self.rules_page)
        self.stack.addWidget(self.priorities_page)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.merge_before_delete_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("duplicate.rules.merge_before_delete", checked))

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self.TAB_KEYS):
            self.stack.setCurrentIndex(index)
            self.dialog.set_setting_str("duplicate.settings.active_tab", self.TAB_KEYS[index][0])

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

    def refresh(self) -> None:
        self._loading = True
        try:
            tab_keys = [key for key, _title in self.TAB_KEYS]
            active_tab = str(self.settings.value("duplicate/settings/active_tab", "rules", type=str) or "rules")
            if active_tab not in tab_keys:
                active_tab = "rules"
            with QSignalBlocker(self.tabs):
                self.tabs.setCurrentIndex(tab_keys.index(active_tab))
            self.stack.setCurrentIndex(tab_keys.index(active_tab))
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
            with QSignalBlocker(self.merge_before_delete_toggle):
                self.merge_before_delete_toggle.setChecked(bool(self.settings.value("duplicate/rules/merge_before_delete", False, type=bool)))
            for key, _label, default_value in DUPLICATE_MERGE_FIELDS:
                with QSignalBlocker(self.merge_toggles[key]):
                    self.merge_toggles[key].setChecked(bool(self.settings.value(key.replace(".", "/"), default_value, type=bool)))
        finally:
            self._loading = False


class AISettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("AI"))
        layout.addWidget(_description("AI-specific controls are not native yet. This page is ready for future expansion."))
        placeholder = QLabel("AI-powered settings are coming soon.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(placeholder, 1)


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
            ("Metadata", MetadataSettingsPage(self)),
            ("Similar File Rules", DuplicateSettingsPage(self)),
            ("AI", AISettingsPage(self)),
        ]
        for title, page in self._page_defs:
            self.category_list.addItem(title)
            self.pages.addWidget(page)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Close")
        buttons.rejected.connect(self.close)
        buttons.accepted.connect(self.close)
        root.addWidget(buttons)
        self._button_box = buttons

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
        self.refresh_from_settings()
        if self.isVisible():
            self.raise_()
            self.activateWindow()
            return
        self.open()
        self.raise_()
        self.activateWindow()
        self._apply_native_title_bar_theme()

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
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
            }}
            QLabel#settingsSectionTitle {{
                font-size: 16px;
                font-weight: 700;
                color: {text};
            }}
            QLabel#settingsDescription {{
                color: {muted};
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
            QListWidget#settingsReorderList {{
                background-color: {control_bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
            }}
            QListWidget#settingsReorderList::item {{
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 8px 10px;
                margin: 1px 0;
                color: {text};
            }}
            QListWidget#settingsReorderList::item:hover {{
                background: {category_hover};
            }}
            QListWidget#settingsReorderList::item:selected {{
                background: {accent_soft};
                border: 1px solid {accent_str};
                color: {text};
            }}
            QGroupBox {{
                margin-top: 10px;
                padding-top: 8px;
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: {muted};
            }}
            QLineEdit, QComboBox, QSpinBox, QListWidget#qt_spinbox_lineedit {{
                background-color: {control_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 5px 8px;
                selection-background-color: {accent_str};
                selection-color: {selection_text};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
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
        self._apply_native_title_bar_theme()

    def set_setting_bool(self, key: str, value: bool) -> None:
        if not self.bridge.set_setting_bool(key, bool(value)):
            self.settings.setValue(key.replace(".", "/"), bool(value))
            self.settings.sync()

    def set_setting_str(self, key: str, value: str) -> None:
        if not self.bridge.set_setting_str(key, str(value or "")):
            self.settings.setValue(key.replace(".", "/"), str(value or ""))
            self.settings.sync()
