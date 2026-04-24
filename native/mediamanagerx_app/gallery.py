from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *
from native.mediamanagerx_app.bridge import *

class NativeDragTooltip(QWidget):
    """A floating stack with preview image above tooltip text during drag operations."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("nativeDragTooltip")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.preview_label = QLabel(self)
        self.preview_label.setObjectName("nativeDragTooltipPreview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.hide()
        layout.addWidget(self.preview_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.text_label = QLabel(self)
        self.text_label.setObjectName("nativeDragTooltipText")
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.update_style(QColor(Theme.ACCENT_DEFAULT), Theme.get_is_light())

    def update_style(self, accent_color: QColor, is_light: bool):
        bg = Theme.get_control_bg(accent_color)
        fg = Theme.get_text_color()
        border = Theme.get_border(accent_color)
        
        self.setStyleSheet(f"""
            #nativeDragTooltipText {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }}
        """)

    def update_text(self, text: str):
        self.text_label.setText(text)
        self.adjustSize()

    def set_preview_pixmap(self, pixmap: QPixmap | None) -> None:
        if pixmap is None or pixmap.isNull():
            self.preview_label.clear()
            self.preview_label.hide()
        else:
            self.preview_label.setPixmap(pixmap)
            self.preview_label.show()
        self.adjustSize()

    def follow_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() + 10, pos.y() - (self.height() // 2))
        if not self.isVisible():
            self.show()


class NativeSeparator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(21)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(Theme.get_border(QColor(Theme.ACCENT_DEFAULT))))
        pen.setWidth(2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        y = self.height() // 2
        painter.drawLine(0, y, self.width(), y)


class StatusTextEdit(QPlainTextEdit):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.on_nonempty_text = None
        self.setPlainText(str(text or ""))
        self.setVisible(bool(str(text or "").strip()))
        self._copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self._copy_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._copy_shortcut.activated.connect(self.copy)
        self.copyAvailable.connect(self._focus_when_selection_available)

    def setText(self, text: str) -> None:
        clean = str(text or "")
        self.setPlainText(clean)
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.setPosition(0)
        self.setTextCursor(cursor)
        has_text = bool(clean.strip())
        self.setVisible(has_text)
        if has_text and callable(self.on_nonempty_text):
            QTimer.singleShot(0, self.on_nonempty_text)

    def text(self) -> str:
        return self.toPlainText()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

    def _focus_when_selection_available(self, available: bool) -> None:
        if available:
            self.setFocus(Qt.FocusReason.MouseFocusReason)


class ProgressStatusLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(str(text or ""), parent)
        self.setWordWrap(True)
        self.setVisible(bool(str(text or "").strip()))

    def setText(self, text: str) -> None:
        super().setText(str(text or ""))
        self.setVisible(bool(str(text or "").strip()))


class GalleryView(QWebEngineView):
    """Gallery view that accepts drag and drop from external file explorers."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def _probe_gallery_folder_target(self, x: int, y: int) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if not bridge:
            return

        script = (
            "(() => {"
            f"  const el = document.elementFromPoint({int(x)}, {int(y)});"
            "  const card = el && el.closest ? el.closest('.folder-card[data-path]') : null;"
            "  return card ? card.getAttribute('data-path') : '';"
            "})()"
        )

        def _apply_target(target_path: str) -> None:
            try:
                bridge.drag_target_folder = str(target_path or "")
                bridge.dragOverFolder.emit(Path(target_path).name if target_path else "")
            except Exception:
                pass

        try:
            self.page().runJavaScript(script, _apply_target)
        except Exception:
            try:
                bridge.drag_target_folder = ""
                bridge.dragOverFolder.emit("")
            except Exception:
                pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent):
        # Determine target folder
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        
        is_file_drag = False
        if bridge and bridge.drag_paths:
            is_file_drag = True
        elif event.mimeData().hasUrls():
            is_file_drag = True
            
        if is_file_drag and bridge:
            try:
                pos = event.position()
                x, y = int(pos.x()), int(pos.y())
            except Exception:
                pos = event.pos()
                x, y = int(pos.x()), int(pos.y())
            self._probe_gallery_folder_target(x, y)
            target_folder = bridge.drag_target_folder or ""
            
            # Count items: side-channel first (internal), then MIME (external)
            count = len(bridge.drag_paths) if bridge.drag_paths else len(event.mimeData().urls())
            if count == 0: count = 1
            
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            
            # Target folder name for display
            target_name = Path(target_folder).name if target_folder else ""
            
            bridge.update_drag_tooltip(count, is_copy, target_name)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.drag_target_folder = ""
            bridge.dragOverFolder.emit("")
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
            
            mime = event.mimeData()
            src_paths = []
            
            # Priority 0: Side-channel from Bridge (Internal Gallery -> Gallery)
            if bridge and bridge.drag_paths:
                src_paths = list(bridge.drag_paths)
            
            # Priority 1: Fallback to MIME data (External drops)
            if not src_paths and mime.hasUrls():
                src_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]
            
            if src_paths:
                if bridge.drag_paths:
                    target_path = bridge.drag_target_folder
                else:
                    target_path = ""
                if not target_path and not bridge.drag_paths:
                    selected = bridge.get_selected_folders()
                    target_path = selected[0] if selected else ""
                
                if target_path:
                    target_path_norm = target_path.replace("\\", "/").lower()

                    # Internal gallery drags dropped back onto the gallery background
                    # should be treated as a cancelled drag, not as a move/copy into
                    # the currently loaded folder.
                    if bridge.drag_paths:
                        if not bridge.drag_target_folder:
                            event.ignore()
                            return

                    # Filter out if moving to THE SAME folder
                    src_paths = [p for p in src_paths if os.path.dirname(p).replace("\\", "/").lower() != target_path_norm]
                    
                    if src_paths:
                        # Determine if COPY or MOVE
                        is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                        op_type = "copy" if is_copy else "move"
                        
                        paths_obj = [Path(p) for p in src_paths]
                        bridge._process_file_op(op_type, paths_obj, Path(target_path))
                        bridge.drag_target_folder = ""
                        bridge.dragOverFolder.emit("")
                        event.acceptProposedAction()
                        return
                if bridge.drag_paths:
                    bridge.drag_target_folder = ""
                    bridge.dragOverFolder.emit("")
                    event.ignore()
                    return
        
        super().dropEvent(event)


class GalleryWebPage(QWebEnginePage):
    """Logs WebEngine console and renderer failures into the app log."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id) -> None:
        view = self.parent()
        main_win = view.window() if view else None
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            try:
                level_name = getattr(level, "name", str(level))
                if "Info" in level_name and not getattr(bridge, "_verbose_logs", False):
                    return
                bridge._log(
                    "Web console: "
                    f"level={level_name} source={source_id or '<inline>'} "
                    f"line={int(line_number)} message={message}"
                )
            except Exception:
                pass
        super().javaScriptConsoleMessage(level, message, line_number, source_id)




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
