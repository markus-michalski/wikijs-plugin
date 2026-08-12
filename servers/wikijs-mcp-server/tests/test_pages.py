"""Tests for tools/pages.py — business logic behind the wikijs_* MCP tools.

The update_page tests port tests/update-page.test.ts 1:1 (auto-fetch content/
title/description/tags on metadata-only updates — see the original PR notes,
Ticket 897857).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from tools import pages


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
