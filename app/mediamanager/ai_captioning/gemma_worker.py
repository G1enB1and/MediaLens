from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PilImage
from PIL.ImageOps import exif_transpose

from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID


def _settings_from_json(raw: str) -> dict[str, Any]:
    return dict(json.loads(raw or "{}"))


def _models_dir(settings: dict[str, Any]) -> Path:
    raw = str(settings.get("models_dir") or "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[3] / "local_ai_models"


def _configure_hf_cache(settings: dict[str, Any]) -> None:
    # Gemma uses a newer Transformers runtime than InternLM. Keep downloaded
    # model code and caches under a Gemma-specific folder so it cannot affect
    # the working InternLM/XComposer runtime.
    root = _models_dir(settings) / "gemma4_runtime"
    home = root / "hf_home"
    modules = root / "hf_modules_cache"
    home.mkdir(parents=True, exist_ok=True)
    modules.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(home))
    os.environ.setdefault("HF_MODULES_CACHE", str(modules))


def _resolve_model(settings: dict[str, Any], model_id: str) -> str:
    local = _models_dir(settings) / model_id
    if (local / "config.json").is_file():
        return str(local)
    return model_id


def _open_image(source_path: str | Path) -> PilImage.Image:
    source_path = Path(source_path)
    PilImage.MAX_IMAGE_PIXELS = None
    try:
        with PilImage.open(source_path) as image:
            image.load()
            return exif_transpose(image).convert("RGB")
    except Exception:
        data = source_path.read_bytes()
        with PilImage.open(BytesIO(data)) as image:
            image.load()
            return exif_transpose(image).convert("RGB")


def _load_model(settings: dict[str, Any]):
    _configure_hf_cache(settings)
    try:
        import torch
        import transformers
        from transformers import AutoProcessor
    except Exception as exc:
        raise RuntimeError("Gemma 4 is not installed correctly. Install the optional Gemma 4 local AI package and try again.") from exc

    model_id = _resolve_model(settings, GEMMA4_MODEL_ID)
    processor = AutoProcessor.from_pretrained(model_id)
    model_class = getattr(transformers, "AutoModelForMultimodalLM", None)
    if model_class is None:
        model_class = getattr(transformers, "AutoModelForImageTextToText", None)
    if model_class is None:
        raise RuntimeError("Gemma 4 cannot be loaded with the installed optional local AI package.")

    device = str(settings.get("device") or "gpu").lower()
    gpu_index = max(0, int(settings.get("gpu_index") or 0))
    load_args: dict[str, Any] = {"dtype": "auto"}
    if device == "gpu" and torch.cuda.is_available():
        load_args["device_map"] = {"": gpu_index}
    model = model_class.from_pretrained(model_id, **load_args)
    if "device_map" not in load_args:
        model.to(torch.device("cpu"))
    model.eval()
    return torch, processor, model


def _clean_response(text: object) -> str:
    if isinstance(text, dict):
        for key in ("answer", "content", "text", "response"):
            if key in text:
                return _clean_response(text.get(key))
        return " ".join(str(value) for value in text.values() if str(value).strip()).strip()
    if isinstance(text, (list, tuple)):
        return " ".join(_clean_response(part) for part in text if str(part).strip()).strip()
    clean = str(text or "").strip()
    clean = re.sub(r"<\|channel\>thought.*?<channel\|>", "", clean, flags=re.DOTALL)
    clean = re.sub(r"<\|.*?\|>", "", clean)
    return " ".join(clean.split())


def _generate_text(source_path: str, prompt: str, settings: dict[str, Any], max_new_tokens: int) -> str:
    torch, processor, model = _load_model(settings)
    image = _open_image(source_path)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    )
    target_device = getattr(model, "device", None)
    if target_device is not None:
        inputs = {key: value.to(target_device) if hasattr(value, "to") else value for key, value in inputs.items()}
    input_len = inputs["input_ids"].shape[-1]
    generation_args = {
        "max_new_tokens": max(1, int(max_new_tokens)),
        "do_sample": bool(settings.get("do_sample") or False),
        "temperature": float(settings.get("temperature") or 1.0),
        "top_k": int(settings.get("top_k") or 50),
        "top_p": float(settings.get("top_p") or 1.0),
        "repetition_penalty": float(settings.get("repetition_penalty") or 1.0),
    }
    with torch.inference_mode():
        output_ids = model.generate(**inputs, **generation_args)
    response = processor.decode(output_ids[0][input_len:], skip_special_tokens=False)
    if hasattr(processor, "parse_response"):
        try:
            response = processor.parse_response(response)
        except Exception:
            pass
    text = _clean_response(response)
    if not text:
        raise RuntimeError("Gemma 4 returned an empty response.")
    return text


def _split_tags(raw: str, settings: dict[str, Any]) -> list[str]:
    raw = re.sub(r"^(tags?|keywords?)\s*:\s*", "", str(raw or ""), flags=re.IGNORECASE).strip()
    raw = raw.replace("\n", ",")
    tags: list[str] = []
    for part in re.split(r"[,;|]", raw):
        tag = re.sub(r"^[\-\*\d\.\)\s]+", "", part).strip().strip("\"'")
        if tag:
            tags.append(tag)
    excluded = {part.strip().casefold() for part in str(settings.get("tags_to_exclude") or "").split(",") if part.strip()}
    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        key = tag.casefold()
        if key in seen or key in excluded:
            continue
        seen.add(key)
        out.append(tag)
    return out[: max(1, int(settings.get("tag_max_tags") or 75))]


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens Gemma 4 local AI task.")
    parser.add_argument("--operation", choices=("tags", "description"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    parser.add_argument("--tags-json", default="[]")
    args = parser.parse_args()

    try:
        settings = _settings_from_json(args.settings_json)
        if args.operation == "tags":
            prompt = (
                "Generate concise searchable tags for this image. Return only comma-separated tags, "
                f"with at most {max(1, int(settings.get('tag_max_tags') or 75))} tags."
            )
            extra = str(settings.get("tag_prompt") or "").strip()
            if extra:
                prompt = f"{prompt}\nRules: {extra}"
            with contextlib.redirect_stdout(sys.stderr):
                text = _generate_text(args.source, prompt, settings, max(32, min(512, int(settings.get("tag_max_tags") or 75) * 5)))
            tags = _split_tags(text, settings)
            if not tags:
                raise RuntimeError(f"Gemma 4 returned no parseable tags. Raw response: {text[:240]}")
            print(json.dumps({"ok": True, "tags": tags}, ensure_ascii=False), flush=True)
            return 0
        tags = [str(tag) for tag in json.loads(args.tags_json or "[]") if str(tag).strip()]
        prompt_template = str(settings.get("caption_prompt") or "Please describe this image. Use these tags as context: {tags}")
        prompt = prompt_template.replace("{tags}", ", ".join(tags))
        with contextlib.redirect_stdout(sys.stderr):
            description = _generate_text(args.source, prompt, settings, max(1, int(settings.get("max_new_tokens") or 200)))
        caption_start = str(settings.get("caption_start") or "").strip()
        if caption_start and not description.startswith(caption_start):
            description = f"{caption_start} {description}".strip()
        print(json.dumps({"ok": True, "description": description}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
