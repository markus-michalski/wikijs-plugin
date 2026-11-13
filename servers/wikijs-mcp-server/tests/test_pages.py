"""Tests for tools/pages.py — business logic behind the wikijs_* MCP tools.

Wiki.js 3 updates are partial (PATCH): update_page sends only the fields the
caller passed, so there is no auto-fetch of title/description/tags any more.
The one remaining fetch is for the content-shrink guard and path resolution.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
from tools import history, pages

PID = "309a0d75-e06d-4ab3-a8cf-9dae8f27c85a"
NEW_PID = "7c1f2a9e-5b34-4c0a-9d41-0e6a8b2f3d10"
MISSING_PID = "00000000-0000-4000-8000-000000000000"


def make_client(**overrides) -> MagicMock:
    client = MagicMock()
    client.get_page_by_id.return_value = {
        "id": PID,
        "path": "test/page",
        "title": "Test Page",
        "content": "# Existing Content\n\nThis is the existing content.",
        "locale": "en",
        "isPublished": False,
        "tags": ["existing-tag"],
    }
    client.get_page_by_path.return_value = {
        "id": PID,
        "path": "test/page",
        "title": "Test Page",
        "content": "# Existing Content\n\nThis is the existing content.",
        "locale": "en",
        "isPublished": False,
        "tags": ["existing-tag"],
    }
    client.update_page.return_value = {"ok": True, "message": "Page updated successfully"}
    for key, value in overrides.items():
        setattr(client, key, value)
    return client


class TestUpdatePagePartial:
    def test_metadata_only_update_sends_only_that_field_and_fetches_nothing(self):
        client = make_client()
        pages.update_page(client, page_id=PID, is_published=True)

        client.get_page_by_id.assert_not_called()
        client.update_page.assert_called_with(
            page_id=PID,
            content=None,
            title=None,
            description=None,
            is_published=True,
            tags=None,
            reason=None,
            locale_relations=None,
        )

    def test_title_only_update(self):
        client = make_client()
        pages.update_page(client, page_id=PID, title="New Title")
        args = client.update_page.call_args.kwargs
        assert args["title"] == "New Title"
        assert args["content"] is None

    def test_description_only_update(self):
        client = make_client()
        pages.update_page(client, page_id=PID, description="New description")
        args = client.update_page.call_args.kwargs
        assert args["description"] == "New description"
        assert args["content"] is None

    def test_explicit_content_is_sent_unchanged(self):
        client = make_client()
        pages.update_page(client, page_id=PID, content="# New Content", is_published=True)
        args = client.update_page.call_args.kwargs
        assert args["content"] == "# New Content"
        assert args["is_published"] is True

    def test_resolves_page_by_path_and_uses_its_id(self):
        client = make_client()
        pages.update_page(client, path="test/page", locale="en", is_published=True)

        client.get_page_by_path.assert_called_with("test/page", "en")
        args = client.update_page.call_args.kwargs
        assert args["page_id"] == PID
        assert args["content"] is None

    def test_tags_are_passed_through_when_set(self):
        client = make_client()
        pages.update_page(client, page_id=PID, content="# Updated Content", tags=["new-tag"])
        assert client.update_page.call_args.kwargs["tags"] == ["new-tag"]

    def test_tags_are_left_alone_when_omitted(self):
        client = make_client()
        pages.update_page(client, page_id=PID, content="# Updated Content")
        assert client.update_page.call_args.kwargs["tags"] is None


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
                    "id": PID,
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
            pages.update_page(client, page_id=PID, content="short")
        client.update_page.assert_not_called()

    def test_error_names_old_and_new_lengths_and_the_escape_hatch(self):
        client = self._client_with_old_content()
        with pytest.raises(ValueError) as exc_info:
            pages.update_page(client, page_id=PID, content="short")
        message = str(exc_info.value)
        assert str(len(self._OLD_CONTENT)) in message
        # Must be the MCP-facing camelCase name (server.py's actual parameter),
        # not the internal Python kwarg — this text is what an LLM caller sees
        # and retries with.
        assert "confirmContentShrink" in message
        assert "confirm_content_shrink" not in message

    def test_allows_drastic_shrink_with_confirmation(self):
        client = self._client_with_old_content()
        pages.update_page(client, page_id=PID, content="short", confirm_content_shrink=True)
        assert client.update_page.call_args.kwargs["content"] == "short"

    def test_allows_similar_size_replacement_without_confirmation(self):
        client = self._client_with_old_content()
        new_content = self._OLD_CONTENT + " Plus a bit more text appended."
        pages.update_page(client, page_id=PID, content=new_content)
        assert client.update_page.call_args.kwargs["content"] == new_content

    def test_skips_guard_for_small_existing_pages(self):
        """Default fixture content (~51 chars) is under the guard's minimum length."""
        client = make_client()
        pages.update_page(client, page_id=PID, content="x")
        assert client.update_page.call_args.kwargs["content"] == "x"

    def test_does_not_apply_when_content_is_omitted(self):
        """Metadata-only updates never touch content, so the guard must not fire."""
        client = self._client_with_old_content()
        pages.update_page(client, page_id=PID, is_published=True)
        client.get_page_by_id.assert_not_called()
        assert client.update_page.call_args.kwargs["content"] is None

    def test_blocks_drastic_shrink_when_page_resolved_by_path(self):
        """current_page comes from get_page_by_path on this branch, not
        get_page_by_id — a distinct code path that must be guarded too."""
        client = make_client(
            get_page_by_path=MagicMock(
                return_value={
                    "id": PID,
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
            pages.update_page(client, page_id=MISSING_PID, content="# New")

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
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
        result = pages.create_page(
            client, path="new/page", title="New", content="content", description="desc"
        )
        assert result["page"]["id"] == NEW_PID
        assert "new/page" in result["message"]

    def test_rejects_invalid_editor(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.create_page(
                client, path="p", title="T", content="c", description="d", editor="Word Perfect"
            )


class TestGetPage:
    def test_returns_page_by_id(self):
        client = make_client()
        result = pages.get_page(client, page_id=PID)
        assert result["id"] == PID

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.get_page(client)

    def test_raises_when_page_not_found(self):
        client = make_client(get_page_by_id=MagicMock(return_value=None))
        with pytest.raises(ValueError, match="not found"):
            pages.get_page(client, page_id=PID)


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
        client.delete_page.assert_called_with(PID)

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.delete_page(client)


class TestMovePage:
    def test_moves_by_id(self):
        client = make_client()
        client.move_page.return_value = {"succeeded": True, "errorCode": 0, "message": "ok"}
        result = pages.move_page(client, page_id=PID, destination_path="new/path")
        assert result["to"] == "new/path"
        client.move_page.assert_called_with(PID, "new/path", "en", update_links=False)

    def test_raises_when_neither_id_nor_path(self):
        client = make_client()
        with pytest.raises(ValueError):
            pages.move_page(client, destination_path="new/path")


class TestCreatePageSourceTracking:
    """Phase 2: optional source_repo/source_ref/summary logged to page_history, never in content."""

    def test_logs_history_when_source_ref_given(self):
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
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
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
        pages.create_page(client, path="new/page", title="New", content="content", description="desc")
        assert history.get_page_history("new/page") == []

    def test_source_fields_never_reach_the_wikijs_client(self):
        """The visible page content/description must never carry the source ref."""
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
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
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
        result = pages.create_page(
            client, path="new/page", title="New", content="content", description="desc",
            source_ref="abc123",
        )
        assert result["page"]["id"] == NEW_PID
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
        pages.update_page(client, page_id=PID, is_published=True, source_ref="ghi789")
        entries = history.get_page_history("test/page")  # make_client()'s fixture page path
        assert len(entries) == 1
        assert entries[0]["source_ref"] == "ghi789"

    def test_no_history_row_when_no_source_fields_given(self):
        client = make_client()
        pages.update_page(client, page_id=PID, is_published=True)
        assert history.get_page_history("test/page") == []

    def test_logs_actual_page_locale_not_request_default_when_resolving_by_id(self):
        """Regression test: an ID-based update must log the page's real locale
        (from the auto-fetched current page), not silently default to "en"
        just because the caller's `locale` kwarg defaulted to "en"."""
        client = make_client(
            get_page_by_id=MagicMock(return_value={
                "id": PID, "path": "test/page", "title": "Test Page",
                "content": "c", "locale": "de", "isPublished": False, "tags": [],
            })
        )
        pages.update_page(client, page_id=PID, is_published=True, source_ref="abc123")
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
            client, page_id=PID, content="# New", title="New Title", description="New desc",
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


class TestReasonForChange:
    def test_create_passes_summary_as_reason(self):
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "new/page", "title": "New"}
        pages.create_page(client, path="new/page", title="New", content="c", description="d", summary="Initial docs")
        assert client.create_page.call_args.kwargs["reason"] == "Initial docs"

    def test_update_passes_summary_as_reason(self):
        client = make_client()
        pages.update_page(client, page_id=PID, title="T", summary="Fix typo")
        assert client.update_page.call_args.kwargs["reason"] == "Fix typo"

    def test_reason_is_capped_at_wiki_limit(self):
        client = make_client()
        pages.update_page(client, page_id=PID, title="T", summary="x" * 400)
        assert len(client.update_page.call_args.kwargs["reason"]) == 255

    def test_empty_summary_sends_no_reason(self):
        client = make_client()
        pages.update_page(client, page_id=PID, title="T")
        assert client.update_page.call_args.kwargs["reason"] is None


class TestMoveUpdateLinks:
    def test_update_links_is_passed_through(self):
        client = make_client()
        pages.move_page(client, page_id=PID, destination_path="new/path", update_links=True)
        client.move_page.assert_called_with(PID, "new/path", "en", update_links=True)

    def test_update_links_defaults_to_false(self):
        client = make_client()
        pages.move_page(client, page_id=PID, destination_path="new/path")
        client.move_page.assert_called_with(PID, "new/path", "en", update_links=False)


class TestVersionTools:
    def _versions(self, n=3):
        return [{"id": f"v{i}", "action": "updated", "versionDate": f"2026-11-0{i}T10:00:00.000Z",
                 "changedFields": ["content"], "reason": "r", "path": "test/page", "title": "T",
                 "author": {"id": "u", "name": "Admin", "email": "a@b"}, "via": None}
                for i in range(n, 0, -1)]

    def test_list_versions_by_id_limits_and_trims_fields(self):
        client = make_client()
        client.list_versions.return_value = self._versions(3)
        result = pages.list_page_versions(client, page_id=PID, limit=2)
        client.list_versions.assert_called_with(PID)
        assert [v["id"] for v in result["versions"]] == ["v3", "v2"]
        assert result["total"] == 3
        assert result["versions"][0]["author"] == "Admin"
        assert "email" not in str(result)

    def test_list_versions_by_path_resolves_id(self):
        client = make_client()
        client.list_versions.return_value = self._versions(1)
        pages.list_page_versions(client, path="test/page", locale="en")
        client.get_page_by_path.assert_called_with("test/page", "en")
        client.list_versions.assert_called_with(PID)

    def test_list_versions_requires_id_or_path(self):
        with pytest.raises(ValueError, match="id.*path|path.*id"):
            pages.list_page_versions(make_client())

    def test_get_version_returns_content(self):
        client = make_client()
        client.get_version.return_value = {"id": "v1", "content": "# Old", "action": "updated",
                                           "versionDate": "d", "reason": "", "path": "p", "title": "T",
                                           "author": {"name": "Admin"}, "meta": {"tags": ["a"]}}
        result = pages.get_page_version(client, page_id=PID, version_id="v1")
        assert result["content"] == "# Old"
        assert result["tags"] == ["a"]

    def test_get_version_not_found(self):
        client = make_client()
        client.get_version.return_value = None
        with pytest.raises(ValueError, match="not found"):
            pages.get_page_version(client, page_id=PID, version_id="nope")

    def test_version_id_is_validated(self):
        with pytest.raises(ValueError):
            pages.get_page_version(make_client(), page_id=PID, version_id="../x")


class TestRecycleBinTools:
    def test_list_deleted(self):
        client = make_client()
        client.list_deleted.return_value = [
            {"pageId": PID, "versionId": "v9", "path": "a", "title": "A", "locale": "en",
             "deletedAt": "2026-11-13T15:30:00Z", "deletedBy": {"id": "u", "name": "Admin"}, "editor": "markdown"},
        ]
        result = pages.list_deleted_pages(client, locale="en")
        client.list_deleted.assert_called_with("en")
        assert result["pages"][0] == {
            "pageId": PID, "versionId": "v9", "path": "a", "title": "A", "locale": "en",
            "deletedAt": "2026-11-13T15:30:00Z", "deletedBy": "Admin",
        }

    def test_restore_page(self):
        client = make_client()
        client.restore_page.return_value = {"ok": True, "page": {"id": PID, "path": "a", "title": "A"}}
        result = pages.restore_page(client, page_id=PID, version_id="v9")
        client.restore_page.assert_called_with(PID, "v9", path=None, locale=None, title=None)
        assert result["page"]["id"] == PID

    def test_restore_validates_destination_path(self):
        with pytest.raises(ValueError):
            pages.restore_page(make_client(), page_id=PID, version_id="v9", path="../bad")

    def test_delete_message_mentions_recycle_bin(self):
        client = make_client()
        client.delete_page.return_value = {"ok": True}
        result = pages.delete_page(client, page_id=PID)
        assert "recycle bin" in result["message"]


class TestListTags:
    def test_returns_tags_sorted_by_usage(self):
        client = make_client()
        client.list_tags.return_value = [{"tag": "b", "usageCount": 2}, {"tag": "a", "usageCount": 9}]
        result = pages.list_tags(client)
        assert [t["tag"] for t in result["tags"]] == ["a", "b"]


class TestLocaleRelationsTools:
    rel = [{"locale": "en", "path": "mcp/x"}]

    def test_create_passes_relations(self):
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "mcp/x", "title": "T"}
        pages.create_page(client, path="mcp/x", title="T", content="c", description="d",
                          locale="de-DE", locale_relations=self.rel)
        assert client.create_page.call_args.kwargs["locale_relations"] == self.rel

    def test_create_without_relations_passes_none(self):
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "p", "title": "T"}
        pages.create_page(client, path="p", title="T", content="c", description="d")
        assert client.create_page.call_args.kwargs["locale_relations"] is None

    def test_update_passes_relations_without_fetching(self):
        client = make_client()
        pages.update_page(client, page_id=PID, locale_relations=self.rel)
        client.get_page_by_id.assert_not_called()
        assert client.update_page.call_args.kwargs["locale_relations"] == self.rel

    def test_empty_list_unlinks(self):
        client = make_client()
        pages.update_page(client, page_id=PID, locale_relations=[])
        assert client.update_page.call_args.kwargs["locale_relations"] == []

    @pytest.mark.parametrize("bad", [
        [{"locale": "EN", "path": "a"}],
        [{"locale": "en", "path": "../a"}],
        [{"locale": "en"}],
        [{"locale": "en", "path": "a", "extra": "x"}],
        ["en"],
        [{"locale": "en", "path": "a"}] * 11,
    ])
    def test_invalid_relations_are_rejected(self, bad):
        client = make_client()
        with pytest.raises(ValueError):
            pages.update_page(client, page_id=PID, locale_relations=bad)
        client.update_page.assert_not_called()

    def test_get_page_returns_relations_and_publish_state(self):
        client = make_client(get_page_by_id=MagicMock(return_value={
            "id": PID, "path": "p", "title": "T", "locale": "en", "publishState": "draft",
            "isPublished": False, "localeRelations": [{"locale": "de-DE", "path": "p", "title": "T"}],
        }))
        result = pages.get_page(client, page_id=PID)
        assert result["localeRelations"] == [{"locale": "de-DE", "path": "p", "title": "T"}]
        assert result["publishState"] == "draft"


class TestRenderAfterWrite:
    """Wiki.js shows the stored render, not the source. A REST write does not refresh it:
    without a queued render readers (and search) keep the old page. Found live."""

    def test_update_with_content_queues_a_render(self):
        client = make_client()
        result = pages.update_page(client, page_id=PID, content="# New")
        client.render_page.assert_called_once_with(PID)
        assert result["renderQueued"] is True

    def test_update_without_content_does_not_render(self):
        client = make_client()
        result = pages.update_page(client, page_id=PID, title="T")
        client.render_page.assert_not_called()
        assert "renderQueued" not in result

    def test_update_by_path_renders_the_resolved_id(self):
        client = make_client()
        pages.update_page(client, path="test/page", locale="en", content="# New")
        client.render_page.assert_called_once_with(PID)

    def test_create_queues_a_render(self):
        client = make_client()
        client.create_page.return_value = {"id": NEW_PID, "path": "p", "title": "T"}
        result = pages.create_page(client, path="p", title="T", content="c", description="d")
        client.render_page.assert_called_once_with(NEW_PID)
        assert result["renderQueued"] is True

    def test_render_failure_does_not_fail_the_write(self):
        from tools.client import WikiJsError
        client = make_client()
        client.render_page.side_effect = WikiJsError("Wiki.js API error (HTTP 429): slow down")
        result = pages.update_page(client, page_id=PID, content="# New")
        assert result["renderQueued"] is False
        assert "429" in result["renderWarning"]
        assert "wikijs_render_page" in result["renderWarning"]

    def test_render_page_tool_by_path(self):
        client = make_client()
        client.render_page.return_value = {"ok": True, "message": "Page queued for rendering."}
        result = pages.render_page(client, path="test/page", locale="en")
        client.render_page.assert_called_once_with(PID)
        assert result["pageId"] == PID
