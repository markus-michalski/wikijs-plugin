"""Page-history logging and retrieval (Phase 2: source-ref tracking).

A logged source_ref means "the page was written at this commit". Only rows with
verified = 1 mean "the page was checked against the code at this commit" (see
mark_verified), and only those serve as the baseline for diff-based updates.
"""
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
    verified: bool = False,
    page_updated_at: str = "",
) -> None:
    """Record one wikijs_create_page/update_page call in page_history."""
    with db_connection() as conn:
        with conn:
            conn.execute(
                """INSERT INTO page_history
                       (page_path, locale, source_repo, source_ref, summary, verified, page_updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (page_path, locale, source_repo, source_ref, summary, int(verified), page_updated_at),
            )


def mark_verified(
    *,
    page_path: str,
    locale: str,
    source_repo: str,
    source_ref: str,
    page_updated_at: str,
    summary: str = "",
) -> None:
    """Record that a page was checked against the source at source_ref.

    Callers set this only after the claim check passed for that page and ref.
    Repo, ref and the page's Wiki.js updatedAt are required: without a ref the
    marker cannot serve as a diff baseline, and without updatedAt a later edit
    made outside the gated flow could not be told apart from the checked text.
    Values are stored stripped, since a trailing newline copied from
    `git rev-parse HEAD` would break `git diff {ref}..HEAD`.
    """
    source_repo = source_repo.strip()
    source_ref = source_ref.strip()
    page_updated_at = page_updated_at.strip()
    if not source_repo:
        raise ValueError("source_repo is required to mark a page as verified")
    if not source_ref:
        raise ValueError("source_ref is required to mark a page as verified")
    if not page_updated_at:
        raise ValueError("page_updated_at is required to mark a page as verified")
    log_page_change(
        page_path=page_path, locale=locale, source_repo=source_repo,
        source_ref=source_ref, summary=summary, verified=True, page_updated_at=page_updated_at,
    )


def get_verified_refs(
    *, page_path: str | None = None, locale: str | None = None
) -> list[dict[str, Any]]:
    """Newest verified ref per (page, locale), ordered by path and locale.

    Later unverified writes do not hide an older verified ref: the verified
    ref is the last point at which the page was checked against the code.
    """
    query = """
        SELECT page_path, locale, source_repo, source_ref, page_updated_at, changed_at AS verified_at
        FROM page_history
        WHERE verified = 1
          AND id = (
              SELECT MAX(h.id) FROM page_history h
              WHERE h.page_path = page_history.page_path
                AND h.locale = page_history.locale
                AND h.verified = 1
          )
    """
    params: list[Any] = []
    if page_path is not None:
        query += " AND page_path = ?"
        params.append(page_path)
    if locale is not None:
        query += " AND locale = ?"
        params.append(locale)
    query += " ORDER BY page_path, locale"

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_page_history(
    page_path: str, *, locale: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Return past changes for a page, newest first."""
    query = (
        "SELECT id, page_path, locale, changed_at, source_repo, source_ref, summary, verified, page_updated_at "
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
