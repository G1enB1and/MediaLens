from __future__ import annotations

from native.mediamanagerx_app.settings_common import *

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
        self.startup_none_radio = QRadioButton("Do not open a folder on launch")
        self.restore_last_toggle = QRadioButton("Restore previous folder on launch")
        self.startup_specific_radio = QRadioButton("Open a specific folder on launch")
        self.startup_mode_buttons = QButtonGroup(self)
        self.startup_mode_buttons.addButton(self.startup_none_radio)
        self.startup_mode_buttons.addButton(self.restore_last_toggle)
        self.startup_mode_buttons.addButton(self.startup_specific_radio)
        self.show_hidden_toggle = QCheckBox("Show hidden files and folders")
        self.include_nested_files_toggle = QCheckBox("Include nested files in gallery")
        self.show_folders_in_gallery_toggle = QCheckBox("Show folders in gallery")
        startup_layout.addWidget(self.randomize_toggle)
        startup_layout.addWidget(self.startup_none_radio)
        startup_layout.addWidget(self.restore_last_toggle)
        startup_layout.addWidget(self.startup_specific_radio)
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
        self.startup_none_radio.toggled.connect(self._on_startup_none_changed)
        self.restore_last_toggle.toggled.connect(self._on_restore_last_changed)
        self.startup_specific_radio.toggled.connect(self._on_startup_specific_changed)
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
        enabled = self.startup_specific_radio.isChecked()
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
        if not checked:
            return
        self.dialog.set_setting_str("gallery.startup_mode", "last")
        self.dialog.set_setting_bool("gallery.restore_last", True)
        self._sync_start_folder_enabled()

    def _on_startup_none_changed(self, checked: bool) -> None:
        if not checked:
            return
        self.dialog.set_setting_str("gallery.startup_mode", "none")
        self.dialog.set_setting_bool("gallery.restore_last", False)
        self._sync_start_folder_enabled()

    def _on_startup_specific_changed(self, checked: bool) -> None:
        if not checked:
            return
        self.dialog.set_setting_str("gallery.startup_mode", "specific")
        self.dialog.set_setting_bool("gallery.restore_last", False)
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
        startup_mode = str(state.get("gallery.startup_mode", "none") or "none")
        if startup_mode not in {"none", "last", "specific"}:
            startup_mode = "last" if bool(state.get("gallery.restore_last", False)) else "none"
        with QSignalBlocker(self.startup_none_radio):
            self.startup_none_radio.setChecked(startup_mode == "none")
        with QSignalBlocker(self.restore_last_toggle):
            self.restore_last_toggle.setChecked(startup_mode == "last")
        with QSignalBlocker(self.startup_specific_radio):
            self.startup_specific_radio.setChecked(startup_mode == "specific")
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




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
