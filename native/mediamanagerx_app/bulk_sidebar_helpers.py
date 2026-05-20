from __future__ import annotations


def bulk_selected_file_tags_text(tags: list[str]) -> str:
    clean = [str(tag or "").strip() for tag in list(tags or []) if str(tag or "").strip()]
    return ", ".join(clean)


def is_valid_bulk_selected_file_row(row, row_type) -> bool:
    if not isinstance(row, row_type):
        return False
    try:
        import shiboken6

        return bool(shiboken6.isValid(row))
    except Exception:
        return True
