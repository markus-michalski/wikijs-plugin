"""Page-history logging and retrieval (Phase 2: source-ref tracking)."""
from __future__ import annotations

from typing import Any

from .db import db_connection


def log_page_change(
    *,
    page_path: str,
    locale: str,
    source_repo: str = "",
    source_ref: str = "",
    summary: str = "",
) -> None:
    """Record one wikijs_create_page/update_page call in page_history."""
    with db_connection() as conn:
        with conn:
            conn.execute(
                """INSERT INTO page_history (page_path, locale, source_repo, source_ref, summary)
                   VALUES (?, ?, ?, ?, ?)""",
                (page_path, locale, source_repo, source_ref, summary),
            )


def get_page_history(
    page_path: str, *, locale: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Return past changes for a page, newest first."""
    query = (
        "SELECT id, page_path, locale, changed_at, source_repo, source_ref, summary "
        "FROM page_history WHERE page_path = ?"
    )
    params: list[Any] = [page_path]
    if locale is not None:
        query += " AND locale = ?"
        params.append(locale)
    query += " ORDER BY changed_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
