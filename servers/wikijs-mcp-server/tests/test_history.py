"""Tests for page-history logging/retrieval (Phase 2: source-ref tracking)."""
from __future__ import annotations

from tools.history import get_page_history, log_page_change


class TestLogPageChange:
    def test_logs_a_row_retrievable_by_path(self):
        log_page_change(
            page_path="mcp/wikijs-plugin", locale="de",
            source_repo="wikijs-plugin", source_ref="abc123", summary="Initial docs",
        )
        entries = get_page_history("mcp/wikijs-plugin")
        assert len(entries) == 1
        assert entries[0]["source_repo"] == "wikijs-plugin"
        assert entries[0]["source_ref"] == "abc123"
        assert entries[0]["summary"] == "Initial docs"
        assert entries[0]["locale"] == "de"

    def test_defaults_are_empty_strings_not_null(self):
        log_page_change(page_path="mcp/wikijs-plugin", locale="en")
        entries = get_page_history("mcp/wikijs-plugin", locale="en")
        assert entries[0]["source_repo"] == ""
        assert entries[0]["source_ref"] == ""
        assert entries[0]["summary"] == ""

    def test_changed_at_is_populated(self):
        log_page_change(page_path="mcp/wikijs-plugin", locale="de", source_ref="abc123")
        entries = get_page_history("mcp/wikijs-plugin")
        assert entries[0]["changed_at"]


class TestGetPageHistory:
    def test_returns_empty_list_for_unknown_page(self):
        assert get_page_history("no/such/page") == []

    def test_orders_newest_first(self):
        log_page_change(page_path="p", locale="en", source_ref="first")
        log_page_change(page_path="p", locale="en", source_ref="second")
        log_page_change(page_path="p", locale="en", source_ref="third")
        entries = get_page_history("p")
        assert [e["source_ref"] for e in entries] == ["third", "second", "first"]

    def test_filters_by_locale(self):
        log_page_change(page_path="p", locale="de", source_ref="de-ref")
        log_page_change(page_path="p", locale="en", source_ref="en-ref")
        de_entries = get_page_history("p", locale="de")
        assert [e["source_ref"] for e in de_entries] == ["de-ref"]

    def test_no_locale_filter_returns_all_locales(self):
        log_page_change(page_path="p", locale="de", source_ref="de-ref")
        log_page_change(page_path="p", locale="en", source_ref="en-ref")
        entries = get_page_history("p")
        assert {e["source_ref"] for e in entries} == {"de-ref", "en-ref"}

    def test_respects_limit(self):
        for i in range(5):
            log_page_change(page_path="p", locale="en", source_ref=f"ref-{i}")
        entries = get_page_history("p", limit=2)
        assert len(entries) == 2
        assert [e["source_ref"] for e in entries] == ["ref-4", "ref-3"]

    def test_scoped_to_exact_page_path(self):
        log_page_change(page_path="a/b", locale="en", source_ref="ab")
        log_page_change(page_path="a/b/c", locale="en", source_ref="abc")
        entries = get_page_history("a/b")
        assert [e["source_ref"] for e in entries] == ["ab"]
