from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import mimetypes
import base64
from io import BytesIO
from pathlib import Path
from typing import Any

DEFAULT_CAPTION_PROMPT = (
    "Please provide a description of this image in natural language paragraph style. "
    "Describe this woman's body type, proportions, and posture in emotionally rich, artistic language. "
    "Focus on the curves, tone, and overall visual balance. Also include make up, clothing (if any), "
    "hair, background, and colors. Emphasize elegance, softness, or power where appropriate. "
    "Use the following tags as context: {tags}"
)

try:
    from app.mediamanager.ai_captioning.gemma_gguf import GEMMA_GGUF_BACKEND_ID
    from app.mediamanager.ai_captioning.gemma_gguf_prompting import (
        build_gguf_description_prompt,
        build_gguf_rewrite_prompt,
        build_user_description_prompt,
        classify_gguf_description,
        clean_response_text,
        excerpt_text,
        salvage_description,
        tune_gguf_description_settings,
    )
    from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID
except ModuleNotFoundError:
    from gemma_gguf import GEMMA_GGUF_BACKEND_ID
    from gemma_gguf_prompting import (
        build_gguf_description_prompt,
        build_gguf_rewrite_prompt,
        build_user_description_prompt,
        classify_gguf_description,
        clean_response_text,
        excerpt_text,
        salvage_description,
        tune_gguf_description_settings,
    )
    from model_registry import GEMMA4_MODEL_ID


def _settings_from_json(raw: str) -> dict[str, Any]:
    return dict(json.loads(raw or "{}"))


def _models_dir(settings: dict[str, Any]) -> Path:
    raw = str(settings.get("models_dir") or "").strip()
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[3] / "local_ai_models"


def _configure_hf_cache(settings: dict[str, Any]) -> None:
    # Gemma uses a newer Transformers runtime than InternLM. Keep downloaded
    # model code and caches under a Gemma-specific folder so it cannot affect
    # the working InternLM/XComposer runtime.
    root = _models_dir(settings) / "gemma4_runtime"
    home = root / "hf_home"
    modules = root / "hf_modules_cache"
    home.mkdir(parents=True, exist_ok=True)
    modules.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(home))
    os.environ.setdefault("HF_MODULES_CACHE", str(modules))


def _resolve_model(settings: dict[str, Any], model_id: str) -> str:
    local = _models_dir(settings) / model_id
    if (local / "config.json").is_file():
        return str(local)
    return model_id


def _build_description_prompt(prompt_template: str, tags: list[str], caption_start: str) -> str:
    prompt = build_user_description_prompt(prompt_template or DEFAULT_CAPTION_PROMPT, tags, caption_start)
    prompt = (
        f"{prompt.rstrip()}\n"
        "Return only the final answer. Do not include reasoning, analysis, chain-of-thought, or channel markers."
    )
    return prompt.strip()


def _open_image(source_path: str | Path):
    from PIL import Image as PilImage
    from PIL.ImageOps import exif_transpose

    source_path = Path(source_path)
    PilImage.MAX_IMAGE_PIXELS = None
    try:
        with PilImage.open(source_path) as image:
            image.load()
            return exif_transpose(image).convert("RGB")
    except Exception:
        data = source_path.read_bytes()
        with PilImage.open(BytesIO(data)) as image:
            image.load()
            return exif_transpose(image).convert("RGB")


def _load_model(settings: dict[str, Any]):
    try:
        from app.mediamanager.ai_captioning.local_captioning import (
            format_torch_runtime_summary,
            inspect_torch_cuda_runtime,
        )
    except ModuleNotFoundError:
        from local_captioning import format_torch_runtime_summary, inspect_torch_cuda_runtime

    _configure_hf_cache(settings)
    try:
        import torch
        import transformers
        from transformers import AutoProcessor
    except Exception as exc:
        raise RuntimeError("Gemma 4 is not installed correctly. Install the optional Gemma 4 local AI package and try again.") from exc

    model_id = _resolve_model(settings, GEMMA4_MODEL_ID)
    processor = AutoProcessor.from_pretrained(model_id)
    model_class = getattr(transformers, "AutoModelForMultimodalLM", None)
    if model_class is None:
        model_class = getattr(transformers, "AutoModelForImageTextToText", None)
    if model_class is None:
        raise RuntimeError("Gemma 4 cannot be loaded with the installed optional local AI package.")

    device = str(settings.get("device") or "gpu").lower()
    gpu_index = max(0, int(settings.get("gpu_index") or 0))
    runtime = inspect_torch_cuda_runtime(torch, device, gpu_index)
    print(format_torch_runtime_summary("Gemma 4 runtime", runtime), file=sys.stderr, flush=True)
    load_args: dict[str, Any] = {"dtype": "auto"}
    selected_device = str(runtime.get("selected_device") or "cpu")
    if selected_device.startswith("cuda:"):
        load_args["device_map"] = {"": selected_device}
    model = model_class.from_pretrained(model_id, **load_args)
    if "device_map" not in load_args:
        model.to(torch.device("cpu"))
    actual_device = getattr(model, "device", None)
    print(
        f"Gemma 4 model device: requested={device}, selected={selected_device}, actual={actual_device if actual_device is not None else selected_device}",
        file=sys.stderr,
        flush=True,
    )
    model.eval()
    return torch, processor, model, torch.device(selected_device)


def _gguf_enabled(settings: dict[str, Any]) -> bool:
    backend = str(settings.get("gemma_backend") or "").strip().lower()
    model_path = Path(str(settings.get("gemma_model_path") or "").strip())
    mmproj_path = Path(str(settings.get("gemma_mmproj_path") or "").strip())
    server_path = Path(str(settings.get("gemma_llama_server") or "").strip())
    return backend == GEMMA_GGUF_BACKEND_ID and model_path.is_file() and mmproj_path.is_file() and server_path.is_file()


def _gguf_cli_path(settings: dict[str, Any]) -> Path:
    server_path = Path(str(settings.get("gemma_llama_server") or "").strip())
    if server_path.is_file():
        return server_path.with_name("llama-mtmd-cli.exe" if os.name == "nt" else "llama-mtmd-cli")
    return Path()


def _encode_image_data_uri(source_path: str | Path) -> str:
    source_path = Path(source_path)
    mime_type, _encoding = mimetypes.guess_type(str(source_path))
    mime_type = mime_type or "application/octet-stream"
    return f"data:{mime_type};base64,{base64.b64encode(source_path.read_bytes()).decode('ascii')}"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _server_health_url(port: int) -> str:
    return f"http://127.0.0.1:{int(port)}/v1/health"


def _server_chat_url(port: int) -> str:
    return f"http://127.0.0.1:{int(port)}/v1/chat/completions"


def _wait_for_server_ready(process, port: int, timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + max(10, int(timeout_seconds))
    health_url = _server_health_url(port)
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Gemma GGUF server exited early with code {process.returncode}. {last_error}".strip())
        try:
            request = urllib.request.Request(health_url, headers={"User-Agent": "MediaLens-Gemma-GGUF"})
            with urllib.request.urlopen(request, timeout=3) as response:
                if int(getattr(response, "status", 200) or 200) < 500:
                    return
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
        time.sleep(0.5)
    raise RuntimeError(f"Gemma GGUF server did not become ready. {last_error}".strip())


def _start_gguf_server(settings: dict[str, Any]):
    model_path = Path(str(settings.get("gemma_model_path") or "").strip())
    mmproj_path = Path(str(settings.get("gemma_mmproj_path") or "").strip())
    server_path = Path(str(settings.get("gemma_llama_server") or "").strip())
    if not server_path.is_file():
        raise RuntimeError("Gemma GGUF runtime is missing llama-server.exe.")
    if not model_path.is_file() or not mmproj_path.is_file():
        raise RuntimeError("Gemma GGUF model files are missing.")
    port = _find_free_port()
    ctx_size = max(512, int(settings.get("gemma_ctx_size") or 2048))
    gpu_layers = int(settings.get("gemma_gpu_layers") or 999)
    threads = max(1, int(settings.get("gemma_threads") or 8))
    command = [
        str(server_path),
        "-m",
        str(model_path),
        "--mmproj",
        str(mmproj_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-c",
        str(ctx_size),
        "-ngl",
        str(gpu_layers),
        "-t",
        str(threads),
        "-np",
        "1",
        "--jinja",
        "--reasoning-budget",
        "0",
    ]
    env = os.environ.copy()
    process = __import__("subprocess").Popen(
        command,
        stdout=__import__("subprocess").PIPE,
        stderr=__import__("subprocess").STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    _wait_for_server_ready(process, port)
    return process, port


def _stop_process(process) -> None:
    if process is None:
        return
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=10)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=10)
        except Exception:
            pass


def _gguf_cli_completion(source_path: str, prompt: str, settings: dict[str, Any], max_new_tokens: int) -> str:
    cli_path = _gguf_cli_path(settings)
    if not cli_path.is_file():
        raise RuntimeError("Gemma GGUF CLI runtime is missing llama-mtmd-cli.")
    model_path = Path(str(settings.get("gemma_model_path") or "").strip())
    mmproj_path = Path(str(settings.get("gemma_mmproj_path") or "").strip())
    if not model_path.is_file() or not mmproj_path.is_file():
        raise RuntimeError("Gemma GGUF model files are missing.")
    ctx_size = max(512, int(settings.get("gemma_ctx_size") or 2048))
    gpu_layers = int(settings.get("gemma_gpu_layers") or 999)
    threads = max(1, int(settings.get("gemma_threads") or 8))
    command = [
        str(cli_path),
        "-m",
        str(model_path),
        "--mmproj",
        str(mmproj_path),
        "--image",
        str(source_path),
        "-p",
        str(prompt),
        "-n",
        str(max(1, int(max_new_tokens))),
        "-c",
        str(ctx_size),
        "-ngl",
        str(gpu_layers),
        "-t",
        str(threads),
        "--jinja",
        "--no-warmup",
        "--reasoning-budget",
        "0",
        "--temp",
        str(float(settings.get("temperature") or 1.0)),
        "--top-k",
        str(int(settings.get("top_k") or 50)),
        "--top-p",
        str(float(settings.get("top_p") or 1.0)),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(120, max_new_tokens * 2),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if str(part or "").strip())
    if completed.returncode != 0:
        tail = "\n".join(line for line in combined.splitlines()[-12:] if line.strip())
        raise RuntimeError(f"Gemma GGUF CLI failed with exit code {completed.returncode}. {tail}".strip())
    text = clean_response_text(completed.stdout or combined)
    if not text:
        tail = "\n".join(line for line in combined.splitlines()[-12:] if line.strip())
        raise RuntimeError(f"Gemma GGUF CLI returned an empty response. {tail}".strip())
    return text


def _gguf_chat_completion(source_path: str, prompt: str, settings: dict[str, Any], max_new_tokens: int) -> str:
    process = None
    try:
        process, port = _start_gguf_server(settings)
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": _encode_image_data_uri(source_path)}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": float(settings.get("temperature") or 1.0),
            "top_p": float(settings.get("top_p") or 1.0),
            "top_k": int(settings.get("top_k") or 50),
            "max_tokens": max(1, int(max_new_tokens)),
            "stream": False,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            _server_chat_url(port),
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MediaLens-Gemma-GGUF",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=max(60, max_new_tokens)) as response:
            result = json.loads(response.read().decode("utf-8", errors="replace"))
        choices = list(result.get("choices") or [])
        if not choices:
            raise RuntimeError("Gemma GGUF server returned no choices.")
        message = dict(choices[0].get("message") or {})
        text = clean_response_text(message.get("content") or "")
        if not text:
            finish_reason = str(choices[0].get("finish_reason") or "").strip()
            raise RuntimeError(
                f"Gemma GGUF returned an empty response. finish_reason={finish_reason or 'unknown'} response_keys={','.join(sorted(result.keys()))}"
            )
        return text
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Gemma GGUF server request failed: HTTP {exc.code}. {body[:400]}".strip(), file=sys.stderr, flush=True)
    except Exception as server_exc:
        print(f"Gemma GGUF server fallback failed: {server_exc}", file=sys.stderr, flush=True)
    finally:
        _stop_process(process)
    cli_path = _gguf_cli_path(settings)
    if cli_path.is_file():
        return _gguf_cli_completion(source_path, prompt, settings, max_new_tokens)
    raise RuntimeError("Gemma GGUF could not produce a response with server or CLI runtime.")


def _extract_final_description(text: str, settings: dict[str, Any]) -> str:
    return classify_gguf_description(text, str(settings.get("caption_start") or "")).get("description", "")


def _repair_gguf_description(source_path: str, raw_text: str, settings: dict[str, Any], max_new_tokens: int) -> str:
    rewrite_prompt = build_gguf_rewrite_prompt(str(settings.get("caption_start") or ""), raw_text)
    repaired = _generate_text(source_path, rewrite_prompt, settings, max_new_tokens)
    return _extract_final_description(repaired, settings)


def _generate_text(source_path: str, prompt: str, settings: dict[str, Any], max_new_tokens: int) -> str:
    if _gguf_enabled(settings):
        return _gguf_chat_completion(source_path, prompt, settings, max_new_tokens)
    torch, processor, model, target_device = _load_model(settings)
    image = _open_image(source_path)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    )
    if target_device is not None:
        inputs = {key: value.to(target_device) if hasattr(value, "to") else value for key, value in inputs.items()}
    input_len = inputs["input_ids"].shape[-1]
    generation_args = {
        "max_new_tokens": max(1, int(max_new_tokens)),
        "do_sample": bool(settings.get("do_sample") or False),
        "temperature": float(settings.get("temperature") or 1.0),
        "top_k": int(settings.get("top_k") or 50),
        "top_p": float(settings.get("top_p") or 1.0),
        "repetition_penalty": float(settings.get("repetition_penalty") or 1.0),
    }
    with torch.inference_mode():
        output_ids = model.generate(**inputs, **generation_args)
    response = processor.decode(output_ids[0][input_len:], skip_special_tokens=False)
    if hasattr(processor, "parse_response"):
        try:
            response = processor.parse_response(response)
        except Exception:
            pass
    text = clean_response_text(response)
    if not text:
        raise RuntimeError("Gemma 4 returned an empty response.")
    return text


def _split_tags(raw: str, settings: dict[str, Any]) -> list[str]:
    raw = re.sub(r"^(tags?|keywords?)\s*:\s*", "", str(raw or ""), flags=re.IGNORECASE).strip()
    raw = raw.replace("\n", ",")
    tags: list[str] = []
    for part in re.split(r"[,;|]", raw):
        tag = re.sub(r"^[\-\*\d\.\)\s]+", "", part).strip().strip("\"'")
        if tag:
            tags.append(tag)
    excluded = {part.strip().casefold() for part in str(settings.get("tags_to_exclude") or "").split(",") if part.strip()}
    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        key = tag.casefold()
        if key in seen or key in excluded:
            continue
        seen.add(key)
        out.append(tag)
    return out[: max(1, int(settings.get("tag_max_tags") or 75))]


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Run one isolated MediaLens Gemma 4 local AI task.")
    parser.add_argument("--operation", choices=("tags", "description", "preload"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--settings-json", required=True)
    parser.add_argument("--tags-json", default="[]")
    args = parser.parse_args()

    try:
        settings = _settings_from_json(args.settings_json)
        if args.operation == "preload":
            with contextlib.redirect_stdout(sys.stderr):
                if _gguf_enabled(settings):
                    process, _port = _start_gguf_server(settings)
                    _stop_process(process)
                else:
                    _load_model(settings)
            print(json.dumps({"ok": True}, ensure_ascii=False), flush=True)
            return 0
        if args.operation == "tags":
            prompt = (
                "Generate concise searchable tags for this image. Return only comma-separated tags, "
                f"with at most {max(1, int(settings.get('tag_max_tags') or 75))} tags."
            )
            extra = str(settings.get("tag_prompt") or "").strip()
            if extra:
                prompt = f"{prompt}\nRules: {extra}"
            with contextlib.redirect_stdout(sys.stderr):
                text = _generate_text(args.source, prompt, settings, max(32, min(512, int(settings.get("tag_max_tags") or 75) * 5)))
            tags = _split_tags(text, settings)
            if not tags:
                raise RuntimeError(f"Gemma 4 returned no parseable tags. Raw response: {text[:240]}")
            print(json.dumps({"ok": True, "tags": tags}, ensure_ascii=False), flush=True)
            return 0
        tags = [str(tag) for tag in json.loads(args.tags_json or "[]") if str(tag).strip()]
        inference_settings = settings
        if _gguf_enabled(settings):
            inference_settings = tune_gguf_description_settings(settings)
            prompt = build_gguf_description_prompt(
                str(settings.get("caption_prompt") or DEFAULT_CAPTION_PROMPT),
                tags,
                str(settings.get("caption_start") or ""),
            )
        else:
            prompt_template = str(settings.get("caption_prompt") or DEFAULT_CAPTION_PROMPT)
            prompt = _build_description_prompt(prompt_template, tags, str(settings.get("caption_start") or ""))
        max_new_tokens = max(1, int(settings.get("max_new_tokens") or 200))
        with contextlib.redirect_stdout(sys.stderr):
            raw_description = _generate_text(args.source, prompt, inference_settings, max_new_tokens)
        description = _extract_final_description(raw_description, settings)
        if _gguf_enabled(settings):
            initial_result = classify_gguf_description(raw_description, str(settings.get("caption_start") or ""))
            print(
                "Gemma GGUF description initial: "
                f"reason={initial_result.get('reason')} "
                f"raw={initial_result.get('raw_excerpt')} "
                f"clean={initial_result.get('clean_excerpt')} "
                f"extracted={excerpt_text(initial_result.get('description'))}",
                file=sys.stderr,
                flush=True,
            )
        if not description:
            if _gguf_enabled(settings):
                with contextlib.redirect_stdout(sys.stderr):
                    description = _repair_gguf_description(
                        args.source,
                        raw_description,
                        inference_settings,
                        max_new_tokens,
                    )
                repaired_result = classify_gguf_description(description, str(settings.get("caption_start") or "")) if description else {"reason": "empty"}
                print(
                    "Gemma GGUF description repair: "
                    f"reason={repaired_result.get('reason')} "
                    f"extracted={excerpt_text(repaired_result.get('description'))}",
                    file=sys.stderr,
                    flush=True,
                )
                if not description:
                    description = salvage_description(raw_description)
                    print(
                        "Gemma GGUF description salvage: "
                        f"extracted={excerpt_text(description)}",
                        file=sys.stderr,
                        flush=True,
                    )
                if not description:
                    failure = classify_gguf_description(raw_description, str(settings.get("caption_start") or ""))
                    raise RuntimeError(
                        "Gemma GGUF returned no description "
                        f"(reason={failure.get('reason')}, raw={failure.get('raw_excerpt')}, clean={failure.get('clean_excerpt')})."
                    )
            else:
                raise RuntimeError("Gemma 4 produced an empty description.")
        print(json.dumps({"ok": True, "description": description}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc) or exc.__class__.__name__}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(_run_cli())
