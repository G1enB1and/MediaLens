from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *

class Theme:
    """Centralized theme system with neutral surfaces and restrained accent usage."""
    _theme_mode_override: str | None = None

    @staticmethod
    def mix(base_hex: str, accent_color: QColor | str, strength: float) -> str:
        """Mix a base hex color with an accent QColor (or hex string)."""
        base = QColor(base_hex)
        acc = QColor(accent_color) if isinstance(accent_color, str) else accent_color
        r = int(base.red() + (acc.red() - base.red()) * strength)
        g = int(base.green() + (acc.green() - base.green()) * strength)
        b = int(base.blue() + (acc.blue() - base.blue()) * strength)
        return QColor(r, g, b).name()

    BASE_BG_DARK = "#1e1e1e"
    BASE_SIDEBAR_BG_DARK = "#252526"
    BASE_CONTROL_BG_DARK = "#2d2d30"
    BASE_BORDER_DARK = "#3b3b40"

    BASE_BG_LIGHT = "#f4f5f7"
    BASE_SIDEBAR_BG_LIGHT = "#fbfbfc"
    BASE_CONTROL_BG_LIGHT = "#ffffff"
    BASE_BORDER_LIGHT = "#d9dde3"

    @staticmethod
    def set_theme_mode(mode: str | None) -> None:
        clean = str(mode or "").strip().lower()
        if clean not in {"light", "dark"}:
            Theme._theme_mode_override = None
            return
        Theme._theme_mode_override = clean
    
    @staticmethod
    def get_is_light() -> bool:
        if Theme._theme_mode_override in {"light", "dark"}:
            return Theme._theme_mode_override == "light"
        settings = app_settings()
        val = settings.value("ui/theme_mode", "dark")
        # Ensure we handle both string and potential type-wrapped values cleanly
        return str(val).lower() == "light"

    @staticmethod
    def get_bg(accent: QColor) -> str:
        return Theme.BASE_BG_LIGHT if Theme.get_is_light() else Theme.BASE_BG_DARK

    @staticmethod
    def get_sidebar_bg(accent: QColor) -> str:
        return Theme.BASE_SIDEBAR_BG_LIGHT if Theme.get_is_light() else Theme.BASE_SIDEBAR_BG_DARK

    @staticmethod
    def get_control_bg(accent: QColor) -> str:
        return Theme.BASE_CONTROL_BG_LIGHT if Theme.get_is_light() else Theme.BASE_CONTROL_BG_DARK

    @staticmethod
    def get_border(accent: QColor) -> str:
        return Theme.BASE_BORDER_LIGHT if Theme.get_is_light() else Theme.BASE_BORDER_DARK

    @staticmethod
    def get_scrollbar_track(accent: QColor) -> str:
        return "#181818" if not Theme.get_is_light() else "#f1f2f4"

    @staticmethod
    def get_scrollbar_thumb(accent: QColor) -> str:
        return "#c3c8d1" if Theme.get_is_light() else "#4a4a50"

    @staticmethod
    def get_scrollbar_thumb_hover(accent: QColor) -> str:
        return "#aeb5bf" if Theme.get_is_light() else "#5a5a61"

    @staticmethod
    def get_splitter_idle(accent: QColor) -> str:
        return "#c8ccd3" if Theme.get_is_light() else "#4a4a50"

    @staticmethod
    def get_accent_soft(accent: QColor) -> str:
        base = Theme.get_control_bg(accent)
        strength = 0.18 if Theme.get_is_light() else 0.16
        return Theme.mix(base, accent, strength)

    # UI constants
    @staticmethod
    def get_text_color() -> str:
        return "#1f2329" if Theme.get_is_light() else "#f2f2f3"

    @staticmethod
    def get_text_muted() -> str:
        return "#60656f" if Theme.get_is_light() else "#b4b7bd"

    @staticmethod
    def get_btn_save_bg(accent: QColor) -> str:
        return Theme.get_control_bg(accent)

    @staticmethod
    def get_btn_save_hover(accent: QColor) -> str:
        return Theme.get_accent_soft(accent)

    @staticmethod
    def get_input_bg(accent: QColor) -> str:
        return Theme.get_control_bg(accent)

    @staticmethod
    def get_input_border(accent: QColor) -> str:
        return Theme.get_border(accent)

    ACCENT_DEFAULT = "#8ab4f8"


class ToolTipProxyStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 300
        return super().styleHint(hint, option, widget, returnData)


def _selection_text_for_color(color: QColor | str) -> str:
    q = QColor(color)
    if not q.isValid():
        return "#ffffff"

    def _to_linear(channel: int) -> float:
        value = max(0.0, min(1.0, channel / 255.0))
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * _to_linear(q.red())
        + 0.7152 * _to_linear(q.green())
        + 0.0722 * _to_linear(q.blue())
    )
    contrast_black = (luminance + 0.05) / 0.05
    contrast_white = 1.05 / (luminance + 0.05)
    return "#000000" if contrast_black >= contrast_white else "#ffffff"


def _dialog_accent() -> QColor:
    try:
        accent = str(app_settings().value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
    except Exception:
        accent = Theme.ACCENT_DEFAULT
    resolved = QColor(accent)
    return resolved if resolved.isValid() else QColor(Theme.ACCENT_DEFAULT)


def _themed_input_dialog_stylesheet(accent_q: QColor) -> str:
    bg = Theme.get_bg(accent_q)
    control_bg = Theme.get_input_bg(accent_q)
    fg = Theme.get_text_color()
    muted = Theme.get_text_muted()
    border = Theme.get_input_border(accent_q)
    popup_border = Theme.mix(border, accent_q, 0.18)
    btn_bg = Theme.get_btn_save_bg(accent_q)
    btn_hover = Theme.get_btn_save_hover(accent_q)
    selection_text = _selection_text_for_color(accent_q)
    accent_str = accent_q.name()
    return f"""
        QInputDialog {{
            background-color: {bg};
            color: {fg};
        }}
        QLabel {{
            color: {fg};
            background: transparent;
        }}
        QLineEdit, QComboBox, QListView {{
            background-color: {control_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QLineEdit, QComboBox {{
            padding: 6px 8px;
            selection-background-color: {accent_str};
            selection-color: {selection_text};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 1px solid {accent_str};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView, QListView {{
            background-color: {control_bg};
            color: {fg};
            border: 1px solid {popup_border};
            border-radius: 8px;
            padding: 4px;
            selection-background-color: {accent_str};
            selection-color: {selection_text};
            outline: none;
        }}
        QComboBox QAbstractItemView::item, QListView::item {{
            min-height: 24px;
            padding: 6px 10px;
            margin: 2px 0;
            border-radius: 6px;
            background: transparent;
        }}
        QPushButton {{
            background-color: {btn_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 8px 18px;
            font-weight: 600;
            min-width: 84px;
        }}
        QPushButton:hover {{
            background-color: {btn_hover};
            border: 1px solid {accent_str};
        }}
        QPushButton:pressed {{
            background-color: {Theme.mix(btn_hover, accent_q, 0.12)};
            border: 1px solid {accent_str};
        }}
        QPushButton:disabled {{
            color: {muted};
        }}
    """


def _themed_message_box_stylesheet(accent_q: QColor) -> str:
    bg = Theme.get_bg(accent_q)
    control_bg = Theme.get_input_bg(accent_q)
    fg = Theme.get_text_color()
    muted = Theme.get_text_muted()
    border = Theme.get_input_border(accent_q)
    btn_bg = Theme.get_btn_save_bg(accent_q)
    btn_hover = Theme.get_btn_save_hover(accent_q)
    accent_str = accent_q.name()
    return f"""
        QMessageBox {{
            background-color: {bg};
            color: {fg};
        }}
        QMessageBox QLabel {{
            color: {fg};
            background: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {btn_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 8px 18px;
            min-width: 88px;
            font-weight: 600;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {btn_hover};
            border: 1px solid {accent_str};
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {Theme.mix(btn_hover, accent_q, 0.12)};
            border: 1px solid {accent_str};
        }}
        QMessageBox QPushButton:disabled {{
            color: {muted};
        }}
        QMessageBox QWidget {{
            background-color: {bg};
            color: {fg};
        }}
        QMessageBox QTextEdit, QMessageBox QPlainTextEdit {{
            background-color: {control_bg};
            color: {fg};
            border: 1px solid {border};
        }}
    """


def _question_icon_pixmap(accent_q: QColor, size: int = 36) -> QPixmap:
    accent = QColor(accent_q)
    if not accent.isValid():
        accent = QColor(Theme.ACCENT_DEFAULT)
    glyph = QColor(_selection_text_for_color(accent))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    painter.drawEllipse(0, 0, size, size)

    font = QFont()
    font.setBold(True)
    font.setPointSizeF(max(14.0, size * 0.48))
    painter.setFont(font)
    painter.setPen(glyph)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return pixmap


def _run_themed_question_dialog(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.No,
) -> QMessageBox.StandardButton:
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.NoIcon)
    accent_q = _dialog_accent()
    dialog.setIconPixmap(_question_icon_pixmap(accent_q))
    dialog.setWindowTitle(title)
    dialog.setText(text)
    dialog.setStandardButtons(buttons)
    dialog.setDefaultButton(default_button)
    dialog.setStyleSheet(_themed_message_box_stylesheet(accent_q))
    return QMessageBox.StandardButton(dialog.exec())


def _run_themed_text_input_dialog(
    parent: QWidget | None,
    title: str,
    label: str,
    *,
    text: str = "",
    echo: QLineEdit.EchoMode = QLineEdit.EchoMode.Normal,
) -> tuple[str, bool]:
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(str(text or ""))
    dialog.setTextEchoMode(echo)
    dialog.setOption(QInputDialog.InputDialogOption.UsePlainTextEditForTextInput, False)
    dialog.setStyleSheet(_themed_input_dialog_stylesheet(_dialog_accent()))
    dialog.resize(420, dialog.sizeHint().height())
    ok = dialog.exec() == int(QDialog.DialogCode.Accepted)
    return dialog.textValue(), ok


def _run_themed_item_input_dialog(
    parent: QWidget | None,
    title: str,
    label: str,
    items: list[str],
    *,
    current: int = 0,
    editable: bool = False,
) -> tuple[str, bool]:
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setComboBoxItems([str(item) for item in items])
    dialog.setComboBoxEditable(bool(editable))
    if items:
        safe_index = max(0, min(int(current), len(items) - 1))
        dialog.setTextValue(str(items[safe_index]))
    dialog.setStyleSheet(_themed_input_dialog_stylesheet(_dialog_accent()))
    dialog.resize(440, dialog.sizeHint().height())
    ok = dialog.exec() == int(QDialog.DialogCode.Accepted)
    return dialog.textValue(), ok


def _rounded_preview_pixmap(source: QPixmap, target: QSize, border_color: str, radius: float = 10.0) -> QPixmap:
    scaled = source.scaled(
        target,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        return scaled
    result = QPixmap(scaled.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    draw_rect = QRectF(0.5, 0.5, max(0.0, result.width() - 1.0), max(0.0, result.height() - 1.0))
    path = QPainterPath()
    path.addRoundedRect(draw_rect, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.setClipping(False)
    pen = QPen(QColor(border_color))
    pen.setWidth(1)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(draw_rect, radius, radius)
    painter.end()
    return result


class FileConflictDialog(QDialog):
    def __init__(self, existing_path: Path, incoming_path: Path, bridge, parent=None):
        super().__init__(parent)
        self.existing_path = existing_path
        self.incoming_path = incoming_path
        self.bridge = bridge
        self.result_action = "keep_both"
        self.apply_to_all = False
        
        self.setWindowTitle("File Conflict")
        self.setMinimumWidth(600)
        
        # Get theme colors
        accent_str = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT))
        accent_q = QColor(accent_str)
        is_light = Theme.get_is_light()
        
        bg_color = Theme.get_bg(accent_q)
        fg_color = Theme.get_text_color()
        muted_color = Theme.get_text_muted()
        border_color = Theme.get_border(accent_q)
        btn_bg = Theme.get_btn_save_bg(accent_q)
        btn_hover = Theme.get_btn_save_hover(accent_q)
        input_bg = Theme.get_input_bg(accent_q)
        selection_text = _selection_text_for_color(accent_q)
        
        # Physical SVG for checkbox (data URIs are unreliable in Qt QSS)
        check_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "scrollbar_arrows", "check.svg").replace("\\", "/")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {fg_color};
            }}
            QLabel {{
                color: {fg_color};
                font-size: 10pt;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {accent_str};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px;
                selection-background-color: {accent_str};
                selection-color: {selection_text};
            }}
            QLineEdit:focus {{
                border: 1px solid {accent_str};
            }}
            QCheckBox {{
                color: {muted_color};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                background-color: #fff;
                border: 1px solid {"#888" if is_light else border_color};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_str};
                image: url("{check_path}");
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Style refinements for light mode
        other_btn_style = ""
        replace_btn_style = f"background-color: {accent_str}; color: #fff; border: 1px solid {border_color};"
        other_hover_style = f"background-color: {Theme.mix(btn_bg, accent_q, 0.4)}; border: 1px solid {accent_str};"
        replace_hover_bg = Theme.mix("#ffffff", accent_q, 0.9)
        
        if is_light:
            darker_border = Theme.mix(border_color, QColor("#000000"), 0.4)
            other_btn_bg = Theme.get_control_bg(accent_q)
            replace_btn_bg = Theme.get_accent_soft(accent_q)
            other_btn_style = f"background-color: {other_btn_bg}; color: #000; border: 1px solid {darker_border};"
            replace_btn_style = f"background-color: {replace_btn_bg}; color: #000; border: 1px solid {darker_border};"
            
            # Hover styles stay restrained and only introduce a soft accent.
            other_hover_bg = Theme.mix(other_btn_bg, accent_q, 0.12)
            other_hover_style = f"background-color: {other_hover_bg}; border: 1px solid {accent_str};"
            
            replace_hover_bg = Theme.mix(replace_btn_bg, accent_q, 0.08)
            replace_hover_style = f"background-color: {replace_hover_bg}; color: #000; border: 1px solid {accent_str};"
        else:
            replace_hover_style = f"background-color: {replace_hover_bg}; border: 1px solid {accent_str};"
        
        header = QLabel("<h3>A file with this name already exists.</h3>")
        header.setStyleSheet("margin-bottom: 4px;")
        layout.addWidget(header)
        
        # Grid for side-by-side comparison
        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setRowStretch(2, 1) # Allow name label row to expand
        layout.addLayout(grid)
        
        def create_card(title_text, path, col):
            # Title
            title = QLabel(f"<b>{title_text}</b>")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(title, 0, col)
            
            # Thumbnail
            thumb = QLabel()
            thumb.setFixedSize(240, 180)
            thumb.setStyleSheet(f"background: #000; border: 2px solid {border_color}; border-radius: 8px;")
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_thumb(thumb, path)
            grid.addWidget(thumb, 1, col, Qt.AlignmentFlag.AlignCenter)
            
            # Name
            name_label = QLabel(path.name)
            name_label.setWordWrap(True)
            name_label.setFixedWidth(240)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Ensure it can grow vertically without clipping
            name_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
            name_label.setContentsMargins(0, 5, 0, 5)
            grid.addWidget(name_label, 2, col, Qt.AlignmentFlag.AlignCenter)
            
            # Stats (Size, Date)
            try:
                stat = path.stat()
                size_str = self._format_size(stat.st_size)
                date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
                stats = QLabel(f"<span style='color: {muted_color};'>{size_str} â€¢ {date_str}</span>")
                stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(stats, 3, col, Qt.AlignmentFlag.AlignCenter)
            except: pass
            
            # Rename components
            rename_btn = QPushButton("Rename Item")
            rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rename_input = QLineEdit(path.name)
            rename_input.hide()
            grid.addWidget(rename_btn, 4, col)
            grid.addWidget(rename_input, 4, col)
            
            if is_light:
                rename_btn.setStyleSheet(f"""
                    QPushButton {{ {other_btn_style} }}
                    QPushButton:hover {{ {other_hover_style} }}
                """)
            
            def show_rename():
                rename_btn.hide()
                rename_input.show()
                rename_input.setFocus()
            rename_btn.clicked.connect(show_rename)
            
            return rename_input

        self.existing_rename_input = create_card("Existing File", existing_path, 0)
        self.incoming_rename_input = create_card("Incoming File", incoming_path, 1)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        keep_both_btn = QPushButton("Keep Both")
        replace_btn = QPushButton("Replace")
        skip_btn = QPushButton("Skip")
        
        for b in (keep_both_btn, replace_btn, skip_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_light and b != replace_btn:
                b.setStyleSheet(f"QPushButton {{ {other_btn_style} }}")
        
        keep_both_btn.clicked.connect(lambda: self._finish("keep_both"))
        replace_btn.clicked.connect(lambda: self._finish("replace"))
        skip_btn.clicked.connect(lambda: self._finish("skip"))
        
        replace_btn.setStyleSheet(f"""
            QPushButton {{ 
                {replace_btn_style}
            }}
            QPushButton:hover {{ 
                {replace_hover_style}
            }}
        """)
        
        # Consistent style for other buttons in light mode
        if is_light:
            for b in (skip_btn, keep_both_btn):
                b.setStyleSheet(f"""
                    QPushButton {{ {other_btn_style} }}
                    QPushButton:hover {{ {other_hover_style} }}
                """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(skip_btn)
        btn_layout.addWidget(keep_both_btn)
        btn_layout.addWidget(replace_btn)
        layout.addLayout(btn_layout)
        
        # Apply to all
        self.apply_all_cb = QCheckBox("Apply to all remaining conflicts")
        self.apply_all_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.apply_all_cb)

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _set_thumb(self, label, path: Path):
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            img = _read_image_with_svg_support(path)
            
            # Fallback for AVIF or other formats Qt can't read natively
            if (img is None or img.isNull()) and ext == ".avif":
                poster = self.bridge._ensure_video_poster(path)
                if poster and poster.exists():
                    img = QImageReader(str(poster)).read()

            if img is not None and not img.isNull():
                pix = QPixmap.fromImage(img).scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pix)
            else:
                label.setText("Image Corrupt")
        else:
            # Try to get poster for video or AVIF that failed direct read
            poster = self.bridge._ensure_video_poster(path)
            if poster and poster.exists():
                img = QImageReader(str(poster)).read()
                if not img.isNull():
                    pix = QPixmap.fromImage(img).scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(pix)
                else:
                    label.setText("Thumb Fail")
            else:
                is_vid = path.suffix.lower() in VIDEO_EXTS
                label.setText("Video" if is_vid else "File")

    @property
    def new_existing_name(self):
        return self.existing_rename_input.text()

    @property
    def new_incoming_name(self):
        return self.incoming_rename_input.text()

    def _finish(self, action):
        self.result_action = action
        self.apply_to_all = self.apply_all_cb.isChecked()
        self.accept()




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
