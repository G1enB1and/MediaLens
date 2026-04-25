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

class WindowLayoutPanelsMixin:
    def _add_sep(self, obj_name: str) -> NativeSeparator:
        sep = NativeSeparator()
        sep.setObjectName(obj_name)
        sep.setFixedHeight(21)
        sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return sep

    def _native_arrow_icon(self, direction: str) -> QIcon:
        mode = "light" if Theme.get_is_light() else "dark"
        icon_path = Path(__file__).with_name("web") / "scrollbar_arrows" / f"{mode}_{direction}.svg"
        return QIcon(str(icon_path))

    def _set_bulk_tag_section_toggle(self, toggle: QToolButton, label: str, expanded: bool) -> None:
        toggle.setText(label)
        toggle.setProperty("sectionLabel", label)
        toggle.setIcon(self._native_arrow_icon("down" if expanded else "right"))
        toggle.setIconSize(QSize(12, 12))
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def _build_layout(self) -> None:
        try:
            accent_val = str(self.bridge.settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
        except Exception:
            accent_val = Theme.ACCENT_DEFAULT
        
        self._current_accent = accent_val
        accent_q = QColor(accent_val)

        splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter

        # Left: folder tree (native)
        self.left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(0)

        # Choose initial root based on settings.
        default_root = None
        if self.bridge._restore_last_enabled():
            lf = self.bridge._last_folder()
            if lf:
                p = Path(lf)
                if p.exists() and p.is_dir():
                    default_root = p

        if default_root is None:
            sf = self.bridge._start_folder_setting()
            if sf:
                p = Path(sf)
                if p.exists() and p.is_dir():
                    default_root = p

        if default_root is None:
            p = Path("C:/Pictures")
            if p.exists():
                default_root = p

        if default_root is None:
            default_root = Path.home()

        self.bridge._log(f"Tree: Initializing with root={default_root}")
        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath(str(default_root))

        # Use a proxy model to show the root folder itself at the top.
        self.proxy_model = RootFilterProxyModel(self.bridge, self)
        self.proxy_model.setSourceModel(self.fs_model)
        self.proxy_model.setRootPath(str(default_root))

        self.tree = FolderTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setProperty("showDecorationSelected", False)
        self.tree.setItemDelegate(AccentSelectionTreeDelegate(self.bridge, self.tree))
        
        # Set the tree root to the PARENT of our desired root folder
        # root_parent needs to be loaded by fs_model for visibility.
        root_parent = default_root.parent
        self.bridge._log(f"Tree: Setting root index to parent={root_parent}")
        parent_idx = self.fs_model.setRootPath(str(root_parent))
        
        proxy_parent_idx = self.proxy_model.mapFromSource(parent_idx)
        self.bridge._log(f"Tree: Proxy parent index valid={proxy_parent_idx.isValid()}")
        self.tree.setRootIndex(proxy_parent_idx)

        # Expand the root folder by default
        root_idx = self.proxy_model.mapFromSource(self.fs_model.index(str(default_root)))
        self.bridge._log(f"Tree: Root index valid={root_idx.isValid()}")
        if root_idx.isValid():
            self.tree.expand(root_idx)
        else:
            # If still invalid, it might be because the model hasn't loaded the parent yet.
            # We'll rely on directoryLoaded to fix this.
            self.bridge._log(f"Tree: Root index (late load pending) for {default_root}")
        
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(14)
        self.tree.setExpandsOnDoubleClick(True)
        from PySide6.QtWidgets import QAbstractItemView
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Hide columns: keep only name (indices are on the proxy model)
        for col in range(1, self.proxy_model.columnCount()):
            self.tree.hideColumn(col)

        self.tree.selectionModel().selectionChanged.connect(self._on_tree_selection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Connect to directoryLoaded so we can refresh icons/expansion once ready
        self.fs_model.directoryLoaded.connect(self._on_directory_loaded)

        self.left_sections_splitter = CustomSplitter(Qt.Orientation.Vertical)
        self.left_sections_splitter.setObjectName("leftSectionsSplitter")
        self.left_sections_splitter.setChildrenCollapsible(False)
        self.left_sections_splitter.setHandleWidth(5)

        pinned_section = QWidget(self.left_sections_splitter)
        pinned_layout = QVBoxLayout(pinned_section)
        pinned_layout.setContentsMargins(0, 0, 0, 0)
        pinned_layout.setSpacing(6)
        self.pinned_header = QLabel("Pinned Folders")
        pinned_layout.addWidget(self.pinned_header)

        self.pinned_folders_list = PinnedFolderListWidget()
        self.pinned_folders_list.setObjectName("pinnedFoldersList")
        self.pinned_folders_list.setMinimumHeight(0)
        self.pinned_folders_list.itemSelectionChanged.connect(self._on_pinned_folder_selection_changed)
        self.pinned_folders_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pinned_folders_list.customContextMenuRequested.connect(self._on_pinned_folders_context_menu)
        pinned_layout.addWidget(self.pinned_folders_list, 1)
        pinned_section.setMinimumHeight(self.pinned_header.sizeHint().height() + pinned_layout.contentsMargins().top())

        folders_section = QWidget(self.left_sections_splitter)
        folders_layout = QVBoxLayout(folders_section)
        folders_layout.setContentsMargins(0, 8, 0, 0)
        folders_layout.setSpacing(6)

        folders_header_row = QWidget(folders_section)
        folders_header_layout = QHBoxLayout(folders_header_row)
        folders_header_layout.setContentsMargins(0, 0, 0, 0)
        folders_header_layout.setSpacing(6)
        self.folders_header = QLabel("Folders")
        folders_header_layout.addWidget(self.folders_header)
        folders_header_layout.addStretch(1)

        self.folders_menu_btn = QPushButton("...")
        self.folders_menu_btn.setObjectName("foldersMenuButton")
        self.folders_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folders_menu_btn.setFixedSize(QSize(26, 22))
        self.folders_menu_btn.clicked.connect(self._show_folders_header_menu)
        folders_header_layout.addWidget(self.folders_menu_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        folders_layout.addWidget(folders_header_row)
        folders_layout.addWidget(self.tree, 1)

        collections_section = QWidget(self.left_sections_splitter)
        collections_layout = QVBoxLayout(collections_section)
        collections_layout.setContentsMargins(0, 8, 0, 0)
        collections_layout.setSpacing(6)
        self.collections_header = QLabel("Collections")
        collections_layout.addWidget(self.collections_header)

        self.collections_list = CollectionListWidget()
        self.collections_list.setObjectName("collectionsList")
        self.collections_list.setMinimumHeight(0)
        self.collections_list.itemSelectionChanged.connect(self._on_collection_selection_changed)
        self.collections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.collections_list.customContextMenuRequested.connect(self._on_collections_context_menu)
        collections_layout.addWidget(self.collections_list, 1)
        collections_section.setMinimumHeight(self.collections_header.sizeHint().height() + collections_layout.contentsMargins().top())

        smart_collections_section = QWidget(self.left_sections_splitter)
        smart_collections_layout = QVBoxLayout(smart_collections_section)
        smart_collections_layout.setContentsMargins(0, 8, 0, 0)
        smart_collections_layout.setSpacing(6)
        self.smart_collections_header = QLabel("Smart Collections")
        smart_collections_layout.addWidget(self.smart_collections_header)

        self.smart_collections_list = CollectionListWidget()
        self.smart_collections_list.setObjectName("smartCollectionsList")
        self.smart_collections_list.setMinimumHeight(0)
        self.smart_collections_list.setAcceptDrops(False)
        self.smart_collections_list.setDropIndicatorShown(False)
        self.smart_collections_list.itemSelectionChanged.connect(self._on_smart_collection_selection_changed)
        smart_collections_layout.addWidget(self.smart_collections_list, 1)
        smart_collections_section.setMinimumHeight(self.smart_collections_header.sizeHint().height() + smart_collections_layout.contentsMargins().top())

        self.left_sections_splitter.addWidget(pinned_section)
        self.left_sections_splitter.addWidget(folders_section)
        self.left_sections_splitter.addWidget(collections_section)
        self.left_sections_splitter.addWidget(smart_collections_section)
        self.left_sections_splitter.setStretchFactor(0, 0)
        self.left_sections_splitter.setStretchFactor(1, 1)
        self.left_sections_splitter.setStretchFactor(2, 0)
        self.left_sections_splitter.setStretchFactor(3, 0)
        left_sections_state = self.bridge.settings.value("ui/left_sections_splitter_state_v3")
        if left_sections_state:
            self.left_sections_splitter.restoreState(left_sections_state)
        else:
            self.left_sections_splitter.setSizes([140, 260, 150, 150])
        self.left_sections_splitter.splitterMoved.connect(lambda *args: self._save_splitter_state())

        left_layout.addWidget(self.left_sections_splitter, 1)

        self.bridge.pinnedFoldersChanged.connect(self._reload_pinned_folders)
        self.bridge.collectionsChanged.connect(self._reload_collections)
        self.bridge.collectionsChanged.connect(self._reload_smart_collections)
        self._reload_pinned_folders()
        self._reload_collections()
        self._reload_smart_collections()

        self._navigate_to_folder(str(default_root), record_history=True, re_root_tree=True)

        # Apply UI flags from settings
        try:
            show_left = bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool))
            self._apply_ui_flag("ui.show_left_panel", show_left)
        except Exception:
            pass

        # Center: embedded WebEngine UI scaffold + future bottom chat panel
        center_container = QWidget(splitter)
        center_container_layout = QVBoxLayout(center_container)
        center_container_layout.setContentsMargins(0, 0, 0, 0)

        center_splitter = CustomSplitter(Qt.Orientation.Vertical)
        center_splitter.setObjectName("centerSplitter")
        center_splitter.setMouseTracking(True)
        center_splitter.setHandleWidth(7)
        center_splitter.setChildrenCollapsible(False)
        self.center_splitter = center_splitter

        center = QWidget(center_splitter)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.web = GalleryView(center)
        if bool(_WINDOWS_WEBENGINE_RUNTIME.get("use_custom_page", True)):
            self.web.setPage(GalleryWebPage(self.web))
        center_layout.addWidget(self.web)

        # Native loading overlay shown while the WebEngine page itself is loading.
        self.web_loading = QWidget(self.web)
        self.web_loading.setStyleSheet(f"background: {Theme.get_bg(accent_q)};")
        self.web_loading.setGeometry(self.web.rect())
        self.web_loading.setVisible(True)

        wl_layout = QVBoxLayout(self.web_loading)
        wl_layout.setContentsMargins(24, 24, 24, 24)
        wl_layout.setSpacing(10)

        loading_center = QWidget(self.web_loading)
        center_layout_loading = QVBoxLayout(loading_center)
        center_layout_loading.setContentsMargins(0, 0, 0, 0)
        center_layout_loading.setSpacing(10)

        self.web_loading_label = QLabel("Loading gallery UIâ€¦")
        self.web_loading_label.setObjectName("webLoadingLabel")
        self.web_loading_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        center_layout_loading.addWidget(self.web_loading_label)

        self.web_loading_bar = QProgressBar()
        self.web_loading_bar.setRange(0, 100)
        self.web_loading_bar.setValue(0)
        self.web_loading_bar.setTextVisible(False)
        self.web_loading_bar.setFixedSize(QSize(320, 10))
        try:
            accent = str(self.bridge.settings.value("ui/accent_color", "#8ab4f8", type=str) or "#8ab4f8")
        except Exception:
            accent = "#8ab4f8"

        self.web_loading_bar.setStyleSheet(
            "QProgressBar{background: rgba(255,255,255,25); border-radius: 5px;} "
            f"QProgressBar::chunk{{background: {accent}; border-radius: 5px;}}"
        )
        center_layout_loading.addWidget(self.web_loading_bar, 0, Qt.AlignmentFlag.AlignHCenter)

        wl_layout.addStretch(1)
        wl_layout.addWidget(loading_center, 0, Qt.AlignmentFlag.AlignCenter)
        wl_layout.addStretch(1)

        # Right: Tag List + Metadata Panels
        self.right_panel_host = QWidget(splitter)
        self.right_panel_host.setObjectName("rightPanelHost")
        right_host_layout = QVBoxLayout(self.right_panel_host)
        right_host_layout.setContentsMargins(0, 0, 0, 0)
        right_host_layout.setSpacing(0)

        self.right_splitter = CustomSplitter(Qt.Orientation.Horizontal)
        self.right_splitter.setObjectName("rightSplitter")
        self.right_splitter.setHandleWidth(7)
        self.right_splitter.setChildrenCollapsible(False)
        right_host_layout.addWidget(self.right_splitter)

        self.tag_list_panel = QWidget(self.right_splitter)
        self.tag_list_panel.setObjectName("tagListPanel")
        self.tag_list_panel.setMinimumWidth(220)
        self.tag_list_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.tag_list_panel_layout = QVBoxLayout(self.tag_list_panel)
        self.tag_list_panel_layout.setContentsMargins(12, 12, 12, 12)
        self.tag_list_panel_layout.setSpacing(8)

        self.tag_list_header_row = QWidget(self.tag_list_panel)
        self.tag_list_header_row.setObjectName("tagListHeaderRow")
        tag_list_header_layout = QHBoxLayout(self.tag_list_header_row)
        tag_list_header_layout.setContentsMargins(0, 0, 0, 0)
        tag_list_header_layout.setSpacing(8)
        self.tag_list_title_lbl = QLabel("Tag List")
        self.tag_list_title_lbl.setObjectName("tagListTitleLabel")
        tag_list_header_layout.addWidget(self.tag_list_title_lbl)
        tag_list_header_layout.addStretch(1)
        self.tag_list_close_btn = QPushButton("")
        self.tag_list_close_btn.setObjectName("tagListCloseButton")
        self.tag_list_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tag_list_close_btn.setFixedSize(22, 22)
        self.tag_list_close_btn.clicked.connect(self._close_tag_list_panel)
        tag_list_header_layout.addWidget(self.tag_list_close_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tag_list_panel_layout.addWidget(self.tag_list_header_row)

        self.tag_list_select = QComboBox(self.tag_list_panel)
        self.tag_list_select.setObjectName("tagListSelect")
        self._configure_tag_list_combo(self.tag_list_select)
        self.tag_list_select.currentIndexChanged.connect(self._on_tag_list_changed)
        self.tag_list_panel_layout.addWidget(self.tag_list_select)

        self.btn_create_tag_list = QPushButton("Create New List")
        self.btn_create_tag_list.setObjectName("btnCreateTagList")
        self.btn_create_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create_tag_list.clicked.connect(self._create_tag_list)
        self.tag_list_panel_layout.addWidget(self.btn_create_tag_list)

        self.active_tag_list_name_lbl = ContextClickableLabel("")
        self.active_tag_list_name_lbl.setObjectName("activeTagListNameLabel")
        self.active_tag_list_name_lbl.setVisible(False)
        self.active_tag_list_name_lbl.rightClicked.connect(self._rename_active_tag_list)
        self.tag_list_panel_layout.addWidget(self.active_tag_list_name_lbl)

        self.tag_list_sort_lbl = QLabel("Sort By")
        self.tag_list_sort_lbl.setObjectName("tagListSortLabel")
        self.tag_list_sort_lbl.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.tag_list_sort_lbl)

        self.tag_list_sort_select = QComboBox(self.tag_list_panel)
        self.tag_list_sort_select.setObjectName("tagListSortSelect")
        self._configure_tag_list_combo(self.tag_list_sort_select)
        self.tag_list_sort_select.addItem("None", "none")
        self.tag_list_sort_select.addItem("A-Z", "az")
        self.tag_list_sort_select.addItem("Z-A", "za")
        self.tag_list_sort_select.addItem("Most Used", "most_used")
        self.tag_list_sort_select.addItem("Least Used", "least_used")
        self.tag_list_sort_select.currentIndexChanged.connect(self._on_tag_list_sort_changed)
        self.tag_list_sort_select.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.tag_list_sort_select)

        self.btn_add_tag_list_tag = QPushButton("Add New Tag")
        self.btn_add_tag_list_tag.setObjectName("btnAddTagListTag")
        self.btn_add_tag_list_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_tag_list_tag.clicked.connect(self._add_tag_to_active_list)
        self.btn_add_tag_list_tag.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_add_tag_list_tag)

        self.btn_import_tag_list_tags = QPushButton("Import Tags from Selected File(s)")
        self.btn_import_tag_list_tags.setObjectName("btnImportTagListTags")
        self.btn_import_tag_list_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_tag_list_tags.clicked.connect(self._import_tags_from_current_file_into_active_list)
        self.btn_import_tag_list_tags.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_import_tag_list_tags)

        self.btn_clear_tag_scope_filter = QPushButton("Deselect Tag Filter")
        self.btn_clear_tag_scope_filter.setObjectName("btnClearTagScopeFilter")
        self.btn_clear_tag_scope_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_tag_scope_filter.clicked.connect(self._clear_tag_scope_filter)
        self.btn_clear_tag_scope_filter.setVisible(False)
        self.tag_list_panel_layout.addWidget(self.btn_clear_tag_scope_filter)

        self.tag_list_rows = TagListRowsWidget(self.tag_list_panel)
        self.tag_list_rows.setObjectName("tagListRows")
        self.tag_list_rows.setMinimumHeight(0)
        self.tag_list_rows.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tag_list_rows.orderChanged.connect(self._persist_active_tag_list_order)
        self.tag_list_rows.backgroundClicked.connect(self._clear_tag_scope_filter)
        self.tag_list_panel_layout.addWidget(self.tag_list_rows, 1)

        self.tag_list_empty_lbl = QLabel("Create or select a tag list.")
        self.tag_list_empty_lbl.setObjectName("tagListEmptyLabel")
        self.tag_list_empty_lbl.setWordWrap(True)
        self.tag_list_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.tag_list_empty_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tag_list_empty_lbl.setVisible(True)
        self.tag_list_panel_layout.addWidget(self.tag_list_empty_lbl)

        self.tag_list_bottom_spacer = QSpacerItem(
            0,
            0,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )
        self.tag_list_panel_layout.addItem(self.tag_list_bottom_spacer)

        self.right_panel = QWidget(self.right_splitter)
        self.right_panel.setObjectName("rightPanel")
        outer_right_layout = QVBoxLayout(self.right_panel)
        outer_right_layout.setContentsMargins(0, 0, 0, 0)
        outer_right_layout.setSpacing(0)

        self.right_workspace_stack = QStackedWidget(self.right_panel)
        self.right_workspace_stack.setObjectName("rightWorkspaceStack")
        outer_right_layout.addWidget(self.right_workspace_stack)

        self.details_workspace = QWidget(self.right_workspace_stack)
        self.details_workspace.setObjectName("detailsWorkspace")
        details_workspace_layout = QVBoxLayout(self.details_workspace)
        details_workspace_layout.setContentsMargins(0, 0, 0, 0)
        details_workspace_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("metaScrollArea")
        self.scroll_area.viewport().installEventFilter(self)
        
        self.scroll_container = QWidget(self.scroll_area)
        self.scroll_container.setObjectName("rightPanelScrollContainer")
        right_layout = QVBoxLayout(self.scroll_container)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(6)
        self.right_layout = right_layout

        # Preview Header Row (Always visible title + toggle buttons)
        self.preview_header_row = QWidget(self.scroll_container)
        self.preview_header_row.setObjectName("previewHeaderRow")
        preview_header_layout = QHBoxLayout(self.preview_header_row)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(6)
        
        self.preview_header_lbl = QLabel("Preview")
        self.preview_header_lbl.setObjectName("previewHeaderLabel")
        preview_header_layout.addWidget(self.preview_header_lbl)
        preview_header_layout.addStretch(1)

        self.btn_play_preview = QPushButton("Play")
        self.btn_play_preview.setObjectName("btnPlayPreview")
        self.btn_play_preview.setToolTip("Open selected video preview")
        self.btn_play_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_preview.clicked.connect(self._play_selected_video_in_sidebar)
        self.btn_play_preview.hide()
        preview_header_layout.addWidget(self.btn_play_preview)

        # Toggle OFF (Hide) button
        self.btn_close_preview = QPushButton("")
        self.btn_close_preview.setObjectName("btnClosePreview")
        self.btn_close_preview.setToolTip("Hide preview image")
        self.btn_close_preview.setFixedSize(QSize(22, 22))
        self.btn_close_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_preview.clicked.connect(lambda: self.bridge.set_setting_bool("ui.preview_above_details", False))
        preview_header_layout.addWidget(self.btn_close_preview)

        # Toggle ON (Show) button
        self.btn_show_preview_inline = QPushButton("â›¶") # Unicode maximize/corners
        self.btn_show_preview_inline.setObjectName("btnShowPreviewInline")
        self.btn_show_preview_inline.setToolTip("Show preview image")
        self.btn_show_preview_inline.setFixedSize(QSize(22, 22))
        self.btn_show_preview_inline.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show_preview_inline.clicked.connect(lambda: self.bridge.set_setting_bool("ui.preview_above_details", True))
        preview_header_layout.addWidget(self.btn_show_preview_inline)

        right_layout.addWidget(self.preview_header_row)

        self.preview_image_lbl = QLabel()
        self.preview_image_lbl.setObjectName("previewImageLabel")
        self.preview_image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_lbl.setMinimumHeight(0)
        self.preview_image_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.preview_image_lbl.setText("No preview")
        self.preview_image_lbl.setWordWrap(True)
        self.preview_image_lbl.setCursor(Qt.CursorShape.ArrowCursor)
        self._preview_bg_hint = ""
        self._preview_source_pixmap: QPixmap | None = None
        self._preview_movie: QMovie | None = None
        self._preview_aspect_ratio = 1.0
        right_layout.addWidget(self.preview_image_lbl)

        # Sidebar preview overlay is manually positioned to the preview label's rect.
        # Avoid also putting it in a layout, which can produce bad geometry/clipping.
        self.sidebar_video_overlay: LightboxVideoOverlay | None = None

        self.btn_preview_overlay_play = QPushButton(self.preview_image_lbl)
        self.btn_preview_overlay_play.setObjectName("btnPreviewOverlayPlay")
        self.btn_preview_overlay_play.setToolTip("Play video in preview")
        self.btn_preview_overlay_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_preview_overlay_play.setFixedSize(QSize(52, 52))
        self.btn_preview_overlay_play.setIconSize(QSize(30, 30))
        self._update_preview_play_button_icon()
        self.btn_preview_overlay_play.clicked.connect(self._play_selected_video_in_sidebar)
        self.btn_preview_overlay_play.installEventFilter(self)
        self.btn_preview_overlay_play.hide()
        self.btn_preview_overlay_play.raise_()
        self._video_preview_transition_active = False

        self.preview_sep = self._add_sep("preview_sep_line")
        right_layout.addWidget(self.preview_sep)

        self.details_header_lbl = QLabel("Details")
        self.details_header_lbl.setObjectName("detailsHeaderLabel")
        right_layout.addWidget(self.details_header_lbl)

        self.meta_empty_state_lbl = QLabel("Select file(s) to view details.")
        self.meta_empty_state_lbl.setObjectName("metaEmptyStateLabel")
        self.meta_empty_state_lbl.setWordWrap(True)
        self.meta_empty_state_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self.meta_empty_state_lbl)
        self.meta_empty_state_lbl.setVisible(False)

        self.meta_empty_select_all_btn = QPushButton("Select All")
        self.meta_empty_select_all_btn.setObjectName("metaEmptySelectAllButton")
        self.meta_empty_select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_empty_select_all_btn.clicked.connect(self._select_all_visible_gallery_items)
        self.meta_empty_select_all_btn.setVisible(False)
        right_layout.addWidget(self.meta_empty_select_all_btn)

        self.scroll_area.setWidget(self.scroll_container)
        details_workspace_layout.addWidget(self.scroll_area)

        # --- Filename (editable, triggers rename) ---
        self.lbl_fn_cap = QLabel("Filename:")
        right_layout.addWidget(self.lbl_fn_cap)
        self.meta_filename_edit = QLineEdit()
        self.meta_filename_edit.setPlaceholderText("filename.ext")
        self.meta_filename_edit.setObjectName("metaFilenameEdit")
        self.meta_filename_edit.editingFinished.connect(self._rename_from_panel)
        right_layout.addWidget(self.meta_filename_edit)

        # --- Read-only file info (single label per field, label + value inline) ---
        self.meta_path_lbl = QLabel("Folder:")
        self.meta_path_lbl.setObjectName("metaPathLabel")
        self.meta_path_lbl.setWordWrap(True)
        right_layout.addWidget(self.meta_path_lbl)

        self.meta_size_lbl = QLabel("File Size:")
        self.meta_size_lbl.setObjectName("metaSizeLabel")

        self.meta_res_lbl = QLabel("")
        self.meta_res_lbl.setObjectName("metaResLabel")

        self.lbl_exif_date_taken_cap = QLabel("Date Taken:")
        self.lbl_exif_date_taken_cap.setObjectName("metaExifDateTakenCaption")
        self.meta_exif_date_taken_edit = QLineEdit()
        self.meta_exif_date_taken_edit.setObjectName("metaExifDateTakenEdit")
        self.meta_exif_date_taken_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")

        self.lbl_metadata_date_cap = QLabel("Date Acquired:")
        self.lbl_metadata_date_cap.setObjectName("metaMetadataDateCaption")
        self.meta_metadata_date_edit = QLineEdit()
        self.meta_metadata_date_edit.setObjectName("metaMetadataDateEdit")
        self.meta_metadata_date_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")

        self.lbl_original_file_date_cap = QLabel("Original File Date:")
        self.lbl_original_file_date_cap.setObjectName("metaOriginalFileDateCaption")
        self.meta_original_file_date_lbl = QLabel("")
        self.meta_original_file_date_lbl.setObjectName("metaOriginalFileDateLabel")
        self.meta_original_file_date_lbl.setWordWrap(True)

        self.lbl_file_created_date_cap = QLabel("Windows ctime:")
        self.lbl_file_created_date_cap.setObjectName("metaFileCreatedDateCaption")
        self.meta_file_created_date_lbl = QLabel("")
        self.meta_file_created_date_lbl.setObjectName("metaFileCreatedDateLabel")
        self.meta_file_created_date_lbl.setWordWrap(True)

        self.lbl_file_modified_date_cap = QLabel("Date Modified:")
        self.lbl_file_modified_date_cap.setObjectName("metaFileModifiedDateCaption")
        self.meta_file_modified_date_lbl = QLabel("")
        self.meta_file_modified_date_lbl.setObjectName("metaFileModifiedDateLabel")
        self.meta_file_modified_date_lbl.setWordWrap(True)

        self.lbl_text_detected_cap = QLabel("Text and OCR")
        self.lbl_text_detected_cap.setObjectName("metaTextDetectedCaption")
        self.meta_text_detected_row = QWidget()
        self.meta_text_detected_row.setObjectName("metaSwitchRow")
        text_detected_layout = QHBoxLayout(self.meta_text_detected_row)
        text_detected_layout.setContentsMargins(0, 0, 0, 0)
        text_detected_layout.setSpacing(8)
        self.meta_text_detected_toggle = QCheckBox()
        self.meta_text_detected_toggle.setObjectName("metaSwitch")
        self.meta_text_detected_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_text_detected_value_lbl = QLabel("No Text")
        self.meta_text_detected_value_lbl.setObjectName("metaSwitchValueLabel")
        text_detected_layout.addWidget(self.meta_text_detected_toggle)
        text_detected_layout.addWidget(self.meta_text_detected_value_lbl)
        text_detected_layout.addStretch(1)
        self.meta_text_detected_toggle.toggled.connect(
            lambda checked: self._set_switch_value_label(self.meta_text_detected_value_lbl, checked, "Text", "No Text")
        )
        self.meta_text_detected_toggle.clicked.connect(self._save_text_detected_override_from_toggle)
        self.lbl_text_detected_note = QLabel("This overrides the auto text detection value of [No Text Detected]")
        self.lbl_text_detected_note.setObjectName("metaFieldNoteLabel")
        self.lbl_text_detected_note.setWordWrap(True)

        self.lbl_detected_text_cap = QLabel("Text and OCR:")
        self.lbl_detected_text_cap.setObjectName("metaDetectedTextCaption")
        self.meta_detected_text_edit = QPlainTextEdit()
        self.meta_detected_text_edit.setObjectName("metaDetectedTextEdit")
        self.meta_detected_text_edit.setPlaceholderText("OCR text or manually entered text...")
        self.meta_detected_text_edit.setMaximumHeight(90)
        self.ocr_progress_lbl = ProgressStatusLabel("")
        self.ocr_progress_lbl.setObjectName("localAiProgressLabel")
        self._configure_progress_status_label(self.ocr_progress_lbl)
        self.ocr_progress_lbl.setVisible(False)
        self.ocr_progress_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.ocr_progress_lbl.setMinimumWidth(0)
        self.ocr_error_edit = QPlainTextEdit()
        self.ocr_error_edit.setObjectName("localAiErrorText")
        self._configure_local_ai_error_widget(self.ocr_error_edit)
        self.ocr_error_edit.setVisible(False)
        self.ocr_error_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.ocr_error_edit.setMinimumWidth(0)
        self.ocr_button_row = QWidget()
        self.ocr_button_row.setObjectName("ocrButtonRow")
        self.ocr_button_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.ocr_button_row.setMinimumWidth(0)
        ocr_button_layout = QVBoxLayout(self.ocr_button_row)
        ocr_button_layout.setContentsMargins(0, 0, 0, 0)
        ocr_button_layout.setSpacing(6)
        self.btn_use_ocr = QPushButton("OCR (Fast)")
        self.btn_use_ocr.setObjectName("btnUseOcr")
        self.btn_use_ocr.setProperty("baseText", "OCR (Fast)")
        self.btn_use_ocr.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use_ocr.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_use_ocr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_use_ocr.clicked.connect(lambda: self._run_text_ocr("paddle_fast"))
        self.btn_use_ocr_gemma = QPushButton("OCR (AI)")
        self.btn_use_ocr_gemma.setObjectName("btnUseOcrGemma")
        self.btn_use_ocr_gemma.setProperty("baseText", "OCR (AI)")
        self.btn_use_ocr_gemma.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use_ocr_gemma.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_use_ocr_gemma.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_use_ocr_gemma.clicked.connect(lambda: self._run_text_ocr("gemma4"))
        ocr_button_layout.addWidget(self.btn_use_ocr)
        ocr_button_layout.addWidget(self.btn_use_ocr_gemma)
        
        self.meta_fields_layout = QVBoxLayout()
        self.meta_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.meta_fields_layout.setSpacing(6)
        right_layout.addLayout(self.meta_fields_layout)

        # --- Group Labels ---
        self.lbl_group_general = QLabel("General")
        self.lbl_group_general.setObjectName("metaGroupLabel")
        self.lbl_group_general.hide()

        self.lbl_group_camera = QLabel("Camera")
        self.lbl_group_camera.setObjectName("metaGroupLabel")
        self.lbl_group_camera.hide()

        self.lbl_group_ai = QLabel("AI")
        self.lbl_group_ai.setObjectName("metaGroupLabel")
        self.lbl_group_ai.hide()

        self.meta_camera_lbl = QLabel("")
        self.meta_camera_lbl.setObjectName("metaCameraLabel")

        self.meta_location_lbl = QLabel("")
        self.meta_location_lbl.setObjectName("metaLocationLabel")

        self.meta_iso_lbl = QLabel("")
        self.meta_iso_lbl.setObjectName("metaISOLabel")

        self.meta_shutter_lbl = QLabel("")
        self.meta_shutter_lbl.setObjectName("metaShutterLabel")

        self.meta_aperture_lbl = QLabel("")
        self.meta_aperture_lbl.setObjectName("metaApertureLabel")

        self.meta_software_lbl = QLabel("")
        self.meta_software_lbl.setObjectName("metaSoftwareLabel")

        self.meta_lens_lbl = QLabel("")
        self.meta_lens_lbl.setObjectName("metaLensLabel")

        self.meta_dpi_lbl = QLabel("")
        self.meta_dpi_lbl.setObjectName("metaDPILabel")

        self.meta_duration_lbl = QLabel("")
        self.meta_duration_lbl.setObjectName("metaDurationLabel")

        self.meta_fps_lbl = QLabel("")
        self.meta_fps_lbl.setObjectName("metaFPSLabel")

        self.meta_codec_lbl = QLabel("")
        self.meta_codec_lbl.setObjectName("metaCodecLabel")

        self.meta_audio_lbl = QLabel("")
        self.meta_audio_lbl.setObjectName("metaAudioLabel")

        self.lbl_embedded_tags_cap = QLabel("Embedded-Tags (semicolon separated):")
        self.lbl_embedded_tags_cap.setObjectName("metaEmbeddedTagsCaption")
        self.meta_embedded_tags_edit = QLineEdit()
        self.meta_embedded_tags_edit.setObjectName("metaEmbeddedTagsEdit")
        self.meta_embedded_tags_edit.setPlaceholderText("keyword1; keyword2; keyword3")

        self.lbl_embedded_comments_cap = QLabel("Embedded-Comments:")
        self.lbl_embedded_comments_cap.setObjectName("metaEmbeddedCommentsCaption")
        self.meta_embedded_comments_edit = QTextEdit()
        self.meta_embedded_comments_edit.setObjectName("metaEmbeddedCommentsEdit")
        self.meta_embedded_comments_edit.setPlaceholderText("Embedded comments...")
        self.meta_embedded_comments_edit.setMaximumHeight(70)

        self.lbl_embedded_metadata_cap = QLabel("Embedded Metadata:")
        self.lbl_embedded_metadata_cap.setObjectName("metaEmbeddedMetadataCaption")
        self.meta_embedded_metadata_edit = QTextEdit()
        self.meta_embedded_metadata_edit.setObjectName("metaEmbeddedMetadataEdit")
        self.meta_embedded_metadata_edit.setReadOnly(True)
        self.meta_embedded_metadata_edit.setPlaceholderText("Embedded XMP/RDF and custom metadata...")
        self.meta_embedded_metadata_edit.setMaximumHeight(110)

        self.lbl_ai_status_cap = QLabel("AI Detection:")
        self.lbl_ai_status_cap.setObjectName("metaAIStatusCaption")
        self.meta_ai_status_edit = QLineEdit()
        self.meta_ai_status_edit.setObjectName("metaAIStatusEdit")
        self.meta_ai_status_edit.setReadOnly(True)
        self.meta_ai_status_edit.setPlaceholderText("AI detection status...")

        self.lbl_ai_generated_cap = QLabel("AI Generated?")
        self.lbl_ai_generated_cap.setObjectName("metaAIGeneratedCaption")
        self.meta_ai_generated_row = QWidget()
        self.meta_ai_generated_row.setObjectName("metaSwitchRow")
        ai_generated_layout = QHBoxLayout(self.meta_ai_generated_row)
        ai_generated_layout.setContentsMargins(0, 0, 0, 0)
        ai_generated_layout.setSpacing(8)
        self.meta_ai_generated_toggle = QCheckBox()
        self.meta_ai_generated_toggle.setObjectName("metaSwitch")
        self.meta_ai_generated_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.meta_ai_generated_value_lbl = QLabel("Non-AI")
        self.meta_ai_generated_value_lbl.setObjectName("metaSwitchValueLabel")
        ai_generated_layout.addWidget(self.meta_ai_generated_toggle)
        ai_generated_layout.addWidget(self.meta_ai_generated_value_lbl)
        ai_generated_layout.addStretch(1)
        self.meta_ai_generated_toggle.toggled.connect(
            lambda checked: self._set_switch_value_label(self.meta_ai_generated_value_lbl, checked, "AI", "Non-AI")
        )
        self.meta_ai_generated_toggle.clicked.connect(self._save_ai_generated_override_from_toggle)
        self.lbl_ai_generated_note = QLabel("This overrides the auto AI Detection value of [Not AI Generated]")
        self.lbl_ai_generated_note.setObjectName("metaFieldNoteLabel")
        self.lbl_ai_generated_note.setWordWrap(True)

        self.lbl_ai_source_cap = QLabel("AI Tool / Source:")
        self.lbl_ai_source_cap.setObjectName("metaAISourceCaption")
        self.meta_ai_source_edit = QTextEdit()
        self.meta_ai_source_edit.setObjectName("metaAISourceEdit")
        self.meta_ai_source_edit.setReadOnly(False)
        self.meta_ai_source_edit.setPlaceholderText("Tool and source metadata...")
        self.meta_ai_source_edit.setMaximumHeight(60)

        self.lbl_ai_families_cap = QLabel("AI Metadata Families:")
        self.lbl_ai_families_cap.setObjectName("metaAIFamiliesCaption")
        self.meta_ai_families_edit = QLineEdit()
        self.meta_ai_families_edit.setObjectName("metaAIFamiliesEdit")
        self.meta_ai_families_edit.setReadOnly(False)
        self.meta_ai_families_edit.setPlaceholderText("Detected metadata families...")

        self.lbl_ai_detection_reasons_cap = QLabel("AI Detection Reasons:")
        self.lbl_ai_detection_reasons_cap.setObjectName("metaAIDetectionReasonsCaption")
        self.meta_ai_detection_reasons_edit = QTextEdit()
        self.meta_ai_detection_reasons_edit.setObjectName("metaAIDetectionReasonsEdit")
        self.meta_ai_detection_reasons_edit.setReadOnly(False)
        self.meta_ai_detection_reasons_edit.setPlaceholderText("Detection reasons...")
        self.meta_ai_detection_reasons_edit.setMaximumHeight(60)

        self.lbl_ai_loras_cap = QLabel("AI LoRAs:")
        self.lbl_ai_loras_cap.setObjectName("metaAILorasCaption")
        self.meta_ai_loras_edit = QTextEdit()
        self.meta_ai_loras_edit.setObjectName("metaAILorasEdit")
        self.meta_ai_loras_edit.setReadOnly(True)
        self.meta_ai_loras_edit.setPlaceholderText("LoRAs...")
        self.meta_ai_loras_edit.setMaximumHeight(60)

        self.lbl_ai_model_cap = QLabel("AI Model:")
        self.lbl_ai_model_cap.setObjectName("metaAIModelCaption")
        self.meta_ai_model_edit = QLineEdit()
        self.meta_ai_model_edit.setObjectName("metaAIModelEdit")
        self.meta_ai_model_edit.setReadOnly(False)
        self.meta_ai_model_edit.setPlaceholderText("Model...")

        self.lbl_ai_checkpoint_cap = QLabel("AI Checkpoint:")
        self.lbl_ai_checkpoint_cap.setObjectName("metaAICheckpointCaption")
        self.meta_ai_checkpoint_edit = QLineEdit()
        self.meta_ai_checkpoint_edit.setObjectName("metaAICheckpointEdit")
        self.meta_ai_checkpoint_edit.setReadOnly(False)
        self.meta_ai_checkpoint_edit.setPlaceholderText("Checkpoint...")

        self.lbl_ai_sampler_cap = QLabel("AI Sampler:")
        self.lbl_ai_sampler_cap.setObjectName("metaAISamplerCaption")
        self.meta_ai_sampler_edit = QLineEdit()
        self.meta_ai_sampler_edit.setObjectName("metaAISamplerEdit")
        self.meta_ai_sampler_edit.setReadOnly(False)
        self.meta_ai_sampler_edit.setPlaceholderText("Sampler...")

        self.lbl_ai_scheduler_cap = QLabel("AI Scheduler:")
        self.lbl_ai_scheduler_cap.setObjectName("metaAISchedulerCaption")
        self.meta_ai_scheduler_edit = QLineEdit()
        self.meta_ai_scheduler_edit.setObjectName("metaAISchedulerEdit")
        self.meta_ai_scheduler_edit.setReadOnly(False)
        self.meta_ai_scheduler_edit.setPlaceholderText("Scheduler...")

        self.lbl_ai_cfg_cap = QLabel("AI CFG:")
        self.lbl_ai_cfg_cap.setObjectName("metaAICFGCaption")
        self.meta_ai_cfg_edit = QLineEdit()
        self.meta_ai_cfg_edit.setObjectName("metaAICFGEdit")
        self.meta_ai_cfg_edit.setReadOnly(False)
        self.meta_ai_cfg_edit.setPlaceholderText("CFG...")

        self.lbl_ai_steps_cap = QLabel("AI Steps:")
        self.lbl_ai_steps_cap.setObjectName("metaAIStepsCaption")
        self.meta_ai_steps_edit = QLineEdit()
        self.meta_ai_steps_edit.setObjectName("metaAIStepsEdit")
        self.meta_ai_steps_edit.setReadOnly(False)
        self.meta_ai_steps_edit.setPlaceholderText("Steps...")

        self.lbl_ai_seed_cap = QLabel("AI Seed:")
        self.lbl_ai_seed_cap.setObjectName("metaAISeedCaption")
        self.meta_ai_seed_edit = QLineEdit()
        self.meta_ai_seed_edit.setObjectName("metaAISeedEdit")
        self.meta_ai_seed_edit.setReadOnly(False)
        self.meta_ai_seed_edit.setPlaceholderText("Seed...")

        self.lbl_ai_upscaler_cap = QLabel("AI Upscaler:")
        self.lbl_ai_upscaler_cap.setObjectName("metaAIUpscalerCaption")
        self.meta_ai_upscaler_edit = QLineEdit()
        self.meta_ai_upscaler_edit.setObjectName("metaAIUpscalerEdit")
        self.meta_ai_upscaler_edit.setReadOnly(False)
        self.meta_ai_upscaler_edit.setPlaceholderText("Upscaler...")

        self.lbl_ai_denoise_cap = QLabel("AI Denoise:")
        self.lbl_ai_denoise_cap.setObjectName("metaAIDenoiseCaption")
        self.meta_ai_denoise_edit = QLineEdit()
        self.meta_ai_denoise_edit.setObjectName("metaAIDenoiseEdit")
        self.meta_ai_denoise_edit.setReadOnly(False)
        self.meta_ai_denoise_edit.setPlaceholderText("Denoise strength...")

        # --- Separators ---
        self.meta_sep1 = self._add_sep("meta_sep1_line")
        self.meta_sep2 = self._add_sep("meta_sep2_line")
        self.meta_sep3 = self._add_sep("meta_sep3_line")
        # --- Separators (Container + Line pattern for perfect 1px rendering) ---

        # --- Editable metadata ---
        self.lbl_desc_cap = QLabel("Description:")
        self.meta_desc = QTextEdit()
        self.meta_desc.setPlaceholderText("Add a description...")
        self.meta_desc.setMaximumHeight(130)
        self.meta_desc.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.generate_description_btn_row = QWidget()
        self.generate_description_btn_row.setObjectName("generateDescriptionButtonRow")
        self.generate_description_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_btn_row.setMinimumWidth(0)
        generate_description_btn_layout = QHBoxLayout(self.generate_description_btn_row)
        generate_description_btn_layout.setContentsMargins(0, 0, 0, 0)
        generate_description_btn_layout.setSpacing(0)
        self.btn_generate_description = QPushButton("Generate Description")
        self.btn_generate_description.setObjectName("btnGenerateDescription")
        self.btn_generate_description.setProperty("baseText", "Generate Description")
        self.btn_generate_description.setToolTip("Generate a local AI description using the current database tags as context")
        self.btn_generate_description.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_generate_description.clicked.connect(self._run_local_ai_description)
        generate_description_btn_layout.addWidget(self.btn_generate_description)
        self.generate_description_progress_lbl = ProgressStatusLabel("")
        self.generate_description_progress_lbl.setObjectName("localAiProgressLabel")
        self._configure_progress_status_label(self.generate_description_progress_lbl)
        self.generate_description_progress_lbl.setVisible(False)
        self.generate_description_progress_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_progress_lbl.setMinimumWidth(0)
        self.generate_description_error_edit = QPlainTextEdit()
        self.generate_description_error_edit.setObjectName("localAiErrorText")
        self._configure_local_ai_error_widget(self.generate_description_error_edit)
        self.generate_description_error_edit.setVisible(False)
        self.generate_description_error_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_description_error_edit.setMinimumWidth(0)

        self.lbl_tags_cap = QLabel("Tags (comma separated):")
        self.meta_tags = QTextEdit()
        self.meta_tags.setPlaceholderText("tag1, tag2...")
        self.meta_tags.setMaximumHeight(118)
        self.meta_tags.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.meta_tags.textChanged.connect(self._save_native_tags)
        self.meta_tags.textChanged.connect(lambda: self._refresh_tag_list_rows_state())

        self.generate_tags_btn_row = QWidget()
        self.generate_tags_btn_row.setObjectName("generateTagsButtonRow")
        self.generate_tags_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_btn_row.setMinimumWidth(0)
        generate_tags_btn_layout = QHBoxLayout(self.generate_tags_btn_row)
        generate_tags_btn_layout.setContentsMargins(0, 0, 0, 0)
        generate_tags_btn_layout.setSpacing(0)
        self.btn_generate_tags = QPushButton("Generate Tags")
        self.btn_generate_tags.setObjectName("btnGenerateTags")
        self.btn_generate_tags.setProperty("baseText", "Generate Tags")
        self.btn_generate_tags.setToolTip("Generate local AI tags and merge them into the database tag field")
        self.btn_generate_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_generate_tags.clicked.connect(self._run_local_ai_tags)
        generate_tags_btn_layout.addWidget(self.btn_generate_tags)
        self.generate_tags_progress_lbl = ProgressStatusLabel("")
        self.generate_tags_progress_lbl.setObjectName("localAiProgressLabel")
        self._configure_progress_status_label(self.generate_tags_progress_lbl)
        self.generate_tags_progress_lbl.setVisible(False)
        self.generate_tags_progress_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_progress_lbl.setMinimumWidth(0)
        self.generate_tags_error_edit = QPlainTextEdit()
        self.generate_tags_error_edit.setObjectName("localAiErrorText")
        self._configure_local_ai_error_widget(self.generate_tags_error_edit)
        self.generate_tags_error_edit.setVisible(False)
        self.generate_tags_error_edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.generate_tags_error_edit.setMinimumWidth(0)

        self.tag_list_open_btn_row = QWidget()
        self.tag_list_open_btn_row.setObjectName("tagListOpenButtonRow")
        self.tag_list_open_btn_row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        tag_list_open_btn_layout = QHBoxLayout(self.tag_list_open_btn_row)
        tag_list_open_btn_layout.setContentsMargins(0, 0, 0, 0)
        tag_list_open_btn_layout.setSpacing(0)
        self.btn_open_tag_list = QPushButton("Open Tag List")
        self.btn_open_tag_list.setObjectName("btnOpenTagList")
        self.btn_open_tag_list.setProperty("baseText", "Open Tag List")
        self.btn_open_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_tag_list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_open_tag_list.clicked.connect(self._toggle_tag_list_panel)
        tag_list_open_btn_layout.addWidget(self.btn_open_tag_list)

        self.lbl_ai_prompt_cap = QLabel("AI Prompt:")
        self.lbl_ai_prompt_cap.setObjectName("metaAIPromptCaption")
        self.meta_ai_prompt_edit = QTextEdit()
        self.meta_ai_prompt_edit.setObjectName("metaAIPromptEdit")
        self.meta_ai_prompt_edit.setPlaceholderText("AI prompt...")
        self.meta_ai_prompt_edit.setMaximumHeight(70)

        self.lbl_ai_negative_prompt_cap = QLabel("AI Negative Prompt:")
        self.lbl_ai_negative_prompt_cap.setObjectName("metaAINegativePromptCaption")
        self.meta_ai_negative_prompt_edit = QTextEdit()
        self.meta_ai_negative_prompt_edit.setObjectName("metaAINegativePromptEdit")
        self.meta_ai_negative_prompt_edit.setPlaceholderText("AI negative prompt...")
        self.meta_ai_negative_prompt_edit.setMaximumHeight(70)

        self.lbl_ai_params_cap = QLabel("AI Parameters:")
        self.lbl_ai_params_cap.setObjectName("metaAIParamsCaption")
        self.meta_ai_params_edit = QTextEdit()
        self.meta_ai_params_edit.setObjectName("metaAIParamsEdit")
        self.meta_ai_params_edit.setPlaceholderText("AI parameters...")
        self.meta_ai_params_edit.setMaximumHeight(70)

        self.lbl_ai_workflows_cap = QLabel("AI Workflows:")
        self.lbl_ai_workflows_cap.setObjectName("metaAIWorkflowsCaption")
        self.meta_ai_workflows_edit = QTextEdit()
        self.meta_ai_workflows_edit.setObjectName("metaAIWorkflowsEdit")
        self.meta_ai_workflows_edit.setReadOnly(True)
        self.meta_ai_workflows_edit.setPlaceholderText("Workflow metadata...")
        self.meta_ai_workflows_edit.setMaximumHeight(70)

        self.lbl_ai_provenance_cap = QLabel("AI Provenance:")
        self.lbl_ai_provenance_cap.setObjectName("metaAIProvenanceCaption")
        self.meta_ai_provenance_edit = QTextEdit()
        self.meta_ai_provenance_edit.setObjectName("metaAIProvenanceEdit")
        self.meta_ai_provenance_edit.setReadOnly(True)
        self.meta_ai_provenance_edit.setPlaceholderText("Provenance metadata...")
        self.meta_ai_provenance_edit.setMaximumHeight(70)

        self.lbl_ai_character_cards_cap = QLabel("AI Character Cards:")
        self.lbl_ai_character_cards_cap.setObjectName("metaAICharacterCardsCaption")
        self.meta_ai_character_cards_edit = QTextEdit()
        self.meta_ai_character_cards_edit.setObjectName("metaAICharacterCardsEdit")
        self.meta_ai_character_cards_edit.setReadOnly(True)
        self.meta_ai_character_cards_edit.setPlaceholderText("Character card metadata...")
        self.meta_ai_character_cards_edit.setMaximumHeight(70)

        self.lbl_ai_raw_paths_cap = QLabel("AI Metadata Paths:")
        self.lbl_ai_raw_paths_cap.setObjectName("metaAIRawPathsCaption")
        self.meta_ai_raw_paths_edit = QTextEdit()
        self.meta_ai_raw_paths_edit.setObjectName("metaAIRawPathsEdit")
        self.meta_ai_raw_paths_edit.setReadOnly(True)
        self.meta_ai_raw_paths_edit.setPlaceholderText("Embedded metadata paths...")
        self.meta_ai_raw_paths_edit.setMaximumHeight(70)

        self.lbl_notes_cap = QLabel("Notes:")
        self.meta_notes = QPlainTextEdit()
        self.meta_notes.setPlaceholderText("Personal notes...")
        self.meta_notes.setMaximumHeight(90)

        right_layout.addStretch(1)

        self.btn_clear_bulk_tags = QPushButton("Clear All Tags")
        self.btn_clear_bulk_tags.setObjectName("btnClearBulkTags")
        self.btn_clear_bulk_tags.setProperty("baseText", "Clear All Tags")
        self.btn_clear_bulk_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_bulk_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_clear_bulk_tags.clicked.connect(self._clear_bulk_tags)
        right_layout.addWidget(self.btn_clear_bulk_tags)
        self.btn_clear_bulk_tags.setVisible(False)

        self.btn_save_meta = QPushButton("Save Changes to Database")
        self.btn_save_meta.setObjectName("btnSaveMeta")
        self.btn_save_meta.setProperty("baseText", "Save Changes to Database")
        self.btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_meta.clicked.connect(self._save_native_metadata)
        self.btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.btn_save_meta)

        for attr_name, widget in self.__dict__.items():
            if not isinstance(widget, QLabel):
                continue
            if not (attr_name.startswith("lbl_") or attr_name.startswith("meta_")):
                continue
            if widget is self.preview_image_lbl:
                continue
            widget.setIndent(0)
            widget.setMargin(0)
            self._make_detail_label_copyable(widget)
            if attr_name.startswith("lbl_"):
                widget.setProperty("detailCaption", True)

        # AI/EXIF Actions
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        self.btn_import_exif = QPushButton("Import Metadata")
        self.btn_import_exif.setObjectName("btnImportExif")
        self.btn_import_exif.setProperty("baseText", "Import Metadata")
        self.btn_import_exif.setToolTip("Append tags/comments from file to database")
        self.btn_import_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_import_exif.clicked.connect(self._import_exif_to_db)
        action_layout.addWidget(self.btn_import_exif)

        self.btn_merge_hidden_meta = QPushButton("Merge Hidden Metadata Into Visible Comments Field")
        self.btn_merge_hidden_meta.setObjectName("btnMergeHiddenMeta")
        self.btn_merge_hidden_meta.setProperty("baseText", "Merge Hidden Metadata Into Visible Comments Field")
        self.btn_merge_hidden_meta.setToolTip("Write combined hidden metadata into the Windows-visible comments field using the existing embed path")
        self.btn_merge_hidden_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_merge_hidden_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_merge_hidden_meta.clicked.connect(self._merge_hidden_metadata_into_visible_comments)
        action_layout.addWidget(self.btn_merge_hidden_meta)

        self.btn_save_to_exif = QPushButton("Embed Data in File")
        self.btn_save_to_exif.setObjectName("btnSaveToExif")
        self.btn_save_to_exif.setProperty("baseText", "Embed Data in File")
        self.btn_save_to_exif.setToolTip("Write tags and comments from these fields into the file's embedded metadata")
        self.btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_to_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_save_to_exif.clicked.connect(self._save_to_exif_cmd)
        action_layout.addWidget(self.btn_save_to_exif)
        right_layout.addLayout(action_layout)

        self.meta_status_lbl = StatusTextEdit("")
        self.meta_status_lbl.setObjectName("metaStatusLabel")
        self.meta_status_lbl.setMinimumWidth(0)
        self._configure_status_text_widget(self.meta_status_lbl)
        right_layout.addWidget(self.meta_status_lbl)

        self.bulk_editor_panel = QWidget(self.right_workspace_stack)
        self.bulk_editor_panel.setObjectName("bulkTagEditorPanel")
        bulk_editor_outer_layout = QVBoxLayout(self.bulk_editor_panel)
        bulk_editor_outer_layout.setContentsMargins(12, 12, 12, 12)
        bulk_editor_outer_layout.setSpacing(8)

        self.bulk_header_lbl = QLabel("Bulk Editor")
        self.bulk_header_lbl.setObjectName("bulkTagEditorHeaderLabel")
        bulk_editor_outer_layout.addWidget(self.bulk_header_lbl)

        self.bulk_editor_mode_row = QWidget(self.bulk_editor_panel)
        self.bulk_editor_mode_row.setObjectName("bulkEditorModeRow")
        bulk_editor_mode_layout = QHBoxLayout(self.bulk_editor_mode_row)
        bulk_editor_mode_layout.setContentsMargins(0, 0, 0, 0)
        bulk_editor_mode_layout.setSpacing(8)
        self.bulk_mode_tags_btn = QPushButton("Tags")
        self.bulk_mode_tags_btn.setObjectName("bulkEditorModeButton")
        self.bulk_mode_tags_btn.setCheckable(True)
        self.bulk_mode_tags_btn.clicked.connect(lambda checked=False: self._set_active_bulk_editor_mode("tags"))
        bulk_editor_mode_layout.addWidget(self.bulk_mode_tags_btn)
        self.bulk_mode_captions_btn = QPushButton("Captions")
        self.bulk_mode_captions_btn.setObjectName("bulkEditorModeButton")
        self.bulk_mode_captions_btn.setCheckable(True)
        self.bulk_mode_captions_btn.clicked.connect(lambda checked=False: self._set_active_bulk_editor_mode("captions"))
        bulk_editor_mode_layout.addWidget(self.bulk_mode_captions_btn)
        bulk_editor_mode_layout.addStretch(1)
        bulk_editor_outer_layout.addWidget(self.bulk_editor_mode_row)

        self.bulk_pages_stack = QStackedWidget(self.bulk_editor_panel)
        self.bulk_pages_stack.setObjectName("bulkEditorPagesStack")
        bulk_editor_outer_layout.addWidget(self.bulk_pages_stack, 1)

        self.bulk_tags_page = QWidget(self.bulk_pages_stack)
        self.bulk_tags_page.setObjectName("bulkTagsPage")
        bulk_tags_page_layout = QVBoxLayout(self.bulk_tags_page)
        bulk_tags_page_layout.setContentsMargins(0, 0, 0, 0)
        bulk_tags_page_layout.setSpacing(0)

        self.bulk_scroll_area = QScrollArea()
        self.bulk_scroll_area.setWidgetResizable(True)
        self.bulk_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.bulk_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bulk_scroll_area.setObjectName("bulkTagEditorScrollArea")
        self.bulk_scroll_area.viewport().installEventFilter(self)

        self.bulk_scroll_container = QWidget(self.bulk_scroll_area)
        self.bulk_scroll_container.setObjectName("bulkTagEditorScrollContainer")
        self.bulk_right_layout = QVBoxLayout(self.bulk_scroll_container)
        self.bulk_right_layout.setContentsMargins(12, 12, 12, 12)
        self.bulk_right_layout.setSpacing(6)

        self.bulk_btn_open_tag_list = QPushButton("Open Tag Lists")
        self.bulk_btn_open_tag_list.setObjectName("bulkBtnOpenTagList")
        self.bulk_btn_open_tag_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_open_tag_list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        bulk_open_font = QFont(self.bulk_btn_open_tag_list.font())
        bulk_open_font.setBold(True)
        self.bulk_btn_open_tag_list.setFont(bulk_open_font)
        self.bulk_btn_open_tag_list.clicked.connect(self._toggle_tag_list_panel)
        self.bulk_right_layout.addWidget(self.bulk_btn_open_tag_list)

        self.bulk_selection_lbl = QLabel("")
        self.bulk_selection_lbl.setObjectName("bulkTagEditorSelectionLabel")
        self.bulk_selection_lbl.setWordWrap(True)
        self.bulk_right_layout.addWidget(self.bulk_selection_lbl)

        self.bulk_btn_select_all_gallery = QPushButton("Select All Files in Gallery")
        self.bulk_btn_select_all_gallery.setObjectName("bulkBtnSelectAllGallery")
        self.bulk_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_btn_select_all_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_select_all_gallery.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_select_all_gallery.clicked.connect(self._select_all_visible_gallery_items)
        self.bulk_right_layout.addWidget(self.bulk_btn_select_all_gallery)

        self.bulk_tags_cap_lbl = QLabel("Tags to add to all selected files:")
        self.bulk_tags_cap_lbl.setObjectName("bulkTagEditorTagsLabel")
        self.bulk_right_layout.addWidget(self.bulk_tags_cap_lbl)

        self.bulk_meta_tags = QLineEdit()
        self.bulk_meta_tags.setObjectName("bulkTagEditorTagsEdit")
        self.bulk_meta_tags.setPlaceholderText("tag1, tag2, tag3")
        self.bulk_meta_tags.editingFinished.connect(self._save_native_tags)
        self.bulk_meta_tags.textChanged.connect(lambda _text: self._refresh_tag_list_rows_state())
        self.bulk_right_layout.addWidget(self.bulk_meta_tags)

        self.bulk_common_tags_toggle = QToolButton()
        self.bulk_common_tags_toggle.setObjectName("bulkTagEditorSectionToggle")
        self.bulk_common_tags_toggle.setCheckable(True)
        self.bulk_common_tags_toggle.setChecked(False)
        self._set_bulk_tag_section_toggle(self.bulk_common_tags_toggle, "Common Tags", False)
        self.bulk_common_tags_toggle.clicked.connect(
            lambda checked: self._toggle_bulk_tag_section(self.bulk_common_tags_toggle, self.bulk_common_tags_text, checked)
        )
        self.bulk_right_layout.addWidget(self.bulk_common_tags_toggle)

        self.bulk_common_tags_text = QPlainTextEdit()
        self.bulk_common_tags_text.setObjectName("bulkTagEditorCommonTagsText")
        self.bulk_common_tags_text.setReadOnly(True)
        self.bulk_common_tags_text.setPlaceholderText("Tags present in all selected files")
        self.bulk_common_tags_text.setMaximumHeight(72)
        self.bulk_common_tags_text.setVisible(False)
        self.bulk_right_layout.addWidget(self.bulk_common_tags_text)

        self.bulk_uncommon_tags_toggle = QToolButton()
        self.bulk_uncommon_tags_toggle.setObjectName("bulkTagEditorSectionToggle")
        self.bulk_uncommon_tags_toggle.setCheckable(True)
        self.bulk_uncommon_tags_toggle.setChecked(False)
        self._set_bulk_tag_section_toggle(self.bulk_uncommon_tags_toggle, "Uncommon Tags", False)
        self.bulk_uncommon_tags_toggle.clicked.connect(
            lambda checked: self._toggle_bulk_tag_section(self.bulk_uncommon_tags_toggle, self.bulk_uncommon_tags_text, checked)
        )
        self.bulk_right_layout.addWidget(self.bulk_uncommon_tags_toggle)

        self.bulk_uncommon_tags_text = QPlainTextEdit()
        self.bulk_uncommon_tags_text.setObjectName("bulkTagEditorUncommonTagsText")
        self.bulk_uncommon_tags_text.setReadOnly(True)
        self.bulk_uncommon_tags_text.setPlaceholderText("Tags present in some, but not all, selected files")
        self.bulk_uncommon_tags_text.setMaximumHeight(96)
        self.bulk_uncommon_tags_text.setVisible(False)
        self.bulk_right_layout.addWidget(self.bulk_uncommon_tags_text)

        self.bulk_selected_files_lbl = QLabel("Selected Files:")
        self.bulk_selected_files_lbl.setObjectName("bulkTagEditorSelectedFilesLabel")
        self.bulk_right_layout.addWidget(self.bulk_selected_files_lbl)

        self.bulk_selected_files_list = BulkSelectedFilesListWidget()
        self.bulk_selected_files_list.setObjectName("bulkSelectedFilesList")
        self.bulk_selected_files_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.bulk_selected_files_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bulk_selected_files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_selected_files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.bulk_selected_files_list.setSpacing(4)
        self.bulk_selected_files_list.setMinimumHeight(120)
        self.bulk_selected_files_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bulk_selected_files_list.setViewportMargins(0, 0, 4, 0)
        self.bulk_selected_files_list.layoutSyncRequested.connect(self._sync_bulk_selected_files_layout)
        self.bulk_selected_files_list.verticalScrollBar().rangeChanged.connect(lambda _min, _max: self._queue_bulk_selected_files_layout_sync())
        self.bulk_right_layout.addWidget(self.bulk_selected_files_list, 1)

        self.bulk_status_lbl = StatusTextEdit("")
        self.bulk_status_lbl.setObjectName("bulkTagEditorStatusLabel")
        self._configure_status_text_widget(self.bulk_status_lbl)
        self.bulk_right_layout.addWidget(self.bulk_status_lbl)

        self.bulk_btn_run_local_ai = QPushButton("Generate Tags for All")
        self.bulk_btn_run_local_ai.setObjectName("bulkBtnRunLocalAI")
        self.bulk_btn_run_local_ai.setProperty("baseText", "Generate Tags for All")
        self.bulk_btn_run_local_ai.setToolTip("Run local AI tag generation for selected files")
        self.bulk_btn_run_local_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_run_local_ai.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_run_local_ai.clicked.connect(self._run_local_ai_tags)
        self.bulk_right_layout.addWidget(self.bulk_btn_run_local_ai)

        self.bulk_btn_save_meta = QPushButton("Save Tags to DB")
        self.bulk_btn_save_meta.setObjectName("bulkBtnSaveMeta")
        self.bulk_btn_save_meta.setProperty("baseText", "Save Tags to DB")
        self.bulk_btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_save_meta.clicked.connect(self._save_native_metadata)
        self.bulk_right_layout.addWidget(self.bulk_btn_save_meta)

        self.bulk_btn_clear_tags = QPushButton("Clear All Tags")
        self.bulk_btn_clear_tags.setObjectName("bulkBtnClearTags")
        self.bulk_btn_clear_tags.setProperty("baseText", "Clear All Tags")
        self.bulk_btn_clear_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_clear_tags.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_clear_tags.clicked.connect(self._clear_bulk_tags)
        self.bulk_right_layout.addWidget(self.bulk_btn_clear_tags)

        self.bulk_btn_save_to_exif = QPushButton("Embed Tags in Files")
        self.bulk_btn_save_to_exif.setObjectName("bulkBtnSaveToExif")
        self.bulk_btn_save_to_exif.setProperty("baseText", "Embed Tags in Files")
        self.bulk_btn_save_to_exif.setToolTip("Write only the entered tags into each selected file's embedded metadata")
        self.bulk_btn_save_to_exif.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_btn_save_to_exif.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_btn_save_to_exif.clicked.connect(self._save_to_exif_cmd)
        self.bulk_right_layout.addWidget(self.bulk_btn_save_to_exif)

        self.bulk_scroll_area.setWidget(self.bulk_scroll_container)
        bulk_tags_page_layout.addWidget(self.bulk_scroll_area)

        self.bulk_captions_page = QWidget(self.bulk_pages_stack)
        self.bulk_captions_page.setObjectName("bulkCaptionsPage")
        bulk_captions_page_layout = QVBoxLayout(self.bulk_captions_page)
        bulk_captions_page_layout.setContentsMargins(0, 0, 0, 0)
        bulk_captions_page_layout.setSpacing(0)

        self.bulk_caption_scroll_area = QScrollArea()
        self.bulk_caption_scroll_area.setWidgetResizable(True)
        self.bulk_caption_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.bulk_caption_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_caption_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bulk_caption_scroll_area.setObjectName("bulkCaptionEditorScrollArea")
        self.bulk_caption_scroll_area.viewport().installEventFilter(self)

        self.bulk_caption_scroll_container = QWidget(self.bulk_caption_scroll_area)
        self.bulk_caption_scroll_container.setObjectName("bulkCaptionEditorScrollContainer")
        self.bulk_caption_right_layout = QVBoxLayout(self.bulk_caption_scroll_container)
        self.bulk_caption_right_layout.setContentsMargins(12, 12, 12, 12)
        self.bulk_caption_right_layout.setSpacing(6)

        self.bulk_caption_selection_lbl = QLabel("")
        self.bulk_caption_selection_lbl.setObjectName("bulkTagEditorSelectionLabel")
        self.bulk_caption_selection_lbl.setWordWrap(True)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selection_lbl)

        self.bulk_caption_btn_select_all_gallery = QPushButton("Select All Files in Gallery")
        self.bulk_caption_btn_select_all_gallery.setObjectName("bulkBtnSelectAllGallery")
        self.bulk_caption_btn_select_all_gallery.setProperty("baseText", "Select All Files in Gallery")
        self.bulk_caption_btn_select_all_gallery.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_select_all_gallery.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_select_all_gallery.clicked.connect(self._select_all_visible_gallery_items)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_select_all_gallery)

        self.bulk_caption_selected_files_lbl = QLabel("Selected Files:")
        self.bulk_caption_selected_files_lbl.setObjectName("bulkTagEditorSelectedFilesLabel")
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selected_files_lbl)

        self.bulk_caption_selected_files_list = BulkSelectedFilesListWidget()
        self.bulk_caption_selected_files_list.setObjectName("bulkSelectedFilesList")
        self.bulk_caption_selected_files_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.bulk_caption_selected_files_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bulk_caption_selected_files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bulk_caption_selected_files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.bulk_caption_selected_files_list.setSpacing(4)
        self.bulk_caption_selected_files_list.setMinimumHeight(120)
        self.bulk_caption_selected_files_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bulk_caption_selected_files_list.setViewportMargins(0, 0, 4, 0)
        self.bulk_caption_selected_files_list.layoutSyncRequested.connect(self._sync_bulk_caption_selected_files_layout)
        self.bulk_caption_selected_files_list.verticalScrollBar().rangeChanged.connect(lambda _min, _max: self._queue_bulk_caption_selected_files_layout_sync())
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_selected_files_list, 1)

        self.bulk_caption_status_lbl = StatusTextEdit("")
        self.bulk_caption_status_lbl.setObjectName("bulkTagEditorStatusLabel")
        self._configure_status_text_widget(self.bulk_caption_status_lbl)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_status_lbl)

        self.bulk_caption_btn_run_local_ai = QPushButton("Generate Descriptions for All")
        self.bulk_caption_btn_run_local_ai.setObjectName("bulkBtnRunLocalAI")
        self.bulk_caption_btn_run_local_ai.setProperty("baseText", "Generate Descriptions for All")
        self.bulk_caption_btn_run_local_ai.setToolTip("Run local AI description generation for selected files")
        self.bulk_caption_btn_run_local_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_run_local_ai.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_run_local_ai.clicked.connect(self._run_local_ai_description)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_run_local_ai)

        self.bulk_caption_btn_save_meta = QPushButton("Save Descriptions to DB")
        self.bulk_caption_btn_save_meta.setObjectName("bulkBtnSaveMeta")
        self.bulk_caption_btn_save_meta.setProperty("baseText", "Save Descriptions to DB")
        self.bulk_caption_btn_save_meta.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_save_meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_save_meta.clicked.connect(self._save_bulk_descriptions_to_db)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_save_meta)

        self.bulk_caption_btn_clear = QPushButton("Clear Descriptions from DB")
        self.bulk_caption_btn_clear.setObjectName("bulkBtnClearTags")
        self.bulk_caption_btn_clear.setProperty("baseText", "Clear Descriptions from DB")
        self.bulk_caption_btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bulk_caption_btn_clear.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.bulk_caption_btn_clear.clicked.connect(self._clear_bulk_descriptions)
        self.bulk_caption_right_layout.addWidget(self.bulk_caption_btn_clear)

        self.bulk_caption_scroll_area.setWidget(self.bulk_caption_scroll_container)
        bulk_captions_page_layout.addWidget(self.bulk_caption_scroll_area)

        self.bulk_pages_stack.addWidget(self.bulk_tags_page)
        self.bulk_pages_stack.addWidget(self.bulk_captions_page)

        self.right_workspace_stack.addWidget(self.details_workspace)
        self.right_workspace_stack.addWidget(self.bulk_editor_panel)
        self.right_workspace_stack.setCurrentWidget(self.details_workspace)
        self._bulk_editor_mode = "tags"
        self._set_active_bulk_editor_mode("tags")
        self._sync_close_button_icons()
        self._sync_sidebar_panel_widths()

        self._update_native_styles(accent_val)
        self._update_splitter_style(accent_val)

        self._devtools: QWebEngineView | None = None
        self.video_overlay = LightboxVideoOverlay(parent=self.web)
        self.video_overlay.setGeometry(self.web.rect())
        # When native overlay closes, also close the web lightbox chrome.
        self.video_overlay.on_close = self._close_web_lightbox
        self.video_overlay.on_prev = self._on_video_prev
        self.video_overlay.on_next = self._on_video_next
        self.video_overlay.on_log = self.bridge._log
        self.video_overlay.raise_()

        self.channel = QWebChannel(self.web.page())
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)
        try:
            self.web.page().renderProcessTerminated.connect(
                lambda status, exit_code: self.bridge._log(
                    f"Web render process terminated: status={status} exit_code={int(exit_code)}"
                )
            )
        except Exception:
            pass

        index_path = Path(__file__).with_name("web") / "index.html"

        # Web loading signals (with minimum on-screen time to avoid flashing)
        self._web_loading_shown_ms: int | None = None
        self._web_loading_min_ms = 1000
        self.web.loadStarted.connect(lambda: self._set_web_loading(True))
        self.web.loadProgress.connect(self._on_web_load_progress)
        self.web.loadFinished.connect(lambda _ok: self._set_web_loading(False))
        self.web.loadFinished.connect(lambda ok: self._schedule_startup_compare_seed() if ok else None)
        self.web.loadFinished.connect(
            lambda ok: self.bridge._log(
                f"Web load finished: ok={bool(ok)} url={self.web.url().toString()}"
            )
        )

        self.web.setUrl(QUrl.fromLocalFile(str(index_path.resolve())))

        self.bottom_panel = QWidget(center_splitter)
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setMinimumHeight(0)
        self.bottom_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(14, 10, 14, 14)
        bottom_layout.setSpacing(10)

        self.bottom_panel_header_row = QWidget(self.bottom_panel)
        bottom_panel_header_layout = QHBoxLayout(self.bottom_panel_header_row)
        bottom_panel_header_layout.setContentsMargins(0, 0, 0, 0)
        bottom_panel_header_layout.setSpacing(8)

        self.bottom_panel_prev_group_btn = QPushButton("Previous Group")
        self.bottom_panel_prev_group_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_prev_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_prev_group_btn.setToolTip("Jump to Previous Group")
        self.bottom_panel_prev_group_btn.setFixedHeight(22)
        self.bottom_panel_prev_group_btn.setIcon(self._native_arrow_icon("left"))
        self.bottom_panel_prev_group_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_prev_group_btn.clicked.connect(lambda: self._jump_review_group(-1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_prev_group_btn, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_left_prev_image_btn = QPushButton("Prev Image")
        self.bottom_panel_left_prev_image_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_left_prev_image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_left_prev_image_btn.setToolTip("Load the previous image into the left comparison slot")
        self.bottom_panel_left_prev_image_btn.setFixedHeight(22)
        self.bottom_panel_left_prev_image_btn.setMaximumWidth(102)
        self.bottom_panel_left_prev_image_btn.setIcon(self._native_arrow_icon("left"))
        self.bottom_panel_left_prev_image_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_left_prev_image_btn.setEnabled(False)
        self.bottom_panel_left_prev_image_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.bottom_panel_left_prev_image_btn.clicked.connect(lambda: self._jump_review_image("left", -1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_left_prev_image_btn, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_left_next_image_btn = QPushButton("Next Image")
        self.bottom_panel_left_next_image_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_left_next_image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_left_next_image_btn.setToolTip("Load the next image into the left comparison slot")
        self.bottom_panel_left_next_image_btn.setFixedHeight(22)
        self.bottom_panel_left_next_image_btn.setMaximumWidth(102)
        self.bottom_panel_left_next_image_btn.setIcon(self._native_arrow_icon("right"))
        self.bottom_panel_left_next_image_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_left_next_image_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.bottom_panel_left_next_image_btn.setEnabled(False)
        self.bottom_panel_left_next_image_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.bottom_panel_left_next_image_btn.clicked.connect(lambda: self._jump_review_image("left", 1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_left_next_image_btn, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_header = QLabel("Image Comparison")
        self.bottom_panel_header.setObjectName("bottomPanelHeader")
        self.bottom_panel_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addWidget(self.bottom_panel_header, 0, Qt.AlignmentFlag.AlignCenter)
        bottom_panel_header_layout.addStretch(1)

        self.bottom_panel_right_prev_image_btn = QPushButton("Prev Image")
        self.bottom_panel_right_prev_image_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_right_prev_image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_right_prev_image_btn.setToolTip("Load the previous image into the right comparison slot")
        self.bottom_panel_right_prev_image_btn.setFixedHeight(22)
        self.bottom_panel_right_prev_image_btn.setMaximumWidth(102)
        self.bottom_panel_right_prev_image_btn.setIcon(self._native_arrow_icon("left"))
        self.bottom_panel_right_prev_image_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_right_prev_image_btn.setEnabled(False)
        self.bottom_panel_right_prev_image_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.bottom_panel_right_prev_image_btn.clicked.connect(lambda: self._jump_review_image("right", -1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_right_prev_image_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_right_next_image_btn = QPushButton("Next Image")
        self.bottom_panel_right_next_image_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_right_next_image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_right_next_image_btn.setToolTip("Load the next image into the right comparison slot")
        self.bottom_panel_right_next_image_btn.setFixedHeight(22)
        self.bottom_panel_right_next_image_btn.setMaximumWidth(102)
        self.bottom_panel_right_next_image_btn.setIcon(self._native_arrow_icon("right"))
        self.bottom_panel_right_next_image_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_right_next_image_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.bottom_panel_right_next_image_btn.setEnabled(False)
        self.bottom_panel_right_next_image_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.bottom_panel_right_next_image_btn.clicked.connect(lambda: self._jump_review_image("right", 1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_right_next_image_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_next_group_btn = QPushButton("Next Group")
        self.bottom_panel_next_group_btn.setObjectName("bottomPanelGroupNavButton")
        self.bottom_panel_next_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_next_group_btn.setToolTip("Jump to Next Group")
        self.bottom_panel_next_group_btn.setFixedHeight(22)
        self.bottom_panel_next_group_btn.setIcon(self._native_arrow_icon("right"))
        self.bottom_panel_next_group_btn.setIconSize(QSize(12, 12))
        self.bottom_panel_next_group_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.bottom_panel_next_group_btn.clicked.connect(lambda: self._jump_review_group(1))
        bottom_panel_header_layout.addWidget(self.bottom_panel_next_group_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.bottom_panel_close_btn = QPushButton("")
        self.bottom_panel_close_btn.setObjectName("bottomPanelCloseButton")
        self.bottom_panel_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bottom_panel_close_btn.setFixedSize(22, 22)
        self.bottom_panel_close_btn.clicked.connect(lambda: self._set_panel_setting("ui/show_bottom_panel", False))
        bottom_panel_header_layout.addWidget(self.bottom_panel_close_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addWidget(self.bottom_panel_header_row)

        self.compare_panel = ComparePanel(self.bridge, self.bottom_panel)
        bottom_layout.addWidget(self.compare_panel, 1)
        self._apply_compare_panel_theme(accent_val)

        center_splitter.addWidget(center)
        center_splitter.addWidget(self.bottom_panel)
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 0)
        center_container_layout.addWidget(center_splitter)

        splitter.addWidget(self.left_panel)
        splitter.addWidget(center_container)

        self.right_splitter.addWidget(self.tag_list_panel)
        self.right_splitter.addWidget(self.right_panel)
        self.right_splitter.setStretchFactor(0, 0)
        self.right_splitter.setStretchFactor(1, 1)

        splitter.addWidget(self.right_panel_host)
        splitter.setStretchFactor(1, 1)
        splitter.setObjectName("mainSplitter")
        splitter.setMouseTracking(True)
        splitter.setHandleWidth(7)

        self._restore_main_splitter_sizes()
        self._restore_center_splitter_sizes()
        self._restore_right_splitter_sizes()

        splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())
        center_splitter.splitterMoved.connect(lambda *args: self._on_splitter_moved())
        self.right_splitter.splitterMoved.connect(lambda *args: self._on_right_splitter_moved())

        self.setCentralWidget(splitter)

        # Apply initial style
        self._update_splitter_style(accent_val)

        # Apply right panel flag from settings
        try:
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            self._apply_ui_flag("ui.show_right_panel", show_right)
        except Exception:
            pass
        try:
            show_bottom = bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool))
            self._apply_ui_flag("ui.show_bottom_panel", show_bottom)
        except Exception:
            pass

        # Initial clear/hide based on default settings
        # Must be at the very end to ensure all UI attributes (meta_desc, etc.) are initialized.
        self._setup_metadata_layout()
        self._reload_tag_lists()
        self._sync_tag_list_panel_visibility()
        self._update_preview_visibility()
        self._clear_metadata_panel()
        self._gallery_relayout_timer = QTimer(self)
        self._gallery_relayout_timer.setSingleShot(True)
        self._gallery_relayout_timer.setInterval(90)
        self._gallery_relayout_timer.timeout.connect(self._notify_gallery_container_resized)
        QTimer.singleShot(0, self._apply_initial_web_background)
        QTimer.singleShot(0, self._schedule_gallery_container_relayout)

    def _apply_initial_web_background(self) -> None:
        # Some Windows installs abort inside Qt WebEngine if this runs during
        # synchronous layout construction. Defer it until the event loop starts.
        try:
            page = self.web.page()
            if page is None:
                self.bridge._log("Web background skipped: page unavailable")
                return
            accent_q = QColor(self._current_accent)
            page.setBackgroundColor(QColor(Theme.get_bg(accent_q)))
            self.bridge._log("Web background applied")
        except Exception as exc:
            self.bridge._log(f"Web background apply failed: {exc}")

    def _schedule_gallery_container_relayout(self, delay_ms: int = 90) -> None:
        timer = getattr(self, "_gallery_relayout_timer", None)
        if timer is None:
            return
        try:
            timer.start(max(0, int(delay_ms or 0)))
        except Exception:
            pass

    def _notify_gallery_container_resized(self) -> None:
        try:
            self.web.page().runJavaScript(
                "try{ window.__mmx_scheduleGalleryRelayout && window.__mmx_scheduleGalleryRelayout('qt'); }catch(e){}"
            )
        except Exception:
            pass

    def _set_selected_folders(self, folder_paths: list[str]) -> None:
        self.bridge.set_selected_folders(folder_paths)

    def _get_saved_panel_width(self, qkey: str, default: int) -> int:
        try:
            val = int(self.bridge.settings.value(qkey, default, type=int) or default)
        except Exception:
            val = default
        return max(120, val)

    def _get_saved_panel_height(self, qkey: str, default: int) -> int:
        try:
            val = int(self.bridge.settings.value(qkey, default, type=int) or default)
        except Exception:
            val = default
        return max(140, val)

    def _current_splitter_sizes(self) -> list[int]:
        try:
            sizes = [int(v) for v in self.splitter.sizes()]
        except Exception:
            sizes = []
        if len(sizes) < 3:
            return [
                self._DEFAULT_LEFT_PANEL_WIDTH,
                self._DEFAULT_CENTER_WIDTH,
                self._DEFAULT_RIGHT_PANEL_WIDTH,
            ]
        return sizes[:3]

    def _save_main_panel_widths(self) -> None:
        try:
            sizes = self._current_splitter_sizes()
            if self.left_panel.isVisible() and sizes[0] > 0:
                self.bridge.settings.setValue("ui/left_panel_width", int(sizes[0]))
            if self.right_panel_host.isVisible():
                self.bridge.settings.setValue("ui/right_panel_width", int(self._details_panel_width_without_tag_list()))
        except Exception:
            pass

    def _save_bottom_panel_height(self) -> None:
        try:
            if not hasattr(self, "center_splitter") or not hasattr(self, "bottom_panel"):
                return
            sizes = [int(v) for v in self.center_splitter.sizes()]
            if len(sizes) >= 2 and self.bottom_panel.isVisible() and sizes[1] > 0:
                self.bridge.settings.setValue("ui/bottom_panel_height", int(sizes[1]))
        except Exception:
            pass

    def _restore_main_splitter_sizes(self) -> None:
        try:
            show_left = bool(self.bridge.settings.value("ui/show_left_panel", True, type=bool))
            show_right = bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool))
            left_width = self._get_saved_panel_width("ui/left_panel_width", self._DEFAULT_LEFT_PANEL_WIDTH)
            right_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
            sizes = [
                left_width if show_left else 0,
                self._DEFAULT_CENTER_WIDTH,
                right_width if show_right else 0,
            ]
            self.splitter.setSizes(sizes)
        except Exception:
            pass

    def _restore_center_splitter_sizes(self) -> None:
        try:
            show_bottom = bool(self.bridge.settings.value("ui/show_bottom_panel", True, type=bool))
            bottom_height = self._get_saved_panel_height("ui/bottom_panel_height", self._DEFAULT_BOTTOM_PANEL_HEIGHT)
            sizes = [
                self._DEFAULT_CENTER_WIDTH,
                bottom_height if show_bottom else 0,
            ]
            self.center_splitter.setSizes(sizes)
        except Exception:
            pass

    def _current_right_splitter_sizes(self) -> list[int]:
        try:
            sizes = [int(v) for v in self.right_splitter.sizes()]
        except Exception:
            sizes = []
        if len(sizes) < 2:
            return [0, self._DEFAULT_RIGHT_PANEL_WIDTH]
        return sizes[:2]

    def _save_tag_list_panel_width(self) -> None:
        try:
            sizes = self._current_right_splitter_sizes()
            if self.tag_list_panel.isVisible() and sizes[0] > 0:
                self.bridge.settings.setValue("ui/tag_list_panel_width", int(sizes[0]))
        except Exception:
            pass

    def _restore_right_splitter_sizes(self) -> None:
        try:
            saved_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH), type=int) or self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)))
            details_width = saved_details_width
            tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
            show_tag_list = bool(self.bridge.settings.value("ui/show_tag_list_panel", False, type=bool)) and self._can_show_tag_list_panel()
            self.tag_list_panel.setVisible(show_tag_list)
            if show_tag_list:
                self.right_splitter.setSizes([tag_width, details_width])
            else:
                self.right_splitter.setSizes([0, details_width])
        except Exception:
            pass

    def _details_panel_width_without_tag_list(self) -> int:
        try:
            if hasattr(self, "right_panel") and self.right_panel.width() > 0:
                return max(240, int(self.right_panel.width()))
            if hasattr(self, "right_splitter") and self.tag_list_panel.isVisible():
                sizes = self._current_right_splitter_sizes()
                if len(sizes) >= 2 and sizes[1] > 0:
                    return max(240, int(sizes[1]))
        except Exception:
            pass
        return max(240, int(self.right_panel_host.width() or self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)))

    def _resize_window_for_tag_list_visibility(self, show: bool) -> None:
        if not hasattr(self, "splitter"):
            return
        sizes = self._current_splitter_sizes()
        if len(sizes) < 3:
            return
        tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
        if show:
            if not hasattr(self, "_tag_list_prev_main_sizes") or not isinstance(getattr(self, "_tag_list_prev_main_sizes", None), list):
                self._tag_list_prev_main_sizes = [int(v) for v in sizes[:3]]

            saved_hidden_details_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
            saved_tag_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", saved_hidden_details_width, type=int) or saved_hidden_details_width))
            current_details_width = max(240, self._details_panel_width_without_tag_list())
            baseline_details_width = saved_tag_details_width if self.tag_list_panel.isVisible() else saved_hidden_details_width
            details_width = max(baseline_details_width, current_details_width)
            self.bridge.settings.setValue("ui/tag_list_last_details_width", details_width)
            desired_right_width = details_width + tag_width
            current_right_width = max(0, int(sizes[2]))
            needed_extra = max(0, desired_right_width - current_right_width)
            left_width = int(sizes[0])
            center_width = int(sizes[1])
            right_width = current_right_width + needed_extra
            remaining_extra = needed_extra
            if remaining_extra > 0:
                center_shrink = min(max(0, center_width - 120), remaining_extra)
                center_width -= center_shrink
                remaining_extra -= center_shrink
            if remaining_extra > 0:
                left_shrink = min(max(0, left_width - 120), remaining_extra)
                left_width -= left_shrink
                remaining_extra -= left_shrink
            if remaining_extra > 0:
                right_width -= remaining_extra

            self.splitter.setSizes([left_width, center_width, right_width])
            self.tag_list_panel.setVisible(True)
            self.right_splitter.setSizes([tag_width, details_width])
            return

        prev_main_sizes = getattr(self, "_tag_list_prev_main_sizes", None)
        details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._DEFAULT_RIGHT_PANEL_WIDTH, type=int) or self._DEFAULT_RIGHT_PANEL_WIDTH))
        if isinstance(prev_main_sizes, list) and len(prev_main_sizes) >= 3:
            self.splitter.setSizes([int(prev_main_sizes[0]), int(prev_main_sizes[1]), int(prev_main_sizes[2])])
        else:
            current_sizes = self._current_splitter_sizes()
            if len(current_sizes) >= 3:
                left_width = int(current_sizes[0])
                center_width = int(current_sizes[1])
                right_width = int(current_sizes[2])
                target_right_width = max(240, details_width)
                released_width = max(0, right_width - target_right_width)
                if released_width > 0:
                    center_width += released_width
                right_width = target_right_width
                self.splitter.setSizes([left_width, center_width, right_width])
        self.tag_list_panel.setVisible(False)
        self.right_splitter.setSizes([0, details_width])
        self._tag_list_prev_main_sizes = None

    def _is_tag_list_panel_requested_visible(self) -> bool:
        try:
            return bool(self.bridge.settings.value("ui/show_tag_list_panel", False, type=bool))
        except Exception:
            return False

    def _update_tag_list_toggle_controls(self, visible: bool | None = None) -> None:
        is_visible = self.tag_list_panel.isVisible() if visible is None else bool(visible)
        if hasattr(self, "btn_open_tag_list"):
            self.btn_open_tag_list.setText("Close Tag List" if is_visible else "Open Tag List")
            self.btn_open_tag_list.setEnabled(bool(hasattr(self, "tag_list_open_btn_row") and self.tag_list_open_btn_row.isVisible()))
        if hasattr(self, "bulk_btn_open_tag_list"):
            self.bulk_btn_open_tag_list.setText("Close Tag Lists" if is_visible else "Open Tag Lists")
            self.bulk_btn_open_tag_list.setEnabled(True)
        if hasattr(self, "act_toggle_tag_list_panel"):
            self.act_toggle_tag_list_panel.blockSignals(True)
            self.act_toggle_tag_list_panel.setChecked(is_visible)
            self.act_toggle_tag_list_panel.blockSignals(False)
            self.act_toggle_tag_list_panel.setEnabled(True)

    def _set_tag_list_panel_requested_visible(self, visible: bool) -> None:
        self.bridge.settings.setValue("ui/show_tag_list_panel", bool(visible))
        self._sync_tag_list_panel_visibility()

    def _toggle_tag_list_panel(self) -> None:
        self._set_tag_list_panel_requested_visible(not self.tag_list_panel.isVisible())

    def _toggle_tag_list_panel_from_menu(self, checked: bool) -> None:
        if checked and not bool(self.bridge.settings.value("ui/show_right_panel", True, type=bool)):
            self.bridge.settings.setValue("ui/show_right_panel", True)
            self.bridge.uiFlagChanged.emit("ui.show_right_panel", True)
        self._set_tag_list_panel_requested_visible(bool(checked))

    def _can_show_tag_list_panel(self) -> bool:
        return bool(hasattr(self, "right_panel_host") and self.right_panel_host.isVisible())

    def _sync_tag_list_panel_visibility(self, refresh_contents: bool = True) -> None:
        if not hasattr(self, "tag_list_panel"):
            return
        should_show = self._is_tag_list_panel_requested_visible() and self._can_show_tag_list_panel()
        if not should_show:
            self._save_tag_list_panel_width()
        was_visible = self.tag_list_panel.isVisible()
        saved_hidden_details_width = self._get_saved_panel_width("ui/right_panel_width", self._DEFAULT_RIGHT_PANEL_WIDTH)
        saved_tag_details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", saved_hidden_details_width, type=int) or saved_hidden_details_width))
        tag_width = self._get_saved_panel_width("ui/tag_list_panel_width", 280)
        desired_right_width = saved_tag_details_width + tag_width
        current_right_width = max(0, int(self._current_splitter_sizes()[2] if hasattr(self, "splitter") else 0))
        needs_outer_resize = should_show and current_right_width < max(240, desired_right_width - 2)
        if should_show and (not was_visible or needs_outer_resize):
            if not was_visible:
                self.bridge.settings.setValue("ui/tag_list_last_details_width", max(saved_hidden_details_width, self._details_panel_width_without_tag_list()))
            self._resize_window_for_tag_list_visibility(True)
        elif not should_show and was_visible:
            self._resize_window_for_tag_list_visibility(False)
        self.tag_list_panel.setVisible(should_show)
        if should_show:
            self._restore_right_splitter_sizes()
            if refresh_contents:
                if was_visible:
                    self._refresh_tag_list_rows_state()
                else:
                    self._refresh_tag_list_panel()
        elif hasattr(self, "right_splitter"):
            details_width = max(240, int(self.bridge.settings.value("ui/tag_list_last_details_width", self._DEFAULT_RIGHT_PANEL_WIDTH, type=int) or self._DEFAULT_RIGHT_PANEL_WIDTH))
            self.right_splitter.setSizes([0, details_width])
        self._update_tag_list_toggle_controls(should_show)

    def _open_tag_list_panel(self) -> None:
        self._set_tag_list_panel_requested_visible(True)

    def _close_tag_list_panel(self) -> None:
        self._save_tag_list_panel_width()
        self._set_tag_list_panel_requested_visible(False)



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
