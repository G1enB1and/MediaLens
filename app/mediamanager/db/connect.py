from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.mediamanager.db.migrations import (
    _ensure_is_hidden_columns,
    _ensure_media_item_date_columns,
    _ensure_media_metadata_columns,
    init_db,
)


# Pragmas applied to every per-thread connection.
# WAL has been unreliable in this Windows packaging/runtime environment and
# can report success before later writes fail with disk I/O errors, so we
# stick with MEMORY journaling. busy_timeout lets a thread wait briefly for
# a peer's write to finish instead of erroring out with "database is locked".
_CONNECTION_PRAGMAS = (
    "PRAGMA foreign_keys=ON;",
    "PRAGMA journal_mode=MEMORY;",
    "PRAGMA busy_timeout=5000;",
)


class ThreadLocalConnection:
    """Proxy that gives each thread its own sqlite3.Connection to the same file.

    Python's sqlite3 module is not safe for truly concurrent use of a single
    Connection even with check_same_thread=False — calls must be serialized or
    you get SQLITE_MISUSE ("bad parameter or other API misuse") errors. This
    proxy hands each thread its own Connection and relies on SQLite's own
    file-level locking to coordinate writes, which eliminates the race without
    adding a Python-level lock that would stall the UI during background scans.

    All common Connection methods (cursor, execute, executemany, executescript,
    commit, rollback, close) are forwarded to the current thread's connection.
    Any other attribute is forwarded via __getattr__. `with conn:` also works.
    """

    def __init__(self, db_path: str) -> None:
        # Use object.__setattr__ so these bypass any future __setattr__ hook.
        object.__setattr__(self, "_db_path", str(db_path))
        object.__setattr__(self, "_local", threading.local())
        object.__setattr__(self, "_registry_lock", threading.Lock())
        object.__setattr__(self, "_registry", [])

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            for pragma in _CONNECTION_PRAGMAS:
                conn.execute(pragma)
            self._local.conn = conn
            with self._registry_lock:
                self._registry.append(conn)
        return conn

    def close_all(self) -> None:
        """Close every connection this proxy has ever handed out.

        Call on app shutdown. Individual threads whose connections are closed
        from under them will get errors on next use; only invoke once nothing
        else is going to touch the DB.
        """
        with self._registry_lock:
            connections = list(self._registry)
            self._registry.clear()
        for c in connections:
            try:
                c.close()
            except Exception:
                pass

    # ---- Hot-path forwards (explicit to avoid __getattr__ overhead) ----

    def cursor(self, *args, **kwargs):
        return self._conn().cursor(*args, **kwargs)

    def execute(self, *args, **kwargs):
        return self._conn().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        return self._conn().executemany(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        return self._conn().executescript(*args, **kwargs)

    def commit(self):
        return self._conn().commit()

    def rollback(self):
        return self._conn().rollback()

    def close(self):
        """Close this thread's connection only. Use close_all() for full shutdown."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    # ---- Context-manager support so `with conn:` works ----

    def __enter__(self):
        return self._conn().__enter__()

    def __exit__(self, *args):
        return self._conn().__exit__(*args)

    # ---- Catch-all forward for any attribute we didn't define explicitly ----

    def __getattr__(self, name):
        # __getattr__ is only called when normal attribute lookup fails, so
        # internal attributes set via object.__setattr__ never route here.
        return getattr(self._conn(), name)


def connect_db(db_path: str) -> ThreadLocalConnection:
    """Open the app DB and return a thread-safe connection proxy.

    The returned object quacks like a sqlite3.Connection for all call sites in
    this codebase (execute/cursor/commit/etc.) but internally gives each thread
    its own real Connection. SQLite handles concurrent reads and serializes
    writes at the file level.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    init_db(str(path))

    proxy = ThreadLocalConnection(str(path))
    # Run schema migrations on the main thread's connection before returning.
    main_conn = proxy._conn()
    _ensure_media_metadata_columns(main_conn)
    _ensure_is_hidden_columns(main_conn)
    _ensure_media_item_date_columns(main_conn)
    main_conn.commit()
    return proxy
