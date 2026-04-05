from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.mediamanager.metadata.models import ParsedMetadataResult, RawMetadataEnvelope


_XMP_NS_PREFIXES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/exif/1.0/": "exif",
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/photoshop/1.0/": "photoshop",
    "http://ns.adobe.com/lightroom/1.0/": "lr",
    "http://ns.microsoft.com/photo/1.2/": "MicrosoftPhoto",
    "http://ns.adobe.com/tiff/1.0/": "tiff",
    "http://ns.adobe.com/xap/1.0/mm/": "xmpMM",
    "http://ns.adobe.com/xap/1.0/sType/ResourceRef#": "stRef",
    "http://ns.adobe.com/xap/1.0/sType/ResourceEvent#": "stEvt",
}
_XMP_CONTAINER_NAMES = {"xmpmeta", "rdf:rdf", "rdf:description", "metadata"}
_XMP_LIST_NAMES = {"rdf:bag", "rdf:seq", "rdf:alt"}


def _xmp_prefixed_name(tag: str) -> str:
    value = str(tag or "")
    if value.startswith("{") and "}" in value:
        uri, local = value[1:].split("}", 1)
        prefix = _XMP_NS_PREFIXES.get(uri)
        return f"{prefix}:{local}" if prefix else local
    return value


def _xmp_clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _add_unknown_field(fields: dict[str, object], key: str, value: object) -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return
    if isinstance(value, list):
        cleaned = [_xmp_clean_text(item) for item in value if _xmp_clean_text(item)]
        if not cleaned:
            return
        existing = fields.get(normalized_key)
        if isinstance(existing, list):
            for item in cleaned:
                if item not in existing:
                    existing.append(item)
        elif existing:
            merged = [_xmp_clean_text(existing), *cleaned]
            fields[normalized_key] = [item for idx, item in enumerate(merged) if item and item not in merged[:idx]]
        else:
            fields[normalized_key] = cleaned
        return
    cleaned_value = _xmp_clean_text(value)
    if not cleaned_value:
        return
    existing = fields.get(normalized_key)
    if existing is None:
        fields[normalized_key] = cleaned_value
    elif isinstance(existing, list):
        if cleaned_value not in existing:
            existing.append(cleaned_value)
    elif cleaned_value != existing:
        fields[normalized_key] = [existing, cleaned_value]


def _extract_xmp_fields(packet: str) -> dict[str, object]:
    fields: dict[str, object] = {}
    try:
        root = ET.fromstring(str(packet or ""))
    except Exception:
        return fields

    def walk(element: ET.Element, prefix: str = "") -> None:
        name = _xmp_prefixed_name(element.tag)
        lower_name = name.lower()
        current_prefix = prefix if lower_name in _XMP_CONTAINER_NAMES else (f"{prefix}.{name}" if prefix else name)

        for attr_name, attr_value in element.attrib.items():
            prefixed_attr = _xmp_prefixed_name(attr_name)
            if prefixed_attr in {"rdf:about", "xml:lang"}:
                continue
            attr_key = prefixed_attr if lower_name == "rdf:description" and not current_prefix else (
                f"{current_prefix}.@{prefixed_attr}" if current_prefix else prefixed_attr
            )
            _add_unknown_field(fields, attr_key, attr_value)

        children = list(element)
        if not children:
            if current_prefix:
                _add_unknown_field(fields, current_prefix, "".join(element.itertext()))
            return

        list_children = [child for child in children if _xmp_prefixed_name(child.tag).lower() in _XMP_LIST_NAMES]
        if current_prefix and list_children and len(list_children) == len(children):
            values: list[str] = []
            for collection in list_children:
                for li in list(collection):
                    if _xmp_prefixed_name(li.tag).lower() != "rdf:li":
                        continue
                    item_text = _xmp_clean_text("".join(li.itertext()))
                    if item_text:
                        values.append(item_text)
            _add_unknown_field(fields, current_prefix, values)
            return

        own_text = _xmp_clean_text(element.text)
        if own_text and current_prefix:
            _add_unknown_field(fields, current_prefix, own_text)
        for child in children:
            walk(child, current_prefix)

    walk(root)
    return fields


def parse_generic_embedded(raw: RawMetadataEnvelope) -> ParsedMetadataResult | None:
    description = ""
    tags: list[str] = []
    extracted_paths: list[str] = []
    raw_blobs: list[dict[str, object]] = []
    xmp_fields: dict[str, object] = {}
    text_entries: dict[str, object] = {}
    for entry in raw.png_text_entries:
        key = entry.keyword.lower()
        _add_unknown_field(text_entries, entry.keyword, entry.text)
        if entry.text.strip():
            extracted_paths.append(entry.path_descriptor)
            raw_blobs.append({"path": entry.path_descriptor, "text": entry.text})
        if key in {"comment", "comments", "description", "subject", "title"} and not description:
            description = entry.text.strip()
        elif key in {"keywords", "tags"}:
            parts = [part.strip() for part in re.split(r"[;,]", entry.text) if part.strip()]
            for part in parts:
                if part not in tags:
                    tags.append(part)

    for key, value in (raw.pillow_info or {}).items():
        key_text = str(key or "").lower()
        value_text = str(value or "").strip()
        if key_text in {"svg:desc", "svg:title", "comment", "comments", "description", "subject", "title"} and value_text and not description:
            description = value_text
            extracted_paths.append(f"container:{key_text}")
        elif key_text in {"keywords", "tags"}:
            parts = [part.strip() for part in re.split(r"[;,]", value_text) if part.strip()]
            for part in parts:
                if part not in tags:
                    tags.append(part)
            extracted_paths.append(f"container:{key_text}")

    for index, packet in enumerate(raw.xmp_packets or [], start=1):
        packet_text = str(packet or "").strip()
        if not packet_text:
            continue
        extracted_paths.append(f"xmp:packet[{index}]")
        raw_blobs.append({"path": f"xmp:packet[{index}]", "text": packet_text})
        for field_key, field_value in _extract_xmp_fields(packet_text).items():
            _add_unknown_field(xmp_fields, field_key, field_value)

    if not description:
        for key in ("dc:description", "dc:title", "exif:UserComment", "photoshop:Headline", "photoshop:CaptionWriter"):
            value = xmp_fields.get(key)
            if isinstance(value, list):
                description = next((str(item).strip() for item in value if str(item).strip()), "")
            elif value:
                description = str(value).strip()
            if description:
                break

    for key in ("dc:subject", "lr:hierarchicalSubject", "MicrosoftPhoto:LastKeywordXMP"):
        value = xmp_fields.get(key)
        if isinstance(value, list):
            for item in value:
                part = str(item).strip()
                if part and part not in tags:
                    tags.append(part)
        elif value:
            part = str(value).strip()
            if part and part not in tags:
                tags.append(part)

    if not description and not tags and not raw.exif and not raw.xmp_packets and not raw.iptc and not text_entries and not raw.pillow_info:
        return None

    normalized = {
        "source_format": "generic_embedded",
        "description": description,
        "unknown_fields": {
            "tags": tags,
            "exif": raw.exif,
            "iptc": raw.iptc,
            "text_entries": text_entries,
            "xmp_fields": xmp_fields,
            "xmp_packets": raw.xmp_packets,
            "container_info": raw.pillow_info,
        },
    }
    return ParsedMetadataResult(
        family="generic_embedded",
        confidence=0.55,
        normalized=normalized,
        extracted_paths=extracted_paths,
        raw_blobs=raw_blobs,
    )
