from __future__ import annotations

import weakref

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *

class CustomSplitterHandle(QSplitterHandle):
    """Custom handle that paints itself to ensure hover colors work on all platforms."""
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._last_global_pos: QPoint | None = None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        accent_str = str(self.parent().window().bridge.settings.value("ui/accent_color", "#8ab4f8"))
        accent = QColor(accent_str)
        track = QColor(Theme.get_bg(accent))
        idle = QColor(Theme.get_splitter_idle(accent))
        color = accent if self.underMouse() else idle

        painter.fillRect(self.rect(), track)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        mid_x = self.rect().center().x()
        mid_y = self.rect().center().y()
        if self.orientation() == Qt.Orientation.Horizontal:
            painter.drawLine(mid_x, self.rect().top(), mid_x, self.rect().bottom())
        else:
            painter.drawLine(self.rect().left(), mid_y, self.rect().right(), mid_y)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_global_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        prev_global = self._last_global_pos
        super().mouseMoveEvent(event)
        current_global = event.globalPosition().toPoint()
        if prev_global is not None:
            delta = current_global - prev_global
            try:
                parent_splitter = self.parent()
                window = parent_splitter.window() if parent_splitter is not None else None
                if (
                    isinstance(parent_splitter, QSplitter)
                    and parent_splitter.objectName() == "rightSplitter"
                    and window is not None
                    and hasattr(window, "_handle_right_splitter_overflow_drag")
                ):
                    window._handle_right_splitter_overflow_drag(int(delta.x()))
            except Exception:
                pass
        self._last_global_pos = current_global

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_global_pos = None
        super().mouseReleaseEvent(event)


class CustomSplitter(QSplitter):
    """Splitter that uses CustomSplitterHandle."""
    def createHandle(self) -> QSplitterHandle:
        return CustomSplitterHandle(self.orientation(), self)


class FolderTreeView(QTreeView):
    """Tree view that does NOT change selection on right-click.

    Windows Explorer behavior: right-click opens context menu without changing
    the active selection (unless explicitly choosing/selecting).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            idx = self.indexAt(event.position().toPoint())
            if idx.isValid() and not self.selectionModel().isSelected(idx):
                # Only if not already selected, we might want to select just this one?
                # Explorer actually selects on right-click if nothing is selected.
                pass
            # Don't call super() if we want to block the default selection behavior
            # BUT we need it for the context menu to know WHERE we clicked.
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        if idx.isValid():
            source_idx = self.model().mapToSource(idx)
            fs_model = self.model().sourceModel()
            if fs_model.isDir(source_idx):
                target_folder = fs_model.filePath(source_idx)
                
                # Check modifier keys for Copy vs Move
                is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                
                # Update tooltip via bridge
                main_win = self.window()
                bridge = getattr(main_win, "bridge", None)
                if bridge:
                    # Count items from side-channel or mime
                    count = len(bridge.drag_paths) if bridge.drag_paths else 1
                    bridge.update_drag_tooltip(count, is_copy, Path(target_folder).name)
                
                self.setExpanded(idx, True)
                event.setDropAction(Qt.DropAction.CopyAction if is_copy else Qt.DropAction.MoveAction)
                event.accept()
                return
        
        # If not over a folder, hide tooltip target
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            count = len(bridge.drag_paths) if bridge.drag_paths else 1
            is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            bridge.update_drag_tooltip(count, is_copy, "")
            
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        main_win = self.window()
        bridge = getattr(main_win, "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        mime = event.mimeData()
        idx = self.indexAt(event.position().toPoint())
        
        # Determine target folder
        target_path = ""
        if idx.isValid():
            # Handle proxy model mapping
            model = self.model()
            if isinstance(model, QSortFilterProxyModel):
                source_idx = model.mapToSource(idx)
                fs_model = model.sourceModel()
                if isinstance(fs_model, QFileSystemModel):
                    if fs_model.isDir(source_idx):
                        target_path = fs_model.filePath(source_idx)
                    else:
                        target_path = fs_model.filePath(source_idx.parent())
            elif isinstance(model, QFileSystemModel):
                if model.isDir(idx):
                    target_path = model.filePath(idx)
                else:
                    target_path = model.filePath(idx.parent())

        if not target_path:
            event.ignore()
            return

        # Gather source paths
        src_paths = []
        
        # Priority 0: Side-channel from Bridge (Reliable for internal Gallery -> Tree)
        if bridge and hasattr(bridge, "drag_paths") and bridge.drag_paths:
            src_paths = list(bridge.drag_paths)
        
        # Priority 1: fallback to MIME data for tree-to-tree or external drops
        if not src_paths:
            if mime.hasUrls():
                src_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]

        if not src_paths:
            event.ignore()
            return

        # Filter out if moving to THE SAME folder
        src_paths = [p for p in src_paths if os.path.dirname(p).replace("\\", "/").lower() != target_path.replace("\\", "/").lower()]

        if not src_paths:
            event.ignore()
            return

        # Determine if COPY or MOVE
        is_copy = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        op_type = "copy" if is_copy else "move"
        
        if bridge:
            # Perform operation
            paths_obj = [Path(p) for p in src_paths]
            bridge._process_file_op(op_type, paths_obj, Path(target_path))
            event.acceptProposedAction()
        else:
            event.ignore()


class CollectionListWidget(QListWidget):
    """Flat collection list with right-click context menu and gallery drop support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if self.viewport() is not None:
            self.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        self.setCursor(Qt.CursorShape.PointingHandCursor if item else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or bool(getattr(self.window().bridge, "drag_paths", [])):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        item = self.itemAt(event.position().toPoint())
        if item and bridge:
            count = len(bridge.drag_paths) if bridge.drag_paths else max(1, len(event.mimeData().urls()))
            bridge.update_drag_tooltip(count, True, item.text())
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        if bridge:
            bridge.update_drag_tooltip(len(bridge.drag_paths) or 1, True, "")
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        item = self.itemAt(event.position().toPoint())
        if not item or not bridge:
            event.ignore()
            return

        src_paths = list(bridge.drag_paths) if bridge.drag_paths else []
        if not src_paths and event.mimeData().hasUrls():
            src_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        if not src_paths:
            event.ignore()
            return

        collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if collection_id <= 0:
            event.ignore()
            return

        if bridge.add_paths_to_collection(collection_id, src_paths) > 0:
            event.acceptProposedAction()
            return
        event.ignore()


class PinnedFolderListWidget(QListWidget):
    """Flat pinned-folder list with drag-and-drop support for folders only."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        self.setCursor(Qt.CursorShape.PointingHandCursor if item else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    @staticmethod
    def _extract_folder_paths(mime: QMimeData, bridge: "Bridge | None") -> list[str]:
        raw_paths: list[str] = []
        if bridge and bridge.drag_paths:
            raw_paths = list(bridge.drag_paths)
        elif mime.hasUrls():
            raw_paths = [url.toLocalFile() for url in mime.urls() if url.toLocalFile()]

        folders: list[str] = []
        seen: set[str] = set()
        for raw_path in raw_paths:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                p = Path(path_str)
                if not p.exists() or not p.is_dir():
                    continue
                normalized = str(p.absolute())
            except Exception:
                continue
            key = normalized.replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            folders.append(normalized)
        return folders

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if folders:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if folders:
            if bridge:
                bridge.update_drag_tooltip(len(folders), True, "Pinned Folders")
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        bridge = getattr(self.window(), "bridge", None)
        if bridge:
            bridge.hide_drag_tooltip()

        folders = self._extract_folder_paths(event.mimeData(), bridge)
        if not folders or not bridge:
            event.ignore()
            return

        if bridge.pin_folders(folders) > 0:
            event.acceptProposedAction()
            return
        event.ignore()


class ContextClickableLabel(QLabel):
    rightClicked = Signal()

    def contextMenuEvent(self, event) -> None:
        self.rightClicked.emit()
        event.accept()


class TagListRowsWidget(QListWidget):
    orderChanged = Signal()
    backgroundClicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setMouseTracking(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_user_sort_enabled(self, enabled: bool) -> None:
        self.setDragEnabled(bool(enabled))
        self.setAcceptDrops(bool(enabled))
        self.setDropIndicatorShown(bool(enabled))
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if enabled else
            QAbstractItemView.DragDropMode.NoDragDrop
        )

    def begin_drag_for_item(self, item: QListWidgetItem | None) -> None:
        if item is None or self.dragDropMode() != QAbstractItemView.DragDropMode.InternalMove:
            return
        self.setCurrentItem(item)
        self.startDrag(Qt.DropAction.MoveAction)

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        row = self.itemWidget(item) if item is not None else None
        if item is None or row is None:
            super().startDrag(supportedActions)
            return

        drag = QDrag(self)
        mime = self.mimeData(self.selectedItems())
        if mime is None:
            super().startDrag(supportedActions)
            return
        drag.setMimeData(mime)
        item_rect = self.visualItemRect(item)
        pixmap = row.create_drag_pixmap(item_rect) if isinstance(row, TagListTagRow) else row.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            if isinstance(row, TagListTagRow):
                drag.setHotSpot(row.drag_hotspot(item_rect))
            else:
                drag.setHotSpot(QPoint(max(0, pixmap.width() // 2), max(0, pixmap.height() // 2)))
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event: QDropEvent) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is None and event.button() == Qt.MouseButton.LeftButton:
            self.clearSelection()
            self.backgroundClicked.emit()
        super().mousePressEvent(event)


class TagListTagRow(QWidget):
    addToSelectionRequested = Signal(str)
    removeFromSelectionRequested = Signal(str)
    removeFromListRequested = Signal(int, str)
    filterRequested = Signal(str)

    def __init__(self, parent_list: TagListRowsWidget, item: QListWidgetItem, entry: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._parent_list = parent_list
        self._item = item
        self._press_pos: QPoint | None = None
        self._drag_started = False
        self._tag_id = int(entry.get("tag_id") or 0)
        self._tag_name = str(entry.get("name") or "")
        self._scope_use_count = int(entry.get("scope_use_count") or 0)
        self._global_use_count = int(entry.get("global_use_count") or 0)
        self._selection_state = str(entry.get("selection_state") or ("selected" if entry.get("in_selected_tags") else "none"))
        self._filter_active = bool(entry.get("filter_active"))
        self._can_remove_from_selection = False
        self._drag_bg_color = QColor("#dbeafe")
        self._drag_border_color = QColor("#8ab4f8")
        self._drag_text_color = QColor("#111111")
        self.setObjectName("tagListTagRow")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        self.remove_from_list_btn = QPushButton("")
        self.remove_from_list_btn.setObjectName("tagListRemoveFromListButton")
        self.remove_from_list_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_from_list_btn.setFixedSize(30, 28)
        self.remove_from_list_btn.setToolTip("Delete tag from list")
        self.remove_from_list_btn.clicked.connect(lambda: self.removeFromListRequested.emit(self._tag_id, self._tag_name))
        layout.addWidget(self.remove_from_list_btn, 0)

        self.scope_btn = QPushButton(str(self._scope_use_count))
        self.scope_btn.setObjectName("tagListScopeCountButton")
        self.scope_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scope_btn.setFixedHeight(24)
        self.scope_btn.setMinimumWidth(28)
        self.scope_btn.clicked.connect(lambda: self.filterRequested.emit(self._tag_name))
        self.scope_btn.setToolTip(f"The tag {self._tag_name} was found in {self._scope_use_count} files within the current scope")
        layout.addWidget(self.scope_btn, 0)

        self.name_lbl = QLabel(self._tag_name)
        self.name_lbl.setObjectName("tagListTagName")
        self.name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.name_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.name_lbl.setAutoFillBackground(False)
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.name_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.name_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_lbl.setToolTip(f"Click to filter gallery using Tag: {self._tag_name}")
        self.name_lbl.customContextMenuRequested.connect(lambda _pos: self.filterRequested.emit(self._tag_name))
        layout.addWidget(self.name_lbl, 1)

        self.remove_from_selection_btn = QPushButton("X")
        self.remove_from_selection_btn.setObjectName("tagListRemoveFromSelectionButton")
        self.remove_from_selection_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_from_selection_btn.setFixedSize(26, 24)
        self.remove_from_selection_btn.setToolTip("Remove this tag from the selected file's Tags field")
        self.remove_from_selection_btn.clicked.connect(self._on_remove_from_selection_clicked)
        layout.addWidget(self.remove_from_selection_btn, 0)

        self.add_btn = QPushButton("â†’")
        self.add_btn.setObjectName("tagListAddButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setFixedSize(26, 24)
        self.add_btn.setToolTip("Add tag to selected file(s)")
        self.add_btn.clicked.connect(lambda: self.addToSelectionRequested.emit(self._tag_name))
        layout.addWidget(self.add_btn, 0)

    @property
    def tag_id(self) -> int:
        return self._tag_id

    @property
    def tag_name(self) -> str:
        return self._tag_name

    def update_entry(self, entry: dict) -> None:
        next_scope_use_count = int(entry.get("scope_use_count") or 0)
        next_global_use_count = int(entry.get("global_use_count") or 0)
        next_selection_state = str(entry.get("selection_state") or ("selected" if entry.get("in_selected_tags") else "none"))
        next_filter_active = bool(entry.get("filter_active"))
        changed = (
            next_scope_use_count != self._scope_use_count
            or next_global_use_count != self._global_use_count
            or next_selection_state != self._selection_state
            or next_filter_active != self._filter_active
        )
        self._scope_use_count = next_scope_use_count
        self._global_use_count = next_global_use_count
        self._selection_state = next_selection_state
        self._filter_active = next_filter_active
        self.scope_btn.setText(str(self._scope_use_count))
        self.scope_btn.setToolTip(f"The tag {self._tag_name} was found in {self._scope_use_count} files within the current scope")
        self.name_lbl.setToolTip(f"Click to filter gallery using Tag: {self._tag_name}")
        return changed

    def _on_remove_from_selection_clicked(self) -> None:
        if not self._can_remove_from_selection:
            return
        self.removeFromSelectionRequested.emit(self._tag_name)

    def apply_theme(self, *, accent_color: str, accent_text: str, accent_text_muted: str, text: str, text_muted: str, btn_bg: str, btn_hover: str, btn_border: str, btn_border_hover: str, is_light: bool) -> None:
        trash_svg_name = "trashcan.svg" if is_light else "trashcan-white.svg"
        trash_svg = (Path(__file__).with_name("web") / "icons" / trash_svg_name).as_posix()
        trash_red_svg = (Path(__file__).with_name("web") / "icons" / "trashcan-red.svg").as_posix()
        trash_disabled_svg = (Path(__file__).with_name("web") / "icons" / "trashcan-gray.svg").as_posix()
        self._drag_bg_color = QColor(Theme.get_accent_soft(QColor(accent_color)))
        self._drag_border_color = QColor(accent_color)
        is_selected = self._selection_state in {"selected", "common"}
        is_uncommon = self._selection_state == "uncommon"
        row_filter_active = self._filter_active
        row_text = accent_text if is_selected else (accent_text_muted if is_uncommon else text)
        row_weight = "700" if is_selected else ("600" if is_uncommon else "400")
        self._drag_text_color = QColor(row_text)
        row_bg = btn_bg if row_filter_active else "transparent"
        row_border = accent_color if row_filter_active else "transparent"

        self.setStyleSheet(
            f"""
            QWidget#tagListTagRow {{
                background-color: {row_bg};
                border: 1px solid {row_border};
                border-radius: 8px;
            }}
            """
        )

        name_palette = self.name_lbl.palette()
        name_palette.setColor(QPalette.ColorRole.WindowText, QColor(row_text))
        name_palette.setColor(QPalette.ColorRole.Text, QColor(row_text))
        name_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        name_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        self.name_lbl.setPalette(name_palette)
        name_font = QFont(self.name_lbl.font())
        if str(row_weight) == "700":
            name_font.setWeight(QFont.Weight.Bold)
        elif str(row_weight) == "600":
            name_font.setWeight(QFont.Weight.DemiBold)
        else:
            name_font.setWeight(QFont.Weight.Normal)
        self.name_lbl.setFont(name_font)
        scope_text = accent_text if row_filter_active else text
        button_qss = (
            f"QPushButton {{ background-color: {btn_bg}; color: {text}; border: 1px solid {btn_border}; border-radius: 6px; padding: 2px 6px; }}"
            f"QPushButton:hover {{ background-color: {btn_hover}; border-color: {btn_border_hover}; }}"
        )
        self.scope_btn.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {scope_text}; border: 1px solid {btn_border}; border-radius: 6px; padding: 2px 6px; }}"
            f"QPushButton:hover {{ background-color: {btn_hover}; border-color: {accent_color}; }}"
        )
        self.add_btn.setStyleSheet(
            f"""
            QPushButton#tagListAddButton {{
                background-color: {btn_bg};
                color: {text};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 0px;
                font-weight: 700;
            }}
            QPushButton#tagListAddButton:hover {{
                background-color: {btn_hover};
                color: {'#000000' if is_light else '#ffffff'};
                border-color: {accent_color};
                font-weight: 800;
            }}
            """
        )

        self.remove_from_list_btn.setEnabled(True)
        self.remove_from_list_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_from_list_btn.setToolTip("Delete tag from list")
        self.remove_from_list_btn.setStyleSheet(
            f"""
            QPushButton#tagListRemoveFromListButton {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 6px;
                image: url('{trash_svg}');
            }}
            QPushButton#tagListRemoveFromListButton:hover {{
                background-color: {btn_bg};
                border-color: #d45a5a;
                padding: 6px;
                image: url('{trash_red_svg}');
            }}
            """
        )

        can_remove_from_selection = self._selection_state in {"selected", "common", "uncommon"}
        self._can_remove_from_selection = bool(can_remove_from_selection)
        self.remove_from_selection_btn.setEnabled(True)
        self.remove_from_selection_btn.setCursor(
            Qt.CursorShape.PointingHandCursor if can_remove_from_selection else Qt.CursorShape.ForbiddenCursor
        )
        self.remove_from_selection_btn.setToolTip(
            "Remove this tag from the selected file's Tags field"
            if can_remove_from_selection else
            "This tag isn't in the file(s) selected"
        )
        self.remove_from_selection_btn.setStyleSheet(
            f"""
            QPushButton#tagListRemoveFromSelectionButton {{
                background-color: {btn_bg};
                color: {'#ffffff' if can_remove_from_selection else text_muted};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 0px;
                font-weight: 700;
            }}
            QPushButton#tagListRemoveFromSelectionButton:hover {{
                background-color: {btn_bg};
                color: #d45a5a;
                border-color: #d45a5a;
            }}
            QPushButton#tagListRemoveFromSelectionButton[removeEnabled="false"] {{
                background-color: {btn_bg};
                color: {text_muted};
                border-color: {btn_border};
            }}
            """
        )
        self.remove_from_selection_btn.setProperty("removeEnabled", "true" if can_remove_from_selection else "false")
        self.remove_from_selection_btn.style().unpolish(self.remove_from_selection_btn)
        self.remove_from_selection_btn.style().polish(self.remove_from_selection_btn)

    def create_drag_pixmap(self, item_rect: QRect | None = None) -> QPixmap:
        text = self._tag_name
        resolved_rect = item_rect if item_rect is not None and item_rect.isValid() else QRect(QPoint(0, 0), self.size())
        width = max(120, int(resolved_rect.width() or 0))
        height = max(32, int(resolved_rect.height() or 0))
        dpr = max(1.0, float(self.devicePixelRatioF() or 1.0))
        pixmap = QPixmap(int(width * dpr), int(height * dpr))
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(dpr)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setPen(QPen(self._drag_border_color, 1))
        painter.setBrush(self._drag_bg_color)
        logical_rect = QRectF(0.5, 0.5, width - 1.0, height - 1.0)
        painter.drawRoundedRect(logical_rect, 8, 8)
        painter.setPen(self._drag_text_color)
        painter.setFont(self.name_lbl.font())
        viewport = self._parent_list.viewport()
        name_top_left = self.name_lbl.mapTo(viewport, QPoint(0, 0))
        item_top_left = resolved_rect.topLeft()
        name_left = max(10, int(name_top_left.x() - item_top_left.x()))
        text_rect = QRect(
            name_left,
            0,
            max(20, int(width - name_left - 10)),
            height,
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.end()
        return pixmap

    def drag_hotspot(self, item_rect: QRect | None = None) -> QPoint:
        resolved_rect = item_rect if item_rect is not None and item_rect.isValid() else QRect(QPoint(0, 0), self.size())
        fallback = QPoint(max(0, int(resolved_rect.width() * 0.5)), max(0, int(resolved_rect.height() * 0.5)))
        if self._press_pos is None:
            return fallback
        viewport = self._parent_list.viewport()
        row_top_left = self.mapTo(viewport, QPoint(0, 0))
        item_top_left = resolved_rect.topLeft()
        offset = row_top_left - item_top_left
        return QPoint(
            max(0, min(int(resolved_rect.width()) - 1, int(offset.x() + self._press_pos.x()))),
            max(0, min(int(resolved_rect.height()) - 1, int(offset.y() + self._press_pos.y()))),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._drag_started = False
            self._parent_list.setCurrentItem(self._item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._press_pos is not None
            and (event.position().toPoint() - self._press_pos).manhattanLength() >= QApplication.startDragDistance()
        ):
            self._drag_started = True
            self._parent_list.begin_drag_for_item(self._item)
            self._press_pos = None
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._drag_started:
            child = self.childAt(event.position().toPoint())
            if child not in {
                self.scope_btn,
                self.add_btn,
                self.remove_from_selection_btn,
                self.remove_from_list_btn,
            }:
                self.filterRequested.emit(self._tag_name)
                event.accept()
                self._press_pos = None
                return
        self._press_pos = None
        self._drag_started = False
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.filterRequested.emit(self._tag_name)
        event.accept()


class BulkSelectedFileRow(QWidget):
    tagsEdited = Signal(str, str)
    generateRequested = Signal(str)
    _TAG_CONTENT_HEIGHT = 92
    _CAPTION_CONTENT_HEIGHT = 132
    _GENERATE_BUTTON_HEIGHT = 28
    _RIGHT_GUTTER = 5
    _MIN_EDITOR_WIDTH = 140

    class _TagsEdit(QPlainTextEdit):
        editingFinished = Signal()

        def focusOutEvent(self, event) -> None:
            self.editingFinished.emit()
            super().focusOutEvent(event)

    def __init__(
        self,
        path: str,
        thumbnail: QPixmap | None,
        name: str,
        tags_text: str,
        parent: QWidget | None = None,
        *,
        content_height: int | None = None,
        placeholder_text: str = "Tags for this file",
        thumbnail_bg_hint: str = "",
        generate_button_text: str = "",
    ) -> None:
        super().__init__(parent)
        self._path = str(path or "")
        self._content_height = max(72, int(content_height or self._TAG_CONTENT_HEIGHT))
        self.setObjectName("bulkSelectedFileRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._shared_width_managed = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 12)
        layout.setSpacing(4)
        self._root_layout = layout

        self.name_lbl = QLabel(str(name or ""))
        self.name_lbl.setObjectName("bulkSelectedFileName")
        self.name_lbl.setWordWrap(False)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.name_lbl.setTextFormat(Qt.TextFormat.PlainText)
        name_font = QFont(self.name_lbl.font())
        name_font.setBold(True)
        self.name_lbl.setFont(name_font)
        layout.addWidget(self.name_lbl)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 6, 0)
        content_row.setSpacing(12)
        self._content_row = content_row

        self.thumb_lbl = QLabel()
        self.thumb_lbl.setObjectName("bulkSelectedFileThumb")
        self.thumb_lbl.setFixedSize(self._content_height, self._content_height)
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_hint = str(thumbnail_bg_hint or "").strip().lower()
        if thumb_hint == "light":
            thumb_bg = "#ffffff" if Theme.get_is_light() else "#f7f8fa"
        elif thumb_hint == "dark":
            thumb_bg = "#101114"
        else:
            thumb_bg = "transparent"
        self.thumb_lbl.setStyleSheet(
            f"QLabel#bulkSelectedFileThumb {{ background-color: {thumb_bg}; border-radius: 6px; }}"
        )
        if thumbnail is not None and not thumbnail.isNull():
            self.thumb_lbl.setPixmap(thumbnail)
            self._thumbnail_loaded = True
        else:
            self.thumb_lbl.setText("â€¢")
        if not hasattr(self, "_thumbnail_loaded"):
            self._thumbnail_loaded = False
        content_row.addWidget(self.thumb_lbl, 0, Qt.AlignmentFlag.AlignTop)

        self.tags_edit = self._TagsEdit()
        self.tags_edit.setObjectName("bulkSelectedFileTagsEdit")
        self.tags_edit.setPlaceholderText(str(placeholder_text or ""))
        self.tags_edit.setDocumentTitle("bulk-selected-file-tags")
        self.tags_edit.document().setDocumentMargin(6)
        self.tags_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tags_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.tags_edit.setPlainText(str(tags_text or ""))
        self.tags_edit.setFixedHeight(self._content_height)
        self.tags_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.tags_edit.editingFinished.connect(self._emit_tags_edited)

        self.tags_edit_host = QWidget()
        self.tags_edit_host.setObjectName("bulkSelectedFileTagsHost")
        self.tags_edit_host.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        tags_host_layout = QVBoxLayout(self.tags_edit_host)
        tags_host_layout.setContentsMargins(0, 0, 0, 0)
        tags_host_layout.setSpacing(5)
        tags_host_layout.addWidget(self.tags_edit)
        self.generate_btn = QPushButton(str(generate_button_text or ""))
        self.generate_btn.setObjectName("bulkSelectedFileGenerateButton")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setFixedHeight(self._GENERATE_BUTTON_HEIGHT)
        self.generate_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.generate_btn.setVisible(bool(str(generate_button_text or "").strip()))
        self.generate_btn.clicked.connect(self._emit_generate_requested)
        tags_host_layout.addWidget(self.generate_btn)
        self._tags_host_layout = tags_host_layout
        content_row.addWidget(self.tags_edit_host, 1)
        content_row.addSpacing(4)

        layout.addLayout(content_row, 1)
        self._queue_sync_editor_width()

    def _emit_tags_edited(self) -> None:
        try:
            self.tagsEdited.emit(self._path, self.tags_edit.toPlainText())
        except RuntimeError:
            pass

    def _emit_generate_requested(self) -> None:
        try:
            self.generateRequested.emit(self._path)
        except RuntimeError:
            pass

    def set_generate_enabled(self, enabled: bool) -> None:
        try:
            if self.generate_btn.isVisible():
                self.generate_btn.setEnabled(bool(enabled))
        except RuntimeError:
            pass

    def set_thumbnail(self, thumbnail: QPixmap | None, thumbnail_bg_hint: str = "") -> None:
        try:
            thumb_hint = str(thumbnail_bg_hint or "").strip().lower()
            if thumb_hint == "light":
                thumb_bg = "#ffffff" if Theme.get_is_light() else "#f7f8fa"
            elif thumb_hint == "dark":
                thumb_bg = "#101114"
            else:
                thumb_bg = "transparent"
            self.thumb_lbl.setStyleSheet(
                f"QLabel#bulkSelectedFileThumb {{ background-color: {thumb_bg}; border-radius: 6px; }}"
            )
            if thumbnail is not None and not thumbnail.isNull():
                self.thumb_lbl.setText("")
                self.thumb_lbl.setPixmap(thumbnail)
            self._thumbnail_loaded = True
        except RuntimeError:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._queue_sync_editor_width()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._queue_sync_editor_width()

    def event(self, event) -> bool:
        result = super().event(event)
        if event.type() in {QEvent.Type.LayoutRequest, QEvent.Type.Polish, QEvent.Type.PolishRequest}:
            self._queue_sync_editor_width()
        return result

    def _queue_sync_editor_width(self) -> None:
        row_ref = weakref.ref(self)

        def _sync_if_alive() -> None:
            row = row_ref()
            if row is None:
                return
            try:
                import shiboken6

                if not shiboken6.isValid(row):
                    return
            except Exception:
                pass
            try:
                row._sync_editor_width()
            except RuntimeError:
                pass

        QTimer.singleShot(0, _sync_if_alive)

    def set_shared_editor_widths(self, host_width: int) -> None:
        self._shared_width_managed = True
        clamped_width = max(self._MIN_EDITOR_WIDTH, int(host_width or 0))
        self.tags_edit_host.setFixedWidth(clamped_width)
        self.tags_edit.setFixedWidth(clamped_width)
        if hasattr(self, "generate_btn"):
            self.generate_btn.setFixedWidth(clamped_width)

    def _sync_editor_width(self) -> None:
        try:
            import shiboken6

            if not shiboken6.isValid(self):
                return
        except Exception:
            pass
        try:
            if self._shared_width_managed:
                return
            if (
                not hasattr(self, "tags_edit_host")
                or not hasattr(self, "thumb_lbl")
                or not hasattr(self, "_root_layout")
                or not hasattr(self, "_content_row")
                or not hasattr(self, "_tags_host_layout")
            ):
                return
            total_width = max(0, self.width())
            if total_width <= 0:
                return
            root_margins = self._root_layout.contentsMargins()
            row_margins = self._content_row.contentsMargins()
            thumb_width = self.thumb_lbl.width()
            spacing = self._content_row.spacing()
            host_width = max(
                self._MIN_EDITOR_WIDTH,
                total_width
                - root_margins.left()
                - root_margins.right()
                - row_margins.left()
                - row_margins.right()
                - thumb_width
                - spacing
                - self._RIGHT_GUTTER,
            )
            self.tags_edit_host.setFixedWidth(host_width)
            self.tags_edit.setFixedWidth(host_width)
            if hasattr(self, "generate_btn"):
                self.generate_btn.setFixedWidth(host_width)
        except RuntimeError:
            pass

    def item_height(self) -> int:
        extra = self._GENERATE_BUTTON_HEIGHT + 8 if getattr(self, "generate_btn", None) is not None and self.generate_btn.isVisible() else 0
        return int(self._content_height) + 60 + extra


class BulkSelectedFilesListWidget(QListWidget):
    layoutSyncRequested = Signal()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.layoutSyncRequested.emit()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.layoutSyncRequested.emit()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self.layoutSyncRequested.emit()

    def viewportEvent(self, event) -> bool:
        result = super().viewportEvent(event)
        if event.type() in {QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest}:
            self.layoutSyncRequested.emit()
        return result


class RootFilterProxyModel(QSortFilterProxyModel):
    """Filters a QFileSystemModel to only show a specific root folder and its children.
    
    Siblings of the root folder are hidden.
    """
    def __init__(self, bridge: Bridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self._root_path = ""
        self._fallback_icon: QIcon | None = None

    def setRootPath(self, path: str) -> None:
        self._root_path = str(Path(path).absolute()).replace("\\", "/").lower()
        self.invalidateFilter()

    def _has_visible_child_dirs(self, raw_path: str) -> bool:
        path_str = str(raw_path or "").strip()
        if not path_str:
            return False
        try:
            root = Path(path_str)
            if not root.exists() or not root.is_dir():
                return False
            show_hidden = self.bridge._show_hidden_enabled()
            for child in root.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    if not show_hidden and self.bridge.repo.is_path_hidden(str(child)):
                        continue
                    return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._root_path:
            return True
            
        fs_model = self.sourceModel()
        source_index = fs_model.index(source_row, 0, source_parent)
        raw_path = fs_model.filePath(source_index)
        
        # Consistent normalization for all path checks
        from app.mediamanager.utils.pathing import normalize_windows_path
        normalized_path = normalize_windows_path(raw_path)
        
        # Hidden logic: if show_hidden is False, skip database-marked hidden paths
        # This check must come before the root path inclusion logic.
        if not self.bridge._show_hidden_enabled():
            try:
                if self.bridge.repo.is_path_hidden(raw_path):
                    return False
            except Exception as exc:
                try:
                    self.bridge._log(f"Tree hidden-path filter skipped for {raw_path}: {exc}")
                except Exception:
                    pass

        root = normalize_windows_path(self._root_path).rstrip("/")
        norm_path = normalized_path.rstrip("/")

        # Show the root path itself
        if norm_path == root:
            return True
            
        # Show children/descendants of the root path
        if normalized_path.startswith(root + "/"):
            return True
            
        # Show ancestors of the root path (so we can reach it from the top)
        if (root + "/").startswith(norm_path + "/"):
            return True
            
        # Special case: show Windows drives if they are ancestors
        if len(norm_path) == 2 and norm_path[1] == ":" and root.startswith(norm_path):
            return True

        return False

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        if not parent.isValid():
            return super().hasChildren(parent)

        source_model = self.sourceModel()
        if not isinstance(source_model, QFileSystemModel):
            return super().hasChildren(parent)

        source_index = self.mapToSource(parent)
        if not source_index.isValid() or not source_model.isDir(source_index):
            return False

        raw_path = source_model.filePath(source_index)
        return self._has_visible_child_dirs(raw_path)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        source_idx = self.mapToSource(index)
        source_model = self.sourceModel()
        is_directory = isinstance(source_model, QFileSystemModel) and source_model.isDir(source_idx)

        # Prevent "customized" folder icons (which sometimes fail to load or are empty)
        # by forcing the standard folder icon for all directories.
        if role == Qt.ItemDataRole.DecorationRole and is_directory:
            if not self._fallback_icon:
                provider = QFileIconProvider()
                self._fallback_icon = provider.icon(QFileIconProvider.IconType.Folder)
            return self._fallback_icon.pixmap(QSize(16, 16))
                
        return super().data(index, role)


class AccentSelectionTreeDelegate(QStyledItemDelegate):
    """Paint selected tree rows with accent-colored bold text without tinting the folder icon."""

    def __init__(self, bridge: "Bridge", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge

    def paint(self, painter: QPainter, option, index) -> None:
        from PySide6.QtWidgets import QStyleOptionViewItem
        from app.mediamanager.utils.pathing import normalize_windows_path

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        tree = self.parent()
        is_active_index = bool(tree is not None and hasattr(tree, "currentIndex") and tree.currentIndex() == index)
        is_selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        active_folder_path = ""
        try:
            selected_folders = getattr(self.bridge, "_selected_folders", []) or []
            if selected_folders:
                active_folder_path = normalize_windows_path(str(selected_folders[0] or "")).rstrip("/")
        except Exception:
            active_folder_path = ""
        item_path = ""
        try:
            model = index.model()
            if hasattr(model, "mapToSource") and hasattr(model, "sourceModel"):
                source_idx = model.mapToSource(index)
                source_model = model.sourceModel()
                if hasattr(source_model, "filePath"):
                    item_path = normalize_windows_path(str(source_model.filePath(source_idx) or "")).rstrip("/")
            elif hasattr(model, "filePath"):
                item_path = normalize_windows_path(str(model.filePath(index) or "")).rstrip("/")
        except Exception:
            item_path = ""
        is_active_path = bool(active_folder_path and item_path and item_path == active_folder_path)

        if is_selected or is_active_index or is_active_path:
            accent_str = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
            accent = QColor(accent_str)
            
            # Mix 24% foreground text color into the accent color for better readability in both light and dark extremes
            text_color = Theme.get_text_color()
            accent = QColor(Theme.mix(text_color, accent, 0.76))

            opt.font.setBold(True)
            opt.palette.setColor(opt.palette.ColorRole.Highlight, Qt.GlobalColor.transparent)
            opt.palette.setColor(opt.palette.ColorRole.Text, accent)
            opt.palette.setColor(opt.palette.ColorRole.WindowText, accent)
            opt.palette.setColor(opt.palette.ColorRole.HighlightedText, accent)
            if is_active_index or is_active_path:
                opt.state |= QStyle.StateFlag.State_Selected
            opt.state &= ~QStyle.StateFlag.State_HasFocus

        super().paint(painter, opt, index)


class TagListComboDelegate(QStyledItemDelegate):
    """Paint combo popup rows with accent-selected text and extra vertical breathing room."""

    def __init__(self, bridge: "Bridge", combo: QComboBox, parent: QWidget | None = None, *, show_actions: bool = False) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self.combo = combo
        self.show_actions = bool(show_actions)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        min_height = option.fontMetrics.height() + 10
        size.setHeight(max(size.height(), min_height))
        return size

    @staticmethod
    def trash_icon_rect(row_rect: QRect) -> QRect:
        icon_size = 16
        right_padding = 12
        return QRect(
            row_rect.right() - right_padding - icon_size + 1,
            row_rect.center().y() - (icon_size // 2),
            icon_size,
            icon_size,
        )

    @staticmethod
    def rename_chip_rect(row_rect: QRect) -> QRect:
        chip_width = 58
        chip_height = 22
        gap = 10
        trash_rect = TagListComboDelegate.trash_icon_rect(row_rect)
        return QRect(
            trash_rect.left() - gap - chip_width,
            row_rect.center().y() - (chip_height // 2),
            chip_width,
            chip_height,
        )

    @staticmethod
    def visibility_icon_rect(row_rect: QRect) -> QRect:
        chip_width = 28
        chip_height = 22
        gap = 8
        rename_rect = TagListComboDelegate.rename_chip_rect(row_rect)
        return QRect(
            rename_rect.left() - gap - chip_width,
            row_rect.center().y() - (chip_height // 2),
            chip_width,
            chip_height,
        )

    @staticmethod
    def action_at(row_rect: QRect, point: QPoint) -> str:
        if TagListComboDelegate.visibility_icon_rect(row_rect).contains(point):
            return "visibility"
        if TagListComboDelegate.rename_chip_rect(row_rect).contains(point):
            return "rename"
        if TagListComboDelegate.trash_icon_rect(row_rect).contains(point):
            return "delete"
        return ""

    def _hover_action(self, row_rect: QRect) -> str:
        parent = self.parent()
        try:
            target = parent.viewport() if parent is not None and hasattr(parent, "viewport") else parent
            point = target.mapFromGlobal(QCursor.pos()) if target is not None else QPoint(-1, -1)
        except Exception:
            point = QPoint(-1, -1)
        return self.action_at(row_rect, point) if row_rect.contains(point) else ""

    @staticmethod
    def _paint_eye_icon(painter: QPainter, rect: QRect, color: QColor, *, slashed: bool) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center_x = rect.left() + (rect.width() / 2.0)
        center_y = rect.top() + (rect.height() / 2.0)
        icon_rect = QRectF(
            center_x - 7.0,
            center_y - 5.0,
            14.0,
            10.0,
        )
        r = icon_rect.adjusted(0.5, 1.5, -0.5, -1.5)
        path = QPainterPath()
        path.moveTo(r.left(), r.center().y())
        path.cubicTo(r.left() + r.width() * 0.28, r.top(), r.left() + r.width() * 0.72, r.top(), r.right(), r.center().y())
        path.cubicTo(r.left() + r.width() * 0.72, r.bottom(), r.left() + r.width() * 0.28, r.bottom(), r.left(), r.center().y())
        painter.drawPath(path)
        pupil = QRectF(center_x - 1.8, center_y - 1.8, 3.6, 3.6)
        painter.setBrush(color)
        painter.drawEllipse(pupil)
        if slashed:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(
                round(icon_rect.left() + 1),
                round(icon_rect.bottom() - 1),
                round(icon_rect.right() - 1),
                round(icon_rect.top() + 1),
            )
        painter.restore()

    def paint(self, painter: QPainter, option, index) -> None:
        accent_str = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
        accent = QColor(accent_str)
        is_light = Theme.get_is_light()
        text_color = QColor(Theme.get_text_color())
        accent_text = QColor(Theme.mix(Theme.get_text_color(), accent, 0.76))
        combo_bg = QColor("#ffffff" if is_light else Theme.mix(Theme.get_control_bg(accent), "#000000", 0.12))
        hover_bg = QColor(Theme.mix(combo_bg.name(), "#000000" if is_light else "#ffffff", 0.04 if is_light else 0.07))
        is_current_value = index.row() == self.combo.currentIndex()
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        hover_action = self._hover_action(option.rect) if self.show_actions and is_hover else ""
        is_hidden = bool(index.data(Qt.ItemDataRole.UserRole + 1))

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(option.rect, hover_bg if is_hover and not is_current_value else combo_bg)

        font = option.font
        font.setBold(is_current_value)
        font.setItalic(is_hidden)
        painter.setFont(font)
        hidden_text = QColor(Theme.get_text_muted())
        painter.setPen(accent_text if is_current_value else (hidden_text if is_hidden else text_color))

        rename_rect = self.rename_chip_rect(option.rect) if self.show_actions else QRect()
        icon_rect = self.trash_icon_rect(option.rect) if self.show_actions else QRect()
        visibility_rect = self.visibility_icon_rect(option.rect) if self.show_actions else QRect()
        right_pad = (option.rect.right() - visibility_rect.left() + 12) if self.show_actions else 12
        text_rect = option.rect.adjusted(12, 5, -right_pad, -5)
        text = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
            Qt.TextElideMode.ElideRight,
            max(0, text_rect.width()),
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        if self.show_actions:
            default_chip_bg = QColor("#f3f4f6" if is_light else "#303236")
            default_chip_border = QColor("#c8cdd4" if is_light else "#5a5f66")
            hover_chip_bg = QColor(Theme.mix(combo_bg.name(), accent.name(), 0.18 if is_light else 0.26))
            hover_chip_border = QColor(Theme.mix(accent.name(), combo_bg.name(), 0.22 if is_light else 0.08))
            chip_bg = hover_chip_bg if hover_action == "rename" else default_chip_bg
            chip_border = hover_chip_border if hover_action == "rename" else default_chip_border
            chip_text = QColor(_selection_text_for_color(chip_bg))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QPen(chip_border, 1))
            painter.setBrush(chip_bg)
            painter.drawRoundedRect(QRectF(rename_rect), 6, 6)
            painter.setPen(chip_text)
            rename_font = QFont(font)
            rename_font.setBold(True)
            rename_font.setPointSizeF(max(8.5, rename_font.pointSizeF() - 0.5))
            painter.setFont(rename_font)
            painter.drawText(rename_rect, Qt.AlignmentFlag.AlignCenter, "Rename")

            eye_bg = hover_chip_bg if hover_action == "visibility" else default_chip_bg
            eye_border = hover_chip_border if hover_action == "visibility" else default_chip_border
            painter.setPen(QPen(eye_border, 1))
            painter.setBrush(eye_bg)
            painter.drawRoundedRect(QRectF(visibility_rect), 6, 6)
            self._paint_eye_icon(
                painter,
                visibility_rect,
                QColor(_selection_text_for_color(eye_bg)),
                slashed=is_hidden,
            )

            trash_icon_name = "trashcan.svg" if is_light else "trashcan-white.svg"
            trash_icon = QIcon(str((Path(__file__).with_name("web") / "icons" / trash_icon_name).resolve()))
            trash_hover_icon = QIcon(str((Path(__file__).with_name("web") / "icons" / "trashcan-red.svg").resolve()))
            icon = trash_hover_icon if hover_action == "delete" else trash_icon
            icon.paint(painter, icon_rect)
        painter.restore()


class TagListComboPopupView(QListView):
    deleteRequested = Signal(int)
    renameRequested = Signal(int)
    hiddenToggled = Signal(int, bool)

    def __init__(self, bridge: "Bridge", combo: QComboBox, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self.combo = combo
        self.setMouseTracking(True)

    def _tag_list_id_for_index(self, index: QModelIndex) -> int:
        if not index.isValid():
            return 0
        return int(index.data(Qt.ItemDataRole.UserRole) or 0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self.indexAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and index.isValid():
            point = event.position().toPoint()
            row_rect = self.visualRect(index)
            tag_list_id = self._tag_list_id_for_index(index)
            action = TagListComboDelegate.action_at(row_rect, point) if tag_list_id > 0 else ""
            if action == "visibility":
                self.combo.setCurrentIndex(index.row())
                is_hidden = bool(index.data(Qt.ItemDataRole.UserRole + 1))
                self.hiddenToggled.emit(tag_list_id, not is_hidden)
                event.accept()
                return
            if action == "rename":
                self.combo.setCurrentIndex(index.row())
                self.renameRequested.emit(tag_list_id)
                event.accept()
                return
            if action == "delete":
                self.combo.setCurrentIndex(index.row())
                self.deleteRequested.emit(tag_list_id)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        point = event.position().toPoint()
        index = self.indexAt(point)
        action = ""
        if index.isValid() and self._tag_list_id_for_index(index) > 0:
            action = TagListComboDelegate.action_at(self.visualRect(index), point)
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if action else Qt.CursorShape.ArrowCursor)
        self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().update()
        super().leaveEvent(event)

    def contextMenuEvent(self, event) -> None:
        index = self.indexAt(event.pos())
        if not index.isValid():
            super().contextMenuEvent(event)
            return

        tag_list_id = self._tag_list_id_for_index(index)
        if tag_list_id <= 0:
            return
        is_hidden = bool(index.data(Qt.ItemDataRole.UserRole + 1))

        self.combo.setCurrentIndex(index.row())
        menu = QMenu(self)
        act_toggle_hidden = menu.addAction("Unhide Tag List" if is_hidden else "Hide Tag List")
        act_rename = menu.addAction("Rename Tag List...")
        act_delete = menu.addAction("Delete Tag List")
        chosen = menu.exec(event.globalPos())
        if chosen == act_toggle_hidden:
            self.hiddenToggled.emit(tag_list_id, not is_hidden)
        elif chosen == act_rename:
            self.renameRequested.emit(tag_list_id)
        elif chosen == act_delete:
            self.deleteRequested.emit(tag_list_id)




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
