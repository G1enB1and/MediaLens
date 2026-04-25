from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeVideoMetadataMixin:
    @Slot(str, result=float)
    def get_video_duration_seconds(self, video_path: str) -> float:
        try:
            ffprobe = self._ffprobe_bin()
            if not ffprobe:
                self._log(f"Video duration unavailable; ffprobe not found for {video_path}")
                return 0.0
            runtime_path = self._video_runtime_path(video_path)
            cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", runtime_path]
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, check=True, timeout=5)
            return float((r.stdout or "").strip() or 0.0)
        except Exception as exc:
            self._log(f"Video duration probe failed for {video_path}: {type(exc).__name__}: {exc}")
            return 0.0

    def _probe_video_size(self, video_path: str) -> tuple[int, int, bool]:
        ffprobe = self._ffprobe_bin()
        if not ffprobe:
            self._log(f"Video size probe unavailable; ffprobe not found for {video_path}")
            return (0, 0, False)
        runtime_path = self._video_runtime_path(video_path)
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", runtime_path]
        try:
            import json
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "").strip().replace("\r", " ").replace("\n", " ")
                self._log(f"Video size probe failed for {video_path}: exit={r.returncode} {err[:500]}")
                return (0, 0, False)
            data = json.loads(r.stdout)
            streams = data.get("streams", [])
            if not streams: return (0, 0, False)
            for s in streams:
                if s.get("codec_type") == "video":
                    w_raw, h_raw = int(s.get("width", 0)), int(s.get("height", 0))
                    sar = s.get("sample_aspect_ratio", "1:1")
                    parsed_sar = 1.0
                    if sar and ":" in sar and sar != "1:1":
                        try: num, den = sar.split(":", 1); parsed_sar = float(num) / float(den)
                        except Exception: pass
                    w, h = max(2, int(w_raw * parsed_sar)), max(2, h_raw)
                    
                    cw_rot = 0
                    tags = s.get("tags", {})
                    if "rotate" in tags:
                        cw_rot = int(tags["rotate"]) % 360
                    for sd in s.get("side_data_list", []):
                        if "rotation" in sd:
                            cw_rot = int(abs(float(sd["rotation"]))) % 360
                    
                    if cw_rot in (90, 270): 
                        w, h = h, w
                        
                    return (w, h, (w % 2 != 0 or h % 2 != 0))
            return (0, 0, False)
        except Exception as exc:
            self._log(f"Video size probe error for {video_path}: {type(exc).__name__}: {exc}")
            return (0, 0, False)

    @Slot(str, bool, bool, bool, int, int, result=bool)
    def open_native_video(self, video_path: str, autoplay: bool, loop: bool, muted: bool, w: int = 0, h: int = 0) -> bool:
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video for non-file path: {video_path}")
                return False
            runtime_path = self._video_runtime_path(video_path)
            if w <= 0 or h <= 0:
                w, h, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (w % 2 != 0 or h % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, w, h)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoRequested.emit(str(fixed), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoRequested.emit(runtime_path, bool(autoplay), bool(loop), bool(muted), int(w), int(h))
            return True
        except Exception:
            return False

    @Slot(str, int, int, int, int, bool, bool, bool, int, int)
    def open_native_video_inplace(self, video_path: str, x: int, y: int, w: int, h: int, autoplay: bool, loop: bool, muted: bool, vw: int = 0, vh: int = 0) -> None:
        if not loop:
            d_s = self.get_video_duration_seconds(video_path)
            if self._should_loop_video(int(float(d_s or 0) * 1000)):
                loop = True
        try:
            path_obj = Path(video_path)
            if not path_obj.exists() or not path_obj.is_file():
                self._log(f"Rejected open_native_video_inplace for non-file path: {video_path}")
                return
            runtime_path = self._video_runtime_path(video_path)

            if vw <= 0 or vh <= 0:
                vw, vh, is_malformed = self._probe_video_size(video_path)
            else:
                is_malformed = (vw % 2 != 0 or vh % 2 != 0)

            if is_malformed:
                self.videoPreprocessingStatus.emit("Preparing video...")
                def work():
                    try:
                        fixed = self._preprocess_to_even_dims(video_path, vw, vh)
                        if fixed:
                            pw, ph, _ = self._probe_video_size(fixed)
                            self.videoPreprocessingStatus.emit("")
                            self.openVideoInPlaceRequested.emit(str(fixed), int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(pw), int(ph))
                        else:
                            self.videoPreprocessingStatus.emit("Error preparing video.")
                    except Exception:
                        self.videoPreprocessingStatus.emit("Error preparing video.")
                threading.Thread(target=work, daemon=True).start()
            else:
                self.openVideoInPlaceRequested.emit(runtime_path, int(x), int(y), int(w), int(h), bool(autoplay), bool(loop), bool(muted), int(vw), int(vh))
        except Exception:
            pass

    @Slot(str, int, int)
    def preload_video(self, video_path: str, w: int = 0, h: int = 0) -> None:
        """Proactively prepare a video for playback in the background."""
        def work():
            try:
                # 1. Probe if dimensions unknown
                nonlocal w, h
                if w <= 0 or h <= 0:
                    w, h, is_malformed = self._probe_video_size(video_path)
                else:
                    is_malformed = (w % 2 != 0 or h % 2 != 0)
                
                # 2. Trigger "safety gate" preprocessing ahead of time if malformed
                if is_malformed:
                    self._preprocess_to_even_dims(video_path, w, h)
                    
                # 3. Future: Warm up QMediaPlayer instance if needed
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    @Slot(int, int, int, int)
    def update_native_video_rect(self, x, y, w, h):
        self.updateVideoRectRequested.emit(x, y, w, h)

    @Slot(bool)
    def set_video_muted(self, muted: bool) -> None:
        self.videoMutedChanged.emit(muted)

    @Slot(bool)
    def set_video_paused(self, paused: bool) -> None:
        self.videoPausedChanged.emit(paused)

    def _preprocess_to_even_dims(self, video_path: str, w: int, h: int) -> str | None:
        import tempfile
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            self._log(f"Video preprocessing unavailable; ffmpeg not found for {video_path}")
            return None
        runtime_path = self._video_runtime_path(video_path)
        ew, eh = (w if w % 2 == 0 else w - 1), (h if h % 2 == 0 else h - 1)
        if ew <= 0 or eh <= 0: return None
        tmp = tempfile.NamedTemporaryFile(prefix="mmx_fixed_", suffix=".mkv", delete=False)
        tmp.close()
        out_path = tmp.name
        vf = f"scale={ew}:{eh},setsar=1,format=yuv420p"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "warning", "-i", runtime_path, "-vf", vf, "-c:v", "mjpeg", "-q:v", "3", "-c:a", "copy", out_path]
        try:
            result = _run_hidden_subprocess(cmd, capture_output=True, timeout=60)
            if result.returncode == 0:
                self._log(f"Video preprocessing succeeded for {video_path}: {out_path}")
                return out_path
            err_bytes = result.stderr or result.stdout or b""
            err = err_bytes.decode("utf-8", errors="replace") if isinstance(err_bytes, bytes) else str(err_bytes)
            self._log(f"Video preprocessing failed for {video_path}: exit={result.returncode} {err.strip()[:500]}")
        except Exception as exc:
            self._log(f"Video preprocessing error for {video_path}: {type(exc).__name__}: {exc}")
        return None

    @Slot(result=bool)
    def close_native_video(self) -> bool:
        try:
            self.closeVideoRequested.emit()
            return True
        except Exception:
            return False

    @Slot(str, list, str, result=bool)
    def dismiss_review_pair(self, path: str, related_paths: list, review_mode: str) -> bool:
        from app.mediamanager.db.media_repo import add_review_pair_exclusions

        try:
            return add_review_pair_exclusions(self.conn, path, related_paths or [], review_mode) > 0
        except Exception as exc:
            try:
                self._log(f"Dismiss review pair failed for {path!r}: {exc}")
            except Exception:
                pass
            return False

    @Slot(result=bool)
    def reset_review_group_exclusions(self) -> bool:
        from app.mediamanager.db.media_repo import clear_review_pair_exclusions

        try:
            clear_review_pair_exclusions(self.conn)
            return True
        except Exception as exc:
            try:
                self._log(f"Reset review group exclusions failed: {exc}")
            except Exception:
                pass
            return False

    @Slot(str, result=dict)
    def get_media_metadata(self, path: str) -> dict:
        return _load_media_metadata_payload(self.conn, path, self._log)

    @Slot(str, str, str, str, str, str, str, str, str)
    def update_media_metadata(self, path, title, desc, notes, etags="", ecomm="", aip="", ainp="", aiparam="") -> None:
        from app.mediamanager.db.media_repo import get_media_by_path
        from app.mediamanager.db.metadata_repo import upsert_media_metadata
        try:
            m = get_media_by_path(self.conn, path)
            if m: upsert_media_metadata(self.conn, m["id"], title, desc, notes, etags, ecomm, aip, ainp, aiparam)
        except Exception: pass

    @Slot(str, str, str)
    def update_media_dates(self, path: str, exif_date_taken: str, metadata_date: str) -> None:
        from app.mediamanager.db.media_repo import get_media_by_path, update_media_dates
        try:
            m = get_media_by_path(self.conn, path)
            if m:
                update_media_dates(
                    self.conn,
                    m["id"],
                    exif_date_taken=exif_date_taken.strip() or None,
                    metadata_date=metadata_date.strip() or None,
                )
        except Exception:
            pass

    @Slot(str, bool)
    def update_media_text_override(self, path: str, text_present_override: bool) -> None:
        from app.mediamanager.db.media_repo import update_user_confirmed_text_detected
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                update_user_confirmed_text_detected(self.conn, m["id"], bool(text_present_override))
                if self._current_gallery_filter_uses_text():
                    self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
        except Exception:
            pass

    @Slot(str, str)
    def update_media_detected_text(self, path: str, detected_text: str) -> None:
        from app.mediamanager.db.media_repo import update_media_detected_text
        try:
            m = self._ensure_media_record_for_tag_write(path)
            if m:
                update_media_detected_text(self.conn, m["id"], detected_text)
                self.galleryScopeChanged.emit()
        except Exception:
            pass

    def _manual_ocr_source_path(self, media_path: Path) -> Path:
        if media_path.suffix.lower() not in VIDEO_EXTS:
            return media_path
        poster = self._video_poster_path(media_path)
        if poster.exists():
            return poster
        poster = self._ensure_video_poster(media_path)
        if poster and poster.exists():
            return poster
        raise RuntimeError("No video preview image is available for OCR.")

    def _ocr_runtime_python_path(self) -> Path:
        configured = str(self.settings.value("ocr/paddle_python", "", type=str) or "").strip()
        if configured:
            return Path(configured)
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        exe_name = "python.exe" if os.name == "nt" else "python"
        default_path = self._local_ai_runtime_root() / ".venv-paddleocr" / scripts_dir / exe_name
        candidates = [
            default_path,
            self._local_ai_worker_source_root() / ".venv-paddleocr" / scripts_dir / exe_name,
            Path.cwd() / ".venv-paddleocr" / scripts_dir / exe_name,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return default_path

    @Slot(result="QVariantMap")
    def get_paddle_ocr_status(self) -> dict:
        try:
            python_path = self._ocr_runtime_python_path()
            device = str(self.settings.value("ocr/paddle_device", "auto", type=str) or "auto")
            prefer_gpu = bool(self.settings.value("ocr/paddle_prefer_gpu", True, type=bool))
            gpu_target = self._paddle_ocr_gpu_install_target()
            probe: dict = {}
            if python_path.is_file():
                code = (
                    "import json\n"
                    "import traceback\n"
                    "from importlib import metadata\n"
                    "payload={'ok': True}\n"
                    "try:\n"
                    " import paddle\n"
                    " import paddleocr\n"
                    " payload['paddle_version']=str(getattr(paddle, '__version__', ''))\n"
                    " payload['paddleocr_version']=str(getattr(paddleocr, '__version__', ''))\n"
                    " payload['paddle_path']=str(getattr(paddle, '__file__', ''))\n"
                    " payload['paddlepaddle_dist']=metadata.version('paddlepaddle') if any(d.metadata.get('Name','').lower() == 'paddlepaddle' for d in metadata.distributions()) else ''\n"
                    " payload['paddlepaddle_gpu_dist']=metadata.version('paddlepaddle-gpu') if any(d.metadata.get('Name','').lower() == 'paddlepaddle-gpu' for d in metadata.distributions()) else ''\n"
                    " payload['compiled_with_cuda']=bool(paddle.device.is_compiled_with_cuda())\n"
                    " if payload['compiled_with_cuda']:\n"
                    "  try:\n"
                    "   paddle.set_device('gpu')\n"
                    "  except Exception as device_exc:\n"
                    "   payload['gpu_error']=str(device_exc)\n"
                    " payload['current_device']=str(paddle.get_device())\n"
                    "except Exception as exc:\n"
                    " payload={'ok': False, 'error': str(exc), 'traceback': traceback.format_exc()[-1600:]}\n"
                    "print(json.dumps(payload), flush=True)\n"
                )
                try:
                    cache_root = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default())) / "paddleocr_cache"
                    home_dir = cache_root / "home"
                    temp_dir = cache_root / "tmp"
                    child_env = self._local_ai_subprocess_env(str(self._local_ai_worker_source_root()))
                    for directory in (cache_root, home_dir, temp_dir, cache_root / "paddle", cache_root / "ppocr", cache_root / "xdg", cache_root / "hf_home"):
                        try:
                            directory.mkdir(parents=True, exist_ok=True)
                        except Exception:
                            pass
                    child_env["PADDLE_PDX_CACHE_HOME"] = str(cache_root / "paddlex")
                    child_env["PADDLE_HOME"] = str(cache_root / "paddle")
                    child_env["PPOCR_HOME"] = str(cache_root / "ppocr")
                    child_env["XDG_CACHE_HOME"] = str(cache_root / "xdg")
                    child_env["HF_HOME"] = str(cache_root / "hf_home")
                    child_env["HOME"] = str(home_dir)
                    child_env["USERPROFILE"] = str(home_dir)
                    child_env["TEMP"] = str(temp_dir)
                    child_env["TMP"] = str(temp_dir)
                    completed = _run_hidden_subprocess(
                        [str(python_path), "-c", code],
                        capture_output=True,
                        text=True,
                        timeout=12,
                        env=child_env,
                    )
                    if completed.returncode == 0:
                        probe = json.loads((completed.stdout or "{}").strip() or "{}")
                    else:
                        probe = {"ok": False, "error": (completed.stderr or completed.stdout or "").strip()[-500:]}
                except Exception as exc:
                    probe = {"ok": False, "error": str(exc)}
            current_device = str(probe.get("current_device") or "").strip().lower()
            gpu_active = current_device.startswith("gpu") or current_device.startswith("cuda")
            installed = bool(python_path.is_file() and probe.get("ok") and not probe.get("error"))
            gpu_issue = ""
            if installed and prefer_gpu and bool(gpu_target.get("available")) and not gpu_active:
                if probe.get("gpu_error"):
                    gpu_issue = str(probe.get("gpu_error") or "").strip()
                elif probe.get("paddlepaddle_dist") and not probe.get("paddlepaddle_gpu_dist"):
                    gpu_issue = "CPU Paddle package is installed even though an NVIDIA GPU was detected."
                elif probe.get("compiled_with_cuda"):
                    gpu_issue = f"Paddle reports CUDA support, but the active device is {current_device or 'cpu'}."
                else:
                    gpu_issue = "Installed Paddle runtime is not CUDA-enabled."
            payload = {
                "installed": installed,
                "python_path": str(python_path),
                "device": device,
                "prefer_gpu": prefer_gpu,
                "runtime_probe": probe,
                "gpu_active": gpu_active,
                "gpu_available": bool(probe.get("compiled_with_cuda")),
                "gpu_detected": bool(gpu_target.get("available")),
                "gpu_target": gpu_target,
                "gpu_issue": gpu_issue,
                "current_device": current_device,
                "fast_enabled": True,
                "accurate_enabled": False,
            }
            if python_path.is_file() and not installed:
                detail = str(probe.get("error") or probe.get("gpu_error") or probe.get("traceback") or "").strip()
                if detail:
                    payload["error"] = detail
            return payload
        except Exception as exc:
            return {"installed": False, "error": str(exc) or "Could not read Paddle OCR status."}

    @Slot(result=bool)
    def uninstall_paddle_ocr_runtime(self) -> bool:
        if bool(getattr(self, "_paddle_ocr_runtime_installing", False)):
            self.paddleOcrRuntimeInstallStatus.emit({"state": "error", "message": "Paddle OCR runtime is currently installing."})
            return False
        try:
            runtime_dir = self._ocr_runtime_python_path().parent.parent
            if runtime_dir.exists():
                shutil.rmtree(runtime_dir)
            self.settings.remove("ocr/paddle_python")
            self.settings.sync()
            payload = self.get_paddle_ocr_status()
            payload.update({"state": "not_installed", "running": False, "message": "Paddle OCR runtime was uninstalled."})
            self.paddleOcrRuntimeInstallStatus.emit(payload)
            return True
        except Exception as exc:
            self.paddleOcrRuntimeInstallStatus.emit({"state": "error", "running": False, "message": str(exc) or "Paddle OCR runtime uninstall failed."})
            return False

    @Slot(result=bool)
    def delete_paddle_ocr_cache(self) -> bool:
        try:
            cache_root = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default())) / "paddleocr_cache"
            if cache_root.exists():
                shutil.rmtree(cache_root)
            payload = self.get_paddle_ocr_status()
            payload.update({"state": "installed" if payload.get("installed") else "not_installed", "running": False, "message": "Paddle OCR cache was deleted."})
            self.paddleOcrRuntimeInstallStatus.emit(payload)
            return True
        except Exception as exc:
            self.paddleOcrRuntimeInstallStatus.emit({"state": "error", "running": False, "message": str(exc) or "Paddle OCR cache delete failed."})
            return False

    def _ocr_worker_launcher(self, python_path: str | Path) -> tuple[list[str], Path, str]:
        source_root = self._local_ai_worker_source_root()
        worker_script = source_root / "app" / "mediamanager" / "ocr" / "paddle_worker.py"
        if worker_script.is_file():
            return [str(python_path), str(worker_script)], self._local_ai_runtime_root(), str(source_root)
        return [str(python_path), "-m", "app.mediamanager.ocr.paddle_worker"], source_root, str(source_root)

    @staticmethod
    def _parse_driver_version(value: str) -> tuple[int, int, int]:
        parts = [int(part) for part in re.findall(r"\d+", str(value or ""))[:3]]
        while len(parts) < 3:
            parts.append(0)
        return int(parts[0]), int(parts[1]), int(parts[2])

    @staticmethod
    def _driver_at_least(current: tuple[int, int, int], minimum: tuple[int, int, int]) -> bool:
        return tuple(current) >= tuple(minimum)

    def _nvidia_smi_candidates(self) -> list[str]:
        candidates: list[str] = []
        for value in (
            shutil.which("nvidia-smi"),
            str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "nvidia-smi.exe") if os.name == "nt" else "",
            str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Sysnative" / "nvidia-smi.exe") if os.name == "nt" else "",
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe" if os.name == "nt" else "",
            "nvidia-smi",
        ):
            text = str(value or "").strip()
            if not text or text in candidates:
                continue
            candidates.append(text)
        return candidates

    def _paddle_ocr_gpu_install_target(self) -> dict:
        errors: list[str] = []
        for executable in self._nvidia_smi_candidates():
            try:
                completed = _run_hidden_subprocess(
                    [executable, "--query-gpu=driver_version", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    env=self._local_ai_subprocess_env(""),
                )
            except Exception as exc:
                errors.append(f"{executable}: {exc}")
                continue
            output = str(completed.stdout or "").strip()
            detail = str(completed.stderr or output or "").strip()
            if completed.returncode != 0 or not output:
                errors.append(f"{executable}: {detail or self._local_ai_exit_code_text(completed.returncode)}")
                continue
            driver_text = output.splitlines()[0].strip()
            driver = self._parse_driver_version(driver_text)
            if self._driver_at_least(driver, (550, 54, 14)):
                return {
                    "available": True,
                    "driver": driver_text,
                    "package": "paddlepaddle-gpu==3.2.0",
                    "index_url": "https://www.paddlepaddle.org.cn/packages/stable/cu126/",
                    "label": "CUDA 12.6",
                }
            if self._driver_at_least(driver, (452, 39, 0)):
                return {
                    "available": True,
                    "driver": driver_text,
                    "package": "paddlepaddle-gpu==3.2.0",
                    "index_url": "https://www.paddlepaddle.org.cn/packages/stable/cu118/",
                    "label": "CUDA 11.8",
                }
            return {"available": False, "driver": driver_text, "reason": f"NVIDIA driver {driver_text} is too old for Paddle GPU wheels."}
        return {"available": False, "reason": f"NVIDIA GPU was not detected. Tried: {'; '.join(errors[-4:]) if errors else 'nvidia-smi not found'}"}

    def _paddle_ocr_runtime_env(self) -> dict[str, str]:
        cache_root = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default())) / "paddleocr_cache"
        home_dir = cache_root / "home"
        temp_dir = cache_root / "tmp"
        child_env = self._local_ai_subprocess_env(str(self._local_ai_worker_source_root()))
        for directory in (cache_root, home_dir, temp_dir, cache_root / "paddle", cache_root / "ppocr", cache_root / "xdg", cache_root / "hf_home", cache_root / "paddlex"):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        child_env["PADDLE_PDX_CACHE_HOME"] = str(cache_root / "paddlex")
        child_env["PADDLE_HOME"] = str(cache_root / "paddle")
        child_env["PPOCR_HOME"] = str(cache_root / "ppocr")
        child_env["XDG_CACHE_HOME"] = str(cache_root / "xdg")
        child_env["HF_HOME"] = str(cache_root / "hf_home")
        child_env["HOME"] = str(home_dir)
        child_env["USERPROFILE"] = str(home_dir)
        child_env["TEMP"] = str(temp_dir)
        child_env["TMP"] = str(temp_dir)
        return child_env

    def _paddle_ocr_run_command(self, command: list[str], message: str, emit_status, *, runtime_env: bool = False) -> None:
        emit_status(message)
        returncode, last_line = self._local_ai_run_command_stream(
            command,
            self._local_ai_worker_source_root(),
            message,
            emit_status,
            env=self._paddle_ocr_runtime_env() if runtime_env else None,
        )
        if returncode != 0:
            raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")

    def _ensure_paddle_ocr_packaging_tools(self, python_path: Path, emit_status) -> None:
        try:
            self._paddle_ocr_run_command([str(python_path), "-m", "pip", "--version"], "Checking Paddle OCR package installer...", emit_status)
        except Exception:
            self._paddle_ocr_run_command([str(python_path), "-m", "ensurepip", "--upgrade"], "Repairing Paddle OCR package installer...", emit_status)
        self._paddle_ocr_run_command([str(python_path), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "setuptools", "wheel"], "Installing Paddle OCR packaging tools...", emit_status)

    @Slot(result=bool)
    def install_paddle_ocr_runtime(self) -> bool:
        if bool(getattr(self, "_paddle_ocr_runtime_installing", False)):
            self.paddleOcrRuntimeInstallStatus.emit({"state": "installing", "message": "Paddle OCR runtime is already installing."})
            return False
        self._paddle_ocr_runtime_installing = True

        def work() -> None:
            def emit_status(message: str, **extra) -> None:
                payload = {"state": "installing", "running": True, "message": str(message or "").strip()}
                payload.update(extra)
                self.paddleOcrRuntimeInstallStatus.emit(payload)

            try:
                python_path = self._ocr_runtime_python_path()
                runtime_dir = Path(python_path).parent.parent
                runtime_dir.parent.mkdir(parents=True, exist_ok=True)
                bootstrap_python = self._ensure_local_ai_python_bootstrap(lambda msg: emit_status(msg))
                if not bootstrap_python:
                    raise RuntimeError("MediaLens could not prepare the Python bootstrap needed to create the OCR runtime.")
                if not python_path.is_file():
                    self._paddle_ocr_run_command([bootstrap_python, "-m", "venv", str(runtime_dir)], "Creating Paddle OCR runtime...", emit_status)
                self._ensure_paddle_ocr_packaging_tools(python_path, emit_status)
                self._paddle_ocr_run_command([str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"], "Removing existing Paddle package...", emit_status)

                requirements_path = self._local_ai_requirements_path(type("Spec", (), {"requirements_file": "requirements-local-ocr-paddle.txt"})())
                self._paddle_ocr_run_command([str(python_path), "-m", "pip", "install", "-r", str(requirements_path)], "Installing PaddleOCR support...", emit_status)
                self._paddle_ocr_run_command([str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"], "Removing Paddle package selected by dependency resolver...", emit_status)

                def clean_install_error(value: object) -> str:
                    text = " ".join(str(value or "").split()).strip()
                    text = re.sub(r"<pip\._vendor\.urllib3\.connection\.HTTPSConnection object at 0x[0-9a-fA-F]+>", "pip HTTPS connection", text)
                    return text[-700:]

                def install_paddle_package(package_base: str, index_urls: list[str], message_prefix: str) -> str:
                    versions = ("3.2.2", "3.2.1", "3.2.0")
                    errors: list[str] = []
                    for version in versions:
                        package = f"{package_base}=={version}"
                        for index_url in index_urls:
                            source_label = "PyPI" if not index_url else str(index_url).rstrip("/")
                            command = [str(python_path), "-m", "pip", "install", package]
                            if index_url:
                                command.extend(["-i", index_url])
                            try:
                                self._paddle_ocr_run_command(
                                    command,
                                    f"{message_prefix} ({version}, {source_label})...",
                                    emit_status,
                                )
                                return package
                            except Exception as exc:
                                cleaned = clean_install_error(exc)
                                errors.append(cleaned)
                                self._log(f"{message_prefix} {version} from {source_label} failed: {cleaned}")
                    raise RuntimeError(errors[-1] if errors else f"{message_prefix} failed.")

                gpu_target = self._paddle_ocr_gpu_install_target()
                gpu_error = ""
                installed_package = ""
                if bool(gpu_target.get("available")):
                    try:
                        installed_package = install_paddle_package(
                            "paddlepaddle-gpu",
                            [str(gpu_target["index_url"])],
                            f"Installing Paddle GPU runtime ({gpu_target.get('label')})",
                        )
                        status = self.get_paddle_ocr_status()
                        if status.get("gpu_active"):
                            payload = dict(status)
                            payload.update({"state": "installed", "running": False, "message": f"Paddle OCR runtime is installed. GPU is active ({installed_package})."})
                            self.paddleOcrRuntimeInstallStatus.emit(payload)
                            return
                        probe = dict(status.get("runtime_probe") or {})
                        gpu_error = str(probe.get("gpu_error") or "GPU package installed, but Paddle did not activate the GPU.")
                        self._log(f"Paddle OCR GPU runtime inactive; falling back to CPU: {gpu_error}")
                    except Exception as exc:
                        gpu_error = str(exc)
                        self._log(f"Paddle OCR GPU runtime install failed; falling back to CPU: {exc}")
                else:
                    gpu_error = str(gpu_target.get("reason") or "No compatible NVIDIA GPU was detected.")

                emit_status(f"Installing Paddle CPU runtime... GPU fallback reason: {gpu_error}")
                try:
                    self._paddle_ocr_run_command([str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"], "Removing inactive Paddle GPU package...", emit_status)
                except Exception as exc:
                    self._log(f"Paddle OCR cleanup before CPU fallback failed: {exc}")
                installed_package = install_paddle_package(
                    "paddlepaddle",
                    ["https://www.paddlepaddle.org.cn/packages/stable/cpu/", ""],
                    "Installing Paddle CPU runtime",
                )
                status = self.get_paddle_ocr_status()
                if not status.get("installed"):
                    probe = dict(status.get("runtime_probe") or {})
                    detail = str(probe.get("error") or probe.get("gpu_error") or probe.get("traceback") or "Paddle OCR runtime probe failed after install.")
                    raise RuntimeError(detail)
                message = "Paddle OCR runtime is installed."
                if status.get("gpu_active"):
                    message = f"{message} GPU is active."
                else:
                    message = f"{message} CPU fallback is active. GPU fallback reason: {gpu_error}"
                payload = dict(status)
                payload.update({"state": "installed", "running": False, "message": f"{message} ({installed_package})."})
                self.paddleOcrRuntimeInstallStatus.emit(payload)
            except Exception as exc:
                self.paddleOcrRuntimeInstallStatus.emit({"state": "error", "running": False, "installed": False, "message": str(exc) or "Paddle OCR runtime installation failed."})
            finally:
                self._paddle_ocr_runtime_installing = False

        threading.Thread(target=work, daemon=True, name="paddle-ocr-runtime-install").start()
        return True

    def _run_paddle_ocr_worker(self, source_path: Path, profile: str) -> dict:
        python_path = self._ocr_runtime_python_path()
        if not python_path.is_file():
            # Developer fallback only. Packaged installs should use the isolated OCR runtime.
            try:
                import paddleocr  # noqa: F401
                python_path = Path(sys.executable)
            except Exception as exc:
                expected = self._local_ai_runtime_root() / ".venv-paddleocr"
                raise RuntimeError(
                    "PaddleOCR runtime is not installed yet. "
                    f"Expected runtime folder: {expected}. "
                    "Install the optional OCR runtime before using Paddle OCR."
                ) from exc
        launcher, worker_cwd, worker_pythonpath = self._ocr_worker_launcher(python_path)
        settings_payload = {
            "lang": str(self.settings.value("ocr/paddle_lang", "en", type=str) or "en"),
            "device": str(self.settings.value("ocr/paddle_device", "auto", type=str) or "auto"),
            "prefer_gpu": bool(self.settings.value("ocr/paddle_prefer_gpu", True, type=bool)),
            "cache_dir": str(Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default())) / "paddleocr_cache"),
        }
        command = [
            *launcher,
            "--source",
            str(source_path),
            "--profile",
            str(profile or "fast"),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        cache_root = Path(str(settings_payload["cache_dir"]))
        home_dir = cache_root / "home"
        temp_dir = cache_root / "tmp"
        child_env["PADDLE_PDX_CACHE_HOME"] = str(cache_root)
        child_env["PADDLE_HOME"] = str(cache_root / "paddle")
        child_env["PPOCR_HOME"] = str(cache_root / "ppocr")
        child_env["XDG_CACHE_HOME"] = str(cache_root / "xdg")
        child_env["HF_HOME"] = str(cache_root / "hf_home")
        child_env["HOME"] = str(home_dir)
        child_env["USERPROFILE"] = str(home_dir)
        child_env["TEMP"] = str(temp_dir)
        child_env["TMP"] = str(temp_dir)
        child_env.setdefault("FLAGS_use_mkldnn", "0")
        child_env.setdefault("FLAGS_enable_pir_api", "0")
        if os.name == "nt":
            child_env["HOMEDRIVE"] = str(home_dir.drive or "C:")
            child_env["HOMEPATH"] = str(home_dir)[len(str(home_dir.drive or "")) :] or "\\"
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
        completed = subprocess.run(command, timeout=300, **popen_kwargs)
        if completed.stderr.strip():
            self._log(f"Paddle OCR worker stderr for {source_path}: {completed.stderr.strip()[-2000:]}")
        payload = None
        for line in reversed([line.strip() for line in completed.stdout.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail[-500:] if detail else "Paddle OCR worker exited without a result.")
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or "Paddle OCR failed."))
        return payload

    def _save_ocr_payload(self, path: str, payload: dict, *, select_as_winner: bool = False) -> str:
        from app.mediamanager.db.ocr_repo import add_ocr_result, get_ocr_winner

        media = self._ensure_media_record_for_tag_write(path)
        if not media:
            raise FileNotFoundError("Selected media record could not be created.")
        text = str(payload.get("text") or "").strip()
        if not text:
            return ""
        add_ocr_result(
            self.conn,
            int(media["id"]),
            source=str(payload.get("source") or "unknown"),
            text=text,
            confidence=payload.get("confidence"),
            engine_version=str(payload.get("engine_version") or ""),
            preprocess_profile=str(payload.get("preprocess_profile") or ""),
            metadata=dict(payload.get("metadata") or {}),
            select_as_winner=bool(select_as_winner),
            selected_by="manual" if select_as_winner else "rules",
        )
        self.galleryScopeChanged.emit()
        winner = get_ocr_winner(self.conn, int(media["id"])) or {}
        return str(winner.get("text") or text).strip()

    def _run_gemma_ocr_worker(self, source_path: Path, media_id: int | None = None) -> dict:
        from app.mediamanager.db.ocr_repo import get_ocr_results

        ai_settings = self._local_ai_caption_settings()
        previous = get_ocr_results(self.conn, int(media_id)) if media_id else []
        return self._run_local_ai_worker_process("ocr", source_path, ai_settings, previous_ocr=previous)

    @Slot(str)
    def run_manual_ocr(self, path: str) -> None:
        self.run_manual_ocr_with_source(path, "paddle_fast")

    @Slot(str, str)
    def run_manual_ocr_with_source(self, path: str, source: str) -> None:
        def work() -> None:
            text = ""
            error = ""
            try:
                media_path = Path(path)
                if not media_path.exists() or not media_path.is_file():
                    raise FileNotFoundError("Selected file was not found.")
                m = self._ensure_media_record_for_tag_write(path)
                if not m:
                    raise FileNotFoundError("Selected media record could not be created.")
                ocr_source_path = self._manual_ocr_source_path(media_path)
                mode = str(source or "paddle_fast").strip().lower()
                if mode == "gemma4":
                    payload = self._run_gemma_ocr_worker(ocr_source_path, int(m["id"]))
                elif mode == "windows_ocr_legacy":
                    from app.mediamanager.utils.text_detection import extract_text_windows_ocr

                    legacy_text = extract_text_windows_ocr(ocr_source_path)
                    payload = {
                        "source": "windows_ocr_legacy",
                        "text": legacy_text,
                        "confidence": None,
                        "engine_version": "windows_media_ocr",
                        "preprocess_profile": "legacy_variants",
                    }
                else:
                    profile = "accurate" if mode in {"paddle_accurate", "accurate"} else "fast"
                    payload = self._run_paddle_ocr_worker(ocr_source_path, profile)
                text = self._save_ocr_payload(path, payload, select_as_winner=False)
            except Exception as exc:
                error = str(exc) or "OCR failed."
            self.manualOcrFinished.emit(path, text, error)

        threading.Thread(target=work, daemon=True, name=f"manual-ocr-{str(source or 'paddle_fast')}").start()

    @Slot(result=list)
    def get_ocr_review_items(self) -> list:
        from app.mediamanager.db.ocr_repo import list_open_ocr_reviews

        try:
            return list_open_ocr_reviews(self.conn)
        except Exception as exc:
            self._log(f"List OCR reviews failed: {exc}")
            return []

    @Slot(int, int, result=bool)
    def keep_ocr_result(self, media_id: int, result_id: int) -> bool:
        from app.mediamanager.db.ocr_repo import set_ocr_winner

        try:
            set_ocr_winner(self.conn, int(media_id), int(result_id), selected_by="user")
            self.galleryScopeChanged.emit()
            return True
        except Exception as exc:
            self._log(f"Keep OCR result failed: {exc}")
            return False

    @Slot(int, str, result=bool)
    def keep_latest_ocr_result_source(self, media_id: int, source: str) -> bool:
        from app.mediamanager.db.ocr_repo import set_ocr_winner

        try:
            row = self.conn.execute(
                """
                SELECT id
                FROM media_ocr_results
                WHERE media_id = ? AND source = ? AND COALESCE(text, '') != ''
                ORDER BY created_at_utc DESC, id DESC
                LIMIT 1
                """,
                (int(media_id), str(source or "")),
            ).fetchone()
            if not row:
                return False
            set_ocr_winner(self.conn, int(media_id), int(row["id"] if hasattr(row, "keys") else row[0]), selected_by="user")
            self.galleryScopeChanged.emit()
            return True
        except Exception as exc:
            self._log(f"Keep latest OCR result failed: {exc}")
            return False

    @Slot(int, str, result=bool)
    def keep_user_ocr_text(self, media_id: int, text: str) -> bool:
        from app.mediamanager.db.ocr_repo import add_ocr_result

        try:
            clean_text = str(text or "").strip()
            add_ocr_result(
                self.conn,
                int(media_id),
                source="user",
                text=clean_text,
                confidence=1.0,
                engine_version="manual_review",
                preprocess_profile="user_edit",
                select_as_winner=True,
                selected_by="user",
            )
            self.galleryScopeChanged.emit()
            return True
        except Exception as exc:
            self._log(f"Keep edited OCR text failed: {exc}")
            return False

    @Slot(int, result=bool)
    def mark_ocr_review_no_text(self, media_id: int) -> bool:
        try:
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            self.conn.execute(
                "UPDATE media_items SET detected_text = '', user_confirmed_text_detected = 0, updated_at_utc = ? WHERE id = ?",
                (now, int(media_id)),
            )
            self.conn.execute(
                "DELETE FROM media_ocr_winners WHERE media_id = ?",
                (int(media_id),),
            )
            self.conn.execute(
                "UPDATE media_ocr_results SET is_user_selected = 0 WHERE media_id = ?",
                (int(media_id),),
            )
            self.conn.execute(
                "UPDATE media_ocr_review_items SET status = 'resolved', updated_at_utc = ? WHERE media_id = ?",
                (now, int(media_id)),
            )
            self.conn.commit()
            if self._current_gallery_filter_uses_text():
                self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
            return True
        except Exception as exc:
            self._log(f"Mark OCR review no-text failed: {exc}")
            return False



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
