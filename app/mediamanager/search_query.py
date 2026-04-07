from __future__ import annotations

import fnmatch
import re
import shlex
from pathlib import Path
from datetime import datetime, timezone


STRING_FIELD_ALIASES = {
    "path": "path",
    "filename": "filename",
    "file": "filename",
    "name": "filename",
    "folder": "folder",
    "dir": "folder",
    "title": "title",
    "description": "description",
    "desc": "description",
    "notes": "notes",
    "note": "notes",
    "tags": "tags",
    "tag": "tags",
    "collection": "collection_names",
    "collections": "collection_names",
    "prompt": "ai_prompt",
    "negative": "ai_negative_prompt",
    "negprompt": "ai_negative_prompt",
    "tool": "tool_name",
    "model": "model_name",
    "checkpoint": "checkpoint_name",
    "sampler": "sampler",
    "scheduler": "scheduler",
    "source": "source_formats",
    "family": "metadata_families",
    "lora": "ai_loras",
    "type": "media_type",
    "ext": "ext",
    "extension": "ext",
}

NUMERIC_FIELD_ALIASES = {
    "cfg": "cfg_scale",
    "steps": "steps",
    "seed": "seed",
    "width": "width",
    "height": "height",
    "duration": "duration",
    "size": "file_size",
}

DATE_FIELD_ALIASES = {
    "datetaken": "exif_date_taken",
    "exifdatetaken": "exif_date_taken",
    "dateacquired": "metadata_date",
    "metadatadate": "metadata_date",
    "originalfiledate": "original_file_date",
    "datecreated": "file_created_time",
    "filecreateddate": "file_created_time",
    "created": "file_created_time",
    "datemodified": "modified_time",
    "filemodifieddate": "modified_time",
    "modified": "modified_time",
}

FIELD_ALIASES = {**STRING_FIELD_ALIASES, **NUMERIC_FIELD_ALIASES, **DATE_FIELD_ALIASES}
OPERATORS = (">=", "<=", ">", "<", "=")


def matches_media_search(row: dict, search_query: str) -> bool:
    terms = _tokenize_query(search_query)
    if not terms:
        return True

    for group in _split_or_groups(terms):
        if group and _matches_group(row, group):
            return True
    return False


def _tokenize_query(search_query: str) -> list[str]:
    try:
        raw_terms = [term for term in shlex.split(search_query) if term.strip()]
    except Exception:
        raw_terms = [term for term in search_query.split() if term.strip()]
    return _normalize_terms(raw_terms)


def _normalize_terms(terms: list[str]) -> list[str]:
    normalized: list[str] = []
    i = 0
    while i < len(terms):
        term = terms[i]
        if i + 1 < len(terms):
            base = term[1:] if term[:1] in ("+", "-") else term
            if base.endswith(":") or any(base.endswith(op) for op in OPERATORS):
                normalized.append(term + terms[i + 1])
                i += 2
                continue
        normalized.append(term)
        i += 1
    return normalized


def _split_or_groups(terms: list[str]) -> list[list[str]]:
    groups: list[list[str]] = [[]]
    for term in terms:
        if term.upper() == "OR" or term == "|":
            if groups[-1]:
                groups.append([])
            continue
        groups[-1].append(term)
    return [group for group in groups if group]


def _matches_group(row: dict, terms: list[str]) -> bool:
    for raw_term in terms:
        negate = raw_term.startswith("-") and len(raw_term) > 1
        required_term = raw_term[1:] if negate or (raw_term.startswith("+") and len(raw_term) > 1) else raw_term
        matched = _match_term(row, required_term)
        if negate:
            if matched:
                return False
        elif not matched:
            return False
    return True


def _match_term(row: dict, term: str) -> bool:
    field, operator, value = _parse_field_term(term)
    if field:
        return _match_field(row, field, operator, value)
    return _match_generic(row, term)


def _parse_field_term(term: str) -> tuple[str | None, str | None, str]:
    if ":" in term:
        field_candidate, expr = term.split(":", 1)
        field_key = FIELD_ALIASES.get(field_candidate.lower())
        if field_key:
            for op in OPERATORS:
                if expr.startswith(op):
                    return field_key, op, expr[len(op):]
            return field_key, "contains", expr

    match = re.match(r"^([A-Za-z_][\w-]*)(>=|<=|>|<|=)(.+)$", term)
    if match:
        field_key = FIELD_ALIASES.get(match.group(1).lower())
        if field_key:
            return field_key, match.group(2), match.group(3)

    return None, None, term


def _match_field(row: dict, field: str, operator: str | None, value: str) -> bool:
    if field in NUMERIC_FIELD_ALIASES.values():
        return _match_numeric_field(row, field, operator or "=", value)
    if field in DATE_FIELD_ALIASES.values():
        return _match_date_field(row, field, operator or "=", value)

    values = _field_values(row, field)
    if not values:
        return False
    needle = str(value or "").strip().lower()
    if not needle:
        return False
    use_glob = "*" in needle or "?" in needle

    for candidate in values:
        candidate_text = candidate.lower()
        if operator == "=":
            if use_glob and _wildcard_matches(candidate_text, needle):
                return True
            if candidate_text == needle:
                return True
        else:
            if use_glob and _wildcard_matches(candidate_text, needle):
                return True
            if needle in candidate_text:
                return True
    return False


def _match_numeric_field(row: dict, field: str, operator: str, value: str) -> bool:
    candidate = _numeric_value_for_field(row, field)
    expected = _parse_numeric_value(field, value)
    if candidate is None or expected is None:
        return False

    if operator == ">":
        return candidate > expected
    if operator == ">=":
        return candidate >= expected
    if operator == "<":
        return candidate < expected
    if operator == "<=":
        return candidate <= expected
    return candidate == expected


def _match_generic(row: dict, term: str) -> bool:
    needle = term.strip().lower()
    if not needle:
        return False

    candidates = _generic_values(row)
    use_glob = "*" in needle or "?" in needle
    for candidate in candidates:
        candidate_text = candidate.lower()
        if use_glob and _wildcard_matches(candidate_text, needle):
            return True
        if needle in candidate_text:
            return True
    return False


def _match_date_field(row: dict, field: str, operator: str, value: str) -> bool:
    candidate = _date_value_for_field(row, field)
    expected, date_only = _parse_date_query_value(value)
    if candidate is None or expected is None:
        return False

    if date_only:
        day_end = expected + 86400
        if operator == ">":
            return candidate >= day_end
        if operator == ">=":
            return candidate >= expected
        if operator == "<":
            return candidate < expected
        if operator == "<=":
            return candidate < day_end
        return expected <= candidate < day_end

    if operator == ">":
        return candidate > expected
    if operator == ">=":
        return candidate >= expected
    if operator == "<":
        return candidate < expected
    if operator == "<=":
        return candidate <= expected
    return candidate == expected


def _wildcard_matches(candidate_text: str, pattern: str) -> bool:
    regex = _wildcard_pattern_to_regex(pattern)
    if regex.search(candidate_text):
        return True
    for token in _candidate_tokens(candidate_text):
        if regex.search(token):
            return True
    return False


def _candidate_tokens(candidate_text: str) -> list[str]:
    tokens = {candidate_text}
    for part in re.split(r"[\s,;:/\\|()\[\]{}<>\"']+", candidate_text):
        part = part.strip()
        if part:
            tokens.add(part)
    return list(tokens)


def _wildcard_pattern_to_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*", ".*").replace(r"\?", ".")
    return re.compile(escaped, re.IGNORECASE)


def _generic_values(row: dict) -> list[str]:
    fields = [
        "path",
        "filename",
        "folder",
        "title",
        "description",
        "notes",
        "tags",
        "collection_names",
        "ai_prompt",
        "ai_negative_prompt",
        "tool_name",
        "model_name",
        "checkpoint_name",
        "sampler",
        "scheduler",
        "source_formats",
        "metadata_families",
        "ai_loras",
        "media_type",
        "ext",
    ]
    values: list[str] = []
    for field in fields:
        values.extend(_field_values(row, field))
    return values


def _field_values(row: dict, field: str) -> list[str]:
    path_value = str(row.get("path") or "")
    path_obj = Path(path_value) if path_value else None
    derived = {
        "filename": path_obj.name if path_obj else "",
        "folder": str(path_obj.parent) if path_obj else "",
        "tool_name": row.get("tool_name_found") or row.get("tool_name_inferred") or "",
        "ext": path_obj.suffix.lower().lstrip(".") if path_obj else "",
    }
    raw = derived.get(field, row.get(field))
    if raw in (None, ""):
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(value) for value in raw if str(value or "").strip()]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _numeric_value_for_field(row: dict, field: str) -> float | None:
    value = row.get(field)
    if field == "duration" and value is None and row.get("duration_ms") is not None:
        value = row.get("duration_ms")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _date_value_for_field(row: dict, field: str) -> float | None:
    return _parse_date_value(row.get(field))


def _parse_numeric_value(field: str, raw: str) -> float | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    try:
        if field == "file_size":
            return _parse_size_bytes(text)
        if field == "duration":
            return _parse_duration_seconds(text)
        return float(text)
    except Exception:
        return None


def _parse_date_value(raw: str | None) -> float | None:
    parsed, _ = _parse_date_query_value(raw)
    return parsed


def _parse_date_query_value(raw: str | None) -> tuple[float | None, bool]:
    text = str(raw or "").strip()
    if not text:
        return None, False
    normalized = text.replace("Z", "+00:00")
    for parser in (
        _parse_iso_datetime,
        _parse_slash_datetime,
        _parse_dash_datetime,
    ):
        parsed = parser(normalized)
        if parsed is not None:
            return parsed, _is_date_only_value(text)
    return None, False


def _parse_iso_datetime(text: str) -> float | None:
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _parse_slash_datetime(text: str) -> float | None:
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            continue
    return None


def _parse_dash_datetime(text: str) -> float | None:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            continue
    return None


def _is_date_only_value(text: str) -> bool:
    value = str(text or "").strip()
    return bool(
        re.match(r"^\d{4}-\d{2}-\d{2}$", value)
        or re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", value)
    )


def _parse_size_bytes(text: str) -> float:
    match = re.match(r"^(\d+(?:\.\d+)?)(b|kb|mb|gb|tb)?$", text)
    if not match:
        raise ValueError("invalid size")
    value = float(match.group(1))
    unit = (match.group(2) or "b").lower()
    factors = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
    return value * factors[unit]


def _parse_duration_seconds(text: str) -> float:
    match = re.match(r"^(\d+(?:\.\d+)?)(ms|s|sec|secs|m|min|mins|h|hr|hrs)?$", text)
    if not match:
        raise ValueError("invalid duration")
    value = float(match.group(1))
    unit = (match.group(2) or "s").lower()
    factors = {
        "ms": 0.001,
        "s": 1,
        "sec": 1,
        "secs": 1,
        "m": 60,
        "min": 60,
        "mins": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
    }
    return value * factors[unit]
