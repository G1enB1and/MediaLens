from __future__ import annotations

import json
from typing import Any

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


TEXT_NODE_TYPES = {"CLIPTextEncode", "CLIPTextEncodeFlux", "CLIPTextEncodeSDXL"}


def _find_entry(raw: RawMetadataEnvelope, keyword: str) -> tuple[str, str] | None:
    for entry in raw.png_text_entries:
        if entry.keyword.lower() == keyword:
            return entry.path_descriptor, entry.text
    return None


def _node_inputs(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("inputs", {})


def _resolve_node(graph: dict[str, Any], node_ref: Any) -> dict[str, Any] | None:
    node_id = node_ref
    if isinstance(node_ref, list) and node_ref:
        node_id = node_ref[0]
    return graph.get(str(node_id))


def _resolve_static_value(graph: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, list) or not value:
        return value
    node = _resolve_node(graph, value)
    if not node:
        return value
    inputs = _node_inputs(node)
    class_type = node.get("class_type", "")
    if class_type in {"PrimitiveInt", "PrimitiveFloat"}:
        return inputs.get("value")
    return value


def _resolve_text(graph: dict[str, Any], value: Any, seen: set[str] | None = None) -> str:
    seen = seen or set()
    node = _resolve_node(graph, value)
    if not node:
        return ""
    node_id = str(node.get("id") or "")
    if node_id and node_id in seen:
        return ""
    seen.add(node_id)
    class_type = node.get("class_type", "")
    inputs = _node_inputs(node)
    if class_type in TEXT_NODE_TYPES:
        return str(inputs.get("text", "")).strip()
    if class_type == "ConditioningZeroOut":
        return ""
    if class_type in {"ConditioningSetTimestepRange", "FluxGuidance"} and "conditioning" in inputs:
        return _resolve_text(graph, inputs.get("conditioning"), seen)
    for key in ("conditioning", "positive", "negative", "text"):
        if key in inputs:
            resolved = _resolve_text(graph, inputs[key], seen)
            if resolved:
                return resolved
    return ""


def _extract_core_fields(graph: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "source_format": "comfyui",
        "tool_name_found": "ComfyUI",
        "tool_name_confidence": 1.0,
    }
    workflow_blobs: list[dict[str, Any]] = []

    for node_id, node in graph.items():
        class_type = node.get("class_type", "")
        inputs = _node_inputs(node)
        if class_type == "CheckpointLoaderSimple" and not fields.get("checkpoint_name"):
            fields["checkpoint_name"] = inputs.get("ckpt_name", "")
            fields.setdefault("model_name", fields["checkpoint_name"])
        elif class_type == "UNETLoader" and not fields.get("model_name"):
            fields["model_name"] = inputs.get("unet_name", "")
        elif class_type == "VAELoader" and not fields.get("vae_name"):
            fields["vae_name"] = inputs.get("vae_name", "")
        elif class_type == "KSampler" and not fields.get("sampler"):
            fields["seed"] = inputs.get("seed")
            fields["steps"] = inputs.get("steps")
            fields["cfg_scale"] = inputs.get("cfg")
            fields["sampler"] = inputs.get("sampler_name", "")
            fields["scheduler"] = inputs.get("scheduler", "")
            fields["denoise_strength"] = inputs.get("denoise")
            fields["ai_prompt"] = _resolve_text(graph, inputs.get("positive"))
            fields["ai_negative_prompt"] = _resolve_text(graph, inputs.get("negative"))
        elif class_type == "KSamplerSelect" and not fields.get("sampler"):
            fields["sampler"] = inputs.get("sampler_name", "")
        elif class_type == "CFGGuider":
            fields.setdefault("cfg_scale", inputs.get("cfg"))
            if not fields.get("ai_prompt"):
                fields["ai_prompt"] = _resolve_text(graph, inputs.get("positive"))
            if not fields.get("ai_negative_prompt"):
                fields["ai_negative_prompt"] = _resolve_text(graph, inputs.get("negative"))
        elif class_type == "Flux2Scheduler":
            fields.setdefault("steps", inputs.get("steps"))
            width = _resolve_static_value(graph, inputs.get("width"))
            height = _resolve_static_value(graph, inputs.get("height"))
            if isinstance(width, (int, float, str)):
                fields.setdefault("width", width)
            if isinstance(height, (int, float, str)):
                fields.setdefault("height", height)
        elif class_type == "SaveImage":
            workflow_blobs.append({"node_id": node_id, "filename_prefix": inputs.get("filename_prefix", "")})
        elif class_type in TEXT_NODE_TYPES and not fields.get("ai_prompt"):
            text = str(inputs.get("text", "")).strip()
            if text and "negative" not in text.lower():
                fields["ai_prompt"] = text

    if workflow_blobs:
        fields["workflows"] = workflow_blobs
    return fields


def parse_comfyui(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    prompt_entry = _find_entry(raw, "prompt")
    workflow_entry = _find_entry(raw, "workflow")
    if not prompt_entry and not workflow_entry:
        return None

    extracted_paths: list[str] = []
    raw_blobs: list[dict[str, Any]] = []
    warnings: list[str] = []
    normalized: dict[str, Any] = {
        "source_format": "comfyui",
        "tool_name_found": "ComfyUI",
        "tool_name_confidence": 1.0,
    }

    if prompt_entry:
        extracted_paths.append(prompt_entry[0])
        raw_blobs.append({"path": prompt_entry[0], "text": prompt_entry[1]})
        try:
            prompt_graph = json.loads(prompt_entry[1])
            normalized.update(_extract_core_fields(prompt_graph))
            normalized["raw_prompt_json"] = prompt_graph
        except Exception as exc:
            warnings.append(f"Failed to parse ComfyUI prompt JSON: {exc}")

    if workflow_entry:
        extracted_paths.append(workflow_entry[0])
        raw_blobs.append({"path": workflow_entry[0], "text": workflow_entry[1]})
        try:
            workflow_json = json.loads(workflow_entry[1])
            normalized["raw_workflow_json"] = workflow_json
        except Exception as exc:
            warnings.append(f"Failed to parse ComfyUI workflow JSON: {exc}")

    return ParsedMetadataResult(
        family="comfyui",
        confidence=0.99,
        normalized=normalized,
        raw_blobs=raw_blobs,
        extracted_paths=extracted_paths,
        warnings=warnings,
    )
