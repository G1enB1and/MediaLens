from __future__ import annotations

from pathlib import Path

from app.mediamanager.metadata.containers import extract_raw_metadata
from app.mediamanager.metadata.detectors import detect_families
from app.mediamanager.metadata.merge import merge_results
from app.mediamanager.metadata.models import InspectionResult
from app.mediamanager.metadata.parsers import (
    parse_a1111_like,
    parse_c2pa,
    parse_comfyui,
    parse_generic_embedded,
    parse_sillytavern,
)


PARSERS = {
    "a1111_like": parse_a1111_like,
    "comfyui": parse_comfyui,
    "c2pa": parse_c2pa,
    "sillytavern": parse_sillytavern,
    "generic_embedded": parse_generic_embedded,
}


def inspect_file(path: str | Path) -> InspectionResult:
    raw = extract_raw_metadata(path)
    detections = detect_families(raw)
    parsed = []
    for hit in detections:
        parser = PARSERS.get(hit.family)
        if not parser:
            continue
        result = parser(raw)
        if result:
            parsed.append(result)
    canonical = merge_results(detections, parsed)
    return InspectionResult(raw=raw, detections=detections, parsed=parsed, canonical=canonical)
