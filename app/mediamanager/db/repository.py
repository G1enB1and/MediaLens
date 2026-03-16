from __future__ import annotations

import sqlite3
from typing import Iterable

from app.mediamanager.db.collections_repo import (
    add_media_paths_to_collection,
    create_collection,
    delete_collection,
    list_collections,
    rename_collection,
)
from app.mediamanager.db.ai_metadata_repo import get_media_ai_metadata, replace_media_ai_metadata
from app.mediamanager.db.media_repo import add_media_item, list_media_in_collection, list_media_in_scope
from app.mediamanager.db.metadata_repo import get_media_metadata, upsert_media_metadata
from app.mediamanager.db.selection_state import get_selection, replace_selection
from app.mediamanager.db.tags_repo import attach_tags, list_media_tags
from app.mediamanager.metadata.models import InspectionResult
from app.mediamanager.metadata.persistence import inspect_and_persist_file, inspect_and_persist_if_supported


class MediaRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ingest_media(self, path: str, media_type: str) -> int:
        media_id = add_media_item(self.conn, path, media_type)
        inspect_and_persist_if_supported(self.conn, media_id, path, media_type)
        return media_id

    def set_selection(self, selected_roots: Iterable[str]) -> None:
        replace_selection(self.conn, selected_roots)

    def current_selection(self) -> list[str]:
        return get_selection(self.conn)

    def scoped_media(
        self,
        selected_roots: list[str] | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        roots = selected_roots if selected_roots is not None else self.current_selection()
        return list_media_in_scope(self.conn, roots, limit=limit, offset=offset)

    def list_collections(self) -> list[dict]:
        return list_collections(self.conn)

    def create_collection(self, name: str) -> dict:
        return create_collection(self.conn, name)

    def rename_collection(self, collection_id: int, name: str) -> bool:
        return rename_collection(self.conn, collection_id, name)

    def delete_collection(self, collection_id: int) -> bool:
        return delete_collection(self.conn, collection_id)

    def add_paths_to_collection(self, collection_id: int, paths: Iterable[str]) -> int:
        return add_media_paths_to_collection(self.conn, collection_id, paths)

    def collection_media(
        self,
        collection_id: int,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        return list_media_in_collection(self.conn, collection_id, limit=limit, offset=offset)

    def save_metadata(self, media_id: int, title: str | None = None, description: str | None = None, notes: str | None = None) -> None:
        upsert_media_metadata(self.conn, media_id, title=title, description=description, notes=notes)

    def load_metadata(self, media_id: int) -> dict | None:
        return get_media_metadata(self.conn, media_id)

    def save_ai_metadata(self, media_id: int, inspection: InspectionResult) -> None:
        replace_media_ai_metadata(self.conn, media_id, inspection)

    def load_ai_metadata(self, media_id: int) -> dict | None:
        return get_media_ai_metadata(self.conn, media_id)

    def inspect_and_save_ai_metadata(self, media_id: int, path: str) -> InspectionResult:
        return inspect_and_persist_file(self.conn, media_id, path)

    def add_tags(self, media_id: int, tag_names: Iterable[str]) -> None:
        attach_tags(self.conn, media_id, tag_names)

    def get_tags(self, media_id: int) -> list[str]:
        return list_media_tags(self.conn, media_id)
