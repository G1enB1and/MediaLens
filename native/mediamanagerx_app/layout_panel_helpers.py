from __future__ import annotations


def left_section_default_expanded_height(key: str) -> int:
    return {
        "pinned": 140,
        "folders": 260,
        "collections": 150,
        "smart_collections": 150,
    }.get(key, 150)


def left_section_min_expanded_height(key: str, collapsed_height: int) -> int:
    if key == "pinned":
        return max(collapsed_height + 52, 88)
    return max(collapsed_height + 40, 72)
