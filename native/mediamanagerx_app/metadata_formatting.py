from __future__ import annotations

import re
from datetime import datetime, timezone


def format_sidebar_datetime(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%Y-%m-%d %I:%M %p").lstrip("0").replace(" 0", " ")
    except Exception:
        return str(value or "")


def normalize_metadata_datetime(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for parser in (
        lambda raw: datetime.fromisoformat(raw),
        lambda raw: datetime.strptime(raw, "%Y:%m:%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y:%m:%d"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d"),
    ):
        try:
            parsed = parser(text)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.replace(microsecond=0).isoformat(sep="T")
        except Exception:
            continue
    return text


def format_editable_datetime(value: str | None) -> str:
    normalized = normalize_metadata_datetime(value)
    if not normalized:
        return ""
    try:
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return normalized


def format_exif_datetime(value: str | None) -> str:
    normalized = normalize_metadata_datetime(value)
    if not normalized:
        return ""
    try:
        return datetime.fromisoformat(normalized).strftime("%Y:%m:%d %H:%M:%S")
    except Exception:
        return ""


def format_xmp_datetime(value: str | None) -> str:
    normalized = normalize_metadata_datetime(value)
    if not normalized:
        return ""
    try:
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return ""


def parse_ai_text_list(value: str | None) -> list[str]:
    raw = str(value or "").replace("\r", "\n")
    parts: list[str] = []
    for chunk in raw.replace(",", "\n").split("\n"):
        text = chunk.strip()
        if text and text not in parts:
            parts.append(text)
    return parts


def parse_optional_float(value: str | None):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def parse_optional_int(value: str | None):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def parse_ai_status_override(value: str | None, fallback_detected: bool, fallback_confidence: float) -> tuple[bool, float]:
    text = str(value or "").strip()
    if not text:
        return bool(fallback_detected), float(fallback_confidence or 0.0)
    lowered = text.lower()
    detected = bool(fallback_detected)
    if any(token in lowered for token in ("not detected", "non-ai", "non ai", "no ai", "false", "no")):
        detected = False
    elif any(token in lowered for token in ("detected", "ai generated", "true", "yes")):
        detected = True

    confidence = float(fallback_confidence or 0.0)
    pct_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        confidence = max(0.0, min(1.0, float(pct_match.group(1)) / 100.0))
    else:
        num_match = re.search(r"(-?\d+(?:\.\d+)?)", text)
        if num_match:
            parsed = float(num_match.group(1))
            confidence = max(0.0, min(1.0, parsed if parsed <= 1.0 else parsed / 100.0))
        elif detected != bool(fallback_detected):
            confidence = 1.0 if detected else 0.0
    return detected, confidence


def parse_ai_source_override(value: str | None, fallback: dict | None = None) -> dict:
    text = str(value or "").replace("\r", "\n").strip()
    existing = dict(fallback or {})
    tool_found = str(existing.get("tool_name_found") or "").strip()
    tool_inferred = str(existing.get("tool_name_inferred") or "").strip()
    tool_confidence = float(existing.get("tool_name_confidence") or 0.0)
    source_formats = [str(item).strip() for item in (existing.get("source_formats") or []) if str(item).strip()]
    if not text:
        return {
            "tool_name_found": tool_found,
            "tool_name_inferred": tool_inferred,
            "tool_name_confidence": tool_confidence,
            "source_formats": source_formats,
        }

    freeform_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("found:"):
            tool_found = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("inferred:"):
            tool_inferred = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("inference confidence:"):
            tool_confidence = parse_ai_status_override(line, True, tool_confidence)[1]
            continue
        if lower.startswith("formats:") or lower.startswith("source formats:"):
            source_formats = parse_ai_text_list(line.split(":", 1)[1])
            continue
        freeform_lines.append(line)

    if freeform_lines:
        if not tool_found and len(freeform_lines) == 1:
            tool_found = freeform_lines[0]
        elif not tool_found:
            tool_found = freeform_lines[0]
            for line in freeform_lines[1:]:
                if line not in source_formats:
                    source_formats.append(line)
    return {
        "tool_name_found": tool_found,
        "tool_name_inferred": tool_inferred,
        "tool_name_confidence": tool_confidence,
        "source_formats": source_formats,
    }


def auto_text_detected_note_value(value) -> str:
    if isinstance(value, str):
        detected = value.strip().lower() in {"1", "true", "yes", "text", "text_detected"}
    else:
        detected = bool(value)
    return "Text Detected" if detected else "No Text Detected"


def auto_ai_detected_note_value(value) -> str:
    if isinstance(value, str):
        detected = value.strip().lower() in {"1", "true", "yes", "ai", "ai_generated"}
    else:
        detected = bool(value)
    return "AI Generated" if detected else "Not AI Generated"


def parse_user_confirmed_ai(value: str | None):
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in {"yes", "true", "1", "ai", "detected"}:
        return True
    if text in {"no", "false", "0", "non-ai", "non ai", "not detected"}:
        return False
    return None


def format_duration_seconds(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return ""
    total_ms = int(round(seconds * 1000))
    total_seconds = total_ms // 1000
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
