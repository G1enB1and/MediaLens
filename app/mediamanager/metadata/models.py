from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TextEntry:
    container: str
    keyword: str
    text: str
    offset: int
    language: str = ""
    translated_keyword: str = ""

    @property
    def path_descriptor(self) -> str:
        return f"{self.container}:text[{self.keyword}]@{self.offset}"


@dataclass
class BinaryEntry:
    container: str
    chunk_type: str
    offset: int
    length: int
    raw_binary_b64: str = ""
    printable_strings: list[str] = field(default_factory=list)

    @property
    def path_descriptor(self) -> str:
        return f"{self.container}:{self.chunk_type}@{self.offset}"


@dataclass
class JpegSegment:
    marker: str
    name: str
    offset: int
    length: int
    kind: str = ""
    text: str = ""
    raw_binary_b64: str = ""

    @property
    def path_descriptor(self) -> str:
        suffix = f":{self.kind}" if self.kind else ""
        return f"jpeg:{self.name}{suffix}@{self.offset}"


@dataclass
class RawMetadataEnvelope:
    file_path: Path
    file_type: str
    media_type: str
    png_text_entries: list[TextEntry] = field(default_factory=list)
    png_binary_entries: list[BinaryEntry] = field(default_factory=list)
    jpeg_segments: list[JpegSegment] = field(default_factory=list)
    pillow_info: dict[str, Any] = field(default_factory=dict)
    exif: dict[str, Any] = field(default_factory=dict)
    iptc: dict[str, Any] = field(default_factory=dict)
    xmp_packets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "file_type": self.file_type,
            "media_type": self.media_type,
            "png_text_entries": [asdict(entry) for entry in self.png_text_entries],
            "png_binary_entries": [asdict(entry) for entry in self.png_binary_entries],
            "jpeg_segments": [asdict(entry) for entry in self.jpeg_segments],
            "pillow_info": self.pillow_info,
            "exif": self.exif,
            "iptc": self.iptc,
            "xmp_packets": self.xmp_packets,
            "warnings": self.warnings,
        }


@dataclass
class DetectionHit:
    family: str
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class ParsedMetadataResult:
    family: str
    confidence: float
    normalized: dict[str, Any] = field(default_factory=dict)
    raw_blobs: list[dict[str, Any]] = field(default_factory=list)
    extracted_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "confidence": self.confidence,
            "normalized": self.normalized,
            "raw_blobs": self.raw_blobs,
            "extracted_paths": self.extracted_paths,
            "warnings": self.warnings,
        }


@dataclass
class CanonicalMetadata:
    source_formats: list[str] = field(default_factory=list)
    metadata_families_detected: list[str] = field(default_factory=list)
    is_ai_detected: bool = False
    is_ai_confidence: float = 0.0
    ai_detection_reasons: list[str] = field(default_factory=list)
    tool_name_found: str = ""
    tool_name_inferred: str = ""
    tool_name_confidence: float = 0.0
    ai_prompt: str = ""
    ai_negative_prompt: str = ""
    description: str = ""
    model_name: str = ""
    model_hash: str = ""
    checkpoint_name: str = ""
    sampler: str = ""
    scheduler: str = ""
    cfg_scale: Any = None
    steps: Any = None
    seed: Any = None
    width: Any = None
    height: Any = None
    denoise_strength: Any = None
    upscaler: str = ""
    loras: list[dict[str, Any]] = field(default_factory=list)
    workflows: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    character_cards: list[dict[str, Any]] = field(default_factory=list)
    raw_paths: list[str] = field(default_factory=list)
    unknown_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InspectionResult:
    raw: RawMetadataEnvelope
    detections: list[DetectionHit]
    parsed: list[ParsedMetadataResult]
    canonical: CanonicalMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw.to_dict(),
            "detections": [asdict(hit) for hit in self.detections],
            "parsed": [item.to_dict() for item in self.parsed],
            "canonical": self.canonical.to_dict(),
        }
