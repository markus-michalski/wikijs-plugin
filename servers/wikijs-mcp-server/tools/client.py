"""Wiki.js 3 REST API client."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx

from .validation import CHARACTER_LIMIT

API_TIMEOUT = 30.0

# The search endpoint caps `limit` at 100.
_SEARCH_CHUNK = 100


class WikiJsError(Exception):
    """Raised when a Wiki.js API request fails."""


def path_hash(path: str) -> str:
    """Hash a page path the way Wiki.js 3 does (cyrb53, `generatePathHash` upstream).

    Wiki.js 3 addresses a page by the hash of its path, not by the path itself:
    ``GET /pages/{hash}?path=...&locale=...``. The hash runs over UTF-16 code
    units, exactly like the JavaScript original.
    """
    mask = 0xFFFFFFFF

    def imul(a: int, b: int) -> int:
        return ((a & mask) * (b & mask)) & mask

    h1, h2 = 0xDEADBEEF, 0x41C6CE57
    units = (path.removeprefix("/") or "home").encode("utf-16-le")
    for i in range(0, len(units), 2):
        ch = units[i] | (units[i + 1] << 8)
        h1 = imul(h1 ^ ch, 2654435761)
        h2 = imul(h2 ^ ch, 1597334677)
    h1 = imul(h1 ^ (h1 >> 16), 2246822507)
    h1 ^= imul(h2 ^ (h2 >> 13), 3266489909)
    h2 = imul(h2 ^ (h2 >> 16), 2246822507)
    h2 ^= imul(h1 ^ (h1 >> 13), 3266489909)
    return format(4294967296 * (2097151 & h2) + (h1 & mask), "x")


class WikiJsClient:
    """Thin client for the Wiki.js 3 page API (`/_api/sites/:siteId/pages`)."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = API_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
        site_id: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._hostname = urlsplit(self._base_url).hostname or ""
        self._site_id = site_id or None
        self._client = httpx.Client(
            # No fixed Content-Type: httpx sets application/json itself when a JSON
            # body is sent, and Wiki.js rejects a bodyless request (DELETE) that
            # declares it ("Body cannot be empty").
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a request to ``{base_url}/_api{path}``; raise on any HTTP error except 404."""
        try:
            response = self._client.request(
                method, f"{self._base_url}/_api{path}", params=params, json=json
            )
        except httpx.TimeoutException as exc:
            raise WikiJsError("Request timed out. Please try again.") from exc
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise WikiJsError(f"Wiki.js API request failed: {exc}") from exc

        if response.status_code >= 400 and response.status_code != 404:
            raise WikiJsError(self._describe_error(response))
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Like `_send`, but 404 is an error too and the JSON body is returned."""
        response = self._send(method, path, **kwargs)
        if response.status_code == 404:
            raise WikiJsError(self._describe_error(response))
        if response.status_code == 204 or not response.content:
            return {"ok": True}
        return response.json()

    @staticmethod
    def _describe_error(response: httpx.Response) -> str:
        message = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                message = str(body.get("message") or body.get("error") or "")
        except ValueError:
            pass
        suffix = f": {message}" if message else ""
        return f"Wiki.js API error (HTTP {response.status_code}){suffix}"

    @property
    def site_id(self) -> str:
        """The site this client talks to, resolved once via `/_api/bootstrap`."""
        if self._site_id is None:
            data = self._request("GET", "/bootstrap", params={"hostname": self._hostname})
            site = data.get("site") or {}
            if not site.get("id"):
                raise WikiJsError(
                    f"Wiki.js returned no site for hostname '{self._hostname}'. "
                    "Check WIKIJS_API_URL, or set WIKIJS_SITE_ID explicitly."
                )
            self._site_id = site["id"]
        return self._site_id

    def _pages_path(self, suffix: str = "") -> str:
        return f"/sites/{self.site_id}/pages{suffix}"

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_pages(
        self, locale: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """List pages. Wiki.js 3's list route is a stub, so this pages through search.

        Search results carry no publish state, so the drafts are fetched with a second,
        `publishState=draft` filtered search and used to set `isPublished` on each entry.
        """
        pages, total = self._search_listing(locale, offset, limit)
        drafts = {p["id"] for p in self._search_listing(locale, 0, None, publish_state="draft")[0]}
        for page in pages:
            page["isPublished"] = page["id"] not in drafts
        return {"pages": pages, "total": total}

    def _search_listing(
        self,
        locale: str | None,
        offset: int,
        limit: int | None,
        publish_state: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Collect search hits from `offset`, up to `limit` (None = all), 100 per request."""
        pages: list[dict[str, Any]] = []
        total = 0
        while limit is None or len(pages) < limit:
            chunk = _SEARCH_CHUNK if limit is None else min(_SEARCH_CHUNK, limit - len(pages))
            params: dict[str, Any] = {"limit": chunk, "offset": offset + len(pages)}
            if locale:
                params["locales"] = locale
            if publish_state:
                params["publishState"] = publish_state
            data = self._request("GET", self._pages_path("/search"), params=params)
            results = data.get("results") or []
            total = data.get("totalHits", offset + len(pages) + len(results))
            pages.extend(self._normalize(r) for r in results)
            if not results or offset + len(pages) >= total:
                break
        return pages, total

    def get_page_by_id(self, page_id: str) -> dict[str, Any] | None:
        response = self._send(
            "GET", self._pages_path(f"/{page_id}"), params={"withContent": "true"}
        )
        return self._page_from_response(response)

    def get_page_by_path(self, path: str, locale: str = "en") -> dict[str, Any] | None:
        response = self._send(
            "GET",
            self._pages_path(f"/{path_hash(path)}"),
            params={"path": path, "locale": locale, "withContent": "true"},
        )
        return self._page_from_response(response)

    def search_pages(self, search_query: str, locale: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"query": search_query, "limit": _SEARCH_CHUNK}
        if locale:
            params["locales"] = locale
        data = self._request("GET", self._pages_path("/search"), params=params)
        results = [self._normalize(r) for r in data.get("results") or []]
        return {
            "results": results,
            "suggestions": data.get("suggestions") or [],
            "totalHits": data.get("totalHits", len(results)),
        }

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create_page(
        self,
        *,
        path: str,
        title: str,
        content: str,
        description: str,
        locale: str,
        editor: str,
        is_published: bool,
        tags: list[str],
        reason: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "path": path,
            "title": title,
            "content": content,
            "description": description,
            "locale": locale,
            "editor": editor,
            "publishState": self._publish_state(is_published),
            "tags": tags,
        }
        if reason:
            body["reasonForChange"] = reason
        data = self._request("POST", self._pages_path(), json=body)
        return data["page"]

    def update_page(
        self,
        *,
        page_id: str,
        content: str | None = None,
        title: str | None = None,
        description: str | None = None,
        is_published: bool | None = None,
        tags: list[str] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Partial update (PATCH): only the fields passed are sent and changed.

        `reason` is recorded on the page version this save produces; it is not a
        change by itself.
        """
        body: dict[str, Any] = {}
        if content is not None:
            body["content"] = content
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if is_published is not None:
            body["publishState"] = self._publish_state(is_published)
        if tags is not None:
            body["tags"] = tags
        if not body:
            raise WikiJsError("Nothing to update: pass at least one field to change.")
        if reason:
            body["reasonForChange"] = reason
        return self._request("PATCH", self._pages_path(f"/{page_id}"), json=body)

    def delete_page(self, page_id: str) -> dict[str, Any]:
        return self._request("DELETE", self._pages_path(f"/{page_id}"))

    def move_page(
        self,
        page_id: str,
        destination_path: str,
        destination_locale: str = "en",
        update_links: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"path": destination_path, "locale": destination_locale}
        if update_links:
            body["updateLinks"] = True
        return self._request("PUT", self._pages_path(f"/{page_id}/path"), json=body)

    # ------------------------------------------------------------------
    # Versions, recycle bin, tags
    # ------------------------------------------------------------------

    def list_versions(self, page_id: str) -> list[dict[str, Any]]:
        """The page's version history, newest first."""
        data = self._request("GET", self._pages_path(f"/{page_id}/history"))
        entries: list[dict[str, Any]] = data if isinstance(data, list) else []
        return sorted(entries, key=lambda e: e.get("versionDate") or "", reverse=True)

    def get_version(self, page_id: str, version_id: str) -> dict[str, Any] | None:
        response = self._send("GET", self._pages_path(f"/{page_id}/history/{version_id}"))
        if response.status_code == 404:
            return None
        return self._truncate_content(response.json())

    def list_deleted(self, locale: str) -> list[dict[str, Any]]:
        data = self._request("GET", self._pages_path("/deleted"), params={"locale": locale})
        return data if isinstance(data, list) else []

    def restore_page(
        self,
        page_id: str,
        version_id: str,
        *,
        path: str | None = None,
        locale: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Bring a deleted page back from the recycle bin (optionally under a new path)."""
        body: dict[str, Any] = {"versionId": version_id}
        if path is not None:
            body["path"] = path
        if locale is not None:
            body["locale"] = locale
        if title is not None:
            body["title"] = title
        return self._request("POST", self._pages_path(f"/{page_id}/restore"), json=body)

    def list_tags(self) -> list[dict[str, Any]]:
        data = self._request("GET", f"/sites/{self.site_id}/tags")
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _publish_state(is_published: bool) -> str:
        return "published" if is_published else "draft"

    @staticmethod
    def _normalize(page: dict[str, Any]) -> dict[str, Any]:
        """Add the v2-style `isPublished` flag derived from v3's `publishState`."""
        state = page.get("publishState")
        if state is not None:
            page["isPublished"] = state == "published"
        return page

    def _page_from_response(self, response: httpx.Response) -> dict[str, Any] | None:
        if response.status_code == 404:
            return None
        return self._truncate_content(self._normalize(response.json()))

    @staticmethod
    def _truncate_content(page: dict[str, Any] | None) -> dict[str, Any] | None:
        if page and page.get("content") and len(page["content"]) > CHARACTER_LIMIT:
            original_length = len(page["content"])
            page["content"] = (
                page["content"][:CHARACTER_LIMIT]
                + f"\n\n[Content truncated. Original length: {original_length} chars. "
                "Use path-based access for full content.]"
            )
        return page
