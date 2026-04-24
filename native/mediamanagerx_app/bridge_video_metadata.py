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

    @Slot(str)
    def run_manual_ocr(self, path: str) -> None:
        def work() -> None:
            text = ""
            error = ""
            try:
                media_path = Path(path)
                if not media_path.exists() or not media_path.is_file():
                    raise FileNotFoundError("Selected file was not found.")
                from app.mediamanager.db.media_repo import update_media_detected_text, update_user_confirmed_text_detected
                from app.mediamanager.utils.text_detection import extract_text_windows_ocr

                ocr_source_path = self._manual_ocr_source_path(media_path)
                text = extract_text_windows_ocr(ocr_source_path)
                if text.strip():
                    m = self._ensure_media_record_for_tag_write(path)
                    if m:
                        update_media_detected_text(self.conn, m["id"], text)
                        update_user_confirmed_text_detected(self.conn, m["id"], True)
                        self.galleryScopeChanged.emit()
            except Exception as exc:
                error = str(exc) or "OCR failed."
            self.manualOcrFinished.emit(path, text, error)

        threading.Thread(target=work, daemon=True, name="manual-ocr").start()



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
