"""Business logic for the wikijs_* MCP tools (port of the TS src/tools/*.ts handlers)."""
from __future__ import annotations

from typing import Any

from .client import WikiJsClient
from .validation import (
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
    # whatever wasn't explicitly provided so a metadata-only update doesn't blank them.
    needs_current_page = content is None or title is None or description is None
    if needs_current_page and current_page is None:
        current_page = client.get_page_by_id(resolved_id)
        if not current_page:
            raise ValueError(f"Page not found with ID: {resolved_id}")

    content_to_use = content if content is not None else (current_page or {}).get("content")
    title_to_use = title if title is not None else (current_page or {}).get("title")
    description_to_use = description if description is not None else (current_page or {}).get("description")

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
    return {"message": f"Page {resolved_id} updated successfully", "result": result}


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
