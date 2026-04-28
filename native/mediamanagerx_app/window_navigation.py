from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *
from native.mediamanagerx_app.bridge import *
from native.mediamanagerx_app.gallery import *

class WindowNavigationMixin:
    def _update_navigation_state(self) -> None:
        self.bridge._can_nav_back = self._folder_history_index > 0
        self.bridge._can_nav_forward = 0 <= self._folder_history_index < (len(self._folder_history) - 1)
        self.bridge.emit_navigation_state()

    def _sync_tree_to_folder(self, path_str: str) -> None:
        if not path_str:
            return
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(path_str))
        self._suppress_tree_selection_history = True
        try:
            if root_idx.isValid():
                selection_model = self.tree.selectionModel()
                if selection_model is not None:
                    selection_model.clearSelection()
                    selection_model.setCurrentIndex(
                        root_idx,
                        QItemSelectionModel.SelectionFlag.ClearAndSelect
                        | QItemSelectionModel.SelectionFlag.Rows
                        | QItemSelectionModel.SelectionFlag.Current,
                    )
                else:
                    self.tree.setCurrentIndex(root_idx)
                self.tree.scrollTo(root_idx)
                self.tree.expand(root_idx)
        finally:
            self._suppress_tree_selection_history = False

    def _queue_tree_sync(self, path_str: str, *, re_root_tree: bool = False) -> None:
        if not path_str:
            return
        self._suspend_tree_auto_reveal = False
        self._pending_tree_sync_path = str(path_str)
        self._pending_tree_reroot = self._pending_tree_reroot or bool(re_root_tree)
        if not self.left_panel.isVisible():
            return
        self._tree_sync_timer.start(0)

    def _apply_pending_tree_sync(self) -> None:
        path_str = str(self._pending_tree_sync_path or "")
        re_root_tree = bool(self._pending_tree_reroot)
        self._pending_tree_sync_path = ""
        self._pending_tree_reroot = False
        if not path_str or not self.left_panel.isVisible():
            return
        self._suppress_tree_selection_history = True
        try:
            if re_root_tree or not self._tree_root_path:
                self._set_tree_root(path_str)
            self._sync_tree_to_folder(path_str)
        except Exception as exc:
            self.bridge._log(f"Tree sync failed for {path_str}: {exc}")
        finally:
            self._suppress_tree_selection_history = False

    def _set_tree_root(self, folder_path: str) -> None:
        if not folder_path:
            return
        p = Path(folder_path)
        path_str = str(p.absolute())
        self._tree_root_path = path_str
        self.proxy_model.setRootPath(path_str)

        if os.name == "nt":
            self.tree.setRootIndex(QModelIndex())
        else:
            root_parent = p.parent
            parent_idx = self.fs_model.setRootPath(str(root_parent))
            self.tree.setRootIndex(self.proxy_model.mapFromSource(parent_idx))

        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(path_str))
        if root_idx.isValid():
            self.tree.expand(root_idx)
        self._sync_pinned_selection_to_root()

    def _tree_needs_reroot_for_path(self, folder_path: str) -> bool:
        path_str = str(folder_path or "").strip()
        current_root = str(self._tree_root_path or "").strip()
        if not path_str or not current_root:
            return True
        try:
            from app.mediamanager.utils.pathing import normalize_windows_path
            norm_target = normalize_windows_path(path_str).rstrip("/")
            norm_root = normalize_windows_path(current_root).rstrip("/")
        except Exception:
            norm_target = path_str.replace("\\", "/").rstrip("/").lower()
            norm_root = current_root.replace("\\", "/").rstrip("/").lower()
        if not norm_target or not norm_root:
            return True
        if norm_target == norm_root:
            return False
        return not norm_target.startswith(norm_root + "/")

    def _navigate_to_folder(self, folder_path: str, *, record_history: bool = True, refresh: bool = False, re_root_tree: bool = False) -> None:
        if not folder_path:
            return
        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            QMessageBox.warning(self, "Invalid Folder", f"The folder does not exist:\n{folder_path}")
            return

        path_str = str(p.absolute())
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        is_new_target = path_str != current_path
        re_root_tree = bool(re_root_tree or self._tree_needs_reroot_for_path(path_str))

        if is_new_target or refresh:
            self._set_selected_folders([path_str])
            if refresh and not is_new_target:
                self.bridge.selectionChanged.emit([path_str])
        self._queue_tree_sync(path_str, re_root_tree=re_root_tree)

        if record_history:
            if self._folder_history_index >= 0 and self._folder_history[self._folder_history_index] == path_str:
                pass
            else:
                if self._folder_history_index < len(self._folder_history) - 1:
                    self._folder_history = self._folder_history[: self._folder_history_index + 1]
                self._folder_history.append(path_str)
                self._folder_history_index = len(self._folder_history) - 1
        self._update_navigation_state()

    def _on_load_folder_requested(self, folder_path: str) -> None:
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)

    def _load_drag_source_pixmap(self, path_str: str) -> QPixmap:
        source_pixmap = QPixmap()
        if path_str:
            try:
                p = Path(path_str)
                if p.exists():
                    candidates: list[Path] = [p]
                    poster = self.bridge._ensure_video_poster(p)
                    if poster and poster.exists() and poster not in candidates:
                        candidates.append(poster)

                    for candidate in candidates:
                        source_pixmap = QPixmap(str(candidate))
                        if not source_pixmap.isNull():
                            break
                        reader = QImageReader(str(candidate))
                        img = reader.read()
                        if not img.isNull():
                            source_pixmap = QPixmap.fromImage(img)
                            break
            except Exception:
                source_pixmap = QPixmap()

        if source_pixmap.isNull():
            provider = QFileIconProvider()
            source_pixmap = provider.icon(QFileIconProvider.IconType.File).pixmap(QSize(64, 64))
        return source_pixmap

    def _scaled_drag_preview_pixmap(self, path_str: str, preferred_width: int = 0, preferred_height: int = 0) -> QPixmap:
        max_preview = 100
        source_pixmap = self._load_drag_source_pixmap(path_str)
        src_w = int(preferred_width or source_pixmap.width() or max_preview)
        src_h = int(preferred_height or source_pixmap.height() or max_preview)
        if src_w <= 0:
            src_w = max_preview
        if src_h <= 0:
            src_h = max_preview
        scale = min(max_preview / src_w, max_preview / src_h, 1.0)
        draw_w = max(1, int(round(src_w * scale)))
        draw_h = max(1, int(round(src_h * scale)))
        return source_pixmap.scaled(draw_w, draw_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def _build_drag_preview_pixmap(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> QPixmap:
        clean_paths = [str(Path(p).absolute()) for p in (paths or []) if p]
        if not clean_paths and preview_path:
            clean_paths = [str(Path(preview_path).absolute())]
        if not clean_paths:
            return QPixmap()

        stack_paths: list[str] = []
        for candidate in [preview_path, *clean_paths]:
            if candidate and candidate not in stack_paths:
                stack_paths.append(candidate)
            if len(stack_paths) >= 3:
                break

        layered: list[tuple[QPixmap, int, int]] = []
        spread = 14
        max_w = 0
        max_h = 0
        back_to_front = list(reversed(stack_paths))
        layer_count = len(back_to_front)
        for idx, candidate in enumerate(back_to_front):
            preferred_w = preview_width if candidate == preview_path else 0
            preferred_h = preview_height if candidate == preview_path else 0
            pixmap = self._scaled_drag_preview_pixmap(candidate, preferred_w, preferred_h)
            x = (layer_count - 1 - idx) * spread
            y = idx * spread
            layered.append((pixmap, x, y))
            max_w = max(max_w, x + pixmap.width())
            max_h = max(max_h, y + pixmap.height())

        canvas = QPixmap(max_w, max_h)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        for pixmap, x, y in layered:
            painter.drawPixmap(x, y, pixmap)
        painter.end()
        return canvas

    def _start_native_gallery_drag(self, paths: list[str], preview_path: str, preview_width: int, preview_height: int) -> None:
        clean_paths = [str(Path(p).absolute()) for p in (paths or []) if p]
        if not clean_paths:
            return

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in clean_paths])
        mime.setText("\n".join(clean_paths))

        drag = QDrag(self.web)
        drag.setMimeData(mime)
        preview_pixmap = self._build_drag_preview_pixmap(clean_paths, preview_path, preview_width, preview_height)
        if hasattr(self, "native_tooltip"):
            self.native_tooltip.set_preview_pixmap(preview_pixmap)
        empty_drag = QPixmap(1, 1)
        empty_drag.fill(Qt.GlobalColor.transparent)
        drag.setPixmap(empty_drag)
        drag.setHotSpot(QPoint(0, 0))

        try:
            self.bridge.drag_target_folder = ""
            drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        finally:
            self.bridge.drag_target_folder = ""
            if hasattr(self, "native_tooltip"):
                self.native_tooltip.set_preview_pixmap(None)
            self.bridge.hide_drag_tooltip()
            self.bridge.set_drag_paths([])
            self.bridge.nativeDragFinished.emit()

    def show_recycle_bin_viewer(self):
        try:
            from native.mediamanagerx_app.recycle_bin import RecycleBinViewerWindow
            self.recycle_bin_viewer = RecycleBinViewerWindow(self)
            self.recycle_bin_viewer.show()
            self.recycle_bin_viewer.raise_()
            self.recycle_bin_viewer.activateWindow()
        except Exception as e:
            print("Failed to open recycle bin viewer:", e)

    def _on_navigate_to_folder_requested(self, folder_path: str) -> None:
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=False)

    def _navigate_back(self) -> None:
        if self._folder_history_index <= 0:
            self._update_navigation_state()
            return
        self._folder_history_index -= 1
        self._navigate_to_folder(self._folder_history[self._folder_history_index], record_history=False)

    def _navigate_forward(self) -> None:
        if self._folder_history_index >= len(self._folder_history) - 1:
            self._update_navigation_state()
            return
        self._folder_history_index += 1
        self._navigate_to_folder(self._folder_history[self._folder_history_index], record_history=False)

    def _navigate_up(self) -> None:
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if not current_path:
            self._update_navigation_state()
            return
        current = Path(current_path)
        parent = current.parent
        if str(parent) == str(current):
            self._update_navigation_state()
            return
        self._navigate_to_folder(str(parent), record_history=True)

    def _refresh_current_folder(self) -> None:
        self.bridge._invalidate_scan_caches()
        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if not current_path:
            self._update_navigation_state()
            return
        self._navigate_to_folder(current_path, record_history=False, refresh=True)

    def _on_directory_loaded(self, path: str) -> None:
        """Triggered when QFileSystemModel finishes loading a directory's contents."""
        self.bridge._log(f"Tree: Directory loaded: {path}")
        self._suppress_tree_selection_history = True
        try:
            self._on_directory_loaded_impl(path)
        finally:
            self._suppress_tree_selection_history = False

    def _on_directory_loaded_impl(self, path: str) -> None:
        self.proxy_model.invalidate()
        
        # If the tree's root index is still invalid, try to fix it now
        if not self.tree.rootIndex().isValid():
            root_path_str = self.proxy_model._root_path
            root_parent = Path(root_path_str).parent
            parent_idx = self.fs_model.index(str(root_parent))
            
            self.bridge._log(f"Tree: Late loading check - parent_idx valid={parent_idx.isValid()} for {root_parent}")
            
            if parent_idx.isValid():
                proxy_idx = self.proxy_model.mapFromSource(parent_idx)
                if proxy_idx.isValid():
                    self.bridge._log(f"Tree: Setting root index from directoryLoaded (late load success) for {root_parent}")
                    self.tree.setRootIndex(proxy_idx)
                else:
                    self.bridge._log(f"Tree: Proxy index still invalid for {root_parent}")
        
        # Also ensure the actual root is expanded
        root_path_str = self.proxy_model._root_path
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(root_path_str))
        if root_idx.isValid():
            if not self.tree.isExpanded(root_idx):
                self.bridge._log(f"Tree: Expanding root index for {root_path_str}")
                self.tree.expand(root_idx)
        else:
            # Try with normalized path if exact match fails
            norm_root = root_path_str.rstrip("/")
            root_idx = self.proxy_model.mapFromSource(self.fs_model.index(norm_root))
            if root_idx.isValid() and not self.tree.isExpanded(root_idx):
                self.bridge._log(f"Tree: Expanding root index (normalized) for {norm_root}")
                self.tree.expand(root_idx)

        current_path = self.bridge._selected_folders[0] if self.bridge._selected_folders else ""
        if current_path and not self._suspend_tree_auto_reveal:
            try:
                self._sync_tree_to_folder(current_path)
                self.tree.viewport().update()
            except Exception as exc:
                self.bridge._log(f"Tree current-folder sync failed after directory load: {exc}")

    def _on_tree_selection(self, *_args) -> None:
        if self._suppress_tree_selection_history:
            return
        self._suspend_tree_auto_reveal = False
        selection_model = self.tree.selectionModel()
        selected_indices = selection_model.selectedRows()
        
        paths = []
        for idx in selected_indices:
            if idx.isValid():
                source_idx = self.proxy_model.mapToSource(idx)
                path = self.fs_model.filePath(source_idx)
                if path:
                    paths.append(path)
        
        if paths:
            if hasattr(self, "collections_list"):
                self.collections_list.blockSignals(True)
                self.collections_list.clearSelection()
                self.collections_list.blockSignals(False)
            if hasattr(self, "smart_collections_list"):
                self.smart_collections_list.blockSignals(True)
                self.smart_collections_list.clearSelection()
                self.smart_collections_list.blockSignals(False)
            if len(paths) == 1:
                self._navigate_to_folder(paths[0], record_history=True)
            else:
                self._set_selected_folders(paths)
                self._update_navigation_state()

    def _reload_pinned_folders(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        try:
            pinned_folders = self.bridge.list_pinned_folders()
        except Exception:
            pinned_folders = []

        current_root = str(self._tree_root_path or "")
        current_root_key = current_root.replace("\\", "/").lower()
        show_hidden = self.bridge._show_hidden_enabled()

        self.pinned_folders_list.blockSignals(True)
        self.pinned_folders_list.clear()
        for folder_path in pinned_folders:
            path_str = str(folder_path or "").strip()
            if not path_str:
                continue
            try:
                is_hidden = self.bridge.repo.is_path_hidden(path_str)
            except Exception as exc:
                try:
                    self.bridge._log(f"Pinned folder hidden-state lookup skipped for {path_str}: {exc}")
                except Exception:
                    pass
                is_hidden = False
            if is_hidden and not show_hidden:
                continue
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, path_str)
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(is_hidden))
            item.setToolTip(path_str)
            self.pinned_folders_list.addItem(item)
            row_widget = self._build_pinned_folder_item_widget(path_str, is_hidden=is_hidden)
            item.setSizeHint(row_widget.sizeHint())
            self.pinned_folders_list.setItemWidget(item, row_widget)
            if path_str.replace("\\", "/").lower() == current_root_key:
                item.setSelected(True)
                self.pinned_folders_list.setCurrentItem(item)
                self._set_pinned_folder_row_selected(row_widget, True)
        self.pinned_folders_list.blockSignals(False)

    def _build_pinned_folder_item_widget(self, folder_path: str, *, is_hidden: bool = False) -> QWidget:
        row = QWidget()
        row.setObjectName("pinnedFolderRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        provider = QFileIconProvider()
        folder_icon = provider.icon(QFileIconProvider.IconType.Folder)

        icon_label = QLabel()
        icon_label.setObjectName("pinnedFolderIcon")
        folder_pixmap = folder_icon.pixmap(QSize(16, 16))
        icon_label.setPixmap(folder_pixmap)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_label = QLabel(Path(folder_path).name or folder_path)
        text_label.setObjectName("pinnedFolderText")
        text_label.setToolTip(folder_path)
        layout.addWidget(text_label, 1)

        pin_label = QLabel()
        pin_label.setObjectName("pinnedFolderPin")
        pin_label.setPixmap(self._create_pinned_icon_pixmap())
        pin_label.setToolTip("Pinned folder")
        layout.addWidget(pin_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        item_height = max(28, row.sizeHint().height())
        row.setMinimumHeight(item_height)
        row.setProperty("folderPixmap", folder_pixmap)
        row.setProperty("iconLabel", icon_label)
        row.setProperty("textLabel", text_label)
        row.setProperty("pinLabel", pin_label)
        row.setProperty("hidden", bool(is_hidden))
        text_label.setProperty("hidden", bool(is_hidden))
        icon_label.setProperty("hidden", bool(is_hidden))
        pin_label.setProperty("hidden", bool(is_hidden))
        if is_hidden:
            row.setToolTip(f"{folder_path}\nHidden")
            pin_label.setToolTip("Pinned folder\nHidden")
        self._set_pinned_folder_row_selected(row, False)
        return row

    def _set_pinned_folder_row_selected(self, row: QWidget, selected: bool) -> None:
        if row is None:
            return

        row.setProperty("selected", bool(selected))

        text_label = row.property("textLabel")
        if isinstance(text_label, QLabel):
            text_label.setProperty("selected", bool(selected))
            font = text_label.font()
            font.setBold(bool(selected))
            text_label.setFont(font)
            text_label.style().unpolish(text_label)
            text_label.style().polish(text_label)

        icon_label = row.property("iconLabel")
        folder_pixmap = row.property("folderPixmap")
        if isinstance(icon_label, QLabel) and isinstance(folder_pixmap, QPixmap):
            icon_label.setPixmap(folder_pixmap)
            icon_label.setProperty("selected", bool(selected))
            icon_label.style().unpolish(icon_label)
            icon_label.style().polish(icon_label)

        row.style().unpolish(row)
        row.style().polish(row)
        row.update()

    def _create_pinned_icon_pixmap(self, size: int = 14) -> QPixmap:
        asset_path = Path(__file__).with_name("web") / "icons" / "pin.svg"
        renderer = QSvgRenderer(str(asset_path))
        if not renderer.isValid():
            return QPixmap()

        logical_size = max(16, size + 2)
        device_pixel_ratio = 2.0
        canvas_size = int(logical_size * device_pixel_ratio)
        inset = int(2 * device_pixel_ratio)
        image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter, QRect(inset, inset, canvas_size - (inset * 2), canvas_size - (inset * 2)))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor(Theme.get_text_color()))
        painter.end()

        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        return pixmap

    def _sync_pinned_selection_to_root(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        root_key = str(self._tree_root_path or "").replace("\\", "/").lower()
        self.pinned_folders_list.blockSignals(True)
        matched_item: QListWidgetItem | None = None
        for row in range(self.pinned_folders_list.count()):
            item = self.pinned_folders_list.item(row)
            item_key = str(item.data(Qt.ItemDataRole.UserRole) or "").replace("\\", "/").lower()
            is_match = bool(root_key) and item_key == root_key
            item.setSelected(is_match)
            row_widget = self.pinned_folders_list.itemWidget(item)
            if isinstance(row_widget, QWidget):
                self._set_pinned_folder_row_selected(row_widget, is_match)
            if is_match:
                matched_item = item
        if matched_item is not None:
            self.pinned_folders_list.setCurrentItem(matched_item)
        else:
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.setCurrentItem(None)
        self.pinned_folders_list.blockSignals(False)

    def _on_pinned_folder_selection_changed(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        item = self.pinned_folders_list.currentItem()
        if not item:
            return
        folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not folder_path:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "collections_list"):
            self.collections_list.blockSignals(True)
            self.collections_list.clearSelection()
            self.collections_list.blockSignals(False)
        if hasattr(self, "smart_collections_list"):
            self.smart_collections_list.blockSignals(True)
            self.smart_collections_list.clearSelection()
            self.smart_collections_list.blockSignals(False)
        self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)

    def _on_pinned_folders_order_changed(self) -> None:
        if not hasattr(self, "pinned_folders_list"):
            return
        ordered: list[str] = []
        for row in range(self.pinned_folders_list.count()):
            item = self.pinned_folders_list.item(row)
            folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "").strip() if item is not None else ""
            if folder_path:
                ordered.append(folder_path)
        if ordered:
            self.bridge.reorder_pinned_folders(ordered)

    def _on_pinned_folders_context_menu(self, pos: QPoint) -> None:
        item = self.pinned_folders_list.itemAt(pos)
        if not item:
            return

        folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not folder_path:
            return
        is_hidden = bool(item.data(Qt.ItemDataRole.UserRole + 1))

        menu = QMenu(self)
        act_open = menu.addAction("Open Folder")
        act_hide = None
        act_unhide = None
        if is_hidden:
            act_unhide = menu.addAction("Unhide Folder")
        else:
            act_hide = menu.addAction("Hide Folder")
        act_unpin = menu.addAction("Unpin Folder")
        menu.addSeparator()
        act_explorer = menu.addAction("Open in File Explorer")

        chosen = menu.exec(self.pinned_folders_list.viewport().mapToGlobal(pos))
        if chosen == act_open:
            self._navigate_to_folder(folder_path, record_history=True, re_root_tree=True)
        elif chosen == act_hide:
            if self.bridge.set_folder_hidden(folder_path, True):
                self.proxy_model.invalidateFilter()
                self._reload_pinned_folders()
        elif chosen == act_unhide:
            if self.bridge.set_folder_hidden(folder_path, False):
                self.proxy_model.invalidateFilter()
                self._reload_pinned_folders()
        elif chosen == act_unpin:
            self.bridge.unpin_folder(folder_path)
        elif chosen == act_explorer:
            self.bridge.open_in_explorer(folder_path)

    def _show_folders_header_menu(self) -> None:
        menu = QMenu(self)
        act_expand_all = menu.addAction("Expand All")
        act_collapse_all = menu.addAction("Collapse All")
        chosen = menu.exec(self.folders_menu_btn.mapToGlobal(QPoint(0, self.folders_menu_btn.height())))
        if chosen == act_expand_all:
            self._expand_tree_from_root()
        elif chosen == act_collapse_all:
            self._collapse_tree_to_root()

    def _expand_tree_branch(self, parent_index: QModelIndex) -> None:
        model = self.tree.model()
        if model is None or not parent_index.isValid():
            return
        row_count = model.rowCount(parent_index)
        for row in range(row_count):
            child_index = model.index(row, 0, parent_index)
            if not child_index.isValid():
                continue
            if model.hasChildren(child_index):
                self.tree.expand(child_index)
                self._expand_tree_branch(child_index)

    def _expand_tree_from_root(self) -> None:
        root_index = self.tree.rootIndex()
        if not root_index.isValid():
            return
        self._suspend_tree_auto_reveal = False
        self.tree.expand(root_index)
        self._expand_tree_branch(root_index)

    def _collapse_tree_to_root(self) -> None:
        root_index = self.tree.rootIndex()
        if not root_index.isValid():
            return
        self._suspend_tree_auto_reveal = True
        self._pending_tree_sync_path = ""
        self._pending_tree_reroot = False
        self._tree_sync_timer.stop()
        self.tree.collapseAll()
        root_path = str(self._tree_root_path or "")
        if root_path:
            root_item = self.proxy_model.mapFromSource(self.fs_model.index(root_path))
            if root_item.isValid():
                self.tree.expand(root_item)

    def _reload_collections(self) -> None:
        if not hasattr(self, "collections_list"):
            return
        try:
            collections = self.bridge.list_collections()
            active = self.bridge.get_active_collection()
            active_id = int(active.get("id", 0) or 0)
        except Exception:
            collections = []
            active_id = 0

        self.collections_list.blockSignals(True)
        self.collections_list.clear()
        for collection in collections:
            count = int(collection.get("item_count", 0) or 0)
            label = str(collection.get("name", ""))
            is_hidden = bool(collection.get("is_hidden", 0))
            
            # If show_hidden is False, skip hidden collections in the list
            if not self.bridge._show_hidden_enabled() and is_hidden:
                continue

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, int(collection.get("id", 0)))
            item.setData(Qt.ItemDataRole.UserRole + 1, is_hidden)
            item.setToolTip(f"{label} ({count} items)")
            
            if is_hidden:
                # Dim the text for hidden collections if they are shown
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setForeground(QColor(128, 128, 128))

            self.collections_list.addItem(item)
            if int(collection.get("id", 0)) == active_id:
                item.setSelected(True)
                self.collections_list.setCurrentItem(item)
        self.collections_list.blockSignals(False)

    def _reload_smart_collections(self) -> None:
        if not hasattr(self, "smart_collections_list"):
            return
        try:
            smart_collections = self.bridge.list_smart_collections()
            active = self.bridge.get_active_smart_collection()
            active_key = str(active.get("key", "") or "")
        except Exception:
            smart_collections = []
            active_key = ""

        self.smart_collections_list.blockSignals(True)
        self.smart_collections_list.clear()
        for definition in smart_collections:
            count = int(definition.get("item_count", 0) or 0)
            label = str(definition.get("name", ""))
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(definition.get("key", "") or ""))
            item.setToolTip(f"{label} ({count} items)")
            self.smart_collections_list.addItem(item)
            if str(definition.get("key", "") or "") == active_key:
                item.setSelected(True)
                self.smart_collections_list.setCurrentItem(item)
        self.smart_collections_list.blockSignals(False)

    def _on_collection_selection_changed(self) -> None:
        if not hasattr(self, "collections_list"):
            return
        item = self.collections_list.currentItem()
        if not item:
            return
        collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
        if collection_id <= 0:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "pinned_folders_list"):
            self.pinned_folders_list.blockSignals(True)
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.blockSignals(False)
        if hasattr(self, "smart_collections_list"):
            self.smart_collections_list.blockSignals(True)
            self.smart_collections_list.clearSelection()
            self.smart_collections_list.blockSignals(False)
        self.bridge.set_active_collection(collection_id)

    def _on_smart_collection_selection_changed(self) -> None:
        if not hasattr(self, "smart_collections_list"):
            return
        item = self.smart_collections_list.currentItem()
        if not item:
            return
        smart_key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not smart_key:
            return
        self.tree.selectionModel().clearSelection()
        if hasattr(self, "pinned_folders_list"):
            self.pinned_folders_list.blockSignals(True)
            self.pinned_folders_list.clearSelection()
            self.pinned_folders_list.blockSignals(False)
        if hasattr(self, "collections_list"):
            self.collections_list.blockSignals(True)
            self.collections_list.clearSelection()
            self.collections_list.blockSignals(False)
        self.bridge.set_active_smart_collection(smart_key)

    def _on_collections_context_menu(self, pos: QPoint) -> None:
        item = self.collections_list.itemAt(pos)
        menu = QMenu(self)
        act_new = menu.addAction("New Collection...")
        act_rename = None
        act_delete = None
        act_hide = None
        act_unhide = None
        if item:
            is_hidden = item.data(Qt.ItemDataRole.UserRole + 1)
            if is_hidden:
                act_unhide = menu.addAction("Unhide Collection")
            else:
                act_hide = menu.addAction("Hide Collection")
            
            act_rename = menu.addAction("Rename...")
            act_delete = menu.addAction("Delete")

        chosen = menu.exec(self.collections_list.viewport().mapToGlobal(pos))
        if chosen == act_new:
            name, ok = _run_themed_text_input_dialog(self, "New Collection", "Collection Name:")
            if ok and name.strip():
                created = self.bridge.create_collection(name)
                if created:
                    self._reload_collections()
                    self.bridge.set_active_collection(int(created.get("id", 0) or 0))
                    self._reload_collections()
        elif item and chosen == act_rename:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            current_name = item.text()
            name, ok = _run_themed_text_input_dialog(self, "Rename Collection", "Collection Name:", text=current_name)
            if ok and name.strip() and name.strip() != current_name:
                if self.bridge.rename_collection(collection_id, name):
                    self._reload_collections()
        elif item and chosen == act_hide:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            if self.bridge.set_collection_hidden(collection_id, True):
                self._reload_collections()
        elif item and chosen == act_unhide:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            if self.bridge.set_collection_hidden(collection_id, False):
                self._reload_collections()
        elif item and chosen == act_delete:
            collection_id = int(item.data(Qt.ItemDataRole.UserRole) or 0)
            reply = QMessageBox.question(
                self,
                "Delete Collection",
                f"Delete collection '{item.text()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.bridge.delete_collection(collection_id):
                    self._reload_collections()



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
