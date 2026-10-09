"""Tests for page-history logging/retrieval (Phase 2: source-ref tracking)."""
from __future__ import annotations

import pytest
from tools.history import get_page_history, get_verified_refs, log_page_change, mark_verified

UPDATED_AT = "2026-10-01T10:00:00.000Z"


def _mark(**kwargs):
    kwargs.setdefault("page_updated_at", UPDATED_AT)
    mark_verified(**kwargs)


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


class TestVerifiedFlag:
    def test_plain_log_is_unverified(self):
        log_page_change(page_path="p", locale="de", source_ref="abc")
        assert get_page_history("p")[0]["verified"] == 0

    def test_log_with_verified_flag_is_exposed_in_history(self):
        log_page_change(page_path="p", locale="de", source_ref="abc", verified=True)
        assert get_page_history("p")[0]["verified"] == 1


class TestMarkVerified:
    def test_marks_page_verified_at_ref(self):
        _mark(page_path="p", locale="de", source_repo="proj", source_ref="abc", summary="baseline")
        refs = get_verified_refs(page_path="p", locale="de")
        assert [(r["page_path"], r["locale"], r["source_ref"], r["source_repo"]) for r in refs] == [
            ("p", "de", "abc", "proj")
        ]
        assert refs[0]["verified_at"]

    def test_requires_a_ref(self):
        with pytest.raises(ValueError, match="source_ref"):
            _mark(page_path="p", locale="de", source_repo="proj", source_ref="")

    def test_requires_a_repo(self):
        with pytest.raises(ValueError, match="source_repo"):
            _mark(page_path="p", locale="de", source_repo="", source_ref="abc")

    def test_requires_the_page_state_it_was_checked_at(self):
        """Without the page's updatedAt a later manual edit in Wiki.js cannot be
        detected, so the marker would stay valid for content it never covered."""
        with pytest.raises(ValueError, match="page_updated_at"):
            mark_verified(page_path="p", locale="de", source_repo="proj", source_ref="abc", page_updated_at=" ")

    def test_stores_page_updated_at_and_returns_it(self):
        _mark(page_path="p", locale="de", source_repo="proj", source_ref="abc", page_updated_at="2026-10-02T08:00:00Z")
        assert get_verified_refs(page_path="p", locale="de")[0]["page_updated_at"] == "2026-10-02T08:00:00Z"

    def test_strips_whitespace_before_storing(self):
        """A trailing newline from `git rev-parse HEAD` would otherwise break
        `git diff {ref}..HEAD` and silently force a full re-check every time."""
        _mark(page_path="p", locale="de", source_repo=" proj ", source_ref="abc123\n")
        ref = get_verified_refs(page_path="p", locale="de")[0]
        assert (ref["source_repo"], ref["source_ref"]) == ("proj", "abc123")

    def test_same_second_writes_still_pick_the_latest(self):
        for ref in ("first", "second", "third"):
            _mark(page_path="p", locale="de", source_repo="proj", source_ref=ref)
        assert get_verified_refs(page_path="p", locale="de")[0]["source_ref"] == "third"

    def test_newest_verified_ref_wins(self):
        _mark(page_path="p", locale="de", source_repo="proj", source_ref="old")
        _mark(page_path="p", locale="de", source_repo="proj", source_ref="new")
        assert get_verified_refs(page_path="p", locale="de")[0]["source_ref"] == "new"

    def test_unverified_write_never_counts_as_verified(self):
        log_page_change(page_path="p", locale="de", source_repo="proj", source_ref="written-at")
        assert get_verified_refs(page_path="p", locale="de") == []

    def test_later_unverified_write_does_not_hide_the_verified_ref(self):
        _mark(page_path="p", locale="de", source_repo="proj", source_ref="checked")
        log_page_change(page_path="p", locale="de", source_repo="proj", source_ref="newer-but-unchecked")
        assert get_verified_refs(page_path="p", locale="de")[0]["source_ref"] == "checked"


class TestGetVerifiedRefs:
    def test_unknown_page_has_no_verified_ref(self):
        assert get_verified_refs(page_path="no/such/page") == []

    def test_without_filter_lists_one_row_per_page_and_locale(self):
        _mark(page_path="a", locale="de", source_repo="r", source_ref="1")
        _mark(page_path="a", locale="en", source_repo="r", source_ref="2")
        _mark(page_path="b", locale="de", source_repo="r", source_ref="3")
        _mark(page_path="b", locale="de", source_repo="r", source_ref="4")
        refs = get_verified_refs()
        assert {(r["page_path"], r["locale"]): r["source_ref"] for r in refs} == {
            ("a", "de"): "1", ("a", "en"): "2", ("b", "de"): "4",
        }

    def test_locale_filter(self):
        _mark(page_path="a", locale="de", source_repo="r", source_ref="1")
        _mark(page_path="a", locale="en", source_repo="r", source_ref="2")
        assert [r["locale"] for r in get_verified_refs(page_path="a", locale="en")] == ["en"]
