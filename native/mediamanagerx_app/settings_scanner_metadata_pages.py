from __future__ import annotations

from PySide6.QtCore import Slot

from native.mediamanagerx_app.image_utils import _read_image_with_svg_support, _render_svg_image
from native.mediamanagerx_app.settings_common import *
from native.mediamanagerx_app.settings_general_pages import *

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
            ocr_source_row = QWidget()
            ocr_source_layout = QVBoxLayout(ocr_source_row)
            ocr_source_layout.setContentsMargins(0, 0, 0, 0)
            ocr_source_layout.setSpacing(4)
            ocr_fast_toggle = QCheckBox("Fast OCR")
            ocr_ai_toggle = QCheckBox("AI Generated OCR")
            ocr_source_layout.addWidget(QLabel("OCR Versions to run:"))
            ocr_source_layout.addWidget(ocr_fast_toggle)
            ocr_source_layout.addWidget(ocr_ai_toggle)
            ocr_source_row.setVisible(key == "ocr_text")
            ocr_scope_row = QWidget()
            ocr_scope_layout = QVBoxLayout(ocr_scope_row)
            ocr_scope_layout.setContentsMargins(0, 0, 0, 0)
            ocr_scope_layout.setSpacing(4)
            ocr_scope_label = QLabel("Files to scan:")
            ocr_scope_detected_radio = QRadioButton("Only files set to Text Detected")
            ocr_scope_all_radio = QRadioButton("All files in scope")
            ocr_scope_group = QButtonGroup(ocr_scope_row)
            ocr_scope_group.addButton(ocr_scope_detected_radio)
            ocr_scope_group.addButton(ocr_scope_all_radio)
            ocr_scope_layout.addWidget(ocr_scope_label)
            ocr_scope_layout.addWidget(ocr_scope_detected_radio)
            ocr_scope_layout.addWidget(ocr_scope_all_radio)
            ocr_scope_row.setVisible(key == "ocr_text")

            schedule_row = QHBoxLayout()
            schedule_row.setContentsMargins(0, 0, 0, 0)
            schedule_label = QLabel("Run every")
            interval = QSpinBox()
            interval.setRange(1, 24 * 30)
            interval.setSuffix(" hours")
            schedule_row.addWidget(schedule_label)
            schedule_row.addWidget(interval)
            schedule_row.addStretch(1)

            source_group = QGroupBox("Scanners Scope")
            source_layout = QVBoxLayout(source_group)
            source_layout.setSpacing(6)
            source_note = _description("Scheduled scanner runs use these folders instead of the current gallery selection.")
            source_list = QListWidget()
            source_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            source_list.setMinimumHeight(74)
            source_list.setMaximumHeight(120)
            source_buttons = QHBoxLayout()
            source_buttons.setContentsMargins(0, 0, 0, 0)
            add_source_btn = QPushButton("Add Folder")
            remove_source_btn = QPushButton("Remove")
            source_buttons.addWidget(add_source_btn)
            source_buttons.addWidget(remove_source_btn)
            source_buttons.addStretch(1)
            source_layout.addWidget(source_note)
            source_layout.addWidget(source_list)
            source_layout.addLayout(source_buttons)

            action_row = QHBoxLayout()
            action_row.setContentsMargins(0, 0, 0, 0)
            run_btn = QPushButton("Run Now")
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setVisible(key == "ocr_text")
            cancel_btn.setEnabled(False)
            status_label = QLabel("Status: Idle")
            status_label.setWordWrap(True)
            action_row.addWidget(run_btn)
            action_row.addWidget(cancel_btn)
            action_row.addWidget(status_label, 1)

            last_run_label = QLabel("Last run: Never")
            last_run_label.setWordWrap(True)
            review_btn = QPushButton("Review Flagged OCR")
            review_btn.setVisible(key == "ocr_text")

            group_layout.addWidget(desc_label)
            group_layout.addWidget(enable_toggle)
            group_layout.addWidget(ocr_source_row)
            group_layout.addWidget(ocr_scope_row)
            group_layout.addLayout(schedule_row)
            group_layout.addWidget(source_group)
            group_layout.addLayout(action_row)
            group_layout.addWidget(review_btn)
            group_layout.addWidget(last_run_label)
            layout.addWidget(group)

            self._widgets[key] = {
                "enable": enable_toggle,
                "ocr_source_row": ocr_source_row,
                "ocr_fast": ocr_fast_toggle,
                "ocr_ai": ocr_ai_toggle,
                "ocr_scope_row": ocr_scope_row,
                "ocr_scope_detected": ocr_scope_detected_radio,
                "ocr_scope_all": ocr_scope_all_radio,
                "interval": interval,
                "source_group": source_group,
                "source_list": source_list,
                "add_source": add_source_btn,
                "remove_source": remove_source_btn,
                "run": run_btn,
                "cancel": cancel_btn,
                "review": review_btn,
                "status": status_label,
                "last_run": last_run_label,
            }
            enable_toggle.toggled.connect(lambda checked, scanner_key=key: self._set_enabled(scanner_key, checked))
            ocr_fast_toggle.toggled.connect(lambda checked, source_key="run_fast": self._set_ocr_source_enabled(source_key, checked))
            ocr_ai_toggle.toggled.connect(lambda checked, source_key="run_ai": self._set_ocr_source_enabled(source_key, checked))
            ocr_scope_detected_radio.toggled.connect(lambda checked: checked and self._set_ocr_scope_all_files(False))
            ocr_scope_all_radio.toggled.connect(lambda checked: checked and self._set_ocr_scope_all_files(True))
            interval.valueChanged.connect(lambda value, scanner_key=key: self._set_interval(scanner_key, int(value)))
            add_source_btn.clicked.connect(lambda _checked=False, scanner_key=key: self._add_source_folder(scanner_key))
            remove_source_btn.clicked.connect(lambda _checked=False, scanner_key=key: self._remove_selected_source_folders(scanner_key))
            run_btn.clicked.connect(lambda _checked=False, scanner_key=key: self._run_now(scanner_key))
            cancel_btn.clicked.connect(lambda _checked=False, scanner_key=key: self._cancel(scanner_key))
            review_btn.clicked.connect(self._open_ocr_review)

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

    def _set_ocr_source_enabled(self, source_key: str, checked: bool) -> None:
        self.dialog.set_setting_bool(f"scanners.ocr_text.{source_key}", checked)

    def _set_ocr_scope_all_files(self, checked: bool) -> None:
        self.dialog.set_setting_bool("scanners.ocr_text.all_files", checked)

    @staticmethod
    def _clean_source_folders(values: list[object]) -> list[str]:
        folders: list[str] = []
        seen: set[str] = set()
        for value in values:
            folder = str(value or "").strip()
            if not folder:
                continue
            key = str(Path(folder)).casefold()
            if key in seen:
                continue
            seen.add(key)
            folders.append(folder)
        return folders

    def _source_folders(self, scanner_key: str) -> list[str]:
        widgets = self._widgets.get(scanner_key) or {}
        source_list = widgets.get("source_list")
        if not isinstance(source_list, QListWidget):
            return []
        return [str(source_list.item(i).data(Qt.ItemDataRole.UserRole) or source_list.item(i).text()) for i in range(source_list.count())]

    def _source_folders_from_settings(self, scanner_key: str) -> list[str]:
        try:
            raw = str(self.settings.value(f"scanners/{scanner_key}/source_folders", "", type=str) or "")
            parsed = json.loads(raw or "[]")
        except Exception:
            parsed = []
        return self._clean_source_folders(list(parsed or []) if isinstance(parsed, list) else [])

    def _save_source_folders(self, scanner_key: str, folders: list[str]) -> None:
        self.dialog.set_setting_str(f"scanners.{scanner_key}.source_folders", json.dumps(self._clean_source_folders(list(folders or []))))

    def _add_source_folder(self, scanner_key: str) -> None:
        current = ""
        folders = self._source_folders(scanner_key)
        if folders:
            current = folders[-1]
        elif self.bridge and getattr(self.bridge, "_selected_folders", None):
            current = str(self.bridge._selected_folders[0])
        selected = QFileDialog.getExistingDirectory(self, "Add Scanner Source Folder", current)
        if not selected:
            return
        folders.append(str(selected))
        self._save_source_folders(scanner_key, folders)
        self._set_source_folders(scanner_key, folders)

    def _remove_selected_source_folders(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        source_list = widgets.get("source_list")
        if not isinstance(source_list, QListWidget):
            return
        selected_rows = {source_list.row(item) for item in source_list.selectedItems()}
        folders = [folder for index, folder in enumerate(self._source_folders(scanner_key)) if index not in selected_rows]
        self._save_source_folders(scanner_key, folders)
        self._set_source_folders(scanner_key, folders)

    def _set_source_folders(self, scanner_key: str, folders: list[str]) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        source_list = widgets.get("source_list")
        if not isinstance(source_list, QListWidget):
            return
        source_list.clear()
        for folder in self._clean_source_folders(list(folders or [])):
            item = QListWidgetItem(folder)
            item.setToolTip(folder)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            source_list.addItem(item)

    def _run_now(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        status = widgets.get("status")
        if isinstance(status, QLabel):
            status.setText("Status: Starting...")
        try:
            if hasattr(self.bridge, "run_scanner_now"):
                started = bool(self.bridge.run_scanner_now(scanner_key))
                if not started and isinstance(status, QLabel):
                    status.setText("Status: Nothing to run")
        except Exception:
            if isinstance(status, QLabel):
                status.setText("Status: Error starting scanner")

    def _cancel(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        status = widgets.get("status")
        try:
            canceled = bool(self.bridge.cancel_scanner(scanner_key)) if hasattr(self.bridge, "cancel_scanner") else False
            if not canceled and isinstance(status, QLabel):
                status.setText("Status: Nothing to cancel")
        except Exception:
            if isinstance(status, QLabel):
                status.setText("Status: Error canceling scanner")

    def _sync_enabled_state(self, scanner_key: str) -> None:
        widgets = self._widgets.get(scanner_key) or {}
        enable = widgets.get("enable")
        enabled = bool(enable.isChecked()) if isinstance(enable, QCheckBox) else True
        for child_key in ("interval",):
            widget = widgets.get(child_key)
            if widget is not None:
                widget.setEnabled(enabled)
        for child_key in ("source_group", "source_list", "add_source", "remove_source"):
            widget = widgets.get(child_key)
            if widget is not None:
                widget.setEnabled(enabled)
        run_btn = widgets.get("run")
        if run_btn is not None:
            run_btn.setEnabled(True)
        cancel_btn = widgets.get("cancel")
        if cancel_btn is not None:
            cancel_btn.setEnabled(False)

    def _open_ocr_review(self) -> None:
        dialog = OcrReviewDialog(self)
        dialog.exec()

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
        cancel_btn = widgets.get("cancel")
        running = bool(payload.get("running"))
        ocr_fast = widgets.get("ocr_fast")
        ocr_ai = widgets.get("ocr_ai")
        ocr_scope_detected = widgets.get("ocr_scope_detected")
        ocr_scope_all = widgets.get("ocr_scope_all")
        self._set_source_folders(scanner_key, list(payload.get("source_folders") or []))
        if isinstance(enable, QCheckBox):
            with QSignalBlocker(enable):
                enable.setChecked(enabled)
        if isinstance(ocr_fast, QCheckBox):
            with QSignalBlocker(ocr_fast):
                ocr_fast.setChecked(bool(payload.get("run_fast", True)))
        if isinstance(ocr_ai, QCheckBox):
            with QSignalBlocker(ocr_ai):
                ocr_ai.setChecked(bool(payload.get("run_ai", False)))
        all_files = bool(payload.get("all_files", False))
        if isinstance(ocr_scope_detected, QRadioButton):
            with QSignalBlocker(ocr_scope_detected):
                ocr_scope_detected.setChecked(not all_files)
        if isinstance(ocr_scope_all, QRadioButton):
            with QSignalBlocker(ocr_scope_all):
                ocr_scope_all.setChecked(all_files)
        if isinstance(interval, QSpinBox):
            with QSignalBlocker(interval):
                interval.setValue(max(1, interval_value))
        if isinstance(status, QLabel):
            status.setText(f"Status: {payload.get('status') or 'Idle'}")
        if isinstance(last_run, QLabel):
            last_run.setText(f"Last run: {self._format_last_run(payload.get('last_run_utc'))}")
        self._sync_enabled_state(scanner_key)
        if cancel_btn is not None:
            cancel_btn.setEnabled(running)

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
                    "run_fast": bool(self.settings.value("scanners/ocr_text/run_fast", True, type=bool)),
                    "run_ai": bool(self.settings.value("scanners/ocr_text/run_ai", False, type=bool)),
                    "all_files": bool(self.settings.value("scanners/ocr_text/all_files", False, type=bool)),
                    "source_folders": self._source_folders_from_settings(scanner_key),
                }
            self._apply_status(scanner_key, payload)


class OcrReviewDialog(QDialog):
    SOURCE_LABELS = {
        "paddle_fast": "Fast OCR",
        "gemma4": "Gemma OCR",
        "user": "User Typed",
        "windows_ocr_legacy": "Windows OCR",
    }

    def __init__(self, page: ScannersSettingsPage) -> None:
        super().__init__(page)
        self.page = page
        self.bridge = page.bridge
        self._pending_ocr_paths: set[str] = set()
        self._pending_ocr_cells: dict[str, tuple[str, QPlainTextEdit, QPushButton]] = {}
        self.setWindowTitle("Review OCR Results")
        self.resize(1100, 720)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        header = QLabel("Files with conflicting or low-confidence OCR results")
        header.setObjectName("settingsFieldTitle")
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(12)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
        if hasattr(self.bridge, "manualOcrFinished"):
            self.bridge.manualOcrFinished.connect(self._on_manual_ocr_finished)
        self._reload()

    def _reload(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        try:
            rows = self.bridge.get_ocr_review_items() if hasattr(self.bridge, "get_ocr_review_items") else []
        except Exception:
            rows = []
        if not rows:
            empty = QLabel("No OCR results need review.")
            empty.setWordWrap(True)
            self.content_layout.addWidget(empty)
            self.content_layout.addStretch(1)
            return
        for item in rows:
            self.content_layout.addWidget(self._build_review_row(dict(item or {})))
        self.content_layout.addStretch(1)

    def _build_review_row(self, item: dict) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(8)
        title = QLabel(Path(str(item.get("path") or "")).name or str(item.get("path") or ""))
        title.setObjectName("settingsFieldTitle")
        title.setWordWrap(True)
        reason = QLabel(f"Review reason: {item.get('reason') or 'review needed'}")
        reason.setWordWrap(True)
        panel_layout.addWidget(title)
        panel_layout.addWidget(reason)

        grid = QGridLayout()
        grid.setSpacing(8)
        preview = QLabel()
        preview.setMinimumSize(180, 120)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setText("Preview")
        pixmap = self._review_preview_pixmap(str(item.get("path") or ""))
        if pixmap is not None and not pixmap.isNull():
            preview.setText("")
            preview.setPixmap(pixmap)
        grid.addWidget(preview, 0, 0)

        results = list(item.get("results") or [])
        latest_by_source: dict[str, dict] = {}
        for result in results:
            latest_by_source.setdefault(str(result.get("source") or ""), dict(result or {}))
        if "user" not in latest_by_source:
            winner = dict(item.get("winner") or {})
            latest_by_source["user"] = {
                "id": 0,
                "media_id": int(item.get("media_id") or 0),
                "source": "user",
                "text": str(item.get("detected_text") or winner.get("text") or ""),
                "confidence": 1.0,
            }
        for required_source in ("paddle_fast", "gemma4", "user"):
            if required_source not in latest_by_source:
                latest_by_source[required_source] = {
                    "id": 0,
                    "media_id": int(item.get("media_id") or 0),
                    "source": required_source,
                    "text": "",
                    "confidence": None,
                }
        ordered_sources = ["paddle_fast", "gemma4", "user", "windows_ocr_legacy"]
        col = 1
        for source in ordered_sources:
            result = latest_by_source.get(source)
            if result is None:
                continue
            grid.addWidget(self._build_result_cell(int(item.get("media_id") or 0), str(item.get("path") or ""), result), 0, col)
            col += 1
        panel_layout.addLayout(grid)
        return panel

    def _review_preview_pixmap(self, path: str) -> QPixmap | None:
        clean_path = str(path or "").strip()
        if not clean_path:
            return None
        source_path = Path(clean_path)
        try:
            if hasattr(self.bridge, "_local_ai_source_path"):
                source_path = self.bridge._local_ai_source_path(source_path)
        except Exception:
            source_path = Path(clean_path)
        try:
            if source_path.suffix.lower() == ".svg":
                image = _render_svg_image(source_path, QSize(220, 160))
            else:
                image = _read_image_with_svg_support(source_path)
            if image is None or image.isNull():
                return None
            return QPixmap.fromImage(image).scaled(
                220,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception:
            return None

    def _build_result_cell(self, media_id: int, path: str, result: dict) -> QWidget:
        cell = QFrame()
        cell.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(cell)
        layout.setSpacing(6)
        source = str(result.get("source") or "")
        confidence = result.get("confidence")
        confidence_text = "" if confidence is None else f" ({float(confidence):.0%})"
        label = QLabel(f"{self.SOURCE_LABELS.get(source, source or 'OCR')}{confidence_text}")
        label.setObjectName("settingsFieldTitle")
        text = QPlainTextEdit(str(result.get("text") or ""))
        is_user_text = source == "user"
        text.setReadOnly(not is_user_text)
        text.setMinimumWidth(190)
        text.setMinimumHeight(120)
        keep_btn = QPushButton("Keep")
        result_id = int(result.get("id") or 0)
        if is_user_text:
            keep_btn.clicked.connect(lambda _checked=False, mid=media_id, edit=text: self._keep_user_text(mid, edit.toPlainText()))
        else:
            if result_id > 0:
                keep_btn.clicked.connect(lambda _checked=False, mid=media_id, rid=result_id: self._keep_result(mid, rid))
            else:
                keep_btn.clicked.connect(lambda _checked=False, mid=media_id, src=source: self._keep_source_result(mid, src))
            keep_btn.setEnabled(result_id > 0)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)
        button_row.addWidget(keep_btn)
        if is_user_text:
            no_text_btn = QPushButton("No Text")
            no_text_btn.clicked.connect(lambda _checked=False, mid=media_id: self._mark_no_text(mid))
            button_row.addWidget(no_text_btn)
        if source in {"paddle_fast", "gemma4"}:
            generate_btn = QPushButton("Generate")
            generate_btn.clicked.connect(lambda _checked=False, p=path, s=source, edit=text, keep=keep_btn: self._generate_ocr(p, s, edit, keep))
            button_row.addWidget(generate_btn)
        button_row.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(text, 1)
        layout.addLayout(button_row)
        return cell

    def _generate_ocr(self, path: str, source: str, edit: QPlainTextEdit, keep_btn: QPushButton) -> None:
        clean_path = str(path or "").strip()
        if not clean_path or not hasattr(self.bridge, "run_manual_ocr_with_source"):
            return
        self._pending_ocr_paths.add(clean_path)
        self._pending_ocr_cells[clean_path] = (str(source or "paddle_fast"), edit, keep_btn)
        edit.setPlainText("Running OCR...")
        self.bridge.run_manual_ocr_with_source(clean_path, str(source or "paddle_fast"))

    @Slot(str, str, str)
    def _on_manual_ocr_finished(self, path: str, text: str, error: str) -> None:
        clean_path = str(path or "").strip()
        if clean_path not in self._pending_ocr_paths:
            return
        self._pending_ocr_paths.discard(clean_path)
        source, edit, keep_btn = self._pending_ocr_cells.pop(clean_path, ("", None, None))
        if error:
            QMessageBox.warning(self, "OCR Failed", str(error or "OCR failed."))
            return
        if edit is not None:
            edit.setPlainText(str(text or ""))
        if keep_btn is not None:
            keep_btn.setEnabled(bool(str(text or "").strip()))

    def _keep_result(self, media_id: int, result_id: int) -> None:
        try:
            if self.bridge.keep_ocr_result(int(media_id), int(result_id)):
                self._reload()
        except Exception:
            pass

    def _keep_source_result(self, media_id: int, source: str) -> None:
        try:
            if hasattr(self.bridge, "keep_latest_ocr_result_source") and self.bridge.keep_latest_ocr_result_source(int(media_id), str(source or "")):
                self._reload()
        except Exception:
            pass

    def _keep_user_text(self, media_id: int, text: str) -> None:
        try:
            if self.bridge.keep_user_ocr_text(int(media_id), str(text or "")):
                self._reload()
        except Exception:
            pass

    def _mark_no_text(self, media_id: int) -> None:
        try:
            if hasattr(self.bridge, "mark_ocr_review_no_text") and self.bridge.mark_ocr_review_no_text(int(media_id)):
                self._reload()
        except Exception:
            pass


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




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
