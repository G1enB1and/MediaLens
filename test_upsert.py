import sqlite3
import traceback
from app.mediamanager.db.metadata_repo import upsert_media_metadata

def main():
    conn = sqlite3.connect('C:\\Users\\glenb\\AppData\\Roaming\\G1enB1and\\MediaManagerX\\mediamanagerx.db')
    try:
        upsert_media_metadata(conn, 1, "test title", "test desc", "test notes", "test tags", "test comm", "test ai", "test negative", "test params")
        print("Success")
    except Exception as e:
        print("Error:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
