from __future__ import annotations

from native.mediamanagerx_app.common import *


class BridgePeopleMixin:
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
            self._log("People scan requested. InsightFace runtime is installed, but face extraction is not implemented yet.")
        except Exception:
            pass
        return False
