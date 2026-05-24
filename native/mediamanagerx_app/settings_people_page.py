from __future__ import annotations

from native.mediamanagerx_app.settings_common import *


class PeopleSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("People"))
        layout.addWidget(_description("Configure local People detection and identity review behavior. Face embeddings point to existing files and do not create duplicate person folders."))

        engine_box = QGroupBox("Recognition Engine")
        engine_layout = QVBoxLayout(engine_box)
        self.engine_label = QLabel("Engine: InsightFace")
        self.engine_label.setObjectName("settingsFieldTitle")
        engine_layout.addWidget(self.engine_label)
        self.runtime_status = QLabel("Runtime status: not installed")
        self.runtime_status.setObjectName("settingsDescription")
        self.runtime_status.setWordWrap(True)
        engine_layout.addWidget(self.runtime_status)
        layout.addWidget(engine_box)

        workflow_box = QGroupBox("Workflow")
        workflow_layout = QVBoxLayout(workflow_box)
        self.bootstrap_tags = QCheckBox("Use matching tags as person name suggestions")
        self.bootstrap_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.bootstrap_tags)
        self.auto_apply_tags = QCheckBox("Add confirmed people as regular tags")
        self.auto_apply_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.auto_apply_tags)
        layout.addWidget(workflow_box)

        threshold_box = QGroupBox("Matching")
        threshold_layout = QVBoxLayout(threshold_box)
        self.threshold_combo = QComboBox()
        self.threshold_combo.addItem("Conservative", "conservative")
        self.threshold_combo.addItem("Balanced", "balanced")
        self.threshold_combo.addItem("Loose", "loose")
        threshold_layout.addWidget(QLabel("Automatic match threshold"))
        threshold_layout.addWidget(self.threshold_combo)
        layout.addWidget(threshold_box)
        layout.addStretch(1)

        self.bootstrap_tags.toggled.connect(lambda value: self.dialog.set_setting_bool("people.bootstrap_tags", bool(value)))
        self.auto_apply_tags.toggled.connect(lambda value: self.dialog.set_setting_bool("people.sync_confirmed_to_tags", bool(value)))
        self.threshold_combo.currentIndexChanged.connect(self._save_threshold)

    def refresh(self) -> None:
        self.bootstrap_tags.blockSignals(True)
        self.auto_apply_tags.blockSignals(True)
        self.threshold_combo.blockSignals(True)
        try:
            self.bootstrap_tags.setChecked(bool(self.settings.value("people/bootstrap_tags", True, type=bool)))
            self.auto_apply_tags.setChecked(bool(self.settings.value("people/sync_confirmed_to_tags", False, type=bool)))
            value = str(self.settings.value("people/match_threshold", "balanced", type=str) or "balanced")
            index = self.threshold_combo.findData(value)
            self.threshold_combo.setCurrentIndex(index if index >= 0 else 1)
        finally:
            self.bootstrap_tags.blockSignals(False)
            self.auto_apply_tags.blockSignals(False)
            self.threshold_combo.blockSignals(False)

    def _save_threshold(self) -> None:
        value = str(self.threshold_combo.currentData() or "balanced")
        self.dialog.set_setting_str("people.match_threshold", value)
