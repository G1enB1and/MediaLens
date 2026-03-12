from __future__ import annotations

import base64
import struct
from pathlib import Path

from app.mediamanager.metadata.models import JpegSegment


def _decode_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16le", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding).rstrip("\x00")
        except Exception:
            continue
    return raw.decode("latin-1", errors="replace").rstrip("\x00")


def parse_jpeg_segments(path: Path) -> tuple[list[JpegSegment], list[str]]:
    segments: list[JpegSegment] = []
    warnings: list[str] = []
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        return segments, warnings

    offset = 2
    while offset < len(data) - 1:
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            warnings.append("Truncated JPEG segment header")
            break
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        payload = data[offset + 2 : offset + segment_length]
        if len(payload) != segment_length - 2:
            warnings.append(f"Truncated JPEG segment FF{marker:02X} at {offset - 2}")
            break

        name = {
            0xE0: "APP0",
            0xE1: "APP1",
            0xE2: "APP2",
            0xE3: "APP3",
            0xE4: "APP4",
            0xE5: "APP5",
            0xE6: "APP6",
            0xE7: "APP7",
            0xE8: "APP8",
            0xE9: "APP9",
            0xEA: "APP10",
            0xEB: "APP11",
            0xEC: "APP12",
            0xED: "APP13",
            0xEE: "APP14",
            0xEF: "APP15",
            0xFE: "COM",
        }.get(marker, f"MARKER_{marker:02X}")

        segment = JpegSegment(
            marker=f"FF{marker:02X}",
            name=name,
            offset=offset - 2,
            length=segment_length - 2,
            raw_binary_b64=base64.b64encode(payload).decode("ascii"),
        )
        if name == "COM":
            segment.text = _decode_bytes(payload)
        elif name == "APP1":
            if payload.startswith(b"Exif\x00\x00"):
                segment.kind = "Exif"
            elif payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
                segment.kind = "XMP"
                segment.text = _decode_bytes(payload[len(b"http://ns.adobe.com/xap/1.0/\x00") :])
        segments.append(segment)
        offset += segment_length
        if marker == 0xDA:
            break

    return segments, warnings
