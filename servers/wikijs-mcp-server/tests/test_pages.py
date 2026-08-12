"""Tests for tools/pages.py — business logic behind the wikijs_* MCP tools.

The update_page tests port tests/update-page.test.ts 1:1 (auto-fetch content/
title/description/tags on metadata-only updates — see the original PR notes,
Ticket 897857).
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
from tools import history, pages


def make_client(**overrides) -> MagicMock:
    client = MagicMock()
    client.get_page_by_id.return_value = {
        "id": 42,
        "path": "test/page",
        "title": "Test Page",
        "content": "# Existing Content\n\nThis is the existing content.",
        "locale": "en",
        "isPublished": False,
        "tags": ["existing-tag"],
    }
    client.get_page_by_path.return_value = {
        "id": 42,
        "path": "test/page",
        "title": "Test Page",
        "content": "# Existing Content\n\nThis is the existing content.",
        "locale": "en",
        "isPublished": False,
        "tags": ["existing-tag"],
    }
    client.get_all_pages.return_value = [
        {"id": 42, "path": "test/page", "title": "Test Page", "tags": ["existing-tag"]},
    ]
    client.update_page.return_value = {"succeeded": True, "errorCode": 0, "message": "Page updated successfully"}
    for key, value in overrides.items():
        setattr(client, key, value)
    return client


class TestUpdatePageAutoFetch:
    def test_auto_fetches_content_when_only_ispublished_changed(self):
        client = make_client()
        pages.update_page(client, page_id=42, is_published=True)

        client.get_page_by_id.assert_called_with(42)
        client.update_page.assert_called_with(
            page_id=42,
            content="# Existing Content\n\nThis is the existing content.",
            title="Test Page",
            description=None,
            is_published=True,
            tags=["existing-tag"],
        )

    def test_auto_fetches_content_when_only_title_changed(self):
        client = make_client()
        pages.update_page(client, page_id=42, title="New Title")

        client.get_page_by_id.assert_called_with(42)
        args = client.update_page.call_args.kwargs
        assert args["content"] == "# Existing Content\n\nThis is the existing content."
        assert args["title"] == "New Title"

    def test_auto_fetches_content_when_only_description_changed(self):
        client = make_client()
        pages.update_page(client, page_id=42, description="New description")

        client.get_page_by_id.assert_called_with(42)
        args = client.update_page.call_args.kwargs
        assert args["content"] == "# Existing Content\n\nThis is the existing content."
        assert args["description"] == "New description"

    def test_does_not_override_content_when_explicitly_provided(self):
        client = make_client()
        pages.update_page(client, page_id=42, content="# New Content", is_published=True)

        args = client.update_page.call_args.kwargs
        assert args["content"] == "# New Content"
        assert args["is_published"] is True

    def test_resolves_page_by_path_and_auto_fetches_content(self):
        client = make_client()
        pages.update_page(client, path="test/page", locale="en", is_published=True)

        client.get_page_by_path.assert_called_with("test/page", "en")
        args = client.update_page.call_args.kwargs
        assert args["page_id"] == 42
        assert args["content"] == "# Existing Content\n\nThis is the existing content."


class TestUpdatePageTags:
    def test_preserves_existing_tags_when_not_provided(self):
        client = make_client()
        pages.update_page(client, page_id=42, content="# Updated Content")

        client.get_all_pages.assert_called()
        assert client.update_page.call_args.kwargs["tags"] == ["existing-tag"]

    def test_uses_provided_tags_when_explicitly_set(self):
        client = make_client()
        pages.update_page(client, page_id=42, content="# Updated Content", tags=["new-tag"])

        client.get_all_pages.assert_not_called()
        assert client.update_page.call_args.kwargs["tags"] == ["new-tag"]


class TestUpdatePageTitleDescriptionAutoFetch:
    def test_auto_fetches_title_when_only_content_updated(self):
        client = make_client()
        pages.update_page(client, page_id=42, content="# New Content")
        assert client.update_page.call_args.kwargs["title"] == "Test Page"

    def test_auto_fetches_description_when_only_content_updated(self):
        client = make_client(
            get_page_by_id=MagicMock(
                return_value={
                    "id": 42,
                    "path": "test/page",
                    "title": "Test Page",
                    "description": "Existing description",
                    "content": "# Existing Content",
                    "locale": "en",
                    "isPublished": False,
                    "tags": ["existing-tag"],
                }
            )
        )
        pages.update_page(client, page_id=42, content="# New Content")
        assert client.update_page.call_args.kwargs["description"] == "Existing description"

    def test_does_not_override_title_when_explicitly_provided(self):
        client = make_client()
        pages.update_page(client, page_id=42, title="Custom Title", content="# New Content")
        assert client.update_page.call_args.kwargs["title"] == "Custom Title"

    def test_does_not_override_description_when_explicitly_provided(self):
        client = make_client()
        pages.update_page(client, page_id=42, description="Custom desc", content="# New Content")
        assert client.update_page.call_args.kwargs["description"] == "Custom desc"

    def test_auto_fetches_title_and_description_via_path_resolution(self):
        client = make_client(
            get_page_by_path=MagicMock(
                return_value={
                    "id": 42,
                    "path": "test/page",
                    "title": "Path Page Title",
                    "description": "Path page description",
                    "content": "# Path Content",
                    "locale": "en",
                    "isPublished": True,
                    "tags": ["tag1"],
                }
            )
        )
        pages.update_page(client, path="test/page", locale="en", is_published=False)
        args = client.update_page.call_args.kwargs
        assert args["title"] == "Path Page Title"
        assert args["description"] == "Path page description"
        assert args["content"] == "# Path Content"


class TestUpdatePageContentShrinkGuard:
    """Safety net against wikijs_update_page's `content` silently wiping a
    page — content has no diff/merge, it fully REPLACES the body. Regression
    coverage for the incident that motivated this guard: a caller passed an
    unexpanded placeholder as `content`, which wiped a real multi-KB page
    with zero error or warning."""

    _OLD_CONTENT = "# Existing\n\n" + ("Lorem ipsum dolor sit amet. " * 20)  # well over 200 chars

    def _client_with_old_content(self) -> MagicMock:
        return make_client(
            get_page_by_id=MagicMock(
                return_value={
                    "id": 42,
                    "path": "test/page",
                    "title": "Test Page",
                    "content": self._OLD_CONTENT,
                    "locale": "en",
                    "isPublished": False,
                    "tags": [],
                }
            )
        )

    def test_blocks_drastic_shrink_without_confirmation(self):
        client = self._client_with_old_content()
        with pytest.raises(ValueError, match="Refusing update"):
            pages.update_page(client, page_id=42, content="short")
        client.update_page.assert_not_called()

    def test_error_names_old_and_new_lengths_and_the_escape_hatch(self):
        client = self._client_with_old_content()
        with pytest.raises(ValueError) as exc_info:
            pages.update_page(client, page_id=42, content="short")
        message = str(exc_info.value)
        assert str(len(self._OLD_CONTENT)) in message
        # Must be the MCP-facing camelCase name (server.py's actual parameter),
        # not the internal Python kwarg — this text is what an LLM caller sees
        # and retries with.
        assert "confirmContentShrink" in message
        assert "confirm_content_shrink" not in message

    def test_allows_drastic_shrink_with_confirmation(self):
        client = self._client_with_old_content()
        pages.update_page(client, page_id=42, content="short", confirm_content_shrink=True)
        assert client.update_page.call_args.kwargs["content"] == "short"

    def test_allows_similar_size_replacement_without_confirmation(self):
        client = self._client_with_old_content()
        new_content = self._OLD_CONTENT + " Plus a bit more text appended."
        pages.update_page(client, page_id=42, content=new_content)
        assert client.update_page.call_args.kwargs["content"] == new_content

    def test_skips_guard_for_small_existing_pages(self):
        """Default fixture content (~51 chars) is under the guard's minimum length."""
        client = make_client()
        pages.update_page(client, page_id=42, content="x")
        assert client.update_page.call_args.kwargs["content"] == "x"

    def test_does_not_apply_when_content_is_omitted(self):
        """Metadata-only updates never touch content, so the guard must not fire."""
        client = self._client_with_old_content()
        pages.update_page(client, page_id=42, is_published=True)
        assert client.update_page.call_args.kwargs["content"] == self._OLD_CONTENT

    def test_blocks_drastic_shrink_when_page_resolved_by_path(self):
        """current_page comes from get_page_by_path on this branch, not
        get_page_by_id — a distinct code path that must be guarded too."""
        client = make_client(
            get_page_by_path=MagicMock(
                return_value={
                    "id": 42,
                    "path": "test/page",
                    "title": "Test Page",
                    "content": self._OLD_CONTENT,
                    "locale": "en",
                    "isPublished": False,
                    "tags": [],
                }
            )
        )
        with pytest.raises(ValueError, match="Refusing update"):
            pages.update_page(client, path="test/page", locale="en", content="short")
        client.update_page.assert_not_called()


class TestUpdatePageErrors:
    def test_raises_when_page_not_found_by_id(self):
        client = make_client(get_page_by_id=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            pages.update_page(client, page_id=999, is_published=True)

    def test_raises_when_page_not_found_by_path(self):
        client = make_client(get_page_by_path=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            pages.update_page(client, path="nonexistent/page", is_published=True)

    def test_raises_when_neither_id_nor_path_provided(self):
        client = make_client()
        with pytest.raises(ValueError, match="id.*path|path.*id"):
            pages.update_page(client, is_published=True)


class TestCreatePage:
    def test_creates_page_successfully(self):
        client = make_client()
        client.create_page.return_value = {"id": 5, "path": "new/page", "title": "New"}
        result = pages.create_page(
            client, path="new/page", title="New", content="content", description="desc"
        )
        assert result["page"]["id"] == 5
        assert "new/page" in result["message"]

    def test_rejects_invalid_editor(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.create_page(
                client, path="p", title="T", content="c", description="d", editor="wordperfect"
            )


class TestGetPage:
    def test_returns_page_by_id(self):
        client = make_client()
        result = pages.get_page(client, page_id=42)
        assert result["id"] == 42

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.get_page(client)

    def test_raises_when_page_not_found(self):
        client = make_client(get_page_by_id=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            pages.get_page(client, page_id=1)


class TestListPages:
    def test_maps_pagination(self):
        client = make_client()
        client.list_pages.return_value = {
            "pages": [
                {"id": 1, "path": "a", "title": "A", "locale": "en", "tags": []},
            ],
            "total": 5,
        }
        result = pages.list_pages(client, limit=1, offset=0)
        assert result["pagination"]["has_more"] is True
        assert result["pagination"]["next_offset"] == 1

    def test_rejects_out_of_range_limit(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.list_pages(client, limit=0)


class TestSearchPages:
    def test_rejects_short_query(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.search_pages(client, query="a")


class TestDeletePage:
    def test_resolves_id_from_path(self):
        client = make_client()
        client.delete_page.return_value = {"succeeded": True, "errorCode": 0, "message": "ok"}
        pages.delete_page(client, path="test/page", locale="en")
        client.delete_page.assert_called_with(42)

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.delete_page(client)


class TestMovePage:
    def test_moves_by_id(self):
        client = make_client()
        client.move_page.return_value = {"succeeded": True, "errorCode": 0, "message": "ok"}
        result = pages.move_page(client, page_id=42, destination_path="new/path")
        assert result["to"] == "new/path"
        client.move_page.assert_called_with(42, "new/path", "en")

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.move_page(client, destination_path="new/path")


class TestCreatePageSourceTracking:
    """Phase 2: optional source_repo/source_ref/summary logged to page_history, never in content."""

    def test_logs_history_when_source_ref_given(self):
        client = make_client()
        client.create_page.return_value = {"id": 5, "path": "new/page", "title": "New"}
        pages.create_page(
            client, path="new/page", title="New", content="content", description="desc",
            locale="de", source_repo="wikijs-plugin", source_ref="abc123", summary="Initial docs",
        )
        entries = history.get_page_history("new/page")
        assert len(entries) == 1
        assert entries[0]["source_ref"] == "abc123"
        assert entries[0]["source_repo"] == "wikijs-plugin"
        assert entries[0]["summary"] == "Initial docs"
        assert entries[0]["locale"] == "de"

    def test_no_history_row_when_no_source_fields_given(self):
        client = make_client()
        client.create_page.return_value = {"id": 5, "path": "new/page", "title": "New"}
        pages.create_page(client, path="new/page", title="New", content="content", description="desc")
        assert history.get_page_history("new/page") == []

    def test_source_fields_never_reach_the_wikijs_client(self):
        """The visible page content/description must never carry the source ref."""
        client = make_client()
        client.create_page.return_value = {"id": 5, "path": "new/page", "title": "New"}
        pages.create_page(
            client, path="new/page", title="New", content="content", description="desc",
            source_ref="abc123",
        )
        call_kwargs = client.create_page.call_args.kwargs
        assert "abc123" not in call_kwargs["content"]
        assert "abc123" not in call_kwargs["description"]
        assert "source_ref" not in call_kwargs

    def test_history_logging_failure_does_not_fail_an_already_successful_write(self, monkeypatch, capsys):
        """Regression test: the Wiki.js write already committed by the time
        history logging runs — a DB error there must degrade to a stderr
        message, never propagate and make a successful create look failed."""
        def _raise(*a, **kw):
            raise sqlite3.OperationalError("disk I/O error")

        monkeypatch.setattr(history, "log_page_change", _raise)
        client = make_client()
        client.create_page.return_value = {"id": 5, "path": "new/page", "title": "New"}
        result = pages.create_page(
            client, path="new/page", title="New", content="content", description="desc",
            source_ref="abc123",
        )
        assert result["page"]["id"] == 5
        assert "page-history logging failed" in capsys.readouterr().err


class TestUpdatePageSourceTracking:
    def test_logs_history_using_explicit_path(self):
        client = make_client()
        pages.update_page(
            client, path="test/page", locale="en", content="# Updated",
            source_repo="wikijs-plugin", source_ref="def456",
        )
        entries = history.get_page_history("test/page")
        assert len(entries) == 1
        assert entries[0]["source_ref"] == "def456"

    def test_logs_history_using_id_by_resolving_path(self):
        """No path given directly — must resolve it (from the auto-fetched current page) before logging."""
        client = make_client()
        pages.update_page(client, page_id=42, is_published=True, source_ref="ghi789")
        entries = history.get_page_history("test/page")  # make_client()'s fixture page path
        assert len(entries) == 1
        assert entries[0]["source_ref"] == "ghi789"

    def test_no_history_row_when_no_source_fields_given(self):
        client = make_client()
        pages.update_page(client, page_id=42, is_published=True)
        assert history.get_page_history("test/page") == []

    def test_logs_actual_page_locale_not_request_default_when_resolving_by_id(self):
        """Regression test: an ID-based update must log the page's real locale
        (from the auto-fetched current page), not silently default to "en"
        just because the caller's `locale` kwarg defaulted to "en"."""
        client = make_client(
            get_page_by_id=MagicMock(return_value={
                "id": 42, "path": "test/page", "title": "Test Page",
                "content": "c", "locale": "de", "isPublished": False, "tags": [],
            })
        )
        pages.update_page(client, page_id=42, is_published=True, source_ref="abc123")
        de_entries = history.get_page_history("test/page", locale="de")
        en_entries = history.get_page_history("test/page", locale="en")
        assert [e["source_ref"] for e in de_entries] == ["abc123"]
        assert en_entries == []

    def test_history_logging_failure_does_not_fail_an_already_successful_write(self, monkeypatch, capsys):
        def _raise(*a, **kw):
            raise sqlite3.OperationalError("disk I/O error")

        monkeypatch.setattr(history, "log_page_change", _raise)
        client = make_client()
        result = pages.update_page(
            client, path="test/page", locale="en", content="# Updated", source_ref="def456",
        )
        assert "updated successfully" in result["message"]
        assert "page-history logging failed" in capsys.readouterr().err

    def test_logs_history_via_fallback_fetch_when_full_payload_given_by_id(self):
        """page_id + explicit content/title/description still triggers
        update_page's auto-fetch (needed for the content-shrink guard), which
        populates current_page/path for _log_update_history_safely. This test
        guards the outcome (history gets logged) regardless of which fetch
        path supplies the page — it would also catch a regression back to
        the old "auto-fetch skipped when everything is given" behavior,
        which relied on _log_update_history_safely's own separate
        client.get_page_by_id() fallback to learn the path/locale."""
        client = make_client()
        pages.update_page(
            client, page_id=42, content="# New", title="New Title", description="New desc",
            source_ref="jkl012",
        )
        entries = history.get_page_history("test/page")
        assert [e["source_ref"] for e in entries] == ["jkl012"]


class TestGetPageHistoryTool:
    def test_returns_logged_entries_for_path(self):
        history.log_page_change(page_path="mcp/wikijs-plugin", locale="de", source_ref="abc123")
        result = pages.get_page_history(path="mcp/wikijs-plugin")
        assert result["path"] == "mcp/wikijs-plugin"
        assert len(result["entries"]) == 1
        assert result["entries"][0]["source_ref"] == "abc123"

    def test_rejects_out_of_range_limit(self):
        with pytest.raises(ValueError):
            pages.get_page_history(path="mcp/wikijs-plugin", limit=0)

    def test_empty_for_unknown_path(self):
        result = pages.get_page_history(path="no/such/page")
        assert result["entries"] == []

    def test_accepts_paths_that_validate_path_would_reject(self):
        """Regression test: a page created/discovered outside this tool can
        have a path with a dot or non-ASCII char (validate_path's charset
        restriction is for writes, not for looking up an existing log
        entry). Logged verbatim via log_page_change to mirror how
        _log_update_history_safely writes whatever Wiki.js returns."""
        history.log_page_change(page_path="docs/v1.2", locale="en", source_ref="abc123")
        result = pages.get_page_history(path="docs/v1.2")
        assert [e["source_ref"] for e in result["entries"]] == ["abc123"]
