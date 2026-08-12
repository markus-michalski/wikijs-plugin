"""Tests for input validation (port of the TS Zod schema constraints)."""
from __future__ import annotations

import pytest
from tools.validation import (
    MAX_CONTENT_SIZE,
    MAX_TAG_LENGTH,
    MAX_TAGS_PER_PAGE,
    validate_content,
    validate_locale,
    validate_page_id,
    validate_path,
    validate_tags,
)


class TestValidateLocale:
    @pytest.mark.parametrize("locale", ["en", "de", "en-US", "de-DE"])
    def test_accepts_valid_locales(self, locale):
        assert validate_locale(locale) == locale

    @pytest.mark.parametrize("locale", ["EN", "e", "eng", "en_US", "123", ""])
    def test_rejects_invalid_locales(self, locale):
        with pytest.raises(ValueError):
            validate_locale(locale)


class TestValidatePath:
    @pytest.mark.parametrize("path", ["home", "osticket/plugin-name", "a-b_c/d", "x"])
    def test_accepts_valid_paths(self, path):
        assert validate_path(path) == path

    def test_rejects_double_dot(self):
        with pytest.raises(ValueError):
            validate_path("../etc/passwd")

    def test_rejects_double_slash(self):
        with pytest.raises(ValueError):
            validate_path("foo//bar")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_path("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            validate_path("a" * 501)

    def test_rejects_leading_slash(self):
        with pytest.raises(ValueError):
            validate_path("/leading-slash")


class TestValidateTags:
    def test_accepts_empty_and_normal_tags(self):
        assert validate_tags([]) == []
        assert validate_tags(["tutorial", "dev"]) == ["tutorial", "dev"]

    def test_rejects_tag_too_long(self):
        with pytest.raises(ValueError):
            validate_tags(["a" * (MAX_TAG_LENGTH + 1)])

    def test_rejects_too_many_tags(self):
        with pytest.raises(ValueError):
            validate_tags([f"tag{i}" for i in range(MAX_TAGS_PER_PAGE + 1)])


class TestValidateContent:
    def test_accepts_normal_content(self):
        assert validate_content("# Hello") == "# Hello"

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_content("")

    def test_rejects_too_large(self):
        with pytest.raises(ValueError):
            validate_content("a" * (MAX_CONTENT_SIZE + 1))


class TestValidatePageId:
    def test_accepts_positive_int(self):
        assert validate_page_id(42) == 42

    @pytest.mark.parametrize("value", [0, -1, -100])
    def test_rejects_non_positive(self, value):
        with pytest.raises(ValueError):
            validate_page_id(value)
