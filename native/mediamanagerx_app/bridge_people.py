from __future__ import annotations

from native.mediamanagerx_app.common import *


class BridgePeopleMixin:
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
        completed = subprocess.run(command, **popen_kwargs)
        combined = "\n".join(part for part in (completed.stdout, completed.stderr) if str(part or "").strip())
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
        scanned = 0
        detected = 0
        errors = 0
        for raw_path in paths:
            try:
                media_path = Path(str(raw_path or ""))
                if not media_path.is_file():
                    continue
                source_path = self._local_ai_source_path(media_path)
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
            except Exception as exc:
                errors += 1
                try:
                    self._log(f"People scan failed for {raw_path}: {exc}")
                except Exception:
                    pass
        try:
            self._log(f"People scan finished. Files scanned: {scanned}; faces detected: {detected}; errors: {errors}.")
            self._clear_gallery_count_cache()
            self.galleryFilterSensitiveMetadataChanged.emit()
            self.galleryScopeChanged.emit()
        except Exception:
            pass

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
            engine = str(self.settings.value("people/recognition_engine", "none", type=str) or "none").strip().lower()
            if engine != "insightface":
                self._log("People scan requested, but People recognition engine is disabled.")
                return False
            from app.mediamanager.ai_captioning.model_registry import INSIGHTFACE_MODEL_ID, model_spec

            status = self._local_ai_status_payload_for_spec(model_spec(INSIGHTFACE_MODEL_ID, "faces"))
            if not bool(status.get("installed")):
                self._log("People scan requested, but InsightFace is not installed.")
                return False
            clean_paths = [str(path or "").strip() for path in list(paths or []) if str(path or "").strip()]
            if not clean_paths:
                self._log("People scan requested, but no media files were selected.")
                return False
            threading.Thread(
                target=self._scan_faces_worker,
                args=(clean_paths,),
                daemon=True,
                name="people-insightface-scan",
            ).start()
            self._log(f"People scan started with InsightFace for {len(clean_paths)} files.")
            return True
        except Exception as exc:
            try:
                self._log(f"People scan could not start: {exc}")
            except Exception:
                pass
            return False
