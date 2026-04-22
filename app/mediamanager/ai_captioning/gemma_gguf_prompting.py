from __future__ import annotations

import re
from typing import Any


DEFAULT_GGUF_DESCRIPTION_RULES = (
    "Return only the final description paragraph.",
    "Do not output reasoning, analysis, planning, numbered steps, labels, markdown, or quotes.",
)

DEFAULT_BF16_DESCRIPTION_RULES = (
    "Return exactly one natural-language image description paragraph.",
    "Do not output reasoning, analysis, planning, numbered steps, labels, markdown, or quotes.",
    "Do not repeat the prompt or explain what you will do.",
    "Do not include headings such as Image Analysis, Subject, Setting, or Execution.",
)


def build_user_description_prompt(prompt_template: str, tags: list[str], caption_start: str) -> str:
    prompt = str(prompt_template or "").strip()
    clean_tags = ", ".join(str(tag).strip() for tag in tags if str(tag).strip())
    clean_start = " ".join(str(caption_start or "").split())
    if "{tags}" in prompt:
        prompt = prompt.replace("{tags}", clean_tags)
    if "{starter}" in prompt:
        prompt = prompt.replace("{starter}", clean_start)
    elif clean_start:
        prompt = f"{prompt.rstrip()}\nStart your description with: {clean_start}"
    return prompt.strip()


def build_gguf_description_prompt(prompt_template: str, tags: list[str], caption_start: str) -> str:
    base_prompt = build_user_description_prompt(prompt_template, tags, caption_start)
    suffix = " ".join(DEFAULT_GGUF_DESCRIPTION_RULES)
    return f"{base_prompt.rstrip()}\n{suffix}".strip()


def build_bf16_description_prompt(prompt_template: str, tags: list[str], caption_start: str) -> str:
    base_prompt = build_user_description_prompt(prompt_template, tags, caption_start)
    suffix = " ".join(DEFAULT_BF16_DESCRIPTION_RULES)
    return f"{base_prompt.rstrip()}\n{suffix}".strip()


def build_gguf_rewrite_prompt(caption_start: str, draft: str) -> str:
    clean_start = " ".join(str(caption_start or "").split())
    parts = [
        "Rewrite the draft below into exactly one natural-language image description paragraph.",
        "Keep only visible image content.",
        "Remove instructions, planning, bullets, numbered steps, labels, reasoning, and prompt echo.",
        "Do not mention rewriting or analysis.",
        "Return only the final paragraph.",
    ]
    if clean_start:
        parts.append(f"Begin the paragraph exactly with: {clean_start}")
    parts.append("Draft:")
    parts.append(str(draft or "").strip())
    return "\n".join(parts).strip()


def build_bf16_rewrite_prompt(caption_start: str, draft: str) -> str:
    clean_start = " ".join(str(caption_start or "").split())
    parts = [
        "Convert the text below into exactly one final image description paragraph.",
        "Keep only visible image content.",
        "Remove analysis, headings, bullets, numbered lists, prompt echo, and any explanation of the task.",
        "Return only the final paragraph.",
    ]
    if clean_start:
        parts.append(f"Begin the paragraph exactly with: {clean_start}")
    parts.append("Text:")
    parts.append(str(draft or "").strip())
    return "\n".join(parts).strip()


def tune_gguf_description_settings(settings: dict[str, Any]) -> dict[str, Any]:
    tuned = dict(settings)
    tuned["temperature"] = min(0.2, float(settings.get("temperature") or 1.0))
    tuned["top_p"] = min(0.9, float(settings.get("top_p") or 1.0))
    tuned["top_k"] = min(40, int(settings.get("top_k") or 50))
    return tuned


def clean_response_text(text: object) -> str:
    if isinstance(text, dict):
        for key in ("answer", "content", "text", "response"):
            if key in text:
                return clean_response_text(text.get(key))
        return " ".join(str(value) for value in text.values() if str(value).strip()).strip()
    if isinstance(text, (list, tuple)):
        return " ".join(clean_response_text(part) for part in text if str(part).strip()).strip()
    clean = str(text or "").strip()
    clean = re.sub(r"<\|channel\>thought\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<\|channel\>\w+\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<\|.*?\|>", "", clean)
    return " ".join(clean.split())


def _instruction_markers() -> tuple[str, ...]:
    return (
        "Execution:",
        "*Subject:",
        "*Setting:",
        "*Background:",
        "*Colors:",
        "Describe the main subject",
        "Describe the setting/background",
        "Describe the colors and overall tone",
    )


def extract_final_description(text: str, caption_start: str) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return ""
    markers = _instruction_markers()
    numbered_instruction = re.search(r'(?:^|\s)[1-9]\.\s+(?:Describe|Analyze|Write|Focus|Return)\b', clean, flags=re.IGNORECASE)
    starter = " ".join(str(caption_start or "").split()).strip()
    if starter:
        starter_index = clean.find(starter)
        if starter_index >= 0:
            candidate = clean[starter_index:].strip()
            if not any(marker in candidate for marker in markers) and not numbered_instruction:
                return candidate
    for marker in ("Final answer:", "Final:", "Answer:"):
        marker_index = clean.find(marker)
        if marker_index >= 0:
            candidate = clean[marker_index + len(marker):].strip()
            if candidate and not any(marker in candidate for marker in markers):
                return candidate
    if "Here's a thinking process" in clean and ". " in clean:
        candidate = clean.split("Here's a thinking process", 1)[-1]
        starter_index = candidate.find("This image")
        if starter_index >= 0:
            candidate = candidate[starter_index:].strip()
            if not any(marker in candidate for marker in markers):
                return candidate
    if any(marker in clean for marker in markers) or numbered_instruction:
        return ""
    return clean


def salvage_description(text: str) -> str:
    clean = clean_response_text(text)
    if not clean:
        return ""
    clean = re.sub(r'^"[^"]+"\.\s*', "", clean).strip()
    segments: list[str] = []
    for segment in re.split(r"(?<=[.!?])\s+", clean):
        part = str(segment or "").strip().strip('"')
        if not part:
            continue
        if re.fullmatch(r"\d+\.", part):
            continue
        if re.match(r"^(?:\d+\.\s*)?(?:Describe|Write|Output|Return|Begin|Keep|Remove|Do not|Analyze|Focus)\b", part, flags=re.IGNORECASE):
            continue
        if any(marker in part for marker in _instruction_markers()):
            continue
        segments.append(part)
    if segments:
        return " ".join(segments)
    labeled_parts: list[str] = []
    for label in ("Subject", "Setting", "Background", "Colors"):
        match = re.search(rf"\*{label}:\s*(.+?)(?=(?:\s*\*[A-Za-z]+:|$))", clean)
        if match:
            piece = re.sub(r"^[\-\:\s]+", "", match.group(1)).strip().rstrip(".")
            piece = piece.replace("*", " ").strip()
            piece = re.sub(r"^[^-]+-\s*", "", piece).strip()
            if piece:
                labeled_parts.append(piece)
    if labeled_parts:
        return ", ".join(labeled_parts).strip() + "."
    return ""


def classify_gguf_description(raw_text: str, caption_start: str) -> dict[str, str]:
    clean = clean_response_text(raw_text)
    extracted = extract_final_description(clean, caption_start)
    if extracted:
        reason = "ok"
    elif not clean:
        reason = "empty"
    elif any(marker in clean for marker in _instruction_markers()):
        reason = "instruction_text"
    else:
        reason = "malformed_output"
    return {
        "raw_excerpt": excerpt_text(raw_text),
        "clean_excerpt": excerpt_text(clean),
        "description": extracted,
        "reason": reason,
    }


def excerpt_text(text: object, limit: int = 220) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."
