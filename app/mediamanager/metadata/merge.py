from __future__ import annotations

from app.mediamanager.metadata.models import CanonicalMetadata, DetectionHit, ParsedMetadataResult


def merge_results(detections: list[DetectionHit], parsed_results: list[ParsedMetadataResult]) -> CanonicalMetadata:
    canonical = CanonicalMetadata()
    ai_detection_families = {"a1111_like", "comfyui", "c2pa", "sillytavern", "ai_likely"}
    canonical.metadata_families_detected = [hit.family for hit in detections if hit.family in ai_detection_families]
    canonical.ai_detection_reasons = [reason for hit in detections if hit.family in ai_detection_families for reason in hit.reasons]
    canonical.is_ai_confidence = max(
        (hit.confidence for hit in detections if hit.family in {"a1111_like", "comfyui", "c2pa", "ai_likely"}),
        default=0.0,
    )
    canonical.is_ai_detected = canonical.is_ai_confidence >= 0.65

    for result in parsed_results:
        source_format = result.normalized.get("source_format")
        if source_format and source_format not in canonical.source_formats:
            canonical.source_formats.append(str(source_format))
        if result.family != "generic_embedded":
            for path in result.extracted_paths:
                if path not in canonical.raw_paths:
                    canonical.raw_paths.append(path)

        if result.family == "a1111_like":
            canonical.ai_prompt = canonical.ai_prompt or result.normalized.get("ai_prompt", "")
            canonical.ai_negative_prompt = canonical.ai_negative_prompt or result.normalized.get("ai_negative_prompt", "")
            canonical.description = canonical.description or result.normalized.get("description", "")
            canonical.model_name = canonical.model_name or result.normalized.get("model_name", "")
            canonical.model_hash = canonical.model_hash or result.normalized.get("model_hash", "")
            canonical.checkpoint_name = canonical.checkpoint_name or result.normalized.get("checkpoint_name", "")
            canonical.sampler = canonical.sampler or result.normalized.get("sampler", "")
            canonical.scheduler = canonical.scheduler or result.normalized.get("scheduler", "")
            canonical.cfg_scale = canonical.cfg_scale if canonical.cfg_scale is not None else result.normalized.get("cfg_scale")
            canonical.steps = canonical.steps if canonical.steps is not None else result.normalized.get("steps")
            canonical.seed = canonical.seed if canonical.seed is not None else result.normalized.get("seed")
            canonical.width = canonical.width if canonical.width is not None else result.normalized.get("width")
            canonical.height = canonical.height if canonical.height is not None else result.normalized.get("height")
            canonical.denoise_strength = canonical.denoise_strength if canonical.denoise_strength is not None else result.normalized.get("denoise_strength")
            canonical.upscaler = canonical.upscaler or result.normalized.get("upscaler", "")
            for lora in result.normalized.get("loras", []):
                if lora not in canonical.loras:
                    canonical.loras.append(lora)
            inferred = result.normalized.get("tool_name_inferred", "")
            if inferred and not canonical.tool_name_inferred:
                canonical.tool_name_inferred = inferred
                canonical.tool_name_confidence = float(result.normalized.get("tool_name_confidence", 0.0))
            for key, value in result.normalized.get("unknown_fields", {}).items():
                canonical.unknown_fields.setdefault(key, value)
        elif result.family == "comfyui":
            canonical.ai_prompt = canonical.ai_prompt or result.normalized.get("ai_prompt", "")
            canonical.ai_negative_prompt = canonical.ai_negative_prompt or result.normalized.get("ai_negative_prompt", "")
            canonical.model_name = canonical.model_name or result.normalized.get("model_name", "")
            canonical.checkpoint_name = canonical.checkpoint_name or result.normalized.get("checkpoint_name", "")
            canonical.sampler = canonical.sampler or result.normalized.get("sampler", "")
            canonical.scheduler = canonical.scheduler or result.normalized.get("scheduler", "")
            canonical.cfg_scale = canonical.cfg_scale if canonical.cfg_scale is not None else result.normalized.get("cfg_scale")
            canonical.steps = canonical.steps if canonical.steps is not None else result.normalized.get("steps")
            canonical.seed = canonical.seed if canonical.seed is not None else result.normalized.get("seed")
            canonical.width = canonical.width if canonical.width is not None else result.normalized.get("width")
            canonical.height = canonical.height if canonical.height is not None else result.normalized.get("height")
            canonical.denoise_strength = canonical.denoise_strength if canonical.denoise_strength is not None else result.normalized.get("denoise_strength")
            if not canonical.tool_name_found:
                canonical.tool_name_found = result.normalized.get("tool_name_found", "")
                canonical.tool_name_confidence = float(result.normalized.get("tool_name_confidence", 0.0))
            for key in ("raw_prompt_json", "raw_workflow_json"):
                if key in result.normalized:
                    canonical.workflows.append({"kind": key, "data": result.normalized[key]})
        elif result.family == "c2pa":
            if not canonical.tool_name_found and result.normalized.get("tool_name_found"):
                canonical.tool_name_found = result.normalized.get("tool_name_found", "")
                canonical.tool_name_confidence = float(result.normalized.get("tool_name_confidence", 0.0))
            canonical.model_name = canonical.model_name or result.normalized.get("model_name", "")
            for item in result.normalized.get("provenance", []):
                if item not in canonical.provenance:
                    canonical.provenance.append(item)
            for key, value in result.normalized.get("unknown_fields", {}).items():
                canonical.unknown_fields.setdefault(key, value)
        elif result.family == "sillytavern":
            for card in result.normalized.get("character_cards", []):
                if card not in canonical.character_cards:
                    canonical.character_cards.append(card)
            canonical.description = canonical.description or result.normalized.get("description", "")
        elif result.family == "generic_embedded":
            canonical.description = canonical.description or result.normalized.get("description", "")

    return canonical
