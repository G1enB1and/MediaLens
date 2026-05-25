from __future__ import annotations

from native.mediamanagerx_app.common import *


class BridgePeopleMixin:
    def _ensure_people_scan_state(self) -> None:
        if not hasattr(self, "_people_scan_pause"):
            self._people_scan_pause = threading.Event()
        if not hasattr(self, "_people_scan_running"):
            self._people_scan_running = False

    def _people_scan_debug(self, message: str) -> None:
        clean = str(message or "").strip()
        if not clean:
            return
        line = f"People scan: {clean}"
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            self._log(line)
        except Exception:
            pass

    def _emit_people_scan_status(
        self,
        state: str,
        message: str,
        *,
        current: int = 0,
        total: int = 0,
        path: str = "",
        detected: int = 0,
        errors: int = 0,
    ) -> None:
        payload = {
            "state": str(state or ""),
            "message": str(message or ""),
            "current": int(current or 0),
            "total": int(total or 0),
            "path": str(path or ""),
            "detected": int(detected or 0),
            "errors": int(errors or 0),
        }
        if total:
            payload["percent"] = max(0, min(100, round((int(current or 0) / max(1, int(total or 0))) * 100)))
        else:
            payload["percent"] = 0
        try:
            self.peopleScanStatus.emit(payload)
        except Exception:
            pass

    def _people_scan_paths_from_current_scope(self) -> list[str]:
        try:
            folders = list(getattr(self, "_selected_folders", []) or [])
            if not folders:
                return []
            filter_type = str(getattr(self, "_current_gallery_filter", "all") or "all")
            search_query = str(getattr(self, "_current_gallery_search", "") or "")
            candidates = self._get_reconciled_candidates(folders, filter_type, search_query)
            return [
                str(item.get("path") or "").strip()
                for item in candidates
                if str(item.get("path") or "").strip() and not bool(item.get("is_folder"))
            ]
        except Exception as exc:
            self._people_scan_debug(f"could not resolve current gallery scope: {exc}")
            return []

    def _people_match_threshold_value(self) -> float:
        value = str(self.settings.value("people/match_threshold", "balanced", type=str) or "balanced").strip().lower()
        return {
            "conservative": 0.55,
            "balanced": 0.45,
            "loose": 0.36,
        }.get(value, 0.45)

    def _run_insightface_detection(self, python_path: Path, spec, source_path: Path, settings_payload: dict) -> dict:
        launcher, worker_cwd, worker_pythonpath = self._local_ai_worker_launcher(python_path, spec.worker_module)
        command = [
            *launcher,
            "--operation",
            "detect",
            "--source",
            str(source_path),
            "--settings-json",
            json.dumps(settings_payload, ensure_ascii=False),
        ]
        child_env = self._local_ai_subprocess_env(worker_pythonpath)
        popen_kwargs = dict(
            cwd=str(worker_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            timeout=180,
        )
        if _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS:
            popen_kwargs.update(_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS)
        self._people_scan_debug(f"running worker for {source_path} with {python_path}")
        completed = subprocess.run(command, **popen_kwargs)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if str(part or "").strip())
        if str(completed.stderr or "").strip():
            self._people_scan_debug(f"worker stderr for {source_path}: {str(completed.stderr).strip()[-2000:]}")
        payload = None
        for line in reversed([line.strip() for line in combined.splitlines() if line.strip()]):
            try:
                payload = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(payload, dict):
            raise RuntimeError(f"InsightFace detection returned no JSON ({self._local_ai_exit_code_text(completed.returncode)}).")
        if completed.returncode != 0 or not bool(payload.get("ok")):
            raise RuntimeError(str(payload.get("error") or payload.get("reason") or "InsightFace detection failed."))
        return payload

    def _scan_faces_worker(self, paths: list[str]) -> None:
        from app.mediamanager.ai_captioning.model_registry import INSIGHTFACE_MODEL_ID, model_spec
        from app.mediamanager.db.people_repo import replace_detected_faces

        spec = model_spec(INSIGHTFACE_MODEL_ID, "faces")
        python_path = self._local_ai_runtime_python_path(spec)
        settings_payload = self._local_ai_default_settings_payload_for_spec(spec)
        total = len(paths)
        scanned = 0
        detected = 0
        errors = 0
        self._people_scan_debug(f"worker started for {total} files; runtime_python={python_path}")
        self._emit_people_scan_status("running", "Starting People scan...", current=0, total=total)
        try:
            for raw_path in paths:
                current = scanned + errors + 1
                self._ensure_people_scan_state()
                while self._people_scan_pause.is_set():
                    self._emit_people_scan_status("paused", "People scan paused.", current=max(0, current - 1), total=total, path=str(raw_path or ""), detected=detected, errors=errors)
                    time.sleep(0.25)
                try:
                    media_path = Path(str(raw_path or ""))
                    if not media_path.is_file():
                        errors += 1
                        self._people_scan_debug(f"skipping missing file: {raw_path}")
                        self._emit_people_scan_status("running", f"Skipping missing file: {Path(str(raw_path or '')).name}", current=current, total=total, path=str(raw_path or ""), detected=detected, errors=errors)
                        continue
                    source_path = self._local_ai_source_path(media_path)
                    self._emit_people_scan_status("running", f"Scanning {media_path.name}", current=current - 1, total=total, path=str(media_path), detected=detected, errors=errors)
                    payload = self._run_insightface_detection(python_path, spec, source_path, settings_payload)
                    faces = [dict(face or {}) for face in list(payload.get("faces") or [])]
                    count = replace_detected_faces(
                        self.conn,
                        str(media_path),
                        faces,
                        detection_engine="insightface",
                        recognition_model="buffalo_l",
                        match_threshold=self._people_match_threshold_value(),
                    )
                    scanned += 1
                    detected += int(count or 0)
                    self._people_scan_debug(f"{media_path} detected={int(count or 0)} raw_faces={len(faces)}")
                    self._emit_people_scan_status("running", f"Scanned {media_path.name}: {int(count or 0)} faces", current=scanned + errors, total=total, path=str(media_path), detected=detected, errors=errors)
                except Exception as exc:
                    errors += 1
                    self._people_scan_debug(f"failed for {raw_path}: {exc}")
                    self._emit_people_scan_status("error" if errors >= total and scanned == 0 else "running", f"Error scanning {Path(str(raw_path or '')).name}: {exc}", current=scanned + errors, total=total, path=str(raw_path or ""), detected=detected, errors=errors)
            final_state = "finished" if errors == 0 or scanned > 0 else "error"
            final_message = f"People scan finished. Files scanned: {scanned}; faces detected: {detected}; errors: {errors}."
            self._people_scan_debug(final_message)
            self._emit_people_scan_status(final_state, final_message, current=total, total=total, detected=detected, errors=errors)
            self._clear_gallery_count_cache()
            self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
        finally:
            self._ensure_people_scan_state()
            self._people_scan_running = False
            self._people_scan_pause.clear()

    @Slot(result=list)
    def list_people(self) -> list:
        from app.mediamanager.db.people_repo import list_people

        try:
            return list_people(self.conn, include_unnamed=True)
        except Exception as exc:
            try:
                self._log(f"List people failed: {exc}")
            except Exception:
                pass
            return []

    @Slot(int, result=list)
    def list_person_faces(self, person_id: int) -> list:
        from app.mediamanager.db.people_repo import list_faces_for_person

        try:
            return list_faces_for_person(self.conn, int(person_id or 0))
        except Exception as exc:
            try:
                self._log(f"List person faces failed: {exc}")
            except Exception:
                pass
            return []

    @Slot(str, result=list)
    def list_media_people(self, path: str) -> list:
        from app.mediamanager.db.people_repo import list_people_for_media

        try:
            return list_people_for_media(self.conn, path)
        except Exception:
            return []

    @Slot(str, str, result=bool)
    def assign_media_person(self, path: str, person_name: str) -> bool:
        from app.mediamanager.db.people_repo import add_manual_face_assignment

        try:
            add_manual_face_assignment(self.conn, path, person_name, status="confirmed")
            self._clear_gallery_count_cache()
            self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
            return True
        except Exception as exc:
            try:
                self._log(f"Assign media person failed: {exc}")
            except Exception:
                pass
            return False

    @Slot(int, str, result=int)
    def name_person_group(self, person_id: int, person_name: str) -> int:
        from app.mediamanager.db.people_repo import name_person_group

        try:
            next_id = name_person_group(self.conn, int(person_id or 0), person_name)
            self._clear_gallery_count_cache()
            self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
            return int(next_id or 0)
        except Exception as exc:
            try:
                self._log(f"Name person group failed: {exc}")
            except Exception:
                pass
            return 0

    @Slot(int, result=bool)
    def confirm_person_group(self, person_id: int) -> bool:
        from app.mediamanager.db.people_repo import confirm_person_group

        try:
            ok = confirm_person_group(self.conn, int(person_id or 0))
            if ok:
                self._clear_gallery_count_cache()
                self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
            return bool(ok)
        except Exception as exc:
            try:
                self._log(f"Confirm person group failed: {exc}")
            except Exception:
                pass
            return False

    @Slot(int, str, result=bool)
    def assign_face_person(self, face_id: int, person_name: str) -> bool:
        from app.mediamanager.db.people_repo import assign_face_to_person

        try:
            ok = assign_face_to_person(self.conn, int(face_id or 0), person_name)
            if ok:
                self._clear_gallery_count_cache()
                self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
            return bool(ok)
        except Exception:
            return False

    @Slot(int, result=bool)
    def reject_face_person(self, face_id: int) -> bool:
        from app.mediamanager.db.people_repo import reject_face_from_person

        try:
            ok = reject_face_from_person(self.conn, int(face_id or 0))
            if ok:
                self._clear_gallery_count_cache()
                self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
            return bool(ok)
        except Exception:
            return False

    @Slot(int, result=bool)
    def ignore_face(self, face_id: int) -> bool:
        from app.mediamanager.db.people_repo import ignore_face

        try:
            ok = ignore_face(self.conn, int(face_id or 0))
            if ok:
                self._clear_gallery_count_cache()
                self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
            return bool(ok)
        except Exception:
            return False

    @Slot(list, result=int)
    def bootstrap_people_from_tags(self, paths: list | None = None) -> int:
        from app.mediamanager.db.people_repo import bootstrap_people_from_tags

        try:
            count = bootstrap_people_from_tags(self.conn, paths or None)
            if count:
                self._clear_gallery_count_cache()
                self.galleryFilterSensitiveMetadataChanged.emit()
                self.galleryScopeChanged.emit()
            return int(count or 0)
        except Exception as exc:
            try:
                self._log(f"People tag bootstrap failed: {exc}")
            except Exception:
                pass
            return 0

    @Slot(list, result=bool)
    def scan_faces_async(self, paths: list | None = None) -> bool:
        try:
            self._ensure_people_scan_state()
            if bool(self._people_scan_running):
                self._people_scan_debug("scan requested while another People scan is running")
                self._emit_people_scan_status("running", "People scan is already running.")
                return False
            self._people_scan_debug("scan requested")
            engine = str(self.settings.value("people/recognition_engine", "none", type=str) or "none").strip().lower()
            if engine != "insightface":
                self._people_scan_debug("recognition engine is disabled")
                self._emit_people_scan_status("error", "People recognition engine is disabled.")
                return False
            from app.mediamanager.ai_captioning.model_registry import INSIGHTFACE_MODEL_ID, model_spec

            spec = model_spec(INSIGHTFACE_MODEL_ID, "faces")
            status = self._local_ai_status_payload_for_spec(spec)
            self._people_scan_debug(f"status={status.get('state')} installed={status.get('installed')} runtime={status.get('runtime_python')} models={status.get('model_files_installed')}")
            if not bool(status.get("installed")):
                self._people_scan_debug("InsightFace is not installed")
                self._emit_people_scan_status("error", "InsightFace is not installed. Open AI Models Status and install it.")
                return False
            clean_paths = [str(path or "").strip() for path in list(paths or []) if str(path or "").strip()]
            if not clean_paths:
                clean_paths = self._people_scan_paths_from_current_scope()
                self._people_scan_debug(f"resolved {len(clean_paths)} files from current gallery scope")
            if not clean_paths:
                self._people_scan_debug("no media files were selected or found in current scope")
                self._emit_people_scan_status("error", "No media files were selected or found in the current gallery scope.")
                return False
            self._emit_people_scan_status("starting", f"Starting People scan for {len(clean_paths)} files...", current=0, total=len(clean_paths))
            self._people_scan_running = True
            threading.Thread(
                target=self._scan_faces_worker,
                args=(clean_paths,),
                daemon=True,
                name="people-insightface-scan",
            ).start()
            self._people_scan_debug(f"started with InsightFace for {len(clean_paths)} files")
            return True
        except Exception as exc:
            self._people_scan_debug(f"could not start: {exc}")
            self._emit_people_scan_status("error", f"People scan could not start: {exc}")
            return False

    @Slot(result=bool)
    def pause_people_scan(self) -> bool:
        self._ensure_people_scan_state()
        if not bool(self._people_scan_running):
            self._emit_people_scan_status("error", "No People scan is running.")
            return False
        self._people_scan_pause.set()
        self._people_scan_debug("pause requested")
        self._emit_people_scan_status("paused", "People scan paused.")
        return True

    @Slot(result=bool)
    def resume_people_scan(self) -> bool:
        self._ensure_people_scan_state()
        if not bool(self._people_scan_running):
            self._emit_people_scan_status("error", "No People scan is running.")
            return False
        self._people_scan_pause.clear()
        self._people_scan_debug("resume requested")
        self._emit_people_scan_status("running", "People scan resumed.")
        return True
