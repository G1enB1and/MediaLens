from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeNavigationCollectionsMixin:
    @Slot(list)
    def set_selected_folders(self, folders: list[str]) -> None:
        if folders == self._selected_folders:
            return
        self._selected_folders = folders
        self._current_gallery_tag_scope_search = ""
        if folders:
            self._active_collection_id = None
            self._active_collection_name = ""
            self._active_smart_collection_key = ""
            self._active_smart_collection_name = ""
        try:
            # Persistent settings
            settings = app_settings()
            primary = folders[0] if folders else ""
            settings.setValue("gallery/last_folder", primary)
        except Exception:
            pass
        self.selectionChanged.emit(self._selected_folders)

    def _pinned_folders_setting_key(self) -> str:
        return "folders/pinned"

    def _normalize_pinned_folder_paths(self, folders: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                resolved = str(path_obj.absolute())
            except Exception:
                resolved = path_str
            key = resolved.replace("\\", "/").lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(resolved)
        return normalized

    def _read_pinned_folders(self) -> list[str]:
        raw_value = self.settings.value(self._pinned_folders_setting_key(), "[]", type=str)
        try:
            parsed = json.loads(str(raw_value or "[]"))
        except Exception:
            parsed = []
        if not isinstance(parsed, list):
            parsed = []
        normalized = self._normalize_pinned_folder_paths(parsed)
        if normalized != parsed:
            try:
                self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
            except Exception:
                pass
        return normalized

    def _write_pinned_folders(self, folders: list[str]) -> None:
        normalized = self._normalize_pinned_folder_paths(folders)
        self.settings.setValue(self._pinned_folders_setting_key(), json.dumps(normalized))
        self.settings.sync()
        self.pinnedFoldersChanged.emit(normalized)

    @Slot(result=list)
    def list_pinned_folders(self) -> list:
        return self._read_pinned_folders()

    @Slot(str, result=bool)
    def is_folder_pinned(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        return any(path.replace("\\", "/").lower() == target_key for path in self._read_pinned_folders())

    @Slot(str, result=bool)
    def pin_folder(self, folder_path: str) -> bool:
        return self.pin_folders([folder_path]) > 0

    @Slot(list, result=int)
    def pin_folders(self, folders: list[str]) -> int:
        existing = self._read_pinned_folders()
        existing_keys = {path.replace("\\", "/").lower() for path in existing}
        added_count = 0
        for raw_path in folders or []:
            path_str = str(raw_path or "").strip()
            if not path_str:
                continue
            try:
                path_obj = Path(path_str)
                if not path_obj.exists() or not path_obj.is_dir():
                    continue
                normalized = str(path_obj.absolute())
            except Exception:
                continue
            key = normalized.replace("\\", "/").lower()
            if key in existing_keys:
                continue
            existing.append(normalized)
            existing_keys.add(key)
            added_count += 1
        if added_count:
            self._write_pinned_folders(existing)
        return added_count

    @Slot(str, result=bool)
    def unpin_folder(self, folder_path: str) -> bool:
        target = str(folder_path or "").strip()
        if not target:
            return False
        try:
            target = str(Path(target).absolute())
        except Exception:
            pass
        target_key = target.replace("\\", "/").lower()
        existing = self._read_pinned_folders()
        remaining = [path for path in existing if path.replace("\\", "/").lower() != target_key]
        if remaining == existing:
            return False
        self._write_pinned_folders(remaining)
        return True

    @Slot(list)
    def set_drag_paths(self, paths: list[str]) -> None:
        """Called from JS to register the actual files being dragged."""
        self.drag_paths = [str(p) for p in paths]
        if not self.drag_paths:
            self.drag_target_folder = ""

    @Slot(str)
    def set_drag_target_folder(self, folder_path: str) -> None:
        self.drag_target_folder = str(folder_path or "")

    @Slot(int, bool, str)
    def update_drag_tooltip(self, count: int, is_copy: bool, target_folder: str) -> None:
        self.updateTooltipRequested.emit(count, is_copy, target_folder)

    @Slot()
    def hide_drag_tooltip(self) -> None:
        self.hideTooltipRequested.emit()

    @Slot(result=list)
    def get_selected_folders(self) -> list:
        return self._selected_folders

    @Slot(str, str)
    def set_current_gallery_scope_state(self, filter_type: str, search_query: str) -> None:
        next_filter = str(filter_type or "all")
        next_search = str(search_query or "")
        if next_filter == self._current_gallery_filter and next_search == self._current_gallery_search:
            return
        self._current_gallery_filter = next_filter
        self._current_gallery_search = next_search
        self._current_gallery_tag_scope_search = ""
        self.galleryScopeChanged.emit()

    @Slot(str)
    def set_current_gallery_tag_scope_state(self, search_query: str) -> None:
        next_search = str(search_query or "")
        if next_search == self._current_gallery_tag_scope_search:
            return
        self._current_gallery_tag_scope_search = next_search
        self.galleryScopeChanged.emit()

    def _current_gallery_filter_uses_text(self) -> bool:
        _, text_filter, _, _, _ = self._parse_filter_groups(getattr(self, "_current_gallery_filter", "all"))
        return text_filter in {"text_detected", "no_text_detected"}

    def _current_gallery_filter_uses_ai(self) -> bool:
        _, _, _, _, ai_filter = self._parse_filter_groups(getattr(self, "_current_gallery_filter", "all"))
        return ai_filter in {"ai_generated", "non_ai"}

    @Slot(result="QVariantMap")
    def get_navigation_state(self) -> dict:
        current_path = self._selected_folders[0] if self._selected_folders else ""
        can_up = False
        if current_path:
            try:
                parent = Path(current_path).parent
                can_up = str(parent) != str(Path(current_path))
            except Exception:
                can_up = False
        return {
            "canBack": self._can_nav_back,
            "canForward": self._can_nav_forward,
            "canUp": can_up,
            "currentPath": current_path,
        }

    def emit_navigation_state(self) -> None:
        state = self.get_navigation_state()
        self.navigationStateChanged.emit(
            bool(state.get("canBack")),
            bool(state.get("canForward")),
            bool(state.get("canUp")),
            str(state.get("currentPath", "")),
        )

    def _list_child_folders_impl(self, folder_path: str) -> list:
        try:
            root = Path(str(folder_path or ""))
            if not root.exists() or not root.is_dir():
                return []
            children: list[dict] = []
            for child in root.iterdir():
                try:
                    if not child.is_dir():
                        continue
                    children.append({
                        "name": child.name or str(child),
                        "path": str(child),
                    })
                except Exception:
                    continue
            children.sort(key=lambda item: str(item.get("name", "")).lower())
            return children
        except Exception:
            return []

    @Slot(str, result=list)
    def list_child_folders(self, folder_path: str) -> list:
        return self._list_child_folders_impl(folder_path)

    @Slot(str, str)
    def list_child_folders_async(self, request_id: str, folder_path: str) -> None:
        req = str(request_id or "")
        path = str(folder_path or "")

        def work() -> None:
            items = self._list_child_folders_impl(path)
            self.childFoldersListed.emit(req, items)

        threading.Thread(target=work, daemon=True).start()

    @Slot(int, result=bool)
    def set_active_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import get_collection
        try:
            collection = get_collection(self.conn, int(collection_id))
            if not collection:
                return False
            self._active_collection_id = int(collection["id"])
            self._active_collection_name = str(collection["name"])
            self._active_smart_collection_key = ""
            self._active_smart_collection_name = ""
            self._selected_folders = []
            self.selectionChanged.emit([])
            return True
        except Exception:
            return False

    @Slot(result=dict)
    def get_active_collection(self) -> dict:
        if self._active_collection_id is not None:
            return {"id": self._active_collection_id, "name": self._active_collection_name}
        if self._active_smart_collection_key:
            return {"id": -1, "name": self._active_smart_collection_name, "key": self._active_smart_collection_key, "smart": True}
        return {}

    def _smart_collection_defs(self) -> list[dict]:
        return [
            {"key": "acquired_7d", "name": "Acquired Last 7 Days", "field": "metadata_date", "days": 7},
            {"key": "acquired_14d", "name": "Acquired Last 14 Days", "field": "metadata_date", "days": 14},
            {"key": "acquired_30d", "name": "Acquired Last 30 Days", "field": "metadata_date", "days": 30},
            {"key": "modified_7d", "name": "Modified Last 7 Days", "field": "modified_time_utc", "days": 7},
            {"key": "modified_14d", "name": "Modified Last 14 Days", "field": "modified_time_utc", "days": 14},
            {"key": "modified_30d", "name": "Modified Last 30 Days", "field": "modified_time_utc", "days": 30},
            {"key": "no_tags", "name": "No Tags", "field": "no_tags"},
            {"key": "no_description", "name": "No Description", "field": "no_description"},
            {"key": "large_3mb", "name": "Larger Than 3 MB", "field": "file_size_gt_3mb"},
            {"key": "large_10mb", "name": "Larger Than 10 MB", "field": "file_size_gt_10mb"},
            {"key": "large_25mb", "name": "Larger Than 25 MB", "field": "file_size_gt_25mb"},
            {"key": "large_100mb", "name": "Larger Than 100 MB", "field": "file_size_gt_100mb"},
            {"key": "large_1gb", "name": "Larger Than 1 GB", "field": "file_size_gt_1gb"},
        ]

    def _smart_collection_def(self, key: str) -> dict | None:
        wanted = str(key or "").strip().lower()
        if not wanted:
            return None
        return next((item for item in self._smart_collection_defs() if str(item.get("key") or "").lower() == wanted), None)

    def _smart_collection_cutoff_iso(self, days: int) -> str:
        try:
            count = max(1, int(days or 0))
        except Exception:
            count = 7
        return (datetime.now(timezone.utc) - timedelta(days=count)).replace(microsecond=0).isoformat()

    @Slot(str, result=bool)
    def set_active_smart_collection(self, smart_key: str) -> bool:
        try:
            definition = self._smart_collection_def(str(smart_key or ""))
            if not definition:
                return False
            self._active_smart_collection_key = str(definition["key"])
            self._active_smart_collection_name = str(definition["name"])
            self._active_collection_id = None
            self._active_collection_name = ""
            self._selected_folders = []
            self.selectionChanged.emit([])
            return True
        except Exception:
            return False

    @Slot(result=dict)
    def get_active_smart_collection(self) -> dict:
        if not self._active_smart_collection_key:
            return {}
        return {"key": self._active_smart_collection_key, "name": self._active_smart_collection_name}

    @Slot(result=list)
    def list_smart_collections(self) -> list:
        from app.mediamanager.db.media_repo import count_media_in_smart_collection
        items: list[dict] = []
        try:
            for definition in self._smart_collection_defs():
                cutoff_iso = self._smart_collection_cutoff_iso(int(definition.get("days") or 0))
                count = count_media_in_smart_collection(self.conn, str(definition.get("field") or ""), cutoff_iso)
                items.append({
                    "key": str(definition.get("key") or ""),
                    "name": str(definition.get("name") or ""),
                    "field": str(definition.get("field") or ""),
                    "days": int(definition.get("days") or 0),
                    "item_count": int(count or 0),
                })
            return items
        except Exception:
            return []

    @Slot(result=list)
    def list_collections(self) -> list:
        from app.mediamanager.db.collections_repo import list_collections
        try:
            return list_collections(self.conn)
        except Exception:
            return []

    @Slot(str, result=dict)
    def create_collection(self, name: str) -> dict:
        from app.mediamanager.db.collections_repo import create_collection
        try:
            created = create_collection(self.conn, name)
            self.collectionsChanged.emit()
            return created
        except Exception:
            return {}

    @Slot(int, str, result=bool)
    def rename_collection(self, collection_id: int, name: str) -> bool:
        from app.mediamanager.db.collections_repo import rename_collection, get_collection
        try:
            ok = rename_collection(self.conn, int(collection_id), name)
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                collection = get_collection(self.conn, int(collection_id))
                self._active_collection_name = str(collection["name"]) if collection else ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, result=bool)
    def delete_collection(self, collection_id: int) -> bool:
        from app.mediamanager.db.collections_repo import delete_collection
        try:
            ok = delete_collection(self.conn, int(collection_id))
            if not ok:
                return False
            if self._active_collection_id == int(collection_id):
                self._active_collection_id = None
                self._active_collection_name = ""
                self.selectionChanged.emit([])
            self.collectionsChanged.emit()
            return True
        except Exception:
            return False

    @Slot(int, list, result=int)
    def add_paths_to_collection(self, collection_id: int, paths: list[str]) -> int:
        from app.mediamanager.db.collections_repo import add_media_paths_to_collection
        try:
            added = add_media_paths_to_collection(self.conn, int(collection_id), paths)
            self.collectionsChanged.emit()
            if added and self._active_collection_id == int(collection_id):
                self.selectionChanged.emit([])
            return int(added)
        except Exception:
            return 0

    @Slot(list, result=bool)
    def add_paths_to_collection_interactive(self, paths: list[str]) -> bool:
        from app.mediamanager.db.collections_repo import create_collection, list_collections
        clean_paths = [str(path or "").strip() for path in paths if str(path or "").strip()]
        if not clean_paths:
            return False
        try:
            collections = list_collections(self.conn)
            options = ["New collection..."] + [str(collection["name"]) for collection in collections]
            choice, ok = _run_themed_item_input_dialog(
                None,
                "Add to Collection",
                "Collection:",
                options,
                current=0,
                editable=False,
            )
            if not ok or not choice:
                return False

            if choice == "New collection...":
                name, created_ok = _run_themed_text_input_dialog(None, "New Collection", "Collection Name:")
                if not created_ok or not name.strip():
                    return False
                created = create_collection(self.conn, name)
                collection_id = int(created["id"])
            else:
                selected = next((c for c in collections if str(c["name"]) == choice), None)
                if not selected:
                    return False
                collection_id = int(selected["id"])

            added = self.add_paths_to_collection(collection_id, clean_paths)
            return added > 0
        except Exception:
            return False



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
