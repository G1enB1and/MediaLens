from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path


def _settings_from_json(raw: str) -> dict:
    payload = json.loads(raw or "{}")
    if "models_dir" not in payload:
        payload["models_dir"] = str(Path.cwd() / "local_ai_models")
    return payload


def _provider_names(requested_device: str) -> list[str]:
    requested = str(requested_device or "gpu").strip().lower()
    if requested == "gpu":
        return ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _preload(settings: dict) -> dict:
    try:
        import insightface
        import onnxruntime as ort
        from insightface.app import FaceAnalysis
    except Exception as exc:
        raise RuntimeError(f"InsightFace runtime import failed: {exc}") from exc

    models_root = Path(str(settings.get("models_dir") or "")).expanduser() / "insightface"
    models_root.mkdir(parents=True, exist_ok=True)
    requested_device = str(settings.get("device") or "gpu")
    providers = _provider_names(requested_device)
    available = set(ort.get_available_providers())
    active_providers = [provider for provider in providers if provider in available]
    if "CPUExecutionProvider" not in active_providers:
        active_providers.append("CPUExecutionProvider")
    ctx_id = int(settings.get("gpu_index") or 0) if active_providers[0] != "CPUExecutionProvider" else -1

    app = FaceAnalysis(name="buffalo_l", root=str(models_root), providers=active_providers)
    app.prepare(ctx_id=ctx_id, det_size=(640, 640))
    model_dir = models_root / "models" / "buffalo_l"
    return {
        "ok": True,
        "backend": "insightface",
        "insightface_version": str(getattr(insightface, "__version__", "") or ""),
        "onnxruntime_version": str(getattr(ort, "__version__", "") or ""),
        "available_providers": sorted(available),
        "active_providers": active_providers,
        "model_dir": str(model_dir),
        "model_files": sorted(path.name for path in model_dir.glob("*.onnx")),
    }


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens InsightFace People task.")
    parser.add_argument("--operation", choices=("preload",), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    args = parser.parse_args()

    try:
        settings = _settings_from_json(args.settings_json)
        with contextlib.redirect_stdout(sys.stderr):
            payload = _preload(settings)
            print(
                f"InsightFace ready with providers: {', '.join(payload.get('active_providers') or [])}",
                file=sys.stderr,
                flush=True,
            )
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
