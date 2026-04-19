from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


TAG_MODEL_ID = "SmilingWolf/wd-swinv2-tagger-v3"
CAPTION_MODEL_ID = "internlm/internlm-xcomposer2-vl-1_8b"
GEMMA4_MODEL_ID = "google/gemma-4-E2B-it"


@dataclass(frozen=True)
class LocalAiModelSpec:
    id: str
    kind: str
    label: str
    worker_module: str
    venv_dir: str
    settings_key: str
    install_label: str
    requirements_file: str
    description: str
    estimated_size: str


MODEL_SPECS: tuple[LocalAiModelSpec, ...] = (
    LocalAiModelSpec(
        id=TAG_MODEL_ID,
        kind="tagger",
        label="WD SwinV2 Tagger v3",
        worker_module="app.mediamanager.ai_captioning.wd_swinv2_worker",
        venv_dir=".venv-wd-swinv2",
        settings_key="wd_swinv2",
        install_label="WD SwinV2 Tagger v3",
        requirements_file="requirements-local-ai-wd-swinv2.txt",
        description="Fast searchable tag generation for images.",
        estimated_size="Approx. 0.6 GB download total (runtime packages plus 467 MB model files on first use).",
    ),
    LocalAiModelSpec(
        id=GEMMA4_MODEL_ID,
        kind="tagger",
        label="Gemma 4 E2B Instruct",
        worker_module="app.mediamanager.ai_captioning.gemma_worker",
        venv_dir=".venv-gemma",
        settings_key="gemma4",
        install_label="Gemma 4",
        requirements_file="requirements-local-ai-gemma.txt",
        description="General vision-language model for tags and descriptions.",
        estimated_size="Approx. 13.0 GB download total (10.3 GB model files plus 2.6 GB Torch runtime).",
    ),
    LocalAiModelSpec(
        id=CAPTION_MODEL_ID,
        kind="captioner",
        label="InternLM XComposer2 VL 1.8B",
        worker_module="app.mediamanager.ai_captioning.xcomposer2_worker",
        venv_dir=".venv-internlm-xcomposer2",
        settings_key="internlm_xcomposer2",
        install_label="InternLM XComposer2 VL 1.8B",
        requirements_file="requirements-local-ai-internlm-xcomposer2.txt",
        description="Image description generation using your description prompt.",
        estimated_size="Approx. 7.6 GB download total (4.9 GB model files plus 2.6 GB Torch runtime).",
    ),
    LocalAiModelSpec(
        id=GEMMA4_MODEL_ID,
        kind="captioner",
        label="Gemma 4 E2B Instruct",
        worker_module="app.mediamanager.ai_captioning.gemma_worker",
        venv_dir=".venv-gemma",
        settings_key="gemma4",
        install_label="Gemma 4",
        requirements_file="requirements-local-ai-gemma.txt",
        description="General vision-language model for tags and descriptions.",
        estimated_size="Approx. 13.0 GB download total (10.3 GB model files plus 2.6 GB Torch runtime).",
    ),
)


def available_models() -> list[dict[str, str]]:
    return [
        {
            "id": spec.id,
            "kind": spec.kind,
            "label": spec.label,
            "description": spec.description,
            "estimated_size": spec.estimated_size,
        }
        for spec in MODEL_SPECS
    ]


def model_ids_for_kind(kind: str) -> set[str]:
    return {spec.id for spec in MODEL_SPECS if spec.kind == kind}


def model_spec(model_id: str, kind: str) -> LocalAiModelSpec:
    for spec in MODEL_SPECS:
        if spec.id == model_id and spec.kind == kind:
            return spec
    raise KeyError(f"Unsupported local AI {kind} model: {model_id}")


def default_python_for_runtime(project_root: Path, spec: LocalAiModelSpec) -> Path:
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return Path(project_root) / spec.venv_dir / scripts_dir / executable


def current_python_matches_runtime(spec: LocalAiModelSpec) -> bool:
    # Dev fallback only: this lets existing installs keep working until the
    # per-model runtime folders have been created. Packaged builds should ship
    # or install the model-specific interpreter paths directly.
    exe = Path(sys.executable).resolve()
    return bool(re.search(rf"{re.escape(spec.venv_dir)}(?:$|[\\/])", str(exe), flags=re.IGNORECASE))
