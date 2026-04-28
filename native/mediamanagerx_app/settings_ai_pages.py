from __future__ import annotations

from native.mediamanagerx_app.settings_common import *
from native.mediamanagerx_app.settings_general_pages import *
from native.mediamanagerx_app.settings_scanner_metadata_pages import *
from native.mediamanagerx_app.settings_duplicate_pages import *

class AISettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        from app.mediamanager.ai_captioning.local_captioning import (
            CAPTION_MODEL_ID,
            DEFAULT_BAD_WORDS,
            DEFAULT_CAPTION_PROMPT,
            DEFAULT_CAPTION_START,
            DEFAULT_OCR_PROMPT,
            TAG_MODEL_ID,
        )
        from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID, MODEL_SPECS
        models_dir_default = self.bridge._local_ai_models_dir_default() if hasattr(self.bridge, "_local_ai_models_dir_default") else ""

        self.defaults = {
            "models_dir": models_dir_default,
            "tag_model_id": TAG_MODEL_ID,
            "caption_model_id": CAPTION_MODEL_ID,
            "ocr_model_id": GEMMA4_MODEL_ID,
            "tag_prompt": "",
            "caption_prompt": DEFAULT_CAPTION_PROMPT,
            "ocr_prompt": DEFAULT_OCR_PROMPT,
            "caption_start": DEFAULT_CAPTION_START,
            "bad_words": DEFAULT_BAD_WORDS,
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("AI"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        self.ai_section_tabs = QTabBar()
        self.ai_section_tabs.setExpanding(False)
        self.ai_section_tabs.addTab("Tags")
        self.ai_section_tabs.addTab("Descriptions")
        self.ai_section_tabs.addTab("Text and OCR")
        self.ai_section_tabs.addTab("Local Models")
        content_layout.addWidget(self.ai_section_tabs)

        self.ai_section_stack = QStackedWidget()
        content_layout.addWidget(self.ai_section_stack)

        tags_page = QWidget()
        tags_page_layout = QVBoxLayout(tags_page)
        tags_page_layout.setContentsMargins(0, 0, 0, 0)
        tags_page_layout.setSpacing(12)
        self.ai_section_stack.addWidget(tags_page)

        descriptions_page = QWidget()
        descriptions_page_layout = QVBoxLayout(descriptions_page)
        descriptions_page_layout.setContentsMargins(0, 0, 0, 0)
        descriptions_page_layout.setSpacing(12)
        self.ai_section_stack.addWidget(descriptions_page)

        ocr_page = QWidget()
        ocr_page_layout = QVBoxLayout(ocr_page)
        ocr_page_layout.setContentsMargins(0, 0, 0, 0)
        ocr_page_layout.setSpacing(12)
        self.ai_section_stack.addWidget(ocr_page)

        local_models_page = QWidget()
        local_models_page_layout = QVBoxLayout(local_models_page)
        local_models_page_layout.setContentsMargins(0, 0, 0, 0)
        local_models_page_layout.setSpacing(12)
        self.ai_section_stack.addWidget(local_models_page)
        self.ai_section_tabs.currentChanged.connect(self.ai_section_stack.setCurrentIndex)

        tags_group = QGroupBox("Tags")
        tags_form = QFormLayout(tags_group)
        tags_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        tags_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tags_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        tags_form.setVerticalSpacing(5)
        tags_form.setHorizontalSpacing(12)
        tags_page_layout.addWidget(tags_group)

        self.tag_model_combo = QComboBox()
        for spec in MODEL_SPECS:
            if spec.kind == "tagger":
                self.tag_model_combo.addItem(spec.label, spec.id)
        tags_form.addRow("Tag Model", self.tag_model_combo)

        self.tag_model_description_label = QLabel("")
        self.tag_model_description_label.setWordWrap(True)
        self.tag_model_description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.tag_model_description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.tag_model_description_label.setMinimumHeight(22)
        self.tag_model_description_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tag_model_status_label = QLabel("")
        self.tag_model_status_label.setObjectName("aiSettingsModelStatus")
        self.tag_model_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.tag_model_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.tag_model_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.tag_model_submodel_combo = QComboBox()
        self.tag_model_submodel_combo.setVisible(False)
        self.tag_model_submodel_combo.currentIndexChanged.connect(lambda _index: self._on_gemma_submodel_changed("tagger"))
        self.tag_model_advanced_btn = QPushButton("Advanced")
        self.tag_model_advanced_btn.setFlat(True)
        self.tag_model_advanced_btn.clicked.connect(lambda: self.dialog.main_window.open_local_ai_setup("tagger", show_advanced=True))
        self.tag_model_install_btn = QPushButton("Install Model")
        self.tag_model_install_btn.clicked.connect(lambda: self._install_selected_ai_model("tagger"))
        tag_model_status_row = QWidget()
        tag_model_status_layout = QHBoxLayout(tag_model_status_row)
        tag_model_status_layout.setContentsMargins(0, 0, 0, 0)
        tag_model_status_layout.setSpacing(8)
        tag_model_status_panel = QWidget()
        tag_model_status_panel_layout = QVBoxLayout(tag_model_status_panel)
        tag_model_status_panel_layout.setContentsMargins(0, 0, 0, 0)
        tag_model_status_panel_layout.setSpacing(4)
        tag_model_status_panel_layout.addWidget(self.tag_model_status_label)
        tag_model_status_panel_layout.addWidget(self.tag_model_submodel_combo)
        tag_model_status_panel_layout.addWidget(self.tag_model_advanced_btn, 0, Qt.AlignmentFlag.AlignLeft)
        tag_model_status_layout.addWidget(tag_model_status_panel, 1)
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
        self.tag_prompt_edit.setFixedHeight(80)
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
        descriptions_page_layout.addWidget(descriptions_group)

        self.caption_model_combo = QComboBox()
        for spec in MODEL_SPECS:
            if spec.kind == "captioner":
                self.caption_model_combo.addItem(spec.label, spec.id)
        descriptions_form.addRow("Description Model", self.caption_model_combo)

        self.caption_model_description_label = QLabel("")
        self.caption_model_description_label.setWordWrap(True)
        self.caption_model_description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.caption_model_description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.caption_model_description_label.setMinimumHeight(22)
        self.caption_model_description_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.caption_model_status_label = QLabel("")
        self.caption_model_status_label.setObjectName("aiSettingsModelStatus")
        self.caption_model_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.caption_model_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.caption_model_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.caption_model_submodel_combo = QComboBox()
        self.caption_model_submodel_combo.setVisible(False)
        self.caption_model_submodel_combo.currentIndexChanged.connect(lambda _index: self._on_gemma_submodel_changed("captioner"))
        self.caption_model_advanced_btn = QPushButton("Advanced")
        self.caption_model_advanced_btn.setFlat(True)
        self.caption_model_advanced_btn.clicked.connect(lambda: self.dialog.main_window.open_local_ai_setup("captioner", show_advanced=True))
        self.caption_model_install_btn = QPushButton("Install Model")
        self.caption_model_install_btn.clicked.connect(lambda: self._install_selected_ai_model("captioner"))
        caption_model_status_row = QWidget()
        caption_model_status_layout = QHBoxLayout(caption_model_status_row)
        caption_model_status_layout.setContentsMargins(0, 0, 0, 0)
        caption_model_status_layout.setSpacing(8)
        caption_model_status_panel = QWidget()
        caption_model_status_panel_layout = QVBoxLayout(caption_model_status_panel)
        caption_model_status_panel_layout.setContentsMargins(0, 0, 0, 0)
        caption_model_status_panel_layout.setSpacing(4)
        caption_model_status_panel_layout.addWidget(self.caption_model_status_label)
        caption_model_status_panel_layout.addWidget(self.caption_model_submodel_combo)
        caption_model_status_panel_layout.addWidget(self.caption_model_advanced_btn, 0, Qt.AlignmentFlag.AlignLeft)
        caption_model_status_layout.addWidget(caption_model_status_panel, 1)
        caption_model_status_layout.addWidget(self.caption_model_install_btn)
        descriptions_form.addRow("Description", self.caption_model_description_label)
        descriptions_form.addRow("Status", caption_model_status_row)

        self.description_write_mode_combo = QComboBox()
        self.description_write_mode_combo.addItem("Overwrite Description", "overwrite")
        self.description_write_mode_combo.addItem("Append Description", "append")
        self.description_write_mode_combo.addItem("Only If Empty", "skip_existing")
        descriptions_form.addRow("Description Rule", self.description_write_mode_combo)

        self.caption_prompt_edit = QTextEdit()
        self.caption_prompt_edit.setFixedHeight(80)
        self.caption_prompt_edit.setPlaceholderText("Prompt. Use {tags} to insert tags and {starter} to place the starter.")
        descriptions_form.addRow("Description Prompt", self.caption_prompt_edit)

        self.caption_start_edit = QLineEdit()
        descriptions_form.addRow("Start Description With", self.caption_start_edit)

        self.bad_words_edit = QLineEdit()
        descriptions_form.addRow("Discourage", self.bad_words_edit)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 2048)
        descriptions_form.addRow("Maximum Tokens", self.max_tokens_spin)

        ocr_ai_group = QGroupBox("AI OCR")
        ocr_ai_form = QFormLayout(ocr_ai_group)
        ocr_ai_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        ocr_ai_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        ocr_ai_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        ocr_ai_form.setVerticalSpacing(5)
        ocr_ai_form.setHorizontalSpacing(12)
        ocr_page_layout.addWidget(ocr_ai_group)

        self.ocr_model_combo = QComboBox()
        self.ocr_model_combo.addItem("Gemma 4", self.defaults["ocr_model_id"])
        self.ocr_model_combo.setEnabled(False)
        ocr_ai_form.addRow("OCR Model", self.ocr_model_combo)

        self.ocr_model_description_label = QLabel("Gemma 4 image transcription.")
        self.ocr_model_description_label.setWordWrap(True)
        self.ocr_model_description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.ocr_model_description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ocr_model_status_label = QLabel("")
        self.ocr_model_status_label.setObjectName("aiSettingsModelStatus")
        self.ocr_model_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.ocr_model_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.ocr_model_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ocr_model_submodel_combo = QComboBox()
        self.ocr_model_submodel_combo.setVisible(False)
        self.ocr_model_submodel_combo.currentIndexChanged.connect(lambda _index: self._on_gemma_submodel_changed("ocr"))
        self.ocr_model_advanced_btn = QPushButton("Advanced")
        self.ocr_model_advanced_btn.setFlat(True)
        self.ocr_model_advanced_btn.clicked.connect(lambda: self.dialog.main_window.open_local_ai_setup("captioner", show_advanced=True))
        self.ocr_model_install_btn = QPushButton("Install Model")
        self.ocr_model_install_btn.clicked.connect(lambda: self._install_selected_ai_model("ocr"))
        ocr_model_status_row = QWidget()
        ocr_model_status_layout = QHBoxLayout(ocr_model_status_row)
        ocr_model_status_layout.setContentsMargins(0, 0, 0, 0)
        ocr_model_status_layout.setSpacing(8)
        ocr_model_status_panel = QWidget()
        ocr_model_status_panel_layout = QVBoxLayout(ocr_model_status_panel)
        ocr_model_status_panel_layout.setContentsMargins(0, 0, 0, 0)
        ocr_model_status_panel_layout.setSpacing(4)
        ocr_model_status_panel_layout.addWidget(self.ocr_model_status_label)
        ocr_model_status_panel_layout.addWidget(self.ocr_model_submodel_combo)
        ocr_model_status_panel_layout.addWidget(self.ocr_model_advanced_btn, 0, Qt.AlignmentFlag.AlignLeft)
        ocr_model_status_layout.addWidget(ocr_model_status_panel, 1)
        ocr_model_status_layout.addWidget(self.ocr_model_install_btn)
        ocr_ai_form.addRow("Description", self.ocr_model_description_label)
        ocr_ai_form.addRow("Status", ocr_model_status_row)

        self.ocr_prompt_edit = QTextEdit()
        self.ocr_prompt_edit.setFixedHeight(80)
        self.ocr_prompt_edit.setPlaceholderText("OCR prompt and rules.")
        ocr_ai_form.addRow("OCR Prompt", self.ocr_prompt_edit)

        paddle_group = QGroupBox("Non-AI OCR")
        paddle_form = QFormLayout(paddle_group)
        paddle_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        paddle_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        paddle_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        paddle_form.setVerticalSpacing(5)
        paddle_form.setHorizontalSpacing(12)
        ocr_page_layout.addWidget(paddle_group)

        self.paddle_fast_status_label = QLabel("")
        self.paddle_fast_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.paddle_fast_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        paddle_form.addRow("Paddle Fast", self.paddle_fast_status_label)
        ocr_page_layout.addStretch(1)

        models_group = QGroupBox("Models")
        models_form = QFormLayout(models_group)
        models_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        models_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        local_models_page_layout.addWidget(models_group)

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

        models_status_btn = QPushButton("AI Models Status")
        models_status_btn.clicked.connect(lambda: self.dialog.main_window.open_local_ai_setup("captioner", show_advanced=True))
        models_form.addRow("Status Page", models_status_btn)
        local_models_page_layout.addStretch(1)

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
        ):
            combo.currentIndexChanged.connect(self._save)
        self.tag_model_combo.currentIndexChanged.connect(lambda _index: self._refresh_ai_model_statuses())
        self.caption_model_combo.currentIndexChanged.connect(lambda _index: self._refresh_ai_model_statuses())
        if hasattr(self.bridge, "localAiModelInstallStatus"):
            self.bridge.localAiModelInstallStatus.connect(self._on_local_ai_model_install_status)
        if hasattr(self.bridge, "paddleOcrRuntimeInstallStatus"):
            self.bridge.paddleOcrRuntimeInstallStatus.connect(self._on_paddle_ocr_runtime_install_status)
        self.tag_prompt_edit.textChanged.connect(self._save)
        self.caption_prompt_edit.textChanged.connect(self._save)
        self.ocr_prompt_edit.textChanged.connect(self._save)
        self.tag_max_tags_spin.valueChanged.connect(self._save)
        self.max_tokens_spin.valueChanged.connect(self._save)
        self._load_settings_values()

    def _setting(self, key: str, default, value_type=None):
        qkey = key.replace(".", "/")
        if value_type is None:
            return self.settings.value(qkey, default)
        return self.settings.value(qkey, default, type=value_type)

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _selected_ai_model_id(self, kind: str) -> str:
        if kind == "ocr":
            return str(self.ocr_model_combo.currentData() or self.defaults["ocr_model_id"])
        combo = self.tag_model_combo if kind == "tagger" else self.caption_model_combo
        return str(combo.currentData() or "")

    @staticmethod
    def _model_status_kind(kind: str) -> str:
        return "captioner" if kind == "ocr" else kind

    def _status_widgets(self, kind: str):
        if kind == "tagger":
            return self.tag_model_description_label, self.tag_model_status_label, self.tag_model_install_btn, self.tag_model_submodel_combo, self.tag_model_advanced_btn
        if kind == "ocr":
            return self.ocr_model_description_label, self.ocr_model_status_label, self.ocr_model_install_btn, self.ocr_model_submodel_combo, self.ocr_model_advanced_btn
        return self.caption_model_description_label, self.caption_model_status_label, self.caption_model_install_btn, self.caption_model_submodel_combo, self.caption_model_advanced_btn

    def _populate_gemma_submodels(self, combo: QComboBox, status: dict) -> None:
        from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id

        downloaded = list(status.get("gemma_downloaded_profiles") or [])
        selected_id = str(status.get("gemma_selected_profile_id") or "").strip()
        with QSignalBlocker(combo):
            combo.clear()
            for profile_id in downloaded:
                profile = gemma_profile_by_id(str(profile_id))
                if profile is None:
                    continue
                combo.addItem(profile.label, profile.id)
            combo.setVisible(combo.count() > 0)
            if combo.count() > 0:
                idx = combo.findData(selected_id)
                combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _on_gemma_submodel_changed(self, kind: str) -> None:
        if kind == "tagger":
            combo = self.tag_model_submodel_combo
        elif kind == "ocr":
            combo = self.ocr_model_submodel_combo
        else:
            combo = self.caption_model_submodel_combo
        profile_id = str(combo.currentData() or "").strip()
        if not profile_id:
            return
        self.settings.setValue("ai_caption/gemma_selected_profile_id", profile_id)
        if hasattr(self.bridge, "_sync_selected_gemma_profile_settings"):
            self.bridge._sync_selected_gemma_profile_settings(sync_qsettings=False)
        self.settings.sync()
        self._refresh_ai_model_statuses()

    def _apply_ai_model_status(self, kind: str, status: dict) -> None:
        description_label, status_label, button, submodel_combo, advanced_btn = self._status_widgets(kind)
        state = str(status.get("state") or "").strip()
        description = str(status.get("description") or "").strip()
        message = str(status.get("message") or "").strip()
        runtime_probe = dict(status.get("runtime_probe") or {})
        Theme = _theme_api()
        is_light = Theme.get_is_light()
        ok_color = "#238636" if is_light else "#7ee787"
        bad_color = "#c62828" if is_light else "#ff7b72"
        if state == "installed":
            status_text = f'<span style="color:{ok_color};">✓</span> Installed'
            selected_device = str(runtime_probe.get("selected_device") or "").strip().lower()
            status_text += f'<br><span style="color:{ok_color};">✓</span> GPU' if (selected_device.startswith("cuda") or selected_device == "gpu") else "<br>CPU"
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
        if str(status.get("settings_key") or "") == "gemma4":
            self._populate_gemma_submodels(submodel_combo, status)
        else:
            submodel_combo.setVisible(False)
        advanced_btn.setVisible(True)
        button.setVisible(state in {"not_installed", "error", "installing"})
        button.setEnabled(state in {"not_installed", "error"})
        button.setText("Installing..." if state == "installing" else "Install Model")

    def _refresh_ai_model_statuses(self) -> None:
        if bool(getattr(self, "_loading", False)):
            return
        for kind in ("tagger", "captioner", "ocr"):
            model_id = self._selected_ai_model_id(kind)
            if not model_id:
                continue
            if hasattr(self.bridge, "get_local_ai_model_status"):
                try:
                    self._apply_ai_model_status(kind, dict(self.bridge.get_local_ai_model_status(model_id, self._model_status_kind(kind)) or {}))
                except Exception as exc:
                    self._apply_ai_model_status(kind, {"state": "error", "message": str(exc) or "Could not read model status."})
        self._refresh_paddle_ocr_status()

    def _refresh_paddle_ocr_status(self) -> None:
        Theme = _theme_api()
        is_light = Theme.get_is_light()
        ok_color = "#238636" if is_light else "#7ee787"
        bad_color = "#c62828" if is_light else "#ff7b72"
        try:
            status = dict(self.bridge.get_paddle_ocr_status() or {}) if hasattr(self.bridge, "get_paddle_ocr_status") else {}
        except Exception as exc:
            status = {"installed": False, "error": str(exc)}
        installed = bool(status.get("installed"))
        if installed:
            current_device = str(status.get("current_device") or "").strip()
            probe = dict(status.get("runtime_probe") or {})
            gpu_active = bool(status.get("gpu_active"))
            if gpu_active:
                gpu_line = f'<span style="color:{ok_color};">✓</span> GPU'
            else:
                reason = str(status.get("gpu_issue") or probe.get("gpu_error") or probe.get("error") or "").strip()
                gpu_line = "CPU fallback" if not bool(status.get("gpu_detected")) else "GPU inactive"
                if reason:
                    gpu_line = f"{gpu_line}<br>{html.escape(reason)}"
            self.paddle_fast_status_label.setText(f'<b><span style="color:{ok_color};">✓</span> Installed</b><br><b>{gpu_line}</b>')
        else:
            detail = html.escape(str(status.get("error") or status.get("message") or status.get("python_path") or "Runtime not installed."))
            self.paddle_fast_status_label.setText(f'<span style="color:{bad_color};">Not installed</span><br>{detail}')

    def _on_paddle_ocr_runtime_install_status(self, payload: dict) -> None:
        payload = dict(payload or {})
        state = str(payload.get("state") or "").strip()
        message = html.escape(str(payload.get("message") or "").strip() or "Installing Paddle OCR runtime...")
        if state == "installed":
            self._refresh_paddle_ocr_status()
            current = self.paddle_fast_status_label.text()
            self.paddle_fast_status_label.setText(f"{current}<br>{message}")
        elif state == "error":
            self.paddle_fast_status_label.setText(f'<span style="color:#c62828;">Install failed</span><br>{message}')
        else:
            self.paddle_fast_status_label.setText(message)

    def _install_selected_ai_model(self, kind: str) -> None:
        model_id = self._selected_ai_model_id(kind)
        if not model_id or not hasattr(self.bridge, "install_local_ai_model"):
            return
        status_kind = self._model_status_kind(kind)
        status = dict(self.bridge.get_local_ai_model_status(model_id, status_kind) or {}) if hasattr(self.bridge, "get_local_ai_model_status") else {}
        label = str(status.get("label") or "this model")
        size = str(status.get("estimated_size") or "").strip()
        message = f"Install {label} local AI support?"
        if size:
            message = f"{message}\n\nEstimated size: {size}"
        message = f"{message}\n\nThis downloads packages and model files from the internet as needed."
        reply = QMessageBox.question(self, "Install AI Model", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        started = bool(self.bridge.install_local_ai_model(model_id, status_kind))
        if not started:
            self._refresh_ai_model_statuses()

    def _on_local_ai_model_install_status(self, status_key: str, payload: dict) -> None:
        payload = dict(payload or {})
        for kind in ("tagger", "captioner", "ocr"):
            current = {}
            if hasattr(self.bridge, "get_local_ai_model_status"):
                try:
                    current = dict(self.bridge.get_local_ai_model_status(self._selected_ai_model_id(kind), self._model_status_kind(kind)) or {})
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
        s.setValue("ai_caption/ocr_prompt", self.ocr_prompt_edit.toPlainText().strip() or self.defaults["ocr_prompt"])
        s.setValue("ai_caption/caption_start", self.caption_start_edit.text())
        s.setValue("ai_caption/bad_words", self.bad_words_edit.text())
        s.setValue("ai_caption/tags_to_exclude", self.tags_to_exclude_edit.text())
        try:
            min_probability = float(self.tag_min_probability_edit.text().strip())
        except Exception:
            min_probability = 0.35
        s.setValue("ai_caption/tag_min_probability", max(0.0, min(1.0, min_probability)))
        s.setValue("ai_caption/tag_max_tags", self.tag_max_tags_spin.value())
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

    def _load_settings_values(self) -> None:
        self._loading = True
        try:
            self.models_dir_edit.setText(str(self._setting("ai_caption.models_dir", self.defaults["models_dir"], str) or self.defaults["models_dir"]))
            self._set_combo_data(self.tag_model_combo, str(self._setting("ai_caption.tag_model_id", self.defaults["tag_model_id"], str) or self.defaults["tag_model_id"]))
            self._set_combo_data(self.caption_model_combo, str(self._setting("ai_caption.caption_model_id", self.defaults["caption_model_id"], str) or self.defaults["caption_model_id"]))
            self._set_combo_data(self.tag_write_mode_combo, str(self._setting("ai_caption.tag_write_mode", "union", str) or "union"))
            self._set_combo_data(self.description_write_mode_combo, str(self._setting("ai_caption.description_write_mode", "overwrite", str) or "overwrite"))
            self.tag_prompt_edit.setPlainText(str(self._setting("ai_caption.tag_prompt", self.defaults["tag_prompt"], str) or self.defaults["tag_prompt"]))
            self.caption_prompt_edit.setPlainText(str(self._setting("ai_caption.caption_prompt", self.defaults["caption_prompt"], str) or self.defaults["caption_prompt"]))
            self.ocr_prompt_edit.setPlainText(str(self._setting("ai_caption.ocr_prompt", self.defaults["ocr_prompt"], str) or self.defaults["ocr_prompt"]))
            self.caption_start_edit.setText(str(self._setting("ai_caption.caption_start", self.defaults["caption_start"], str) or self.defaults["caption_start"]))
            self.bad_words_edit.setText(str(self._setting("ai_caption.bad_words", self.defaults["bad_words"], str) or self.defaults["bad_words"]))
            self.tags_to_exclude_edit.setText(str(self._setting("ai_caption.tags_to_exclude", "", str) or ""))
            self.tag_min_probability_edit.setText(str(self._setting("ai_caption.tag_min_probability", 0.35, float) or 0.35))
            self.tag_max_tags_spin.setValue(int(self._setting("ai_caption.tag_max_tags", 75, int) or 75))
            self.max_tokens_spin.setValue(int(self._setting("ai_caption.max_new_tokens", 200, int) or 200))
        finally:
            self._loading = False

    def refresh(self) -> None:
        self._load_settings_values()
        self._refresh_ai_model_statuses()


class LocalAiSetupDialog(QDialog):
    statusResolved = Signal(str, "QVariantMap", int)
    paddleStatusResolved = Signal("QVariantMap", int)

    def __init__(self, main_window: QWidget, focus_kind: str = "") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.bridge = main_window.bridge
        self.focus_kind = str(focus_kind or "").strip()
        self.setWindowTitle("Local AI Models")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(860, 620)
        self.setModal(False)
        self._rows: dict[str, dict[str, object]] = {}
        self._refresh_generation = 0
        self._advanced_visible = False
        self._simple_status_message = ""
        self._simple_status_seconds = 0
        self._simple_status_timer = QTimer(self)
        self._simple_status_timer.setInterval(5000)
        self._simple_status_timer.timeout.connect(self._tick_simple_status)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

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

        self.use_recommended_btn = QPushButton("Use Recommended Settings")
        self.use_recommended_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_recommended_btn.clicked.connect(self._use_recommended_models)
        root.addWidget(self.use_recommended_btn)

        self.advanced_toggle_btn = QPushButton("Show Advanced options")
        self.advanced_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.advanced_toggle_btn.clicked.connect(self._toggle_advanced_options)
        root.addWidget(self.advanced_toggle_btn)

        self.simple_status_label = QLabel("")
        self.simple_status_label.setWordWrap(True)
        self.simple_status_label.setVisible(False)
        root.addWidget(self.simple_status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.rows_layout = QVBoxLayout(content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
        scroll.setWidget(content)
        self.advanced_scroll = scroll
        root.addWidget(scroll)

        self.skip_startup_cb = QCheckBox("Don't show on startup (Can still open from View menu)")
        self.skip_startup_cb.setChecked(bool(self.bridge.settings.value("ai_caption/setup_dialog_skip_startup", False, type=bool)))
        self.skip_startup_cb.toggled.connect(lambda checked: self.bridge.settings.setValue("ai_caption/setup_dialog_skip_startup", checked))
        root.addWidget(self.skip_startup_cb)

        if hasattr(self.bridge, "localAiModelInstallStatus"):
            self.bridge.localAiModelInstallStatus.connect(self._on_install_status)
        if hasattr(self.bridge, "paddleOcrRuntimeInstallStatus"):
            self.bridge.paddleOcrRuntimeInstallStatus.connect(self._on_paddle_install_status)
        if hasattr(self.bridge, "accentColorChanged"):
            self.bridge.accentColorChanged.connect(lambda _value: self._apply_theme())
        self.statusResolved.connect(self._on_status_resolved)
        self.paddleStatusResolved.connect(self._on_paddle_status_resolved)

        self._build_rows()
        self._set_advanced_visible(False)
        self.refresh_statuses()
        self._apply_theme()

    def _unique_model_specs(self):
        from app.mediamanager.ai_captioning.model_registry import MODEL_SPECS
        from types import SimpleNamespace

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
        rows["paddle_ocr"] = {
            "spec": SimpleNamespace(
                id="paddle_ocr",
                kind="ocr",
                label="Paddle OCR",
                settings_key="paddle_ocr",
                install_label="Paddle OCR",
                description="Fast local OCR runtime for text recognition.",
                estimated_size="Approx. 0.5-2.2 GB depending on CPU/GPU runtime.",
            ),
            "kinds": {"ocr"},
        }
        order = {"gemma4": 0, "paddle_ocr": 1, "wd_swinv2": 2, "internlm_xcomposer2": 3}
        return dict(sorted(rows.items(), key=lambda item: (order.get(item[0], 99), str(item[0]))))

    @staticmethod
    def _capabilities_label(kinds: set[str]) -> str:
        labels = []
        if "tagger" in kinds:
            labels.append("tags")
        if "captioner" in kinds:
            labels.append("descriptions")
        if "ocr" in kinds:
            labels.append("OCR")
        return ", ".join(labels) if labels else "local AI"

    def _build_rows(self) -> None:
        for status_key, item in self._unique_model_specs().items():
            spec = item["spec"]
            kinds = item["kinds"]
            frame = QFrame()
            frame.setObjectName("localAiModelRow")
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(10)

            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(12)
            title_btn = QPushButton("")
            title_btn.setObjectName("localAiHeaderButton")
            title_btn.setCheckable(True)
            title_btn.setChecked(False)
            title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            title_btn.setFlat(True)
            title_btn.setIconSize(QSize(12, 12))
            title_btn.setToolTip("Expand model details")
            header_layout.addWidget(title_btn, 1)

            status_badge = QLabel("Checking")
            status_badge.setObjectName("localAiStatusBadge")
            status_badge.setTextFormat(Qt.TextFormat.RichText)
            badge_font = status_badge.font()
            badge_font.setBold(True)
            status_badge.setFont(badge_font)
            status_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_badge.setMinimumWidth(178)
            header_layout.addWidget(status_badge)
            layout.addWidget(header)

            content_panel = QWidget()
            content_layout = QGridLayout(content_panel)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setHorizontalSpacing(20)
            content_layout.setVerticalSpacing(0)
            content_panel.setVisible(False)

            details_panel = QWidget()
            details_layout = QVBoxLayout(details_panel)
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(6)

            summary_view = SelectableRichTextView()
            summary_view.setObjectName("localAiModelDetailsView")

            gemma_profile_row = QWidget()
            gemma_profile_layout = QGridLayout(gemma_profile_row)
            gemma_profile_layout.setContentsMargins(0, 0, 0, 0)
            gemma_profile_layout.setHorizontalSpacing(8)
            gemma_profile_layout.setVerticalSpacing(6)
            gemma_profile_label = QLabel("")
            gemma_profile_label.setObjectName("localAiModelMeta")
            gemma_profile_combo = QComboBox()
            gemma_profile_combo.setObjectName("localAiProfileCombo")
            gemma_profile_combo.setMinimumWidth(420)
            gemma_profile_size_lbl = QLabel("")
            gemma_profile_size_lbl.setObjectName("localAiModelMeta")
            gemma_profile_recommended_lbl = QLabel("")
            gemma_profile_recommended_lbl.setObjectName("localAiModelRecommended")
            gemma_profile_download_btn = QPushButton("Download Model")
            gemma_profile_download_btn.setObjectName("localAiProfileActionButton")
            gemma_profile_download_btn.setFixedHeight(28)
            gemma_profile_download_btn.setMinimumWidth(120)
            gemma_profile_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gemma_profile_delete_btn = QPushButton("Delete Model")
            gemma_profile_delete_btn.setObjectName("localAiProfileDeleteButton")
            gemma_profile_delete_btn.setFixedHeight(28)
            gemma_profile_delete_btn.setMinimumWidth(110)
            gemma_profile_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            gemma_profile_layout.addWidget(gemma_profile_label, 0, 0, 1, 4)
            gemma_profile_layout.addWidget(gemma_profile_combo, 1, 0, 1, 4)
            gemma_profile_layout.addWidget(gemma_profile_size_lbl, 2, 0)
            gemma_profile_layout.addWidget(gemma_profile_recommended_lbl, 2, 1)
            gemma_profile_layout.addWidget(gemma_profile_download_btn, 2, 2)
            gemma_profile_layout.addWidget(gemma_profile_delete_btn, 2, 3)
            gemma_profile_layout.setColumnStretch(0, 1)
            gemma_profile_row.setVisible(False)

            gemma_profile_download_status = SelectableRichTextView()
            gemma_profile_download_status.setObjectName("localAiModelDetailsView")
            gemma_profile_download_status.setVisible(False)

            details_toggle_btn = QToolButton()
            details_toggle_btn.setText("Show technical specs")
            details_toggle_btn.setCheckable(True)
            details_toggle_btn.setChecked(False)
            details_toggle_btn.setObjectName("localAiDetailsToggle")
            details_toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

            details_layout.addWidget(summary_view)
            details_layout.addWidget(gemma_profile_row)
            details_layout.addWidget(gemma_profile_download_status)
            details_layout.addWidget(details_toggle_btn)

            technical_view = SelectableRichTextView()
            technical_view.setObjectName("localAiTechnicalDetailsView")
            technical_view.setVisible(False)
            details_layout.addWidget(technical_view)
            details_toggle_btn.toggled.connect(
                lambda checked, view=technical_view, btn=details_toggle_btn: (
                    view.setVisible(bool(checked)),
                    btn.setText("Hide technical specs" if checked else "Show technical specs"),
                )
            )
            content_layout.addWidget(details_panel, 0, 0)

            actions_panel = QWidget()
            actions_layout = QVBoxLayout(actions_panel)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(8)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

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
            uninstall_btn.setMaximumWidth(100)
            uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            uninstall_btn.clicked.connect(lambda _checked=False, s=spec: self._uninstall_model(s))
            actions_layout.addWidget(uninstall_btn, 0, Qt.AlignmentFlag.AlignRight)

            delete_btn = QPushButton("Delete Model")
            delete_btn.setObjectName("localAiDeleteButton")
            delete_btn.setFixedHeight(28)
            delete_btn.setMaximumWidth(120)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda _checked=False, s=spec: self._delete_model_files(s))
            actions_layout.addWidget(delete_btn, 0, Qt.AlignmentFlag.AlignRight)
            actions_layout.addStretch(1)

            content_layout.addWidget(actions_panel, 0, 1)
            content_layout.setColumnStretch(0, 1)
            content_layout.setColumnMinimumWidth(1, 178)
            layout.addWidget(content_panel)

            self.rows_layout.addWidget(frame)
            self._rows[status_key] = {
                "spec": spec,
                "kinds": set(kinds),
                "title_button": title_btn,
                "badge": status_badge,
                "button": install_btn,
                "uninstall_button": uninstall_btn,
                "delete_button": delete_btn,
                "content_panel": content_panel,
                "summary_view": summary_view,
                "technical_view": technical_view,
                "details_toggle_button": details_toggle_btn,
                "gemma_profile_row": gemma_profile_row,
                "gemma_profile_combo": gemma_profile_combo,
                "gemma_profile_label": gemma_profile_label,
                "gemma_profile_size_lbl": gemma_profile_size_lbl,
                "gemma_profile_recommended_lbl": gemma_profile_recommended_lbl,
                "gemma_profile_download_btn": gemma_profile_download_btn,
                "gemma_profile_delete_btn": gemma_profile_delete_btn,
                "gemma_profile_download_status": gemma_profile_download_status,
                "frame": frame,
            }
            title_btn.toggled.connect(lambda checked, key=status_key: self._toggle_row_content(key, checked))
            if spec.settings_key == "gemma4":
                self._configure_gemma_profile_controls(row=self._rows[status_key])
        self.rows_layout.addStretch(1)

    def _toggle_row_content(self, status_key: str, checked: bool) -> None:
        row = self._rows.get(status_key)
        if not row:
            return
        panel = row.get("content_panel")
        title_btn = row.get("title_button")
        if panel is not None:
            panel.setVisible(bool(checked) and self._advanced_visible)
        if title_btn is not None:
            spec = row.get("spec")
            title_btn.setText(self._row_header_text(spec, bool(checked)))
            self._sync_row_header_icon(row, bool(checked))

    def _set_advanced_visible(self, visible: bool) -> None:
        self._advanced_visible = bool(visible)
        self.advanced_scroll.setVisible(self._advanced_visible)
        self.advanced_scroll.setMaximumHeight(16777215 if self._advanced_visible else 0)
        self.advanced_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding if self._advanced_visible else QSizePolicy.Policy.Fixed,
        )
        self.skip_startup_cb.setVisible(True)
        self.advanced_toggle_btn.setText("Hide Advanced Options" if self._advanced_visible else "Show Advanced options")
        if self._advanced_visible:
            self._simple_status_timer.stop()
            self.simple_status_label.setVisible(False)
        for row in self._rows.values():
            panel = row.get("content_panel")
            title_btn = row.get("title_button")
            if panel is not None and title_btn is not None:
                panel.setVisible(self._advanced_visible and bool(title_btn.isChecked()))
                spec = row.get("spec")
                title_btn.setText(self._row_header_text(spec, bool(title_btn.isChecked())))
                self._sync_row_header_icon(row, bool(title_btn.isChecked()))

    def _toggle_advanced_options(self) -> None:
        self._set_advanced_visible(not self._advanced_visible)

    def _recommended_gemma_profile(self):
        from app.mediamanager.ai_captioning.gemma_gguf import choose_best_gemma_profile

        vram = self.bridge._local_ai_detect_nvidia_vram() if hasattr(self.bridge, "_local_ai_detect_nvidia_vram") else {}
        return choose_best_gemma_profile(vram.get("total_vram_gb"), vram.get("free_vram_gb"))

    def _simple_recommended_message(self, payload: dict) -> str:
        download_messages = dict(payload.get("download_messages") or {})
        state = str(payload.get("state") or "").strip()
        message = str(payload.get("message") or "").strip()
        if state == "installed":
            return "Gemma 4 is setup. No further action needed.\nYou can start generating descriptions and tags using local private AI anytime now."
        if state == "error":
            return message or "Gemma 4 setup failed."
        if str(payload.get("download_message") or "").strip() or download_messages:
            percents: list[int] = []
            for text in download_messages.values():
                match = re.search(r"(\d{1,3})%", str(text or ""))
                if match:
                    try:
                        percents.append(max(0, min(100, int(match.group(1)))))
                    except Exception:
                        pass
            if percents:
                return f"Downloading Gemma 4... {max(percents)}%"
            return "Downloading Gemma 4..."
        lower = message.lower()
        if "validating" in lower or "finalizing" in lower:
            return "Finalizing Gemma 4..."
        if any(token in lower for token in ("creating", "installing", "runtime", "python", "package", "support")):
            return "Preparing Gemma 4..."
        return "Working on Gemma 4..."

    def _set_simple_status(self, message: str, *, active: bool) -> None:
        self._simple_status_message = str(message or "").strip()
        self._simple_status_seconds = 0
        self.simple_status_label.setText(self._simple_status_message)
        self.simple_status_label.setVisible(bool(self._simple_status_message))
        if active:
            self._simple_status_timer.start()
        else:
            self._simple_status_timer.stop()

    def _tick_simple_status(self) -> None:
        if not self._simple_status_message:
            self._simple_status_timer.stop()
            return
        self._simple_status_seconds += 5
        self.simple_status_label.setText(f"{self._simple_status_message} Still working...")

    @staticmethod
    def _row_header_text(spec, expanded: bool) -> str:
        title = "Gemma 4 (Recommended)" if getattr(spec, "settings_key", "") == "gemma4" else str(getattr(spec, "label", "") or "")
        return title

    def _row_header_icon(self, expanded: bool) -> QIcon:
        Theme = _theme_api()
        mode = "light" if Theme.get_is_light() else "dark"
        direction = "down" if expanded else "right"
        icon_path = Path(__file__).with_name("web") / "scrollbar_arrows" / f"{mode}_{direction}.svg"
        return QIcon(str(icon_path))

    def _sync_row_header_icon(self, row: dict, expanded: bool) -> None:
        button = row.get("title_button")
        if button is None:
            return
        button.setIcon(self._row_header_icon(expanded))
        button.setToolTip("Collapse model details" if expanded else "Expand model details")

    def _use_recommended_models(self) -> None:
        recommended = self._recommended_gemma_profile()
        self.bridge.settings.setValue("ai_caption/gemma_selected_profile_id", recommended.id)
        if hasattr(self.bridge, "_sync_selected_gemma_profile_settings"):
            self.bridge._sync_selected_gemma_profile_settings(sync_qsettings=False)
        self.bridge.settings.sync()
        self._set_simple_status(
            f"Selected {recommended.label}. Click Install or Download Model when you are ready to download files.",
            active=False,
        )
        for row in self._rows.values():
            spec = row.get("spec")
            if getattr(spec, "settings_key", "") == "gemma4":
                self._sync_gemma_profile_controls(row)
                break

    def _row_details_html(self, spec, kinds: set[str], status: dict) -> tuple[str, str, str]:
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            state = str(status.get("state") or "").strip()
            message = str(status.get("message") or "").strip()
            runtime_probe = dict(status.get("runtime_probe") or {})
            gpu_target = dict(status.get("gpu_target") or {})
            if state == "installing":
                gpu_summary = "Checking"
            elif bool(status.get("gpu_active")):
                gpu_summary = "✓ GPU"
            elif str(status.get("gpu_issue") or "").strip():
                gpu_summary = "GPU error"
            elif bool(status.get("gpu_available")):
                gpu_summary = "GPU inactive"
            elif bool(status.get("gpu_detected")):
                gpu_summary = "GPU inactive"
            elif status.get("installed"):
                gpu_summary = "CPU fallback"
            else:
                gpu_summary = "Not installed"
            current_device = str(status.get("current_device") or "").strip()
            summary_lines = [
                "<b>Use:</b> OCR",
                f"<b>Description:</b> {html.escape(str(spec.description or ''))}",
                f"<b>Size:</b> {html.escape(str(spec.estimated_size or ''))}",
                f"<b>Runtime:</b> {'Installed' if bool(status.get('installed')) else 'Not installed'}",
                f"<b>GPU:</b> {html.escape(gpu_summary)}",
            ]
            if message and state in {"installing", "error", "installed", "not_installed"}:
                summary_lines.append(html.escape(message))
            technical_lines = [
                f"<b>Python:</b> {html.escape(str(status.get('python_path') or ''))}",
                f"<b>Device:</b> {html.escape(current_device or 'cpu')}",
                f"<b>Compiled CUDA:</b> {html.escape(str(bool(runtime_probe.get('compiled_with_cuda'))))}",
            ]
            if runtime_probe.get("gpu_error"):
                technical_lines.append(f"<b>GPU error:</b> {html.escape(str(runtime_probe.get('gpu_error') or ''))}")
            if status.get("gpu_issue"):
                technical_lines.append(f"<b>GPU status:</b> {html.escape(str(status.get('gpu_issue') or ''))}")
            if runtime_probe.get("error"):
                technical_lines.append(f"<b>Probe error:</b> {html.escape(str(runtime_probe.get('error') or ''))}")
            if runtime_probe.get("traceback"):
                technical_lines.append(f"<b>Probe traceback:</b> {html.escape(str(runtime_probe.get('traceback') or ''))}")
            if gpu_target:
                technical_lines.append(f"<b>GPU target:</b> {html.escape(str(gpu_target.get('label') or gpu_target.get('reason') or ''))}")
            return "<br>".join(summary_lines), "", "<br>".join(technical_lines)
        state = str(status.get("state") or "").strip()
        message = str(status.get("message") or "").strip()
        download_message = str(status.get("download_message") or "").strip()
        download_messages = dict(status.get("download_messages") or {})
        runtime_summary = str(status.get("runtime_summary") or "").strip()
        runtime_details_html = str(status.get("runtime_details_html") or "").strip()
        gpu_summary = self._compact_gpu_summary(status)
        profile_downloading = bool(status.get("gemma_profile_downloading"))
        summary_lines = [
            f"<b>Use:</b> {html.escape(self._capabilities_label(kinds))}",
            f"<b>Description:</b> {html.escape(str(spec.description or ''))}",
            f"<b>Size:</b> {html.escape(str(spec.estimated_size or ''))}",
            f"<b>GPU:</b> {html.escape(gpu_summary)}" if gpu_summary else "",
        ]
        if bool(status.get("model_files_cached")) and state != "installed":
            summary_lines.append("<b>Model files:</b> Cached locally for faster reinstall")
        if runtime_summary and state != "installed":
            summary_lines.append(f"<b>Status:</b> {html.escape(runtime_summary)}")
        if message and (state in {'installing', 'error'} or profile_downloading or not runtime_summary and not runtime_details_html):
            summary_lines.append(html.escape(message))
        download_lines: list[str] = []
        if download_messages:
            labels = {"model": "Model", "mmproj": "Vision Projector"}
            for key in ("model", "mmproj"):
                value = str(download_messages.get(key) or "").strip()
                if value:
                    download_lines.append(f'<div><b>{html.escape(labels.get(key, key.title()))}:</b> {html.escape(value)}</div>')
        elif download_message:
            download_lines.append(f"<div>{html.escape(download_message)}</div>")
        technical_lines = []
        if runtime_summary:
            technical_lines.append(f"<b>Status:</b> {html.escape(runtime_summary)}")
        if runtime_details_html:
            technical_lines.append(runtime_details_html)
        return (
            "<br>".join(line for line in summary_lines if line),
            (
                '<div style="margin-top:0;"><b>Downloading...</b></div>'
                + "".join(download_lines)
            ) if download_lines else "",
            "<br>".join(line for line in technical_lines if line),
        )

    @staticmethod
    def _compact_gpu_summary(status: dict) -> str:
        probe = dict(status.get("runtime_probe") or {})
        backend = str(probe.get("backend") or "").strip().lower()
        if not probe:
            return ""
        selected_device = str(probe.get("selected_device") or "").strip().lower()
        if backend == "gguf":
            return "Enabled ✓" if selected_device == "gpu" else "Unavailable ✕"
        if backend == "onnx":
            active_provider = str(probe.get("active_provider") or "").strip().lower()
            providers = [str(name).strip().lower() for name in list(probe.get("available_providers") or []) if str(name).strip()]
            onnx_gpu_ready = (
                "cuda" in selected_device
                or selected_device == "gpu"
                or "cudaexecutionprovider" in active_provider
                or "tensorrtexecutionprovider" in active_provider
                or any(provider in {"cudaexecutionprovider", "tensorrtexecutionprovider"} for provider in providers)
            )
            return "Enabled ✓" if onnx_gpu_ready else "Unavailable ✕"
        return "Enabled ✓" if selected_device.startswith("cuda") or selected_device == "gpu" else "Unavailable ✕"

    def _gemma_profile_ui_data(self):
        from app.mediamanager.ai_captioning.gemma_gguf import choose_best_gemma_profile, gemma_profile_options

        vram = self.bridge._local_ai_detect_nvidia_vram() if hasattr(self.bridge, "_local_ai_detect_nvidia_vram") else {}
        recommended = choose_best_gemma_profile(vram.get("total_vram_gb"), vram.get("free_vram_gb"))
        profiles = tuple(sorted(gemma_profile_options(), key=lambda profile: (profile.approx_total_gb, profile.quality_rank)))
        return profiles, recommended

    def _configure_gemma_profile_controls(self, row: dict[str, object]) -> None:
        profiles, recommended = self._gemma_profile_ui_data()
        combo = row["gemma_profile_combo"]
        with QSignalBlocker(combo):
            combo.clear()
            for profile in profiles:
                label = f"{profile.label}  |  {profile.approx_total_gb:.1f} GB"
                if profile.id == recommended.id:
                    label += "  (Recommended)"
                combo.addItem(label, profile.id)
        combo.currentIndexChanged.connect(lambda _index, r=row: self._on_gemma_profile_changed(r))
        row["gemma_profile_download_btn"].clicked.connect(lambda _checked=False, r=row: self._download_selected_gemma_profile(r))
        row["gemma_profile_delete_btn"].clicked.connect(lambda _checked=False, r=row: self._delete_selected_gemma_profile(r))
        self._sync_gemma_profile_controls(row)

    def _sync_gemma_profile_controls(self, row: dict[str, object]) -> None:
        profiles, recommended = self._gemma_profile_ui_data()
        by_id = {profile.id: profile for profile in profiles}
        combo = row["gemma_profile_combo"]
        downloaded = set((row.get("latest_status") or {}).get("gemma_downloaded_profiles") or [])
        row["gemma_profile_label"].setText(f"Select Model. ({len(downloaded)} models downloaded)")
        active_download_id = str((row.get("latest_status") or {}).get("gemma_profile_downloading_id") or "").strip()
        is_profile_downloading = bool((row.get("latest_status") or {}).get("gemma_profile_downloading"))
        selected_id = str(self.bridge.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip() or recommended.id
        with QSignalBlocker(combo):
            current_id = str(combo.currentData() or "")
            index = combo.findData(selected_id)
            if index < 0 and current_id:
                index = combo.findData(current_id)
            index = max(0, index)
            combo.setCurrentIndex(index)
            for idx, profile in enumerate(profiles):
                label = f"{'✓ ' if profile.id in downloaded else ''}{profile.label}  |  {profile.approx_total_gb:.1f} GB"
                if profile.id == recommended.id:
                    label += "  (Recommended)"
                combo.setItemText(idx, label)
        profile = by_id.get(str(combo.currentData() or "")) or recommended
        row["gemma_profile_size_lbl"].setText(f"{profile.approx_total_gb:.1f} GB")
        row["gemma_profile_recommended_lbl"].setText("Recommended" if profile.id == recommended.id else "")
        is_downloaded = profile.id in downloaded
        download_btn = row["gemma_profile_download_btn"]
        delete_btn = row["gemma_profile_delete_btn"]
        downloading_selected = is_profile_downloading and profile.id == active_download_id
        download_btn.setText("Cancel Download" if downloading_selected else "Download Model")
        if downloading_selected:
            download_btn.setVisible(True)
            download_btn.setEnabled(True)
            delete_btn.setVisible(False)
            delete_btn.setEnabled(False)
        elif is_profile_downloading:
            download_btn.setVisible(False)
            download_btn.setEnabled(False)
            delete_btn.setVisible(False)
            delete_btn.setEnabled(False)
        else:
            download_btn.setVisible(not is_downloaded)
            download_btn.setEnabled(not is_downloaded)
            delete_btn.setVisible(is_downloaded)
            delete_btn.setEnabled(is_downloaded)

    def _on_gemma_profile_changed(self, row: dict[str, object]) -> None:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            gemma_profile_by_id,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        combo = row["gemma_profile_combo"]
        profile_id = str(combo.currentData() or "").strip()
        self.bridge.settings.setValue("ai_caption/gemma_selected_profile_id", profile_id)
        if hasattr(self.bridge, "_sync_selected_gemma_profile_settings"):
            self.bridge._sync_selected_gemma_profile_settings(sync_qsettings=False)
        profile = gemma_profile_by_id(profile_id)
        models_dir = Path(
            str(
                self.bridge.settings.value(
                    "ai_caption/models_dir",
                    getattr(self.bridge, "_local_ai_models_dir_default", lambda: "")(),
                    type=str,
                )
                or getattr(self.bridge, "_local_ai_models_dir_default", lambda: "")()
            )
        )
        if profile is not None and gemma_profile_is_installed(models_dir, profile):
            self.bridge.settings.setValue("ai_caption/gemma_profile_id", profile.id)
            self.bridge.settings.setValue("ai_caption/gemma_profile_label", profile.label)
            self.bridge.settings.setValue("ai_caption/gemma_model_path", str(gemma_profile_model_path(models_dir, profile)))
            self.bridge.settings.setValue("ai_caption/gemma_mmproj_path", str(gemma_profile_mmproj_path(models_dir, profile)))
        self._sync_gemma_profile_controls(row)
        self.refresh_statuses()

    def _download_selected_gemma_profile(self, row: dict[str, object]) -> None:
        status = dict(row.get("latest_status") or {})
        selected_id = str((row["gemma_profile_combo"]).currentData() or "").strip()
        if bool(status.get("gemma_profile_downloading")) and str(status.get("gemma_profile_downloading_id") or "").strip() == selected_id:
            if hasattr(self.bridge, "cancel_gemma_profile_download"):
                self.bridge.cancel_gemma_profile_download()
            return
        if not hasattr(self.bridge, "download_gemma_profile_files"):
            return
        combo = row["gemma_profile_combo"]
        profile_id = str(combo.currentData() or "").strip()
        if profile_id:
            self.bridge.download_gemma_profile_files(profile_id)

    def _delete_selected_gemma_profile(self, row: dict[str, object]) -> None:
        if not hasattr(self.bridge, "delete_gemma_profile_files"):
            return
        combo = row["gemma_profile_combo"]
        profile_id = str(combo.currentData() or "").strip()
        label = combo.currentText().replace("✓ ", "").split("  |  ", 1)[0]
        reply = QMessageBox.question(
            self,
            "Delete Gemma Model",
            f"Delete downloaded files for {label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.bridge.delete_gemma_profile_files(profile_id)

    def refresh_statuses(self) -> None:
        self._refresh_generation += 1
        generation = self._refresh_generation
        for status_key, row in self._rows.items():
            spec = row["spec"]
            self._apply_status(status_key, {"state": "checking", "message": "Checking runtime status..."})
            if status_key == "paddle_ocr":
                threading.Thread(
                    target=self._resolve_paddle_status_async,
                    args=(generation,),
                    daemon=True,
                    name="local-ai-status-paddle-ocr",
                ).start()
            else:
                threading.Thread(
                    target=self._resolve_status_async,
                    args=(status_key, spec, generation),
                    daemon=True,
                    name=f"local-ai-status-{status_key}",
                ).start()

    def _resolve_status_async(self, status_key: str, spec, generation: int) -> None:
        try:
            status = self._status_for_spec(spec)
            self.statusResolved.emit(str(status_key or ""), dict(status or {}), int(generation))
        except RuntimeError as exc:
            if "already deleted" not in str(exc):
                raise
        except Exception:
            pass

    def _resolve_paddle_status_async(self, generation: int) -> None:
        try:
            status = self._paddle_status_payload()
            self.paddleStatusResolved.emit(dict(status or {}), int(generation))
        except RuntimeError as exc:
            if "already deleted" not in str(exc):
                raise
        except Exception:
            pass

    def _paddle_status_payload(self, payload: dict | None = None) -> dict:
        status = dict(payload or {})
        if not status and hasattr(self.bridge, "get_paddle_ocr_status"):
            status = dict(self.bridge.get_paddle_ocr_status() or {})
        installed = bool(status.get("installed"))
        if not str(status.get("state") or "").strip():
            status["state"] = "installed" if installed else "not_installed"
        if installed and str(status.get("gpu_issue") or "").strip() and bool(status.get("prefer_gpu")):
            status["state"] = "error"
            status["message"] = str(status.get("gpu_issue") or "").strip()
        status.setdefault("id", "paddle_ocr")
        status.setdefault("label", "Paddle OCR")
        status.setdefault("settings_key", "paddle_ocr")
        status.setdefault("message", "Installed." if installed else "Not installed.")
        status["model_files_cached"] = self._paddle_cache_exists()
        return status

    def _paddle_cache_exists(self) -> bool:
        try:
            models_dir = Path(str(self.bridge.settings.value("ai_caption/models_dir", self.bridge._local_ai_models_dir_default(), type=str) or self.bridge._local_ai_models_dir_default()))
            return (models_dir / "paddleocr_cache").exists()
        except Exception:
            return False

    def _status_for_spec(self, spec) -> dict:
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            return self._paddle_status_payload()
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
        row["latest_status"] = dict(status or {})
        badge = row["badge"]
        title_button = row["title_button"]
        button = row["button"]
        uninstall_button = row["uninstall_button"]
        delete_button = row["delete_button"]
        summary_view = row["summary_view"]
        gemma_profile_download_status = row.get("gemma_profile_download_status")
        technical_view = row["technical_view"]
        details_toggle_button = row["details_toggle_button"]
        frame = row["frame"]
        spec = row["spec"]
        kinds = set(row.get("kinds") or set())
        state = str(status.get("state") or "").strip()
        Theme = _theme_api()
        is_light = Theme.get_is_light()
        ok_color = "#238636" if is_light else "#7ee787"
        bad_color = "#c62828" if is_light else "#ff7b72"
        if state == "installed":
            badge.setText(f'<span style="color:{ok_color};">✓</span> Installed')
        elif state == "installing":
            badge.setText("Installing")
        elif state == "checking":
            badge.setText("Checking")
        elif state == "error":
            badge.setText(f'<span style="color:{bad_color};">✕</span> Error')
        elif state == "not_installed":
            badge.setText(f'<span style="color:{bad_color};">✕</span> Not installed')
        else:
            badge.setText("Unknown")
        frame.setProperty("installState", state or "unknown")
        badge.setProperty("installState", state or "unknown")
        title_button.setText(self._row_header_text(spec, bool(title_button.isChecked())))
        self._sync_row_header_icon(row, bool(title_button.isChecked()))
        frame.style().unpolish(frame)
        frame.style().polish(frame)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        badge.setVisible(state in {"installed", "error", "checking"})
        profile_downloading = bool(status.get("gemma_profile_downloading"))
        button.setVisible(state in {"not_installed", "error", "installing"} and not profile_downloading)
        button.setEnabled(state in {"not_installed", "error"})
        button.setText("Installing..." if state == "installing" else "Install")
        uninstall_button.setVisible(state == "installed")
        uninstall_button.setEnabled(state == "installed")
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            delete_button.setVisible(bool(status.get("model_files_cached")))
            delete_button.setEnabled(bool(status.get("model_files_cached")))
            delete_button.setText("Delete Cache")
        else:
            delete_button.setVisible(state != "installed" and bool(status.get("model_files_cached")))
            delete_button.setEnabled(state != "installed" and bool(status.get("model_files_cached")))
            delete_button.setText("Delete Model")
        summary_html, download_html, technical_html = self._row_details_html(spec, kinds, status)
        summary_view.setProperty("installState", state)
        summary_view.set_rich_text(summary_html)
        summary_view.style().unpolish(summary_view)
        summary_view.style().polish(summary_view)
        if gemma_profile_download_status is not None:
            gemma_profile_download_status.setProperty("installState", state)
            gemma_profile_download_status.set_rich_text(download_html)
            gemma_profile_download_status.setVisible(bool(download_html))
            gemma_profile_download_status.style().unpolish(gemma_profile_download_status)
            gemma_profile_download_status.style().polish(gemma_profile_download_status)
        technical_view.setProperty("installState", state)
        technical_view.set_rich_text(technical_html)
        technical_view.setVisible(bool(details_toggle_button.isChecked()) and bool(technical_html))
        details_toggle_button.setVisible(bool(technical_html))
        if not technical_html:
            details_toggle_button.setChecked(False)
        gemma_row = row.get("gemma_profile_row")
        if gemma_row is not None:
            gemma_row.setVisible(spec.settings_key == "gemma4")
            if spec.settings_key == "gemma4":
                self._sync_gemma_profile_controls(row)
    def _install_model(self, spec) -> None:
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            if hasattr(self.bridge, "install_paddle_ocr_runtime"):
                self._apply_status("paddle_ocr", {"state": "installing", "running": True, "message": "Starting Paddle OCR runtime install..."})
                started = bool(self.bridge.install_paddle_ocr_runtime())
                if not started:
                    self._apply_status("paddle_ocr", {"state": "error", "message": "Paddle OCR runtime install did not start."})
            else:
                self._apply_status("paddle_ocr", {"state": "error", "message": "Paddle OCR install is not available in this build."})
            return
        if not hasattr(self.bridge, "install_local_ai_model"):
            self._apply_status(spec.settings_key, {"state": "error", "message": "Model installation is not available in this build."})
            return
        self.bridge.install_local_ai_model(spec.id, spec.kind)
        self.refresh_statuses()

    def _uninstall_model(self, spec) -> None:
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            if not hasattr(self.bridge, "uninstall_paddle_ocr_runtime"):
                self._apply_status("paddle_ocr", {"state": "error", "message": "Paddle OCR uninstall is not available in this build."})
                return
            reply = QMessageBox.question(
                self,
                "Uninstall Paddle OCR",
                "Uninstall the Paddle OCR runtime?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.bridge.uninstall_paddle_ocr_runtime()
            self.refresh_statuses()
            return
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

    def _delete_model_files(self, spec) -> None:
        if getattr(spec, "settings_key", "") == "paddle_ocr":
            if not hasattr(self.bridge, "delete_paddle_ocr_cache"):
                self._apply_status("paddle_ocr", {"state": "error", "message": "Paddle OCR cache delete is not available in this build."})
                return
            reply = QMessageBox.question(
                self,
                "Delete Paddle OCR Cache",
                "Delete cached Paddle OCR model and runtime cache files?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.bridge.delete_paddle_ocr_cache()
            self.refresh_statuses()
            return
        if not hasattr(self.bridge, "delete_local_ai_model_files"):
            self._apply_status(spec.settings_key, {"state": "error", "message": "Delete model files is not available in this build."})
            return
        reply = QMessageBox.question(
            self,
            "Delete Model Files",
            f"Delete cached model files for {spec.label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.bridge.delete_local_ai_model_files(spec.id, spec.kind)
        self.refresh_statuses()

    def _on_install_status(self, status_key: str, payload: dict) -> None:
        payload = dict(payload or {})
        self._apply_status(str(status_key or ""), payload)
        if not self._advanced_visible and str(status_key or "") == "gemma4":
            active = str(payload.get("state") or "").strip() in {"installing"} or bool(payload.get("gemma_profile_downloading"))
            self._set_simple_status(self._simple_recommended_message(payload), active=active)

    def _on_status_resolved(self, status_key: str, payload: dict, generation: int) -> None:
        if int(generation) != int(self._refresh_generation):
            return
        payload = dict(payload or {})
        self._apply_status(str(status_key or ""), payload)
        if not self._advanced_visible and str(status_key or "") == "gemma4" and not self.simple_status_label.isVisible():
            state = str(payload.get("state") or "").strip()
            if state == "installed":
                self._set_simple_status(
                    "Gemma 4 is setup. No further action needed.\nYou can start generating descriptions and tags using local private AI anytime now.",
                    active=False,
                )

    def _on_paddle_install_status(self, payload: dict) -> None:
        self._apply_status("paddle_ocr", self._paddle_status_payload(dict(payload or {})))

    def _on_paddle_status_resolved(self, payload: dict, generation: int) -> None:
        if int(generation) != int(self._refresh_generation):
            return
        self._apply_status("paddle_ocr", self._paddle_status_payload(dict(payload or {})))

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
        accent_text = Theme.mix(text, accent_str, 0.76)
        missing_fg = "#7c1f11" if Theme.get_is_light() else "#ffd1c7"
        error_fg = "#8a111a" if Theme.get_is_light() else "#ffd0d4"
        _check_dir = (Path(__file__).with_name("web") / "scrollbar_arrows").as_posix()
        _lum_r = accent.redF(); _lum_g = accent.greenF(); _lum_b = accent.blueF()
        def _lin(c): return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        _accent_lum = 0.2126 * _lin(_lum_r) + 0.7152 * _lin(_lum_g) + 0.0722 * _lin(_lum_b)
        check_svg = f"{_check_dir}/{'check-dark.svg' if _accent_lum > 0.179 else 'check.svg'}"
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
            QTextEdit#localAiModelDetailsView, QTextEdit#localAiTechnicalDetailsView {{
                color: {text};
                background: transparent;
                border: none;
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
                border-color: {border};
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
            QPushButton#localAiHeaderButton {{
                background: transparent;
                border: none;
                color: {text};
                padding: 0;
                min-height: 0;
                text-align: left;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton#localAiHeaderButton:hover {{
                color: {text};
                background: transparent;
                border: none;
            }}
            QPushButton#localAiHeaderButton:pressed {{
                color: {text};
                background: transparent;
                border: none;
            }}
            QLabel#localAiModelInstallMessage {{
                color: {muted};
                padding-top: 4px;
            }}
            QLabel#localAiModelInstallMessage[installState="error"] {{
                color: {error_fg};
            }}
            QCheckBox {{
                color: {text};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {border};
                background-color: {control_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_str};
                border-color: {accent_str};
                image: url("{check_svg}");
            }}
            QCheckBox::indicator:hover {{
                border-color: {accent_str};
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
            QPushButton#localAiDeleteButton {{
                background-color: {control_bg};
                border-color: {border};
                color: {muted};
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton#localAiDeleteButton:hover {{
                color: {text};
                border-color: {accent_str};
                background-color: {hover};
            }}
            QPushButton#localAiProfileActionButton, QPushButton#localAiProfileDeleteButton {{
                background-color: {Theme.get_btn_save_bg(accent)};
                border-color: {border};
                font-weight: 600;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton#localAiProfileActionButton:hover, QPushButton#localAiProfileDeleteButton:hover {{
                background-color: {hover};
                border-color: {accent_str};
            }}
            QComboBox#localAiProfileCombo {{
                background-color: {Theme.mix(control_bg, "#ffffff", 0.16 if Theme.get_is_light() else 0.12)};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 28px;
            }}
            QComboBox#localAiProfileCombo:hover {{
                border-color: {accent_str};
            }}
            QComboBox#localAiProfileCombo QAbstractItemView {{
                background-color: {bg};
                border: 1px solid {border};
                selection-background-color: {accent_soft};
                selection-color: {text};
            }}
            QLabel#localAiModelMeta {{
                color: {muted};
                font-size: 11px;
            }}
            QLabel#localAiModelRecommended {{
                color: {accent_text};
                font-size: 11px;
                font-weight: 700;
            }}
            QToolButton#localAiDetailsToggle {{
                color: {muted};
                background: transparent;
                border: none;
                padding: 0;
                text-align: left;
                font-size: 12px;
                font-weight: 700;
            }}
            QToolButton#localAiDetailsToggle:hover {{
                color: {text};
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




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
