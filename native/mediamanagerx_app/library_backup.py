from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from native.mediamanagerx_app.common import __version__
from native.mediamanagerx_app.runtime_paths import _appdata_runtime_dir, _runtime_db_path


BACKUP_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"


@dataclass
class LibraryBackupOptions:
    include_recycle_bin: bool = True
    include_settings: bool = True
    include_thumbs: bool = False
    include_local_ai_models: bool = False
    include_ai_runtimes: bool = False


@dataclass
class LibraryBackupResult:
    archive_path: Path
    included: dict[str, bool]
    file_count: int


@dataclass
class LibraryRestoreOptions:
    include_recycle_bin: bool = True
    include_settings: bool = True
    include_thumbs: bool = False
    include_local_ai_models: bool = False
    include_ai_runtimes: bool = False
    merge_existing: bool = False
    backup_existing: bool = True


@dataclass
class LibraryRestoreResult:
    restored: dict[str, bool]
    existing_backup_dir: Path | None


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _sqlite_backup(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()
    return True


def _copy_file(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(target))
    return True


def _copy_dir(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_dir():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(source), str(target), dirs_exist_ok=True)
    return True


def _replace_file(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    shutil.copy2(str(source), str(target))
    return True


def _replace_dir(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_dir():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(str(target))
    shutil.copytree(str(source), str(target))
    return True


def _merge_dir(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_dir():
        return False
    target.mkdir(parents=True, exist_ok=True)
    copied = False
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        out = target / rel
        if path.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            continue
        shutil.copy2(str(path), str(out))
        copied = True
    return copied or any(source.iterdir())


def _merge_recycle_bin_db(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    if not target.exists():
        return _replace_file(source, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(target))
    try:
        dst.execute(
            """
            CREATE TABLE IF NOT EXISTS recycle_bin (
                id TEXT PRIMARY KEY,
                original_path TEXT,
                archived_name TEXT,
                deleted_at DATETIME,
                expires_at DATETIME
            )
            """
        )
        rows = src.execute(
            "SELECT id, original_path, archived_name, deleted_at, expires_at FROM recycle_bin"
        ).fetchall()
        dst.executemany(
            """
            INSERT OR IGNORE INTO recycle_bin (id, original_path, archived_name, deleted_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        dst.commit()
        return True
    finally:
        dst.close()
        src.close()


def _zip_dir(source_dir: Path, archive_path: Path) -> int:
    count = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if not path.is_file():
                continue
            zf.write(str(path), path.relative_to(source_dir).as_posix())
            count += 1
    return count


def _safe_extract(archive_path: Path, target_dir: Path) -> None:
    root = target_dir.resolve()
    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            out_path = (target_dir / info.filename).resolve()
            if root != out_path and root not in out_path.parents:
                raise ValueError(f"Archive contains an unsafe path: {info.filename}")
        zf.extractall(str(target_dir))


def read_library_backup_manifest(archive_path: str | Path) -> dict:
    archive = Path(archive_path)
    with zipfile.ZipFile(archive, "r") as zf:
        try:
            data = zf.read(MANIFEST_NAME)
        except KeyError as exc:
            raise ValueError("This is not a MediaLens library backup archive.") from exc
    manifest = json.loads(data.decode("utf-8"))
    if int(manifest.get("schema_version") or 0) != BACKUP_SCHEMA_VERSION:
        raise ValueError("This MediaLens backup uses an unsupported archive format.")
    return manifest


def create_library_backup(
    destination: str | Path,
    *,
    options: LibraryBackupOptions | None = None,
    appdata_dir: Path | None = None,
) -> LibraryBackupResult:
    opts = options or LibraryBackupOptions()
    appdata = appdata_dir or _appdata_runtime_dir()
    archive_path = Path(destination)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    included = {
        "database": False,
        "recycle_bin": False,
        "recycle_bin_files": False,
        "settings": False,
        "thumbs": False,
        "local_ai_models": False,
        "ai_runtimes": False,
        "python_runtime": False,
        "python_bootstrap": False,
    }
    created_utc = datetime.now(timezone.utc).isoformat()

    with tempfile.TemporaryDirectory(prefix="medialens-library-export-") as tmp_name:
        payload = Path(tmp_name) / "payload"
        payload.mkdir(parents=True, exist_ok=True)

        included["database"] = _sqlite_backup(_runtime_db_path(appdata), payload / "database" / "medialens.db")
        if opts.include_recycle_bin:
            included["recycle_bin"] = _sqlite_backup(appdata / "recycle_bin.sqlite", payload / "recycle" / "recycle_bin.sqlite")
            included["recycle_bin_files"] = _copy_dir(appdata / "RecycleBin", payload / "recycle" / "RecycleBin")
        if opts.include_settings:
            included["settings"] = _copy_file(appdata / "settings.ini", payload / "settings" / "settings.ini")
        if opts.include_thumbs:
            included["thumbs"] = _copy_dir(appdata / "thumbs", payload / "thumbs")
        if opts.include_local_ai_models:
            included["local_ai_models"] = _copy_dir(appdata / "local_ai_models", payload / "ai" / "local_ai_models")
        if opts.include_ai_runtimes:
            included["ai_runtimes"] = _copy_dir(appdata / "ai-runtimes", payload / "ai" / "ai-runtimes")
            included["python_runtime"] = _copy_dir(appdata / "python", payload / "ai" / "python")
            included["python_bootstrap"] = _copy_dir(appdata / "python-bootstrap", payload / "ai" / "python-bootstrap")

        manifest = {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "app": "MediaLens",
            "app_version": __version__,
            "created_utc": created_utc,
            "includes": included,
            "notes": [
                "Legacy MediaManagerX files and debug logs are intentionally excluded.",
                "Downloaded models and AI runtimes are included only when selected.",
                "Importing this archive always restores the database; optional data can be merged or replaced.",
            ],
        }
        (payload / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        file_count = _zip_dir(payload, archive_path)

    return LibraryBackupResult(archive_path=archive_path, included=included, file_count=file_count)


def _backup_existing_supported_files(appdata: Path) -> Path | None:
    existing = [
        _runtime_db_path(appdata),
        appdata / "recycle_bin.sqlite",
        appdata / "settings.ini",
        appdata / "RecycleBin",
        appdata / "thumbs",
        appdata / "local_ai_models",
        appdata / "ai-runtimes",
        appdata / "python",
        appdata / "python-bootstrap",
    ]
    if not any(path.exists() for path in existing):
        return None
    backup_dir = appdata / "import-backups" / f"before-import-{_utc_stamp()}-{int(time.time())}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    _copy_file(_runtime_db_path(appdata), backup_dir / "medialens.db")
    _copy_file(appdata / "recycle_bin.sqlite", backup_dir / "recycle_bin.sqlite")
    _copy_file(appdata / "settings.ini", backup_dir / "settings.ini")
    _copy_dir(appdata / "RecycleBin", backup_dir / "RecycleBin")
    _copy_dir(appdata / "thumbs", backup_dir / "thumbs")
    _copy_dir(appdata / "local_ai_models", backup_dir / "local_ai_models")
    _copy_dir(appdata / "ai-runtimes", backup_dir / "ai-runtimes")
    _copy_dir(appdata / "python", backup_dir / "python")
    _copy_dir(appdata / "python-bootstrap", backup_dir / "python-bootstrap")
    return backup_dir


def restore_library_backup(
    archive: str | Path,
    *,
    options: LibraryRestoreOptions | None = None,
    appdata_dir: Path | None = None,
) -> LibraryRestoreResult:
    opts = options or LibraryRestoreOptions()
    appdata = appdata_dir or _appdata_runtime_dir()
    appdata.mkdir(parents=True, exist_ok=True)
    archive_path = Path(archive)

    restored = {
        "database": False,
        "recycle_bin": False,
        "recycle_bin_files": False,
        "settings": False,
        "thumbs": False,
        "local_ai_models": False,
        "ai_runtimes": False,
        "python_runtime": False,
        "python_bootstrap": False,
    }
    with tempfile.TemporaryDirectory(prefix="medialens-library-import-") as tmp_name:
        extracted = Path(tmp_name) / "extract"
        extracted.mkdir(parents=True, exist_ok=True)
        _safe_extract(archive_path, extracted)
        manifest = read_library_backup_manifest(archive_path)
        includes = dict(manifest.get("includes") or {})

        existing_backup_dir = _backup_existing_supported_files(appdata) if opts.backup_existing else None

        restored["database"] = _replace_file(extracted / "database" / "medialens.db", _runtime_db_path(appdata))
        if opts.include_recycle_bin and includes.get("recycle_bin"):
            if opts.merge_existing:
                restored["recycle_bin"] = _merge_recycle_bin_db(extracted / "recycle" / "recycle_bin.sqlite", appdata / "recycle_bin.sqlite")
            else:
                restored["recycle_bin"] = _replace_file(extracted / "recycle" / "recycle_bin.sqlite", appdata / "recycle_bin.sqlite")
        if opts.include_recycle_bin and includes.get("recycle_bin_files"):
            if opts.merge_existing:
                restored["recycle_bin_files"] = _merge_dir(extracted / "recycle" / "RecycleBin", appdata / "RecycleBin")
            else:
                restored["recycle_bin_files"] = _replace_dir(extracted / "recycle" / "RecycleBin", appdata / "RecycleBin")
        if opts.include_settings and includes.get("settings"):
            restored["settings"] = _replace_file(extracted / "settings" / "settings.ini", appdata / "settings.ini")
        if opts.include_thumbs and includes.get("thumbs"):
            restored["thumbs"] = (
                _merge_dir(extracted / "thumbs", appdata / "thumbs")
                if opts.merge_existing
                else _replace_dir(extracted / "thumbs", appdata / "thumbs")
            )
        if opts.include_local_ai_models and includes.get("local_ai_models"):
            restored["local_ai_models"] = (
                _merge_dir(extracted / "ai" / "local_ai_models", appdata / "local_ai_models")
                if opts.merge_existing
                else _replace_dir(extracted / "ai" / "local_ai_models", appdata / "local_ai_models")
            )
        if opts.include_ai_runtimes:
            if includes.get("ai_runtimes"):
                restored["ai_runtimes"] = (
                    _merge_dir(extracted / "ai" / "ai-runtimes", appdata / "ai-runtimes")
                    if opts.merge_existing
                    else _replace_dir(extracted / "ai" / "ai-runtimes", appdata / "ai-runtimes")
                )
            if includes.get("python_runtime"):
                restored["python_runtime"] = (
                    _merge_dir(extracted / "ai" / "python", appdata / "python")
                    if opts.merge_existing
                    else _replace_dir(extracted / "ai" / "python", appdata / "python")
                )
            if includes.get("python_bootstrap"):
                restored["python_bootstrap"] = (
                    _merge_dir(extracted / "ai" / "python-bootstrap", appdata / "python-bootstrap")
                    if opts.merge_existing
                    else _replace_dir(extracted / "ai" / "python-bootstrap", appdata / "python-bootstrap")
                )

    return LibraryRestoreResult(restored=restored, existing_backup_dir=existing_backup_dir)
