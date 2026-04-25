from __future__ import annotations

from native.mediamanagerx_app.settings_common import *
from native.mediamanagerx_app.settings_general_pages import *
from native.mediamanagerx_app.settings_scanner_metadata_pages import *
from native.mediamanagerx_app.settings_duplicate_pages import *
from native.mediamanagerx_app.settings_ai_pages import *


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

        self.category_list.currentRowChanged.connect(self._on_category_changed)
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

    def open_ai_page(self) -> None:
        for index, (title, _page) in enumerate(self._page_defs):
            if str(title) == "AI":
                self.category_list.setCurrentRow(index)
                break
        self.open_dialog()

    def refresh_from_settings(self) -> None:
        current_row = max(self.category_list.currentRow(), 0)
        self._apply_theme()
        if self.category_list.count():
            self.category_list.setCurrentRow(current_row)
            page = self.pages.widget(current_row)
            if page is not None:
                page.refresh()

    def _on_category_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        page = self.pages.widget(int(index))
        if page is not None:
            page.refresh()

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
        radio_dot = "#000000" if Theme.get_is_light() else "#ffffff"
        
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
            QWidget#settingsExpandableGroup {{
                background-color: {Theme.mix(control_bg, bg, 0.42)};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QToolButton#settingsExpandableHeader {{
                background: transparent;
                color: {text};
                border: none;
                padding: 2px 0px;
                font-weight: 600;
                text-align: left;
            }}
            QToolButton#settingsExpandableHeader:hover {{
                color: {accent_str};
            }}
            QFrame#settingsExpandableDivider {{
                background-color: {Theme.mix(border, accent, 0.26)};
                min-height: 1px;
                max-height: 1px;
                border: none;
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
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid {border};
                background-color: {control_bg};
            }}
            QRadioButton::indicator:hover {{
                border-color: {accent_str};
            }}
            QRadioButton::indicator:checked {{
                border-color: {accent_str};
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {radio_dot}, stop:0.34 {radio_dot}, stop:0.36 {accent_str}, stop:1 {accent_str});
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


__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
