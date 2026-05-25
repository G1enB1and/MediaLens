from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

_DLL_DIRECTORY_HANDLES = []


def _windows_hidden_subprocess_kwargs() -> dict[str, object]:
    if os.name != "nt":
        return {}
    kwargs: dict[str, object] = {}
    try:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    except AttributeError:
        pass
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    except AttributeError:
        pass
    return kwargs


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
            try:
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(candidate)))
            except Exception:
                pass
    if dll_dirs:
        existing_path = str(os.environ.get("PATH") or "")
        os.environ["PATH"] = os.pathsep.join([*dll_dirs, existing_path])


def _package_version(name: str) -> str:
    try:
        return str(metadata.version(name))
    except Exception:
        return ""


def _nvidia_smi_info() -> dict[str, object]:
    result: dict[str, object] = {"available": False, "gpus": []}
    if os.name != "nt":
        return result
    try:
        popen_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        popen_kwargs.update(_windows_hidden_subprocess_kwargs())
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ],
            **popen_kwargs,
        )
    except Exception:
        return result
    if completed.returncode != 0:
        return result
    gpus: list[dict[str, str]] = []
    for raw_line in str(completed.stdout or "").splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if not parts or not parts[0]:
            continue
        gpus.append(
            {
                "name": parts[0],
                "driver_version": parts[1] if len(parts) > 1 else "",
            }
        )
    if gpus:
        result["available"] = True
        result["gpus"] = gpus
    return result


def _probe_torch(requested_device: str, gpu_index: int) -> dict[str, object]:
    result: dict[str, object] = {
        "backend": "torch",
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "requested_device": requested_device,
        "requested_gpu_index": max(0, int(gpu_index or 0)),
        "selected_device": "cpu",
        "ok": True,
        "import_ok": False,
        "torch_version": "",
        "torch_cuda_version": "",
        "cuda_available": False,
        "device_count": 0,
        "gpu_names": [],
        "reason": "",
        "nvidia_smi": _nvidia_smi_info(),
    }
    try:
        import torch
    except Exception as exc:
        result["ok"] = False
        result["reason"] = f"torch import failed: {exc}"
        return result

    result["import_ok"] = True
    result["torch_version"] = str(getattr(torch, "__version__", "") or _package_version("torch"))
    result["torch_cuda_version"] = str(getattr(getattr(torch, "version", None), "cuda", "") or "")
    try:
        result["cuda_available"] = bool(torch.cuda.is_available())
    except Exception as exc:
        result["reason"] = f"torch.cuda.is_available() failed: {exc}"
        return result
    if not result["cuda_available"]:
        result["reason"] = "torch.cuda.is_available() returned False"
        return result
    try:
        result["device_count"] = max(0, int(torch.cuda.device_count()))
    except Exception as exc:
        result["reason"] = f"torch.cuda.device_count() failed: {exc}"
        return result
    gpu_names: list[str] = []
    for index in range(int(result["device_count"])):
        try:
            gpu_names.append(str(torch.cuda.get_device_name(index)))
        except Exception:
            gpu_names.append(f"GPU {index}")
    result["gpu_names"] = gpu_names
    if requested_device == "gpu" and int(result["device_count"]) > 0:
        selected_gpu_index = min(max(0, int(gpu_index or 0)), int(result["device_count"]) - 1)
        result["selected_gpu_index"] = selected_gpu_index
        result["selected_device"] = f"cuda:{selected_gpu_index}"
    elif requested_device != "gpu":
        result["reason"] = "GPU was not requested"
    return result


def _probe_onnx(requested_device: str) -> dict[str, object]:
    result: dict[str, object] = {
        "backend": "onnx",
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "requested_device": requested_device,
        "selected_device": "cpu",
        "ok": True,
        "import_ok": False,
        "onnxruntime_version": "",
        "available_providers": [],
        "active_provider": "CPUExecutionProvider",
        "reason": "",
        "nvidia_smi": _nvidia_smi_info(),
    }
    try:
        import onnxruntime as ort
    except Exception as exc:
        result["ok"] = False
        result["reason"] = f"onnxruntime import failed: {exc}"
        return result

    result["import_ok"] = True
    _add_nvidia_dll_directories()
    if hasattr(ort, "preload_dlls"):
        try:
            ort.preload_dlls(directory="")
        except Exception:
            pass
    result["onnxruntime_version"] = str(getattr(ort, "__version__", "") or _package_version("onnxruntime-gpu") or _package_version("onnxruntime"))
    try:
        providers = list(ort.get_available_providers())
    except Exception as exc:
        result["reason"] = f"provider discovery failed: {exc}"
        return result
    result["available_providers"] = providers
    if requested_device == "gpu":
        if "CUDAExecutionProvider" in providers:
            result["selected_device"] = "gpu"
            result["active_provider"] = "CUDAExecutionProvider"
        elif "DmlExecutionProvider" in providers:
            result["selected_device"] = "gpu"
            result["active_provider"] = "DmlExecutionProvider"
            result["reason"] = "Using DirectML provider because CUDA provider is unavailable"
        else:
            result["reason"] = "No GPU execution provider is available in this runtime"
    else:
        result["reason"] = "GPU was not requested"
    return result


def _probe_insightface(requested_device: str, models_dir: str = "") -> dict[str, object]:
    result = _probe_onnx(requested_device)
    result["backend"] = "insightface"
    result["insightface_version"] = ""
    result["applied_providers"] = []
    if not result.get("ok"):
        return result
    try:
        import insightface
    except Exception as exc:
        result["ok"] = False
        result["reason"] = f"insightface import failed: {exc}"
        return result
    result["insightface_version"] = str(getattr(insightface, "__version__", "") or _package_version("insightface"))
    if models_dir:
        try:
            from insightface.app import FaceAnalysis

            provider_order = ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"] if requested_device == "gpu" else ["CPUExecutionProvider"]
            available = set(result.get("available_providers") or [])
            active_providers = [provider for provider in provider_order if provider in available]
            if "CPUExecutionProvider" not in active_providers:
                active_providers.append("CPUExecutionProvider")
            models_root = Path(models_dir).expanduser() / "insightface"
            app = FaceAnalysis(name="buffalo_l", root=str(models_root), providers=active_providers)
            ctx_id = int(result.get("requested_gpu_index") or 0) if active_providers[0] != "CPUExecutionProvider" else -1
            app.prepare(ctx_id=ctx_id, det_size=(640, 640))
            applied: list[str] = []
            for model in getattr(app, "models", {}).values():
                session = getattr(model, "session", None)
                if session is None or not hasattr(session, "get_providers"):
                    continue
                for provider in list(session.get_providers() or []):
                    provider = str(provider or "")
                    if provider and provider not in applied:
                        applied.append(provider)
            result["applied_providers"] = applied
            if applied:
                result["active_provider"] = applied[0]
                if applied[0] in {"CUDAExecutionProvider", "DmlExecutionProvider"}:
                    result["selected_device"] = "gpu"
                else:
                    result["selected_device"] = "cpu"
                    if "CUDAExecutionProvider" in list(result.get("available_providers") or []):
                        result["reason"] = "CUDA provider is advertised but failed to load for the InsightFace models; using CPU fallback"
        except Exception as exc:
            result["selected_device"] = "cpu"
            result["active_provider"] = "CPUExecutionProvider"
            result["reason"] = f"InsightFace model provider probe failed: {exc}"
    return result


def _main() -> int:
    parser = argparse.ArgumentParser(description="Probe MediaLens local AI runtime health.")
    parser.add_argument("--backend", choices=("torch", "onnx", "insightface"), required=True)
    parser.add_argument("--requested-device", default="gpu")
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--models-dir", default="")
    args = parser.parse_args()

    requested_device = str(args.requested_device or "gpu").strip().lower() or "gpu"
    if args.backend == "torch":
        payload = _probe_torch(requested_device, int(args.gpu_index or 0))
    elif args.backend == "onnx":
        payload = _probe_onnx(requested_device)
    else:
        payload = _probe_insightface(requested_device, str(args.models_dir or ""))
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
