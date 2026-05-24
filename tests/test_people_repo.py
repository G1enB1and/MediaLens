from __future__ import annotations

from app.mediamanager.db.migrations import init_db
from app.mediamanager.db.media_repo import add_media_item, list_media_in_scope
from app.mediamanager.db.people_repo import (
    add_manual_face_assignment,
    list_people,
    list_people_for_media,
)


def test_manual_people_assignment_is_queryable(tmp_path):
    db_path = tmp_path / "people.sqlite"
    init_db(str(db_path))
    import sqlite3

    db = sqlite3.connect(str(db_path))
    media_path = tmp_path / "amy.jpg"
    media_path.write_bytes(b"fake")
    add_media_item(db, str(media_path), "image")

    face_id = add_manual_face_assignment(db, str(media_path), "Amy Rollins")

    people = list_people(db)
    assert people[0]["display_name"] == "Amy Rollins"
    assert people[0]["file_count"] == 1
    assert people[0]["face_count"] == 1

    media_people = list_people_for_media(db, str(media_path))
    assert media_people == [
        {
            "face_id": face_id,
            "person_id": people[0]["id"],
            "display_name": "Amy Rollins",
            "is_confirmed": True,
            "status": "confirmed",
            "match_confidence": 1.0,
        }
    ]

    rows = list_media_in_scope(db, [str(tmp_path)])
    assert rows[0]["people_names"] == "Amy Rollins"
