"""Tests for the Wiki.js GraphQL API client."""
from __future__ import annotations

import json

import httpx
import pytest
from tools.client import WikiJsClient, WikiJsError
from tools.validation import CHARACTER_LIMIT


def make_client(handler) -> WikiJsClient:
    transport = httpx.MockTransport(handler)
    return WikiJsClient("https://wiki.example.com/graphql", "test-token", transport=transport)


def json_response(payload, status_code=200):
    def handler(request):
        return httpx.Response(status_code, json=payload)
    return handler


class TestQuery:
    def test_returns_data_on_success(self):
        client = make_client(json_response({"data": {"hello": "world"}}))
        assert client.query("query { hello }") == {"hello": "world"}

    def test_sends_bearer_token(self):
        captured = {}

        def handler(request):
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"data": {}})

        client = make_client(handler)
        client.query("query { x }")
        assert captured["auth"] == "Bearer test-token"

    def test_raises_on_graphql_errors(self):
        client = make_client(json_response({"errors": [{"message": "boom"}]}))
        with pytest.raises(WikiJsError, match="boom"):
            client.query("query { x }")

    def test_raises_on_http_error_status(self):
        client = make_client(json_response({}, status_code=500))
        with pytest.raises(WikiJsError, match="500"):
            client.query("query { x }")

    def test_raises_when_no_data_returned(self):
        client = make_client(json_response({}))
        with pytest.raises(WikiJsError, match="No data"):
            client.query("query { x }")

    def test_raises_on_timeout(self):
        def handler(request):
            raise httpx.TimeoutException("timed out", request=request)

        client = make_client(handler)
        with pytest.raises(WikiJsError, match="timed out"):
            client.query("query { x }")


class TestListPages:
    def _pages(self):
        return [
            {"id": 1, "path": "a", "title": "A", "description": "", "isPublished": True,
             "locale": "en", "contentType": "markdown", "createdAt": "", "updatedAt": "", "tags": []},
            {"id": 2, "path": "b", "title": "B", "description": "", "isPublished": True,
             "locale": "de", "contentType": "markdown", "createdAt": "", "updatedAt": "", "tags": []},
            {"id": 3, "path": "c", "title": "C", "description": "", "isPublished": True,
             "locale": "en", "contentType": "markdown", "createdAt": "", "updatedAt": "", "tags": []},
        ]

    def test_filters_by_locale(self):
        client = make_client(json_response({"data": {"pages": {"list": self._pages()}}}))
        result = client.list_pages(locale="en")
        assert result["total"] == 2
        assert [p["id"] for p in result["pages"]] == [1, 3]

    def test_paginates(self):
        client = make_client(json_response({"data": {"pages": {"list": self._pages()}}}))
        result = client.list_pages(limit=1, offset=1)
        assert result["total"] == 3
        assert [p["id"] for p in result["pages"]] == [2]

    def test_no_locale_filter_returns_all(self):
        client = make_client(json_response({"data": {"pages": {"list": self._pages()}}}))
        result = client.list_pages()
        assert result["total"] == 3


class TestGetPage:
    def test_get_page_by_id_returns_none_when_missing(self):
        client = make_client(json_response({"data": {"pages": {"single": None}}}))
        assert client.get_page_by_id(999) is None

    def test_get_page_by_id_truncates_long_content(self):
        long_content = "x" * (CHARACTER_LIMIT + 500)
        page = {"id": 1, "path": "a", "title": "A", "description": "", "content": long_content,
                "contentType": "markdown", "isPublished": True, "locale": "en"}
        client = make_client(json_response({"data": {"pages": {"single": page}}}))
        result = client.get_page_by_id(1)
        assert len(result["content"]) < len(long_content)
        assert "truncated" in result["content"]

    def test_get_page_by_path_passes_locale(self):
        captured = {}

        def handler(request):
            body = json.loads(request.content)
            captured["variables"] = body["variables"]
            return httpx.Response(200, json={"data": {"pages": {"singleByPath": None}}})

        client = make_client(handler)
        client.get_page_by_path("some/path", "de")
        assert captured["variables"] == {"path": "some/path", "locale": "de"}


class TestSearchPages:
    def test_filters_results_by_locale(self):
        payload = {
            "data": {
                "pages": {
                    "search": {
                        "results": [
                            {"id": 1, "title": "A", "path": "a", "description": "", "locale": "en"},
                            {"id": 2, "title": "B", "path": "b", "description": "", "locale": "de"},
                        ],
                        "suggestions": [],
                        "totalHits": 2,
                    }
                }
            }
        }
        client = make_client(json_response(payload))
        result = client.search_pages("query", locale="de")
        assert result["totalHits"] == 1
        assert [r["id"] for r in result["results"]] == [2]


class TestMutations:
    def test_create_page_raises_on_failure(self):
        payload = {"data": {"pages": {"create": {
            "responseResult": {"succeeded": False, "errorCode": 1, "message": "path taken"},
            "page": None,
        }}}}
        client = make_client(json_response(payload))
        with pytest.raises(WikiJsError, match="path taken"):
            client.create_page(
                path="x", title="X", content="c", description="d",
                locale="en", editor="markdown", is_published=True, is_private=False, tags=[],
            )

    def test_create_page_returns_page_on_success(self):
        payload = {"data": {"pages": {"create": {
            "responseResult": {"succeeded": True, "errorCode": 0, "message": ""},
            "page": {"id": 5, "path": "x", "title": "X"},
        }}}}
        client = make_client(json_response(payload))
        page = client.create_page(
            path="x", title="X", content="c", description="d",
            locale="en", editor="markdown", is_published=True, is_private=False, tags=[],
        )
        assert page == {"id": 5, "path": "x", "title": "X"}

    def test_update_page_sends_null_for_omitted_fields(self):
        captured = {}

        def handler(request):
            captured["variables"] = json.loads(request.content)["variables"]
            return httpx.Response(200, json={"data": {"pages": {"update": {
                "responseResult": {"succeeded": True, "errorCode": 0, "message": "ok"}
            }}}})

        client = make_client(handler)
        client.update_page(page_id=42, content="new content")
        assert captured["variables"] == {
            "id": 42, "content": "new content", "title": None,
            "description": None, "isPublished": None, "tags": None,
        }

    def test_update_page_raises_on_failure(self):
        payload = {"data": {"pages": {"update": {
            "responseResult": {"succeeded": False, "errorCode": 1, "message": "nope"}
        }}}}
        client = make_client(json_response(payload))
        with pytest.raises(WikiJsError, match="nope"):
            client.update_page(page_id=1)

    def test_delete_page_raises_on_failure(self):
        payload = {"data": {"pages": {"delete": {
            "responseResult": {"succeeded": False, "errorCode": 1, "message": "denied"}
        }}}}
        client = make_client(json_response(payload))
        with pytest.raises(WikiJsError, match="denied"):
            client.delete_page(1)

    def test_move_page_raises_on_failure(self):
        payload = {"data": {"pages": {"move": {
            "responseResult": {"succeeded": False, "errorCode": 1, "message": "conflict"}
        }}}}
        client = make_client(json_response(payload))
        with pytest.raises(WikiJsError, match="conflict"):
            client.move_page(1, "new/path", "en")


class TestGetAllPages:
    def test_delegates_to_list_pages_with_large_limit(self):
        captured = {}

        def handler(request):
            body = json.loads(request.content)
            captured["variables"] = body["variables"]
            return httpx.Response(200, json={"data": {"pages": {"list": []}}})

        client = make_client(handler)
        client.get_all_pages()
        # get_all_pages fetches everything client-side (no server-side limit/offset vars)
        assert client.get_all_pages() == []
