"""SQLite database for Wiki.js page-history tracking (Phase 2).

Records which source commit/tag a wikijs_create_page/update_page call was
based on, without ever writing that reference into the visible page content
(docs-wiki's "no version numbers in body text" rule stays intact).

Schema is ensured lazily on first real use (db_connection()), never at
import time — mirrors server._get_client()'s lazy-credential pattern, so
`import server` (tests, tooling) never touches the filesystem, and a DB
problem degrades page-history logging instead of taking down the whole
server (see tools/pages.py's try/except around history.log_page_change).
"""
from __future__ import annotations

import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Retry settings for SQLITE_BUSY on network/cloud-sync paths — covers only
# connection acquisition (see _connect_with_retry). A lock hit *during* a
# statement inside the `with db_connection() as conn:` body is intentionally
# left to propagate — a @contextmanager cannot safely retry its own body
# (the caller's code already ran), and callers that care (tools/pages.py)
# already treat any history-logging failure as non-fatal.
_BUSY_RETRY_COUNT = 5
_BUSY_RETRY_DELAY = 0.2  # seconds between retries

_NETWORK_PATH_HINTS = (
    "/mnt/", "/media/", "/net/", "/Volumes/",
    "Dropbox", "OneDrive", "Google Drive", "iCloud", "Mobile Documents", "My Drive",
)


def get_db_path() -> Path:
    path = Path.home() / ".wikijs-plugin" / "wikijs-plugin.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _is_network_path(path: Path) -> bool:
    """Heuristic: flag paths that look like a network mount or cloud-sync folder."""
    path_str = str(path)
    return any(hint in path_str for hint in _NETWORK_PATH_HINTS)


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    timeout = 30.0 if _is_network_path(db_path) else 5.0
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _connect_with_retry() -> sqlite3.Connection:
    """Acquire a connection, retrying only SQLITE_BUSY during connect()/PRAGMA."""
    last_exc: Exception | None = None
    for attempt in range(_BUSY_RETRY_COUNT):
        try:
            return get_connection()
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc).lower():
                last_exc = exc
                if attempt < _BUSY_RETRY_COUNT - 1:
                    print(
                        f"[wikijs-plugin] DB locked (attempt {attempt + 1}/{_BUSY_RETRY_COUNT}), retrying...",
                        file=sys.stderr,
                    )
                    time.sleep(_BUSY_RETRY_DELAY * (attempt + 1))
            else:
                raise
    raise last_exc  # type: ignore[misc]


# Bump when page_history's shape changes and add a migration branch below.
# CREATE TABLE/INDEX IF NOT EXISTS silently no-ops on a DB whose definition
# has since changed — PRAGMA user_version is what lets a future _ensure_schema
# actually detect "this file predates schema N" instead of assuming IF NOT
# EXISTS covers evolution (it only covers absence).
_SCHEMA_VERSION = 2


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Per-file idempotent: checks PRAGMA user_version on THIS connection's
    database file, not a process-wide flag — a Python-level "already ran"
    flag would go stale the moment get_db_path() is monkeypatched to a
    different file (e.g. between tests), silently skipping schema creation
    on a brand-new file. Reading a PRAGMA is cheap enough to do on every
    db_connection() call."""
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    if current_version >= _SCHEMA_VERSION:
        return
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS page_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                page_path   TEXT    NOT NULL,
                locale      TEXT    NOT NULL,
                changed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                source_repo TEXT    NOT NULL DEFAULT '',
                source_ref  TEXT    NOT NULL DEFAULT '',
                summary     TEXT    NOT NULL DEFAULT '',
                verified    INTEGER NOT NULL DEFAULT 0,
                page_updated_at TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_page_history_path
                ON page_history(page_path, locale, changed_at DESC);
        """)
        # v1 -> v2: a source_ref written by v1 means "written at", never "checked
        # against the code", so existing rows keep verified = 0. page_updated_at
        # records the Wiki.js updatedAt a page was verified at, so a later edit
        # outside the gated flow can be detected.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(page_history)")}
        for name, definition in _V2_COLUMNS:
            if name not in columns:
                _add_column_tolerating_race(conn, name, definition)
        conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")


_V2_COLUMNS = (
    ("verified", "INTEGER NOT NULL DEFAULT 0"),
    ("page_updated_at", "TEXT NOT NULL DEFAULT ''"),
)


def _add_column_tolerating_race(conn: sqlite3.Connection, name: str, definition: str) -> None:
    """ALTER TABLE ADD COLUMN, treating 'duplicate column name' as success.

    Python's sqlite3 does not wrap DDL in a transaction, so the table_info
    check and the ALTER are not atomic. Two MCP processes migrating at the same
    moment can both pass the check; the loser's ALTER then finds the column
    already added by the winner, which is the state it wanted.
    """
    try:
        conn.execute(f"ALTER TABLE page_history ADD COLUMN {name} {definition}")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


@contextmanager
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager: retries connection acquisition on SQLITE_BUSY, then
    ensures the schema exists before handing the connection to the caller."""
    conn = _connect_with_retry()
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Explicitly ensure the schema exists.

    Not called at import time (see module docstring) — kept for tests/tooling
    that want an up-front guarantee before making assertions. Ordinary
    runtime code never needs to call this: db_connection() already ensures
    the schema on every use.
    """
    with db_connection():
        pass
