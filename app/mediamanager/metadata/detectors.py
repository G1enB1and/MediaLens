from __future__ import annotations

import re

from app.mediamanager.metadata.models import DetectionHit, RawMetadataEnvelope


def _is_interesting_info_key(key: str) -> bool:
    text = str(key or "").strip().lower()
    if not text:
        return False
    return any(
        token in text
        for token in (
            "comment",
            "description",
            "subject",
            "title",
            "keyword",
            "tag",
            "svg:",
            "creation time",
            "date",
            "xmp",
            "rdf",
            "metadata",
        )
    )


def detect_families(raw: RawMetadataEnvelope) -> list[DetectionHit]:
    hits: list[DetectionHit] = []
    keywords = {entry.keyword.lower(): entry for entry in raw.png_text_entries}
    info_keys = {key.lower() for key in raw.pillow_info}
    exif_keys = {str(key).lower() for key in raw.exif}

    sample_texts = [entry.text for entry in raw.png_text_entries]
    sample_texts.extend(str(value) for value in raw.pillow_info.values())
    sample_texts.extend(str(value) for value in raw.exif.values())
    sample_texts.extend(raw.xmp_packets)
    sample_texts.extend(binary.printable_strings[0] for binary in raw.png_binary_entries if binary.printable_strings)
    merged = "\n".join(sample_texts)

    if (
        "parameters" in keywords
        or "parameters" in info_keys
        or (
            re.search(r"\bNegative prompt:", merged, re.IGNORECASE)
            and re.search(r"\bSteps:\s*\d+", merged, re.IGNORECASE)
        )
    ):
        hits.append(DetectionHit("a1111_like", 0.98, ["Found parameters text payload"]))
    if "prompt" in keywords and "workflow" in keywords:
        hits.append(DetectionHit("comfyui", 0.99, ["Found prompt and workflow text chunks"]))
    if any(entry.chunk_type == "caBX" for entry in raw.png_binary_entries):
        hits.append(DetectionHit("c2pa", 0.97, ["Found PNG caBX JUMBF/C2PA chunk"]))
    if "chara" in keywords:
        hits.append(DetectionHit("sillytavern", 0.99, ["Found chara text chunk"]))

    generic_reasons: list[str] = []
    if raw.exif:
        generic_reasons.append("EXIF metadata present")
    if raw.xmp_packets:
        generic_reasons.append("XMP metadata present")
    if raw.iptc:
        generic_reasons.append("IPTC metadata present")
    if raw.png_text_entries:
        generic_reasons.append("Embedded text metadata present")
    if any(_is_interesting_info_key(key) for key in raw.pillow_info):
        generic_reasons.append("Container metadata fields present")
    if generic_reasons:
        hits.append(DetectionHit("generic_embedded", 0.55, generic_reasons))

    ai_hint_reasons: list[str] = []
    for pattern, reason in (
        (r"\bNegative prompt:", "A1111-style negative prompt text"),
        (r"\bSampler:", "Sampler key present"),
        (r"\bc2pa\b", "C2PA provenance strings present"),
        (r"\bSynthID\b", "SynthID provenance strings present"),
        (r"\bworkflow\b", "Workflow JSON present"),
        (r"\b<lora:", "LoRA token present"),
    ):
        if re.search(pattern, merged, re.IGNORECASE):
            ai_hint_reasons.append(reason)
    if ai_hint_reasons:
        hits.append(DetectionHit("ai_likely", 0.7, ai_hint_reasons))

    hits.sort(key=lambda hit: hit.confidence, reverse=True)
    return hits
