"""Tests for the Wiki.js 3 REST API client."""
from __future__ import annotations

import json

import httpx
import pytest
from tools.client import WikiJsClient, WikiJsError, path_hash
from tools.validation import CHARACTER_LIMIT

SITE_ID = "40a75b1e-4ef8-44fe-9d65-92d7b0e243df"
PAGE_ID = "309a0d75-e06d-4ab3-a8cf-9dae8f27c85a"
BASE_URL = "https://wiki.example.com"


class Recorder:
    """Routes MockTransport requests by "METHOD /path" and records them."""

    def __init__(self, routes: dict[str, object] | None = None) -> None:
        self.routes = routes or {}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = f"{request.method} {request.url.path}"
        if key == "GET /_api/bootstrap" and key not in self.routes:
            return httpx.Response(200, json={"site": {"id": SITE_ID}})
        if key not in self.routes:
            return httpx.Response(404, json={"statusCode": 404, "message": f"no route {key}"})
        result = self.routes[key]
        if callable(result):
            return result(request)
        if isinstance(result, httpx.Response):
            return result
        return httpx.Response(200, json=result)

    def calls(self, key: str) -> list[httpx.Request]:
        method, path = key.split(" ", 1)
        return [r for r in self.requests if r.method == method and r.url.path == path]


def make_client(routes: dict[str, object] | None = None, base_url: str = BASE_URL):
    recorder = Recorder(routes)
    client = WikiJsClient(base_url, "test-token", transport=httpx.MockTransport(recorder))
    return client, recorder


def body_of(request: httpx.Request):
    return json.loads(request.content)


class TestPathHash:
    # Reference values computed with the upstream JS implementation (cyrb53).
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("home", "1867eaf483ceab"),
            ("oxid7/pdf-invoice/templates", "14ab9776295947"),
            ("über/größe", "10179a0b0ce370"),
        ],
    )
    def test_matches_upstream(self, path, expected):
        assert path_hash(path) == expected

    def test_leading_slash_is_ignored(self):
        assert path_hash("/home") == path_hash("home")


class TestSiteResolution:
    def test_resolves_site_id_via_bootstrap_with_hostname(self):
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/search": {"results": [], "totalHits": 0}})
        client.search_pages("hello")
        bootstrap = rec.calls("GET /_api/bootstrap")
        assert len(bootstrap) == 1
        assert bootstrap[0].url.params["hostname"] == "wiki.example.com"

    def test_site_id_is_cached(self):
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/search": {"results": [], "totalHits": 0}})
        client.search_pages("one")
        client.search_pages("two")
        assert len(rec.calls("GET /_api/bootstrap")) == 1

    def test_explicit_site_id_skips_bootstrap(self):
        recorder = Recorder({f"GET /_api/sites/{SITE_ID}/pages/search": {"results": [], "totalHits": 0}})
        client = WikiJsClient(
            BASE_URL, "t", site_id=SITE_ID, transport=httpx.MockTransport(recorder)
        )
        client.search_pages("hello")
        assert recorder.calls("GET /_api/bootstrap") == []

    def test_base_url_with_subpath_and_trailing_slash(self):
        recorder = Recorder({"GET /wiki/_api/bootstrap": {"site": {"id": SITE_ID}}})
        client = WikiJsClient(
            "https://example.com/wiki/", "t", transport=httpx.MockTransport(recorder)
        )
        with pytest.raises(WikiJsError):  # search route unknown, but bootstrap path must be right
            client.search_pages("hello")
        assert recorder.calls("GET /wiki/_api/bootstrap")

    def test_missing_site_in_bootstrap_raises(self):
        client, _ = make_client({"GET /_api/bootstrap": {"site": None}})
        with pytest.raises(WikiJsError, match="site"):
            client.search_pages("hello")


class TestRequest:
    def test_malformed_page_id_is_wrapped_not_leaked(self):
        client, _ = make_client()
        with pytest.raises(WikiJsError):
            client.get_page_by_id("abc\ndef")

    def test_sends_bearer_token(self):
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/search": {"results": [], "totalHits": 0}})
        client.search_pages("hello")
        assert all(r.headers["authorization"] == "Bearer test-token" for r in rec.requests)

    def test_http_error_surfaces_server_message(self):
        client, _ = make_client({
            f"GET /_api/sites/{SITE_ID}/pages/search": httpx.Response(
                401, json={"statusCode": 401, "error": "Unauthorized", "message": "Token expired"}
            )
        })
        with pytest.raises(WikiJsError, match="401.*Token expired"):
            client.search_pages("hello")

    def test_http_error_without_json_body(self):
        client, _ = make_client({
            f"GET /_api/sites/{SITE_ID}/pages/search": httpx.Response(502, text="Bad Gateway")
        })
        with pytest.raises(WikiJsError, match="502"):
            client.search_pages("hello")

    def test_raises_on_timeout(self):
        def handler(request):
            if request.url.path == "/_api/bootstrap":
                return httpx.Response(200, json={"site": {"id": SITE_ID}})
            raise httpx.TimeoutException("timed out", request=request)

        client = WikiJsClient(BASE_URL, "t", transport=httpx.MockTransport(handler))
        with pytest.raises(WikiJsError, match="timed out"):
            client.search_pages("hello")


def _search_result(page_id, path, locale, **extra):
    return {"id": page_id, "path": path, "locale": locale, "title": path.upper(),
            "description": "", "tags": [], "createdAt": "", "updatedAt": "", **extra}


class TestListPages:
    route = f"GET /_api/sites/{SITE_ID}/pages/search"

    def _handler(self, everything, drafts=()):
        """Search mock honouring limit/offset/publishState like the real endpoint."""
        def handler(request):
            params = request.url.params
            pool = [p for p in everything if p["id"] in drafts] if params.get("publishState") == "draft" else everything
            if params.get("locales"):
                pool = [p for p in pool if p["locale"] == params["locales"]]
            offset = int(params.get("offset", 0))
            limit = int(params["limit"])
            return httpx.Response(200, json={"results": pool[offset:offset + limit], "totalHits": len(pool)})
        return handler

    def _pages(self, n, locale="en"):
        return [_search_result(str(i), f"p{i}", locale) for i in range(n)]

    def test_offset_and_limit_are_passed_to_the_server(self):
        client, rec = make_client({self.route: self._handler(self._pages(300))})
        result = client.list_pages(limit=10, offset=150)
        assert [p["id"] for p in result["pages"]] == [str(i) for i in range(150, 160)]
        assert result["total"] == 300
        listing = [r for r in rec.calls(self.route) if "publishState" not in r.url.params]
        assert len(listing) == 1
        assert listing[0].url.params["offset"] == "150"
        assert listing[0].url.params["limit"] == "10"

    def test_limit_above_api_maximum_is_fetched_in_chunks(self):
        client, rec = make_client({self.route: self._handler(self._pages(250))})
        result = client.list_pages(limit=200)
        assert len(result["pages"]) == 200
        listing = [r for r in rec.calls(self.route) if "publishState" not in r.url.params]
        assert [r.url.params["limit"] for r in listing] == ["100", "100"]
        assert [r.url.params["offset"] for r in listing] == ["0", "100"]

    def test_stops_at_end_of_results(self):
        client, _ = make_client({self.route: self._handler(self._pages(3))})
        result = client.list_pages(limit=50, offset=0)
        assert result["total"] == 3
        assert len(result["pages"]) == 3

    def test_locale_filter_is_sent_to_server(self):
        everything = self._pages(2, "en") + [_search_result("d", "d", "de-DE")]
        client, rec = make_client({self.route: self._handler(everything)})
        result = client.list_pages(locale="de-DE")
        assert [p["id"] for p in result["pages"]] == ["d"]
        assert all(r.url.params["locales"] == "de-DE" for r in rec.calls(self.route))

    def test_drafts_are_marked_not_published(self):
        client, _ = make_client({self.route: self._handler(self._pages(3), drafts={"1"})})
        flags = {p["id"]: p["isPublished"] for p in client.list_pages()["pages"]}
        assert flags == {"0": True, "1": False, "2": True}


class TestGetPage:
    def test_get_by_id_requests_content_and_normalizes(self):
        page = {"id": PAGE_ID, "path": "a", "title": "A", "locale": "en", "publishState": "draft",
                "content": "hi", "tags": ["x"], "contentType": "markdown"}
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}": page})
        result = client.get_page_by_id(PAGE_ID)
        assert rec.calls(f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}")[0].url.params["withContent"] == "true"
        assert result["isPublished"] is False
        assert result["publishState"] == "draft"
        assert result["content"] == "hi"

    def test_published_state_maps_to_is_published_true(self):
        page = {"id": PAGE_ID, "path": "a", "title": "A", "locale": "en", "publishState": "published"}
        client, _ = make_client({f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}": page})
        assert client.get_page_by_id(PAGE_ID)["isPublished"] is True

    def test_get_by_id_returns_none_on_404(self):
        client, _ = make_client({
            f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}": httpx.Response(404, json={"message": "nope"})
        })
        assert client.get_page_by_id(PAGE_ID) is None

    def test_get_by_id_truncates_long_content(self):
        long_content = "x" * (CHARACTER_LIMIT + 500)
        page = {"id": PAGE_ID, "path": "a", "title": "A", "locale": "en", "content": long_content}
        client, _ = make_client({f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}": page})
        result = client.get_page_by_id(PAGE_ID)
        assert len(result["content"]) < len(long_content)
        assert "truncated" in result["content"]

    def test_get_by_path_uses_path_hash_with_path_and_locale(self):
        h = path_hash("some/path")
        page = {"id": PAGE_ID, "path": "some/path", "title": "S", "locale": "de-DE"}
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/{h}": page})
        result = client.get_page_by_path("some/path", "de-DE")
        params = rec.calls(f"GET /_api/sites/{SITE_ID}/pages/{h}")[0].url.params
        assert params["path"] == "some/path"
        assert params["locale"] == "de-DE"
        assert params["withContent"] == "true"
        assert result["id"] == PAGE_ID

    def test_get_by_path_returns_none_on_404(self):
        client, _ = make_client()
        assert client.get_page_by_path("missing", "en") is None

    def test_other_errors_are_not_swallowed(self):
        client, _ = make_client({
            f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}": httpx.Response(403, json={"message": "forbidden"})
        })
        with pytest.raises(WikiJsError, match="403"):
            client.get_page_by_id(PAGE_ID)


class TestSearchPages:
    def test_passes_query_and_locale_and_maps_total(self):
        payload = {"results": [_search_result("a", "a", "de-DE")], "totalHits": 1}
        client, rec = make_client({f"GET /_api/sites/{SITE_ID}/pages/search": payload})
        result = client.search_pages("query", locale="de-DE")
        params = rec.calls(f"GET /_api/sites/{SITE_ID}/pages/search")[0].url.params
        assert params["query"] == "query"
        assert params["locales"] == "de-DE"
        assert result["totalHits"] == 1
        assert result["results"][0]["id"] == "a"
        assert result["suggestions"] == []


class TestCreatePage:
    def _create(self, client, **overrides):
        kwargs = dict(path="x", title="X", content="c", description="d", locale="en",
                      editor="markdown", is_published=False, tags=["t"])
        kwargs.update(overrides)
        return client.create_page(**kwargs)

    def test_posts_page_input_with_publish_state(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        created = {"ok": True, "message": "ok", "page": {"id": PAGE_ID, "path": "x", "title": "X"}}
        client, rec = make_client({route: created})
        page = self._create(client)
        assert page == {"id": PAGE_ID, "path": "x", "title": "X"}
        assert body_of(rec.calls(route)[0]) == {
            "path": "x", "title": "X", "content": "c", "description": "d",
            "locale": "en", "editor": "markdown", "publishState": "draft", "tags": ["t"],
        }

    def test_published_sends_published(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID, "path": "x", "title": "X"}}})
        self._create(client, is_published=True)
        assert body_of(rec.calls(route)[0])["publishState"] == "published"

    def test_failure_raises_with_server_message(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, _ = make_client({route: httpx.Response(409, json={"message": "path taken"})})
        with pytest.raises(WikiJsError, match="path taken"):
            self._create(client)


class TestUpdatePage:
    route = f"PATCH /_api/sites/{SITE_ID}/pages/{PAGE_ID}"

    def test_sends_only_provided_fields(self):
        client, rec = make_client({self.route: {"ok": True, "message": "saved", "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, content="new content")
        assert body_of(rec.calls(self.route)[0]) == {"content": "new content"}

    def test_is_published_maps_to_publish_state(self):
        client, rec = make_client({self.route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, is_published=True)
        assert body_of(rec.calls(self.route)[0]) == {"publishState": "published"}

    def test_all_fields(self):
        client, rec = make_client({self.route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, content="c", title="t", description="d", tags=["a"])
        assert body_of(rec.calls(self.route)[0]) == {
            "content": "c", "title": "t", "description": "d", "tags": ["a"],
        }

    def test_returns_server_result(self):
        client, _ = make_client({self.route: {"ok": True, "message": "saved", "page": {"id": PAGE_ID}}})
        result = client.update_page(page_id=PAGE_ID, title="t")
        assert result["ok"] is True
        assert result["message"] == "saved"

    def test_failure_raises(self):
        denied = httpx.Response(403, json={"message": "You are not allowed to edit this page."})
        client, _ = make_client({self.route: denied})
        with pytest.raises(WikiJsError, match="not allowed"):
            client.update_page(page_id=PAGE_ID, title="t")

    def test_nothing_to_update_is_rejected_locally(self):
        client, rec = make_client()
        with pytest.raises(WikiJsError, match="Nothing to update"):
            client.update_page(page_id=PAGE_ID)
        assert rec.requests == []


class TestDeletePage:
    route = f"DELETE /_api/sites/{SITE_ID}/pages/{PAGE_ID}"

    def test_delete_handles_204(self):
        client, _ = make_client({self.route: httpx.Response(204)})
        assert client.delete_page(PAGE_ID) == {"ok": True}

    def test_delete_sends_no_json_content_type(self):
        """Wiki.js (Fastify) answers 400 "Body cannot be empty" to a bodyless
        request that declares application/json — found in a live delete."""
        client, rec = make_client({self.route: httpx.Response(204)})
        client.delete_page(PAGE_ID)
        assert "content-type" not in rec.calls(self.route)[0].headers

    def test_requests_with_a_body_are_sent_as_json(self):
        route = f"PATCH /_api/sites/{SITE_ID}/pages/{PAGE_ID}"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, title="t")
        assert rec.calls(route)[0].headers["content-type"] == "application/json"

    def test_delete_failure_raises(self):
        client, _ = make_client({self.route: httpx.Response(403, json={"message": "denied"})})
        with pytest.raises(WikiJsError, match="denied"):
            client.delete_page(PAGE_ID)


class TestMovePage:
    route = f"PUT /_api/sites/{SITE_ID}/pages/{PAGE_ID}/path"

    def test_sends_path_and_locale(self):
        client, rec = make_client({self.route: {"ok": True, "message": "moved", "page": {"id": PAGE_ID}}})
        result = client.move_page(PAGE_ID, "new/path", "de-DE")
        assert body_of(rec.calls(self.route)[0]) == {"path": "new/path", "locale": "de-DE"}
        assert result["ok"] is True

    def test_failure_raises(self):
        client, _ = make_client({self.route: httpx.Response(409, json={"message": "conflict"})})
        with pytest.raises(WikiJsError, match="conflict"):
            client.move_page(PAGE_ID, "new/path", "en")


class TestVersions:
    history = f"GET /_api/sites/{SITE_ID}/pages/{PAGE_ID}/history"

    def test_list_versions_newest_first(self):
        entries = [
            {"id": "v1", "action": "created", "versionDate": "2026-11-01T10:00:00.000Z"},
            {"id": "v3", "action": "updated", "versionDate": "2026-11-03T10:00:00.000Z"},
            {"id": "v2", "action": "updated", "versionDate": "2026-11-02T10:00:00.000Z"},
        ]
        client, _ = make_client({self.history: entries})
        assert [v["id"] for v in client.list_versions(PAGE_ID)] == ["v3", "v2", "v1"]

    def test_get_version_returns_content_truncated(self):
        long_content = "x" * (CHARACTER_LIMIT + 10)
        route = f"{self.history}/v1"
        client, _ = make_client({route: {"id": "v1", "content": long_content}})
        version = client.get_version(PAGE_ID, "v1")
        assert "truncated" in version["content"]

    def test_get_version_returns_none_on_404(self):
        client, _ = make_client()
        assert client.get_version(PAGE_ID, "missing") is None


class TestRecycleBin:
    def test_list_deleted_passes_locale(self):
        route = f"GET /_api/sites/{SITE_ID}/pages/deleted"
        client, rec = make_client({route: [{"pageId": PAGE_ID, "versionId": "v9", "path": "a"}]})
        result = client.list_deleted("de-DE")
        assert result[0]["versionId"] == "v9"
        assert rec.calls(route)[0].url.params["locale"] == "de-DE"

    def test_restore_page_posts_version_id_only_by_default(self):
        route = f"POST /_api/sites/{SITE_ID}/pages/{PAGE_ID}/restore"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.restore_page(PAGE_ID, "v9")
        assert body_of(rec.calls(route)[0]) == {"versionId": "v9"}

    def test_restore_page_optional_destination(self):
        route = f"POST /_api/sites/{SITE_ID}/pages/{PAGE_ID}/restore"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.restore_page(PAGE_ID, "v9", path="new/path", locale="en", title="T")
        assert body_of(rec.calls(route)[0]) == {
            "versionId": "v9", "path": "new/path", "locale": "en", "title": "T",
        }


class TestReasonAndLinks:
    def test_create_sends_reason_for_change(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID, "path": "x", "title": "X"}}})
        client.create_page(path="x", title="X", content="c", description="d", locale="en",
                           editor="markdown", is_published=False, tags=[], reason="Initial docs")
        assert body_of(rec.calls(route)[0])["reasonForChange"] == "Initial docs"

    def test_create_omits_reason_when_empty(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID, "path": "x", "title": "X"}}})
        client.create_page(path="x", title="X", content="c", description="d", locale="en",
                           editor="markdown", is_published=False, tags=[])
        assert "reasonForChange" not in body_of(rec.calls(route)[0])

    def test_update_sends_reason_for_change(self):
        route = f"PATCH /_api/sites/{SITE_ID}/pages/{PAGE_ID}"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, title="t", reason="Fix typo")
        assert body_of(rec.calls(route)[0]) == {"title": "t", "reasonForChange": "Fix typo"}

    def test_reason_alone_is_not_an_update(self):
        client, rec = make_client()
        with pytest.raises(WikiJsError, match="Nothing to update"):
            client.update_page(page_id=PAGE_ID, reason="why")
        assert rec.requests == []

    def test_move_sends_update_links_only_when_requested(self):
        route = f"PUT /_api/sites/{SITE_ID}/pages/{PAGE_ID}/path"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.move_page(PAGE_ID, "new/path", "en", update_links=True)
        assert body_of(rec.calls(route)[0]) == {"path": "new/path", "locale": "en", "updateLinks": True}


class TestTags:
    def test_list_tags(self):
        route = f"GET /_api/sites/{SITE_ID}/tags"
        client, _ = make_client({route: [{"tag": "sylius", "usageCount": 324}]})
        assert client.list_tags() == [{"tag": "sylius", "usageCount": 324}]


class TestLocaleRelations:
    rel = [{"locale": "en", "path": "mcp/x"}]

    def test_create_sends_locale_relations(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID, "path": "x", "title": "X"}}})
        client.create_page(path="x", title="X", content="c", description="d", locale="de-DE",
                           editor="markdown", is_published=False, tags=[], locale_relations=self.rel)
        assert body_of(rec.calls(route)[0])["localeRelations"] == self.rel

    def test_create_omits_locale_relations_by_default(self):
        route = f"POST /_api/sites/{SITE_ID}/pages"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID, "path": "x", "title": "X"}}})
        client.create_page(path="x", title="X", content="c", description="d", locale="en",
                           editor="markdown", is_published=False, tags=[])
        assert "localeRelations" not in body_of(rec.calls(route)[0])

    def test_update_sends_locale_relations_and_they_count_as_a_change(self):
        route = f"PATCH /_api/sites/{SITE_ID}/pages/{PAGE_ID}"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, locale_relations=self.rel)
        assert body_of(rec.calls(route)[0]) == {"localeRelations": self.rel}

    def test_empty_list_is_sent_to_unlink(self):
        route = f"PATCH /_api/sites/{SITE_ID}/pages/{PAGE_ID}"
        client, rec = make_client({route: {"ok": True, "page": {"id": PAGE_ID}}})
        client.update_page(page_id=PAGE_ID, locale_relations=[])
        assert body_of(rec.calls(route)[0]) == {"localeRelations": []}
