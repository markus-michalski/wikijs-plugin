"""Wiki.js GraphQL API client."""
from __future__ import annotations

from typing import Any

import httpx

from .validation import CHARACTER_LIMIT

API_TIMEOUT = 30.0


class WikiJsError(Exception):
    """Raised when a Wiki.js GraphQL request fails."""


class WikiJsClient:
    """Thin GraphQL client for the Wiki.js `pages` API."""

    def __init__(
        self,
        api_url: str,
        api_token: str,
        timeout: float = API_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_url = api_url
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query/mutation and return its `data` field."""
        try:
            response = self._client.post(
                self._api_url,
                json={"query": query, "variables": variables or {}},
            )
        except httpx.TimeoutException as exc:
            raise WikiJsError("Request timed out. Please try again.") from exc
        except httpx.HTTPError as exc:
            raise WikiJsError(f"Wiki.js API request failed: {exc}") from exc

        if response.status_code >= 400:
            raise WikiJsError(f"HTTP error! status: {response.status_code}")

        result = response.json()

        if result.get("errors"):
            messages = "; ".join(e.get("message", "") for e in result["errors"])
            raise WikiJsError(f"GraphQL request failed: {messages}")

        data = result.get("data")
        if data is None:
            raise WikiJsError("No data returned from GraphQL API")

        return data

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_pages(
        self, locale: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        query = """
            query {
              pages {
                list {
                  id
                  path
                  title
                  description
                  isPublished
                  locale
                  contentType
                  createdAt
                  updatedAt
                  tags
                }
              }
            }
        """
        data = self.query(query)
        pages = data["pages"]["list"]
        if locale:
            pages = [p for p in pages if p["locale"] == locale]
        total = len(pages)
        return {"pages": pages[offset : offset + limit], "total": total}

    def get_page_by_id(self, page_id: int) -> dict[str, Any] | None:
        query = """
            query($id: Int!) {
              pages {
                single(id: $id) {
                  id
                  path
                  title
                  description
                  content
                  contentType
                  isPublished
                  locale
                  createdAt
                  updatedAt
                }
              }
            }
        """
        data = self.query(query, {"id": page_id})
        page = data["pages"]["single"]
        return self._truncate_content(page)

    def get_page_by_path(self, path: str, locale: str = "en") -> dict[str, Any] | None:
        query = """
            query($path: String!, $locale: String!) {
              pages {
                singleByPath(path: $path, locale: $locale) {
                  id
                  path
                  title
                  description
                  content
                  contentType
                  isPublished
                  locale
                  createdAt
                  updatedAt
                }
              }
            }
        """
        data = self.query(query, {"path": path, "locale": locale})
        page = data["pages"]["singleByPath"]
        return self._truncate_content(page)

    def search_pages(self, search_query: str, locale: str | None = None) -> dict[str, Any]:
        query = """
            query($query: String!) {
              pages {
                search(query: $query) {
                  results {
                    id
                    title
                    path
                    description
                    locale
                  }
                  suggestions
                  totalHits
                }
              }
            }
        """
        data = self.query(query, {"query": search_query})
        results = data["pages"]["search"]
        if locale and results.get("results"):
            results["results"] = [r for r in results["results"] if r["locale"] == locale]
            results["totalHits"] = len(results["results"])
        return results

    def get_all_pages(self) -> list[dict[str, Any]]:
        """Fetch every page (used to preserve tags on metadata-only updates)."""
        return self.list_pages(None, 10_000, 0)["pages"]

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
        is_private: bool,
        tags: list[str],
    ) -> dict[str, Any]:
        query = """
            mutation(
              $content: String!
              $description: String!
              $editor: String!
              $isPublished: Boolean!
              $isPrivate: Boolean!
              $locale: String!
              $path: String!
              $tags: [String]!
              $title: String!
            ) {
              pages {
                create(
                  content: $content
                  description: $description
                  editor: $editor
                  isPublished: $isPublished
                  isPrivate: $isPrivate
                  locale: $locale
                  path: $path
                  tags: $tags
                  title: $title
                ) {
                  responseResult {
                    succeeded
                    errorCode
                    slug
                    message
                  }
                  page {
                    id
                    path
                    title
                  }
                }
              }
            }
        """
        data = self.query(
            query,
            {
                "content": content,
                "description": description,
                "editor": editor,
                "isPublished": is_published,
                "isPrivate": is_private,
                "locale": locale,
                "path": path,
                "tags": tags,
                "title": title,
            },
        )
        result = data["pages"]["create"]
        if not result["responseResult"]["succeeded"]:
            raise WikiJsError(f"Failed to create page: {result['responseResult']['message']}")
        return result["page"]

    def update_page(
        self,
        *,
        page_id: int,
        content: str | None = None,
        title: str | None = None,
        description: str | None = None,
        is_published: bool | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        query = """
            mutation(
              $id: Int!
              $content: String
              $title: String
              $description: String
              $isPublished: Boolean
              $tags: [String]
            ) {
              pages {
                update(
                  id: $id
                  content: $content
                  title: $title
                  description: $description
                  isPublished: $isPublished
                  tags: $tags
                ) {
                  responseResult {
                    succeeded
                    errorCode
                    message
                  }
                }
              }
            }
        """
        data = self.query(
            query,
            {
                "id": page_id,
                "content": content,
                "title": title,
                "description": description,
                "isPublished": is_published,
                "tags": tags,
            },
        )
        result = data["pages"]["update"]["responseResult"]
        if not result["succeeded"]:
            raise WikiJsError(f"Failed to update page: {result['message']}")
        return result

    def delete_page(self, page_id: int) -> dict[str, Any]:
        query = """
            mutation($id: Int!) {
              pages {
                delete(id: $id) {
                  responseResult {
                    succeeded
                    errorCode
                    message
                  }
                }
              }
            }
        """
        data = self.query(query, {"id": page_id})
        result = data["pages"]["delete"]["responseResult"]
        if not result["succeeded"]:
            raise WikiJsError(f"Failed to delete page: {result['message']}")
        return result

    def move_page(
        self, page_id: int, destination_path: str, destination_locale: str = "en"
    ) -> dict[str, Any]:
        query = """
            mutation($id: Int!, $destinationPath: String!, $destinationLocale: String!) {
              pages {
                move(
                  id: $id
                  destinationPath: $destinationPath
                  destinationLocale: $destinationLocale
                ) {
                  responseResult {
                    succeeded
                    errorCode
                    message
                  }
                }
              }
            }
        """
        data = self.query(
            query,
            {"id": page_id, "destinationPath": destination_path, "destinationLocale": destination_locale},
        )
        result = data["pages"]["move"]["responseResult"]
        if not result["succeeded"]:
            raise WikiJsError(f"Failed to move page: {result['message']}")
        return result

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
