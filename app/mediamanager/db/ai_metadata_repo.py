from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.mediamanager.metadata.models import InspectionResult


PARSER_VERSION = "ai-metadata-pipeline-v3"
NORMALIZED_SCHEMA_VERSION = "ai-metadata-schema-v3"


def _ensure_ai_metadata_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(media_ai_metadata)").fetchall()}
    if "user_confirmed_ai" not in cols:
        conn.execute("ALTER TABLE media_ai_metadata ADD COLUMN user_confirmed_ai INTEGER")
        conn.commit()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        try:
            return float(value)
        except Exception:
            return str(value)
    return str(value)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _preview_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _append_embedded_metadata_lines(lines: list[str], key: str, value: Any, *, depth: int = 0, max_lines: int = 120) -> None:
    if len(lines) >= max_lines or depth > 6 or value in (None, "", [], {}):
        return
    label = str(key or "").strip()
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            next_key = f"{label}.{child_key}" if label else str(child_key)
            _append_embedded_metadata_lines(lines, next_key, child_value, depth=depth + 1, max_lines=max_lines)
            if len(lines) >= max_lines:
                return
        return
    if isinstance(value, list):
        if value and all(not isinstance(item, (dict, list, tuple, set)) for item in value):
            rendered = " | ".join(_preview_text(item, 500) for item in value if _preview_text(item, 500))
            if rendered:
                lines.append(f"{label}: {rendered}" if label else rendered)
            return
        for index, item in enumerate(value, start=1):
            next_key = f"{label}[{index}]" if label else f"[{index}]"
            _append_embedded_metadata_lines(lines, next_key, item, depth=depth + 1, max_lines=max_lines)
            if len(lines) >= max_lines:
                return
        return
    rendered = _preview_text(value, 700)
    if rendered:
        lines.append(f"{label}: {rendered}" if label else rendered)


def _build_embedded_metadata_summary(ai_meta: dict[str, Any] | None) -> str:
    if not ai_meta:
        return ""
    lines: list[str] = []
    _append_embedded_metadata_lines(lines, "", ai_meta.get("unknown_fields") or {})
    if not lines:
        for entry in ai_meta.get("raw_entries") or []:
            path = str(entry.get("path_descriptor") or entry.get("family") or "embedded").strip()
            raw_text = _preview_text(entry.get("raw_text"), 900)
            if raw_text:
                lines.append(f"{path}: {raw_text}")
    return "\n".join(lines[:120])


def _normalize_character_card(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    raw_json = normalized.get("data_json")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    normalized.setdefault(key, value)
        except Exception:
            pass
    return normalized


def _extract_card_description(text: Any) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    match = re.search(r'Description\((.+?)\)\s*$', raw, re.IGNORECASE | re.MULTILINE)
    if not match:
        return raw
    parts = re.findall(r'"([^"]*)"', match.group(1))
    cleaned = " ".join(part.strip() for part in parts if part.strip()).strip()
    return cleaned or raw


def replace_media_ai_metadata(
    conn: sqlite3.Connection,
    media_id: int,
    inspection: InspectionResult,
    *,
    parser_version: str = PARSER_VERSION,
    normalized_schema_version: str = NORMALIZED_SCHEMA_VERSION,
) -> None:
    _ensure_ai_metadata_columns(conn)
    now = _utc_now_iso()
    canonical = inspection.canonical
    existing = get_media_ai_metadata(conn, media_id) or {}
    conn.execute(
        """
        INSERT INTO media_ai_metadata (
          media_id, parser_version, normalized_schema_version, is_ai_detected, is_ai_confidence,
          tool_name_found, tool_name_inferred, tool_name_confidence, ai_prompt, ai_negative_prompt,
          description, model_name, model_hash, checkpoint_name, sampler, scheduler, cfg_scale,
          steps, seed, width, height, denoise_strength, upscaler, source_formats_json,
          metadata_families_json, ai_detection_reasons_json, raw_paths_json, unknown_fields_json, user_confirmed_ai,
          updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          parser_version=excluded.parser_version,
          normalized_schema_version=excluded.normalized_schema_version,
          is_ai_detected=excluded.is_ai_detected,
          is_ai_confidence=excluded.is_ai_confidence,
          tool_name_found=excluded.tool_name_found,
          tool_name_inferred=excluded.tool_name_inferred,
          tool_name_confidence=excluded.tool_name_confidence,
          ai_prompt=excluded.ai_prompt,
          ai_negative_prompt=excluded.ai_negative_prompt,
          description=excluded.description,
          model_name=excluded.model_name,
          model_hash=excluded.model_hash,
          checkpoint_name=excluded.checkpoint_name,
          sampler=excluded.sampler,
          scheduler=excluded.scheduler,
          cfg_scale=excluded.cfg_scale,
          steps=excluded.steps,
          seed=excluded.seed,
          width=excluded.width,
          height=excluded.height,
          denoise_strength=excluded.denoise_strength,
          upscaler=excluded.upscaler,
          source_formats_json=excluded.source_formats_json,
          metadata_families_json=excluded.metadata_families_json,
          ai_detection_reasons_json=excluded.ai_detection_reasons_json,
          raw_paths_json=excluded.raw_paths_json,
          unknown_fields_json=excluded.unknown_fields_json,
          user_confirmed_ai=excluded.user_confirmed_ai,
          updated_at_utc=excluded.updated_at_utc
        """,
        (
            media_id,
            parser_version,
            normalized_schema_version,
            1 if canonical.is_ai_detected else 0,
            float(canonical.is_ai_confidence),
            canonical.tool_name_found or None,
            canonical.tool_name_inferred or None,
            float(canonical.tool_name_confidence),
            canonical.ai_prompt or None,
            canonical.ai_negative_prompt or None,
            canonical.description or None,
            canonical.model_name or None,
            canonical.model_hash or None,
            canonical.checkpoint_name or None,
            canonical.sampler or None,
            canonical.scheduler or None,
            _as_float(canonical.cfg_scale),
            _as_int(canonical.steps),
            None if canonical.seed in (None, "") else str(canonical.seed),
            _as_int(canonical.width),
            _as_int(canonical.height),
            _as_float(canonical.denoise_strength),
            canonical.upscaler or None,
            _json_dumps(canonical.source_formats),
            _json_dumps(canonical.metadata_families_detected),
            _json_dumps(canonical.ai_detection_reasons),
            _json_dumps(canonical.raw_paths),
            _json_dumps(canonical.unknown_fields),
            None if existing.get("user_confirmed_ai") is None else (1 if existing.get("user_confirmed_ai") else 0),
            now,
        ),
    )

    conn.execute("DELETE FROM media_ai_metadata_raw WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_loras WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_workflows WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_provenance WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_character_cards WHERE media_id = ?", (media_id,))

    for result in inspection.parsed:
        for raw_blob in result.raw_blobs:
            path_descriptor = raw_blob.get("path") or (result.extracted_paths[0] if result.extracted_paths else result.family)
            raw_kind = "raw_text"
            raw_text = raw_blob.get("text")
            raw_json = None
            raw_binary_b64 = raw_blob.get("raw_binary_b64")
            if isinstance(raw_blob.get("data"), (dict, list)):
                raw_kind = "raw_json"
                raw_json = _json_dumps(raw_blob["data"])
            elif "raw_binary_b64" in raw_blob:
                raw_kind = "raw_binary_b64"
            conn.execute(
                """
                INSERT INTO media_ai_metadata_raw (
                  media_id, family, container_type, path_descriptor, raw_kind, raw_text, raw_json,
                  raw_binary_b64, parse_status, parser_version, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    result.family,
                    path_descriptor.split(":", 1)[0] if ":" in path_descriptor else None,
                    path_descriptor,
                    raw_kind,
                    raw_text,
                    raw_json,
                    raw_binary_b64,
                    "parsed",
                    parser_version,
                    now,
                ),
            )

    for lora in canonical.loras:
        conn.execute(
            """
            INSERT INTO media_ai_loras (media_id, name, weight, hash, source, created_at_utc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                media_id,
                str(lora.get("name", "")),
                None if lora.get("weight") in (None, "") else str(lora.get("weight")),
                None if lora.get("hash") in (None, "") else str(lora.get("hash")),
                None if lora.get("source") in (None, "") else str(lora.get("source")),
                now,
            ),
        )

    for workflow in canonical.workflows:
        conn.execute(
            """
            INSERT INTO media_ai_workflows (media_id, kind, data_json, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (media_id, str(workflow.get("kind", "workflow")), _json_dumps(workflow.get("data")), now),
        )

    for provenance in canonical.provenance:
        conn.execute(
            """
            INSERT INTO media_ai_provenance (media_id, kind, data_json, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (media_id, str(provenance.get("format", "provenance")), _json_dumps(provenance), now),
        )

    for card in canonical.character_cards:
        conn.execute(
            """
            INSERT INTO media_character_cards (media_id, name, data_json, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (media_id, None if not card.get("name") else str(card.get("name")), _json_dumps(card), now),
        )

    conn.commit()


def delete_media_ai_metadata(conn: sqlite3.Connection, media_id: int) -> None:
    conn.execute("DELETE FROM media_ai_metadata_raw WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_loras WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_workflows WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_provenance WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_character_cards WHERE media_id = ?", (media_id,))
    conn.execute("DELETE FROM media_ai_metadata WHERE media_id = ?", (media_id,))
    conn.commit()


def get_media_ai_metadata(conn: sqlite3.Connection, media_id: int) -> dict[str, Any] | None:
    _ensure_ai_metadata_columns(conn)
    row = conn.execute(
        """
        SELECT media_id, parser_version, normalized_schema_version, is_ai_detected, is_ai_confidence, user_confirmed_ai,
               tool_name_found, tool_name_inferred, tool_name_confidence, ai_prompt, ai_negative_prompt,
               description, model_name, model_hash, checkpoint_name, sampler, scheduler, cfg_scale,
               steps, seed, width, height, denoise_strength, upscaler, source_formats_json,
               metadata_families_json, ai_detection_reasons_json, raw_paths_json, unknown_fields_json,
               updated_at_utc
        FROM media_ai_metadata
        WHERE media_id = ?
        """,
        (media_id,),
    ).fetchone()
    if not row:
        return None

    loras = [
        {
            "name": item[0],
            "weight": item[1],
            "hash": item[2],
            "source": item[3],
        }
        for item in conn.execute(
            "SELECT name, weight, hash, source FROM media_ai_loras WHERE media_id = ? ORDER BY id",
            (media_id,),
        ).fetchall()
    ]
    raw_entries = [
        {
            "family": item[0],
            "container_type": item[1],
            "path_descriptor": item[2],
            "raw_kind": item[3],
            "raw_text": item[4],
            "raw_json": item[5],
            "raw_binary_b64": item[6],
            "parse_status": item[7],
            "parser_version": item[8],
        }
        for item in conn.execute(
            """
            SELECT family, container_type, path_descriptor, raw_kind, raw_text, raw_json, raw_binary_b64,
                   parse_status, parser_version
            FROM media_ai_metadata_raw
            WHERE media_id = ?
            ORDER BY id
            """,
            (media_id,),
        ).fetchall()
    ]

    workflows = [
        {"kind": item[0], "data_json": item[1]}
        for item in conn.execute(
            "SELECT kind, data_json FROM media_ai_workflows WHERE media_id = ? ORDER BY id",
            (media_id,),
        ).fetchall()
    ]
    provenance = [
        {"kind": item[0], "data_json": item[1]}
        for item in conn.execute(
            "SELECT kind, data_json FROM media_ai_provenance WHERE media_id = ? ORDER BY id",
            (media_id,),
        ).fetchall()
    ]
    character_cards = [
        {"name": item[0], "data_json": item[1]}
        for item in conn.execute(
            "SELECT name, data_json FROM media_character_cards WHERE media_id = ? ORDER BY id",
            (media_id,),
        ).fetchall()
    ]

    return {
        "media_id": row[0],
        "parser_version": row[1],
        "normalized_schema_version": row[2],
        "is_ai_detected": bool(row[3]),
        "is_ai_confidence": row[4],
        "user_confirmed_ai": None if row[5] is None else bool(row[5]),
        "tool_name_found": row[6],
        "tool_name_inferred": row[7],
        "tool_name_confidence": row[8],
        "ai_prompt": row[9],
        "ai_negative_prompt": row[10],
        "description": row[11],
        "model_name": row[12],
        "model_hash": row[13],
        "checkpoint_name": row[14],
        "sampler": row[15],
        "scheduler": row[16],
        "cfg_scale": row[17],
        "steps": row[18],
        "seed": row[19],
        "width": row[20],
        "height": row[21],
        "denoise_strength": row[22],
        "upscaler": row[23],
        "source_formats": json.loads(row[24]),
        "metadata_families_detected": json.loads(row[25]),
        "ai_detection_reasons": json.loads(row[26]),
        "raw_paths": json.loads(row[27]),
        "unknown_fields": json.loads(row[28]),
        "updated_at_utc": row[29],
        "loras": loras,
        "raw_entries": raw_entries,
        "workflows": workflows,
        "provenance": provenance,
        "character_cards": character_cards,
    }


def upsert_media_ai_selected_fields(
    conn: sqlite3.Connection,
    media_id: int,
    *,
    is_ai_detected: bool | None = None,
    is_ai_confidence: float | None = None,
    user_confirmed_ai: bool | None | str = "",
    tool_name_found: str | None = None,
    tool_name_inferred: str | None = None,
    tool_name_confidence: float | None = None,
    source_formats: list[str] | None = None,
    ai_prompt: str | None = None,
    ai_negative_prompt: str | None = None,
    description: str | None = None,
    model_name: str | None = None,
    checkpoint_name: str | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    cfg_scale: float | int | str | None = None,
    steps: int | str | None = None,
    seed: str | int | None = None,
    upscaler: str | None = None,
    denoise_strength: float | int | str | None = None,
    metadata_families_detected: list[str] | None = None,
    ai_detection_reasons: list[str] | None = None,
) -> None:
    _ensure_ai_metadata_columns(conn)
    now = _utc_now_iso()
    existing = get_media_ai_metadata(conn, media_id) or {}
    if user_confirmed_ai == "":
        user_confirmed_ai_db = None if existing.get("user_confirmed_ai") is None else (1 if existing.get("user_confirmed_ai") else 0)
    elif user_confirmed_ai is None:
        user_confirmed_ai_db = None
    else:
        user_confirmed_ai_db = 1 if bool(user_confirmed_ai) else 0
    conn.execute(
        """
        INSERT INTO media_ai_metadata (
          media_id, parser_version, normalized_schema_version, is_ai_detected, is_ai_confidence,
          tool_name_found, tool_name_inferred, tool_name_confidence, ai_prompt, ai_negative_prompt,
          description, model_name, model_hash, checkpoint_name, sampler, scheduler, cfg_scale,
          steps, seed, width, height, denoise_strength, upscaler, source_formats_json,
          metadata_families_json, ai_detection_reasons_json, raw_paths_json, unknown_fields_json, user_confirmed_ai,
          updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(media_id) DO UPDATE SET
          is_ai_detected=excluded.is_ai_detected,
          is_ai_confidence=excluded.is_ai_confidence,
          tool_name_found=excluded.tool_name_found,
          tool_name_inferred=excluded.tool_name_inferred,
          tool_name_confidence=excluded.tool_name_confidence,
          ai_prompt=excluded.ai_prompt,
          ai_negative_prompt=excluded.ai_negative_prompt,
          description=excluded.description,
          model_name=excluded.model_name,
          checkpoint_name=excluded.checkpoint_name,
          sampler=excluded.sampler,
          scheduler=excluded.scheduler,
          cfg_scale=excluded.cfg_scale,
          steps=excluded.steps,
          seed=excluded.seed,
          upscaler=excluded.upscaler,
          denoise_strength=excluded.denoise_strength,
          metadata_families_json=excluded.metadata_families_json,
          ai_detection_reasons_json=excluded.ai_detection_reasons_json,
          user_confirmed_ai=excluded.user_confirmed_ai,
          updated_at_utc=excluded.updated_at_utc
        """,
        (
            media_id,
            existing.get("parser_version") or PARSER_VERSION,
            existing.get("normalized_schema_version") or NORMALIZED_SCHEMA_VERSION,
            1 if (existing.get("is_ai_detected") if is_ai_detected is None else is_ai_detected) else 0,
            float(existing.get("is_ai_confidence") or 0.0) if is_ai_confidence is None else float(is_ai_confidence),
            existing.get("tool_name_found") if tool_name_found is None else (tool_name_found or None),
            existing.get("tool_name_inferred") if tool_name_inferred is None else (tool_name_inferred or None),
            float(existing.get("tool_name_confidence") or 0.0) if tool_name_confidence is None else float(tool_name_confidence),
            ai_prompt if ai_prompt is not None else existing.get("ai_prompt"),
            ai_negative_prompt if ai_negative_prompt is not None else existing.get("ai_negative_prompt"),
            description if description is not None else existing.get("description"),
            existing.get("model_name") if model_name is None else (model_name or None),
            existing.get("model_hash") or None,
            existing.get("checkpoint_name") if checkpoint_name is None else (checkpoint_name or None),
            existing.get("sampler") if sampler is None else (sampler or None),
            existing.get("scheduler") if scheduler is None else (scheduler or None),
            _as_float(existing.get("cfg_scale")) if cfg_scale is None else _as_float(cfg_scale),
            _as_int(existing.get("steps")) if steps is None else _as_int(steps),
            (None if existing.get("seed") in (None, "") else str(existing.get("seed"))) if seed is None else (None if seed in (None, "") else str(seed)),
            _as_int(existing.get("width")),
            _as_int(existing.get("height")),
            _as_float(existing.get("denoise_strength")) if denoise_strength is None else _as_float(denoise_strength),
            existing.get("upscaler") if upscaler is None else (upscaler or None),
            _json_dumps(existing.get("source_formats") or []) if source_formats is None else _json_dumps(source_formats),
            _json_dumps(existing.get("metadata_families_detected") or []) if metadata_families_detected is None else _json_dumps(metadata_families_detected),
            _json_dumps(existing.get("ai_detection_reasons") or []) if ai_detection_reasons is None else _json_dumps(ai_detection_reasons),
            _json_dumps(existing.get("raw_paths") or []),
            _json_dumps(existing.get("unknown_fields") or {}),
            user_confirmed_ai_db,
            now,
        ),
    )
    conn.commit()


def replace_media_ai_workflows(conn: sqlite3.Connection, media_id: int, workflows: list[dict[str, Any]]) -> None:
    now = _utc_now_iso()
    upsert_media_ai_selected_fields(conn, media_id)
    conn.execute("DELETE FROM media_ai_workflows WHERE media_id = ?", (media_id,))
    for workflow in workflows or []:
        conn.execute(
            """
            INSERT INTO media_ai_workflows (media_id, kind, data_json, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (
                media_id,
                str(workflow.get("kind") or "workflow"),
                workflow.get("data_json") if isinstance(workflow.get("data_json"), str) else _json_dumps(workflow.get("data")),
                now,
            ),
        )
    conn.commit()


def summarize_media_ai_metadata(ai_meta: dict[str, Any] | None) -> str:
    if not ai_meta:
        return ""

    lines: list[str] = []
    tool = ai_meta.get("tool_name_found") or ai_meta.get("tool_name_inferred")
    if tool:
        lines.append(f"Tool: {tool}")
    model_name = ai_meta.get("model_name")
    if model_name:
        lines.append(f"Model: {model_name}")
    checkpoint_name = ai_meta.get("checkpoint_name")
    if checkpoint_name and checkpoint_name != model_name:
        lines.append(f"Checkpoint: {checkpoint_name}")
    sampler = ai_meta.get("sampler")
    if sampler:
        lines.append(f"Sampler: {sampler}")
    scheduler = ai_meta.get("scheduler")
    if scheduler:
        lines.append(f"Scheduler: {scheduler}")
    cfg_scale = ai_meta.get("cfg_scale")
    if cfg_scale not in (None, ""):
        lines.append(f"CFG scale: {cfg_scale}")
    steps = ai_meta.get("steps")
    if steps not in (None, ""):
        lines.append(f"Steps: {steps}")
    seed = ai_meta.get("seed")
    if seed not in (None, ""):
        lines.append(f"Seed: {seed}")
    width = ai_meta.get("width")
    height = ai_meta.get("height")
    if width not in (None, "") and height not in (None, ""):
        lines.append(f"Size: {width}x{height}")
    denoise_strength = ai_meta.get("denoise_strength")
    if denoise_strength not in (None, ""):
        lines.append(f"Denoising strength: {denoise_strength}")
    upscaler = ai_meta.get("upscaler")
    if upscaler:
        lines.append(f"Upscaler: {upscaler}")

    loras = ai_meta.get("loras") or []
    if loras:
        names = [str(item.get("name", "")).strip() for item in loras if str(item.get("name", "")).strip()]
        if names:
            lines.append(f"LoRAs: {', '.join(names)}")

    source_formats = ai_meta.get("source_formats") or []
    if source_formats:
        lines.append(f"Source Formats: {', '.join(source_formats)}")

    return "\n".join(lines)


def build_media_ai_ui_fields(ai_meta: dict[str, Any] | None) -> dict[str, Any]:
    if not ai_meta:
        return {
            "is_ai_detected": False,
            "is_ai_confidence": 0.0,
            "user_confirmed_ai": None,
            "effective_is_ai": False,
            "tool_name_found": "",
            "tool_name_inferred": "",
            "tool_name_confidence": 0.0,
            "source_formats": [],
            "metadata_families_detected": [],
            "ai_detection_reasons": [],
            "loras": [],
            "workflows": [],
            "provenance": [],
            "character_cards": [],
            "raw_paths": [],
            "unknown_fields": {},
            "ai_status_summary": "",
            "ai_effective_status_summary": "",
            "user_confirmed_ai_summary": "",
            "ai_source_summary": "",
            "ai_families_summary": "",
            "ai_detection_reasons_summary": "",
            "ai_loras_summary": "",
            "ai_model_summary": "",
            "ai_checkpoint_summary": "",
            "ai_sampler_summary": "",
            "ai_scheduler_summary": "",
            "ai_cfg_summary": "",
            "ai_steps_summary": "",
            "ai_seed_summary": "",
            "ai_upscaler_summary": "",
            "ai_denoise_summary": "",
            "ai_workflows_summary": "",
            "ai_provenance_summary": "",
            "ai_character_cards_summary": "",
            "ai_raw_paths_summary": "",
        }

    payload = {
        "is_ai_detected": bool(ai_meta.get("is_ai_detected")),
        "is_ai_confidence": float(ai_meta.get("is_ai_confidence") or 0.0),
        "user_confirmed_ai": ai_meta.get("user_confirmed_ai"),
        "effective_is_ai": bool(ai_meta.get("user_confirmed_ai")) if ai_meta.get("user_confirmed_ai") is not None else bool(ai_meta.get("is_ai_detected")),
        "tool_name_found": ai_meta.get("tool_name_found") or "",
        "tool_name_inferred": ai_meta.get("tool_name_inferred") or "",
        "tool_name_confidence": float(ai_meta.get("tool_name_confidence") or 0.0),
        "source_formats": list(ai_meta.get("source_formats") or []),
        "metadata_families_detected": list(ai_meta.get("metadata_families_detected") or []),
        "ai_detection_reasons": list(ai_meta.get("ai_detection_reasons") or []),
        "loras": list(ai_meta.get("loras") or []),
        "workflows": list(ai_meta.get("workflows") or []),
        "provenance": list(ai_meta.get("provenance") or []),
        "character_cards": list(ai_meta.get("character_cards") or []),
        "raw_paths": list(ai_meta.get("raw_paths") or []),
        "unknown_fields": dict(ai_meta.get("unknown_fields") or {}),
        "model_name": ai_meta.get("model_name") or "",
        "checkpoint_name": ai_meta.get("checkpoint_name") or "",
        "sampler": ai_meta.get("sampler") or "",
        "scheduler": ai_meta.get("scheduler") or "",
        "cfg_scale": ai_meta.get("cfg_scale"),
        "steps": ai_meta.get("steps"),
        "seed": ai_meta.get("seed") or "",
        "upscaler": ai_meta.get("upscaler") or "",
        "denoise_strength": ai_meta.get("denoise_strength"),
    }
    payload.update(build_media_ai_sidebar_fields(ai_meta))
    return payload


def build_media_ai_sidebar_fields(ai_meta: dict[str, Any] | None) -> dict[str, str]:
    if not ai_meta:
        return {
            "ai_status_summary": "",
            "ai_effective_status_summary": "",
            "user_confirmed_ai_summary": "",
            "ai_source_summary": "",
            "ai_families_summary": "",
            "ai_detection_reasons_summary": "",
            "ai_loras_summary": "",
            "ai_model_summary": "",
            "ai_checkpoint_summary": "",
            "ai_sampler_summary": "",
            "ai_scheduler_summary": "",
            "ai_cfg_summary": "",
            "ai_steps_summary": "",
            "ai_seed_summary": "",
            "ai_upscaler_summary": "",
            "ai_denoise_summary": "",
            "ai_workflows_summary": "",
            "ai_provenance_summary": "",
            "ai_character_cards_summary": "",
            "ai_raw_paths_summary": "",
        }

    status = "Detected" if ai_meta.get("is_ai_detected") else "Not detected"
    confidence = float(ai_meta.get("is_ai_confidence") or 0.0)
    status_summary = f"{status} ({confidence:.0%})" if confidence > 0 else status
    user_confirmed_ai = ai_meta.get("user_confirmed_ai")
    if user_confirmed_ai is True:
        effective_status_summary = "Detected (User Confirmed)"
    elif user_confirmed_ai is False:
        effective_status_summary = "Not detected (User Confirmed)"
    else:
        effective_status_summary = status_summary

    source_lines: list[str] = []
    tool_found = str(ai_meta.get("tool_name_found") or "").strip()
    tool_inferred = str(ai_meta.get("tool_name_inferred") or "").strip()
    if tool_found:
        source_lines.append(f"Found: {tool_found}")
    if tool_inferred and tool_inferred != tool_found:
        source_lines.append(f"Inferred: {tool_inferred}")
    tool_confidence = float(ai_meta.get("tool_name_confidence") or 0.0)
    if tool_inferred and tool_confidence > 0:
        source_lines.append(f"Inference confidence: {tool_confidence:.0%}")
    source_formats = [str(item).strip() for item in (ai_meta.get("source_formats") or []) if str(item).strip()]
    if source_formats:
        source_lines.append(f"Formats: {', '.join(source_formats)}")

    families = [str(item).strip() for item in (ai_meta.get("metadata_families_detected") or []) if str(item).strip()]
    reasons = [str(item).strip() for item in (ai_meta.get("ai_detection_reasons") or []) if str(item).strip()]
    raw_paths = [str(item).strip() for item in (ai_meta.get("raw_paths") or []) if str(item).strip()]

    lora_names = [
        str(item.get("name", "")).strip()
        for item in (ai_meta.get("loras") or [])
        if str(item.get("name", "")).strip()
    ]

    workflow_lines = []
    for item in ai_meta.get("workflows") or []:
        kind = str(item.get("kind") or "workflow").strip()
        data_json = str(item.get("data_json") or "").strip()
        if data_json:
            workflow_lines.append(f"{kind}: present")
        else:
            workflow_lines.append(kind)

    provenance_lines = []
    for item in ai_meta.get("provenance") or []:
        kind = str(item.get("kind") or item.get("format") or "provenance").strip()
        data_json = str(item.get("data_json") or "").strip()
        if data_json:
            provenance_lines.append(f"{kind}: present")
        else:
            provenance_lines.append(kind)

    character_lines = []
    for raw_item in ai_meta.get("character_cards") or []:
        item = _normalize_character_card(raw_item)
        name = str(item.get("name") or "").strip()
        short_description = _preview_text(item.get("short_description"))
        description = _preview_text(_extract_card_description(item.get("description")))
        personality = _preview_text(item.get("personality"))
        scenario = _preview_text(item.get("scenario"))
        first_mes = _preview_text(item.get("first_mes"), limit=160)
        bits = [name or "Unnamed character card"]
        if short_description:
            bits.append(f"Short: {short_description}")
        elif description:
            bits.append(f"Description: {description}")
        if personality:
            bits.append(f"Personality: {personality}")
        if scenario:
            bits.append(f"Scenario: {scenario}")
        if first_mes:
            bits.append(f"First message: {first_mes}")
        character_lines.append("\n".join(bits))

    return {
        "ai_status_summary": status_summary,
        "ai_effective_status_summary": effective_status_summary,
        "user_confirmed_ai_summary": "" if user_confirmed_ai is None else ("Yes" if user_confirmed_ai else "No"),
        "ai_source_summary": "\n".join(source_lines),
        "ai_families_summary": ", ".join(families),
        "ai_detection_reasons_summary": "\n".join(reasons),
        "ai_loras_summary": "\n".join(lora_names),
        "ai_model_summary": str(ai_meta.get("model_name") or "").strip(),
        "ai_checkpoint_summary": str(ai_meta.get("checkpoint_name") or "").strip(),
        "ai_sampler_summary": str(ai_meta.get("sampler") or "").strip(),
        "ai_scheduler_summary": str(ai_meta.get("scheduler") or "").strip(),
        "ai_cfg_summary": "" if ai_meta.get("cfg_scale") in (None, "") else str(ai_meta.get("cfg_scale")),
        "ai_steps_summary": "" if ai_meta.get("steps") in (None, "") else str(ai_meta.get("steps")),
        "ai_seed_summary": "" if ai_meta.get("seed") in (None, "") else str(ai_meta.get("seed")),
        "ai_upscaler_summary": str(ai_meta.get("upscaler") or "").strip(),
        "ai_denoise_summary": "" if ai_meta.get("denoise_strength") in (None, "") else str(ai_meta.get("denoise_strength")),
        "ai_workflows_summary": "\n".join(workflow_lines),
        "ai_provenance_summary": "\n".join(provenance_lines),
        "ai_character_cards_summary": "\n\n".join(character_lines),
        "ai_raw_paths_summary": "\n".join(raw_paths),
    }


def summarize_media_ai_tool_metadata(ai_meta: dict[str, Any] | None) -> str:
    if not ai_meta:
        return ""

    lines: list[str] = []
    tool_found = ai_meta.get("tool_name_found") or ""
    tool_inferred = ai_meta.get("tool_name_inferred") or ""
    if tool_found:
        lines.append(f"Tool: {tool_found}")
    elif tool_inferred:
        lines.append(f"Tool (Inferred): {tool_inferred}")

    source_formats = ai_meta.get("source_formats") or []
    if source_formats:
        lines.append(f"Source Formats: {', '.join(source_formats)}")

    families = ai_meta.get("metadata_families_detected") or []
    if families:
        lines.append(f"Families: {', '.join(families)}")

    model_name = ai_meta.get("model_name")
    if model_name:
        lines.append(f"Model: {model_name}")

    loras = ai_meta.get("loras") or []
    if loras:
        names = [str(item.get('name', '')).strip() for item in loras if str(item.get('name', '')).strip()]
        if names:
            lines.append(f"LoRAs: {', '.join(names)}")

    workflows = ai_meta.get("workflows") or []
    if workflows:
        kinds = [str(item.get("kind", "workflow")) for item in workflows]
        lines.append(f"Workflows: {len(workflows)} ({', '.join(kinds)})")

    provenance = ai_meta.get("provenance") or []
    if provenance:
        kinds = [str(item.get("kind") or item.get("format") or "provenance") for item in provenance]
        lines.append(f"Provenance: {', '.join(kinds)}")

    raw_paths = ai_meta.get("raw_paths") or []
    if raw_paths:
        lines.append(f"Metadata Paths: {', '.join(raw_paths)}")

    return "\n".join(lines)
