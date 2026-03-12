from __future__ import annotations

import base64
import json
import re

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


def _extract_wpp_description(text: str) -> str:
    if not text:
        return ""
    match = re.search(r'Description\((.+?)\)\s*$', text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    parts = re.findall(r'"([^"]*)"', match.group(1))
    return " ".join(part.strip() for part in parts if part.strip()).strip()


def _display_description(card: dict[str, object]) -> str:
    short_description = str(card.get("short_description") or "").strip()
    if short_description:
        return short_description

    raw_description = str(card.get("description") or "").strip()
    extracted = _extract_wpp_description(raw_description)
    if extracted:
        return extracted

    scenario = str(card.get("scenario") or "").strip()
    if scenario:
        return scenario

    personality = str(card.get("personality") or "").strip()
    if personality:
        return personality

    return ""


def parse_sillytavern(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    entry = next((item for item in raw.png_text_entries if item.keyword.lower() == "chara"), None)
    if not entry:
        return None

    warnings: list[str] = []
    card: dict[str, object] = {}
    try:
        decoded = base64.b64decode(entry.text)
        card = json.loads(decoded.decode("utf-8", errors="replace"))
    except Exception as exc:
        warnings.append(f"Failed to decode SillyTavern card: {exc}")

    normalized = {
        "source_format": "sillytavern_card",
        "character_name": card.get("name", ""),
        "description": _display_description(card),
        "character_cards": [card] if card else [],
        "unknown_fields": card,
    }
    return ParsedMetadataResult(
        family="sillytavern",
        confidence=0.99,
        normalized=normalized,
        raw_blobs=[{"path": entry.path_descriptor, "text": entry.text}],
        extracted_paths=[entry.path_descriptor + ":base64:json"],
        warnings=warnings,
    )
