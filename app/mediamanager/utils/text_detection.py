from __future__ import annotations

import json
import time
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image
from scipy import ndimage

try:
    import cv2
except Exception:  # pragma: no cover - optional runtime dependency
    cv2 = None

try:
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.storage import StorageFile
except Exception:  # pragma: no cover - optional runtime dependency
    Language = None
    BitmapDecoder = None
    OcrEngine = None
    StorageFile = None

try:
    _RESAMPLE = Image.Resampling.BILINEAR
except AttributeError:  # pragma: no cover - Pillow < 9 compatibility
    _RESAMPLE = Image.BILINEAR

TEXT_DETECTION_VERSION = 24
TEXT_MORE_LIKELY_VERSION = 7
TEXT_VERIFICATION_VERSION = 18
_TEXT_LOG_LOCK = Lock()
_TEXT_STAGE1_TO_STAGE2_SCORE = 0.22
_TEXT_STAGE1_DIRECT_TO_OCR_SCORE = 0.68
_TEXT_STAGE1_FALLBACK_DETECTED_SCORE = 0.50
_TEXT_STAGE2_STRONG_DETECTED_SCORE = 0.96
_TEXT_STAGE1_EARLY_EXIT_SCORE = 0.78
_TEXT_RESCUE_MIN_STAGE1_SCORE = 0.24
_TEXT_STAGE_MAX_CANDIDATES = 2


@dataclass(frozen=True)
class _TextRegionSpec:
    name: str
    zone: str
    x0: float
    y0: float
    x1: float
    y1: float


_TEXT_REGION_SPECS: tuple[_TextRegionSpec, ...] = (
    _TextRegionSpec("top_center", "center", 0.14, 0.0, 0.86, 0.28),
    _TextRegionSpec("bottom_center", "center", 0.12, 0.72, 0.88, 1.0),
    _TextRegionSpec("bottom_left", "bottom-left", 0.0, 0.58, 0.42, 1.0),
    _TextRegionSpec("bottom_right", "bottom-right", 0.58, 0.58, 1.0, 1.0),
    _TextRegionSpec("top_left", "top-left", 0.0, 0.0, 0.42, 0.42),
    _TextRegionSpec("top_right", "top-right", 0.58, 0.0, 1.0, 0.42),
    _TextRegionSpec("full_frame", "center", 0.0, 0.0, 1.0, 1.0),
    _TextRegionSpec("center", "center", 0.21, 0.21, 0.79, 0.79),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _text_log_dir() -> Path:
    path = _repo_root() / "logs" / "TextDetection"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _append_text_detection_log(payload: dict) -> None:
    log_path = _text_log_dir() / f"text_detection_{datetime.now(timezone.utc):%Y%m%d}.jsonl"
    line = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    with _TEXT_LOG_LOCK:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")


def _crop_region_by_spec(img: np.ndarray, spec: _TextRegionSpec) -> np.ndarray:
    h, w = img.shape[:2]
    if h <= 0 or w <= 0:
        return img
    x0 = max(0, min(w - 1, int(round(w * spec.x0))))
    y0 = max(0, min(h - 1, int(round(h * spec.y0))))
    x1 = max(x0 + 1, min(w, int(round(w * spec.x1))))
    y1 = max(y0 + 1, min(h, int(round(h * spec.y1))))
    return img[y0:y1, x0:x1]


def _build_stage1_named_variants(region: np.ndarray) -> list[tuple[str, np.ndarray]]:
    variants = _build_stage1_region_variants(region)
    names = ["base", "enhanced", "high_contrast_dark", "high_contrast_light"]
    return [
        (names[idx] if idx < len(names) else f"variant_{idx}", variant)
        for idx, variant in enumerate(variants)
    ]


def _build_stage2_named_variants(region: np.ndarray) -> list[tuple[str, np.ndarray]]:
    return [
        ("base", region),
        ("enhanced", _enhance_region_for_text(region)),
    ]


def _build_ocr_named_variants(
    region: np.ndarray,
    *,
    include_threshold_variants: bool = True,
) -> list[tuple[str, Image.Image]]:
    if region.size == 0:
        return []
    variants: list[tuple[str, Image.Image]] = []
    base = Image.fromarray(region, mode="L")
    variants.append(("base", base))

    rw, rh = base.size
    scale = 1
    if max(rw, rh) < 900:
        scale = 3 if max(rw, rh) < 360 else 2
    if scale > 1:
        base = base.resize(
            (max(1, rw * scale), max(1, rh * scale)),
            resample=Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC,
        )
        variants.append(("upscaled", base))

    arr = np.asarray(base, dtype=np.uint8)
    if include_threshold_variants and arr.size > 0:
        threshold = int(np.percentile(arr, 70))
        binary = np.where(arr >= threshold, 255, 0).astype(np.uint8)
        variants.append(("high_contrast", Image.fromarray(binary, mode="L")))
        variants.append(("inverted", Image.fromarray(255 - binary, mode="L")))

    deduped: list[tuple[str, Image.Image]] = []
    seen: set[tuple[int, int, bytes]] = set()
    for name, variant in variants:
        try:
            key = (variant.size[0], variant.size[1], variant.tobytes()[:128])
        except Exception:
            key = (variant.size[0], variant.size[1], b"")
        if key in seen:
            continue
        seen.add(key)
        deduped.append((name, variant))
    return deduped


def _ocr_available() -> bool:
    return OcrEngine is not None and Language is not None and StorageFile is not None and BitmapDecoder is not None


def _region_supports_stage2_shortcut(region_name: str | None) -> bool:
    return str(region_name or "") in {"top_left", "top_right", "bottom_left", "bottom_right"}


def _region_spec_by_name(region_name: str | None) -> _TextRegionSpec | None:
    return next((item for item in _TEXT_REGION_SPECS if item.name == str(region_name or "")), None)


def _candidate_by_name(candidates: list[dict], region_name: str) -> dict | None:
    return next((item for item in candidates if item.get("name") == region_name), None)


def _evaluate_stage1_region(spec: _TextRegionSpec, working_region: np.ndarray) -> dict:
    best_score = 0.0
    best_likely = False
    best_variation = "base"
    for variation_name, variant in _build_stage1_named_variants(working_region):
        likely, score = _detect_likely_text_presence_array(variant.astype(np.float32))
        if score > best_score:
            best_score = float(score or 0.0)
            best_variation = variation_name
        if likely:
            best_likely = True
    return {
        "name": spec.name,
        "zone": spec.zone,
        "score": round(float(best_score), 3),
        "variation": best_variation,
        "positive": best_likely,
    }


def _evaluate_stage2_region(spec: _TextRegionSpec, working_region: np.ndarray) -> dict:
    best_score = 0.0
    best_verified = False
    best_variation = "base"
    for variation_name, variant in _build_stage2_named_variants(working_region):
        verified, score = _verify_text_presence_opencv_array(variant, max_side=768)
        if score > best_score:
            best_score = float(score or 0.0)
            best_variation = variation_name
        if verified:
            best_verified = True
    return {
        "stage": "stage2",
        "method": "opencv",
        "status": "positive" if best_verified else "negative",
        "zone": spec.zone,
        "region": spec.name,
        "variation": best_variation,
        "confidence": round(float(best_score), 3),
    }


def _verify_text_presence_windows_ocr_variants(
    variants: list[tuple[str, Image.Image]],
) -> tuple[bool, float, str | None]:
    if not _ocr_available():
        return False, 0.0, None
    try:
        best_verified = False
        best_score = 0.0
        best_variant: str | None = None
        with tempfile.TemporaryDirectory(prefix="medialens_ocr_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            for idx, (variant_name, variant) in enumerate(variants):
                temp_path = tmpdir_path / f"ocr_variant_{idx}.png"
                try:
                    variant.save(temp_path)
                    import asyncio
                    verified, score = asyncio.run(_verify_text_presence_windows_ocr_async(temp_path))
                except Exception:
                    verified, score = False, 0.0
                if score > best_score:
                    best_score = float(score or 0.0)
                    best_variant = variant_name
                if verified:
                    best_verified = True
                    best_score = max(best_score, float(score or 0.0))
                    best_variant = variant_name
                    break
        return best_verified, round(float(best_score), 3), best_variant
    except Exception:
        return False, 0.0, None


def _line_cluster_score(
    centers_x: list[float],
    centers_y: list[float],
    heights: list[float],
    box_w: int,
) -> float:
    if len(centers_x) < 3:
        return 0.0

    xs = np.asarray(sorted(centers_x), dtype=np.float32)
    ys = np.asarray(centers_y, dtype=np.float32)
    hs = np.asarray(heights, dtype=np.float32)
    mean_h = max(float(np.mean(hs)), 1.0)
    baseline_consistency = float(np.std(ys) / mean_h)
    if baseline_consistency > 0.90:
        return 0.0

    gaps = np.diff(xs)
    positive_gaps = gaps[gaps > 0]
    if positive_gaps.size == 0:
        return 0.0
    gap_consistency = float(np.std(positive_gaps) / max(float(np.mean(positive_gaps)), 1.0))
    if gap_consistency > 1.25:
        return 0.0

    span_ratio = float((float(xs.max()) - float(xs.min())) / max(float(box_w), 1.0))
    if span_ratio < 0.18:
        return 0.0

    height_consistency = float(np.std(hs) / mean_h)
    if height_consistency > 0.85:
        return 0.0

    return min(
        1.0,
        min(len(xs) / 7.0, 0.42)
        + min((1.0 - min(baseline_consistency, 1.0)) * 0.18, 0.18)
        + min((1.0 - min(gap_consistency, 1.0)) * 0.16, 0.16)
        + min((1.0 - min(height_consistency, 1.0)) * 0.14, 0.14)
        + min(span_ratio * 0.10, 0.10),
    )


def _verify_text_presence_mser(img: np.ndarray) -> float:
    if cv2 is None:
        return 0.0

    h, w = img.shape[:2]
    if min(h, w) < 24:
        return 0.0

    try:
        mser = cv2.MSER_create(5, 40, max(1200, int(w * h * 0.02)))
        regions, boxes = mser.detectRegions(img)
    except Exception:
        return 0.0

    if boxes is None or len(boxes) == 0:
        return 0.0

    candidates: list[tuple[float, float, float]] = []
    for x, y, box_w, box_h in boxes:
        area = int(box_w) * int(box_h)
        if box_w < 3 or box_h < 5 or area < 18:
            continue
        if box_w > w * 0.30 or box_h > h * 0.20:
            continue
        aspect = float(box_w) / max(float(box_h), 1.0)
        if aspect < 0.10 or aspect > 4.2:
            continue
        candidates.append((
            float(x + (box_w / 2.0)),
            float(y + (box_h / 2.0)),
            float(box_h),
        ))

    if len(candidates) < 3:
        return 0.0

    best = 0.0
    for _, cy, ch in candidates:
        bucket = [
            item for item in candidates
            if abs(item[1] - cy) <= max(ch * 0.65, 6.0)
        ]
        if len(bucket) < 3:
            continue
        score = _line_cluster_score(
            [item[0] for item in bucket],
            [item[1] for item in bucket],
            [item[2] for item in bucket],
            w,
        )
        if score > best:
            best = score
    return best


def _build_focus_region_arrays(img: np.ndarray) -> list[np.ndarray]:
    h, w = img.shape[:2]
    if min(h, w) < 24:
        return [img]

    crop_w = max(24, int(round(w * 0.42)))
    crop_h = max(24, int(round(h * 0.42)))
    hotspot_w = max(18, int(round(w * 0.24)))
    hotspot_h = max(18, int(round(h * 0.24)))
    center_w = max(24, int(round(w * 0.58)))
    center_h = max(24, int(round(h * 0.58)))
    band_h = max(20, int(round(h * 0.24)))
    band_w = max(24, int(round(w * 0.72)))
    lower_band_h = max(20, int(round(h * 0.30)))
    watermark_w = max(18, int(round(w * 0.34)))
    watermark_h = max(16, int(round(h * 0.16)))
    center_text_h = max(20, int(round(h * 0.18)))

    regions = [
        img,
        img[0:crop_h, 0:crop_w],
        img[0:crop_h, max(0, w - crop_w):w],
        img[max(0, h - crop_h):h, 0:crop_w],
        img[max(0, h - crop_h):h, max(0, w - crop_w):w],
        img[0:hotspot_h, 0:hotspot_w],
        img[0:hotspot_h, max(0, w - hotspot_w):w],
        img[max(0, h - hotspot_h):h, 0:hotspot_w],
        img[max(0, h - hotspot_h):h, max(0, w - hotspot_w):w],
        img[max(0, (h - center_h) // 2):max(0, (h - center_h) // 2) + center_h,
            max(0, (w - center_w) // 2):max(0, (w - center_w) // 2) + center_w],
        img[max(0, (h - center_text_h) // 2):max(0, (h - center_text_h) // 2) + center_text_h, :],
        img[max(0, (h - band_h) // 2):max(0, (h - band_h) // 2) + band_h, :],
        img[max(0, h - lower_band_h):h, :],
        img[max(0, h - band_h):h, max(0, (w - band_w) // 2):max(0, (w - band_w) // 2) + band_w],
        img[max(0, h - watermark_h):h, 0:watermark_w],
        img[max(0, h - watermark_h):h, max(0, w - watermark_w):w],
    ]

    out: list[np.ndarray] = []
    seen: set[tuple[int, int, int]] = set()
    for region in regions:
        if region.size == 0 or min(region.shape[:2]) < 24:
            continue
        key = (
            int(region.shape[0]),
            int(region.shape[1]),
            int(region[: min(8, region.shape[0]), : min(8, region.shape[1])].sum()),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(region)
    return out or [img]


def _prepare_opencv_variant(region: np.ndarray, max_side: int) -> np.ndarray:
    h, w = region.shape[:2]
    scale_down = min(1.0, float(max_side) / float(max(h, w)))
    if scale_down < 1.0:
        region = cv2.resize(
            region,
            (max(1, int(round(w * scale_down))), max(1, int(round(h * scale_down)))),
            interpolation=cv2.INTER_AREA,
        )
        h, w = region.shape[:2]

    if max(h, w) < 520:
        upscale = min(3.0, 640.0 / max(float(max(h, w)), 1.0))
        if upscale > 1.15:
            region = cv2.resize(
                region,
                (max(1, int(round(w * upscale))), max(1, int(round(h * upscale)))),
                interpolation=cv2.INTER_CUBIC,
            )
    return region


def _enhance_region_for_text(region: np.ndarray) -> np.ndarray:
    if region.size == 0:
        return region
    out = region
    try:
        if cv2 is not None:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            out = clahe.apply(out)
            out = cv2.GaussianBlur(out, (0, 0), 1.0)
            out = cv2.addWeighted(region, 1.6, out, -0.6, 0)
    except Exception:
        out = region
    return out


def _build_stage1_region_variants(region: np.ndarray) -> list[np.ndarray]:
    variants: list[np.ndarray] = [region]
    enhanced = _enhance_region_for_text(region)
    variants.append(enhanced)
    try:
        arr = enhanced.astype(np.uint8)
        p_lo = int(np.percentile(arr, 38))
        p_hi = int(np.percentile(arr, 68))
        binary_dark = np.where(arr <= p_lo, 0, 255).astype(np.uint8)
        binary_light = np.where(arr >= p_hi, 255, 0).astype(np.uint8)
        variants.append(binary_dark)
        variants.append(binary_light)
    except Exception:
        pass

    out: list[np.ndarray] = []
    seen: set[tuple[int, int, int]] = set()
    for variant in variants:
        key = (
            int(variant.shape[0]),
            int(variant.shape[1]),
            int(variant[: min(8, variant.shape[0]), : min(8, variant.shape[1])].sum()),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(variant)
    return out


def _ocr_word_quality_score(word_text: str) -> float:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", word_text or "")
    if len(cleaned) >= 4:
        return 1.0
    if len(cleaned) == 3:
        return 0.8
    if len(cleaned) == 2:
        return 0.55
    if len(cleaned) == 1:
        return 0.25
    return 0.0


async def _verify_text_presence_windows_ocr_async(path: str | Path) -> tuple[bool, float]:
    if OcrEngine is None or Language is None or StorageFile is None or BitmapDecoder is None:
        return False, 0.0

    try:
        engine = OcrEngine.try_create_from_language(Language("en-US"))
        if engine is None:
            return False, 0.0
        file = await StorageFile.get_file_from_path_async(str(path))
        stream = await file.open_async(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
    except Exception:
        return False, 0.0

    lines = list(result.lines or [])
    if not lines:
        return False, 0.0

    strong_words = 0
    weak_words = 0
    char_count = 0
    line_count = 0
    spatial_score = 0.0

    for line in lines:
        words = list(line.words or [])
        line_word_count = 0
        line_chars = 0
        line_width = 0.0
        line_height = 0.0
        for word in words:
            word_text = str(word.text or "").strip()
            quality = _ocr_word_quality_score(word_text)
            if quality <= 0.0:
                continue
            alnum = re.sub(r"[^A-Za-z0-9]", "", word_text)
            char_count += len(alnum)
            line_chars += len(alnum)
            line_word_count += 1
            if quality >= 0.8:
                strong_words += 1
            else:
                weak_words += 1
            rect = getattr(word, "bounding_rect", None)
            if rect is not None:
                line_width += float(getattr(rect, "width", 0.0) or 0.0)
                line_height = max(line_height, float(getattr(rect, "height", 0.0) or 0.0))
        if line_word_count <= 0:
            continue
        line_count += 1
        if line_width > 0.0 and line_height > 0.0:
            spatial_score += min((line_width / max(line_height, 1.0)) * 0.04, 0.20)
        if line_word_count >= 2:
            spatial_score += 0.10
        if line_chars >= 4:
            spatial_score += 0.08

    if strong_words <= 0 and weak_words <= 0 and char_count < 2:
        return False, 0.0

    confidence = min(
        1.0,
        min(strong_words * 0.28, 0.56)
        + min(weak_words * 0.10, 0.20)
        + min(char_count * 0.025, 0.18)
        + min(line_count * 0.06, 0.12)
        + min(spatial_score, 0.24),
    )
    verified = bool(
        confidence >= 0.02
        and (
            strong_words >= 1
            or (weak_words >= 1 and char_count >= 2)
            or (char_count >= 2 and line_count >= 1)
        )
    )
    return verified, round(float(confidence), 3)


def _build_ocr_variant_images(path: str | Path) -> list[Image.Image]:
    variants: list[Image.Image] = []
    try:
        with Image.open(path) as img:
            gray = img.convert("L")
            base_regions = _build_focus_region_arrays(np.asarray(gray, dtype=np.uint8))
            for region in base_regions:
                variants.append(Image.fromarray(region, mode="L"))

            width, height = gray.size
            longest = max(width, height)

            # Upscale smaller sources so short text gets more pixels.
            if longest < 1400:
                scale = 2 if longest >= 700 else 3
                upscaled = gray.resize(
                    (max(1, width * scale), max(1, height * scale)),
                    resample=Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC,
                )
            else:
                upscaled = gray.copy()
            variants.append(upscaled)

            # High-contrast threshold pass for faint or stylized text.
            arr = np.asarray(upscaled, dtype=np.uint8)
            if arr.size > 0:
                threshold = int(np.percentile(arr, 72))
                binary = np.where(arr >= threshold, 255, 0).astype(np.uint8)
                variants.append(Image.fromarray(binary, mode="L"))
                variants.append(Image.fromarray(255 - binary, mode="L"))
            for region in base_regions[1:]:
                region_img = Image.fromarray(region, mode="L")
                rw, rh = region_img.size
                if max(rw, rh) < 900:
                    scale = 3 if max(rw, rh) < 360 else 2
                    region_img = region_img.resize(
                        (max(1, rw * scale), max(1, rh * scale)),
                        resample=Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC,
                    )
                variants.append(region_img)
                region_arr = np.asarray(region_img, dtype=np.uint8)
                region_threshold = int(np.percentile(region_arr, 70))
                region_binary = np.where(region_arr >= region_threshold, 255, 0).astype(np.uint8)
                variants.append(Image.fromarray(region_binary, mode="L"))
                variants.append(Image.fromarray(255 - region_binary, mode="L"))
    except Exception:
        return []

    deduped: list[Image.Image] = []
    seen_sizes: set[tuple[int, int, bytes]] = set()
    for img in variants:
        try:
            key = (img.size[0], img.size[1], img.tobytes()[:128])
        except Exception:
            key = (img.size[0], img.size[1], b"")
        if key in seen_sizes:
            continue
        seen_sizes.add(key)
        deduped.append(img)
    return deduped


def _glyph_cluster_score(region_arr: np.ndarray) -> tuple[float, int, float]:
    box_h, box_w = region_arr.shape
    if box_h < 6 or box_w < 18:
        return 0.0, 0, 0.0

    local_mean = ndimage.uniform_filter(region_arr, size=5)
    candidates = [
        region_arr < (local_mean - 9.0),
        region_arr > (local_mean + 11.0),
    ]

    best_score = 0.0
    best_glyph_count = 0
    best_span_ratio = 0.0
    for binary in candidates:
        binary = ndimage.binary_opening(binary, structure=np.ones((2, 2), dtype=bool))
        binary = ndimage.binary_dilation(binary, structure=np.ones((1, 2), dtype=bool))
        labels, count = ndimage.label(binary)
        if count <= 0:
            continue

        glyph_heights: list[float] = []
        glyph_widths: list[float] = []
        glyph_centers_x: list[float] = []
        glyph_centers_y: list[float] = []
        ink_area = 0.0

        for idx, obj in enumerate(ndimage.find_objects(labels), start=1):
            if obj is None:
                continue
            ys, xs = obj
            comp_h = int(ys.stop - ys.start)
            comp_w = int(xs.stop - xs.start)
            area = comp_h * comp_w
            if comp_h < 3 or comp_w < 2 or area < 8:
                continue
            if comp_h > box_h * 0.82 or comp_w > box_w * 0.38:
                continue
            aspect = comp_w / max(comp_h, 1)
            if aspect < 0.10 or aspect > 3.6:
                continue
            mask = labels[obj] == idx
            fill_ratio = float(mask.mean())
            if fill_ratio < 0.10 or fill_ratio > 0.90:
                continue

            glyph_heights.append(float(comp_h))
            glyph_widths.append(float(comp_w))
            glyph_centers_x.append(float(xs.start + xs.stop) / 2.0)
            glyph_centers_y.append(float(ys.start + ys.stop) / 2.0)
            ink_area += float(mask.sum())

        glyph_count = len(glyph_heights)
        if glyph_count < 3:
            continue

        heights = np.asarray(glyph_heights, dtype=np.float32)
        widths = np.asarray(glyph_widths, dtype=np.float32)
        width_height_ratio = float(np.median(widths / np.maximum(heights, 1.0)))
        height_consistency = float(np.std(heights) / max(float(np.mean(heights)), 1.0))
        if height_consistency > 0.72:
            continue

        centers_y = np.asarray(glyph_centers_y, dtype=np.float32)
        baseline_consistency = float(np.std(centers_y) / max(float(np.mean(heights)), 1.0))
        if baseline_consistency > 0.85:
            continue

        centers = sorted(glyph_centers_x)
        gaps = np.diff(centers) if len(centers) > 1 else np.asarray([], dtype=np.float32)
        if gaps.size:
            positive_gaps = gaps[gaps > 0]
            if positive_gaps.size == 0:
                continue
            gap_consistency = float(np.std(positive_gaps) / max(float(np.mean(positive_gaps)), 1.0))
            mean_gap = float(np.mean(positive_gaps))
        else:
            gap_consistency = 0.0
            mean_gap = 0.0

        ink_ratio = ink_area / float(box_h * box_w)
        if ink_ratio < 0.03 or ink_ratio > 0.45:
            continue

        span_ratio = float((max(centers) - min(centers)) / max(float(box_w), 1.0)) if len(centers) > 1 else 0.0
        if span_ratio < 0.14:
            continue
        relative_gap = mean_gap / max(float(np.mean(heights)), 1.0) if mean_gap > 0 else 0.0
        if relative_gap > 3.4:
            continue

        score = min(
            1.0,
            min(glyph_count / 8.0, 0.45)
            + min((1.0 - min(height_consistency, 1.0)) * 0.22, 0.22)
            + min((1.0 - min(baseline_consistency, 1.0)) * 0.18, 0.18)
            + min((1.0 - min(gap_consistency, 1.0)) * 0.14, 0.14)
            + min(width_height_ratio * 0.08, 0.08),
        )
        if score > best_score:
            best_score = score
            best_glyph_count = glyph_count
            best_span_ratio = span_ratio

    return best_score, best_glyph_count, best_span_ratio


def _verify_text_presence_opencv_array(img: np.ndarray, max_side: int = 768) -> tuple[bool, float]:
    if cv2 is None or img is None or img.size == 0:
        return False, 0.0
    if min(img.shape[:2]) < 20:
        return False, 0.0
    img = _prepare_opencv_variant(img, max_side)
    h, w = img.shape[:2]
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    grad_x = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    grad_x = cv2.convertScaleAbs(grad_x)
    grad_x = cv2.normalize(grad_x, None, 0, 255, cv2.NORM_MINMAX)

    bw = cv2.adaptiveThreshold(
        grad_x,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        -7,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
    closed = cv2.erode(closed, np.ones((2, 2), dtype=np.uint8), iterations=1)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False, 0.0

    region_scores: list[float] = []
    for contour in contours:
        x, y, box_w, box_h = cv2.boundingRect(contour)
        area = box_w * box_h
        if box_w < 16 or box_h < 6 or area < 110:
            continue
        if box_w > w * 0.94 or box_h > h * 0.26:
            continue
        aspect = box_w / max(box_h, 1)
        if aspect < 1.4 or aspect > 32.0:
            continue
        area_ratio = area / float(w * h)
        if area_ratio > 0.11:
            continue

        roi = img[y:y + box_h, x:x + box_w]
        if roi.size == 0:
            continue
        roi_bw = cv2.adaptiveThreshold(
            roi,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21,
            7,
        )
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(roi_bw, connectivity=8)
        glyph_heights: list[float] = []
        glyph_centers_x: list[float] = []
        glyph_centers_y: list[float] = []
        total_ink = 0.0
        for idx in range(1, num_labels):
            comp_x = int(stats[idx, cv2.CC_STAT_LEFT])
            comp_y = int(stats[idx, cv2.CC_STAT_TOP])
            comp_w = int(stats[idx, cv2.CC_STAT_WIDTH])
            comp_h = int(stats[idx, cv2.CC_STAT_HEIGHT])
            comp_area = int(stats[idx, cv2.CC_STAT_AREA])
            if comp_w < 2 or comp_h < 3 or comp_area < 9:
                continue
            if comp_h > box_h * 0.90 or comp_w > box_w * 0.40:
                continue
            comp_aspect = comp_w / max(comp_h, 1)
            if comp_aspect < 0.10 or comp_aspect > 3.6:
                continue
            total_ink += comp_area
            glyph_heights.append(float(comp_h))
            glyph_centers_x.append(float(centroids[idx][0]))
            glyph_centers_y.append(float(centroids[idx][1]))

        glyph_count = len(glyph_heights)
        if glyph_count < 3:
            continue

        heights = np.asarray(glyph_heights, dtype=np.float32)
        height_consistency = float(np.std(heights) / max(float(np.mean(heights)), 1.0))
        if height_consistency > 0.82:
            continue
        centers_y = np.asarray(glyph_centers_y, dtype=np.float32)
        baseline_consistency = float(np.std(centers_y) / max(float(np.mean(heights)), 1.0))
        if baseline_consistency > 0.95:
            continue

        centers_x = sorted(glyph_centers_x)
        if len(centers_x) > 1:
            gaps = np.diff(np.asarray(centers_x, dtype=np.float32))
            positive_gaps = gaps[gaps > 0]
            if positive_gaps.size == 0:
                continue
            gap_consistency = float(np.std(positive_gaps) / max(float(np.mean(positive_gaps)), 1.0))
            if gap_consistency > 1.25:
                continue
        span_ratio = float((max(centers_x) - min(centers_x)) / max(float(box_w), 1.0))
        if span_ratio < 0.16:
            continue

        ink_ratio = total_ink / float(box_w * box_h)
        if ink_ratio < 0.025 or ink_ratio > 0.54:
            continue

        region_score = min(
            1.0,
            min(glyph_count / 8.0, 0.45)
            + min((1.0 - min(height_consistency, 1.0)) * 0.18, 0.18)
            + min((1.0 - min(baseline_consistency, 1.0)) * 0.14, 0.14)
            + min(span_ratio * 0.24, 0.24),
        )
        if region_score >= 0.30:
            region_scores.append(region_score)

    contour_best = max(region_scores) if region_scores else 0.0
    contour_confidence = min(1.0, contour_best + min(len(region_scores) * 0.06, 0.22)) if region_scores else 0.0
    mser_confidence = _verify_text_presence_mser(img)
    support_bonus = min(contour_confidence, mser_confidence) * 0.22
    confidence = min(1.0, max(contour_confidence, mser_confidence) + support_bonus)
    if confidence <= 0.0:
        return False, 0.0
    verified = bool(
        confidence >= 0.52
        and (
            min(contour_confidence, mser_confidence) >= 0.16
            or max(contour_confidence, mser_confidence) >= 0.73
        )
    )
    return verified, round(float(confidence), 3)


def verify_text_presence_opencv(path: str | Path, max_side: int = 768) -> tuple[bool, float]:
    """Run the OpenCV-only stage-2 verifier on stage-1 candidates."""
    if cv2 is None:
        return False, 0.0

    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    except Exception:
        img = None
    if img is None or img.size == 0:
        return False, 0.0

    best_score = 0.0
    best_verified = False
    for region in _build_focus_region_arrays(img):
        for variant in (region, _enhance_region_for_text(region)):
            verified, score = _verify_text_presence_opencv_array(variant, max_side=max_side)
            if score > best_score:
                best_score = score
            if verified:
                best_verified = True
                best_score = max(best_score, score)
                break
        if best_verified:
            break
    return best_verified, round(float(best_score), 3)


def verify_text_presence_windows_ocr(path: str | Path) -> tuple[bool, float]:
    """Run the OCR-backed stage-3 verifier."""
    if OcrEngine is None or Language is None or StorageFile is None or BitmapDecoder is None:
        return False, 0.0
    try:
        best_verified = False
        best_score = 0.0
        variants = _build_ocr_variant_images(path)
        if not variants:
            import asyncio
            return asyncio.run(_verify_text_presence_windows_ocr_async(path))

        with tempfile.TemporaryDirectory(prefix="medialens_ocr_") as tmpdir:
            tmpdir_path = Path(tmpdir)
            for idx, variant in enumerate(variants):
                temp_path = tmpdir_path / f"ocr_variant_{idx}.png"
                try:
                    variant.save(temp_path)
                    import asyncio
                    verified, score = asyncio.run(_verify_text_presence_windows_ocr_async(temp_path))
                except Exception:
                    verified, score = False, 0.0
                if score > best_score:
                    best_score = float(score or 0.0)
                if verified:
                    best_verified = True
                    best_score = max(best_score, float(score or 0.0))
                    break
        return best_verified, round(float(best_score), 3)
    except Exception:
        return False, 0.0


def _detect_likely_text_presence_array(arr: np.ndarray) -> tuple[bool, float]:
    if arr.size == 0 or min(arr.shape) < 24:
        return False, 0.0
    arr = ndimage.gaussian_filter(arr, sigma=0.6)
    gx = np.abs(np.diff(arr, axis=1, append=arr[:, -1:]))
    gy = np.abs(np.diff(arr, axis=0, append=arr[-1:, :]))
    grad = (gx * 0.72) + (gy * 0.28)
    grad_threshold = max(16.0, float(np.percentile(grad, 89)))
    edge_mask = grad >= grad_threshold

    local_mean = ndimage.uniform_filter(arr, size=9)
    contrast = np.abs(arr - local_mean)
    contrast_threshold = max(10.0, float(np.percentile(contrast, 85)))
    candidate = edge_mask & (contrast >= contrast_threshold)

    # Connect nearby character strokes into word-like regions.
    candidate = ndimage.binary_dilation(candidate, structure=np.ones((2, 5), dtype=bool))
    candidate = ndimage.binary_erosion(candidate, structure=np.ones((2, 2), dtype=bool))

    labels, count = ndimage.label(candidate)
    if count <= 0:
        return False, 0.0

    height, width = candidate.shape
    image_area = float(height * width)
    region_score = 0.0
    region_count = 0
    confirmed_region_count = 0

    for idx, region in enumerate(ndimage.find_objects(labels), start=1):
        if region is None:
            continue
        ys, xs = region
        box_h = int(ys.stop - ys.start)
        box_w = int(xs.stop - xs.start)
        area = box_h * box_w
        if box_w < 14 or box_h < 5 or area < 90:
            continue
        if box_w > width * 0.90 or box_h > height * 0.24:
            continue
        aspect = box_w / max(box_h, 1)
        if aspect < 1.35 or aspect > 28.0:
            continue

        mask = labels[region] == idx
        fill_ratio = float(mask.mean())
        if fill_ratio < 0.08 or fill_ratio > 0.60:
            continue

        box_edge_density = float(edge_mask[region].mean())
        if box_edge_density < 0.12:
            continue

        box_area_ratio = area / image_area
        if box_area_ratio > 0.055:
            continue
        glyph_score, glyph_count, glyph_span_ratio = _glyph_cluster_score(arr[region])
        min_glyph_count = 2 if glyph_score >= 0.34 else 3
        if glyph_score < 0.20 or glyph_count < min_glyph_count:
            continue
        region_count += 1
        confirmed_region_count += 1
        region_score += min(
            1.0,
            0.06
            + min(box_edge_density * 0.88, 0.22)
            + min(box_area_ratio * 5.5, 0.10)
            + min(aspect / 30.0, 0.10)
            + min(glyph_score * 0.30, 0.30)
            + min(glyph_span_ratio * 0.20, 0.20)
        )

    if region_count <= 0:
        return False, 0.0

    row_signal = candidate.mean(axis=1)
    peak_threshold = max(0.016, float(row_signal.mean() + (row_signal.std() * 1.2)))
    horizontal_band_count = int(np.count_nonzero(row_signal >= peak_threshold))

    score = min(
        1.0,
        (confirmed_region_count * 0.06)
        + min(region_score * 0.20, 0.34)
        + min(horizontal_band_count * 0.010, 0.10),
    )
    likely = bool(
        (confirmed_region_count >= 2 and score >= 0.22)
        or (confirmed_region_count >= 1 and horizontal_band_count >= 2 and score >= 0.30)
        or (
            confirmed_region_count == 1
            and horizontal_band_count >= 3
            and score >= 0.36
        )
    )
    return likely, round(float(score), 3)


def detect_likely_text_presence(path: str | Path, max_side: int = 512) -> tuple[bool, float]:
    """Return a fast local text-likelihood signal for an image.

    This is intentionally a lightweight presence detector, not OCR. It works on a
    temporary in-memory analysis image so it can run during scan without creating
    thumbnails on disk.
    """
    try:
        with Image.open(path) as img:
            try:
                img.draft("L", (max_side, max_side))
            except Exception:
                pass
            gray = img.convert("L")
            width, height = gray.size
            if width <= 0 or height <= 0:
                return False, 0.0
            if max(width, height) > max_side:
                gray.thumbnail((max_side, max_side), _RESAMPLE)
            base_arr = np.asarray(gray, dtype=np.float32)
    except Exception:
        return False, 0.0

    if base_arr.size == 0 or min(base_arr.shape) < 24:
        return False, 0.0

    best_score = 0.0
    best_likely = False
    for region in _build_focus_region_arrays(base_arr.astype(np.uint8)):
        for variant in _build_stage1_region_variants(region):
            region_arr = variant.astype(np.float32)
            likely, score = _detect_likely_text_presence_array(region_arr)
            if score > best_score:
                best_score = float(score or 0.0)
            if likely:
                best_likely = True
                best_score = max(best_score, float(score or 0.0))
                break
        if best_likely:
            break
    return best_likely, round(float(best_score), 3)


def detect_text_presence(
    path: str | Path,
    *,
    source_path: str | Path | None = None,
    max_side: int = 512,
) -> tuple[bool, float]:
    started_at = time.perf_counter()
    analysis_path = Path(path)
    source_value = str(source_path or analysis_path)
    log_payload: dict = {
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pipeline_version": TEXT_DETECTION_VERSION,
        "source_path": source_value,
        "analysis_path": str(analysis_path),
        "detected": False,
        "final_confidence": 0.0,
        "final_zone": None,
        "final_region": None,
        "final_method": None,
        "final_variation": None,
        "stages": [],
    }

    try:
        with Image.open(analysis_path) as img:
            try:
                img.draft("L", (max_side, max_side))
            except Exception:
                pass
            original_gray = img.convert("L")
            original_arr = np.asarray(original_gray, dtype=np.uint8)
            working_gray = original_gray.copy()
            if max(working_gray.size) > max_side:
                working_gray.thumbnail((max_side, max_side), _RESAMPLE)
            working_arr = np.asarray(working_gray, dtype=np.uint8)
    except Exception as exc:
        log_payload["error"] = str(exc)
        _append_text_detection_log(log_payload)
        return False, 0.0

    if original_arr.size == 0 or working_arr.size == 0 or min(original_arr.shape[:2]) < 24 or min(working_arr.shape[:2]) < 24:
        log_payload["error"] = "image_too_small"
        _append_text_detection_log(log_payload)
        return False, 0.0

    stage1_candidates: list[dict] = []
    best_stage1: dict | None = None
    best_negative_confidence = 0.0
    rescue_support: dict[str, dict] = {}

    for spec in _TEXT_REGION_SPECS:
        stage1_started = time.perf_counter()
        working_region = _crop_region_by_spec(working_arr, spec)
        if working_region.size == 0 or min(working_region.shape[:2]) < 24:
            continue
        stage1_result = _evaluate_stage1_region(spec, working_region)
        stage1_candidates.append(stage1_result)
        if best_stage1 is None or stage1_result["score"] > float(best_stage1.get("score") or 0.0):
            best_stage1 = stage1_result
        if spec.name in {"top_center", "bottom_center"}:
            rescue_support[spec.name] = stage1_result
        log_payload["stages"].append(
            {
                "stage": "stage1",
                "method": "heuristic",
                "status": "positive" if stage1_result["positive"] else "negative",
                "zone": stage1_result["zone"],
                "region": stage1_result["name"],
                "variation": stage1_result["variation"],
                "confidence": stage1_result["score"],
                "elapsed_ms": round((time.perf_counter() - stage1_started) * 1000.0, 2),
            }
        )
        if stage1_result["score"] < _TEXT_STAGE1_TO_STAGE2_SCORE:
            log_payload["stages"].append(
                {
                    "stage": "stage2",
                    "method": "opencv",
                    "status": "skipped",
                    "zone": stage1_result["zone"],
                    "region": stage1_result["name"],
                    "variation": None,
                    "confidence": stage1_result["score"],
                    "reason": "stage1_below_threshold",
                    "elapsed_ms": 0.0,
                }
            )
            log_payload["stages"].append(
                {
                    "stage": "stage3",
                    "method": "ocr",
                    "status": "skipped",
                    "zone": stage1_result["zone"],
                    "region": stage1_result["name"],
                    "variation": None,
                    "confidence": stage1_result["score"],
                    "reason": "stage1_below_threshold",
                    "elapsed_ms": 0.0,
                }
            )
            continue

        stage2_result: dict | None = None
        if stage1_result["score"] >= _TEXT_STAGE1_DIRECT_TO_OCR_SCORE:
            log_payload["stages"].append(
                {
                    "stage": "stage2",
                    "method": "opencv",
                    "status": "skipped",
                    "zone": stage1_result["zone"],
                    "region": stage1_result["name"],
                    "variation": None,
                    "confidence": stage1_result["score"],
                    "reason": "stage1_direct_to_ocr",
                    "elapsed_ms": 0.0,
                }
            )
        else:
            stage2_started = time.perf_counter()
            stage2_result = _evaluate_stage2_region(spec, working_region)
            stage2_result["elapsed_ms"] = round((time.perf_counter() - stage2_started) * 1000.0, 2)
            log_payload["stages"].append(stage2_result)
            if stage2_result["status"] != "positive":
                best_negative_confidence = max(best_negative_confidence, float(stage2_result["confidence"] or 0.0))
                log_payload["stages"].append(
                    {
                        "stage": "stage3",
                        "method": "ocr",
                        "status": "skipped",
                        "zone": stage2_result["zone"],
                        "region": stage2_result["region"],
                        "variation": None,
                        "confidence": stage2_result["confidence"],
                        "reason": "stage2_negative",
                        "elapsed_ms": 0.0,
                    }
                )
                continue
            if (
                stage2_result["confidence"] >= _TEXT_STAGE2_STRONG_DETECTED_SCORE
                and _region_supports_stage2_shortcut(stage2_result.get("region"))
                and stage1_result.get("name") == stage2_result.get("region")
            ):
                log_payload["stages"].append(
                    {
                        "stage": "stage3",
                        "method": "ocr",
                        "status": "skipped",
                        "zone": stage2_result["zone"],
                        "region": stage2_result["region"],
                        "variation": None,
                        "confidence": stage2_result["confidence"],
                        "reason": "stage2_strong_shortcut",
                        "elapsed_ms": 0.0,
                    }
                )
                log_payload["detected"] = True
                log_payload["final_confidence"] = float(stage2_result["confidence"])
                log_payload["final_zone"] = stage2_result["zone"]
                log_payload["final_region"] = stage2_result["region"]
                log_payload["final_method"] = "opencv"
                log_payload["final_variation"] = stage2_result["variation"]
                log_payload["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
                _append_text_detection_log(log_payload)
                return True, float(log_payload["final_confidence"])

        if not _ocr_available():
            upstream = stage2_result if stage2_result and stage2_result["status"] == "positive" else stage1_result
            fallback_detected = bool(stage1_result["score"] >= _TEXT_STAGE1_FALLBACK_DETECTED_SCORE) or bool(
                stage2_result and stage2_result["status"] == "positive"
            )
            log_payload["stages"].append(
                {
                    "stage": "stage3",
                    "method": "ocr",
                    "status": "skipped",
                    "zone": stage1_result["zone"],
                    "region": stage1_result["name"],
                    "variation": None,
                    "confidence": float(upstream.get("confidence") or upstream.get("score") or 0.0),
                    "reason": "ocr_unavailable",
                    "elapsed_ms": 0.0,
                }
            )
            if fallback_detected:
                log_payload["detected"] = True
                log_payload["final_confidence"] = float(upstream.get("confidence") or upstream.get("score") or 0.0)
                log_payload["final_zone"] = upstream["zone"]
                log_payload["final_region"] = upstream.get("region") or upstream.get("name")
                log_payload["final_method"] = "opencv" if "confidence" in upstream else "heuristic"
                log_payload["final_variation"] = upstream["variation"]
                log_payload["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
                _append_text_detection_log(log_payload)
                return True, float(log_payload["final_confidence"])
            continue

        original_region = _crop_region_by_spec(original_arr, spec)
        stage3_started = time.perf_counter()
        upstream_confidence = float((stage2_result or {}).get("confidence") or stage1_result.get("score") or 0.0)
        ocr_verified, ocr_score, ocr_variation = _verify_text_presence_windows_ocr_variants(
            _build_ocr_named_variants(
                original_region,
                include_threshold_variants=upstream_confidence < 0.85,
            )
        )
        log_payload["stages"].append(
            {
                "stage": "stage3",
                "method": "ocr",
                "status": "positive" if ocr_verified else "negative",
                "zone": spec.zone,
                "region": spec.name,
                "variation": ocr_variation,
                "confidence": ocr_score,
                "elapsed_ms": round((time.perf_counter() - stage3_started) * 1000.0, 2),
            }
        )
        if ocr_verified:
            log_payload["detected"] = True
            log_payload["final_confidence"] = float(ocr_score or 0.0)
            log_payload["final_zone"] = spec.zone
            log_payload["final_region"] = spec.name
            log_payload["final_method"] = "ocr"
            log_payload["final_variation"] = ocr_variation
            log_payload["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
            _append_text_detection_log(log_payload)
            return True, float(log_payload["final_confidence"])
        best_negative_confidence = max(best_negative_confidence, float(ocr_score or 0.0))

    top_center_candidate = rescue_support.get("top_center")
    bottom_center_candidate = rescue_support.get("bottom_center")
    rescue_candidates = [
        candidate
        for candidate in (top_center_candidate, bottom_center_candidate)
        if candidate is not None and float(candidate.get("score") or 0.0) >= _TEXT_RESCUE_MIN_STAGE1_SCORE
    ]
    if _ocr_available() and rescue_candidates:
        rescue_started = time.perf_counter()
        rescue_result: dict | None = None
        for rescue_candidate in sorted(rescue_candidates, key=lambda item: float(item.get("score") or 0.0), reverse=True):
            rescue_spec = _region_spec_by_name(str(rescue_candidate.get("name") or ""))
            if rescue_spec is None:
                continue
            rescue_region = _crop_region_by_spec(original_arr, rescue_spec)
            rescue_verified, rescue_score, rescue_variation = _verify_text_presence_windows_ocr_variants(
                _build_ocr_named_variants(rescue_region, include_threshold_variants=True)
            )
            if rescue_result is None or rescue_score > float(rescue_result.get("confidence") or 0.0):
                rescue_result = {
                    "stage": "stage3_rescue",
                    "method": "ocr",
                    "status": "positive" if rescue_verified else "negative",
                    "zone": rescue_spec.zone,
                    "region": rescue_spec.name,
                    "variation": rescue_variation,
                    "confidence": rescue_score,
                    "elapsed_ms": 0.0,
                }
            if rescue_verified:
                break
        if rescue_result is not None:
            rescue_result["elapsed_ms"] = round((time.perf_counter() - rescue_started) * 1000.0, 2)
            log_payload["stages"].append(rescue_result)
            if rescue_result["status"] == "positive":
                log_payload["detected"] = True
                log_payload["final_confidence"] = float(rescue_result["confidence"] or 0.0)
                log_payload["final_zone"] = rescue_result["zone"]
                log_payload["final_region"] = rescue_result["region"]
                log_payload["final_method"] = "ocr"
                log_payload["final_variation"] = rescue_result["variation"]
                log_payload["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
                _append_text_detection_log(log_payload)
                return True, float(log_payload["final_confidence"])
    else:
        log_payload["stages"].append(
            {
                "stage": "stage3_rescue",
                "method": "ocr",
                "status": "skipped",
                "zone": "center",
                "region": None,
                "variation": None,
                "confidence": 0.0,
                "reason": "no_top_bottom_center_support",
                "elapsed_ms": 0.0,
            }
        )

    log_payload["final_confidence"] = max(
        best_negative_confidence,
        float(best_stage1["score"]) if best_stage1 else 0.0,
    )

    log_payload["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000.0, 2)
    _append_text_detection_log(log_payload)
    return bool(log_payload["detected"]), float(log_payload["final_confidence"])
