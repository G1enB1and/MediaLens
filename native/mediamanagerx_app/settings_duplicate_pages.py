from __future__ import annotations

from native.mediamanagerx_app.settings_common import *
from native.mediamanagerx_app.settings_general_pages import *
from native.mediamanagerx_app.settings_scanner_metadata_pages import *

class DuplicateSettingsPage(SettingsPage):
    def __init__(self, dialog: "SettingsDialog") -> None:
        super().__init__(dialog)
        self._loading = False
        self._folder_priority_syncing = False
        self._saved_preferred_folder_order: list[str] = [DUPLICATE_PREFERRED_FOLDERS_SENTINEL]
        self._folder_icon_provider = QFileIconProvider()
        self._folder_icon = self._folder_icon_provider.icon(QFileIconProvider.IconType.Folder)
        self._folder_icon_pixmap = self._folder_icon.pixmap(QSize(16, 16))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_section_title("Similar File Rules"))

        self.rules_scroll = QScrollArea()
        self.rules_scroll.setObjectName("settingsPageScroll")
        self.rules_scroll.setWidgetResizable(True)
        self.rules_scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.rules_scroll, 1)

        self.rules_page = QWidget()
        self.rules_page.setObjectName("settingsScrollPage")
        rules_layout = QVBoxLayout(self.rules_page)
        rules_layout.setContentsMargins(0, 0, 15, 6)
        rules_layout.setSpacing(12)

        rules_group = QGroupBox("Preference Rules")
        rules_form = QFormLayout(rules_group)
        self.rule_combos: dict[str, QComboBox] = {}
        for key, label_text, options, _default in DUPLICATE_RULE_POLICIES:
            combo = QComboBox()
            for option_value, option_label in options:
                combo.addItem(option_label, option_value)
            combo.currentIndexChanged.connect(lambda _index, setting_key=key, widget=combo: self._on_rule_changed(setting_key, widget))
            rules_form.addRow(label_text, combo)
            self.rule_combos[key] = combo
        rules_layout.addWidget(rules_group)

        format_group = QGroupBox("Prefered File Format Order (Drag and Drop to Sort)")
        format_layout = QVBoxLayout(format_group)
        self.format_list = ReorderListWidget()
        self.format_list.setMinimumHeight(260)
        self.format_list.orderChanged.connect(self._save_format_order)
        format_layout.addWidget(self.format_list)
        rules_layout.addWidget(format_group, 1)

        folders_group = QGroupBox("Folder Priorities")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(10)
        self.use_preferred_folders_toggle = QCheckBox("Use Preferred Folders")
        self.use_preferred_folders_toggle.toggled.connect(self._on_preferred_folders_toggled)
        folders_layout.addWidget(self.use_preferred_folders_toggle)
        self.folder_priority_panel = QWidget()
        folder_priority_panel_layout = QVBoxLayout(self.folder_priority_panel)
        folder_priority_panel_layout.setContentsMargins(0, 0, 0, 0)
        folder_priority_panel_layout.setSpacing(8)
        folder_priority_panel_layout.addWidget(
            _description("Drag and Drop from Available folders on the left into your preferred order on the right")
        )
        lists_row = QHBoxLayout()
        lists_row.setContentsMargins(0, 0, 0, 0)
        lists_row.setSpacing(12)

        available_layout = QVBoxLayout()
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.setSpacing(6)
        available_layout.addWidget(QLabel("Available Folders"))
        self.available_folders_tree = FolderSourceTreeWidget()
        self.available_folders_tree.setMinimumHeight(260)
        available_layout.addWidget(self.available_folders_tree)
        lists_row.addLayout(available_layout, 1)

        prioritized_layout = QVBoxLayout()
        prioritized_layout.setContentsMargins(0, 0, 0, 0)
        prioritized_layout.setSpacing(6)
        prioritized_layout.addWidget(QLabel("Prioritized Folder Order"))
        self.prioritized_folders_list = PrioritizedFolderListWidget()
        self.prioritized_folders_list.setMinimumHeight(260)
        self.prioritized_folders_list.setItemDelegate(PrioritizedFolderItemDelegate(self, self.prioritized_folders_list))
        self.prioritized_folders_list.orderChanged.connect(self._sync_folder_priority_lists)
        self.prioritized_folders_list.removeRequested.connect(self._remove_prioritized_folder)
        prioritized_layout.addWidget(self.prioritized_folders_list)
        lists_row.addLayout(prioritized_layout, 1)

        folder_priority_panel_layout.addLayout(lists_row)
        folders_layout.addWidget(self.folder_priority_panel)
        rules_layout.addWidget(folders_group, 1)

        priorities_group = QGroupBox("Rule Priority Order (Drag and Drop to Sort)")
        priorities_layout = QVBoxLayout(priorities_group)
        self.priority_list = ReorderListWidget()
        self.priority_list.setMinimumHeight(260)
        self.priority_list.orderChanged.connect(self._save_priority_order)
        priorities_layout.addWidget(self.priority_list)
        rules_layout.addWidget(priorities_group)

        merge_group = QGroupBox("Metadata Merge")
        merge_layout = QVBoxLayout(merge_group)
        self.merge_before_delete_toggle = QCheckBox("Merge metadata before deleting duplicates")
        merge_layout.addWidget(self.merge_before_delete_toggle)
        merge_grid = QGridLayout()
        self.merge_toggles: dict[str, QCheckBox] = {}
        for index, (key, label_text, _default) in enumerate(DUPLICATE_MERGE_FIELDS):
            checkbox = QCheckBox(label_text)
            checkbox.toggled.connect(lambda checked, setting_key=key: self._on_merge_toggle_changed(setting_key, checked))
            merge_grid.addWidget(checkbox, index // 2, index % 2)
            self.merge_toggles[key] = checkbox
        merge_layout.addLayout(merge_grid)
        rules_layout.addWidget(merge_group)

        reset_group = QGroupBox("Reset Group Exclusions")
        reset_layout = QVBoxLayout(reset_group)
        reset_copy = QLabel(
            "When you click X on files in duplicate or similar groups MediaLens remembers that file should not "
            "be included in that group on future rescans. If you think you may have made mistakes excluding "
            "actual duplicates you can reset those exclusions below."
        )
        reset_copy.setWordWrap(True)
        reset_copy.setObjectName("settingsDescription")
        reset_layout.addWidget(reset_copy)
        self.reset_group_exclusions_btn = QPushButton("Reset Group Exclusions")
        self.reset_group_exclusions_btn.clicked.connect(self._reset_group_exclusions)
        reset_layout.addWidget(self.reset_group_exclusions_btn, 0, Qt.AlignmentFlag.AlignLeft)
        rules_layout.addWidget(reset_group)
        rules_layout.addStretch(1)
        self.rules_scroll.setWidget(self.rules_page)
        self.merge_before_delete_toggle.toggled.connect(lambda checked: self.dialog.set_setting_bool("duplicate.rules.merge_before_delete", checked))

    def _on_rule_changed(self, key: str, combo: QComboBox) -> None:
        if not self._loading:
            self.dialog.set_setting_str(key, str(combo.currentData() or ""))

    def _save_format_order(self) -> None:
        if self._loading:
            return
        order = [str(self.format_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.format_list.count())]
        self.dialog.set_setting_str("duplicate.rules.format_order", json.dumps(order))

    def _save_priority_order(self) -> None:
        if self._loading:
            return
        order = [str(self.priority_list.item(index).data(Qt.ItemDataRole.UserRole) or "") for index in range(self.priority_list.count())]
        self.dialog.set_setting_str("duplicate.priorities.order", json.dumps(order))

    def _preferred_folder_order(self) -> list[str]:
        order: list[str] = []
        for index in range(self.prioritized_folders_list.count()):
            value = str(self.prioritized_folders_list.item(index).data(Qt.ItemDataRole.UserRole) or "").strip()
            if value:
                order.append(value)
        if DUPLICATE_PREFERRED_FOLDERS_SENTINEL not in order:
            order.append(DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        return order

    @staticmethod
    def _normalize_folder_priority_order(raw: object) -> list[str]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        if isinstance(raw, list):
            parsed = raw
        else:
            try:
                parsed = json.loads(str(raw or "[]"))
            except Exception:
                parsed = []
        order: list[str] = []
        seen: set[str] = set()
        for item in parsed if isinstance(parsed, list) else []:
            text = str(item or "").strip()
            if not text:
                continue
            if text == DUPLICATE_PREFERRED_FOLDERS_SENTINEL:
                key = "__sentinel__"
                normalized = DUPLICATE_PREFERRED_FOLDERS_SENTINEL
            else:
                normalized = normalize_windows_path(text).rstrip("/")
                if not normalized:
                    continue
                key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            order.append(normalized)
        if DUPLICATE_PREFERRED_FOLDERS_SENTINEL not in order:
            order.append(DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        return order

    @staticmethod
    def _folder_item_text(folder_path: str) -> str:
        return folder_path if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else folder_path.replace("/", "\\")

    def _configure_prioritized_folder_item(self, item: QListWidgetItem, folder_path: str, *, centered: bool = False, extra_top_space: int = 0) -> None:
        item.setText(self._folder_item_text(folder_path))
        item.setIcon(QIcon() if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else self._folder_icon)
        item.setData(Qt.ItemDataRole.UserRole, folder_path)
        item.setToolTip("" if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL else self._folder_item_text(folder_path))
        item.setData(FOLDER_PRIORITY_ROLE_CENTERED, bool(centered))
        item.setData(FOLDER_PRIORITY_ROLE_SENTINEL, folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL)
        item.setData(FOLDER_PRIORITY_ROLE_EXTRA_TOP, int(extra_top_space))
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )

    def _add_folder_list_item(self, target: QListWidget, folder_path: str, *, centered: bool = False, extra_top_space: int = 0) -> None:
        item = QListWidgetItem()
        self._configure_prioritized_folder_item(item, folder_path, centered=centered, extra_top_space=extra_top_space)
        target.addItem(item)

    def _rebuild_prioritized_folder_row_widgets(self) -> None:
        count = self.prioritized_folders_list.count()
        sentinel_only = count == 1 and str(self.prioritized_folders_list.item(0).data(Qt.ItemDataRole.UserRole) or "") == DUPLICATE_PREFERRED_FOLDERS_SENTINEL
        viewport_height = max(0, self.prioritized_folders_list.viewport().height())
        for index in range(count):
            item = self.prioritized_folders_list.item(index)
            folder_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
            is_sentinel = folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL
            centered = sentinel_only and is_sentinel
            extra_top_space = 34 if is_sentinel and not centered and index == 0 else 0
            self._configure_prioritized_folder_item(item, folder_path, centered=centered, extra_top_space=extra_top_space)
            item.setSizeHint(QSize(0, max(96, viewport_height - 8) if centered else (74 if is_sentinel and index == 0 else (40 if is_sentinel else 32))))
        self.prioritized_folders_list.viewport().update()

    def _remove_prioritized_folder(self, folder_path: str) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        if folder_path == DUPLICATE_PREFERRED_FOLDERS_SENTINEL:
            return
        for index in range(self.prioritized_folders_list.count()):
            item = self.prioritized_folders_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole) or "") != folder_path:
                continue
            self.prioritized_folders_list.takeItem(index)
            self._sync_folder_priority_lists()
            return

    def _scope_folder_paths(self) -> list[str]:
        from app.mediamanager.utils.pathing import normalize_windows_path

        selected_folders = list(getattr(self.bridge, "_selected_folders", []) or [])
        scope_folders: list[str] = []
        seen: set[str] = set()

        for raw_path in selected_folders:
            normalized = normalize_windows_path(str(raw_path or "")).rstrip("/")
            if normalized and normalized.casefold() not in seen:
                seen.add(normalized.casefold())
                scope_folders.append(normalized)

        for raw_root in selected_folders:
            root = Path(str(raw_root or "").strip())
            if not root.exists() or not root.is_dir():
                continue
            try:
                for child in root.rglob("*"):
                    if not child.is_dir():
                        continue
                    normalized = normalize_windows_path(str(child)).rstrip("/")
                    key = normalized.casefold()
                    if not normalized or key in seen:
                        continue
                    seen.add(key)
                    scope_folders.append(normalized)
            except Exception:
                continue
        return sorted(scope_folders, key=str.casefold)

    def _populate_available_folder_tree(self, scope_folders: list[str]) -> None:
        from app.mediamanager.utils.pathing import normalize_windows_path

        self.available_folders_tree.clear()
        selected_roots = []
        seen_roots: set[str] = set()
        for raw_root in list(getattr(self.bridge, "_selected_folders", []) or []):
            normalized = normalize_windows_path(str(raw_root or "")).rstrip("/")
            if not normalized or normalized.casefold() in seen_roots:
                continue
            seen_roots.add(normalized.casefold())
            selected_roots.append(normalized)

        children_by_parent: dict[str, list[str]] = {}
        for folder_path in scope_folders:
            parent = normalize_windows_path(str(Path(folder_path).parent)).rstrip("/")
            children_by_parent.setdefault(parent, []).append(folder_path)

        def add_node(parent_item: QTreeWidgetItem | None, folder_path: str) -> None:
            label = Path(folder_path).name or folder_path
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, folder_path)
            item.setToolTip(0, self._folder_item_text(folder_path))
            item.setIcon(0, self._folder_icon)
            if parent_item is None:
                self.available_folders_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            for child_path in sorted(children_by_parent.get(folder_path, []), key=str.casefold):
                add_node(item, child_path)

        for root_path in selected_roots:
            add_node(None, root_path)
        self.available_folders_tree.expandAll()

    def _save_preferred_folder_order(self) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        self._saved_preferred_folder_order = self._normalize_folder_priority_order(self._preferred_folder_order())
        raw_value = json.dumps(self._saved_preferred_folder_order)
        self.bridge.settings.setValue("duplicate/rules/preferred_folders_order", raw_value)
        self.bridge.settings.sync()
        try:
            self.bridge.uiFlagChanged.emit("duplicate.rules.preferred_folders_order", True)
        except Exception:
            pass

    def _apply_preferred_folder_sentinel_style(self) -> None:
        self._rebuild_prioritized_folder_row_widgets()

    def _schedule_preferred_folder_layout_refresh(self) -> None:
        QTimer.singleShot(0, self._apply_preferred_folder_sentinel_style)

    def _sync_folder_priority_lists(self) -> None:
        if self._loading or self._folder_priority_syncing:
            return
        self._folder_priority_syncing = True
        try:
            scope_folders = self._scope_folder_paths()
            self._populate_available_folder_tree(scope_folders)
            current_order = self._preferred_folder_order()
            source_order = current_order if current_order else self._saved_preferred_folder_order
            normalized_order = self._normalize_folder_priority_order(source_order)
            self._saved_preferred_folder_order = list(normalized_order)

            self.prioritized_folders_list.clear()
            for path in self._saved_preferred_folder_order:
                self._add_folder_list_item(self.prioritized_folders_list, path)
            self._apply_preferred_folder_sentinel_style()
        finally:
            self._folder_priority_syncing = False
        self._save_preferred_folder_order()

    def _on_preferred_folders_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        self.folder_priority_panel.setVisible(bool(checked))
        self.bridge.settings.setValue("duplicate/rules/preferred_folders_enabled", bool(checked))
        self.bridge.settings.sync()
        try:
            self.bridge.uiFlagChanged.emit("duplicate.rules.preferred_folders_enabled", bool(checked))
        except Exception:
            pass
        if checked:
            self._sync_folder_priority_lists()
            self._schedule_preferred_folder_layout_refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "prioritized_folders_list"):
            self._schedule_preferred_folder_layout_refresh()

    def _on_merge_toggle_changed(self, key: str, checked: bool) -> None:
        if self._loading:
            return
        all_key = "duplicate.rules.merge.all"
        if key == all_key:
            self.dialog.set_setting_bool(all_key, checked)
            if checked:
                for setting_key, toggle in self.merge_toggles.items():
                    if setting_key == all_key:
                        continue
                    with QSignalBlocker(toggle):
                        toggle.setChecked(True)
                    self.dialog.set_setting_bool(setting_key, True)
            return

        self.dialog.set_setting_bool(key, checked)
        if not checked:
            all_toggle = self.merge_toggles.get(all_key)
            if all_toggle is not None and all_toggle.isChecked():
                with QSignalBlocker(all_toggle):
                    all_toggle.setChecked(False)
                self.dialog.set_setting_bool(all_key, False)

    def _reset_group_exclusions(self) -> None:
        self.dialog.reset_review_group_exclusions()

    def refresh(self) -> None:
        self._loading = True
        try:
            for key, _label, options, default_value in DUPLICATE_RULE_POLICIES:
                combo = self.rule_combos[key]
                current_value = str(self.settings.value(key.replace(".", "/"), default_value, type=str) or default_value)
                values = [option_value for option_value, _option_label in options]
                combo.setCurrentIndex(values.index(current_value) if current_value in values else values.index(default_value))
            self.format_list.clear()
            for format_name in _json_list(self.settings.value("duplicate/rules/format_order", "[]", type=str), DUPLICATE_FORMAT_ORDER_DEFAULT):
                item = QListWidgetItem(format_name)
                item.setData(Qt.ItemDataRole.UserRole, format_name)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                self.format_list.addItem(item)
            self.priority_list.clear()
            for label_text in _json_list(self.settings.value("duplicate/priorities/order", "[]", type=str), DUPLICATE_PRIORITY_ORDER_DEFAULT):
                item = QListWidgetItem(label_text)
                item.setData(Qt.ItemDataRole.UserRole, label_text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                self.priority_list.addItem(item)
            preferred_enabled = bool(self.settings.value("duplicate/rules/preferred_folders_enabled", False, type=bool))
            with QSignalBlocker(self.use_preferred_folders_toggle):
                self.use_preferred_folders_toggle.setChecked(preferred_enabled)
            self.folder_priority_panel.setVisible(preferred_enabled)
            self.available_folders_tree.clear()
            self.prioritized_folders_list.clear()
            self._saved_preferred_folder_order = self._normalize_folder_priority_order(
                self.settings.value("duplicate/rules/preferred_folders_order", "[]", type=str)
            )
            for folder_path in self._saved_preferred_folder_order:
                self._add_folder_list_item(self.prioritized_folders_list, folder_path)
            self._sync_folder_priority_lists()
            with QSignalBlocker(self.merge_before_delete_toggle):
                self.merge_before_delete_toggle.setChecked(bool(self.settings.value("duplicate/rules/merge_before_delete", False, type=bool)))
            for key, _label, default_value in DUPLICATE_MERGE_FIELDS:
                with QSignalBlocker(self.merge_toggles[key]):
                    self.merge_toggles[key].setChecked(bool(self.settings.value(key.replace(".", "/"), default_value, type=bool)))
        finally:
            self._loading = False
        self._sync_folder_priority_lists()
        self._schedule_preferred_folder_layout_refresh()




__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
