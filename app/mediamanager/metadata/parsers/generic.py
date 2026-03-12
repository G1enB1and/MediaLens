from __future__ import annotations

import re

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


def parse_generic_embedded(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    description = ""
    tags: list[str] = []
    extracted_paths: list[str] = []
    for entry in raw.png_text_entries:
        key = entry.keyword.lower()
        if key in {"comment", "comments", "description", "subject", "title"} and not description:
            description = entry.text.strip()
            extracted_paths.append(entry.path_descriptor)
        elif key in {"keywords", "tags"}:
            parts = [part.strip() for part in re.split(r"[;,]", entry.text) if part.strip()]
            for part in parts:
                if part not in tags:
                    tags.append(part)
            extracted_paths.append(entry.path_descriptor)

    if not description and not tags and not raw.exif and not raw.xmp_packets and not raw.iptc:
        return None

    normalized = {
        "source_format": "generic_embedded",
        "description": description,
        "unknown_fields": {"tags": tags, "exif": raw.exif, "iptc": raw.iptc, "xmp_packets": raw.xmp_packets},
    }
    return ParsedMetadataResult(
        family="generic_embedded",
        confidence=0.55,
        normalized=normalized,
        extracted_paths=extracted_paths,
    )
