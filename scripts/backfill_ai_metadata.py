import argparse
import json
from pathlib import Path

from app.mediamanager.db.connect import connect_db
from app.mediamanager.metadata.persistence import backfill_ai_metadata_for_media_rows


def _select_rows(conn, media_type: str | None, limit: int | None, path_contains: str | None) -> list[dict]:
    sql = "SELECT id, path, media_type FROM media_items"
    clauses = []
    params = []
    if media_type:
        clauses.append("media_type = ?")
        params.append(media_type)
    if path_contains:
        clauses.append("path LIKE ?")
        params.append(f"%{path_contains.lower()}%")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql, params).fetchall()
    return [{"id": row[0], "path": row[1], "media_type": row[2]} for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill AI metadata tables from existing media_items rows.")
    parser.add_argument("--db", required=True, help="Path to the MediaManagerX sqlite database")
    parser.add_argument("--media-type", default="image", help="Optional media_type filter (default: image)")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for test runs")
    parser.add_argument("--path-contains", default=None, help="Optional substring filter applied to normalized path")
    parser.add_argument("--out", default=None, help="Optional JSON report output path")
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = connect_db(str(db_path))
    try:
        rows = _select_rows(conn, args.media_type, args.limit, args.path_contains)
        results = backfill_ai_metadata_for_media_rows(conn, rows)
    finally:
        conn.close()

    summary = {
        "db": str(db_path),
        "row_count": len(results),
        "ok": sum(1 for item in results if item["status"] == "ok"),
        "missing": sum(1 for item in results if item["status"] == "missing"),
        "error": sum(1 for item in results if item["status"] == "error"),
        "results": results,
    }

    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
