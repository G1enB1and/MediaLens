from __future__ import annotations

import base64
import re

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


def _extract_bytes_from_entry(entry_b64: str) -> bytes:
    try:
        return base64.b64decode(entry_b64)
    except Exception:
        return b""


def _decoded_text(data: bytes) -> str:
    return data.decode("latin-1", errors="replace")


def parse_c2pa(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    entries = [entry for entry in raw.png_binary_entries if entry.chunk_type == "caBX"]
    if not entries:
        return None

    raw_blobs = []
    extracted_paths = []
    tool_name_found = ""
    model_name = ""
    actions: list[str] = []
    unknown_fields: dict[str, object] = {}

    for entry in entries:
        extracted_paths.append(entry.path_descriptor)
        raw_blobs.append(
            {
                "path": entry.path_descriptor,
                "raw_binary_b64": entry.raw_binary_b64,
                "printable_strings": entry.printable_strings,
            }
        )
        payload = _decoded_text(_extract_bytes_from_entry(entry.raw_binary_b64))
        if "ChatGPT" in payload:
            tool_name_found = "ChatGPT"
        elif "Google Generative AI" in payload:
            tool_name_found = "Google Generative AI"
        elif "Google C2PA" in payload or "Google LLC" in payload:
            tool_name_found = tool_name_found or "Google"

        model_match = re.search(r"dnamef([A-Za-z0-9\-\._]+)", payload)
        if model_match and model_match.group(1).startswith("GPT-"):
            model_name = model_match.group(1)

        for pattern in (
            r"c2pa\.created",
            r"c2pa\.converted",
            r"c2pa\.opened",
            r"Created by Google Generative AI\.",
            r"Applied imperceptible SynthID watermark\.",
        ):
            for match in re.findall(pattern, payload):
                if match not in actions:
                    actions.append(match)

        instance_ids = re.findall(r"xmp:iid:[0-9a-fA-F\-]+", payload)
        if instance_ids:
            unknown_fields["instance_ids"] = instance_ids
        digital_source_type_match = re.findall(
            r"http://cv\.iptc\.org/newscodes/digitalsourcetype/[A-Za-z]+",
            payload,
        )
        if digital_source_type_match:
            unknown_fields["digital_source_types"] = digital_source_type_match

    normalized = {
        "source_format": "c2pa",
        "tool_name_found": tool_name_found,
        "tool_name_confidence": 0.95 if tool_name_found else 0.0,
        "model_name": model_name,
        "provenance": [{"format": "c2pa", "actions": actions, "paths": extracted_paths}],
        "unknown_fields": unknown_fields,
    }
    return ParsedMetadataResult(
        family="c2pa",
        confidence=0.97,
        normalized=normalized,
        raw_blobs=raw_blobs,
        extracted_paths=extracted_paths,
    )
