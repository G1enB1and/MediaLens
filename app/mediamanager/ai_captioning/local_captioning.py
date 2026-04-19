from __future__ import annotations

import csv
import argparse
import contextlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image as PilImage
from PIL.ImageOps import exif_transpose


TAG_MODEL_ID = "SmilingWolf/wd-swinv2-tagger-v3"
CAPTION_MODEL_ID = "internlm/internlm-xcomposer2-vl-1_8b"
GEMMA4_MODEL_ID = "google/gemma-4-E2B-it"

DEFAULT_CAPTION_PROMPT = (
    "Please provide a description of this image in natural language paragraph style. "
    "Describe this woman's body type, proportions, and posture in emotionally rich, artistic language. "
    "Focus on the curves, tone, and overall visual balance. Also include make up, clothing (if any), "
    "hair, background, and colors. Emphasize elegance, softness, or power where appropriate. "
    "Use the following tags as context: {tags}"
)
DEFAULT_CAPTION_START = "This image showcases "
DEFAULT_BAD_WORDS = "Appears, Seems, Possibly"

KAOMOJIS = {
    "0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", "<|>_<|>", "=_=",
    ">_<", "3_3", "6_9", ">_o", "@_@", "^_^", "o_o", "u_u", "x_x",
    "|_|", "||_||",
}


@dataclass(frozen=True)
class LocalAiSettings:
    models_dir: Path
    tag_model_id: str = TAG_MODEL_ID
    caption_model_id: str = CAPTION_MODEL_ID
    tag_min_probability: float = 0.35
    tag_max_tags: int = 75
    tags_to_exclude: str = ""
    tag_prompt: str = ""
    tag_write_mode: str = "union"
    caption_prompt: str = DEFAULT_CAPTION_PROMPT
    caption_start: str = DEFAULT_CAPTION_START
    description_write_mode: str = "overwrite"
    device: str = "gpu"
    gpu_index: int = 0
    load_in_4_bit: bool = False
    bad_words: str = DEFAULT_BAD_WORDS
    forced_words: str = ""
    min_new_tokens: int = 1
    max_new_tokens: int = 200
    num_beams: int = 1
    length_penalty: float = 1.0
    do_sample: bool = False
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 1.0
    repetition_penalty: float = 1.0
    no_repeat_ngram_size: int = 3


@dataclass(frozen=True)
class LocalAiResult:
    path: str
    tags: list[str]
    description: str


class DependencyMissingError(RuntimeError):
    pass


def project_models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "local_ai_models"


def available_models() -> list[dict[str, str]]:
    return [
        {"id": TAG_MODEL_ID, "kind": "tagger", "label": "WD SwinV2 Tagger v3"},
        {"id": CAPTION_MODEL_ID, "kind": "captioner", "label": "InternLM XComposer2 VL 1.8B"},
    ]


def _split_escaped_csv(text: str) -> list[str]:
    if not str(text or "").strip():
        return []
    parts = re.split(r"(?<!\\),", str(text))
    return [part.strip().replace(r"\,", ",") for part in parts if part.strip()]


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _resolve_local_or_remote_model(models_dir: Path, model_id: str, marker_names: Iterable[str]) -> str:
    models_dir = Path(models_dir)
    candidate = models_dir / model_id
    if any((candidate / marker).is_file() for marker in marker_names):
        return str(candidate)
    return model_id


def _hf_download(models_dir: Path, model_id: str, filename: str) -> str:
    try:
        import huggingface_hub
    except Exception as exc:
        raise DependencyMissingError("huggingface-hub is required for local AI model downloads.") from exc

    local_dir = Path(models_dir) / model_id
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename
    if local_path.is_file():
        return str(local_path)
    return huggingface_hub.hf_hub_download(model_id, filename=filename, local_dir=str(local_dir))


def _ensure_hf_modules_cache(models_dir: Path) -> None:
    cache_dir = Path(models_dir) / ".hf_modules_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_MODULES_CACHE", str(cache_dir))


def _open_local_ai_image(source_path: Path, mode: str = "RGB") -> PilImage.Image:
    source_path = Path(source_path)
    PilImage.MAX_IMAGE_PIXELS = None
    try:
        with PilImage.open(source_path) as image:
            image.load()
            return exif_transpose(image).convert(mode)
    except Exception as first_exc:
        try:
            data = source_path.read_bytes()
            with PilImage.open(BytesIO(data)) as image:
                image.load()
                return exif_transpose(image).convert(mode)
        except Exception as second_exc:
            message = str(first_exc) or str(second_exc) or "unknown image decode error"
            raise RuntimeError(f"Could not open image for local AI ({source_path.name}): {message}") from second_exc


class WdSwinV2Tagger:
    def __init__(self, settings: LocalAiSettings) -> None:
        try:
            import numpy as np
            from onnxruntime import InferenceSession
        except Exception as exc:
            raise DependencyMissingError("onnxruntime and numpy are required for WD tag generation.") from exc

        self.np = np
        model_path = Path(settings.models_dir) / settings.tag_model_id / "model.onnx"
        tags_path = Path(settings.models_dir) / settings.tag_model_id / "selected_tags.csv"
        if not model_path.is_file():
            model_path = Path(_hf_download(settings.models_dir, settings.tag_model_id, "model.onnx"))
        if not tags_path.is_file():
            tags_path = Path(_hf_download(settings.models_dir, settings.tag_model_id, "selected_tags.csv"))

        self.session = InferenceSession(str(model_path))
        self.tags: list[str] = []
        self.rating_indices: set[int] = set()
        with open(tags_path, "r", encoding="utf-8", newline="") as tags_file:
            for index, row in enumerate(csv.DictReader(tags_file)):
                tag = str(row.get("name") or "").strip()
                if tag not in KAOMOJIS:
                    tag = tag.replace("_", " ")
                self.tags.append(tag)
                if str(row.get("category") or "") == "9":
                    self.rating_indices.add(index)

    def _prepare_image(self, source_path: Path):
        image = _open_local_ai_image(source_path, "RGBA")
        canvas = PilImage.new("RGBA", image.size, (255, 255, 255))
        canvas.alpha_composite(image)
        image = canvas.convert("RGB")
        max_dimension = max(image.size)
        square = PilImage.new("RGB", (max_dimension, max_dimension), (255, 255, 255))
        square.paste(image, ((max_dimension - image.width) // 2, (max_dimension - image.height) // 2))
        _, input_dimension, *_ = self.session.get_inputs()[0].shape
        if max_dimension != input_dimension:
            square = square.resize((input_dimension, input_dimension), resample=PilImage.Resampling.BICUBIC)
        image_array = self.np.array(square, dtype=self.np.float32)
        image_array = image_array[:, :, ::-1]
        return self.np.expand_dims(image_array, axis=0)

    def generate(self, source_path: Path, settings: LocalAiSettings) -> list[str]:
        image_array = self._prepare_image(source_path)
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        probabilities = self.session.run([output_name], {input_name: image_array})[0][0].astype(self.np.float32)
        excluded = {tag.casefold() for tag in _split_escaped_csv(settings.tags_to_exclude)}
        tags_and_probabilities: list[tuple[str, float]] = []
        for index, (tag, probability) in enumerate(zip(self.tags, probabilities)):
            if index in self.rating_indices:
                continue
            if float(probability) < float(settings.tag_min_probability):
                continue
            if tag.casefold() in excluded:
                continue
            tags_and_probabilities.append((tag, float(probability)))
        tags_and_probabilities.sort(key=lambda item: item[1], reverse=True)
        return [tag for tag, _probability in tags_and_probabilities[: max(1, int(settings.tag_max_tags))]]


class XComposer2Captioner:
    def __init__(self, settings: LocalAiSettings) -> None:
        _ensure_hf_modules_cache(settings.models_dir)
        try:
            import torch
            from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:
            raise DependencyMissingError("torch and transformers are required for XComposer2 captions.") from exc

        self.torch = torch
        self.config_class = AutoConfig
        self.tokenizer_class = AutoTokenizer
        self.model_class = AutoModelForCausalLM
        self.device = self._device(settings)
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        model_id = _resolve_local_or_remote_model(settings.models_dir, settings.caption_model_id, ["config.json"])
        self._patch_local_xcomposer_clip_path(Path(model_id), settings.models_dir)
        config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
        self._patch_xcomposer_config(config, Path(model_id))
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        load_args = {"trust_remote_code": True, "use_safetensors": True, "low_cpu_mem_usage": False}
        if self.device.type == "cuda":
            load_args["dtype"] = self.dtype
        self.model = AutoModelForCausalLM.from_pretrained(model_id, config=config, **load_args)
        if hasattr(self.model, "generation_config") and hasattr(self.model.config, "max_length"):
            try:
                self.model.generation_config.max_length = int(self.model.config.max_length)
                delattr(self.model.config, "max_length")
            except Exception:
                pass
        self.model.eval()
        self.model.to(self.device)
        self._patch_clip_vision_forward()

    @staticmethod
    def _patch_xcomposer_config(config, model_path: Path) -> None:
        raw_config = {}
        config_path = model_path / "config.json"
        if config_path.is_file():
            try:
                raw_config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                raw_config = {}
        for key, default in (("max_length", 4096), ("img_size", 490)):
            if not hasattr(config, key):
                setattr(config, key, raw_config.get(key, default))

    @staticmethod
    def _patch_local_xcomposer_clip_path(model_path: Path, models_dir: Path) -> None:
        if not model_path.is_dir():
            return
        build_mlp = model_path / "build_mlp.py"
        modeling = model_path / "modeling_internlm_xcomposer2.py"
        local_clip = Path(models_dir) / "openai" / "clip-vit-large-patch14-336"
        if not build_mlp.is_file() or not (local_clip / "config.json").is_file():
            return
        try:
            text = build_mlp.read_text(encoding="utf-8")
            remote_line = "vision_tower = 'openai/clip-vit-large-patch14-336'"
            local_line = f"vision_tower = {str(local_clip).replace(chr(92), '/')!r}"
            if remote_line in text:
                text = text.replace(remote_line, local_line)
            text = text.replace("return CLIPVisionTower(vision_tower, delay_load=True)", "return CLIPVisionTower(vision_tower)")
            eager_init = "        self.load_model()\n        self.resize_pos()"
            lazy_init = "        # Load lazily after Transformers finishes model construction.\n        pass"
            if eager_init in text:
                text = text.replace(eager_init, lazy_init)
            eager_loaded = "        self.is_loaded = True"
            lazy_loaded = "        self.is_loaded = True\n        self.resize_pos()"
            if lazy_loaded not in text and eager_loaded in text:
                text = text.replace(eager_loaded, lazy_loaded)
            old_cache_line = "            past_length = past_key_values[0][0].shape[2]"
            new_cache_line = (
                "            past_length = past_key_values.get_seq_length() "
                "if hasattr(past_key_values, 'get_seq_length') else past_key_values[0][0].shape[2]"
            )
            old_model_cache_line = "            past_key_values_length = past_key_values[0][0].shape[2]"
            new_model_cache_line = (
                "            past_key_values_length = past_key_values.get_seq_length() "
                "if hasattr(past_key_values, 'get_seq_length') else past_key_values[0][0].shape[2]"
            )
            if old_cache_line in text:
                text = text.replace(old_cache_line, new_cache_line)
            build_mlp.write_text(text, encoding="utf-8")
            for py_file in model_path.glob("modeling_*.py"):
                modeling_text = py_file.read_text(encoding="utf-8")
                if old_cache_line in modeling_text:
                    modeling_text = modeling_text.replace(old_cache_line, new_cache_line)
                if old_model_cache_line in modeling_text:
                    modeling_text = modeling_text.replace(old_model_cache_line, new_model_cache_line)
                modeling_text = modeling_text.replace(
                    "'past_key_values': past_key_values,",
                    "'past_key_values': None if kwargs.get('use_cache') is False else past_key_values,",
                )
                modeling_text = modeling_text.replace(
                    "        for idx, decoder_layer in enumerate(self.layers):",
                    "        if hasattr(past_key_values, 'get_seq_length'):\n            past_key_values = None\n\n        for idx, decoder_layer in enumerate(self.layers):",
                )
                py_file.write_text(modeling_text, encoding="utf-8")
        except Exception:
            pass

    def _device(self, settings: LocalAiSettings):
        torch = self.torch
        if str(settings.device or "").lower() == "gpu" and torch.cuda.is_available():
            return torch.device(f"cuda:{max(0, int(settings.gpu_index))}")
        return torch.device("cpu")

    def _patch_clip_vision_forward(self) -> None:
        def patched_forward(self_, images):
            if not self_.is_loaded:
                self_.load_model()
            if type(images) is list:
                image_features = []
                for image in images:
                    image_forward_out = self_.vision_tower(
                        image.to(device=self_.device, dtype=self_.dtype).unsqueeze(0),
                        output_hidden_states=True,
                        interpolate_pos_encoding=True,
                    )
                    image_features.append(self_.feature_select(image_forward_out).to(image.dtype))
                return image_features
            image_forward_outs = self_.vision_tower(
                images.to(device=self_.device, dtype=self_.dtype),
                output_hidden_states=True,
                interpolate_pos_encoding=True,
            )
            return self_.feature_select(image_forward_outs).to(images.dtype)

        for module_name, module in list(sys.modules.items()):
            if "build_mlp" in module_name and hasattr(module, "CLIPVisionTower"):
                try:
                    module.CLIPVisionTower.forward = patched_forward
                except Exception:
                    pass

    @staticmethod
    def _format_prompt(prompt: str) -> str:
        return f"[UNUSED_TOKEN_146]user\n<ImageHere>{prompt}[UNUSED_TOKEN_145]\n[UNUSED_TOKEN_146]assistant\n"

    def _bad_words_ids(self, text: str):
        words = _split_escaped_csv(text)
        if not words:
            return None
        words = words + [f" {word}" for word in words]
        return self.tokenizer(words, add_special_tokens=False).input_ids

    def _forced_words_ids(self, text: str):
        groups = _split_escaped_csv(text)
        out = []
        for group in groups:
            words = [word.strip().replace(r"\|", "|") for word in re.split(r"(?<!\\)\|", group) if word.strip()]
            if words:
                out.append(self.tokenizer(words, add_special_tokens=False).input_ids)
        return out or None

    def _prepare_inputs(self, source_path: Path, prompt: str, caption_start: str):
        torch = self.torch
        pil_image = _open_local_ai_image(source_path, "RGB")
        text = self._format_prompt(prompt) + caption_start
        processed_image = self.model.vis_processor(pil_image).unsqueeze(0).to(self.device)
        if self.device.type == "cuda":
            processed_image = processed_image.to(dtype=self.dtype)
        if hasattr(self.model, "vit") and hasattr(self.model.vit, "is_loaded") and not self.model.vit.is_loaded:
            self.model.vit.load_model()
            self.model.vit.to(self.device)
        image_embeddings, *_ = self.model.img2emb(processed_image)
        input_embeddings_parts = []
        image_mask_parts = []
        for text_part in text.split("<ImageHere>"):
            part_token_ids = self.tokenizer(text_part, return_tensors="pt").input_ids.to(self.device)
            part_embeddings = self.model.model.tok_embeddings(part_token_ids)
            input_embeddings_parts.append(part_embeddings)
            image_mask_parts.append(torch.zeros(part_embeddings.shape[:2]))
        input_embeddings_parts.insert(1, image_embeddings[0].unsqueeze(0))
        image_mask_parts.insert(1, torch.ones(1, image_embeddings[0].shape[0]))
        input_embeddings = torch.cat(input_embeddings_parts, dim=1).to(self.device)
        image_mask = torch.cat(image_mask_parts, dim=1).bool().to(self.device)
        eos_token_id = [
            self.tokenizer.eos_token_id,
            self.tokenizer.convert_tokens_to_ids(["[UNUSED_TOKEN_145]"])[0],
        ]
        return {"inputs_embeds": input_embeddings, "im_mask": image_mask, "eos_token_id": eos_token_id}

    def generate(self, source_path: Path, tags: list[str], settings: LocalAiSettings) -> str:
        prompt = settings.caption_prompt.replace("{tags}", ", ".join(tags))
        inputs = self._prepare_inputs(source_path, prompt, settings.caption_start)
        with self.torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                bad_words_ids=self._bad_words_ids(settings.bad_words),
                force_words_ids=self._forced_words_ids(settings.forced_words),
                min_new_tokens=max(1, int(settings.min_new_tokens)),
                max_new_tokens=max(1, int(settings.max_new_tokens)),
                num_beams=max(1, int(settings.num_beams)),
                length_penalty=float(settings.length_penalty),
                do_sample=bool(settings.do_sample),
                temperature=float(settings.temperature),
                top_k=int(settings.top_k),
                top_p=float(settings.top_p),
                repetition_penalty=float(settings.repetition_penalty),
                no_repeat_ngram_size=max(0, int(settings.no_repeat_ngram_size)),
                use_cache=False,
            )
        text = self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        text = text.split("[UNUSED_TOKEN_145]")[0].strip()
        formatted_prompt = self._format_prompt(prompt)
        if text.startswith(formatted_prompt):
            text = text[len(formatted_prompt):].strip()
        if settings.caption_start.strip() and not text.startswith(settings.caption_start.strip()):
            text = f"{settings.caption_start.strip()} {text}".strip()
        return " ".join(text.split())


class Gemma4MultimodalModel:
    def __init__(self, settings: LocalAiSettings) -> None:
        _ensure_hf_modules_cache(settings.models_dir)
        try:
            import torch
            import transformers
            from transformers import AutoProcessor
        except Exception as exc:
            raise DependencyMissingError("torch, transformers, and accelerate are required for Gemma 4 local AI.") from exc

        self.torch = torch
        self.device = self._device(settings)
        model_id = _resolve_local_or_remote_model(settings.models_dir, GEMMA4_MODEL_ID, ["config.json", "model.safetensors"])
        self.processor = AutoProcessor.from_pretrained(model_id)
        model_class = getattr(transformers, "AutoModelForMultimodalLM", None) or getattr(transformers, "AutoModelForImageTextToText", None)
        if model_class is None:
            raise DependencyMissingError("This transformers version does not include a Gemma 4 image-text model loader.")
        load_args = {"dtype": "auto"}
        if self.device.type == "cuda":
            load_args["device_map"] = {"": int(self.device.index or 0)}
        self.model = model_class.from_pretrained(model_id, **load_args)
        if self.device.type != "cuda":
            self.model.to(self.device)
        self.model.eval()

    def _device(self, settings: LocalAiSettings):
        torch = self.torch
        if str(settings.device or "").lower() == "gpu" and torch.cuda.is_available():
            return torch.device(f"cuda:{max(0, int(settings.gpu_index))}")
        return torch.device("cpu")

    @staticmethod
    def _clean_response(text: object) -> str:
        if isinstance(text, dict):
            for key in ("answer", "content", "text", "response"):
                if key in text:
                    return Gemma4MultimodalModel._clean_response(text.get(key))
            return " ".join(str(value) for value in text.values() if str(value).strip()).strip()
        if isinstance(text, (list, tuple)):
            return " ".join(Gemma4MultimodalModel._clean_response(part) for part in text if str(part).strip()).strip()
        clean = str(text or "").strip()
        clean = re.sub(r"<\|channel\>thought.*?<channel\|>", "", clean, flags=re.DOTALL)
        clean = re.sub(r"<\|.*?\|>", "", clean)
        return " ".join(clean.split())

    def _generate_text(self, source_path: Path, prompt: str, settings: LocalAiSettings, max_new_tokens: int) -> str:
        image = _open_local_ai_image(source_path, "RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = {key: value.to(self.model.device) if hasattr(value, "to") else value for key, value in inputs.items()}
        input_len = inputs["input_ids"].shape[-1]
        generation_args = {
            "max_new_tokens": max(1, int(max_new_tokens)),
            "do_sample": bool(settings.do_sample),
            "temperature": float(settings.temperature),
            "top_k": int(settings.top_k),
            "top_p": float(settings.top_p),
            "repetition_penalty": float(settings.repetition_penalty),
        }
        with self.torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generation_args)
        response = self.processor.decode(output_ids[0][input_len:], skip_special_tokens=False)
        try:
            parsed = self.processor.parse_response(response)
        except Exception:
            parsed = response
        text = self._clean_response(parsed)
        if not text:
            raise RuntimeError("Gemma 4 returned an empty response.")
        return text

    def generate_tags(self, source_path: Path, settings: LocalAiSettings) -> list[str]:
        extra_rules = str(settings.tag_prompt or "").strip()
        prompt = (
            "Generate concise searchable tags for this image. Return only comma-separated tags, "
            "with no sentence, numbering, markdown, or explanation. "
            f"Use at most {max(1, int(settings.tag_max_tags))} tags."
        )
        if extra_rules:
            prompt = f"{prompt}\nRules: {extra_rules}"
        raw = self._generate_text(
            source_path,
            prompt,
            settings,
            max_new_tokens=max(32, min(512, int(settings.tag_max_tags) * 5)),
        )
        json_match = re.search(r"\[[^\]]+\]", raw)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    raw = ", ".join(str(item) for item in parsed)
            except Exception:
                pass
        raw = re.sub(r"^(tags?|keywords?)\s*:\s*", "", raw, flags=re.IGNORECASE).strip()
        raw = raw.replace("\n", ",")
        tags = []
        for part in re.split(r"[,;|]", raw):
            tag = re.sub(r"^[\-\*\d\.\)\s]+", "", part).strip().strip("\"'")
            if tag:
                tags.append(tag)
        excluded = {tag.casefold() for tag in _split_escaped_csv(settings.tags_to_exclude)}
        tags = [tag for tag in _dedupe_preserve_order(tags) if tag.casefold() not in excluded]
        tags = tags[: max(1, int(settings.tag_max_tags))]
        if not tags:
            raise RuntimeError(f"Gemma 4 returned no parseable tags. Raw response: {raw[:240]}")
        return tags

    def generate_description(self, source_path: Path, tags: list[str], settings: LocalAiSettings) -> str:
        prompt = settings.caption_prompt.replace("{tags}", ", ".join(tags))
        text = self._generate_text(source_path, prompt, settings, max_new_tokens=max(1, int(settings.max_new_tokens)))
        if settings.caption_start.strip() and not text.startswith(settings.caption_start.strip()):
            text = f"{settings.caption_start.strip()} {text}".strip()
        text = " ".join(text.split())
        if not text:
            raise RuntimeError("Gemma 4 returned no description.")
        return text


class LocalAiCaptioningService:
    def __init__(self, settings: LocalAiSettings, log: Callable[[str], None] | None = None) -> None:
        self.settings = settings
        self.log = log or (lambda _msg: None)
        self._tagger: WdSwinV2Tagger | None = None
        self._captioner: XComposer2Captioner | None = None
        self._gemma4: Gemma4MultimodalModel | None = None

    def _get_gemma4(self) -> Gemma4MultimodalModel:
        if self._gemma4 is None:
            self.log(f"Loading local AI Gemma 4 model: {GEMMA4_MODEL_ID}")
            self._gemma4 = Gemma4MultimodalModel(self.settings)
        return self._gemma4

    def _get_tagger(self) -> WdSwinV2Tagger:
        if self.settings.tag_model_id == GEMMA4_MODEL_ID:
            return self._get_gemma4()
        if self._tagger is None:
            self.log(f"Loading local AI tagger: {self.settings.tag_model_id}")
            self._tagger = WdSwinV2Tagger(self.settings)
        return self._tagger

    def _get_captioner(self) -> XComposer2Captioner:
        if self.settings.caption_model_id == GEMMA4_MODEL_ID:
            return self._get_gemma4()
        if self._captioner is None:
            self.log(f"Loading local AI caption model: {self.settings.caption_model_id}")
            self._captioner = XComposer2Captioner(self.settings)
        return self._captioner

    def generate(self, source_path: str | Path, original_path: str | Path | None = None) -> LocalAiResult:
        source = Path(source_path)
        tags = self.generate_tags(source)
        description = self.generate_description(source, tags)
        return LocalAiResult(path=str(original_path or source_path), tags=tags, description=description)

    def generate_tags(self, source_path: str | Path) -> list[str]:
        tagger = self._get_tagger()
        if isinstance(tagger, Gemma4MultimodalModel):
            return tagger.generate_tags(Path(source_path), self.settings)
        return tagger.generate(Path(source_path), self.settings)

    def generate_description(self, source_path: str | Path, tags: list[str]) -> str:
        captioner = self._get_captioner()
        if isinstance(captioner, Gemma4MultimodalModel):
            return captioner.generate_description(Path(source_path), tags, self.settings)
        return captioner.generate(Path(source_path), tags, self.settings)


def apply_result_to_database(conn: sqlite3.Connection, result: LocalAiResult, settings: LocalAiSettings) -> None:
    from app.mediamanager.db.media_repo import get_media_by_path
    from app.mediamanager.db.metadata_repo import get_media_metadata, upsert_media_metadata
    from app.mediamanager.db.tags_repo import attach_tags, list_media_tags, set_media_tags

    media = get_media_by_path(conn, result.path)
    if not media:
        return
    media_id = int(media["id"])

    generated_tags = _dedupe_preserve_order(result.tags)
    current_tags = list_media_tags(conn, media_id)
    tag_mode = str(settings.tag_write_mode or "union").casefold()
    if generated_tags:
        if tag_mode in {"append", "union"}:
            attach_tags(conn, media_id, generated_tags)
        elif tag_mode == "skip_existing":
            if not current_tags:
                set_media_tags(conn, media_id, generated_tags)
        else:
            set_media_tags(conn, media_id, generated_tags)

    meta = get_media_metadata(conn, media_id) or {}
    current_description = str(meta.get("description") or "").strip()
    description = str(result.description or "").strip()
    desc_mode = str(settings.description_write_mode or "overwrite").casefold()
    if description and not (desc_mode == "skip_existing" and current_description):
        if desc_mode == "append" and current_description:
            description = f"{current_description}\n\n{description}"
        upsert_media_metadata(
            conn,
            media_id,
            title=meta.get("title"),
            description=description,
            notes=meta.get("notes"),
            embedded_tags=meta.get("embedded_tags"),
            embedded_comments=meta.get("embedded_comments"),
            ai_prompt=meta.get("ai_prompt"),
            ai_negative_prompt=meta.get("ai_negative_prompt"),
            ai_params=meta.get("ai_params"),
        )


def apply_tags_to_database(conn: sqlite3.Connection, path: str, tags: list[str], settings: LocalAiSettings) -> None:
    apply_result_to_database(conn, LocalAiResult(str(path), tags, ""), settings)


def apply_description_to_database(conn: sqlite3.Connection, path: str, description: str, settings: LocalAiSettings) -> None:
    apply_result_to_database(conn, LocalAiResult(str(path), [], description), settings)


def _settings_from_json(raw: str) -> LocalAiSettings:
    payload = json.loads(raw or "{}")
    if "models_dir" in payload:
        payload["models_dir"] = Path(payload["models_dir"])
    return LocalAiSettings(**payload)


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens local AI captioning task.")
    parser.add_argument("--operation", choices=("tags", "description"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    parser.add_argument("--tags-json", default="[]")
    args = parser.parse_args()

    try:
        settings = _settings_from_json(args.settings_json)
        service = LocalAiCaptioningService(settings, lambda message: print(message, file=sys.stderr, flush=True))
        if args.operation == "tags":
            with contextlib.redirect_stdout(sys.stderr):
                tags = service.generate_tags(Path(args.source))
            print(json.dumps({"ok": True, "tags": tags}, ensure_ascii=False), flush=True)
            return 0
        tags = json.loads(args.tags_json or "[]")
        with contextlib.redirect_stdout(sys.stderr):
            description = service.generate_description(Path(args.source), [str(tag) for tag in tags])
        print(json.dumps({"ok": True, "description": description}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
