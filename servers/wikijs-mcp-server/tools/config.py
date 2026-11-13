"""Configuration loader for the Wiki.js MCP server."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class MissingCredentialsError(RuntimeError):
    """WIKIJS_API_URL / WIKIJS_API_TOKEN are not configured."""


def load_credentials() -> tuple[str, str]:
    """Load WIKIJS_API_URL (the wiki's base URL) / WIKIJS_API_TOKEN.

    Looks for ~/.wikijs-plugin/.env first (survives plugin updates), falling
    back to the current working directory's .env for local development.

    Raises MissingCredentialsError (a plain RuntimeError, never SystemExit)
    so this stays safe to call from inside a tool handler — server._get_client()
    calls it lazily on first tool use, and SystemExit (a BaseException) would
    blow straight through the MCP framework's per-call exception wrapping
    instead of coming back as a normal tool error. run.py's startup path
    catches this exception itself and turns it into a fail-fast process exit.
    """
    env_path = Path.home() / ".wikijs-plugin" / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    api_url = os.environ.get("WIKIJS_API_URL")
    api_token = os.environ.get("WIKIJS_API_TOKEN")

    if not api_url or not api_token:
        raise MissingCredentialsError(
            "Missing required environment variables WIKIJS_API_URL / WIKIJS_API_TOKEN. "
            f"Set them in {env_path} (see .env.example)."
        )

    if api_url.rstrip("/").endswith("/graphql"):
        base_url = api_url.rstrip("/").removesuffix("/graphql")
        raise MissingCredentialsError(
            "WIKIJS_API_URL still points at the Wiki.js 2 GraphQL endpoint. "
            "This plugin talks to Wiki.js 3 (REST): set WIKIJS_API_URL to the wiki's "
            f"base URL (e.g. {base_url}) and WIKIJS_API_TOKEN to a personal access "
            f"token. Config file: {env_path}"
        )

    return api_url, api_token


def load_site_id() -> str | None:
    """Optional WIKIJS_SITE_ID: skips the hostname lookup via /_api/bootstrap.

    Only needed when the wiki is reached under a hostname that does not match a
    site (e.g. an internal address behind a proxy). Call after load_credentials(),
    which loads the .env file.
    """
    return (os.environ.get("WIKIJS_SITE_ID") or "").strip() or None
