from __future__ import annotations

import mimetypes
from pathlib import Path

from app.mediamanager.metadata.containers.jpeg_segments import parse_jpeg_segments
from app.mediamanager.metadata.containers.pillow_extract import extract_pillow_metadata
from app.mediamanager.metadata.containers.png_chunks import parse_png_chunks
from app.mediamanager.metadata.models import RawMetadataEnvelope


def extract_raw_metadata(path: str | Path) -> RawMetadataEnvelope:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_type = "unknown"

    png_text_entries = []
    png_binary_entries = []
    jpeg_segments = []
    warnings: list[str] = []

    if suffix == ".png":
        file_type = "png"
        png_text_entries, png_binary_entries, png_warnings = parse_png_chunks(file_path)
        warnings.extend(png_warnings)
    elif suffix in {".jpg", ".jpeg"}:
        file_type = "jpeg"
        jpeg_segments, jpeg_warnings = parse_jpeg_segments(file_path)
        warnings.extend(jpeg_warnings)

    pillow_info, exif_data, iptc_data, xmp_packets, pillow_warnings = extract_pillow_metadata(file_path)
    warnings.extend(pillow_warnings)
    for segment in jpeg_segments:
        if segment.kind == "XMP" and segment.text:
            xmp_packets.append(segment.text)

    return RawMetadataEnvelope(
        file_path=file_path,
        file_type=file_type,
        media_type=media_type,
        png_text_entries=png_text_entries,
        png_binary_entries=png_binary_entries,
        jpeg_segments=jpeg_segments,
        pillow_info=pillow_info,
        exif=exif_data,
        iptc=iptc_data,
        xmp_packets=xmp_packets,
        warnings=warnings,
    )
