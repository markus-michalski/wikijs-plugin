"""Test configuration — redirects the page-history DB to a temp file per test."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Redirect all DB operations to a temporary file-based SQLite database
    (file-based, not in-memory — the code under test opens its own
    connections per call, which an in-memory :memory: DB wouldn't share).

    Uses tmp_path (unique per test) so each test starts with a clean slate.
    """
    db_file = tmp_path / "test.db"

    import tools.db as db_module

    monkeypatch.setattr(db_module, "get_db_path", lambda: db_file)

    from tools.db import init_db

    init_db()

    yield db_file
