from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import ExifTags, Image


def _decode_value(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        for encoding in ("utf-8", "utf-16le", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding).rstrip("\x00")
            except Exception:
                continue
        return raw.hex()
    return value


def extract_pillow_metadata(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str], list[str]]:
    pillow_info: dict[str, Any] = {}
    exif_data: dict[str, Any] = {}
    iptc_data: dict[str, Any] = {}
    xmp_packets: list[str] = []
    warnings: list[str] = []
    try:
        with Image.open(path) as image:
            for key, value in image.info.items():
                pillow_info[str(key)] = _decode_value(value)
                if str(key).lower() in {"xmp", "xml:com.adobe.xmp"}:
                    xmp_packets.append(str(_decode_value(value)))

            exif = image.getexif()
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                exif_data[f"{tag_id}:{tag_name}"] = _decode_value(value)

            try:
                from PIL import IptcImagePlugin

                iptc = IptcImagePlugin.getiptcinfo(image)
                if iptc:
                    for key, value in iptc.items():
                        iptc_data[str(key)] = _decode_value(value)
            except Exception:
                pass
    except Exception as exc:
        warnings.append(f"Pillow open failed: {exc}")

    return pillow_info, exif_data, iptc_data, xmp_packets, warnings
