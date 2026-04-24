from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.image_utils import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.widgets import *
from native.mediamanagerx_app.compare import *
from native.mediamanagerx_app.metadata_payload import *

class BridgeMediaToolsMixin:
    def debug_log(self, msg: str) -> None:
        """Receive frontend diagnostics without bloating logs during normal use."""
        text = str(msg or "")
        if "JS ERROR" in text or getattr(self, "_verbose_logs", False):
            self._log(f"JS Debug: {text}")

    def _thumb_key(self, path: Path) -> str:
        s = str(path).replace("\\", "/").lower().encode("utf-8")
        return hashlib.sha1(s).hexdigest()

    def _video_poster_path(self, video_path: Path) -> Path:
        return self._thumb_dir / f"{self._thumb_key(video_path)}.jpg"

    def _video_needs_ascii_runtime_path(self, video_path: Path) -> bool:
        try:
            raw = str(video_path)
        except Exception:
            return False
        return any(ord(ch) > 127 for ch in raw)

    def _video_runtime_alias_path(self, video_path: Path) -> Path:
        runtime_dir = _appdata_runtime_dir() / "video-runtime-aliases"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        suffix = video_path.suffix or ".bin"
        return runtime_dir / f"{self._thumb_key(video_path)}{suffix.lower()}"

    def _video_runtime_path(self, video_path: str | Path) -> str:
        path_obj = Path(video_path)
        if not self._video_needs_ascii_runtime_path(path_obj):
            return str(path_obj)

        alias_path = self._video_runtime_alias_path(path_obj)
        try:
            src_stat = path_obj.stat()
        except Exception:
            return str(path_obj)

        try:
            if alias_path.exists():
                alias_stat = alias_path.stat()
                if alias_stat.st_size == src_stat.st_size and alias_stat.st_mtime >= (src_stat.st_mtime - 1):
                    return str(alias_path)
                alias_path.unlink(missing_ok=True)
        except Exception:
            pass

        try:
            shutil.copy2(str(path_obj), str(alias_path))
            self._log(f"Using ASCII-safe runtime alias for video path: {path_obj.name}")
            return str(alias_path)
        except Exception as exc:
            try:
                self._log(f"Failed to create ASCII-safe runtime alias for '{path_obj.name}': {exc}")
            except Exception:
                pass
            return str(path_obj)

    def _bundled_tool_candidates(self, name: str) -> list[Path]:
        exe_name = f"{name}.exe" if os.name == "nt" else name
        roots: list[Path] = []
        try:
            roots.append(Path(sys.executable).resolve().parent)
        except Exception:
            pass
        try:
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                roots.append(Path(meipass).resolve())
        except Exception:
            pass
        try:
            roots.append(Path(__file__).resolve().parents[2])
        except Exception:
            pass

        candidates: list[Path] = []
        for root in roots:
            candidates.extend(
                [
                    root / "tools" / "ffmpeg" / "bin" / exe_name,
                    root / "tools" / exe_name,
                    root / exe_name,
                ]
            )
        return candidates

    def _media_tool_bin(self, name: str) -> str | None:
        env_key = f"MEDIALENS_{name.upper()}_PATH"
        env_path = str(os.environ.get(env_key, "") or "").strip().strip('"')
        candidates = [Path(env_path)] if env_path else []
        candidates.extend(self._bundled_tool_candidates(name))

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    resolved = str(candidate.resolve())
                    if name not in self._logged_tool_paths:
                        self._log(f"Using {name} binary: {resolved}")
                        self._logged_tool_paths.add(name)
                    return resolved
            except Exception:
                continue

        found = shutil.which(name)
        if found:
            if name not in self._logged_tool_paths:
                self._log(f"Using {name} from PATH: {found}")
                self._logged_tool_paths.add(name)
            return found

        if name not in self._logged_missing_tools:
            self._log(f"{name} binary not found. Bundled video tooling is missing and PATH lookup failed.")
            self._logged_missing_tools.add(name)
        return None

    def _ffmpeg_bin(self) -> str | None:
        return self._media_tool_bin("ffmpeg")

    def _ffprobe_bin(self) -> str | None:
        return self._media_tool_bin("ffprobe")

    def _ensure_video_poster(self, video_path: Path) -> Path | None:
        """Generate a poster jpg for a video or image using ffmpeg (if missing)."""
        out = self._video_poster_path(video_path)
        if out.exists():
            return out
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            self._log(f"Video poster unavailable; ffmpeg not found for {video_path}")
            return None
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            ext = video_path.suffix.lower()
            is_vid = ext in {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".wmv"}
            runtime_path = self._video_runtime_path(video_path) if is_vid else str(video_path)
            # For images, don't use -ss as it can fail for 0-duration files
            vf = "thumbnail,scale=min(640\\,iw):-2" if is_vid else "scale=min(640\\,iw):-2"
            
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            if is_vid:
                cmd += ["-ss", "0.5"]
            cmd += ["-i", runtime_path, "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out)]
            
            r = _run_hidden_subprocess(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or "").strip().replace("\r", " ").replace("\n", " ")
                self._log(f"Video poster generation failed for {video_path}: exit={r.returncode} {err[:500]}")
                return None
            return out if out.exists() else None
        except Exception as e:
            self._log(f"Video poster generation error for {video_path}: {type(e).__name__}: {e}")
            return None
        
    def _is_animated(self, path: Path) -> bool:
        """Check if image is animated (GIF or animated WebP)."""
        suffix = path.suffix.lower()
        if suffix == ".gif":
            return True
        if suffix == ".webp":
            try:
                with open(path, "rb") as f:
                    header = f.read(32)
                if header[0:4] == b"RIFF" and header[8:12] == b"WEBP" and header[12:16] == b"VP8X":
                    flags = header[20]
                    return bool(flags & 2)
            except Exception:
                pass
        return False



__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]
