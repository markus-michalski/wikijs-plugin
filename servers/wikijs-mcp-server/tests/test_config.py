"""Tests for the credentials/config loader."""
from __future__ import annotations

import pytest
from tools import config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("WIKIJS_API_URL", "WIKIJS_API_TOKEN", "WIKIJS_SITE_ID"):
        monkeypatch.delenv(var, raising=False)
    # No ~/.wikijs-plugin/.env and no cwd .env leaking into the test.
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)


def test_returns_url_and_token(monkeypatch):
    monkeypatch.setenv("WIKIJS_API_URL", "https://wiki.example.com")
    monkeypatch.setenv("WIKIJS_API_TOKEN", "tok")
    assert config.load_credentials() == ("https://wiki.example.com", "tok")


def test_missing_credentials_raise(monkeypatch):
    with pytest.raises(config.MissingCredentialsError):
        config.load_credentials()


@pytest.mark.parametrize("url", ["https://wiki.example.com/graphql", "https://wiki.example.com/graphql/"])
def test_graphql_url_is_rejected_with_migration_hint(monkeypatch, url):
    monkeypatch.setenv("WIKIJS_API_URL", url)
    monkeypatch.setenv("WIKIJS_API_TOKEN", "tok")
    with pytest.raises(config.MissingCredentialsError, match="Wiki.js 3.*base URL"):
        config.load_credentials()


def test_site_id_is_optional(monkeypatch):
    assert config.load_site_id() is None
    monkeypatch.setenv("WIKIJS_SITE_ID", " 40a75b1e-4ef8-44fe-9d65-92d7b0e243df ")
    assert config.load_site_id() == "40a75b1e-4ef8-44fe-9d65-92d7b0e243df"
