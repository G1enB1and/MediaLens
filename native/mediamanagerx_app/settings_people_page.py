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
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("None", "none")
        self.engine_combo.addItem("InsightFace (Experimental)", "insightface")
        engine_layout.addWidget(QLabel("Face recognition engine"))
        engine_layout.addWidget(self.engine_combo)
        self.license_note = QLabel("InsightFace is optional for development and testing. Its pretrained Buffalo_L model may require separate licensing for commercial use.")
        self.license_note.setObjectName("settingsDescription")
        self.license_note.setWordWrap(True)
        engine_layout.addWidget(self.license_note)
        self.runtime_status = QLabel("Runtime status: not installed")
        self.runtime_status.setObjectName("settingsDescription")
        self.runtime_status.setWordWrap(True)
        engine_layout.addWidget(self.runtime_status)
        self.open_models_btn = QPushButton("Open AI Models Status")
        self.open_models_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_models_btn.clicked.connect(lambda: self.main_window.open_local_ai_setup("faces", show_advanced=True))
        engine_layout.addWidget(self.open_models_btn)
        layout.addWidget(engine_box)

        workflow_box = QGroupBox("Workflow")
        workflow_layout = QVBoxLayout(workflow_box)
        self.bootstrap_tags = QCheckBox("Use matching tags as person name suggestions")
        self.bootstrap_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.bootstrap_tags)
        self.auto_apply_tags = QCheckBox("Add confirmed people as regular tags")
        self.auto_apply_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.auto_apply_tags)
        self.skip_existing_scans = QCheckBox("Rescans skip prescanned files")
        self.skip_existing_scans.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.skip_existing_scans)
        self.show_face_boxes = QCheckBox("Show face boxes in People review")
        self.show_face_boxes.setCursor(Qt.CursorShape.PointingHandCursor)
        workflow_layout.addWidget(self.show_face_boxes)
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
        self.skip_existing_scans.toggled.connect(lambda value: self.dialog.set_setting_bool("people.skip_existing_scans", bool(value)))
        self.show_face_boxes.toggled.connect(lambda value: self.dialog.set_setting_bool("people.show_face_boxes", bool(value)))
        self.engine_combo.currentIndexChanged.connect(self._save_engine)
        self.threshold_combo.currentIndexChanged.connect(self._save_threshold)

    def refresh(self) -> None:
        self.bootstrap_tags.blockSignals(True)
        self.auto_apply_tags.blockSignals(True)
        self.skip_existing_scans.blockSignals(True)
        self.show_face_boxes.blockSignals(True)
        self.engine_combo.blockSignals(True)
        self.threshold_combo.blockSignals(True)
        try:
            self.bootstrap_tags.setChecked(bool(self.settings.value("people/bootstrap_tags", True, type=bool)))
            self.auto_apply_tags.setChecked(bool(self.settings.value("people/sync_confirmed_to_tags", False, type=bool)))
            self.skip_existing_scans.setChecked(bool(self.settings.value("people/skip_existing_scans", True, type=bool)))
            self.show_face_boxes.setChecked(bool(self.settings.value("people/show_face_boxes", True, type=bool)))
            engine = str(self.settings.value("people/recognition_engine", "none", type=str) or "none")
            engine_index = self.engine_combo.findData(engine)
            self.engine_combo.setCurrentIndex(engine_index if engine_index >= 0 else 0)
            self._refresh_runtime_status()
            value = str(self.settings.value("people/match_threshold", "balanced", type=str) or "balanced")
            index = self.threshold_combo.findData(value)
            self.threshold_combo.setCurrentIndex(index if index >= 0 else 1)
        finally:
            self.bootstrap_tags.blockSignals(False)
            self.auto_apply_tags.blockSignals(False)
            self.skip_existing_scans.blockSignals(False)
            self.show_face_boxes.blockSignals(False)
            self.engine_combo.blockSignals(False)
            self.threshold_combo.blockSignals(False)

    def _save_engine(self) -> None:
        value = str(self.engine_combo.currentData() or "none")
        self.dialog.set_setting_str("people.recognition_engine", value)
        self._refresh_runtime_status()

    def _refresh_runtime_status(self) -> None:
        engine = str(self.engine_combo.currentData() or "none")
        if engine != "insightface":
            self.runtime_status.setText("Runtime status: disabled")
            return
        try:
            from app.mediamanager.ai_captioning.model_registry import INSIGHTFACE_MODEL_ID

            status = dict(self.bridge.get_local_ai_model_status(INSIGHTFACE_MODEL_ID, "faces") or {})
            state = str(status.get("state") or "").replace("_", " ").strip() or "unknown"
            message = str(status.get("message") or "").strip()
            self.runtime_status.setText(f"Runtime status: {state}{f' - {message}' if message else ''}")
        except Exception as exc:
            self.runtime_status.setText(f"Runtime status: unavailable - {exc}")

    def _save_threshold(self) -> None:
        value = str(self.threshold_combo.currentData() or "balanced")
        self.dialog.set_setting_str("people.match_threshold", value)
