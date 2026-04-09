from __future__ import annotations

import re
from typing import Any

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


def _looks_like_a1111_parameters(text: str) -> bool:
    sample = str(text or "")
    if not sample.strip():
        return False
    has_negative = bool(re.search(r"\bNegative prompt:", sample, re.IGNORECASE))
    has_steps = bool(re.search(r"\bSteps:\s*\d+", sample, re.IGNORECASE))
    has_sampler = bool(re.search(r"\bSampler:", sample, re.IGNORECASE))
    has_model = bool(re.search(r"\bModel(?: hash)?:", sample, re.IGNORECASE))
    return (has_negative and has_steps) or (has_steps and has_sampler and has_model)


def _find_parameters_sources(raw: RawMetadataEnvelope) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    for entry in raw.png_text_entries:
        if entry.keyword.lower() == "parameters":
            sources.append((entry.path_descriptor, entry.text))
    if "parameters" in raw.pillow_info:
        sources.append(("pillow:info[parameters]", str(raw.pillow_info["parameters"])))
    for key, value in (raw.exif or {}).items():
        value_text = str(value or "")
        if not value_text.strip():
            continue
        if _looks_like_a1111_parameters(value_text):
            sources.append((f"exif:{key}", value_text))
    for index, packet in enumerate(raw.xmp_packets or [], start=1):
        packet_text = str(packet or "")
        if not packet_text.strip():
            continue
        if _looks_like_a1111_parameters(packet_text):
            sources.append((f"xmp:packet[{index}]", packet_text))
            continue
        if re.search(r"UserComment", packet_text, re.IGNORECASE):
            match = re.search(r"<exif:UserComment[^>]*>(.*?)</exif:UserComment>", packet_text, re.IGNORECASE | re.DOTALL)
            extracted = match.group(1) if match else packet_text
            extracted = re.sub(r"<[^>]+>", " ", extracted)
            extracted = " ".join(extracted.split())
            if _looks_like_a1111_parameters(extracted):
                sources.append((f"xmp:packet[{index}]:exif:UserComment", extracted))

    def score_source(item: tuple[str, str]) -> tuple[int, int]:
        _, text = item
        sample = str(text or "")
        score = 0
        if re.search(r"\bNegative prompt:", sample, re.IGNORECASE):
            score += 4
        if re.search(r"\bSteps:\s*\d+", sample, re.IGNORECASE):
            score += 3
        if re.search(r"\bSampler:", sample, re.IGNORECASE):
            score += 2
        if re.search(r"\bModel(?: hash)?:", sample, re.IGNORECASE):
            score += 1
        return (score, len(sample))

    return sorted(sources, key=score_source, reverse=True)


def _split_parameters_blob(text: str) -> tuple[str, str, str]:
    negative_marker = "\nNegative prompt:"
    steps_match = re.search(r"\nSteps:\s", text)
    if negative_marker in text:
        prompt, rest = text.split(negative_marker, 1)
        if steps_match:
            index = rest.find("\nSteps:")
            if index >= 0:
                return prompt.strip(), rest[:index].strip(), rest[index + 1 :].strip()
        return prompt.strip(), rest.strip(), ""
    if steps_match:
        index = steps_match.start()
        return text[:index].strip(), "", text[index + 1 :].strip()
    return text.strip(), "", ""


def _split_key_values(text: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    for char in text:
        if char in {'"', "'"}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        elif quote is None:
            if char in "([{":
                depth += 1
            elif char in ")]}" and depth > 0:
                depth -= 1
            elif char == "," and depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
                continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _parse_kv_tail(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in _split_key_values(text):
        if ":" not in item:
            parsed.setdefault("_unparsed", []).append(item)
            continue
        key, value = item.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _extract_loras(prompt: str, kv: dict[str, Any]) -> list[dict[str, Any]]:
    loras: list[dict[str, Any]] = []
    for name, weight in re.findall(r"<lora:([^:>]+):([^>]+)>", prompt, re.IGNORECASE):
        loras.append({"name": name, "weight": weight, "source": "prompt_token"})
    lora_hashes = kv.get("Lora hashes")
    if lora_hashes:
        for name, hash_value in re.findall(r'([^:,"]+):\s*([0-9a-fA-F]+)', str(lora_hashes)):
            loras.append({"name": name.strip(), "hash": hash_value.strip(), "source": "lora_hashes"})
    return loras


def _maybe_number(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except Exception:
        return text


def parse_a1111_like(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    sources = _find_parameters_sources(raw)
    if not sources:
        return None

    path_descriptor, raw_text = sources[0]
    prompt, negative_prompt, tail = _split_parameters_blob(raw_text)
    kv = _parse_kv_tail(tail)
    width = None
    height = None
    size = kv.get("Size")
    if size and "x" in str(size):
        width_text, height_text = str(size).split("x", 1)
        width = _maybe_number(width_text)
        height = _maybe_number(height_text)

    tool_name_inferred = ""
    tool_name_confidence = 0.0
    if "Distilled CFG Scale" in kv or "Diffusion in Low Bits" in kv or str(kv.get("Version", "")).startswith("f2."):
        tool_name_inferred = "Forge"
        tool_name_confidence = 0.68

    normalized = {
        "source_format": "a1111_parameters",
        "tool_name_inferred": tool_name_inferred,
        "tool_name_confidence": tool_name_confidence,
        "ai_prompt": prompt,
        "ai_negative_prompt": negative_prompt,
        "description": prompt,
        "steps": _maybe_number(kv.get("Steps")),
        "sampler": kv.get("Sampler", ""),
        "scheduler": kv.get("Schedule type", ""),
        "cfg_scale": _maybe_number(kv.get("CFG scale")),
        "seed": _maybe_number(kv.get("Seed")),
        "width": width,
        "height": height,
        "model_name": kv.get("Model", ""),
        "model_hash": kv.get("Model hash", ""),
        "checkpoint_name": kv.get("Model", ""),
        "denoise_strength": _maybe_number(kv.get("Denoising strength")),
        "upscaler": kv.get("Hires upscaler", ""),
        "loras": _extract_loras(prompt, kv),
        "unknown_fields": kv,
    }
    return ParsedMetadataResult(
        family="a1111_like",
        confidence=0.97,
        normalized=normalized,
        raw_blobs=[{"path": path_descriptor, "text": raw_text}],
        extracted_paths=[path_descriptor],
    )
