from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import traceback
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []


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


def _add_nvidia_dll_directories() -> None:
    if os.name != "nt":
        return
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    dll_dirs: list[str] = []
    for relative in (
        Path("nvidia") / "cudnn" / "bin",
        Path("nvidia") / "cublas" / "bin",
        Path("nvidia") / "cuda_runtime" / "bin",
        Path("nvidia") / "cuda_nvrtc" / "bin",
        Path("nvidia") / "cufft" / "bin",
        Path("nvidia") / "curand" / "bin",
        Path("nvidia") / "nvjitlink" / "bin",
    ):
        candidate = site_packages / relative
        if candidate.is_dir():
            dll_dirs.append(str(candidate))
            if not hasattr(os, "add_dll_directory"):
                continue
            with contextlib.suppress(Exception):
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(candidate)))
    if dll_dirs:
        existing_path = str(os.environ.get("PATH") or "")
        os.environ["PATH"] = os.pathsep.join([*dll_dirs, existing_path])


def _load_app(settings: dict):
    try:
        import insightface
        import onnxruntime as ort
        from insightface.app import FaceAnalysis
    except Exception as exc:
        raise RuntimeError(f"InsightFace runtime import failed: {exc}") from exc

    _add_nvidia_dll_directories()
    if hasattr(ort, "preload_dlls"):
        with contextlib.suppress(Exception):
            ort.preload_dlls(directory="")
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
    return app, insightface, ort, active_providers, available, models_root


def _applied_provider_summary(app) -> list[str]:
    providers: list[str] = []
    for model in getattr(app, "models", {}).values():
        session = getattr(model, "session", None)
        if session is None or not hasattr(session, "get_providers"):
            continue
        try:
            for provider in list(session.get_providers() or []):
                provider = str(provider or "")
                if provider and provider not in providers:
                    providers.append(provider)
        except Exception:
            continue
    return providers


def _preload(settings: dict) -> dict:
    app, insightface, ort, active_providers, available, models_root = _load_app(settings)
    model_dir = models_root / "models" / "buffalo_l"
    return {
        "ok": True,
        "backend": "insightface",
        "insightface_version": str(getattr(insightface, "__version__", "") or ""),
        "onnxruntime_version": str(getattr(ort, "__version__", "") or ""),
        "available_providers": sorted(available),
        "active_providers": active_providers,
        "applied_providers": _applied_provider_summary(app),
        "model_dir": str(model_dir),
        "model_files": sorted(path.name for path in model_dir.glob("*.onnx")),
    }


def _detect_with_app(source: Path, app, insightface, ort, active_providers: list[str]) -> dict:
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError(f"OpenCV runtime import failed: {exc}") from exc

    image = cv2.imread(str(source))
    if image is None:
        raise RuntimeError("InsightFace could not read the source image.")
    height, width = image.shape[:2]
    faces = app.get(image)
    detections: list[dict] = []
    for face in faces:
        raw_bbox = getattr(face, "bbox", None)
        bbox = [float(value) for value in list(raw_bbox)[:4]] if raw_bbox is not None else []
        if len(bbox) != 4:
            continue
        left, top, right, bottom = bbox
        embedding = getattr(face, "normed_embedding", None)
        if embedding is None:
            embedding = getattr(face, "embedding", None)
        embedding_list = [float(value) for value in list(embedding)] if embedding is not None else []
        detections.append(
            {
                "bbox": [
                    max(0.0, left),
                    max(0.0, top),
                    max(0.0, right - left),
                    max(0.0, bottom - top),
                ],
                "confidence": float(getattr(face, "det_score", 0.0) or 0.0),
                "embedding": embedding_list,
            }
        )
    return {
        "ok": True,
        "backend": "insightface",
        "model": "buffalo_l",
        "source": str(source),
        "image_width": int(width or 0),
        "image_height": int(height or 0),
        "active_providers": active_providers,
        "applied_providers": _applied_provider_summary(app),
        "insightface_version": str(getattr(insightface, "__version__", "") or ""),
        "onnxruntime_version": str(getattr(ort, "__version__", "") or ""),
        "faces": detections,
    }


def _detect(source: Path, settings: dict) -> dict:
    app, insightface, ort, active_providers, _available, _models_root = _load_app(settings)
    return _detect_with_app(source, app, insightface, ort, active_providers)


def _serve(settings: dict) -> int:
    with contextlib.redirect_stdout(sys.stderr):
        app, insightface, ort, active_providers, _available, _models_root = _load_app(settings)
        applied_providers = _applied_provider_summary(app)
        print(
            f"InsightFace ready with providers: {', '.join(applied_providers or active_providers)}",
            file=sys.stderr,
            flush=True,
        )
    print(
        json.dumps(
            {
                "ok": True,
                "ready": True,
                "active_providers": active_providers,
                "applied_providers": applied_providers,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            request = json.loads(raw_line)
            source = Path(str(request.get("source") or ""))
            with contextlib.redirect_stdout(sys.stderr):
                payload = _detect_with_app(source, app, insightface, ort, active_providers)
            print(json.dumps(payload, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc) or exc.__class__.__name__,
                        "traceback": traceback.format_exc(limit=8),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return 0


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens InsightFace People task.")
    parser.add_argument("--operation", choices=("preload", "detect", "serve"), required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--settings-json", required=True)
    args = parser.parse_args()

    try:
        settings = _settings_from_json(args.settings_json)
        if args.operation == "serve":
            return _serve(settings)
        with contextlib.redirect_stdout(sys.stderr):
            if args.operation == "detect":
                if not args.source:
                    raise RuntimeError("InsightFace detect requires --source.")
                payload = _detect(Path(args.source), settings)
            else:
                payload = _preload(settings)
            print(
                f"InsightFace ready with providers: {', '.join(payload.get('active_providers') or [])}",
                file=sys.stderr,
                flush=True,
            )
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc) or exc.__class__.__name__,
                    "traceback": traceback.format_exc(limit=8),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
