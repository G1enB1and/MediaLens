from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeLocalAiMixin:
    def _local_ai_source_path(self, media_path: Path) -> Path:
        suffix = media_path.suffix.lower()
        needs_poster = (
            suffix in VIDEO_EXTS
            or suffix in {".avif", ".heic", ".heif", ".tif", ".tiff", ".webp"}
            or self._is_animated(media_path)
        )
        if not needs_poster:
            return media_path
        poster = self._video_poster_path(media_path)
        if poster.exists():
            return poster
        poster = self._ensure_video_poster(media_path)
        if poster and poster.exists():
            return poster
        raise RuntimeError("No preview image is available for local AI captioning.")

    def _local_ai_models_dir_default(self) -> str:
        if bool(getattr(sys, "frozen", False)):
            return str(_appdata_runtime_dir() / "local_ai_models")
        from app.mediamanager.ai_captioning.local_captioning import project_models_dir

        return str(project_models_dir())

    def _local_ai_worker_source_root(self) -> Path:
        roots: list[Path] = []
        meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
        if meipass:
            roots.append(Path(meipass))
        if bool(getattr(sys, "frozen", False)):
            roots.append(Path(sys.executable).resolve().parent)
            roots.append(Path(sys.executable).resolve().parent / "_internal")
        roots.append(Path(__file__).resolve().parents[2])

        for root in roots:
            if (root / "app" / "mediamanager" / "ai_captioning" / "model_registry.py").is_file():
                return root
        return roots[0] if roots else Path(__file__).resolve().parents[2]

    def _local_ai_runtime_root(self) -> Path:
        configured = str(self.settings.value("ai_caption/runtime_root", "", type=str) or "").strip()
        if configured:
            return Path(configured)
        if bool(getattr(sys, "frozen", False)):
            return _appdata_runtime_dir() / "ai-runtimes"
        return Path(__file__).resolve().parents[2]

    def _local_ai_python_bootstrap_root(self) -> Path:
        configured = str(self.settings.value("ai_caption/python_bootstrap_root", "", type=str) or "").strip()
        if configured:
            return Path(configured)
        return _appdata_runtime_dir() / "python" / f"cpython-{LOCAL_AI_PYTHON_VERSION}"

    def _local_ai_python_bootstrap_exe(self) -> Path:
        if os.name == "nt":
            return self._local_ai_python_bootstrap_root() / "python.exe"
        return self._local_ai_python_bootstrap_root() / "bin" / "python"

    def _local_ai_bootstrap_download_dir(self) -> Path:
        return _appdata_runtime_dir() / "python-bootstrap"

    def _local_ai_requirements_path(self, spec) -> Path:
        source_root = self._local_ai_worker_source_root()
        candidates = [
            source_root / spec.requirements_file,
            source_root / "_internal" / spec.requirements_file,
            Path(__file__).resolve().parents[2] / spec.requirements_file,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return candidates[0]

    def _local_ai_worker_launcher(self, python_path: str | Path, worker_module: str) -> tuple[list[str], Path, str]:
        source_root = self._local_ai_worker_source_root()
        worker_script = source_root / Path(*str(worker_module).split(".")).with_suffix(".py")
        if worker_script.is_file():
            return [str(python_path), str(worker_script)], self._local_ai_runtime_root(), ""
        return [str(python_path), "-m", str(worker_module)], source_root, str(source_root)

    def _local_ai_subprocess_env(self, worker_pythonpath: str = "") -> dict[str, str]:
        parent_env = os.environ.copy()
        child_env = parent_env.copy()
        if bool(getattr(sys, "frozen", False)):
            safe_env: dict[str, str] = {}
            for key in (
                "APPDATA",
                "COMSPEC",
                "HOMEDRIVE",
                "HOMEPATH",
                "LOCALAPPDATA",
                "NUMBER_OF_PROCESSORS",
                "OS",
                "PATHEXT",
                "PROCESSOR_ARCHITECTURE",
                "PROCESSOR_IDENTIFIER",
                "PROCESSOR_LEVEL",
                "PROCESSOR_REVISION",
                "PROGRAMDATA",
                "SYSTEMDRIVE",
                "SYSTEMROOT",
                "TEMP",
                "TMP",
                "USERDOMAIN",
                "USERNAME",
                "USERPROFILE",
                "WINDIR",
            ):
                value = str(parent_env.get(key, "") or "").strip()
                if value:
                    safe_env[key] = value
            for key, value in parent_env.items():
                upper = str(key).upper()
                if upper.startswith(("CUDA_", "NVIDIA_", "NV_")):
                    safe_env[str(key)] = str(value)
            blocked_roots: list[str] = []
            try:
                app_root = Path(sys.executable).resolve().parent
                blocked_roots.append(str(app_root).replace("\\", "/").casefold())
                blocked_roots.append(str((app_root / "_internal")).replace("\\", "/").casefold())
            except Exception:
                pass
            try:
                meipass = str(getattr(sys, "_MEIPASS", "") or "").strip()
                if meipass:
                    blocked_roots.append(str(Path(meipass).resolve()).replace("\\", "/").casefold())
            except Exception:
                pass
            allowed_path_prefixes = (
                "c:/windows",
                "c:\\windows",
            )
            allowed_path_markers = (
                "nvidia",
                "cuda",
                "cudnn",
                "powershell",
                "system32",
                "wbem",
            )
            path_entries = [entry.strip() for entry in str(parent_env.get("PATH") or "").split(os.pathsep) if entry.strip()]
            filtered_entries: list[str] = []
            seen_entries: set[str] = set()
            for entry in path_entries:
                normalized = entry.replace("\\", "/").casefold()
                if any(normalized.startswith(root) for root in blocked_roots if root):
                    continue
                if normalized in seen_entries:
                    continue
                if normalized.startswith(allowed_path_prefixes) or any(marker in normalized for marker in allowed_path_markers):
                    filtered_entries.append(entry)
                    seen_entries.add(normalized)
            safe_env["PATH"] = os.pathsep.join(filtered_entries)
            child_env = safe_env
            self._log(
                "Local AI subprocess env prepared: "
                f"mode=frozen-clean path_entries={len(filtered_entries)} "
                f"pythonpath={'yes' if bool(worker_pythonpath) else 'no'}"
            )
        if worker_pythonpath:
            child_env["PYTHONPATH"] = worker_pythonpath + (os.pathsep + child_env["PYTHONPATH"] if child_env.get("PYTHONPATH") else "")
        else:
            child_env.pop("PYTHONPATH", None)
        return child_env

    def _local_ai_runtime_python_path(self, spec) -> Path:
        from app.mediamanager.ai_captioning.model_registry import default_python_for_runtime

        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        return Path(configured) if configured else default_python_for_runtime(self._local_ai_runtime_root(), spec)

    def _local_ai_status_payload_for_spec(self, spec) -> dict:
        python_path = self._local_ai_runtime_python_path(spec)
        requirements_path = self._local_ai_requirements_path(spec)
        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        model_files_installed = self._local_ai_model_files_installed(models_dir, spec.id)
        installed = python_path.is_file() and model_files_installed
        dev_fallback = False
        if not installed and model_files_installed and not bool(getattr(sys, "frozen", False)) and not configured:
            installed = True
            dev_fallback = True
        running = spec.settings_key in self._local_ai_model_installs
        profile_download_id = str(getattr(self, "_local_ai_profile_downloads", {}).get(spec.settings_key, "") or "").strip()
        profile_downloading = bool(profile_download_id)
        if running:
            state = "installing"
            message = f"Installing {spec.install_label}..."
        elif installed:
            state = "installed"
            message = "Installed."
        else:
            state = "not_installed"
            message = "Not installed. Install this model before using it."
        runtime_probe = self._local_ai_probe_runtime(spec) if installed else {}
        runtime_summary = self._local_ai_runtime_summary(runtime_probe)
        runtime_details_html = self._local_ai_runtime_details_html(runtime_probe)
        gemma_downloaded_profiles: list[str] = []
        selected_profile_id = ""
        if spec.settings_key == "gemma4":
            self._sync_selected_gemma_profile_settings(sync_qsettings=False)
            gemma_downloaded_profiles = self._local_ai_gemma_downloaded_profile_ids(models_dir)
            selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        return {
            "id": spec.id,
            "kind": spec.kind,
            "label": spec.label,
            "settings_key": spec.settings_key,
            "description": spec.description,
            "estimated_size": spec.estimated_size,
            "state": state,
            "installed": installed,
            "running": running,
            "dev_fallback": dev_fallback,
            "model_files_installed": model_files_installed,
            "model_files_cached": model_files_installed,
            "message": message,
            "runtime_python": str(python_path),
            "runtime_dir": str(Path(python_path).parent.parent),
            "location": str(Path(python_path).parent.parent),
            "requirements_file": str(requirements_path),
            "python_bootstrap": str(self._local_ai_python_bootstrap_exe()),
            "runtime_probe": runtime_probe,
            "runtime_summary": runtime_summary,
            "runtime_details_html": runtime_details_html,
            "gemma_downloaded_profiles": gemma_downloaded_profiles,
            "gemma_selected_profile_id": selected_profile_id,
            "gemma_profile_downloading": profile_downloading,
            "gemma_profile_downloading_id": profile_download_id,
        }

    def _local_ai_model_cache_targets(self, models_dir: Path, spec) -> list[Path]:
        targets = [Path(models_dir) / spec.id]
        if spec.id == "internlm/internlm-xcomposer2-vl-1_8b":
            targets.append(Path(models_dir) / "openai" / "clip-vit-large-patch14-336")
        if spec.id == "google/gemma-4-E2B-it":
            targets.append(Path(models_dir) / "gemma_gguf")
            targets.append(Path(models_dir) / "gemma4_runtime")
        return targets

    def _local_ai_gemma_downloaded_profile_ids(self, models_dir: Path) -> list[str]:
        from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_is_installed, gemma_profile_options

        downloaded: list[str] = []
        for profile in gemma_profile_options():
            try:
                if gemma_profile_is_installed(models_dir, profile):
                    downloaded.append(profile.id)
            except Exception:
                continue
        return downloaded

    def _local_ai_model_files_installed(self, models_dir: Path, model_id: str) -> bool:
        from app.mediamanager.ai_captioning.model_registry import CAPTION_MODEL_ID, GEMMA4_MODEL_ID, TAG_MODEL_ID
        from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id, gemma_profile_is_installed

        local_dir = Path(models_dir) / model_id
        if model_id == TAG_MODEL_ID:
            return (local_dir / "model.onnx").is_file() and (local_dir / "selected_tags.csv").is_file()
        if model_id == CAPTION_MODEL_ID:
            clip_dir = Path(models_dir) / "openai" / "clip-vit-large-patch14-336"
            return (local_dir / "config.json").is_file() and any(local_dir.glob("*.safetensors")) and (clip_dir / "config.json").is_file()
        if model_id == GEMMA4_MODEL_ID:
            profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""))
            if profile and gemma_profile_is_installed(models_dir, profile):
                return True
            if (local_dir / "config.json").is_file() and any(local_dir.glob("*.safetensors")):
                return True
            hf_home = Path(models_dir) / "gemma4_runtime" / "hf_home"
            return any((snapshot / "config.json").is_file() and any(snapshot.glob("*.safetensors")) for snapshot in hf_home.glob("hub/models--google--gemma-4-E2B-it/snapshots/*"))
        return (local_dir / "config.json").is_file()

    @staticmethod
    def _verify_python_can_create_venvs(command: list[str]) -> str:
        result = subprocess.run(
            [*command, "-c", "import venv, sys; print(sys.executable)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        if result.returncode != 0:
            raise RuntimeError(str(result.stderr or result.stdout or "Python cannot create virtual environments.").strip())
        return str(result.stdout.strip() or command[0])

    def _local_ai_bundled_python_installer(self) -> Path | None:
        source_root = self._local_ai_worker_source_root()
        candidates = [
            source_root / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME,
            source_root / "_internal" / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME,
            Path(sys.executable).resolve().parent / "tools" / "python" / LOCAL_AI_PYTHON_PACKAGE_NAME if bool(getattr(sys, "frozen", False)) else Path(),
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _file_sha512_base64(path: Path) -> str:
        digest = hashlib.sha512()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return base64.b64encode(digest.digest()).decode("ascii")

    def _verify_local_ai_python_package(self, path: Path) -> None:
        actual = self._file_sha512_base64(path)
        if actual != LOCAL_AI_PYTHON_PACKAGE_SHA512:
            raise RuntimeError("Python bootstrap package did not match the expected checksum.")

    def _download_local_ai_python_package(self, emit_status) -> Path:
        download_dir = self._local_ai_bootstrap_download_dir()
        download_dir.mkdir(parents=True, exist_ok=True)
        package_path = download_dir / LOCAL_AI_PYTHON_PACKAGE_NAME
        if package_path.is_file():
            self._verify_local_ai_python_package(package_path)
            return package_path
        temp_path = package_path.with_suffix(".download")
        if temp_path.exists():
            temp_path.unlink()
        request = urllib.request.Request(
            LOCAL_AI_PYTHON_PACKAGE_URL,
            headers={"User-Agent": f"MediaLens/{__version__}"},
        )
        emit_status(f"Downloading Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")
        with urllib.request.urlopen(request, timeout=45) as response:
            total = int(response.headers.get("Content-Length") or 0)
            received = 0
            last_emit = 0.0
            with open(temp_path, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    handle.write(chunk)
                    received += len(chunk)
                    if time.monotonic() - last_emit >= 1.0:
                        last_emit = time.monotonic()
                        if total:
                            percent = int(round((received / total) * 100))
                            emit_status(f"Downloading Python bootstrap: {percent}% ({received // (1024 * 1024)} MB / {total // (1024 * 1024)} MB)")
                        else:
                            emit_status(f"Downloading Python bootstrap: {received // (1024 * 1024)} MB")
        self._verify_local_ai_python_package(temp_path)
        if package_path.exists():
            package_path.unlink()
        temp_path.replace(package_path)
        return package_path

    def _extract_local_ai_python_package(self, package_path: Path, emit_status) -> None:
        self._verify_local_ai_python_package(package_path)
        target_dir = self._local_ai_python_bootstrap_root()
        temp_dir = target_dir.with_name(f"{target_dir.name}.extracting")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if target_dir.exists() and not self._local_ai_python_bootstrap_exe().is_file():
            shutil.rmtree(target_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        emit_status(f"Extracting Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")
        try:
            with zipfile.ZipFile(package_path, "r") as archive:
                for member in archive.infolist():
                    name = member.filename.replace("\\", "/")
                    if not name.startswith("tools/") or name.endswith("/"):
                        continue
                    relative = Path(*name.split("/")[1:])
                    if not relative.parts:
                        continue
                    target = temp_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, open(target, "wb") as dest:
                        shutil.copyfileobj(source, dest)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            temp_dir.replace(target_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _ensure_local_ai_python_bootstrap(self, emit_status) -> str:
        bootstrap_python = self._local_ai_python_bootstrap_exe()
        if bootstrap_python.is_file():
            try:
                return self._verify_python_can_create_venvs([str(bootstrap_python)])
            except Exception:
                pass
        if os.name != "nt":
            return self._find_local_ai_bootstrap_python()

        package_path = self._local_ai_bundled_python_installer()
        if package_path is None:
            package_path = self._download_local_ai_python_package(emit_status)
        else:
            self._verify_local_ai_python_package(package_path)
            emit_status(f"Using bundled Python {LOCAL_AI_PYTHON_VERSION} bootstrap...")

        self._extract_local_ai_python_package(package_path, emit_status)
        if not bootstrap_python.is_file():
            raise RuntimeError("Python bootstrap install finished, but python.exe was not found.")
        emit_status(f"Python {LOCAL_AI_PYTHON_VERSION} bootstrap is ready.")
        return self._verify_python_can_create_venvs([str(bootstrap_python)])

    def _find_local_ai_bootstrap_python(self) -> str:
        candidates: list[list[str]] = []
        if not bool(getattr(sys, "frozen", False)) and Path(sys.executable).is_file():
            candidates.append([sys.executable])
        if os.name == "nt":
            candidates.extend([["py", "-3.12"], ["py", "-3"], ["python"]])
        else:
            candidates.extend([["python3"], ["python"]])
        for command in candidates:
            try:
                return self._verify_python_can_create_venvs(command)
            except Exception:
                continue
        return ""

    def _local_ai_detect_nvidia_vram(self) -> dict[str, object]:
        result: dict[str, object] = {
            "available": False,
            "gpu_name": "",
            "driver_version": "",
            "total_vram_gb": 0.0,
            "free_vram_gb": 0.0,
            "reason": "",
        }
        if os.name != "nt":
            result["reason"] = "NVIDIA VRAM detection is implemented for Windows only."
            return result
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            result["reason"] = str(exc) or exc.__class__.__name__
            return result
        if completed.returncode != 0:
            result["reason"] = str(completed.stderr or completed.stdout or "nvidia-smi failed").strip()
            return result
        first_line = next((line.strip() for line in str(completed.stdout or "").splitlines() if line.strip()), "")
        if not first_line:
            result["reason"] = "nvidia-smi returned no GPU rows."
            return result
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) < 4:
            result["reason"] = f"Unexpected nvidia-smi output: {first_line}"
            return result
        try:
            total_gb = round(float(parts[2]) / 1024.0, 2)
            free_gb = round(float(parts[3]) / 1024.0, 2)
        except Exception as exc:
            result["reason"] = f"Could not parse VRAM values: {exc}"
            return result
        result.update(
            {
                "available": True,
                "gpu_name": parts[0],
                "driver_version": parts[1],
                "total_vram_gb": total_gb,
                "free_vram_gb": free_gb,
            }
        )
        return result

    @staticmethod
    def _download_file(url: str, destination: Path, emit_status, should_cancel=None) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_suffix(destination.suffix + ".download")
        if temp_path.exists():
            temp_path.unlink()
        request = urllib.request.Request(
            str(url),
            headers={"User-Agent": f"MediaLens/{__version__}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                total = int(response.headers.get("Content-Length") or 0)
                received = 0
                last_emit = 0.0
                with open(temp_path, "wb") as handle:
                    while True:
                        if callable(should_cancel) and should_cancel():
                            raise RuntimeError("Download canceled.")
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        received += len(chunk)
                        if time.monotonic() - last_emit >= 1.0:
                            last_emit = time.monotonic()
                            if total:
                                emit_status(
                                    f"Downloading {destination.name}: {int(round((received / total) * 100))}% "
                                    f"({received // (1024 * 1024)} MB / {total // (1024 * 1024)} MB)"
                                )
                            else:
                                emit_status(f"Downloading {destination.name}: {received // (1024 * 1024)} MB")
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise
        if destination.exists():
            destination.unlink()
        temp_path.replace(destination)
        return destination

    def _local_ai_gemma_llama_dir(self, runtime_dir: Path) -> Path:
        return Path(runtime_dir) / "llama.cpp"

    def _local_ai_gemma_llama_server_path(self, runtime_dir: Path) -> Path:
        return self._local_ai_gemma_llama_dir(runtime_dir) / "llama-server.exe"

    @staticmethod
    def _extract_zip_into(archive_path: Path, target_dir: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(target_dir)

    def _ensure_gemma_llama_cpp_runtime(self, runtime_dir: Path, emit_status) -> Path:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            LLAMA_CPP_WINDOWS_CUDA12_BIN_URL,
            LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP,
            LLAMA_CPP_WINDOWS_CUDA12_URL,
            LLAMA_CPP_WINDOWS_CUDA12_ZIP,
        )

        llama_dir = self._local_ai_gemma_llama_dir(runtime_dir)
        server_path = self._local_ai_gemma_llama_server_path(runtime_dir)
        if server_path.is_file():
            return server_path
        llama_dir.mkdir(parents=True, exist_ok=True)
        bin_archive_path = llama_dir / LLAMA_CPP_WINDOWS_CUDA12_BIN_ZIP
        archive_path = llama_dir / LLAMA_CPP_WINDOWS_CUDA12_ZIP
        emit_status("Downloading llama.cpp CUDA binaries...")
        self._download_file(LLAMA_CPP_WINDOWS_CUDA12_BIN_URL, bin_archive_path, emit_status)
        emit_status("Downloading llama.cpp CUDA runtime libraries...")
        self._download_file(LLAMA_CPP_WINDOWS_CUDA12_URL, archive_path, emit_status)
        temp_dir = llama_dir.with_name(f"{llama_dir.name}.extracting")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        emit_status("Extracting llama.cpp CUDA files...")
        try:
            self._extract_zip_into(bin_archive_path, temp_dir)
            self._extract_zip_into(archive_path, temp_dir)
            server_candidates = list(temp_dir.rglob("llama-server.exe"))
            if not server_candidates:
                raise RuntimeError("llama.cpp archives were extracted, but llama-server.exe was not found in the release contents.")
            extracted_root = server_candidates[0].parent
            if llama_dir.exists():
                shutil.rmtree(llama_dir, ignore_errors=True)
            extracted_root.replace(llama_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        if not server_path.is_file():
            raise RuntimeError("llama.cpp runtime install completed, but llama-server.exe was not found.")
        return server_path

    def _choose_gemma_gguf_profile(self):
        from app.mediamanager.ai_captioning.gemma_gguf import choose_best_gemma_profile, gemma_profile_by_id

        vram = self._local_ai_detect_nvidia_vram()
        selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        selected_profile = gemma_profile_by_id(selected_profile_id) if selected_profile_id else None
        if selected_profile is not None:
            return selected_profile, vram
        return choose_best_gemma_profile(vram.get("total_vram_gb"), vram.get("free_vram_gb")), vram

    def _ensure_gemma_gguf_profile_downloaded(self, models_dir: Path, profile, emit_status) -> tuple[Path, Path]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            gemma_profile_install_dir,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        install_dir = gemma_profile_install_dir(models_dir, profile)
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        install_dir.mkdir(parents=True, exist_ok=True)
        if not model_path.is_file():
            emit_status(f"Downloading {profile.label} model weights...")
            self._download_file(profile.model_url, model_path, emit_status)
        if not mmproj_path.is_file():
            emit_status(f"Downloading {profile.label} vision projector...")
            self._download_file(profile.mmproj_url, mmproj_path, emit_status)
        return model_path, mmproj_path

    def _download_gemma_gguf_profile_concurrent(self, models_dir: Path, profile, emit_install_status, payload: dict) -> tuple[Path, Path]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            gemma_profile_install_dir,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        install_dir = gemma_profile_install_dir(models_dir, profile)
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        install_dir.mkdir(parents=True, exist_ok=True)
        errors: list[Exception] = []
        lock = threading.Lock()
        download_messages: dict[str, str] = {}

        def emit_download_status(kind: str, message: str) -> None:
            with lock:
                download_messages[kind] = str(message or "").strip()
                payload.update(
                    {
                        "running": True,
                        "download_message": "\n".join(text for text in download_messages.values() if text),
                        "download_messages": dict(download_messages),
                        "gemma_profile_downloading": True,
                        "gemma_profile_downloading_id": profile.id,
                    }
                )
                self.localAiModelInstallStatus.emit("gemma4", dict(payload))

        cancel_check = lambda: bool(getattr(self, "_local_ai_profile_download_cancel", {}).get("gemma4"))

        def download_one(kind: str, url: str, destination: Path) -> None:
            try:
                self._download_file(url, destination, lambda message: emit_download_status(kind, message), cancel_check)
            except Exception as exc:
                errors.append(exc)
            finally:
                with lock:
                    download_messages.pop(kind, None)
                    payload.update(
                        {
                            "download_message": "\n".join(text for text in download_messages.values() if text),
                            "download_messages": dict(download_messages),
                            "gemma_profile_downloading": bool(download_messages),
                            "gemma_profile_downloading_id": profile.id if download_messages else "",
                        }
                    )
                    self.localAiModelInstallStatus.emit("gemma4", dict(payload))

        workers: list[threading.Thread] = []
        if not model_path.is_file():
            workers.append(threading.Thread(target=download_one, args=("model", profile.model_url, model_path), daemon=True, name=f"gemma-model-{profile.id}"))
        if not mmproj_path.is_file():
            workers.append(threading.Thread(target=download_one, args=("mmproj", profile.mmproj_url, mmproj_path), daemon=True, name=f"gemma-mmproj-{profile.id}"))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        if errors:
            raise errors[0]
        with lock:
            payload["download_message"] = ""
            payload["download_messages"] = {}
            payload["gemma_profile_downloading"] = False
            payload["gemma_profile_downloading_id"] = ""
            self.localAiModelInstallStatus.emit("gemma4", dict(payload))
        return model_path, mmproj_path

    def _configure_gemma_gguf_settings(self, profile, runtime_dir: Path, models_dir: Path, vram_info: dict[str, object]) -> dict[str, str | int]:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        server_path = self._local_ai_gemma_llama_server_path(runtime_dir)
        ctx_size = int(profile.recommended_ctx)
        self.settings.setValue("ai_caption/gemma_backend", GEMMA_GGUF_BACKEND_ID)
        self.settings.setValue("ai_caption/gemma_profile_id", profile.id)
        self.settings.setValue("ai_caption/gemma_profile_label", profile.label)
        self.settings.setValue("ai_caption/gemma_model_path", str(model_path))
        self.settings.setValue("ai_caption/gemma_mmproj_path", str(mmproj_path))
        self.settings.setValue("ai_caption/gemma_llama_server", str(server_path))
        self.settings.setValue("ai_caption/gemma_ctx_size", ctx_size)
        self.settings.setValue("ai_caption/gemma_gpu_layers", 999)
        self.settings.setValue("ai_caption/gemma_detected_total_vram_gb", float(vram_info.get("total_vram_gb") or 0.0))
        self.settings.setValue("ai_caption/gemma_detected_free_vram_gb", float(vram_info.get("free_vram_gb") or 0.0))
        self.settings.sync()
        return {
            "backend": GEMMA_GGUF_BACKEND_ID,
            "profile_id": profile.id,
            "profile_label": profile.label,
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
            "server_path": str(server_path),
            "ctx_size": ctx_size,
        }

    def _sync_selected_gemma_profile_settings(self, *, sync_qsettings: bool = True) -> dict[str, str] | None:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
        if not selected_profile_id:
            return None
        profile = gemma_profile_by_id(selected_profile_id)
        if profile is None:
            return None
        models_dir = Path(
            str(
                self.settings.value(
                    "ai_caption/models_dir",
                    self._local_ai_models_dir_default(),
                    type=str,
                )
                or self._local_ai_models_dir_default()
            )
        )
        if not gemma_profile_is_installed(models_dir, profile):
            return None
        model_path = gemma_profile_model_path(models_dir, profile)
        mmproj_path = gemma_profile_mmproj_path(models_dir, profile)
        self.settings.setValue("ai_caption/gemma_backend", GEMMA_GGUF_BACKEND_ID)
        self.settings.setValue("ai_caption/gemma_profile_id", profile.id)
        self.settings.setValue("ai_caption/gemma_profile_label", profile.label)
        self.settings.setValue("ai_caption/gemma_profile_quantization", profile.quantization)
        self.settings.setValue("ai_caption/gemma_model_path", str(model_path))
        self.settings.setValue("ai_caption/gemma_mmproj_path", str(mmproj_path))
        if sync_qsettings:
            self.settings.sync()
        return {
            "profile_id": profile.id,
            "profile_label": profile.label,
            "profile_quantization": profile.quantization,
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
        }

    def _local_ai_gemma_probe(self, spec) -> dict:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_install_dir,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        python_path = self._local_ai_runtime_python_path(spec)
        requested_device = str(self.settings.value("ai_caption/device", "gpu", type=str) or "gpu").strip().lower() or "gpu"
        backend = str(self.settings.value("ai_caption/gemma_backend", "", type=str) or "").strip().lower()
        server_path = Path(str(self.settings.value("ai_caption/gemma_llama_server", "", type=str) or "").strip())
        configured_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""))
        selected_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or ""))
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        profile = configured_profile
        model_path = Path(str(self.settings.value("ai_caption/gemma_model_path", "", type=str) or "").strip())
        mmproj_path = Path(str(self.settings.value("ai_caption/gemma_mmproj_path", "", type=str) or "").strip())
        if selected_profile and gemma_profile_is_installed(models_dir, selected_profile):
            profile = selected_profile
            model_path = gemma_profile_model_path(models_dir, selected_profile)
            mmproj_path = gemma_profile_mmproj_path(models_dir, selected_profile)
        ctx_size = int(self.settings.value("ai_caption/gemma_ctx_size", 2048, type=int) or 2048)
        vram = self._local_ai_detect_nvidia_vram()
        selected_device = "cpu"
        reason = ""
        if backend != GEMMA_GGUF_BACKEND_ID:
            reason = "Gemma is configured to use the legacy Transformers runtime."
        elif requested_device != "gpu":
            reason = "GPU was not requested."
        elif not server_path.is_file():
            reason = "llama.cpp CUDA runtime is missing."
        elif not model_path.is_file() or not mmproj_path.is_file():
            reason = "Gemma GGUF model files are missing."
        elif not bool(vram.get("available")):
            reason = str(vram.get("reason") or "NVIDIA GPU was not detected.")
        else:
            selected_device = "gpu"
        return {
            "backend": "gguf",
            "ok": backend == GEMMA_GGUF_BACKEND_ID and python_path.is_file(),
            "requested_device": requested_device,
            "selected_device": selected_device,
            "python_executable": str(python_path),
            "profile_id": profile.id if profile else str(self.settings.value("ai_caption/gemma_profile_id", "", type=str) or ""),
            "profile_label": profile.label if profile else str(self.settings.value("ai_caption/gemma_profile_label", "", type=str) or ""),
            "quantization": profile.quantization if profile else "",
            "effective_params_label": profile.effective_params_label if profile else "",
            "approx_model_gb": float(profile.approx_model_gb) if profile else 0.0,
            "approx_total_gb": float(profile.approx_total_gb) if profile else 0.0,
            "ctx_size": ctx_size,
            "llama_server": str(server_path),
            "model_path": str(model_path),
            "mmproj_path": str(mmproj_path),
            "detected_total_vram_gb": float(vram.get("total_vram_gb") or 0.0),
            "detected_free_vram_gb": float(vram.get("free_vram_gb") or 0.0),
            "nvidia_smi": {
                "available": bool(vram.get("available")),
                "gpus": (
                    [
                        {
                            "name": str(vram.get("gpu_name") or "").strip(),
                            "driver_version": str(vram.get("driver_version") or "").strip(),
                        }
                    ]
                    if str(vram.get("gpu_name") or "").strip()
                    else []
                ),
            },
            "reason": reason,
        }

    def _local_ai_runtime_backend(self, spec) -> str:
        if str(getattr(spec, "settings_key", "") or "") == "wd_swinv2":
            return "onnx"
        if str(getattr(spec, "settings_key", "") or "") == "gemma4":
            from app.mediamanager.ai_captioning.gemma_gguf import GEMMA_GGUF_BACKEND_ID

            backend = str(self.settings.value("ai_caption/gemma_backend", "", type=str) or "").strip().lower()
            if backend == GEMMA_GGUF_BACKEND_ID:
                return "gguf"
        return "torch"

    def _local_ai_runtime_probe_command(self, spec, python_path: str | Path, requested_device: str, gpu_index: int) -> tuple[list[str], Path, dict[str, str]]:
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(
            python_path,
            "app.mediamanager.ai_captioning.runtime_probe",
        )
        command = [
            *launcher,
            "--backend",
            self._local_ai_runtime_backend(spec),
            "--requested-device",
            str(requested_device or "gpu"),
            "--gpu-index",
            str(max(0, int(gpu_index or 0))),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        return command, worker_cwd, child_env

    def _local_ai_run_command_stream(self, command: list[str], cwd: Path, message: str, emit_status, env: dict[str, str] | None = None) -> tuple[int, str]:
        payload_message = str(message or "").strip()
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        assert process.stdout is not None
        last_emit = 0.0
        last_line = payload_message
        for line in process.stdout:
            clean = " ".join(str(line or "").split()).strip()
            if clean:
                last_line = clean[-240:]
            if time.monotonic() - last_emit >= 1.0:
                last_emit = time.monotonic()
                emit_status(last_line)
        return process.wait(), last_line

    def _local_ai_run_command_capture(self, command: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 25) -> tuple[int, str, str]:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        return completed.returncode, str(completed.stdout or ""), str(completed.stderr or "")

    def _local_ai_probe_runtime(self, spec, force: bool = False) -> dict:
        cache_key = str(getattr(spec, "settings_key", "") or "")
        now = time.monotonic()
        cached = self._local_ai_runtime_status_cache.get(cache_key)
        if not force and cached and (now - cached[0]) < LOCAL_AI_STATUS_CACHE_TTL_SECONDS:
            cached_payload = dict(cached[1])
            if cache_key != "gemma4":
                return cached_payload
            selected_profile_id = str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip()
            if str(cached_payload.get("profile_id") or "").strip() == selected_profile_id:
                return cached_payload

        backend = self._local_ai_runtime_backend(spec)
        if backend == "gguf":
            payload = self._local_ai_gemma_probe(spec)
            self._local_ai_runtime_status_cache[cache_key] = (now, dict(payload))
            return dict(payload)

        python_path = self._local_ai_runtime_python_path(spec)
        if not python_path.is_file():
            payload = {"ok": False, "reason": "Runtime Python was not found.", "selected_device": "cpu"}
            self._local_ai_runtime_status_cache[cache_key] = (now, payload)
            return dict(payload)

        ai_settings = self._local_ai_caption_settings()
        requested_device = str(ai_settings.device or "gpu")
        gpu_index = int(ai_settings.gpu_index or 0)
        command, worker_cwd, child_env = self._local_ai_runtime_probe_command(spec, python_path, requested_device, gpu_index)
        try:
            returncode, stdout, stderr = self._local_ai_run_command_capture(command, worker_cwd, env=child_env, timeout=30)
        except Exception as exc:
            payload = {"ok": False, "reason": f"Runtime probe failed: {exc}", "selected_device": "cpu"}
            self._local_ai_runtime_status_cache[cache_key] = (now, payload)
            return dict(payload)

        combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
        payload = None
        for line in reversed([line.strip() for line in combined.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            payload = {
                "ok": False,
                "reason": f"Runtime probe exited without JSON ({self._local_ai_exit_code_text(returncode)}).",
                "selected_device": "cpu",
            }
        if returncode != 0 and not payload.get("reason"):
            payload["reason"] = f"Runtime probe failed ({self._local_ai_exit_code_text(returncode)})."
        self._local_ai_runtime_status_cache[cache_key] = (now, dict(payload))
        return dict(payload)

    @staticmethod
    def _local_ai_runtime_summary(probe: dict) -> str:
        if not probe:
            return "Runtime: unavailable"
        backend = str(probe.get("backend") or "").strip().lower()
        selected_device = str(probe.get("selected_device") or "cpu").strip().lower() or "cpu"
        status_label = "GPU" if selected_device.startswith("cuda") or selected_device == "gpu" else "CPU"
        if backend == "torch":
            gpu_names = [str(name).strip() for name in list(probe.get("gpu_names") or []) if str(name).strip()]
            parts = [
                f"Runtime: {status_label}",
                f"Torch {probe.get('torch_version') or '?'}",
            ]
            if probe.get("torch_cuda_version"):
                parts.append(f"CUDA {probe.get('torch_cuda_version')}")
            if selected_device.startswith("cuda") and gpu_names:
                selected_index = int(probe.get("selected_gpu_index") or 0)
                if 0 <= selected_index < len(gpu_names):
                    parts.append(gpu_names[selected_index])
                else:
                    parts.append(gpu_names[0])
            elif gpu_names:
                parts.append(f"Visible GPUs: {len(gpu_names)}")
            if probe.get("reason") and selected_device == "cpu":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        if backend == "onnx":
            active_provider = str(probe.get("active_provider") or "CPUExecutionProvider")
            parts = [
                f"Runtime: {status_label}",
                f"ONNX Runtime {probe.get('onnxruntime_version') or '?'}",
                active_provider,
            ]
            if probe.get("reason") and status_label == "CPU":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        if backend == "gguf":
            parts = [
                f"Runtime: {status_label}",
                "llama.cpp GGUF",
            ]
            profile_label = str(probe.get("profile_label") or "").strip()
            quantization = str(probe.get("quantization") or "").strip()
            if profile_label:
                parts.append(profile_label)
            if quantization:
                parts.append(quantization)
            total_vram = float(probe.get("detected_total_vram_gb") or 0.0)
            if total_vram > 0:
                parts.append(f"VRAM {total_vram:.1f} GB")
            if probe.get("reason") and status_label == "CPU":
                parts.append(str(probe.get("reason")))
            return " | ".join(parts)
        reason = str(probe.get("reason") or "").strip()
        return f"Runtime: {'unavailable' if not probe.get('ok') else status_label}{f' | {reason}' if reason else ''}"

    @staticmethod
    def _local_ai_runtime_details_html(probe: dict) -> str:
        if not probe:
            return ""
        lines: list[str] = []
        backend = str(probe.get("backend") or "").strip().lower()
        selected_device = str(probe.get("selected_device") or "cpu").strip() or "cpu"
        requested_device = str(probe.get("requested_device") or "").strip()
        if requested_device:
            lines.append(f"<b>Device:</b> requested {html.escape(requested_device.upper())}, using {html.escape(selected_device.upper())}")
        if probe.get("python_version"):
            lines.append(f"<b>Python:</b> {html.escape(str(probe.get('python_version')))}")
        if backend == "torch":
            if probe.get("torch_version"):
                lines.append(f"<b>Torch:</b> {html.escape(str(probe.get('torch_version')))}")
            if probe.get("torch_cuda_version"):
                lines.append(f"<b>CUDA:</b> {html.escape(str(probe.get('torch_cuda_version')))}")
            gpu_names = [str(name).strip() for name in list(probe.get("gpu_names") or []) if str(name).strip()]
            if gpu_names:
                lines.append(f"<b>GPUs:</b> {html.escape(', '.join(gpu_names[:3]))}")
        elif backend == "onnx":
            if probe.get("onnxruntime_version"):
                lines.append(f"<b>ONNX Runtime:</b> {html.escape(str(probe.get('onnxruntime_version')))}")
            providers = [str(name).strip() for name in list(probe.get("available_providers") or []) if str(name).strip()]
            if providers:
                lines.append(f"<b>Providers:</b> {html.escape(', '.join(providers[:4]))}")
        elif backend == "gguf":
            profile_label = str(probe.get("profile_label") or "").strip()
            if profile_label:
                lines.append(f"<b>Profile:</b> {html.escape(profile_label)}")
            quantization = str(probe.get("quantization") or "").strip()
            if quantization:
                lines.append(f"<b>Quantization:</b> {html.escape(quantization)}")
            effective_params = str(probe.get("effective_params_label") or "").strip()
            if effective_params:
                lines.append(f"<b>Model:</b> {html.escape(effective_params)}")
            approx_total_gb = float(probe.get("approx_total_gb") or 0.0)
            if approx_total_gb > 0:
                lines.append(f"<b>Approx Size:</b> {html.escape(f'{approx_total_gb:.2f} GB incl. mmproj')}")
            ctx_size = int(probe.get("ctx_size") or 0)
            if ctx_size > 0:
                lines.append(f"<b>Context:</b> {html.escape(str(ctx_size))} tokens")
            total_vram = float(probe.get("detected_total_vram_gb") or 0.0)
            free_vram = float(probe.get("detected_free_vram_gb") or 0.0)
            if total_vram > 0:
                if free_vram > 0:
                    lines.append(f"<b>VRAM:</b> {html.escape(f'{total_vram:.2f} GB total, {free_vram:.2f} GB free at install/probe time')}")
                else:
                    lines.append(f"<b>VRAM:</b> {html.escape(f'{total_vram:.2f} GB total')}")
        nvidia_smi = dict(probe.get("nvidia_smi") or {})
        smi_gpus = [dict(item or {}) for item in list(nvidia_smi.get("gpus") or [])]
        if smi_gpus:
            first_gpu = smi_gpus[0]
            gpu_name = str(first_gpu.get("name") or "").strip()
            driver_version = str(first_gpu.get("driver_version") or "").strip()
            driver_text = f"{gpu_name} (driver {driver_version})" if gpu_name and driver_version else gpu_name or driver_version
            if driver_text:
                lines.append(f"<b>NVIDIA:</b> {html.escape(driver_text)}")
        reason = str(probe.get("reason") or "").strip()
        if reason:
            lines.append(f"<b>Note:</b> {html.escape(reason)}")
        return "<br>".join(line for line in lines if line)

    @staticmethod
    def _local_ai_probe_requests_gpu(ai_settings) -> bool:
        return str(getattr(ai_settings, "device", "") or "").strip().lower() == "gpu"

    @staticmethod
    def _local_ai_probe_is_gpu_ready(probe: dict) -> bool:
        selected_device = str(probe.get("selected_device") or "").strip().lower()
        active_provider = str(probe.get("active_provider") or "").strip()
        return selected_device.startswith("cuda") or selected_device == "gpu" or active_provider in {"CUDAExecutionProvider", "DmlExecutionProvider"}

    def _local_ai_preload_model(self, spec, python_path: Path, settings_payload: dict, message: str, payload: dict) -> None:
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(python_path, spec.worker_module)
        command = [
            *launcher,
            "--operation",
            "preload",
            "--source",
            str(Path(__file__).resolve()),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        process = subprocess.Popen(
            command,
            cwd=str(worker_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        assert process.stdout is not None
        last_emit = 0.0
        last_line = message
        for line in process.stdout:
            clean = " ".join(str(line or "").split()).strip()
            if clean:
                last_line = clean[-240:]
            if time.monotonic() - last_emit >= 1.0:
                last_emit = time.monotonic()
                payload.update({"state": "installing", "running": True, "message": last_line})
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")

    def _install_gemma_gguf_model(self, spec, payload: dict, emit_install_status) -> None:
        python_path = self._local_ai_runtime_python_path(spec)
        runtime_dir = Path(python_path).parent.parent
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        profile, vram_info = self._choose_gemma_gguf_profile()
        emit_install_status(
            f"Selected {profile.label} for {float(vram_info.get('total_vram_gb') or 0.0):.1f} GB VRAM "
            f"({float(vram_info.get('free_vram_gb') or 0.0):.1f} GB free)."
        )
        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        download_error: list[Exception] = []
        download_done = threading.Event()

        def download_worker() -> None:
            try:
                self._download_gemma_gguf_profile_concurrent(models_dir, profile, emit_install_status, payload)
            except Exception as exc:
                download_error.append(exc)
            finally:
                download_done.set()

        threading.Thread(target=download_worker, daemon=True, name=f"gemma-download-{profile.id}").start()
        bootstrap_python = self._ensure_local_ai_python_bootstrap(emit_install_status)
        if not bootstrap_python:
            raise RuntimeError(
                "MediaLens could not prepare the Python bootstrap needed to create the Gemma runtime. "
                "Check your internet connection, then try again."
            )
        if not python_path.is_file():
            message = f"Creating {spec.install_label} runtime..."
            payload.update({"state": "installing", "running": True, "message": message})
            self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
            returncode, last_line = self._local_ai_run_command_stream(
                [bootstrap_python, "-m", "venv", str(runtime_dir)],
                self._local_ai_worker_source_root(),
                message,
                emit_install_status,
            )
            if returncode != 0:
                raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")
        self.settings.setValue("ai_caption/runtime_python/gemma4", str(python_path))
        self.settings.setValue("ai_caption/gemma_python", str(python_path))
        self._ensure_gemma_llama_cpp_runtime(runtime_dir, emit_install_status)
        emit_install_status("Waiting for model downloads to finish...")
        download_done.wait()
        if download_error:
            raise download_error[0]
        configured = self._configure_gemma_gguf_settings(profile, runtime_dir, models_dir, vram_info)
        message = f"Validating {configured['profile_label']} runtime..."
        payload.update({"state": "installing", "running": True, "message": message})
        self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
        self._local_ai_preload_model(spec, python_path, self._local_ai_default_settings_payload_for_spec(spec), message, payload)

    def _local_ai_gpu_repair_commands(self, spec, python_path: Path) -> list[tuple[list[str], str]]:
        if os.name != "nt":
            return []
        backend = self._local_ai_runtime_backend(spec)
        if backend == "torch":
            return [
                (
                    [
                        str(python_path),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "--force-reinstall",
                        "--no-cache-dir",
                        "--index-url",
                        LOCAL_AI_TORCH_INDEX_URL_CU124,
                        f"torch=={LOCAL_AI_TORCH_VERSION_CU124}",
                        f"torchvision=={LOCAL_AI_TORCHVISION_VERSION_CU124}",
                    ],
                    "Repairing CUDA Torch packages...",
                ),
            ]
        if backend == "onnx":
            return [
                (
                    [
                        str(python_path),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "--force-reinstall",
                        "--no-cache-dir",
                        f"onnxruntime-gpu=={LOCAL_AI_ORT_GPU_VERSION}",
                    ],
                    "Repairing ONNX Runtime GPU package...",
                ),
            ]
        return []

    def _ensure_local_ai_gpu_runtime(self, spec, python_path: Path, emit_install_status) -> dict:
        ai_settings = self._local_ai_caption_settings()
        probe = self._local_ai_probe_runtime(spec, force=True)
        if not self._local_ai_probe_requests_gpu(ai_settings):
            return probe
        if self._local_ai_probe_is_gpu_ready(probe):
            return probe
        for command, message in self._local_ai_gpu_repair_commands(spec, python_path):
            emit_install_status(message)
            returncode, last_line = self._local_ai_run_command_stream(
                command,
                self._local_ai_worker_source_root(),
                message,
                emit_install_status,
            )
            if returncode != 0:
                self._log(
                    f"Local AI GPU repair failed for {spec.install_label} ({self._local_ai_exit_code_text(returncode)}): {last_line}"
                )
                continue
            probe = self._local_ai_probe_runtime(spec, force=True)
            if self._local_ai_probe_is_gpu_ready(probe):
                return probe
        return probe

    @Slot(str, str, result="QVariantMap")
    def get_local_ai_model_status(self, model_id: str, kind: str) -> dict:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            return self._local_ai_status_payload_for_spec(model_spec(str(model_id), str(kind)))
        except Exception as exc:
            return {"state": "error", "installed": False, "running": False, "message": str(exc) or "Could not read model status."}

    @Slot(str, str, result=bool)
    def install_local_ai_model(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return False

        self._local_ai_model_installs.add(spec.settings_key)
        self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))

        def work() -> None:
            payload = self._local_ai_status_payload_for_spec(spec)

            def emit_install_status(message: str) -> None:
                payload.update({"state": "installing", "running": True, "message": str(message or "").strip()})
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))

            try:
                if spec.settings_key == "gemma4" and os.name == "nt":
                    self._install_gemma_gguf_model(spec, payload, emit_install_status)
                    self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
                    probe = self._local_ai_probe_runtime(spec, force=True)
                    payload = self._local_ai_status_payload_for_spec(spec)
                    final_message = f"{spec.install_label} is installed."
                    if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                        final_message = f"{final_message} GPU was requested but this runtime is still using CPU."
                    payload.update({"state": "installed", "installed": True, "running": False, "message": final_message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, payload)
                    return
                requirements_path = self._local_ai_requirements_path(spec)
                if not requirements_path.is_file():
                    raise RuntimeError(f"Install instructions for {spec.install_label} were not found.")
                python_path = self._local_ai_runtime_python_path(spec)
                runtime_dir = Path(python_path).parent.parent
                runtime_dir.parent.mkdir(parents=True, exist_ok=True)
                bootstrap_python = self._ensure_local_ai_python_bootstrap(emit_install_status)
                if not bootstrap_python:
                    raise RuntimeError(
                        "MediaLens could not prepare the Python bootstrap needed to create the model runtime. "
                        "Check your internet connection, then try again."
                    )
                commands = [
                    ([bootstrap_python, "-m", "venv", str(runtime_dir)], f"Creating {spec.install_label} runtime..."),
                    ([str(python_path), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], "Updating package installer..."),
                    ([str(python_path), "-m", "pip", "install", "-r", str(requirements_path)], f"Installing {spec.install_label} support..."),
                ]
                for command, message in commands:
                    payload.update({"state": "installing", "running": True, "message": message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                    returncode, last_line = self._local_ai_run_command_stream(
                        command,
                        self._local_ai_worker_source_root(),
                        message,
                        emit_install_status,
                    )
                    if returncode != 0:
                        raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")
                probe = self._ensure_local_ai_gpu_runtime(spec, python_path, emit_install_status)
                if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                    emit_install_status(
                        self._local_ai_runtime_summary(probe)
                    )
                models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
                if self._local_ai_model_files_installed(models_dir, spec.id):
                    payload.update({"state": "installing", "running": True, "message": f"{spec.install_label} model files are already present."})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                else:
                    message = f"Downloading {spec.install_label} model files..."
                    payload.update({"state": "installing", "running": True, "message": message})
                    self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                    try:
                        self._local_ai_preload_model(spec, python_path, self._local_ai_default_settings_payload_for_spec(spec), message, payload)
                    except Exception as exc:
                        if self._local_ai_model_files_installed(models_dir, spec.id):
                            self._log(f"Local AI model preload failed for {spec.install_label}, but required model files are present: {exc}")
                        else:
                            raise
                self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
                probe = self._local_ai_probe_runtime(spec, force=True)
                payload = self._local_ai_status_payload_for_spec(spec)
                final_message = f"{spec.install_label} is installed."
                if self._local_ai_probe_requests_gpu(self._local_ai_caption_settings()) and not self._local_ai_probe_is_gpu_ready(probe):
                    final_message = f"{final_message} GPU was requested but this runtime is still using CPU."
                payload.update({"state": "installed", "installed": True, "running": False, "message": final_message})
                self.localAiModelInstallStatus.emit(spec.settings_key, payload)
            except Exception as exc:
                payload.update({"state": "error", "installed": False, "running": False, "message": str(exc) or "Model installation failed."})
                self.localAiModelInstallStatus.emit(spec.settings_key, payload)
                self._log(f"Local AI model install failed for {spec.install_label}: {payload['message']}")
            finally:
                self._local_ai_model_installs.discard(spec.settings_key)

        threading.Thread(target=work, daemon=True, name=f"local-ai-install-{spec.settings_key}").start()
        return True

    @Slot(str, str, result=bool)
    def uninstall_local_ai_model(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "This model is currently installing."})
            return False

        try:
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            targets = [self._local_ai_runtime_python_path(spec).parent.parent]
            for target in targets:
                if target.exists():
                    shutil.rmtree(target)
            if spec.settings_key == "gemma4":
                for key in (
                    "ai_caption/runtime_python/gemma4",
                    "ai_caption/gemma_backend",
                    "ai_caption/gemma_profile_id",
                    "ai_caption/gemma_profile_label",
                    "ai_caption/gemma_model_path",
                    "ai_caption/gemma_mmproj_path",
                    "ai_caption/gemma_llama_server",
                    "ai_caption/gemma_ctx_size",
                    "ai_caption/gemma_gpu_layers",
                    "ai_caption/gemma_detected_total_vram_gb",
                    "ai_caption/gemma_detected_free_vram_gb",
                    "ai_caption/gemma_python",
                ):
                    self.settings.remove(key)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": str(exc) or "Uninstall failed."})
            self._log(f"Local AI model uninstall failed for {spec.install_label}: {exc}")
            return False

    @Slot(str, str, result=bool)
    def delete_local_ai_model_files(self, model_id: str, kind: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.model_registry import model_spec

            spec = model_spec(str(model_id), str(kind))
        except Exception as exc:
            self.localAiModelInstallStatus.emit(str(model_id), {"state": "error", "message": str(exc) or "Unknown model."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "This model is currently installing."})
            return False
        try:
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            for target in self._local_ai_model_cache_targets(models_dir, spec):
                if target.exists():
                    shutil.rmtree(target)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": str(exc) or "Delete model files failed."})
            self._log(f"Local AI model file delete failed for {spec.install_label}: {exc}")
            return False

    @Slot(str, result=bool)
    def download_gemma_profile_files(self, profile_id: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id
            from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID, model_spec

            spec = model_spec(GEMMA4_MODEL_ID, "captioner")
            profile = gemma_profile_by_id(str(profile_id or "").strip())
            if profile is None:
                raise RuntimeError("Unknown Gemma profile.")
        except Exception as exc:
            self.localAiModelInstallStatus.emit("gemma4", {"state": "error", "message": str(exc) or "Unknown Gemma profile."})
            return False
        if spec.settings_key in self._local_ai_model_installs:
            self.localAiModelInstallStatus.emit(spec.settings_key, {"state": "error", "message": "Gemma is currently busy."})
            return False

        downloads = getattr(self, "_local_ai_profile_downloads", None)
        if downloads is None:
            downloads = {}
            self._local_ai_profile_downloads = downloads
        cancel_flags = getattr(self, "_local_ai_profile_download_cancel", None)
        if cancel_flags is None:
            cancel_flags = {}
            self._local_ai_profile_download_cancel = cancel_flags
        downloads[spec.settings_key] = profile.id
        cancel_flags[spec.settings_key] = False
        payload = self._local_ai_status_payload_for_spec(spec)
        payload.update(
            {
                "running": True,
                "message": f"Downloading {profile.label}...",
                "gemma_profile_downloading": True,
                "gemma_profile_downloading_id": profile.id,
                "download_messages": {},
                "download_message": "",
            }
        )
        self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))

        def work() -> None:
            try:
                models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
                self._download_gemma_gguf_profile_concurrent(models_dir, profile, None, payload)
                refreshed = self._local_ai_status_payload_for_spec(spec)
                refreshed.update(
                    {
                        "message": f"{profile.label} is downloaded.",
                        "state": refreshed.get("state") or "not_installed",
                        "running": False,
                        "gemma_profile_downloading": False,
                        "gemma_profile_downloading_id": "",
                        "download_messages": {},
                        "download_message": "",
                    }
                )
                self.localAiModelInstallStatus.emit(spec.settings_key, refreshed)
            except Exception as exc:
                payload.update(
                    {
                        "state": "error",
                        "running": False,
                        "message": str(exc) or "Gemma profile download failed.",
                        "gemma_profile_downloading": False,
                        "gemma_profile_downloading_id": "",
                    }
                )
                self.localAiModelInstallStatus.emit(spec.settings_key, dict(payload))
                self._log(f"Gemma profile download failed for {profile.label}: {payload['message']}")
            finally:
                getattr(self, "_local_ai_profile_downloads", {}).pop(spec.settings_key, None)
                getattr(self, "_local_ai_profile_download_cancel", {}).pop(spec.settings_key, None)

        threading.Thread(target=work, daemon=True, name=f"gemma-profile-download-{profile.id}").start()
        return True

    @Slot(result=bool)
    def cancel_gemma_profile_download(self) -> bool:
        downloads = getattr(self, "_local_ai_profile_downloads", {})
        if not downloads.get("gemma4"):
            return False
        cancel_flags = getattr(self, "_local_ai_profile_download_cancel", None)
        if cancel_flags is None:
            cancel_flags = {}
            self._local_ai_profile_download_cancel = cancel_flags
        cancel_flags["gemma4"] = True
        return True

    @Slot(str, result=bool)
    def delete_gemma_profile_files(self, profile_id: str) -> bool:
        try:
            from app.mediamanager.ai_captioning.gemma_gguf import gemma_profile_by_id, gemma_profile_install_dir
            from app.mediamanager.ai_captioning.model_registry import GEMMA4_MODEL_ID, model_spec

            spec = model_spec(GEMMA4_MODEL_ID, "captioner")
            profile = gemma_profile_by_id(str(profile_id or "").strip())
            if profile is None:
                raise RuntimeError("Unknown Gemma profile.")
            models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
            target = gemma_profile_install_dir(models_dir, profile)
            if target.exists():
                shutil.rmtree(target)
            self._local_ai_runtime_status_cache.pop(spec.settings_key, None)
            self.localAiModelInstallStatus.emit(spec.settings_key, self._local_ai_status_payload_for_spec(spec))
            return True
        except Exception as exc:
            self.localAiModelInstallStatus.emit("gemma4", {"state": "error", "message": str(exc) or "Delete Gemma profile failed."})
            self._log(f"Gemma profile delete failed for {profile_id}: {exc}")
            return False

    def _local_ai_caption_settings(self):
        from app.mediamanager.ai_captioning.local_captioning import (
            CAPTION_MODEL_ID,
            DEFAULT_BAD_WORDS,
            DEFAULT_CAPTION_PROMPT,
            DEFAULT_CAPTION_START,
            TAG_MODEL_ID,
            LocalAiSettings,
        )
        from app.mediamanager.ai_captioning.model_registry import model_ids_for_kind

        models_dir = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default()))
        tag_model_id = str(self.settings.value("ai_caption/tag_model_id", TAG_MODEL_ID, type=str) or TAG_MODEL_ID)
        caption_model_id = str(self.settings.value("ai_caption/caption_model_id", CAPTION_MODEL_ID, type=str) or CAPTION_MODEL_ID)
        if tag_model_id not in model_ids_for_kind("tagger"):
            self._log(f"Unsupported local AI tag model '{tag_model_id}' was reset to '{TAG_MODEL_ID}'.")
            tag_model_id = TAG_MODEL_ID
            self.settings.setValue("ai_caption/tag_model_id", TAG_MODEL_ID)
        if caption_model_id not in model_ids_for_kind("captioner"):
            self._log(f"Unsupported local AI description model '{caption_model_id}' was reset to '{CAPTION_MODEL_ID}'.")
            caption_model_id = CAPTION_MODEL_ID
            self.settings.setValue("ai_caption/caption_model_id", CAPTION_MODEL_ID)
        return LocalAiSettings(
            models_dir=models_dir,
            tag_model_id=tag_model_id,
            caption_model_id=caption_model_id,
            tag_min_probability=float(self.settings.value("ai_caption/tag_min_probability", 0.35, type=float) or 0.35),
            tag_max_tags=int(self.settings.value("ai_caption/tag_max_tags", 75, type=int) or 75),
            tags_to_exclude=str(self.settings.value("ai_caption/tags_to_exclude", "", type=str) or ""),
            tag_prompt=str(self.settings.value("ai_caption/tag_prompt", "", type=str) or ""),
            tag_write_mode=str(self.settings.value("ai_caption/tag_write_mode", "union", type=str) or "union"),
            caption_prompt=str(self.settings.value("ai_caption/caption_prompt", DEFAULT_CAPTION_PROMPT, type=str) or DEFAULT_CAPTION_PROMPT),
            caption_start=str(self.settings.value("ai_caption/caption_start", DEFAULT_CAPTION_START, type=str) or DEFAULT_CAPTION_START),
            description_write_mode=str(self.settings.value("ai_caption/description_write_mode", "overwrite", type=str) or "overwrite"),
            device=str(self.settings.value("ai_caption/device", "gpu", type=str) or "gpu"),
            gpu_index=int(self.settings.value("ai_caption/gpu_index", 0, type=int) or 0),
            load_in_4_bit=bool(self.settings.value("ai_caption/load_in_4_bit", False, type=bool)),
            bad_words=str(self.settings.value("ai_caption/bad_words", DEFAULT_BAD_WORDS, type=str) or DEFAULT_BAD_WORDS),
            forced_words=str(self.settings.value("ai_caption/forced_words", "", type=str) or ""),
            min_new_tokens=int(self.settings.value("ai_caption/min_new_tokens", 1, type=int) or 1),
            max_new_tokens=int(self.settings.value("ai_caption/max_new_tokens", 200, type=int) or 200),
            num_beams=int(self.settings.value("ai_caption/num_beams", 1, type=int) or 1),
            length_penalty=float(self.settings.value("ai_caption/length_penalty", 1.0, type=float) or 1.0),
            do_sample=bool(self.settings.value("ai_caption/do_sample", False, type=bool)),
            temperature=float(self.settings.value("ai_caption/temperature", 1.0, type=float) or 1.0),
            top_k=int(self.settings.value("ai_caption/top_k", 50, type=int) or 50),
            top_p=float(self.settings.value("ai_caption/top_p", 1.0, type=float) or 1.0),
            repetition_penalty=float(self.settings.value("ai_caption/repetition_penalty", 1.0, type=float) or 1.0),
            no_repeat_ngram_size=int(self.settings.value("ai_caption/no_repeat_ngram_size", 3, type=int) or 3),
        )

    def _local_ai_service_for_settings(self, ai_settings):
        from app.mediamanager.ai_captioning.local_captioning import LocalAiCaptioningService

        key = json.dumps(
            {
                "models_dir": str(ai_settings.models_dir),
                "tag_model_id": ai_settings.tag_model_id,
                "caption_model_id": ai_settings.caption_model_id,
                "device": ai_settings.device,
                "gpu_index": ai_settings.gpu_index,
                "load_in_4_bit": ai_settings.load_in_4_bit,
            },
            sort_keys=True,
        )
        if self._local_ai_service is None or self._local_ai_service_key != key:
            self._local_ai_service = LocalAiCaptioningService(ai_settings, self._log)
            self._local_ai_service_key = key
        else:
            self._local_ai_service.settings = ai_settings
        return self._local_ai_service

    def _try_start_local_ai(self) -> bool:
        with self._local_ai_lock:
            if self._local_ai_running:
                return False
            self._local_ai_running = True
            self._local_ai_shutting_down = False
            self._local_ai_cancel.clear()
            return True

    def _finish_local_ai(self) -> None:
        with self._local_ai_lock:
            self._local_ai_running = False
            self._local_ai_cancel.clear()

    def _emit_local_ai_signal(self, signal, *args) -> bool:
        if self._local_ai_shutting_down:
            return False
        try:
            signal.emit(*args)
            return True
        except RuntimeError as exc:
            if "already deleted" not in str(exc):
                self._log(f"Local AI signal emit failed: {exc}")
            return False
        except Exception as exc:
            self._log(f"Local AI signal emit failed: {exc}")
            return False

    def _safe_emit(self, signal, *args) -> bool:
        """Emit a Bridge signal from a worker thread, swallowing the race where
        Qt has already deleted the Bridge's C++ half during app shutdown."""
        if self._shutting_down:
            return False
        try:
            signal.emit(*args)
            return True
        except RuntimeError:
            # "Internal C++ object (Bridge) already deleted" â€” Qt tore down
            # before this daemon thread finished. Nothing to do.
            return False
        except Exception:
            return False

    def _emit_local_ai_status(self, message: str) -> None:
        self._emit_local_ai_signal(self.localAiCaptioningStatus, str(message or "").strip())

    def _local_ai_settings_payload(self, ai_settings) -> dict:
        from app.mediamanager.ai_captioning.gemma_gguf import (
            GEMMA_GGUF_BACKEND_ID,
            gemma_profile_by_id,
            gemma_profile_is_installed,
            gemma_profile_mmproj_path,
            gemma_profile_model_path,
        )

        self._sync_selected_gemma_profile_settings(sync_qsettings=False)
        payload = {
            "models_dir": str(ai_settings.models_dir),
            "tag_model_id": str(ai_settings.tag_model_id),
            "caption_model_id": str(ai_settings.caption_model_id),
            "tag_min_probability": float(ai_settings.tag_min_probability),
            "tag_max_tags": int(ai_settings.tag_max_tags),
            "tags_to_exclude": str(ai_settings.tags_to_exclude),
            "tag_prompt": str(ai_settings.tag_prompt),
            "tag_write_mode": str(ai_settings.tag_write_mode),
            "caption_prompt": str(ai_settings.caption_prompt),
            "caption_start": str(ai_settings.caption_start),
            "description_write_mode": str(ai_settings.description_write_mode),
            "device": str(ai_settings.device),
            "gpu_index": int(ai_settings.gpu_index),
            "load_in_4_bit": bool(ai_settings.load_in_4_bit),
            "bad_words": str(ai_settings.bad_words),
            "forced_words": str(ai_settings.forced_words),
            "min_new_tokens": int(ai_settings.min_new_tokens),
            "max_new_tokens": int(ai_settings.max_new_tokens),
            "num_beams": int(ai_settings.num_beams),
            "length_penalty": float(ai_settings.length_penalty),
            "do_sample": bool(ai_settings.do_sample),
            "temperature": float(ai_settings.temperature),
            "top_k": int(ai_settings.top_k),
            "top_p": float(ai_settings.top_p),
            "repetition_penalty": float(ai_settings.repetition_penalty),
            "no_repeat_ngram_size": int(ai_settings.no_repeat_ngram_size),
        }
        for key, default in (
            ("gemma_backend", ""),
            ("gemma_profile_id", ""),
            ("gemma_profile_label", ""),
            ("gemma_model_path", ""),
            ("gemma_mmproj_path", ""),
            ("gemma_llama_server", ""),
            ("gemma_ctx_size", 2048),
            ("gemma_gpu_layers", 999),
        ):
            settings_key = f"ai_caption/{key}"
            if isinstance(default, int):
                payload[key] = int(self.settings.value(settings_key, default, type=int) or default)
            else:
                payload[key] = str(self.settings.value(settings_key, default, type=str) or default)
        backend = str(payload.get("gemma_backend") or "").strip().lower()
        selected_profile = gemma_profile_by_id(str(self.settings.value("ai_caption/gemma_selected_profile_id", "", type=str) or "").strip())
        if backend == GEMMA_GGUF_BACKEND_ID and selected_profile and gemma_profile_is_installed(ai_settings.models_dir, selected_profile):
            payload["gemma_profile_id"] = selected_profile.id
            payload["gemma_profile_label"] = selected_profile.label
            payload["gemma_profile_quantization"] = selected_profile.quantization
            payload["gemma_model_path"] = str(gemma_profile_model_path(ai_settings.models_dir, selected_profile))
            payload["gemma_mmproj_path"] = str(gemma_profile_mmproj_path(ai_settings.models_dir, selected_profile))
        return payload

    def _local_ai_default_settings_payload_for_spec(self, spec) -> dict:
        payload = self._local_ai_settings_payload(self._local_ai_caption_settings())
        if spec.kind == "tagger":
            payload["tag_model_id"] = spec.id
        else:
            payload["caption_model_id"] = spec.id
        return payload

    def _local_ai_worker_command(self, operation: str, ai_settings) -> tuple[str, str]:
        from app.mediamanager.ai_captioning.model_registry import (
            current_python_matches_runtime,
            default_python_for_runtime,
            model_spec,
        )

        kind = "tagger" if operation == "tags" else "captioner"
        selected_model = ai_settings.tag_model_id if operation == "tags" else ai_settings.caption_model_id
        spec = model_spec(selected_model, kind)
        configured = str(self.settings.value(f"ai_caption/runtime_python/{spec.settings_key}", "", type=str) or "").strip()
        if not configured and spec.settings_key == "gemma4":
            configured = str(self.settings.value("ai_caption/gemma_python", "", type=str) or "").strip()
        runtime_root = self._local_ai_runtime_root()
        default_python = default_python_for_runtime(runtime_root, spec)
        python_path = Path(configured) if configured else default_python
        if not python_path.is_file():
            if not bool(getattr(sys, "frozen", False)) and (current_python_matches_runtime(spec) or not configured):
                python_path = Path(sys.executable)
            else:
                raise RuntimeError(
                    f"{spec.install_label} is not installed yet. Install this local AI model before using it."
                )
        return str(python_path), spec.worker_module

    def _run_local_ai_worker_process(self, operation: str, source_path: Path, ai_settings, tags: list[str] | None = None) -> dict:
        timeout_seconds = int(self.settings.value("ai_caption/item_timeout_seconds", 900, type=int) or 900)
        timeout_seconds = max(30, timeout_seconds)
        operation_label = "description" if operation == "description" else "tags"
        python_exe, worker_module = self._local_ai_worker_command(operation, ai_settings)
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(python_exe, worker_module)
        settings_payload = self._local_ai_settings_payload(ai_settings)
        command = [
            *launcher,
            "--operation",
            operation,
            "--source",
            str(source_path),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        if tags is not None:
            command.extend(["--tags-json", json.dumps(tags, ensure_ascii=False)])
        if str(settings_payload.get("gemma_backend") or "").strip().lower() == "llama_cpp_gguf":
            self._log(
                "Local AI Gemma launch: "
                f"profile={str(settings_payload.get('gemma_profile_id') or '').strip()} "
                f"quant={str(settings_payload.get('gemma_profile_quantization') or '').strip()} "
                f"model={Path(str(settings_payload.get('gemma_model_path') or '')).name} "
                f"mmproj={Path(str(settings_payload.get('gemma_mmproj_path') or '')).name} "
                f"ctx={int(settings_payload.get('gemma_ctx_size') or 0)} "
                f"ngl={int(settings_payload.get('gemma_gpu_layers') or 0)} "
                f"source={source_path.name}"
            )
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        popen_kwargs = dict(
            cwd=str(worker_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
        if _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS:
            popen_kwargs.update(_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS)
        process = subprocess.Popen(command, **popen_kwargs)
        with self._local_ai_lock:
            self._local_ai_processes.add(process)
        started = time.monotonic()
        last_status = 0.0
        try:
            while process.poll() is None:
                if self._local_ai_cancel.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
                        try:
                            process.wait(timeout=5)
                        except Exception:
                            pass
                    raise RuntimeError("Local AI scan was canceled.")
                elapsed = time.monotonic() - started
                if elapsed - last_status >= 5.0:
                    last_status = elapsed
                    self._emit_local_ai_status(
                        f"Generating {operation_label}: still working ({int(elapsed)}s elapsed, timeout {timeout_seconds}s)"
                    )
                if time.monotonic() - started > timeout_seconds:
                    process.kill()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        pass
                    raise TimeoutError(f"Local AI timed out after {timeout_seconds} seconds on {source_path.name}.")
                time.sleep(0.25)
            stdout, stderr = process.communicate(timeout=5)
        finally:
            with self._local_ai_lock:
                self._local_ai_processes.discard(process)
        if stderr.strip():
            self._log(f"Local AI worker stderr for {source_path}: {stderr.strip()[-2000:]}")
        payload = None
        for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            raise RuntimeError(self._local_ai_worker_failure_message(process.returncode, stdout, stderr))
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or "Local AI worker failed."))
        return payload

    @staticmethod
    def _local_ai_exit_code_text(returncode: int | None) -> str:
        if returncode is None:
            return "no exit code"
        if os.name == "nt":
            return f"exit code {returncode} / 0x{returncode & 0xFFFFFFFF:08X}"
        return f"exit code {returncode}"

    @staticmethod
    def _local_ai_worker_failure_message(returncode: int | None, stdout: str, stderr: str) -> str:
        combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
        lines = []
        for raw_line in combined.replace("\r", "\n").splitlines():
            line = " ".join(str(raw_line or "").split()).strip()
            if not line:
                continue
            lowered = line.lower()
            if "loading weights:" in lowered or "it/s]" in lowered:
                continue
            if "you are using a model of type" in lowered:
                continue
            if "set max length" in lowered:
                continue
            if line.startswith("{") and line.endswith("}"):
                continue
            lines.append(line)
        if lines:
            return lines[-1][-500:]
        if returncode:
            return f"Local AI worker exited without a result ({Bridge._local_ai_exit_code_text(returncode)})."
        return "Local AI worker exited without a result."

    def cancel_local_ai_captioning(self) -> None:
        self._local_ai_shutting_down = True
        self._local_ai_cancel.set()
        with self._local_ai_lock:
            processes = list(self._local_ai_processes)
        for process in processes:
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

    @Slot(result=list)
    def list_local_ai_models(self) -> list:
        from app.mediamanager.ai_captioning.model_registry import available_models

        return available_models()

    @Slot(list, result=bool)
    def run_local_ai_tags_descriptions(self, paths: list) -> bool:
        return self.run_local_ai_tags(paths)

    @Slot(list, result=bool)
    def run_local_ai_tags(self, paths: list) -> bool:
        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if not clean_paths or not self._try_start_local_ai():
            return False

        def work() -> None:
            from app.mediamanager.ai_captioning.local_captioning import apply_tags_to_database

            completed = 0
            error = ""
            item_errors: list[str] = []
            self._emit_local_ai_signal(self.localAiCaptioningStarted, len(clean_paths))
            try:
                ai_settings = self._local_ai_caption_settings()
                ai_settings.models_dir.mkdir(parents=True, exist_ok=True)
                for index, raw_path in enumerate(clean_paths, start=1):
                    if self._local_ai_cancel.is_set():
                        error = "Local AI scan was canceled."
                        break
                    self._emit_local_ai_signal(self.localAiCaptioningProgress, raw_path, index, len(clean_paths))
                    try:
                        media = self._ensure_media_record_for_tag_write(raw_path)
                        if not media:
                            raise FileNotFoundError("Selected media record could not be created.")
                        source_path = self._local_ai_source_path(Path(raw_path))
                        result = self._run_local_ai_worker_process("tags", source_path, ai_settings)
                        tags = [str(tag) for tag in (result.get("tags") or []) if str(tag).strip()]
                        if not tags:
                            raise RuntimeError("Local AI generated no tags.")
                        apply_tags_to_database(self.conn, raw_path, tags, ai_settings)
                        completed += 1
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, tags, "", "")
                    except Exception as item_exc:
                        item_error = str(item_exc) or "Local AI captioning failed."
                        item_errors.append(f"{Path(raw_path).name}: {item_error}")
                        self._log(f"Local AI tag generation failed for {raw_path}: {item_error}")
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], "", item_error)
                self._emit_local_ai_signal(self.galleryScopeChanged)
                if item_errors and completed <= 0:
                    error = item_errors[0]
            except Exception as exc:
                error = str(exc) or "Local AI tag generation failed."
                self._log(f"Local AI tag generation failed: {error}")
            finally:
                self._finish_local_ai()
                self._emit_local_ai_signal(self.localAiCaptioningFinished, completed, error)

        threading.Thread(target=work, daemon=True, name="local-ai-captioning").start()
        return True

    @Slot(list, result=bool)
    def run_local_ai_descriptions(self, paths: list) -> bool:
        clean_paths = [str(path or "").strip() for path in (paths or []) if str(path or "").strip()]
        if not clean_paths or not self._try_start_local_ai():
            return False

        def work() -> None:
            from app.mediamanager.ai_captioning.local_captioning import apply_description_to_database
            from app.mediamanager.db.tags_repo import list_media_tags

            completed = 0
            error = ""
            item_errors: list[str] = []
            self._emit_local_ai_signal(self.localAiCaptioningStarted, len(clean_paths))
            try:
                ai_settings = self._local_ai_caption_settings()
                ai_settings.models_dir.mkdir(parents=True, exist_ok=True)
                for index, raw_path in enumerate(clean_paths, start=1):
                    if self._local_ai_cancel.is_set():
                        error = "Local AI scan was canceled."
                        break
                    self._emit_local_ai_signal(self.localAiCaptioningProgress, raw_path, index, len(clean_paths))
                    try:
                        media = self._ensure_media_record_for_tag_write(raw_path)
                        if not media:
                            raise FileNotFoundError("Selected media record could not be created.")
                        source_path = self._local_ai_source_path(Path(raw_path))
                        tags = list_media_tags(self.conn, int(media["id"]))
                        result = self._run_local_ai_worker_process("description", source_path, ai_settings, tags)
                        description = str(result.get("description") or "").strip()
                        if not str(description or "").strip():
                            raise RuntimeError("Local AI generated no description.")
                        apply_description_to_database(self.conn, raw_path, description, ai_settings)
                        completed += 1
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], description, "")
                    except Exception as item_exc:
                        item_error = str(item_exc) or "Local AI description generation failed."
                        item_errors.append(f"{Path(raw_path).name}: {item_error}")
                        self._log(f"Local AI description generation failed for {raw_path}: {item_error}")
                        self._emit_local_ai_signal(self.localAiCaptioningItemFinished, raw_path, [], "", item_error)
                self._emit_local_ai_signal(self.galleryScopeChanged)
                if item_errors and completed <= 0:
                    error = item_errors[0]
            except Exception as exc:
                error = str(exc) or "Local AI description generation failed."
                self._log(f"Local AI description generation failed: {error}")
            finally:
                self._finish_local_ai()
                self._emit_local_ai_signal(self.localAiCaptioningFinished, completed, error)

        threading.Thread(target=work, daemon=True, name="local-ai-description").start()
        return True



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
