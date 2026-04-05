from __future__ import annotations

import mimetypes
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from app.mediamanager.metadata.containers.jpeg_segments import parse_jpeg_segments
from app.mediamanager.metadata.containers.pillow_extract import extract_pillow_metadata
from app.mediamanager.metadata.containers.png_chunks import parse_png_chunks
from app.mediamanager.metadata.models import RawMetadataEnvelope


def _decode_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _svg_local_name(tag: str) -> str:
    text = str(tag or "")
    if text.startswith("{") and "}" in text:
        return text.split("}", 1)[1]
    if ":" in text:
        return text.split(":", 1)[1]
    return text


def _extract_xml_packets_from_text(text: str) -> list[str]:
    packets: list[str] = []
    seen: set[str] = set()
    source = str(text or "")
    if not source:
        return packets

    for pattern in (
        r"(<[^>]*xmpmeta[\s\S]*?</[^>]*xmpmeta>)",
        r"(<rdf:RDF[\s\S]*?</rdf:RDF>)",
        r"(<metadata[\s\S]*?</metadata>)",
    ):
        for match in re.findall(pattern, source, re.IGNORECASE):
            candidate = str(match or "").strip()
            if candidate and candidate not in seen:
                packets.append(candidate)
                seen.add(candidate)
    return packets


def _extract_xmp_packets_from_file(
    path: Path,
    *,
    full_scan_max_bytes: int = 64 * 1024 * 1024,
    edge_scan_bytes: int = 4 * 1024 * 1024,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    try:
        file_size = path.stat().st_size
        if file_size <= full_scan_max_bytes:
            raw = path.read_bytes()
        else:
            with path.open("rb") as handle:
                head = handle.read(edge_scan_bytes)
                tail = b""
                if file_size > edge_scan_bytes:
                    handle.seek(max(0, file_size - edge_scan_bytes))
                    tail = handle.read(edge_scan_bytes)
            raw = head + b"\n" + tail
            warnings.append("Raw XMP scan limited to file head/tail for large file")
    except Exception as exc:
        return [], [f"Raw XMP scan failed: {exc}"]

    text = raw.decode("latin-1", errors="ignore").replace("\x00", "")
    return _extract_xml_packets_from_text(text), warnings


def _extract_svg_metadata(path: Path) -> tuple[dict[str, object], list[str], list[str]]:
    pillow_info: dict[str, object] = {}
    xmp_packets: list[str] = []
    warnings: list[str] = []
    try:
        text = _decode_text_file(path)
    except Exception as exc:
        return pillow_info, xmp_packets, [f"SVG read failed: {exc}"]

    def add_packet(packet: str) -> None:
        candidate = str(packet or "").strip()
        if candidate and candidate not in xmp_packets:
            xmp_packets.append(candidate)

    try:
        root = ET.fromstring(text)
        for child in list(root):
            local = _svg_local_name(child.tag).lower()
            content = " ".join("".join(child.itertext()).split()).strip()
            if local == "title" and content:
                pillow_info["svg:title"] = content
            elif local == "desc" and content:
                pillow_info["svg:desc"] = content
            elif local == "metadata":
                if list(child):
                    for metadata_child in list(child):
                        add_packet(ET.tostring(metadata_child, encoding="unicode"))
                elif content:
                    add_packet(content)
    except Exception as exc:
        warnings.append(f"SVG XML parse failed: {exc}")

    for match in _extract_xml_packets_from_text(text):
        add_packet(match)

    return pillow_info, xmp_packets, warnings


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
    elif suffix == ".avif":
        file_type = "avif"
    elif suffix == ".svg":
        file_type = "svg"

    if suffix == ".svg":
        pillow_info, xmp_packets, svg_warnings = _extract_svg_metadata(file_path)
        exif_data = {}
        iptc_data = {}
        warnings.extend(svg_warnings)
    elif media_type.startswith("video/"):
        pillow_info = {}
        exif_data = {}
        iptc_data = {}
        xmp_packets = []
    else:
        pillow_info, exif_data, iptc_data, xmp_packets, pillow_warnings = extract_pillow_metadata(file_path)
        warnings.extend(pillow_warnings)

    raw_scan_packets, raw_scan_warnings = _extract_xmp_packets_from_file(file_path)
    warnings.extend(raw_scan_warnings)
    for packet in raw_scan_packets:
        if packet not in xmp_packets:
            xmp_packets.append(packet)
    for segment in jpeg_segments:
        if segment.kind == "XMP" and segment.text:
            if segment.text not in xmp_packets:
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
