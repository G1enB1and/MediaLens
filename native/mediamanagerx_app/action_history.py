from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.mediamanager.db import action_history_repo


ACTION_LABELS = {
    "delete": "Deleted",
    "move": "Moved",
    "copy": "Copied",
    "rename": "Renamed",
    "create_folder": "Created folder",
}


def item_type_for_path(path: str) -> str:
    try:
        return "folder" if Path(path).is_dir() else "file"
    except Exception:
        return "file"


def plural_items(count: int) -> str:
    return "1 item" if int(count or 0) == 1 else f"{int(count or 0)} items"


def action_summary(action_type: str, count: int, *, name: str = "") -> str:
    count = int(count or 0)
    if action_type == "rename" and name:
        return f'Renamed "{name}"'
    if action_type == "create_folder" and name:
        return f'Created folder "{name}"'
    label = ACTION_LABELS.get(action_type, action_type.replace("_", " ").title())
    return f"{label} {plural_items(count)}"


def result_status(items: list[dict]) -> str:
    if not items:
        return "failed"
    successes = sum(1 for item in items if str(item.get("result") or "") == "success")
    if successes == len(items):
        return "success"
    if successes:
        return "partial"
    return "failed"


def make_history_item(
    *,
    old_path: str = "",
    new_path: str = "",
    item_type: str = "",
    retention_id: str = "",
    result: str = "success",
    notes: str = "",
) -> dict:
    path = new_path or old_path
    return {
        "item_type": item_type or item_type_for_path(path),
        "old_path": old_path,
        "new_path": new_path,
        "retention_id": retention_id,
        "result": result,
        "current_state": "applied" if result == "success" else "failed",
        "last_change_source": "original_action",
        "notes": notes,
    }


def record_user_action(
    conn,
    *,
    action_type: str,
    items: list[dict],
    summary: str = "",
    metadata: dict | None = None,
    undo_state: str | None = None,
) -> int:
    status = result_status(items)
    if not summary:
        summary = action_summary(action_type, sum(1 for item in items if item.get("result") == "success"))
    action_history_repo.clear_redo_stack(conn)
    return action_history_repo.create_entry(
        conn,
        action_type=action_type,
        summary=summary,
        items=items,
        origin="user",
        status=status,
        undo_state=undo_state,
        metadata=metadata,
    )


def update_media_path_after_restore(conn, old_path: str, new_path: str, item_type: str) -> None:
    from app.mediamanager.db.media_repo import move_directory_in_db, rename_media_path

    try:
        if str(item_type or "") == "folder":
            move_directory_in_db(conn, old_path, new_path)
        else:
            rename_media_path(conn, old_path, new_path)
    except Exception:
        pass


def delete_path_for_undo(path: str) -> bool:
    p = Path(path)
    if not p.exists():
        return True
    if p.is_dir():
        shutil.rmtree(str(p))
    else:
        p.unlink()
    return True


def move_path(src: str, dst: str) -> bool:
    src_p = Path(src)
    dst_p = Path(dst)
    if not src_p.exists():
        return False
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    if dst_p.exists():
        return False
    shutil.move(str(src_p), str(dst_p))
    return True


def restore_retained_path(retention_id: str) -> bool:
    from native.mediamanagerx_app.recycle_bin import restore_from_recycle_bin

    return restore_from_recycle_bin(str(retention_id or ""))


def retain_path(path: str, days: int) -> str:
    from native.mediamanagerx_app.recycle_bin import move_to_recycle_bin_with_id

    return str(move_to_recycle_bin_with_id(path, int(days or 30)) or "")


def parent_folder(path: str) -> str:
    try:
        return str(Path(path).parent)
    except Exception:
        return ""


def path_exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except Exception:
        return False


def retained_path_available(retention_id: str) -> bool:
    if not str(retention_id or "").strip():
        return False
    try:
        from native.mediamanagerx_app.recycle_bin import get_recycle_bin_dir, init_recycle_bin_db

        conn = init_recycle_bin_db()
        try:
            row = conn.execute(
                "SELECT archived_name FROM recycle_bin WHERE id = ?",
                (str(retention_id),),
            ).fetchone()
        finally:
            conn.close()
        return bool(row and (get_recycle_bin_dir() / str(row[0] or "")).exists())
    except Exception:
        return False


def validate_history_item_availability(
    entry: dict,
    item: dict,
    *,
    path_exists_fn=path_exists,
    retained_exists_fn=retained_path_available,
    media_exists_fn=None,
) -> tuple[str | None, str | None, str | None]:
    action_type = str(entry.get("action_type") or "")
    state = str(item.get("current_state") or "")
    old_path = str(item.get("old_path") or "")
    new_path = str(item.get("new_path") or "")
    retention_id = str(item.get("retention_id") or "")

    def exists(path: str) -> bool:
        return bool(path and path_exists_fn(path))

    def media_exists(path: str) -> bool:
        if media_exists_fn is None:
            return exists(path)
        return bool(path and media_exists_fn(path))

    if state == "applied":
        if action_type in {"move", "rename"}:
            if not exists(new_path):
                if exists(old_path):
                    return "undone", "external_change", "Already appears restored outside MediaLens."
                return "unavailable", None, "Undo not available: destination item no longer exists."
            if exists(old_path):
                return "unavailable", None, "Undo not available: original path is already occupied."
        elif action_type == "copy":
            if not exists(new_path):
                return "undone", "external_change", "Copied item no longer exists; marked as already undone."
        elif action_type == "create_folder":
            target = Path(new_path)
            if not exists(new_path):
                return "undone", "external_change", "Folder no longer exists; marked as already undone."
            try:
                if not target.is_dir() or any(target.iterdir()):
                    return "unavailable", None, "Undo not available: folder is no longer empty."
            except Exception:
                return "unavailable", None, "Undo not available: folder could not be checked."
        elif action_type == "delete":
            if exists(old_path):
                return "undone", "external_change", "Item already appears restored outside MediaLens."
            if not retained_exists_fn(retention_id):
                return "unavailable", None, "Undo not available: file no longer exists in MediaLens retention."
        elif action_type in {"metadata", "rotate"}:
            if not media_exists(old_path):
                return "unavailable", None, "Undo not available: media item no longer exists in the library."

    if state == "undone":
        if action_type in {"move", "rename"}:
            if exists(new_path) and not exists(old_path):
                return "applied", "external_change", "Item already appears reapplied outside MediaLens."
            if not exists(old_path):
                return "unavailable", None, "Redo not available: original item no longer exists."
            if exists(new_path):
                return "unavailable", None, "Redo not available: destination path is already occupied."
        elif action_type == "copy":
            if exists(new_path):
                return "applied", "external_change", "Copied item already exists again."
            if not exists(old_path):
                return "unavailable", None, "Redo not available: source item no longer exists."
        elif action_type == "create_folder":
            if exists(new_path):
                return "applied", "external_change", "Folder already exists again."
        elif action_type == "delete":
            if not exists(old_path):
                if retained_exists_fn(retention_id):
                    return "applied", "external_change", "Item already appears deleted into MediaLens retention."
                return "unavailable", None, "Redo not available: item no longer exists."
        elif action_type in {"metadata", "rotate"}:
            if not media_exists(old_path):
                return "unavailable", None, "Redo not available: media item no longer exists in the library."

    return None, None, None
