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

    def _paddle_ocr_default_python_path(self) -> Path:
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        exe_name = "python.exe" if os.name == "nt" else "python"
        return self._local_ai_runtime_root() / ".venv-paddleocr" / scripts_dir / exe_name

    def _paddle_ocr_runtime_dir_for_python(self, python_path: Path) -> Path:
        return Path(python_path).parent.parent

    def _paddle_ocr_staging_dir_for_runtime(self, runtime_dir: Path) -> Path:
        runtime_dir = Path(runtime_dir)
        return runtime_dir.with_name(f"{runtime_dir.name}-installing")

    def _paddle_ocr_managed_runtime_dir(self, runtime_dir: Path) -> bool:
        try:
            runtime_root = self._local_ai_runtime_root().resolve()
            resolved = Path(runtime_dir).resolve()
            allowed = {
                (runtime_root / ".venv-paddleocr").resolve(),
                (runtime_root / ".venv-paddleocr-installing").resolve(),
                (runtime_root / ".venv-paddleocr-previous").resolve(),
            }
            return resolved in allowed
        except Exception:
            return False

    def _remove_paddle_ocr_runtime_dir(self, runtime_dir: Path) -> None:
        runtime_dir = Path(runtime_dir)
        if not runtime_dir.exists():
            return
        if not self._paddle_ocr_managed_runtime_dir(runtime_dir):
            raise RuntimeError(f"Refusing to remove unmanaged Paddle OCR runtime folder: {runtime_dir}")
        shutil.rmtree(runtime_dir)

    def _activate_paddle_ocr_staged_runtime(self, staging_dir: Path, runtime_dir: Path) -> None:
        staging_dir = Path(staging_dir)
        runtime_dir = Path(runtime_dir)
        previous_dir = runtime_dir.with_name(f"{runtime_dir.name}-previous")
        if not self._paddle_ocr_managed_runtime_dir(staging_dir) or not self._paddle_ocr_managed_runtime_dir(runtime_dir):
            raise RuntimeError("Refusing to activate unmanaged Paddle OCR runtime folder.")
        self._remove_paddle_ocr_runtime_dir(previous_dir)
        try:
            if runtime_dir.exists():
                runtime_dir.replace(previous_dir)
            staging_dir.replace(runtime_dir)
            self._remove_paddle_ocr_runtime_dir(previous_dir)
        except Exception:
            if not runtime_dir.exists() and previous_dir.exists():
                try:
                    previous_dir.replace(runtime_dir)
                except Exception:
                    pass
            raise

    def _paddle_ocr_install_log_path(self) -> Path:
        return _debugging_logs_dir(_appdata_runtime_dir()) / "paddle-ocr-install.log"

    def _paddle_ocr_install_log_hint(self) -> str:
        try:
            return f"Install log: {self._paddle_ocr_install_log_path()}"
        except Exception:
            return "Install log: unavailable"

    def _paddle_ocr_install_log(self, message: object) -> None:
        try:
            path = self._paddle_ocr_install_log_path()
            text = _sanitize_diagnostic_text(message)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"[{time.ctime()}] {text}\n")
        except Exception:
            pass

    @Slot(result="QVariantMap")
    def get_paddle_ocr_status(self) -> dict:
        return self._get_paddle_ocr_status(probe_timeout=12)

    def _paddle_ocr_probe_code(self) -> str:
        return (
            "import json\n"
            "import traceback\n"
            "from importlib import metadata\n"
            "def dist_version(name):\n"
            " try:\n"
            "  return metadata.version(name)\n"
            " except metadata.PackageNotFoundError:\n"
            "  return ''\n"
            " except Exception:\n"
            "  return ''\n"
            "payload={'ok': True, 'probe_kind': 'paddle_core'}\n"
            "try:\n"
            " import paddle\n"
            " payload['paddle_version']=str(getattr(paddle, '__version__', ''))\n"
            " payload['paddleocr_dist']=dist_version('paddleocr')\n"
            " payload['paddle_path']=str(getattr(paddle, '__file__', ''))\n"
            " payload['paddlepaddle_dist']=dist_version('paddlepaddle')\n"
            " payload['paddlepaddle_gpu_dist']=dist_version('paddlepaddle-gpu')\n"
            " payload['compiled_with_cuda']=bool(paddle.device.is_compiled_with_cuda())\n"
            " if payload['compiled_with_cuda']:\n"
            "  try:\n"
            "   try:\n"
            "    payload['gpu_device_count']=int(paddle.device.cuda.device_count())\n"
            "   except Exception:\n"
            "    payload['gpu_device_count']=None\n"
            "   paddle.set_device('gpu')\n"
            "  except Exception as device_exc:\n"
            "   payload['gpu_error']=str(device_exc)\n"
            " payload['current_device']=str(paddle.get_device())\n"
            "except Exception as exc:\n"
            " payload={'ok': False, 'probe_kind': 'paddle_core', 'error': str(exc), 'traceback': traceback.format_exc()[-1600:]}\n"
            "print(json.dumps(payload), flush=True)\n"
        )

    def _get_paddle_ocr_status(
        self,
        probe_timeout: int = 12,
        *,
        python_path_override: Path | None = None,
        include_installing_state: bool = True,
    ) -> dict:
        try:
            python_path = Path(python_path_override) if python_path_override is not None else self._ocr_runtime_python_path()
            device = str(self.settings.value("ocr/paddle_device", "auto", type=str) or "auto")
            prefer_gpu = bool(self.settings.value("ocr/paddle_prefer_gpu", True, type=bool))
            gpu_target = self._paddle_ocr_gpu_install_target()
            if include_installing_state and bool(getattr(self, "_paddle_ocr_runtime_installing", False)):
                return {
                    "installed": False,
                    "state": "installing",
                    "running": True,
                    "message": "Paddle OCR runtime is installing.",
                    "python_path": str(python_path),
                    "device": device,
                    "prefer_gpu": prefer_gpu,
                    "runtime_probe": {},
                    "gpu_active": False,
                    "gpu_available": False,
                    "gpu_detected": bool(gpu_target.get("available")),
                    "gpu_target": gpu_target,
                    "gpu_issue": "",
                    "current_device": "",
                    "fast_enabled": True,
                    "accurate_enabled": False,
                }
            probe: dict = {}
            if python_path.is_file():
                try:
                    completed = _run_hidden_subprocess(
                        [str(python_path), "-c", self._paddle_ocr_probe_code()],
                        capture_output=True,
                        text=True,
                        timeout=max(12, int(probe_timeout or 12)),
                        env=self._paddle_ocr_runtime_env(python_path),
                    )
                    if completed.returncode == 0:
                        probe = self._parse_paddle_ocr_probe_stdout(completed.stdout)
                    else:
                        probe = {"ok": False, "error": (completed.stderr or completed.stdout or "").strip()[-500:]}
                except subprocess.TimeoutExpired as exc:
                    detail = "Paddle OCR runtime probe timed out."
                    output = " ".join(str(getattr(exc, "output", "") or getattr(exc, "stdout", "") or getattr(exc, "stderr", "") or "").split()).strip()
                    if output:
                        detail = f"{detail} {output[-500:]}"
                    probe = {"ok": False, "error": detail}
                except Exception as exc:
                    probe = {"ok": False, "error": str(exc)}
            current_device = str(probe.get("current_device") or "").strip().lower()
            gpu_active = current_device.startswith("gpu") or current_device.startswith("cuda")
            has_paddle_package = bool(str(probe.get("paddlepaddle_dist") or probe.get("paddlepaddle_gpu_dist") or "").strip())
            has_paddleocr = bool(str(probe.get("paddleocr_dist") or "").strip())
            installed = bool(python_path.is_file() and probe.get("ok") and not probe.get("error") and has_paddle_package and has_paddleocr)
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
                if not detail and probe.get("ok") and not has_paddleocr:
                    detail = "PaddleOCR package is missing from the OCR runtime."
                elif not detail and probe.get("ok") and not has_paddle_package:
                    detail = "Paddle package is missing from the OCR runtime."
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
    def _parse_paddle_ocr_probe_stdout(stdout: str | None) -> dict:
        text = str(stdout or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            pass
        for line in reversed(text.splitlines()):
            candidate = line.strip()
            if not (candidate.startswith("{") and candidate.endswith("}")):
                continue
            try:
                parsed = json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise ValueError(f"Paddle OCR runtime probe returned non-JSON output: {text[-500:]}")

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
                    "package": "paddlepaddle-gpu==3.2.2",
                    "index_url": "https://www.paddlepaddle.org.cn/packages/stable/cu126/",
                    "label": "CUDA 12.6",
                }
            if self._driver_at_least(driver, (452, 39, 0)):
                return {
                    "available": True,
                    "driver": driver_text,
                    "package": "paddlepaddle-gpu==3.2.2",
                    "index_url": "https://www.paddlepaddle.org.cn/packages/stable/cu118/",
                    "label": "CUDA 11.8",
                }
            return {"available": False, "driver": driver_text, "reason": f"NVIDIA driver {driver_text} is too old for Paddle GPU wheels."}
        return {"available": False, "reason": f"NVIDIA GPU was not detected. Tried: {'; '.join(errors[-4:]) if errors else 'nvidia-smi not found'}"}

    def _paddle_ocr_nvidia_bin_dirs(self, python_path: str | Path | None = None) -> list[str]:
        try:
            if not python_path:
                python_path = self._ocr_runtime_python_path()
            runtime_dir = Path(python_path).parent.parent
            site_packages = runtime_dir / "Lib" / "site-packages"
            nvidia_root = site_packages / "nvidia"
            if not nvidia_root.is_dir():
                return []
            dirs: list[str] = []
            for candidate in nvidia_root.glob("**/bin"):
                if candidate.is_dir():
                    dirs.append(str(candidate))
            return dirs
        except Exception:
            return []

    def _paddle_ocr_runtime_env(self, python_path: str | Path | None = None) -> dict[str, str]:
        cache_root = Path(str(self.settings.value("ai_caption/models_dir", self._local_ai_models_dir_default(), type=str) or self._local_ai_models_dir_default())) / "paddleocr_cache"
        home_dir = cache_root / "home"
        temp_dir = cache_root / "tmp"
        child_env = self._local_ai_subprocess_env("")
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
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        child_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        child_env["PIP_NO_INPUT"] = "1"
        child_env.setdefault("FLAGS_use_mkldnn", "0")
        child_env.setdefault("FLAGS_enable_pir_api", "0")
        nvidia_bin_dirs = self._paddle_ocr_nvidia_bin_dirs(python_path)
        if nvidia_bin_dirs:
            existing_path = str(child_env.get("PATH") or "")
            child_env["PATH"] = os.pathsep.join([*nvidia_bin_dirs, existing_path] if existing_path else nvidia_bin_dirs)
        if os.name == "nt":
            child_env["HOMEDRIVE"] = str(home_dir.drive or "C:")
            child_env["HOMEPATH"] = str(home_dir)[len(str(home_dir.drive or "")) :] or "\\"
        return child_env

    def _paddle_ocr_run_command(self, command: list[str], message: str, emit_status, *, runtime_env: bool = False, python_path: str | Path | None = None) -> None:
        emit_status(message)
        command_text = " ".join(shlex.quote(str(part)) for part in command)
        command_cwd = Path(python_path).parent.parent if python_path else self._local_ai_runtime_root()
        command_cwd.mkdir(parents=True, exist_ok=True)
        self._paddle_ocr_install_log(f"START {message} :: {command_text}")
        try:
            returncode, last_line = self._local_ai_run_command_stream(
                command,
                command_cwd,
                message,
                emit_status,
                env=self._paddle_ocr_runtime_env(python_path) if runtime_env else None,
            )
        except Exception as exc:
            self._paddle_ocr_install_log(f"ERROR {message} :: {exc}")
            raise
        self._paddle_ocr_install_log(f"END {message} :: exit={returncode} last={last_line}")
        if returncode != 0:
            raise RuntimeError(f"{message} failed ({self._local_ai_exit_code_text(returncode)}). {last_line}")

    def _ensure_paddle_ocr_packaging_tools(self, python_path: Path, emit_status) -> None:
        try:
            self._paddle_ocr_run_command([str(python_path), "-m", "pip", "--version"], "Checking Paddle OCR package installer...", emit_status, runtime_env=True, python_path=python_path)
        except Exception:
            self._paddle_ocr_run_command([str(python_path), "-m", "ensurepip", "--upgrade"], "Repairing Paddle OCR package installer...", emit_status, runtime_env=True, python_path=python_path)
        self._paddle_ocr_run_command([str(python_path), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "setuptools", "wheel"], "Installing Paddle OCR packaging tools...", emit_status, runtime_env=True, python_path=python_path)

    def _remove_stale_paddle_package_files(self, python_path: Path, emit_status) -> None:
        code = (
            "import json, shutil, site, sys\n"
            "from pathlib import Path\n"
            "roots=[]\n"
            "for value in site.getsitepackages()+[site.getusersitepackages()]:\n"
            " p=Path(value)\n"
            " if p.exists() and p not in roots:\n"
            "  roots.append(p)\n"
            "removed=[]\n"
            "patterns=('paddle','paddle.libs','paddlepaddle-*.dist-info','paddlepaddle_gpu-*.dist-info')\n"
            "for root in roots:\n"
            " for pattern in patterns:\n"
            "  for path in root.glob(pattern):\n"
            "   try:\n"
            "    if path.is_dir():\n"
            "     shutil.rmtree(path)\n"
            "    else:\n"
            "     path.unlink()\n"
            "    removed.append(str(path))\n"
            "   except FileNotFoundError:\n"
            "    pass\n"
            "print(json.dumps({'removed': removed[-20:]}), flush=True)\n"
        )
        self._paddle_ocr_run_command(
            [str(python_path), "-c", code],
            "Clearing stale Paddle package files...",
            emit_status,
            runtime_env=True,
            python_path=python_path,
        )

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

            staging_dir: Path | None = None
            try:
                active_python_path = self._ocr_runtime_python_path()
                configured_python = str(self.settings.value("ocr/paddle_python", "", type=str) or "").strip()
                default_python_path = self._paddle_ocr_default_python_path()
                target_python_path = Path(configured_python) if configured_python else default_python_path
                target_runtime_dir = self._paddle_ocr_runtime_dir_for_python(target_python_path)
                if configured_python and not self._paddle_ocr_managed_runtime_dir(target_runtime_dir):
                    initial_custom_status = (
                        dict(
                            self._get_paddle_ocr_status(
                                probe_timeout=30,
                                python_path_override=active_python_path,
                                include_installing_state=False,
                            )
                            or {}
                        )
                        if active_python_path.is_file()
                        else {}
                    )
                    if initial_custom_status.get("installed") and not str(initial_custom_status.get("gpu_issue") or "").strip():
                        payload = dict(initial_custom_status)
                        payload.update({"state": "installed", "running": False, "message": "Paddle OCR runtime is already installed."})
                        self.paddleOcrRuntimeInstallStatus.emit(payload)
                        return
                    self._paddle_ocr_install_log(
                        f"Configured Paddle Python is outside the managed runtime; installing into managed runtime instead: {configured_python}"
                    )
                    target_python_path = default_python_path
                    target_runtime_dir = self._paddle_ocr_runtime_dir_for_python(target_python_path)

                runtime_dir = target_runtime_dir
                runtime_dir.parent.mkdir(parents=True, exist_ok=True)
                bootstrap_python = self._ensure_local_ai_python_bootstrap(lambda msg: emit_status(msg))
                if not bootstrap_python:
                    raise RuntimeError("MediaLens could not prepare the Python bootstrap needed to create the OCR runtime.")
                gpu_target = self._paddle_ocr_gpu_install_target()
                prefer_gpu = bool(self.settings.value("ocr/paddle_prefer_gpu", True, type=bool))
                initial_status = (
                    dict(
                        self._get_paddle_ocr_status(
                            probe_timeout=30,
                            python_path_override=target_python_path,
                            include_installing_state=False,
                        )
                        or {}
                    )
                    if target_python_path.is_file()
                    else {}
                )
                if initial_status.get("installed") and not str(initial_status.get("gpu_issue") or "").strip():
                    payload = dict(initial_status)
                    message = "Paddle OCR runtime is already installed."
                    if initial_status.get("gpu_active"):
                        message = f"{message} GPU is active."
                    payload.update({"state": "installed", "running": False, "message": message})
                    self.paddleOcrRuntimeInstallStatus.emit(payload)
                    return

                use_staging = self._paddle_ocr_managed_runtime_dir(runtime_dir)
                if use_staging:
                    staging_dir = self._paddle_ocr_staging_dir_for_runtime(runtime_dir)
                    python_path = staging_dir / target_python_path.relative_to(runtime_dir)
                    emit_status("Preparing clean Paddle OCR runtime...")
                    self._remove_paddle_ocr_runtime_dir(staging_dir)
                    self._paddle_ocr_run_command([bootstrap_python, "-m", "venv", str(staging_dir)], "Creating clean Paddle OCR runtime...", emit_status)
                else:
                    python_path = target_python_path
                    if runtime_dir.exists() and not python_path.is_file():
                        raise RuntimeError(f"Configured Paddle OCR runtime is not a valid Python venv: {runtime_dir}")
                    if not python_path.is_file():
                        self._paddle_ocr_run_command([bootstrap_python, "-m", "venv", str(runtime_dir)], "Creating Paddle OCR runtime...", emit_status)

                if not python_path.is_file():
                    raise RuntimeError("Paddle OCR runtime was created, but python.exe was not found.")
                self._paddle_ocr_install_log(f"Installing Paddle OCR runtime into staging={bool(staging_dir)} python={python_path}")
                self._ensure_paddle_ocr_packaging_tools(python_path, emit_status)

                requirements_path = self._local_ai_requirements_path(type("Spec", (), {"requirements_file": "requirements-local-ocr-paddle.txt"})())
                self._paddle_ocr_run_command([str(python_path), "-m", "pip", "install", "-r", str(requirements_path)], "Installing PaddleOCR support...", emit_status, runtime_env=True, python_path=python_path)
                self._paddle_ocr_run_command([str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"], "Removing Paddle package selected by dependency resolver...", emit_status, runtime_env=True, python_path=python_path)
                self._remove_stale_paddle_package_files(python_path, emit_status)

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
                                    runtime_env=True,
                                    python_path=python_path,
                                )
                                return package
                            except Exception as exc:
                                cleaned = clean_install_error(exc)
                                errors.append(cleaned)
                                self._log(f"{message_prefix} {version} from {source_label} failed: {cleaned}")
                    raise RuntimeError(errors[-1] if errors else f"{message_prefix} failed.")

                gpu_error = ""
                installed_package = ""
                if prefer_gpu and bool(gpu_target.get("available")):
                    try:
                        installed_package = install_paddle_package(
                            "paddlepaddle-gpu",
                            [str(gpu_target["index_url"])],
                            f"Installing Paddle GPU runtime ({gpu_target.get('label')})",
                        )
                        status = self._get_paddle_ocr_status(
                            probe_timeout=90,
                            python_path_override=python_path,
                            include_installing_state=False,
                        )
                        if not status.get("gpu_active"):
                            probe = dict(status.get("runtime_probe") or {})
                            retry_reason = str(
                                probe.get("gpu_error")
                                or probe.get("error")
                                or status.get("gpu_issue")
                                or "Initial GPU probe did not activate."
                            )
                            self._log(f"Paddle OCR clean GPU activation starting: {retry_reason}")
                            self._paddle_ocr_run_command(
                                [str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"],
                                "Removing stale Paddle package before GPU activation...",
                                emit_status,
                                runtime_env=True,
                                python_path=python_path,
                            )
                            self._remove_stale_paddle_package_files(python_path, emit_status)
                            installed_package = install_paddle_package(
                                "paddlepaddle-gpu",
                                [str(gpu_target["index_url"])],
                                f"Activating Paddle GPU runtime ({gpu_target.get('label')})",
                            )
                            status = self._get_paddle_ocr_status(
                                probe_timeout=90,
                                python_path_override=python_path,
                                include_installing_state=False,
                            )
                        if status.get("gpu_active"):
                            final_status = status
                        probe = dict(status.get("runtime_probe") or {})
                        if not status.get("gpu_active"):
                            gpu_error = str(probe.get("gpu_error") or probe.get("error") or "GPU package installed, but Paddle did not activate the GPU.")
                            self._log(f"Paddle OCR GPU runtime probe failed after install; CPU fallback skipped: {gpu_error}")
                            raise RuntimeError(f"Paddle GPU package installed, but the runtime probe failed. {gpu_error}")
                    except Exception as exc:
                        gpu_error = str(exc)
                        if prefer_gpu:
                            raise RuntimeError(f"Paddle GPU runtime install failed on a compatible NVIDIA GPU. CPU fallback was skipped because GPU is preferred. {gpu_error}")
                        self._log(f"Paddle OCR GPU runtime install failed; falling back to CPU: {exc}")
                else:
                    gpu_error = str(gpu_target.get("reason") or "No compatible NVIDIA GPU was detected.")

                if not (prefer_gpu and bool(gpu_target.get("available"))):
                    emit_status(f"Installing Paddle CPU runtime... GPU fallback reason: {gpu_error}")
                    try:
                        self._paddle_ocr_run_command([str(python_path), "-m", "pip", "uninstall", "-y", "paddlepaddle", "paddlepaddle-gpu"], "Removing inactive Paddle GPU package...", emit_status, runtime_env=True, python_path=python_path)
                        self._remove_stale_paddle_package_files(python_path, emit_status)
                    except Exception as exc:
                        self._log(f"Paddle OCR cleanup before CPU fallback failed: {exc}")
                    installed_package = install_paddle_package(
                        "paddlepaddle",
                        ["", "https://www.paddlepaddle.org.cn/packages/stable/cpu/"],
                        "Installing Paddle CPU runtime",
                    )
                    final_status = self._get_paddle_ocr_status(
                        probe_timeout=90,
                        python_path_override=python_path,
                        include_installing_state=False,
                    )
                    if not final_status.get("installed"):
                        probe = dict(final_status.get("runtime_probe") or {})
                        detail = str(probe.get("error") or probe.get("gpu_error") or probe.get("traceback") or "Paddle OCR runtime probe failed after install.")
                        raise RuntimeError(detail)

                if staging_dir is not None:
                    emit_status("Activating Paddle OCR runtime...")
                    self._activate_paddle_ocr_staged_runtime(staging_dir, runtime_dir)
                    staging_dir = None
                    if configured_python and Path(configured_python) != target_python_path:
                        self.settings.remove("ocr/paddle_python")
                        self.settings.sync()
                    final_status = self._get_paddle_ocr_status(
                        probe_timeout=90,
                        python_path_override=target_python_path,
                        include_installing_state=False,
                    )
                    if not final_status.get("installed"):
                        probe = dict(final_status.get("runtime_probe") or {})
                        detail = str(probe.get("error") or probe.get("gpu_error") or probe.get("traceback") or "Paddle OCR runtime probe failed after activation.")
                        raise RuntimeError(detail)

                message = "Paddle OCR runtime is installed."
                if final_status.get("gpu_active"):
                    message = f"{message} GPU is active."
                else:
                    message = f"{message} CPU fallback is active. GPU fallback reason: {gpu_error}"
                payload = dict(final_status)
                payload.update({"state": "installed", "running": False, "message": f"{message} ({installed_package})."})
                self.paddleOcrRuntimeInstallStatus.emit(payload)
            except Exception as exc:
                message = str(exc) or "Paddle OCR runtime installation failed."
                self._paddle_ocr_install_log(f"FAILED Paddle OCR runtime install :: {message}")
                if staging_dir is not None:
                    try:
                        self._remove_paddle_ocr_runtime_dir(staging_dir)
                    except Exception as cleanup_exc:
                        self._paddle_ocr_install_log(f"FAILED cleanup staging runtime :: {cleanup_exc}")
                log_hint = self._paddle_ocr_install_log_hint()
                payload = {"state": "error", "running": False, "installed": False, "message": f"{message}\n{log_hint}"}
                try:
                    status = dict(self._get_paddle_ocr_status(probe_timeout=30, include_installing_state=False) or {})
                except Exception:
                    status = {}
                if status.get("installed"):
                    payload = dict(status)
                    payload.update(
                        {
                            "state": "error" if str(status.get("gpu_issue") or "").strip() else "installed",
                            "running": False,
                            "message": f"Paddle OCR runtime is still installed, but repair failed: {message}\n{log_hint}",
                        }
                    )
                self.paddleOcrRuntimeInstallStatus.emit(payload)
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
        nvidia_bin_dirs = self._paddle_ocr_nvidia_bin_dirs(python_path)
        if nvidia_bin_dirs:
            existing_path = str(child_env.get("PATH") or "")
            child_env["PATH"] = os.pathsep.join([*nvidia_bin_dirs, existing_path] if existing_path else nvidia_bin_dirs)
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

    @Slot(str, str, result=bool)
    def keep_user_ocr_text_for_path(self, path: str, text: str) -> bool:
        try:
            media = self._ensure_media_record_for_tag_write(str(path or ""))
            if not media:
                return False
            return bool(self.keep_user_ocr_text(int(media["id"]), str(text or "")))
        except Exception as exc:
            self._log(f"Keep edited OCR text for path failed: {exc}")
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

    @Slot(str, result=bool)
    def mark_ocr_no_text_for_path(self, path: str) -> bool:
        try:
            media = self._ensure_media_record_for_tag_write(str(path or ""))
            if not media:
                return False
            return bool(self.mark_ocr_review_no_text(int(media["id"])))
        except Exception as exc:
            self._log(f"Mark OCR no-text for path failed: {exc}")
            return False



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
