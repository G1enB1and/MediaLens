from __future__ import annotations

from native.mediamanagerx_app.common import *

def _render_svg_image(path: str | Path) -> QImage | None:
    clean = str(path or "").strip()
    if not clean:
        return None
    renderer = QSvgRenderer(clean)
    if not renderer.isValid():
        return None
    size = renderer.defaultSize()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        size = QSize(512, 512)
    max_dim = max(size.width(), size.height())
    if max_dim > 4096:
        scale = 4096.0 / max_dim
        size = QSize(max(1, int(size.width() * scale)), max(1, int(size.height() * scale)))
    image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return image if not image.isNull() else None


def _read_image_with_svg_support(path: str | Path, *, auto_transform: bool = True) -> QImage | None:
    clean = str(path or "").strip()
    if not clean:
        return None
    reader = QImageReader(clean)
    reader.setAutoTransform(auto_transform)
    image = reader.read()
    if not image.isNull():
        return image
    if Path(clean).suffix.lower() == ".svg":
        return _render_svg_image(clean)
    return None


def _image_size_with_svg_support(path: str | Path) -> QSize:
    clean = str(path or "").strip()
    if not clean:
        return QSize()
    reader = QImageReader(clean)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        transform_name = getattr(reader.transformation(), "name", "")
        if "Rotate90" in transform_name or "Rotate270" in transform_name:
            return QSize(size.height(), size.width())
        return size
    if Path(clean).suffix.lower() == ".svg":
        renderer = QSvgRenderer(clean)
        if renderer.isValid():
            return renderer.defaultSize()
    return QSize()


def _srgb_channel_to_linear(channel: int) -> float:
    value = max(0.0, min(255.0, float(channel))) / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _image_visible_luminance(image: QImage | None) -> float | None:
    if image is None or image.isNull():
        return None
    sample = image
    if sample.width() > 96 or sample.height() > 96:
        sample = sample.scaled(
            96,
            96,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if sample.isNull():
        return None
    weighted_luminance = 0.0
    total_alpha = 0.0
    for y in range(sample.height()):
        for x in range(sample.width()):
            color = sample.pixelColor(x, y)
            alpha = color.alphaF()
            if alpha <= 0.01:
                continue
            luminance = (
                0.2126 * _srgb_channel_to_linear(color.red())
                + 0.7152 * _srgb_channel_to_linear(color.green())
                + 0.0722 * _srgb_channel_to_linear(color.blue())
            )
            weighted_luminance += luminance * alpha
            total_alpha += alpha
    if total_alpha <= 0.0:
        return None
    return weighted_luminance / total_alpha


def _image_has_meaningful_transparency(image: QImage | None) -> bool:
    if image is None or image.isNull():
        return False
    sample = image
    if sample.width() > 96 or sample.height() > 96:
        sample = sample.scaled(
            96,
            96,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    if sample.isNull():
        return False
    total_pixels = max(1, sample.width() * sample.height())
    transparent_pixels = 0
    partial_alpha_pixels = 0
    opaque_visible_pixels = 0
    for y in range(sample.height()):
        for x in range(sample.width()):
            alpha = sample.pixelColor(x, y).alphaF()
            if alpha <= 0.01:
                transparent_pixels += 1
            elif alpha < 0.98:
                partial_alpha_pixels += 1
            else:
                opaque_visible_pixels += 1
    transparency_ratio = (transparent_pixels + partial_alpha_pixels) / total_pixels
    return transparency_ratio >= 0.05 and (transparent_pixels + partial_alpha_pixels) > 0 and opaque_visible_pixels > 0


def _thumbnail_bg_hint(path: str | Path) -> str:
    clean = str(path or "").strip()
    if not clean:
        return ""
    suffix = Path(clean).suffix.lower()
    if suffix not in {".svg", ".png"}:
        return ""
    try:
        stat = Path(clean).stat()
        cache_key = (clean, int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        cache_key = (clean, 0, 0)
    cached = _THUMBNAIL_BG_HINT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    image = _render_svg_image(clean) if suffix == ".svg" else _read_image_with_svg_support(clean)
    if suffix == ".png" and not _image_has_meaningful_transparency(image):
        hint = ""
    else:
        luminance = _image_visible_luminance(image)
        # Only force contrast backgrounds for mostly dark or mostly light artwork.
        if luminance is None:
            hint = ""
        elif luminance <= 0.35:
            hint = "light"
        elif luminance >= 0.75:
            hint = "dark"
        else:
            hint = ""
    if len(_THUMBNAIL_BG_HINT_CACHE) > 512:
        _THUMBNAIL_BG_HINT_CACHE.clear()
    _THUMBNAIL_BG_HINT_CACHE[cache_key] = hint
    return hint
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS["startupinfo"] = startupinfo
    except AttributeError:
        pass




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
