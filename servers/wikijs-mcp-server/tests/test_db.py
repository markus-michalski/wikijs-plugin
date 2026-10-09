"""Tests for the page-history SQLite database."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

# Imported once at module-collection time — later per-test monkeypatching of
# tools.db.get_db_path (see conftest.py's autouse fixture) rebinds the module
# attribute, not this already-bound name, so it stays the real implementation.
import tools.db as db_module
from tools.db import db_connection, get_db_path, init_db


def test_init_db_creates_page_history_table():
    with db_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='page_history'"
        ).fetchone()
    assert row is not None


def test_page_history_table_has_expected_columns():
    with db_connection() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(page_history)").fetchall()}
    assert cols == {
        "id", "page_path", "locale", "changed_at", "source_repo", "source_ref", "summary",
        "verified", "page_updated_at",
    }


_V1_TABLE = """
    CREATE TABLE page_history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        page_path   TEXT    NOT NULL,
        locale      TEXT    NOT NULL,
        changed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
        source_repo TEXT    NOT NULL DEFAULT '',
        source_ref  TEXT    NOT NULL DEFAULT '',
        summary     TEXT    NOT NULL DEFAULT ''
    );
    INSERT INTO page_history (page_path, locale, source_ref) VALUES ('old/page', 'de', 'abc123');
"""


def test_unversioned_db_with_existing_table_migrates(monkeypatch, tmp_path):
    """user_version 0 with a page_history table already present (DB created
    before versioning existed) takes the same migration path as v1."""
    legacy = tmp_path / "unversioned.db"
    raw = sqlite3.connect(legacy)
    raw.executescript(_V1_TABLE)
    raw.commit()
    raw.close()
    monkeypatch.setattr(db_module, "get_db_path", lambda: legacy)

    with db_connection() as conn:
        row = conn.execute("SELECT source_ref, verified, page_updated_at FROM page_history").fetchone()
    assert (row["source_ref"], row["verified"], row["page_updated_at"]) == ("abc123", 0, "")


def test_migration_tolerates_a_concurrent_process_adding_the_columns(monkeypatch, tmp_path):
    """Two MCP processes can both read a v1 schema and both run ALTER TABLE.
    The loser must treat 'duplicate column name' as success instead of failing
    its first history call."""
    racing = tmp_path / "racing.db"
    raw = sqlite3.connect(racing)
    raw.executescript(_V1_TABLE)
    raw.execute("ALTER TABLE page_history ADD COLUMN verified INTEGER NOT NULL DEFAULT 0")
    raw.execute("ALTER TABLE page_history ADD COLUMN page_updated_at TEXT NOT NULL DEFAULT ''")
    raw.execute("PRAGMA user_version = 1")
    raw.commit()
    raw.close()

    class StaleColumnReads:
        """Proxy whose PRAGMA table_info still shows the pre-migration columns."""

        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, *args):
            if sql.strip().upper().startswith("PRAGMA TABLE_INFO"):
                return iter([{"name": n} for n in ("id", "page_path", "locale", "changed_at",
                                                     "source_repo", "source_ref", "summary")])
            return self._conn.execute(sql, *args)

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def __enter__(self):
            return self._conn.__enter__()

        def __exit__(self, *exc):
            return self._conn.__exit__(*exc)

    conn = sqlite3.connect(racing)
    conn.row_factory = sqlite3.Row
    try:
        db_module._ensure_schema(StaleColumnReads(conn))  # must not raise
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    finally:
        conn.close()


def test_existing_rows_are_unverified_after_migration_from_v1(monkeypatch, tmp_path):
    """A v1 DB (written-at refs, no verified column) must migrate in place and
    keep its rows as unverified: an old source_ref says where a page was
    written, not that it was checked against the code."""
    legacy = tmp_path / "legacy.db"
    raw = sqlite3.connect(legacy)
    raw.executescript("""
        CREATE TABLE page_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            page_path   TEXT    NOT NULL,
            locale      TEXT    NOT NULL,
            changed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            source_repo TEXT    NOT NULL DEFAULT '',
            source_ref  TEXT    NOT NULL DEFAULT '',
            summary     TEXT    NOT NULL DEFAULT ''
        );
        INSERT INTO page_history (page_path, locale, source_ref) VALUES ('old/page', 'de', 'abc123');
        PRAGMA user_version = 1;
    """)
    raw.commit()
    raw.close()
    monkeypatch.setattr(db_module, "get_db_path", lambda: legacy)

    with db_connection() as conn:
        row = conn.execute("SELECT source_ref, verified, page_updated_at FROM page_history").fetchone()
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert row["source_ref"] == "abc123"
    assert row["verified"] == 0
    assert row["page_updated_at"] == ""
    assert version == 2


def test_init_db_is_idempotent():
    init_db()
    init_db()  # must not raise
    with db_connection() as conn:
        tables = conn.execute(
            "SELECT count(*) as n FROM sqlite_master WHERE type='table' AND name='page_history'"
        ).fetchone()
    assert tables["n"] == 1


def test_schema_version_is_recorded():
    """PRAGMA user_version must be set once the schema exists — the hook
    future migrations (Phase 3+) need to detect an out-of-date DB. Without
    this, CREATE TABLE/INDEX IF NOT EXISTS silently no-ops on a DB whose
    definition has since changed, with no way to even notice."""
    with db_connection() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version >= 2


def test_wal_mode_enabled():
    with db_connection() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_db_connection_yields_row_factory():
    with db_connection() as conn:
        assert conn.row_factory is sqlite3.Row


def test_db_connection_does_not_retry_the_callers_body():
    """Regression test: a lock error raised *inside* the `with db_connection()`
    body (e.g. during an INSERT, not during connect()) must propagate as its
    real sqlite3.OperationalError, not get swallowed by a retry loop that
    tries to re-enter an already-exhausted generator (which raises an
    unrelated RuntimeError with zero diagnostic value)."""
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        with db_connection():
            raise sqlite3.OperationalError("database is locked")


def test_get_db_path_creates_parent_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = get_db_path()
    assert path.parent.is_dir()
    assert path == tmp_path / ".wikijs-plugin" / "wikijs-plugin.db"


@pytest.mark.parametrize(
    "path,expected",
    [
        (Path("C:/Users/x/OneDrive/.wikijs-plugin/wikijs-plugin.db"), True),
        (Path("/home/x/Dropbox/.wikijs-plugin/wikijs-plugin.db"), True),
        pytest.param(
            Path("/mnt/c/Users/x/.wikijs-plugin/wikijs-plugin.db"), True,
            marks=pytest.mark.skipif(
                os.name != "posix", reason="/mnt/ hint only renders with forward slashes on POSIX"
            ),
        ),
        (Path("/Users/x/Library/Mobile Documents/.wikijs-plugin/wikijs-plugin.db"), True),
        (Path("/home/x/.wikijs-plugin/wikijs-plugin.db"), False),
        (Path("C:/Users/x/.wikijs-plugin/wikijs-plugin.db"), False),
    ],
)
def test_is_network_path(path, expected):
    assert db_module._is_network_path(path) is expected


def test_connect_with_retry_succeeds_after_transient_lock(monkeypatch):
    """_connect_with_retry must retry get_connection() itself (not just
    document that it does) when the lock clears on a later attempt."""
    attempts = {"n": 0}
    real_get_connection = db_module.get_connection

    def flaky_get_connection():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return real_get_connection()

    monkeypatch.setattr(db_module, "get_connection", flaky_get_connection)
    monkeypatch.setattr(db_module.time, "sleep", lambda _seconds: None)

    conn = db_module._connect_with_retry()
    try:
        assert attempts["n"] == 3
    finally:
        conn.close()


def test_connect_with_retry_gives_up_after_exhausting_attempts(monkeypatch):
    """When every attempt hits SQLITE_BUSY, _connect_with_retry must raise
    the real OperationalError after _BUSY_RETRY_COUNT tries, not loop forever
    or swallow the failure."""
    attempts = {"n": 0}

    def always_locked():
        attempts["n"] += 1
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db_module, "get_connection", always_locked)
    monkeypatch.setattr(db_module.time, "sleep", lambda _seconds: None)

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        db_module._connect_with_retry()
    assert attempts["n"] == db_module._BUSY_RETRY_COUNT
