"""Business logic for the wikijs_* MCP tools (port of the TS src/tools/*.ts handlers)."""
from __future__ import annotations

import sys
from typing import Any

from . import history
from .client import WikiJsClient
from .validation import (
    CONTENT_SHRINK_GUARD_MIN_OLD_LEN,
    CONTENT_SHRINK_GUARD_RATIO,
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    validate_content,
    validate_description,
    validate_locale,
    validate_page_id,
    validate_path,
    validate_tags,
    validate_title,
)

_VALID_EDITORS = ("markdown", "code", "ckeditor")


def _log_history_safely(
    *, page_path: str, locale: str, source_repo: str, source_ref: str, summary: str
) -> None:
    """Best-effort page_history write.

    A local DB problem must never fail an already-successful Wiki.js
    create/update — the caller's page write has already committed by the
    time this runs, so raising here would report a false failure and invite
    a retry that duplicates/re-writes the page. See db.py's module docstring
    for why the schema itself doesn't need eager setup either.
    """
    if not (source_repo or source_ref or summary):
        return
    try:
        history.log_page_change(
            page_path=page_path, locale=locale,
            source_repo=source_repo, source_ref=source_ref, summary=summary,
        )
    except Exception as exc:  # intentionally broad — see docstring
        print(f"[wikijs-plugin] page-history logging failed: {exc}", file=sys.stderr)


def _log_update_history_safely(
    client: WikiJsClient,
    *,
    resolved_id: int,
    path: str | None,
    locale: str,
    current_page: dict[str, Any] | None,
    source_repo: str,
    source_ref: str,
    summary: str,
) -> None:
    """Resolve page_path/locale for update_page's history entry, then log it.

    Wrapped as one try/except so a failure in the path-resolution fallback
    fetch (client.get_page_by_id) is just as non-fatal as a failure in the
    DB write itself — see _log_history_safely's docstring.
    """
    if not (source_repo or source_ref or summary):
        return
    try:
        history_path = path if path is not None else (current_page or {}).get("path")
        history_locale = (current_page or {}).get("locale") or locale
        if history_path is None:
            fetched = client.get_page_by_id(resolved_id)
            if fetched:
                history_path = fetched.get("path")
                history_locale = fetched.get("locale") or history_locale
        if history_path:
            history.log_page_change(
                page_path=history_path, locale=history_locale,
                source_repo=source_repo, source_ref=source_ref, summary=summary,
            )
    except Exception as exc:  # intentionally broad — see _log_history_safely
        print(f"[wikijs-plugin] page-history logging failed: {exc}", file=sys.stderr)


def create_page(
    client: WikiJsClient,
    *,
    path: str,
    title: str,
    content: str,
    description: str,
    locale: str = "en",
    editor: str = "markdown",
    is_published: bool = True,
    is_private: bool = False,
    tags: list[str] | None = None,
    source_repo: str = "",
    source_ref: str = "",
    summary: str = "",
) -> dict[str, Any]:
    path = validate_path(path)
    title = validate_title(title)
    content = validate_content(content)
    description = validate_description(description)
    locale = validate_locale(locale)
    if editor not in _VALID_EDITORS:
        raise ValueError(f"editor must be one of {_VALID_EDITORS}")
    tags = validate_tags(tags or [])

    page = client.create_page(
        path=path,
        title=title,
        content=content,
        description=description,
        locale=locale,
        editor=editor,
        is_published=is_published,
        is_private=is_private,
        tags=tags,
    )

    _log_history_safely(page_path=path, locale=locale, source_repo=source_repo, source_ref=source_ref, summary=summary)

    return {
        "message": f"Page created successfully at /{path}",
        "page": {"id": page["id"], "path": page["path"], "title": page["title"]},
    }


def get_page(
    client: WikiJsClient, *, page_id: int | None = None, path: str | None = None, locale: str = "en"
) -> dict[str, Any]:
    locale = validate_locale(locale)
    if page_id is not None:
        page_id = validate_page_id(page_id)
    if path is not None:
        path = validate_path(path)
    if page_id is None and path is None:
        raise ValueError('Either "id" or "path" must be provided')

    page = client.get_page_by_id(page_id) if page_id is not None else client.get_page_by_path(path, locale)  # type: ignore[arg-type]
    if not page:
        suffix = f" at path: {path}" if path else f" with ID: {page_id}"
        raise ValueError(f"Page not found{suffix}")

    return {
        "id": page["id"],
        "path": page["path"],
        "title": page["title"],
        "description": page.get("description"),
        "content": page.get("content"),
        "contentType": page.get("contentType"),
        "isPublished": page.get("isPublished"),
        "locale": page.get("locale"),
        "createdAt": page.get("createdAt"),
        "updatedAt": page.get("updatedAt"),
    }


def list_pages(
    client: WikiJsClient,
    *,
    locale: str | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    if locale is not None:
        locale = validate_locale(locale)
    if not (1 <= limit <= MAX_PAGE_LIMIT):
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_LIMIT}")
    if offset < 0:
        raise ValueError("offset must be >= 0")

    result = client.list_pages(locale, limit, offset)
    pages, total = result["pages"], result["total"]

    page_list = [
        {
            "id": p["id"],
            "path": p["path"],
            "title": p["title"],
            "description": p.get("description"),
            "locale": p["locale"],
            "isPublished": p.get("isPublished"),
            "tags": p.get("tags") or [],
            "updatedAt": p.get("updatedAt"),
        }
        for p in pages
    ]

    has_more = offset + len(page_list) < total
    pagination = {"limit": limit, "offset": offset, "total_count": total, "has_more": has_more}
    if has_more:
        pagination["next_offset"] = offset + len(page_list)

    return {"pages": page_list, "pagination": pagination}


def search_pages(client: WikiJsClient, *, query: str, locale: str | None = None) -> dict[str, Any]:
    if not (2 <= len(query) <= 200):
        raise ValueError("Search query must be between 2 and 200 characters")
    if locale is not None:
        locale = validate_locale(locale)

    results = client.search_pages(query, locale)
    return {
        "totalHits": results["totalHits"],
        "suggestions": results.get("suggestions", []),
        "results": [
            {
                "id": r["id"],
                "title": r["title"],
                "path": r["path"],
                "description": r.get("description"),
                "locale": r["locale"],
            }
            for r in results["results"]
        ],
    }


def _guard_against_content_shrink(*, new_content: str, old_content: str, confirmed: bool) -> None:
    """Refuse an update whose `content` looks like an accidental wholesale overwrite.

    wikijs_update_page's `content` REPLACES the entire page — there is no
    diff/merge. A caller that means to fix one section but accidentally
    passes only that fragment (an unexpanded shell substitution, a truncated
    variable, a partial edit meant to be appended rather than to replace
    everything) silently wipes the rest of the page with no warning and no
    undo from the API's perspective. Genuine, intentional shrinks (trimming a
    bloated page) are rare — one explicit confirmContentShrink=true is a
    small price for catching the accidental case by default.
    """
    if confirmed:
        return
    old_len = len(old_content)
    if old_len < CONTENT_SHRINK_GUARD_MIN_OLD_LEN:
        return
    if len(new_content) >= old_len * CONTENT_SHRINK_GUARD_RATIO:
        return
    raise ValueError(
        f"Refusing update: new content ({len(new_content)} chars) is less than "
        f"{CONTENT_SHRINK_GUARD_RATIO:.0%} of the current page's content "
        f"({old_len} chars). wikijs_update_page's content REPLACES the whole page — "
        "there is no diff/merge. This looks like an accidental partial overwrite "
        "rather than an intentional rewrite. If the shrink is intentional, retry "
        # MCP-facing parameter name (camelCase), not the Python kwarg below —
        # this text goes back to the calling LLM as the tool error result.
        "with confirmContentShrink=true."
    )


def update_page(
    client: WikiJsClient,
    *,
    page_id: int | None = None,
    path: str | None = None,
    locale: str = "en",
    content: str | None = None,
    title: str | None = None,
    description: str | None = None,
    is_published: bool | None = None,
    tags: list[str] | None = None,
    source_repo: str = "",
    source_ref: str = "",
    summary: str = "",
    confirm_content_shrink: bool = False,
) -> dict[str, Any]:
    locale = validate_locale(locale)
    if page_id is not None:
        page_id = validate_page_id(page_id)
    if path is not None:
        path = validate_path(path)
    if page_id is None and path is None:
        raise ValueError('Either "id" or "path" must be provided')
    if content is not None:
        content = validate_content(content)
    if title is not None:
        title = validate_title(title)
    if description is not None:
        description = validate_description(description)
    if tags is not None:
        tags = validate_tags(tags)

    resolved_id = page_id
    current_page: dict[str, Any] | None = None

    if resolved_id is None and path is not None:
        current_page = client.get_page_by_path(path, locale)
        if not current_page:
            raise ValueError(f"Page not found at path: {path}")
        resolved_id = current_page["id"]

    if resolved_id is None:
        raise ValueError("Could not resolve page ID")

    # Wiki.js requires string values for title/description/content — auto-fetch
    # whatever wasn't explicitly provided so a metadata-only update doesn't
    # blank them. Unconditional (not just "if something's missing") because
    # _guard_against_content_shrink below always needs the real old content
    # to compare against, even when content/title/description are all given.
    if current_page is None:
        current_page = client.get_page_by_id(resolved_id)
        if not current_page:
            raise ValueError(f"Page not found with ID: {resolved_id}")

    # current_page is guaranteed non-None past this point — both resolution
    # branches above raise if the fetch comes back falsy.
    if content is not None:
        _guard_against_content_shrink(
            new_content=content,
            # "" (not missing) if the API response ever omits the field —
            # treated as an empty page, so the guard fails open rather than
            # blocking on data it can't actually compare.
            old_content=current_page.get("content") or "",
            confirmed=confirm_content_shrink,
        )

    content_to_use = content if content is not None else current_page.get("content")
    title_to_use = title if title is not None else current_page.get("title")
    description_to_use = description if description is not None else current_page.get("description")

    tags_to_use = tags
    if tags_to_use is None:
        pages = client.get_all_pages()
        found = next((p for p in pages if p["id"] == resolved_id), None)
        tags_to_use = (found or {}).get("tags") or []

    result = client.update_page(
        page_id=resolved_id,
        content=content_to_use,
        title=title_to_use,
        description=description_to_use,
        is_published=is_published,
        tags=tags_to_use,
    )

    _log_update_history_safely(
        client, resolved_id=resolved_id, path=path, locale=locale, current_page=current_page,
        source_repo=source_repo, source_ref=source_ref, summary=summary,
    )

    return {"message": f"Page {resolved_id} updated successfully", "result": result}


def get_page_history(*, path: str, locale: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Read-only: past wikijs_create_page/update_page calls logged for a page.

    Pure local DB read — takes no WikiJsClient, never touches the Wiki.js API.

    Deliberately does NOT run `path` through validate_path()'s charset/dots
    restrictions: those exist to keep bad data out of Wiki.js on writes, but
    here `path` is only a parameterized SQLite lookup key (no injection
    surface) for a page that may already exist with a path validate_path
    would reject today (e.g. containing a dot, or non-ASCII characters) —
    logged via an ID-based update, whose page_path comes verbatim from
    Wiki.js's own API response, not through this validator. Only bounds-check
    length so an absurd input still fails fast.
    """
    if not (1 <= len(path) <= 500):
        raise ValueError("Path must be between 1 and 500 characters")
    if locale is not None:
        locale = validate_locale(locale)
    if not (1 <= limit <= 200):
        raise ValueError("limit must be between 1 and 200")
    return {"path": path, "entries": history.get_page_history(path, locale=locale, limit=limit)}


def delete_page(
    client: WikiJsClient, *, page_id: int | None = None, path: str | None = None, locale: str = "en"
) -> dict[str, Any]:
    locale = validate_locale(locale)
    if page_id is not None:
        page_id = validate_page_id(page_id)
    if path is not None:
        path = validate_path(path)
    if page_id is None and path is None:
        raise ValueError('Either "id" or "path" must be provided')

    if page_id is None:
        page = client.get_page_by_path(path, locale)  # type: ignore[arg-type]
        if not page:
            raise ValueError(f"Page not found at path: {path}")
        page_id = page["id"]

    result = client.delete_page(page_id)
    return {"message": f"Page {page_id} deleted permanently", "result": result}


def move_page(
    client: WikiJsClient,
    *,
    page_id: int | None = None,
    path: str | None = None,
    locale: str = "en",
    destination_path: str,
    destination_locale: str = "en",
) -> dict[str, Any]:
    locale = validate_locale(locale)
    destination_locale = validate_locale(destination_locale)
    destination_path = validate_path(destination_path)
    if page_id is not None:
        page_id = validate_page_id(page_id)
    if path is not None:
        path = validate_path(path)
    if page_id is None and path is None:
        raise ValueError('Either "id" or "path" must be provided')

    source_path = path
    if page_id is None:
        page = client.get_page_by_path(source_path, locale)  # type: ignore[arg-type]
        if not page:
            raise ValueError(f"Page not found at path: {source_path}")
        page_id = page["id"]

    result = client.move_page(page_id, destination_path, destination_locale)
    return {
        "message": "Page moved successfully",
        "from": source_path or f"ID: {page_id}",
        "to": destination_path,
        "destinationLocale": destination_locale,
        "result": result,
    }
