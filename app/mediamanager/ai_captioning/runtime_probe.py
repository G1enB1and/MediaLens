from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from importlib import metadata


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
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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


def _main() -> int:
    parser = argparse.ArgumentParser(description="Probe MediaLens local AI runtime health.")
    parser.add_argument("--backend", choices=("torch", "onnx"), required=True)
    parser.add_argument("--requested-device", default="gpu")
    parser.add_argument("--gpu-index", type=int, default=0)
    args = parser.parse_args()

    requested_device = str(args.requested_device or "gpu").strip().lower() or "gpu"
    if args.backend == "torch":
        payload = _probe_torch(requested_device, int(args.gpu_index or 0))
    else:
        payload = _probe_onnx(requested_device)
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
