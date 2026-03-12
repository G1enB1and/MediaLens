from __future__ import annotations

import base64
import struct
import zlib
from pathlib import Path

from app.mediamanager.metadata.models import BinaryEntry, TextEntry


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _decode_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16le", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding).rstrip("\x00")
        except Exception:
            continue
    return raw.decode("latin-1", errors="replace").rstrip("\x00")


def _extract_printable_strings(raw: bytes, minimum: int = 8) -> list[str]:
    strings: list[str] = []
    current: list[str] = []
    for byte in raw:
        if 32 <= byte <= 126:
            current.append(chr(byte))
            continue
        if len(current) >= minimum:
            strings.append("".join(current))
        current = []
    if len(current) >= minimum:
        strings.append("".join(current))
    return strings[:32]


def parse_png_chunks(path: Path) -> tuple[list[TextEntry], list[BinaryEntry], list[str]]:
    text_entries: list[TextEntry] = []
    binary_entries: list[BinaryEntry] = []
    warnings: list[str] = []
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        return text_entries, binary_entries, warnings

    offset = 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8].decode("latin-1")
        chunk_data = data[offset + 8 : offset + 8 + length]
        if len(chunk_data) != length:
            warnings.append(f"Truncated PNG chunk {chunk_type} at {offset}")
            break

        if chunk_type == "tEXt" and b"\x00" in chunk_data:
            keyword, text = chunk_data.split(b"\x00", 1)
            text_entries.append(
                TextEntry(container="png", keyword=_decode_bytes(keyword), text=_decode_bytes(text), offset=offset)
            )
        elif chunk_type == "zTXt" and b"\x00" in chunk_data:
            keyword, rest = chunk_data.split(b"\x00", 1)
            if rest:
                compression_method = rest[0]
                payload = rest[1:]
                if compression_method == 0:
                    try:
                        payload = zlib.decompress(payload)
                    except Exception as exc:
                        warnings.append(f"Failed to decompress zTXt chunk at {offset}: {exc}")
                text_entries.append(
                    TextEntry(container="png", keyword=_decode_bytes(keyword), text=_decode_bytes(payload), offset=offset)
                )
        elif chunk_type == "iTXt":
            parts = chunk_data.split(b"\x00", 5)
            if len(parts) == 6:
                keyword, compressed_flag, _compression_method, language, translated, text = parts
                if compressed_flag == b"\x01":
                    try:
                        text = zlib.decompress(text)
                    except Exception as exc:
                        warnings.append(f"Failed to decompress iTXt chunk at {offset}: {exc}")
                text_entries.append(
                    TextEntry(
                        container="png",
                        keyword=_decode_bytes(keyword),
                        text=_decode_bytes(text),
                        offset=offset,
                        language=_decode_bytes(language),
                        translated_keyword=_decode_bytes(translated),
                    )
                )
        elif chunk_type in {"caBX", "eXIf"}:
            binary_entries.append(
                BinaryEntry(
                    container="png",
                    chunk_type=chunk_type,
                    offset=offset,
                    length=length,
                    raw_binary_b64=base64.b64encode(chunk_data).decode("ascii"),
                    printable_strings=_extract_printable_strings(chunk_data),
                )
            )

        offset += 12 + length
        if chunk_type == "IEND":
            break

    return text_entries, binary_entries, warnings
