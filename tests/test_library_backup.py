import sqlite3
import shutil
import uuid
import zipfile
from pathlib import Path

from native.mediamanagerx_app.library_backup import (
    LibraryBackupOptions,
    LibraryRestoreOptions,
    create_library_backup,
    read_library_backup_manifest,
    restore_library_backup,
)


def _workspace_tmp() -> Path:
    path = Path("tmp") / "library-backup-tests" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_sqlite(path: Path, table: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(f"CREATE TABLE {table} (value TEXT)")
        conn.execute(f"INSERT INTO {table} (value) VALUES (?)", (value,))
        conn.commit()
    finally:
        conn.close()


def test_library_backup_exports_supported_runtime_data():
    tmp_path = _workspace_tmp()
    try:
        _test_library_backup_exports_supported_runtime_data(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _test_library_backup_exports_supported_runtime_data(tmp_path):
    appdata = tmp_path / "appdata"
    appdata.mkdir()
    _make_sqlite(appdata / "medialens.db", "media", "db-ok")
    _make_sqlite(appdata / "recycle_bin.sqlite", "recycle", "recycle-ok")
    (appdata / "RecycleBin").mkdir()
    (appdata / "RecycleBin" / "archived.bin").write_bytes(b"retained")
    (appdata / "thumbs").mkdir()
    (appdata / "thumbs" / "thumb.jpg").write_bytes(b"thumb")
    (appdata / "settings.ini").write_text("[ui]\ntheme_mode=dark\n", encoding="utf-8")
    (appdata / "local_ai_models" / "model-a").mkdir(parents=True)
    (appdata / "local_ai_models" / "model-a" / "weights.bin").write_bytes(b"model")
    (appdata / "ai-runtimes" / "runtime-a").mkdir(parents=True)
    (appdata / "ai-runtimes" / "runtime-a" / "python.exe").write_bytes(b"runtime")
    (appdata / "python" / "cpython").mkdir(parents=True)
    (appdata / "python" / "cpython" / "python.exe").write_bytes(b"python")
    (appdata / "python-bootstrap").mkdir()
    (appdata / "python-bootstrap" / "python.nupkg").write_bytes(b"bootstrap")
    (appdata / "mediamanagerx.db").write_text("legacy", encoding="utf-8")
    (appdata / "app.log.legacy-1").write_text("legacy log", encoding="utf-8")

    archive = tmp_path / "backup.zip"
    result = create_library_backup(
        archive,
        options=LibraryBackupOptions(
            include_settings=True,
            include_thumbs=False,
            include_local_ai_models=True,
            include_ai_runtimes=True,
        ),
        appdata_dir=appdata,
    )

    assert result.included["database"] is True
    assert result.included["recycle_bin"] is True
    assert result.included["recycle_bin_files"] is True
    assert result.included["settings"] is True
    assert result.included["thumbs"] is False
    assert result.included["local_ai_models"] is True
    assert result.included["ai_runtimes"] is True
    assert result.included["python_runtime"] is True
    assert result.included["python_bootstrap"] is True
    manifest = read_library_backup_manifest(archive)
    assert manifest["schema_version"] == 1
    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
    assert "database/medialens.db" in names
    assert "recycle/recycle_bin.sqlite" in names
    assert "recycle/RecycleBin/archived.bin" in names
    assert "settings/settings.ini" in names
    assert "thumbs/thumb.jpg" not in names
    assert "ai/local_ai_models/model-a/weights.bin" in names
    assert "ai/ai-runtimes/runtime-a/python.exe" in names
    assert "ai/python/cpython/python.exe" in names
    assert "ai/python-bootstrap/python.nupkg" in names
    assert all("mediamanagerx" not in name for name in names)
    assert all("legacy" not in name for name in names)


def test_library_backup_restore_overwrites_current_supported_data():
    tmp_path = _workspace_tmp()
    try:
        _test_library_backup_restore_overwrites_current_supported_data(tmp_path)
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def _test_library_backup_restore_overwrites_current_supported_data(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _make_sqlite(source / "medialens.db", "media", "imported")
    _make_sqlite(source / "recycle_bin.sqlite", "recycle", "imported-recycle")
    (source / "RecycleBin").mkdir()
    (source / "RecycleBin" / "archived.bin").write_bytes(b"imported")
    (source / "settings.ini").write_text("[ui]\ntheme_mode=light\n", encoding="utf-8")
    (source / "thumbs").mkdir()
    (source / "thumbs" / "thumb.jpg").write_bytes(b"imported-thumb")
    (source / "local_ai_models" / "model-a").mkdir(parents=True)
    (source / "local_ai_models" / "model-a" / "weights.bin").write_bytes(b"imported-model")
    (source / "ai-runtimes" / "runtime-a").mkdir(parents=True)
    (source / "ai-runtimes" / "runtime-a" / "python.exe").write_bytes(b"imported-runtime")
    (source / "python" / "cpython").mkdir(parents=True)
    (source / "python" / "cpython" / "python.exe").write_bytes(b"imported-python")
    (source / "python-bootstrap").mkdir()
    (source / "python-bootstrap" / "python.nupkg").write_bytes(b"imported-bootstrap")
    archive = tmp_path / "backup.zip"
    create_library_backup(
        archive,
        options=LibraryBackupOptions(
            include_settings=True,
            include_thumbs=True,
            include_local_ai_models=True,
            include_ai_runtimes=True,
        ),
        appdata_dir=source,
    )

    target = tmp_path / "target"
    target.mkdir()
    _make_sqlite(target / "medialens.db", "media", "old")
    (target / "settings.ini").write_text("[ui]\ntheme_mode=old\n", encoding="utf-8")

    result = restore_library_backup(
        archive,
        options=LibraryRestoreOptions(
            include_settings=True,
            include_thumbs=True,
            include_local_ai_models=True,
            include_ai_runtimes=True,
            backup_existing=True,
        ),
        appdata_dir=target,
    )

    assert result.restored["database"] is True
    assert result.restored["recycle_bin"] is True
    assert result.restored["recycle_bin_files"] is True
    assert result.restored["settings"] is True
    assert result.restored["thumbs"] is True
    assert result.restored["local_ai_models"] is True
    assert result.restored["ai_runtimes"] is True
    assert result.restored["python_runtime"] is True
    assert result.restored["python_bootstrap"] is True
    assert result.existing_backup_dir is not None
    assert (result.existing_backup_dir / "medialens.db").exists()
    assert (target / "RecycleBin" / "archived.bin").read_bytes() == b"imported"
    assert (target / "thumbs" / "thumb.jpg").read_bytes() == b"imported-thumb"
    assert (target / "local_ai_models" / "model-a" / "weights.bin").read_bytes() == b"imported-model"
    assert (target / "ai-runtimes" / "runtime-a" / "python.exe").read_bytes() == b"imported-runtime"
    assert (target / "python" / "cpython" / "python.exe").read_bytes() == b"imported-python"
    assert (target / "python-bootstrap" / "python.nupkg").read_bytes() == b"imported-bootstrap"
    assert "theme_mode=light" in (target / "settings.ini").read_text(encoding="utf-8")

    conn = sqlite3.connect(str(target / "medialens.db"))
    try:
        value = conn.execute("SELECT value FROM media").fetchone()[0]
    finally:
        conn.close()
    assert value == "imported"
