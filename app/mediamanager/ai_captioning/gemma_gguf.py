from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


GEMMA_GGUF_BACKEND_ID = "llama_cpp_gguf"
LLAMA_CPP_RELEASE_TAG = "b8832"
LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP = "llama-b8832-bin-win-cuda-12.4-x64.zip"
LLAMA_CPP_WINDOWS_CUDA12_ZIP = "cudart-llama-bin-win-cuda-12.4-x64.zip"
LLAMA_CPP_WINDOWS_CUDA12_BIN_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_CPP_RELEASE_TAG}/{LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP}"
)
LLAMA_CPP_WINDOWS_CUDA12_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_CPP_RELEASE_TAG}/{LLAMA_CPP_WINDOWS_CUDA12_ZIP}"
)

GEMMA_GGUF_HEADROOM_GB = 2.0


@dataclass(frozen=True)
class GemmaGgufProfile:
    id: str
    label: str
    repo_id: str
    model_filename: str
    mmproj_filename: str
    quantization: str
    approx_model_gb: float
    approx_mmproj_gb: float
    effective_params_label: str
    recommended_ctx: int
    quality_rank: int
    min_total_vram_gb: float

    @property
    def approx_total_gb(self) -> float:
        return float(self.approx_model_gb) + float(self.approx_mmproj_gb)

    @property
    def model_url(self) -> str:
        return f"https://huggingface.co/{self.repo_id}/resolve/main/{self.model_filename}"

    @property
    def mmproj_url(self) -> str:
        return f"https://huggingface.co/{self.repo_id}/resolve/main/{self.mmproj_filename}"


GEMMA_GGUF_PROFILES: tuple[GemmaGgufProfile, ...] = (
    GemmaGgufProfile(
        id="e4b_q6_k",
        label="Gemma 4 E4B Q6_K",
        repo_id="unsloth/gemma-4-E4B-it-GGUF",
        model_filename="gemma-4-E4B-it-Q6_K.gguf",
        mmproj_filename="mmproj-BF16.gguf",
        quantization="Q6_K",
        approx_model_gb=7.07,
        approx_mmproj_gb=0.99,
        effective_params_label="4.5B effective",
        recommended_ctx=2048,
        quality_rank=400,
        min_total_vram_gb=10.0,
    ),
    GemmaGgufProfile(
        id="e4b_q4_k_m",
        label="Gemma 4 E4B Q4_K_M",
        repo_id="unsloth/gemma-4-E4B-it-GGUF",
        model_filename="gemma-4-E4B-it-Q4_K_M.gguf",
        mmproj_filename="mmproj-BF16.gguf",
        quantization="Q4_K_M",
        approx_model_gb=4.98,
        approx_mmproj_gb=0.99,
        effective_params_label="4.5B effective",
        recommended_ctx=2048,
        quality_rank=300,
        min_total_vram_gb=8.0,
    ),
    GemmaGgufProfile(
        id="e2b_q6_k",
        label="Gemma 4 E2B Q6_K",
        repo_id="unsloth/gemma-4-E2B-it-GGUF",
        model_filename="gemma-4-E2B-it-Q6_K.gguf",
        mmproj_filename="mmproj-BF16.gguf",
        quantization="Q6_K",
        approx_model_gb=4.50,
        approx_mmproj_gb=0.99,
        effective_params_label="2.3B effective",
        recommended_ctx=2048,
        quality_rank=200,
        min_total_vram_gb=7.0,
    ),
    GemmaGgufProfile(
        id="e2b_q4_k_m",
        label="Gemma 4 E2B Q4_K_M",
        repo_id="unsloth/gemma-4-E2B-it-GGUF",
        model_filename="gemma-4-E2B-it-Q4_K_M.gguf",
        mmproj_filename="mmproj-BF16.gguf",
        quantization="Q4_K_M",
        approx_model_gb=3.11,
        approx_mmproj_gb=0.99,
        effective_params_label="2.3B effective",
        recommended_ctx=2048,
        quality_rank=100,
        min_total_vram_gb=5.0,
    ),
)


def gemma_profile_by_id(profile_id: str) -> GemmaGgufProfile | None:
    for profile in GEMMA_GGUF_PROFILES:
        if profile.id == str(profile_id or "").strip():
            return profile
    return None


def choose_best_gemma_profile(total_vram_gb: float | None, free_vram_gb: float | None = None) -> GemmaGgufProfile:
    total = max(0.0, float(total_vram_gb or 0.0))
    free = max(0.0, float(free_vram_gb or 0.0))
    usable = max(0.0, total - GEMMA_GGUF_HEADROOM_GB)
    if free > 0.0:
        usable = min(usable or free, free + 0.5)
    candidates = [
        profile
        for profile in GEMMA_GGUF_PROFILES
        if total >= profile.min_total_vram_gb and usable >= profile.approx_total_gb
    ]
    if candidates:
        return sorted(candidates, key=lambda item: (item.quality_rank, item.approx_total_gb), reverse=True)[0]
    for profile in reversed(GEMMA_GGUF_PROFILES):
        if usable >= profile.approx_total_gb:
            return profile
    return GEMMA_GGUF_PROFILES[-1]


def gemma_profile_install_dir(models_dir: Path, profile: GemmaGgufProfile) -> Path:
    return Path(models_dir) / "gemma_gguf" / profile.id


def gemma_profile_model_path(models_dir: Path, profile: GemmaGgufProfile) -> Path:
    return gemma_profile_install_dir(models_dir, profile) / profile.model_filename


def gemma_profile_mmproj_path(models_dir: Path, profile: GemmaGgufProfile) -> Path:
    return gemma_profile_install_dir(models_dir, profile) / profile.mmproj_filename


def gemma_profile_is_installed(models_dir: Path, profile: GemmaGgufProfile) -> bool:
    return gemma_profile_model_path(models_dir, profile).is_file() and gemma_profile_mmproj_path(models_dir, profile).is_file()
