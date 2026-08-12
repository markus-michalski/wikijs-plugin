"""Wiki.js MCP Server.

Provides Model Context Protocol (MCP) tools for interacting with the Wiki.js
GraphQL API. Tool names, parameters, and descriptions mirror the original
TypeScript implementation (wikijs-mcp-server v2.0.1) so existing docs/callers
keep working unchanged.
"""
from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from tools import pages
from tools.client import WikiJsClient
from tools.config import load_credentials

mcp = MCPServer("wikijs-mcp")

_client: WikiJsClient | None = None


def _get_client() -> WikiJsClient:
    """Lazily construct the Wiki.js client on first tool call.

    Deferred (rather than at import time) so `import server` — e.g. from
    tests or tooling — doesn't require WIKIJS_API_URL/WIKIJS_API_TOKEN to be
    configured. `run.py` still validates credentials eagerly at process
    startup so misconfiguration fails fast for real usage.
    """
    global _client
    if _client is None:
        api_url, api_token = load_credentials()
        _client = WikiJsClient(api_url, api_token)
    return _client


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
    )
)
def wikijs_create_page(
    path: str,
    title: str,
    content: str,
    description: str,
    locale: str = "en",
    editor: str = "markdown",
    isPublished: bool = True,
    isPrivate: bool = False,
    tags: list[str] | None = None,
    sourceRepo: str = "",
    sourceRef: str = "",
    summary: str = "",
) -> dict[str, Any]:
    """Create a new page in Wiki.js with markdown or HTML content.

    Creates a new page at the specified path. If a page already exists at
    that path, the operation fails.

    Args:
        path: Page path without leading slash (e.g. "osticket/plugin-name")
        title: Page title (max 200 chars)
        content: Page content in markdown or HTML
        description: Meta description (max 500 chars)
        locale: Page locale, default "en"
        editor: "markdown" (default), "code", or "ckeditor"
        isPublished: Publish immediately, default True
        isPrivate: Private page, default False
        tags: Tags for categorization
        sourceRepo: Optional source repo name for page-history tracking (e.g.
            "wikijs-plugin"). Logged to a local DB only, never written into
            the page content/description — see wikijs_get_page_history.
        sourceRef: Optional source commit/tag (e.g. `git rev-parse HEAD`).
            Same DB-only logging as sourceRepo.
        summary: Optional one-line summary of what changed, DB-only.

    Returns:
        Created page info with ID, path, and title.
    """
    return pages.create_page(
        _get_client(),
        path=path,
        title=title,
        content=content,
        description=description,
        locale=locale,
        editor=editor,
        is_published=isPublished,
        is_private=isPrivate,
        tags=tags,
        source_repo=sourceRepo,
        source_ref=sourceRef,
        summary=summary,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
def wikijs_get_page(
    id: int | None = None,
    path: str | None = None,
    locale: str = "en",
) -> dict[str, Any]:
    """Get a page from Wiki.js by ID or path. Returns full content and metadata.

    Identify the page either by its numeric ID or by its path + locale.
    Content over 100,000 characters is truncated with a notice.

    Args:
        id: Page ID (use this OR path)
        path: Page path (use this OR id)
        locale: Page locale, default "en" (required when using path)
    """
    return pages.get_page(_get_client(), page_id=id, path=path, locale=locale)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
def wikijs_list_pages(
    locale: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all pages in Wiki.js with optional filtering and pagination.

    Use the offset parameter to navigate through large result sets; see
    pagination.has_more / pagination.next_offset in the response.

    Args:
        locale: Filter by locale (e.g. "en", "de")
        limit: Max pages to return, default 50, max 200
        offset: Skip N pages for pagination, default 0
    """
    return pages.list_pages(_get_client(), locale=locale, limit=limit, offset=offset)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
def wikijs_search_pages(query: str, locale: str | None = None) -> dict[str, Any]:
    """Search for pages in Wiki.js by query string.

    Full-text search across page content and metadata, ranked by relevance.

    Args:
        query: Search query (min 2, max 200 chars)
        locale: Filter results by locale (optional)
    """
    return pages.search_pages(_get_client(), query=query, locale=locale)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
def wikijs_update_page(
    id: int | None = None,
    path: str | None = None,
    locale: str = "en",
    content: str | None = None,
    title: str | None = None,
    description: str | None = None,
    isPublished: bool | None = None,
    tags: list[str] | None = None,
    sourceRepo: str = "",
    sourceRef: str = "",
    summary: str = "",
    confirmContentShrink: bool = False,
) -> dict[str, Any]:
    """Update an existing page in Wiki.js.

    Identify the page by ID or path+locale. If content/title/description
    aren't provided, the current values are automatically preserved (so a
    metadata-only update, e.g. changing isPublished, works without resending
    the whole page). Same for tags.

    WARNING: `content`, when provided, REPLACES the page's entire body —
    there is no diff/merge, and no way to append or patch just one section.
    To fix or extend a page, fetch it first with wikijs_get_page and send
    back the full modified content, not a partial edit.

    As a safety net against accidental wholesale overwrites (e.g. sending an
    unexpanded variable or a fragment meant to be appended), an update is
    refused when the new content is less than half the length of the page's
    current content (for pages over ~200 chars) — the error names the exact
    lengths involved. If the shrink is genuinely intended, retry the same
    call with confirmContentShrink=True.

    Args:
        id: Page ID (use this OR path)
        path: Page path (use this OR id)
        locale: Page locale, default "en" (required with path)
        content: New page content — REPLACES the entire page, optional
        title: New title, max 200 chars (optional)
        description: New description, max 500 chars (optional)
        isPublished: Publish/unpublish (optional)
        tags: Replace tags (optional)
        sourceRepo: Optional source repo name for page-history tracking, DB-only
            (never written into the page content/description) — see
            wikijs_get_page_history.
        sourceRef: Optional source commit/tag (e.g. `git rev-parse HEAD`), DB-only.
        summary: Optional one-line summary of what changed, DB-only.
        confirmContentShrink: Set True to confirm an intentional large content
            reduction and bypass the accidental-overwrite guard above.
    """
    return pages.update_page(
        _get_client(),
        page_id=id,
        path=path,
        locale=locale,
        content=content,
        title=title,
        description=description,
        is_published=isPublished,
        tags=tags,
        source_repo=sourceRepo,
        source_ref=sourceRef,
        summary=summary,
        confirm_content_shrink=confirmContentShrink,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True
    )
)
def wikijs_delete_page(
    id: int | None = None,
    path: str | None = None,
    locale: str = "en",
) -> dict[str, Any]:
    """Delete a page from Wiki.js. WARNING: This action is IRREVERSIBLE!

    Permanently removes a page and all its history. Identify the page by
    ID or path+locale.

    Args:
        id: Page ID (use this OR path)
        path: Page path (use this OR id)
        locale: Page locale, default "en" (required with path)
    """
    return pages.delete_page(_get_client(), page_id=id, path=path, locale=locale)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
    )
)
def wikijs_move_page(
    destinationPath: str,
    id: int | None = None,
    path: str | None = None,
    locale: str = "en",
    destinationLocale: str = "en",
) -> dict[str, Any]:
    """Move a page to a new path in Wiki.js.

    Identify the source page by ID or path+locale. This changes the page
    URL — update any links pointing to the old path.

    Note: wikijs_get_page_history entries logged before a move stay filed
    under the old path (page_history is keyed by path, not page ID) — they
    won't show up when querying the new path.

    Args:
        destinationPath: New path for the page (e.g. "new-category/page-name")
        id: Page ID to move (use this OR path)
        path: Current page path (use this OR id)
        locale: Current page locale, default "en"
        destinationLocale: Target locale, default "en"
    """
    return pages.move_page(
        _get_client(),
        page_id=id,
        path=path,
        locale=locale,
        destination_path=destinationPath,
        destination_locale=destinationLocale,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )
)
def wikijs_get_page_history(
    path: str,
    locale: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Get the change history logged for a Wiki.js page (Phase 2: source-ref tracking).

    Local-only read from a SQLite DB (~/.wikijs-plugin/wikijs-plugin.db) —
    never calls the Wiki.js API. Returns entries only for calls that were
    made with sourceRepo/sourceRef/summary set on wikijs_create_page or
    wikijs_update_page; plain edits without those parameters aren't logged.

    Args:
        path: Page path (same as passed to create_page/update_page)
        locale: Filter by locale (optional; omit to see all locales for this path)
        limit: Max entries to return, newest first, default 20, max 200

    Returns:
        {"path": ..., "entries": [{"changed_at", "locale", "source_repo", "source_ref", "summary"}, ...]}
    """
    return pages.get_page_history(path=path, locale=locale, limit=limit)
