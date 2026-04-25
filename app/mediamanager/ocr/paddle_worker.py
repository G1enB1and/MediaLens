from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


def _settings_from_json(raw: str) -> dict[str, Any]:
    return dict(json.loads(raw or "{}"))


def _flatten_text_items(value: Any) -> list[tuple[str, float | None]]:
    items: list[tuple[str, float | None]] = []
    if value is None:
        return items
    json_value = getattr(value, "json", None)
    if isinstance(json_value, dict):
        items.extend(_flatten_text_items(json_value))
    if isinstance(value, dict):
        rec_texts = value.get("rec_texts")
        rec_scores = value.get("rec_scores") or []
        if isinstance(rec_texts, (list, tuple)):
            for index, rec_text in enumerate(rec_texts):
                if not str(rec_text or "").strip():
                    continue
                score = rec_scores[index] if isinstance(rec_scores, (list, tuple)) and index < len(rec_scores) else None
                try:
                    score_value = float(score) if score is not None else None
                except Exception:
                    score_value = None
                items.append((str(rec_text).strip(), score_value))
        text = value.get("text") or value.get("rec_text") or value.get("transcription")
        score = value.get("confidence") or value.get("score") or value.get("rec_score")
        if text:
            try:
                score_value = float(score) if score is not None else None
            except Exception:
                score_value = None
            items.append((str(text).strip(), score_value))
        for child in value.values():
            if isinstance(child, (dict, list, tuple)):
                items.extend(_flatten_text_items(child))
        return items
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[1], (list, tuple)) and value[1]:
            text = value[1][0]
            score = value[1][1] if len(value[1]) > 1 else None
            if isinstance(text, str):
                try:
                    score_value = float(score) if score is not None else None
                except Exception:
                    score_value = None
                items.append((text.strip(), score_value))
        for child in value:
            if isinstance(child, (dict, list, tuple)):
                items.extend(_flatten_text_items(child))
        return items
    return items


def _dedupe_lines(items: list[tuple[str, float | None]]) -> list[tuple[str, float | None]]:
    out: list[tuple[str, float | None]] = []
    seen: set[str] = set()
    for text, score in items:
        clean = re.sub(r"\s+", " ", str(text or "").strip())
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append((clean, score))
    return out


def _prepare_source_image(source: Path, profile: str, temp_dir: Path) -> Path:
    try:
        from PIL import Image, ImageOps
    except Exception:
        return source
    try:
        with Image.open(source) as img:
            img.load()
            if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                background.alpha_composite(rgba)
                img = background.convert("RGB")
            else:
                img = img.convert("RGB")
            img = ImageOps.autocontrast(img)
            max_side = max(img.size)
            min_side = min(img.size)
            scale = 1.0
            if profile == "accurate" and max_side < 2200:
                scale = min(2.0, 2200 / max(max_side, 1))
            elif profile == "fast" and min_side < 900:
                scale = min(1.5, 900 / max(min_side, 1))
            if scale > 1.05:
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
            temp_dir.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(prefix="medialens_ocr_", suffix=".png", dir=str(temp_dir), delete=False)
            handle.close()
            out = Path(handle.name)
            img.save(out)
            return out
    except Exception:
        return source


def _run_paddle(source: Path, profile: str, settings: dict[str, Any]) -> dict[str, Any]:
    cache_dir = str(settings.get("cache_dir") or "").strip()
    if not cache_dir:
        cache_dir = str(Path(__file__).resolve().parents[3] / "local_ai_models" / "paddleocr_cache")
    cache_root = Path(cache_dir)
    home_dir = cache_root / "home"
    temp_dir = cache_root / "tmp"
    for directory in (cache_root, home_dir, temp_dir, cache_root / "paddle", cache_root / "ppocr", cache_root / "xdg", cache_root / "hf_home"):
        directory.mkdir(parents=True, exist_ok=True)
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache_root)
    os.environ["PADDLE_HOME"] = str(cache_root / "paddle")
    os.environ["PPOCR_HOME"] = str(cache_root / "ppocr")
    os.environ["XDG_CACHE_HOME"] = str(cache_root / "xdg")
    os.environ["HF_HOME"] = str(cache_root / "hf_home")
    os.environ["HOME"] = str(home_dir)
    os.environ["USERPROFILE"] = str(home_dir)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    if os.name == "nt":
        os.environ["HOMEDRIVE"] = str(home_dir.drive or "C:")
        os.environ["HOMEPATH"] = str(home_dir)[len(str(home_dir.drive or "")) :] or "\\"
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        raise RuntimeError("PaddleOCR is not installed in the OCR runtime. Install the optional PaddleOCR package first.") from exc

    lang = str(settings.get("lang") or "en").strip() or "en"
    device = str(settings.get("device") or "auto").strip().lower()
    use_gpu = device in {"gpu", "cuda"} or (device == "auto" and bool(settings.get("prefer_gpu", True)))
    common: dict[str, Any] = {
        "lang": lang,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "en_PP-OCRv5_mobile_rec",
        "text_det_limit_side_len": int(settings.get("text_det_limit_side_len") or (1280 if profile == "accurate" else 960)),
        "text_det_limit_type": "max",
        "enable_mkldnn": False,
        "cpu_threads": max(1, int(settings.get("cpu_threads") or 4)),
    }
    common.update({"use_textline_orientation": False})
    if device in {"cpu", "gpu", "cuda"}:
        common["device"] = "gpu" if device in {"gpu", "cuda"} else "cpu"

    try:
        engine = PaddleOCR(**common)
    except Exception as exc:
        if "Unknown argument" not in str(exc):
            raise
        common.pop("device", None)
        try:
            engine = PaddleOCR(**common)
        except Exception as retry_exc:
            if "Unknown argument" not in str(retry_exc):
                raise
            engine = PaddleOCR(lang=lang)

    prepared_source = _prepare_source_image(source, profile, temp_dir)
    try:
        raw = engine.ocr(str(prepared_source))
    except TypeError:
        raw = engine.predict(str(prepared_source))

    lines = _dedupe_lines(_flatten_text_items(raw))
    scores = [score for _text, score in lines if score is not None]
    confidence = float(sum(scores) / len(scores)) if scores else (1.0 if lines else 0.0)
    return {
        "ok": True,
        "source": f"paddle_{profile}",
        "text": "\n".join(text for text, _score in lines).strip(),
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "engine_version": "paddleocr",
        "preprocess_profile": profile,
        "metadata": {
            "line_count": len(lines),
            "scores": scores[:50],
            "lang": lang,
            "device": device,
            "use_gpu_requested": bool(use_gpu),
            "input_path": str(source),
            "prepared_input_path": str(prepared_source),
        },
    }


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens PaddleOCR task.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--profile", choices=("fast", "accurate"), default="fast")
    parser.add_argument("--settings-json", default="{}")
    args = parser.parse_args()
    try:
        source = Path(args.source)
        if not source.is_file():
            raise FileNotFoundError("OCR source image was not found.")
        payload = _run_paddle(source, args.profile, _settings_from_json(args.settings_json))
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
