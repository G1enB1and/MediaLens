from __future__ import annotations

import json
import re
from math import gcd
from pathlib import Path
from typing import Any, Callable

from app.mediamanager.utils.pathing import normalize_windows_path


def normalized_review_pair(path_a: str, path_b: str) -> tuple[str, str] | None:
    left = normalize_windows_path(path_a)
    right = normalize_windows_path(path_b)
    if not left or not right or left == right:
        return None
    return (left, right) if left < right else (right, left)


def load_review_pair_exclusions(conn, entries: list[dict], review_mode: str) -> set[tuple[str, str]]:
    from app.mediamanager.db.media_repo import list_review_pair_exclusions

    paths = [str(entry.get("path") or "").strip() for entry in entries if str(entry.get("path") or "").strip()]
    if not paths:
        return set()
    return list_review_pair_exclusions(conn, review_mode, paths=paths)


def is_review_pair_excluded(
    excluded_pairs: set[tuple[str, str]],
    left_path: str,
    right_path: str,
) -> bool:
    pair = normalized_review_pair(left_path, right_path)
    return bool(pair and pair in excluded_pairs)


def split_duplicate_group_components(
    group_entries: list[dict],
    excluded_pairs: set[tuple[str, str]],
) -> list[list[dict]]:
    if len(group_entries) < 2:
        return []

    parents = list(range(len(group_entries)))

    def find(idx: int) -> int:
        while parents[idx] != idx:
            parents[idx] = parents[parents[idx]]
            idx = parents[idx]
        return idx

    def union(left_idx: int, right_idx: int) -> None:
        left_root = find(left_idx)
        right_root = find(right_idx)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_idx, left_entry in enumerate(group_entries):
        left_path = str(left_entry.get("path") or "")
        if not left_path:
            continue
        for right_idx in range(left_idx + 1, len(group_entries)):
            right_path = str(group_entries[right_idx].get("path") or "")
            if not right_path or is_review_pair_excluded(excluded_pairs, left_path, right_path):
                continue
            union(left_idx, right_idx)

    components: dict[int, list[dict]] = {}
    for index, entry in enumerate(group_entries):
        components.setdefault(find(index), []).append(entry)
    return [component for component in components.values() if len(component) > 1]


def folder_depth_for_duplicate(entry: dict) -> int:
    try:
        parent = Path(str(entry.get("path", ""))).parent
        parts = [part for part in parent.parts if part not in ("\\", "/")]
        return len(parts)
    except Exception:
        return 0


def duplicate_parent_folder(entry: dict) -> str:
    path = str(entry.get("path") or "").strip()
    if not path:
        return ""
    try:
        return normalize_windows_path(str(Path(path).parent)).rstrip("/")
    except Exception:
        return ""


def preferred_folder_priority_state(settings) -> tuple[bool, list[str], dict[str, int]]:
    enabled = bool(settings.value("duplicate/rules/preferred_folders_enabled", False, type=bool))
    raw_value = str(settings.value("duplicate/rules/preferred_folders_order", "[]", type=str) or "[]")
    sentinel = "All other Folders"
    try:
        parsed = json.loads(raw_value)
    except Exception:
        parsed = []
    order: list[str] = []
    seen: set[str] = set()
    for item in parsed if isinstance(parsed, list) else []:
        text = str(item or "").strip()
        if not text:
            continue
        if text == sentinel:
            key = "__sentinel__"
            normalized = sentinel
        else:
            normalized = normalize_windows_path(text).rstrip("/")
            if not normalized:
                continue
            key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        order.append(normalized)
    if sentinel not in order:
        order.append(sentinel)
    sentinel_index = order.index(sentinel)
    score_by_folder = {
        folder: sentinel_index - index
        for index, folder in enumerate(order)
        if folder != sentinel
    }
    return enabled, order, score_by_folder


def preferred_folder_score(entry: dict, *, enabled: bool, score_by_folder: dict[str, int]) -> int:
    if not enabled:
        return 0
    current = duplicate_parent_folder(entry)
    while current:
        score = score_by_folder.get(current)
        if score is not None:
            return int(score)
        parent = normalize_windows_path(str(Path(current).parent)).rstrip("/")
        if not parent or parent == current:
            break
        current = parent
    return 0


def duplicate_metadata_score(entry: dict) -> tuple[int, int]:
    tags = [tag.strip() for tag in str(entry.get("tags") or "").split(",") if tag.strip()]
    filled_fields = sum(
        1
        for key in ("title", "description", "notes", "collection_names", "ai_prompt", "ai_loras", "model_name")
        if str(entry.get(key) or "").strip()
    )
    return (len(set(tags)), filled_fields)


def split_distinct_text_blocks(values: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for raw in values:
        text = str(raw or "").replace("\r\n", "\n").strip()
        if not text:
            continue
        blocks = re.split(r"\n\s*\n+", text)
        for block in blocks:
            normalized = block.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    return merged


def merge_duplicate_text_field(values: list[str]) -> str:
    return "\n\n".join(split_distinct_text_blocks(values))


def merge_duplicate_scalar_field(values: list[str]) -> str:
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        return value
    return ""


def duplicate_score(entry: dict) -> tuple:
    color_rank = 1 if str(entry.get("color_variant") or "") == "color" else 0
    folder_depth = folder_depth_for_duplicate(entry)
    tag_count, filled_fields = duplicate_metadata_score(entry)
    file_size = int(entry.get("file_size") or 0)
    modified_time = int(entry.get("preferred_date") or 0)
    return (
        color_rank,
        folder_depth,
        tag_count,
        filled_fields,
        file_size,
        modified_time,
        str(entry.get("path", "")).lower(),
    )


def sort_duplicate_group(
    entries: list[dict],
    *,
    annotate_group_color_variants: Callable[[list[dict]], None],
) -> list[dict]:
    ranked = [dict(entry) for entry in entries]
    annotate_group_color_variants(ranked)
    ranked.sort(key=duplicate_score, reverse=True)
    metadata_scores = [duplicate_metadata_score(entry) for entry in ranked]
    folder_depths = [folder_depth_for_duplicate(entry) for entry in ranked]
    file_sizes = [int(entry.get("file_size") or 0) for entry in ranked]
    modified_times = [int(entry.get("preferred_date") or 0) for entry in ranked]
    color_modes = [str(entry.get("color_variant") or "") for entry in ranked]
    best_metadata = max(metadata_scores, default=(0, 0))
    best_folder_depth = max(folder_depths, default=0)
    largest_file_size = max(file_sizes, default=0)
    smallest_file_size = min(file_sizes, default=0)
    best_modified = max(modified_times, default=0)
    preferred_folder_scores = [int(entry.get("duplicate_preferred_folder_score") or 0) for entry in ranked]
    best_preferred_folder_score = max(preferred_folder_scores, default=0)
    has_color_variants = "color" in color_modes and "grayscale" in color_modes
    unique_best_metadata = metadata_scores.count(best_metadata) == 1 and best_metadata > (0, 0)
    unique_best_folder = folder_depths.count(best_folder_depth) == 1 and best_folder_depth > 1
    unique_largest_file = file_sizes.count(largest_file_size) == 1 and largest_file_size > smallest_file_size
    unique_smallest_file = file_sizes.count(smallest_file_size) == 1 and largest_file_size > smallest_file_size
    unique_best_modified = modified_times.count(best_modified) == 1 and best_modified > 0
    preferred_folder_winner_exists = best_preferred_folder_score > 0
    for index, entry in enumerate(ranked):
        entry["duplicate_keep_suggestion"] = index == 0
        entry["duplicate_group_position"] = index
        entry["duplicate_folder_depth"] = folder_depth_for_duplicate(entry)
        reasons: list[str] = []
        if has_color_variants:
            if str(entry.get("color_variant") or "") == "color":
                reasons.append("Color version")
            elif str(entry.get("color_variant") or "") == "grayscale":
                reasons.append("Grayscale version")
        if unique_best_metadata and duplicate_metadata_score(entry) == best_metadata:
            reasons.append("Most metadata")
        if unique_best_folder and folder_depth_for_duplicate(entry) == best_folder_depth:
            reasons.append("Best folder organization")
        if preferred_folder_winner_exists and int(entry.get("duplicate_preferred_folder_score") or 0) == best_preferred_folder_score:
            reasons.append("Preferred Folder")
        if unique_largest_file and int(entry.get("file_size") or 0) == largest_file_size:
            reasons.append("Largest file size")
        if unique_smallest_file and int(entry.get("file_size") or 0) == smallest_file_size:
            reasons.append("Smallest file size")
        if unique_best_modified and int(entry.get("preferred_date") or 0) == best_modified:
            reasons.append("Newest edit")
        entry["duplicate_category_reasons"] = reasons
        entry["duplicate_best_reason"] = f" {chr(8226)} ".join(reasons)
        entry["duplicate_is_overall_best"] = index == 0
    return ranked


def rank_duplicate_group(
    entries: list[dict],
    *,
    settings,
    annotate_group_color_variants: Callable[[list[dict]], None],
    iso_to_ns: Callable[[Any], int],
    original_file_date_ns: Callable[[dict], int],
    preferred_date_ns: Callable[[dict], int],
    extra_positive_categories: list[dict[str, Any]] | None = None,
) -> list[dict]:
    ranked = [dict(entry) for entry in entries]
    annotate_group_color_variants(ranked)

    crop_policy = str(settings.value("duplicate/rules/crop_policy", "prefer_full", type=str) or "prefer_full")
    color_policy = str(settings.value("duplicate/rules/color_policy", "prefer_color", type=str) or "prefer_color")
    file_size_policy = str(settings.value("duplicate/rules/file_size_policy", "prefer_largest", type=str) or "prefer_largest")
    format_order_raw = str(settings.value("duplicate/rules/format_order", "[]", type=str) or "[]")
    priorities_raw = str(settings.value("duplicate/priorities/order", "[]", type=str) or "[]")
    try:
        format_order = [str(item).strip().upper() for item in json.loads(format_order_raw or "[]") if str(item).strip()]
    except Exception:
        format_order = []
    if not format_order:
        format_order = ["PNG", "WEBP", "JPEG", "RAW", "TIFF", "BMP", "GIF", "HEIC", "AVIF"]
    try:
        configured_priorities = [str(item).strip() for item in json.loads(priorities_raw or "[]") if str(item).strip()]
    except Exception:
        configured_priorities = []
    default_priorities = [
        "File Size",
        "Resolution",
        "File Format",
        "Preferred Folders",
        "Most metadata",
        "Compression",
        "Color / Grey Preference",
        "Text / No Text Preference",
        "Cropped / Full Preference",
    ]
    if not configured_priorities:
        configured_priorities = list(default_priorities)
    else:
        seen_priorities = {item.casefold() for item in configured_priorities}
        for item in default_priorities:
            if item.casefold() not in seen_priorities:
                configured_priorities.append(item)
                seen_priorities.add(item.casefold())
    preferred_folders_enabled, _preferred_folder_order, preferred_folder_scores = preferred_folder_priority_state(settings)

    def _normalized_aspect_ratio(entry: dict) -> tuple[int, int] | None:
        width = int(entry.get("width") or 0)
        height = int(entry.get("height") or 0)
        if width <= 0 or height <= 0 or entry.get("media_type") != "image":
            return None
        divisor = gcd(width, height)
        if divisor <= 0:
            return None
        return (width // divisor, height // divisor)

    def _display_file_format(entry: dict) -> str:
        suffix = Path(str(entry.get("path") or "")).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".jpe", ".jfif"}:
            return "JPEG"
        if suffix in {".png"}:
            return "PNG"
        if suffix in {".webp"}:
            return "WEBP"
        if suffix in {".tif", ".tiff"}:
            return "TIFF"
        if suffix in {".bmp"}:
            return "BMP"
        if suffix in {".gif"}:
            return "GIF"
        if suffix in {".heic", ".heif"}:
            return "HEIC"
        if suffix in {".avif"}:
            return "AVIF"
        if suffix in {".raw", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".rw2", ".raf", ".srw"}:
            return "RAW"
        return suffix.lstrip(".").upper() or "UNKNOWN"

    def _format_score(entry: dict) -> int:
        fmt = str(entry.get("duplicate_file_format") or "")
        try:
            idx = format_order.index(fmt)
        except ValueError:
            idx = len(format_order)
        return len(format_order) - idx

    def _original_timestamp(entry: dict) -> int:
        for key in ("exif_date_taken", "metadata_date"):
            raw_value = entry.get(key)
            value = raw_value if isinstance(raw_value, int) else iso_to_ns(raw_value)
            if value > 0:
                return value
        value = original_file_date_ns(entry)
        if value > 0:
            return value
        raw_value = entry.get("file_created_time")
        value = raw_value if isinstance(raw_value, int) else iso_to_ns(raw_value)
        if value > 0:
            return value
        return 0

    def _modified_timestamp(entry: dict) -> int:
        raw_value = entry.get("modified_time")
        return raw_value if isinstance(raw_value, int) else iso_to_ns(raw_value)

    for entry in ranked:
        entry["duplicate_folder_depth"] = folder_depth_for_duplicate(entry)
        entry["duplicate_parent_folder"] = duplicate_parent_folder(entry)
        entry["duplicate_preferred_folder_score"] = preferred_folder_score(
            entry,
            enabled=preferred_folders_enabled,
            score_by_folder=preferred_folder_scores,
        )
        entry["duplicate_file_format"] = _display_file_format(entry)
        original_time = _original_timestamp(entry)
        modified_time = _modified_timestamp(entry)
        entry["duplicate_original_timestamp"] = original_time
        entry["duplicate_modified_timestamp"] = modified_time
        entry["duplicate_is_edit_variant"] = (
            original_time > 0
            and modified_time > 0
            and modified_time > original_time + (5 * 60 * 1_000_000_000)
        )
        entry["duplicate_crop_variant"] = ""
        entry["duplicate_size_variant"] = ""

    color_modes = [str(entry.get("color_variant") or "") for entry in ranked]
    has_color_variants = "color" in color_modes and "grayscale" in color_modes
    positive_reasons: list[list[str]] = [[] for _ in ranked]
    informative_reasons: list[list[str]] = [[] for _ in ranked]
    candidate_indices = list(range(len(ranked)))

    if has_color_variants:
        for idx, entry in enumerate(ranked):
            mode = str(entry.get("color_variant") or "")
            if mode == "color":
                informative_reasons[idx].append("Color version")
            elif mode == "grayscale":
                informative_reasons[idx].append("Grayscale version")
        if color_policy == "prefer_color":
            preferred = [idx for idx, entry in enumerate(ranked) if str(entry.get("color_variant") or "") == "color"]
            if preferred:
                candidate_indices = preferred
        elif color_policy == "prefer_bw":
            preferred = [idx for idx, entry in enumerate(ranked) if str(entry.get("color_variant") or "") == "grayscale"]
            if preferred:
                candidate_indices = preferred

    aspect_ratios = [_normalized_aspect_ratio(entry) for entry in ranked]
    image_areas = [int(entry.get("width") or 0) * int(entry.get("height") or 0) for entry in ranked]
    valid_ratio_indices = [idx for idx, ratio in enumerate(aspect_ratios) if ratio is not None and image_areas[idx] > 0]
    distinct_ratios = {aspect_ratios[idx] for idx in valid_ratio_indices}
    if len(distinct_ratios) > 1:
        full_frame_idx = max(valid_ratio_indices, key=lambda idx: image_areas[idx], default=-1)
        full_frame_area = image_areas[full_frame_idx] if full_frame_idx >= 0 else 0
        full_frame_ratio = aspect_ratios[full_frame_idx] if full_frame_idx >= 0 else None
        unique_full_frame = full_frame_idx >= 0 and image_areas.count(full_frame_area) == 1
        cropped_candidates = [
            idx for idx in valid_ratio_indices
            if idx != full_frame_idx
            and aspect_ratios[idx] != full_frame_ratio
            and image_areas[idx] < full_frame_area
        ]
        if unique_full_frame:
            ranked[full_frame_idx]["duplicate_crop_variant"] = "full"
            informative_reasons[full_frame_idx].append("Full frame")
        for idx in cropped_candidates:
            ranked[idx]["duplicate_crop_variant"] = "cropped"
            informative_reasons[idx].append("Cropped version")
        if crop_policy == "prefer_full" and unique_full_frame:
            candidate_indices = [idx for idx in candidate_indices if idx == full_frame_idx] or candidate_indices
        elif crop_policy == "prefer_cropped" and cropped_candidates:
            preferred_cropped = [idx for idx in candidate_indices if idx in cropped_candidates]
            if preferred_cropped:
                candidate_indices = preferred_cropped

    edited_indices = [idx for idx, entry in enumerate(ranked) if entry.get("duplicate_is_edit_variant")]
    if edited_indices:
        edited_modified_times = [int(ranked[idx].get("duplicate_modified_timestamp") or 0) for idx in edited_indices]
        newest_edit_time = max(edited_modified_times, default=0)
        if newest_edit_time > 0 and edited_modified_times.count(newest_edit_time) == 1:
            informative_reasons[edited_indices[edited_modified_times.index(newest_edit_time)]].append("Newer edit")
        original_indices = [
            idx for idx, entry in enumerate(ranked)
            if int(entry.get("duplicate_original_timestamp") or 0) > 0 and not entry.get("duplicate_is_edit_variant")
        ]
        if len(original_indices) == 1:
            informative_reasons[original_indices[0]].append("Original")

    file_sizes = [int(entry.get("file_size") or 0) for entry in ranked]
    largest_file_size = max(file_sizes, default=0)
    smallest_file_size = min(file_sizes, default=0)
    if largest_file_size > smallest_file_size and file_sizes.count(largest_file_size) == 1:
        ranked[file_sizes.index(largest_file_size)]["duplicate_size_variant"] = "largest"
        informative_reasons[file_sizes.index(largest_file_size)].append("Largest file size")
    if largest_file_size > smallest_file_size and file_sizes.count(smallest_file_size) == 1:
        ranked[file_sizes.index(smallest_file_size)]["duplicate_size_variant"] = "smallest"
        informative_reasons[file_sizes.index(smallest_file_size)].append("Smallest file size")
    if file_size_policy == "prefer_smallest":
        preferred_small = [idx for idx in candidate_indices if int(ranked[idx].get("file_size") or 0) == smallest_file_size]
        if preferred_small and largest_file_size > smallest_file_size:
            candidate_indices = preferred_small

    preferred_folder_scores = [int(entry.get("duplicate_preferred_folder_score") or 0) for entry in ranked]
    best_preferred_folder_score = max(preferred_folder_scores, default=0)
    if preferred_folders_enabled and best_preferred_folder_score > 0:
        for idx, score in enumerate(preferred_folder_scores):
            if score == best_preferred_folder_score and "Preferred Folder" not in informative_reasons[idx]:
                informative_reasons[idx].append("Preferred Folder")

    format_scores = [_format_score(entry) for entry in ranked]
    best_format_score = max(format_scores, default=0)
    if best_format_score > 0 and format_scores.count(best_format_score) == 1:
        fmt_idx = format_scores.index(best_format_score)
        informative_reasons[fmt_idx].append(f"Preferred format ({ranked[fmt_idx].get('duplicate_file_format')})")

    priority_category_defs: dict[str, dict[str, Any]] = {
        "File Size": {
            "label": "Smallest file size" if file_size_policy == "prefer_smallest" else "Largest file size",
            "value": (lambda entry: -int(entry.get("file_size") or 0)) if file_size_policy == "prefer_smallest" else (lambda entry: int(entry.get("file_size") or 0)),
            "enabled": lambda values: max(values, default=0) > min(values, default=0),
        },
        "Resolution": {
            "label": "Highest resolution",
            "value": lambda entry: int(entry.get("width") or 0) * int(entry.get("height") or 0),
            "enabled": lambda values: max(values, default=0) > min(values, default=0),
        },
        "File Format": {
            "label": "Preferred format",
            "value": lambda entry: _format_score(entry),
            "enabled": lambda values: max(values, default=0) > min(values, default=0) and max(values, default=0) > 0,
        },
        "Preferred Folders": {
            "label": "Preferred Folder",
            "value": lambda entry: int(entry.get("duplicate_preferred_folder_score") or 0),
            "enabled": lambda values: preferred_folders_enabled and max(values, default=0) > min(values, default=0),
        },
        "Most metadata": {
            "label": "Most metadata",
            "value": lambda entry: duplicate_metadata_score(entry),
            "enabled": lambda values: max(values, default=(0, 0)) > (0, 0),
        },
        "Compression": {
            "label": "Compression",
            "value": lambda entry: 0,
            "enabled": lambda values: False,
        },
        "Color / Grey Preference": {
            "label": "Black & White version" if color_policy == "prefer_bw" else "Color version",
            "value": (
                (lambda entry: 1 if str(entry.get("color_variant") or "") == "grayscale" else 0)
                if color_policy == "prefer_bw"
                else (lambda entry: 1 if str(entry.get("color_variant") or "") == "color" else 0)
            ),
            "enabled": lambda values: max(values, default=0) > min(values, default=0),
        },
        "Text / No Text Preference": {
            "label": "Text preference",
            "value": lambda entry: 0,
            "enabled": lambda values: False,
        },
        "Cropped / Full Preference": {
            "label": "Cropped version" if crop_policy == "prefer_cropped" else "Full frame",
            "value": (
                (lambda entry: 1 if str(entry.get("duplicate_crop_variant") or "") == "cropped" else 0)
                if crop_policy == "prefer_cropped"
                else (lambda entry: 1 if str(entry.get("duplicate_crop_variant") or "") == "full" else 0)
            ),
            "enabled": lambda values: max(values, default=0) > min(values, default=0),
        },
    }
    positive_categories = [priority_category_defs[name] for name in configured_priorities if name in priority_category_defs]
    if extra_positive_categories:
        resolution_idx = next((i for i, cat in enumerate(positive_categories) if cat["label"] == "Highest resolution"), len(positive_categories))
        positive_categories[resolution_idx:resolution_idx] = list(extra_positive_categories)
    positive_categories.extend([
        {
            "label": "Newer edit",
            "value": lambda entry: (entry.get("duplicate_modified_timestamp") or 0) if entry.get("duplicate_is_edit_variant") else 0,
            "enabled": lambda values: max(values, default=0) > min(values, default=0) and max(values, default=0) > 0,
        },
    ])

    while len(candidate_indices) > 1:
        round_winners: set[int] = set()
        for category in positive_categories:
            values = [category["value"](ranked[idx]) for idx in candidate_indices]
            if not values or not category["enabled"](values):
                continue
            best_value = max(values)
            winners = [idx for idx in candidate_indices if category["value"](ranked[idx]) == best_value]
            if len(winners) != 1:
                continue
            winner = winners[0]
            if category["label"] not in positive_reasons[winner]:
                positive_reasons[winner].append(category["label"])
            round_winners.add(winner)
        if not round_winners:
            break
        survivors = [idx for idx in candidate_indices if idx in round_winners]
        if len(survivors) == len(candidate_indices):
            break
        candidate_indices = survivors

    def core_score(idx: int) -> tuple:
        entry = ranked[idx]
        priority_scores: list[int] = []
        for name in configured_priorities:
            if name == "File Size":
                priority_scores.append(-int(entry.get("file_size") or 0) if file_size_policy == "prefer_smallest" else int(entry.get("file_size") or 0))
            elif name == "Resolution":
                priority_scores.append(int(entry.get("width") or 0) * int(entry.get("height") or 0))
            elif name == "File Format":
                priority_scores.append(_format_score(entry))
            elif name == "Preferred Folders":
                priority_scores.append(int(entry.get("duplicate_preferred_folder_score") or 0))
            elif name == "Compression":
                priority_scores.append(0)
            elif name == "Color / Grey Preference":
                if color_policy == "prefer_bw":
                    priority_scores.append(1 if str(entry.get("color_variant") or "") == "grayscale" else 0)
                elif color_policy == "prefer_color":
                    priority_scores.append(1 if str(entry.get("color_variant") or "") == "color" else 0)
                else:
                    priority_scores.append(0)
            elif name == "Text / No Text Preference":
                priority_scores.append(0)
            elif name == "Cropped / Full Preference":
                if crop_policy == "prefer_cropped":
                    priority_scores.append(1 if str(entry.get("duplicate_crop_variant") or "") == "cropped" else 0)
                elif crop_policy == "prefer_full":
                    priority_scores.append(1 if str(entry.get("duplicate_crop_variant") or "") == "full" else 0)
                else:
                    priority_scores.append(0)
        file_size = int(entry.get("file_size") or 0)
        file_size_fallback = -file_size if file_size_policy == "prefer_smallest" else file_size
        area = int(entry.get("width") or 0) * int(entry.get("height") or 0)
        preferred_folder_score_value = int(entry.get("duplicate_preferred_folder_score") or 0)
        tag_count, filled_fields = duplicate_metadata_score(entry)
        preferred_raw = entry.get("preferred_date")
        modified_time = preferred_raw if isinstance(preferred_raw, int) else preferred_date_ns(entry)
        return (
            *priority_scores,
            len(positive_reasons[idx]),
            file_size_fallback,
            area,
            _format_score(entry),
            modified_time,
        )

    def final_score(idx: int) -> tuple:
        entry = ranked[idx]
        return (*core_score(idx), str(entry.get("path", "")).lower())

    contenders = candidate_indices or list(range(len(ranked)))
    best_idx = max(contenders, key=final_score, default=0)
    core_score_by_index = {idx: core_score(idx) for idx in range(len(ranked))}
    score_by_index = {idx: final_score(idx) for idx in range(len(ranked))}
    order = sorted(range(len(ranked)), key=lambda idx: score_by_index[idx], reverse=True)
    sorted_ranked = [ranked[idx] for idx in order]

    for position, original_idx in enumerate(order):
        entry = sorted_ranked[position]
        reasons = positive_reasons[original_idx] + [
            reason for reason in informative_reasons[original_idx]
            if reason not in positive_reasons[original_idx]
        ]
        entry["duplicate_keep_suggestion"] = original_idx == best_idx
        entry["duplicate_group_position"] = position
        entry["duplicate_category_reasons"] = reasons
        entry["duplicate_best_reason"] = f" {chr(8226)} ".join(reasons)
        entry["duplicate_is_overall_best"] = original_idx == best_idx
        next_idx = order[position + 1] if position + 1 < len(order) else None
        entry["duplicate_rank_tied_with_next"] = bool(
            next_idx is not None and core_score_by_index[original_idx] == core_score_by_index[next_idx]
        )
    return sorted_ranked


def build_duplicate_entries(
    entries: list[dict],
    sort_by: str,
    *,
    conn,
    rank_duplicate_group_fn: Callable[[list[dict], list[dict[str, Any]] | None], list[dict]],
    preferred_date_ns: Callable[[dict], int],
    file_type_sort_key: Callable[[dict], str],
) -> list[dict]:
    media_entries = [dict(entry) for entry in entries if not entry.get("is_folder")]
    excluded_pairs = load_review_pair_exclusions(conn, media_entries, "duplicates")
    duplicate_groups: dict[str, list[dict]] = {}
    for entry in media_entries:
        group_key = str(entry.get("content_hash") or "").strip()
        if not group_key:
            continue
        duplicate_groups.setdefault(group_key, []).append(entry)

    split_duplicate_groups: dict[str, list[dict]] = {}
    for content_hash, group_entries in duplicate_groups.items():
        if len(group_entries) < 2:
            continue
        for component_index, component_entries in enumerate(
            split_duplicate_group_components(group_entries, excluded_pairs),
            start=1,
        ):
            split_duplicate_groups[f"duplicate:{content_hash}:{component_index}"] = component_entries

    if not split_duplicate_groups:
        return []

    group_rows: list[tuple[tuple, list[dict]]] = []
    for group_key, group_entries in split_duplicate_groups.items():
        sorted_group = rank_duplicate_group_fn(group_entries, None)
        kept_size = int(sorted_group[0].get("file_size") or 0) if sorted_group else 0
        total_size = sum(int(entry.get("file_size") or 0) for entry in sorted_group)
        savings = max(0, total_size - kept_size)
        for entry in sorted_group:
            entry["duplicate_group_key"] = group_key
            entry["duplicate_group_size"] = len(sorted_group)
            entry["duplicate_space_savings"] = savings
            entry["review_group_mode"] = "duplicates"
        best = sorted_group[0]
        name = Path(str(best.get("path", ""))).name.lower()
        if sort_by == "name_desc":
            order_key = (name, len(sorted_group), savings)
        elif sort_by == "type_asc":
            order_key = (file_type_sort_key(best), -len(sorted_group), -savings, name)
        elif sort_by == "type_desc":
            order_key = (file_type_sort_key(best), len(sorted_group), savings, name)
        elif sort_by == "date_asc":
            order_key = (best.get("preferred_date") or preferred_date_ns(best) or 0, -len(sorted_group), -savings, name)
        elif sort_by == "date_desc":
            order_key = (-(best.get("preferred_date") or preferred_date_ns(best) or 0), -len(sorted_group), -savings, name)
        elif sort_by == "size_asc":
            order_key = (savings, -len(sorted_group), name)
        else:
            order_key = (-savings, -len(sorted_group), name)
        group_rows.append((order_key, sorted_group))

    reverse = sort_by in {"name_desc", "type_desc"}
    group_rows.sort(key=lambda row: row[0], reverse=reverse)

    flattened: list[dict] = []
    for _, group in group_rows:
        flattened.extend(group)
    return flattened


def build_similar_entries(
    entries: list[dict],
    sort_by: str,
    *,
    include_exact: bool,
    threshold: int,
    bucket_prefix: int,
    conn,
    rank_duplicate_group_fn: Callable[[list[dict], list[dict[str, Any]] | None], list[dict]],
    file_type_sort_key: Callable[[dict], str],
) -> list[dict]:
    from app.mediamanager.utils.hashing import phash_distance

    candidates = [
        dict(entry)
        for entry in entries
        if not entry.get("is_folder") and (str(entry.get("content_hash") or "").strip() or str(entry.get("phash") or "").strip())
    ]
    if not include_exact:
        unique_candidates: list[dict] = []
        exact_groups: dict[str, list[dict]] = {}
        for entry in candidates:
            content_hash = str(entry.get("content_hash") or "").strip()
            if content_hash:
                exact_groups.setdefault(content_hash, []).append(entry)
            else:
                unique_candidates.append(entry)
        for grouped_entries in exact_groups.values():
            if len(grouped_entries) == 1:
                unique_candidates.append(grouped_entries[0])
            else:
                unique_candidates.append(rank_duplicate_group_fn(grouped_entries, None)[0])
        candidates = unique_candidates
    if len(candidates) < 2:
        return []
    excluded_pairs = load_review_pair_exclusions(conn, candidates, "similar")

    parents = list(range(len(candidates)))

    def find(idx: int) -> int:
        while parents[idx] != idx:
            parents[idx] = parents[parents[idx]]
            idx = parents[idx]
        return idx

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    buckets: dict[str, list[int]] = {}
    hash_groups: dict[str, list[int]] = {}
    for index, entry in enumerate(candidates):
        phash = str(entry.get("phash") or "")
        bucket = phash[:bucket_prefix] if bucket_prefix > 0 else "*"
        buckets.setdefault(bucket, []).append(index)
        content_hash = str(entry.get("content_hash") or "").strip()
        if include_exact and content_hash:
            hash_groups.setdefault(content_hash, []).append(index)

    for group_items in hash_groups.values():
        if len(group_items) < 2:
            continue
        for pos, left_idx in enumerate(group_items):
            left_path = str(candidates[left_idx].get("path") or "")
            if not left_path:
                continue
            for right_idx in group_items[pos + 1:]:
                right_path = str(candidates[right_idx].get("path") or "")
                if not right_path or is_review_pair_excluded(excluded_pairs, left_path, right_path):
                    continue
                union(left_idx, right_idx)

    for bucket_items in buckets.values():
        for pos, left_idx in enumerate(bucket_items):
            if candidates[left_idx].get("media_type") != "image":
                continue
            left_hash = candidates[left_idx].get("phash") or ""
            if not left_hash:
                continue
            for right_idx in bucket_items[pos + 1:]:
                if candidates[right_idx].get("media_type") != "image":
                    continue
                right_hash = candidates[right_idx].get("phash") or ""
                if not right_hash:
                    continue
                if is_review_pair_excluded(
                    excluded_pairs,
                    str(candidates[left_idx].get("path") or ""),
                    str(candidates[right_idx].get("path") or ""),
                ):
                    continue
                distance = phash_distance(left_hash, right_hash)
                if distance <= threshold and (include_exact or distance > 0):
                    union(left_idx, right_idx)

    groups: dict[int, list[dict]] = {}
    for index, entry in enumerate(candidates):
        groups.setdefault(find(index), []).append(entry)

    similar_groups = [group for group in groups.values() if len(group) > 1]
    if not similar_groups:
        return []

    group_rows: list[tuple[tuple, list[dict]]] = []
    for group_index, group_entries in enumerate(similar_groups, start=1):
        sorted_group = rank_duplicate_group_fn(
            group_entries,
            [
                {
                    "label": "Highest resolution",
                    "value": lambda entry: int(entry.get("width") or 0) * int(entry.get("height") or 0),
                    "enabled": lambda values: max(values, default=0) > min(values, default=0),
                },
            ],
        )
        areas = [int(entry.get("width") or 0) * int(entry.get("height") or 0) for entry in sorted_group]
        max_area = max(areas)
        min_area = min(areas)
        unique_highest_area = areas.count(max_area) == 1 and max_area > min_area
        unique_lowest_area = areas.count(min_area) == 1 and max_area > min_area
        for entry in sorted_group:
            area = int(entry.get("width") or 0) * int(entry.get("height") or 0)
            reasons = list(entry.get("duplicate_category_reasons") or [])
            if unique_lowest_area and area == min_area:
                reasons.append("Downscaled copy")
            entry["duplicate_category_reasons"] = list(dict.fromkeys(reasons))
            entry["duplicate_best_reason"] = f" {chr(8226)} ".join(entry["duplicate_category_reasons"])
            entry["review_group_mode"] = "similar" if include_exact else "similar_only"
            entry["similar_group_distance_threshold"] = threshold
            entry["similar_group_key"] = f"similar-{group_index}"
            entry["duplicate_group_key"] = entry["similar_group_key"]
            entry["duplicate_group_size"] = len(sorted_group)
        best = sorted_group[0]
        name = Path(str(best.get("path", ""))).name.lower()
        area_score = int(best.get("width") or 0) * int(best.get("height") or 0)
        order_key = (-area_score, -len(sorted_group), name)
        if sort_by == "name_desc":
            order_key = (name, -area_score, -len(sorted_group))
        elif sort_by == "type_asc":
            order_key = (file_type_sort_key(best), -area_score, -len(sorted_group), name)
        elif sort_by == "type_desc":
            order_key = (file_type_sort_key(best), area_score, len(sorted_group), name)
        group_rows.append((order_key, sorted_group))

    group_rows.sort(key=lambda row: row[0], reverse=(sort_by in {"name_desc", "type_desc"}))
    flattened: list[dict] = []
    for _, group in group_rows:
        flattened.extend(group)
    return flattened
