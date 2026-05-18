from __future__ import annotations

import shutil
from pathlib import Path

from app.mediamanager.utils.pathing import normalize_windows_path
from native.mediamanagerx_app.action_history import make_history_item
from native.mediamanagerx_app.common import send_to_recycle_bin


def perform_delete(conn, settings, path_str: str, *, permanent: bool = False) -> tuple[bool, dict]:
    p = Path(path_str)
    if not p.exists():
        return (
            False,
            make_history_item(
                old_path=path_str,
                item_type="folder" if p.is_dir() else "file",
                result="failed",
                notes="Path no longer exists.",
            ),
        )

    was_dir = p.is_dir()
    retention_id = ""
    use_medialens_retention = False
    use_recycle = False
    note = ""

    if permanent:
        if was_dir:
            shutil.rmtree(str(p))
        else:
            p.unlink()
        note = "Permanent delete is not undoable."
    else:
        use_medialens_retention = bool(settings.value("gallery/use_medialens_retention", False, type=bool))
        use_recycle = bool(settings.value("gallery/use_recycle_bin", True, type=bool))
        if use_medialens_retention:
            from native.mediamanagerx_app.recycle_bin import move_to_recycle_bin_with_id

            days = int(settings.value("gallery/medialens_retention_days", 30, type=int))
            retention_id = move_to_recycle_bin_with_id(path_str, days)
            if not retention_id and p.exists():
                if was_dir:
                    shutil.rmtree(str(p))
                else:
                    p.unlink()
                note = "Delete is not restorable from MediaLens retention."
        elif use_recycle:
            deleted = send_to_recycle_bin(path_str)
            if not deleted and p.exists():
                if was_dir:
                    shutil.rmtree(str(p))
                else:
                    p.unlink()
                note = "System Recycle Bin failed; item was permanently deleted."
            else:
                note = "Delete is not restorable from MediaLens retention."
        else:
            if was_dir:
                shutil.rmtree(str(p))
            else:
                p.unlink()
            note = "Delete is not restorable from MediaLens retention."

    normalized = normalize_windows_path(path_str)
    if was_dir:
        conn.execute("DELETE FROM media_items WHERE path = ? OR path LIKE ?", (normalized, f"{normalized}/%"))
    else:
        conn.execute("DELETE FROM media_items WHERE path = ?", (normalized,))
    conn.commit()

    return (
        True,
        make_history_item(
            old_path=path_str,
            item_type="folder" if was_dir else "file",
            retention_id=retention_id,
            result="success",
            notes=note,
        ),
    )

