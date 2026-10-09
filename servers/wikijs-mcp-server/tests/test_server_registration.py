"""Server-level smoke tests: import, tool registration, error-wrapping behaviour."""
from __future__ import annotations

import asyncio

EXPECTED_TOOLS = {
    "wikijs_create_page",
    "wikijs_get_page",
    "wikijs_list_pages",
    "wikijs_search_pages",
    "wikijs_update_page",
    "wikijs_delete_page",
    "wikijs_move_page",
    "wikijs_get_page_history",
    "wikijs_mark_verified",
    "wikijs_get_verified_refs",
}


def test_server_module_imports_without_credentials(monkeypatch):
    """`import server` must not require WIKIJS_API_URL/WIKIJS_API_TOKEN — the
    client is constructed lazily on first tool call (see server._get_client)."""
    monkeypatch.delenv("WIKIJS_API_URL", raising=False)
    monkeypatch.delenv("WIKIJS_API_TOKEN", raising=False)
    import server  # noqa: F401 — import success is the assertion


def test_importing_server_does_not_touch_the_page_history_db(monkeypatch):
    """Regression test: `import server` must not touch the page-history DB at
    all — the schema is ensured lazily on first real DB use inside
    db.db_connection(), not at import time. A prior version called
    db.init_db() unconditionally at module scope, which (a) created a real
    ~/.wikijs-plugin/wikijs-plugin.db on every `import server` including in
    tests, defeating conftest.py's per-test DB isolation for anything that
    imports server before its own fixtures run, and (b) meant a broken/
    unwritable DB path took down all 7 unrelated Wiki.js tools at import
    time instead of only degrading page-history logging."""
    import sys

    import tools.db as db_module

    def _fail(*a, **kw):
        raise AssertionError("import server must not touch the page-history DB")

    monkeypatch.setattr(db_module, "init_db", _fail)
    monkeypatch.setattr(db_module, "db_connection", _fail)
    monkeypatch.setattr(db_module, "get_connection", _fail)
    sys.modules.pop("server", None)

    import server  # noqa: F401


def test_all_tools_registered():
    from server import mcp

    async def _list():
        return await mcp.list_tools()

    tools = asyncio.run(_list())
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"Missing registered tools: {sorted(missing)}"


def test_tool_error_is_wrapped_not_raised(monkeypatch):
    """A ValueError raised inside a tool handler (e.g. missing id/path) must
    come back as an MCP error result, not propagate as a Python exception —
    verifies pages.py can rely on plain `raise ValueError(...)` without a
    hand-rolled error handler (unlike the original TS handleToolError)."""
    from mcp.client import Client
    from server import mcp

    async def _call():
        async with Client(mcp) as client:
            return await client.call_tool("wikijs_get_page", {})

    result = asyncio.run(_call())
    assert result.is_error


def test_tool_success_returns_structured_content(monkeypatch):
    from unittest.mock import MagicMock

    import server
    from mcp.client import Client

    fake_client = MagicMock()
    fake_client.get_page_by_id.return_value = {
        "id": 1, "path": "a", "title": "A", "description": "", "content": "c",
        "contentType": "markdown", "isPublished": True, "locale": "en",
    }
    monkeypatch.setattr(server, "_get_client", lambda: fake_client)

    async def _call():
        async with Client(server.mcp) as client:
            return await client.call_tool("wikijs_get_page", {"id": 1})

    result = asyncio.run(_call())
    assert not result.is_error
    assert result.structured_content["id"] == 1


def test_get_page_history_tool_requires_no_wikijs_client(monkeypatch):
    """wikijs_get_page_history is a local DB read — must work without ever
    touching _get_client()/Wiki.js credentials."""
    import server
    from mcp.client import Client
    from tools.history import log_page_change

    def _fail(*a, **kw):
        raise AssertionError("wikijs_get_page_history must not construct a WikiJsClient")

    monkeypatch.setattr(server, "_get_client", _fail)
    log_page_change(page_path="mcp/wikijs-plugin", locale="de", source_ref="abc123")

    async def _call():
        async with Client(server.mcp) as client:
            return await client.call_tool("wikijs_get_page_history", {"path": "mcp/wikijs-plugin"})

    result = asyncio.run(_call())
    assert not result.is_error
    assert result.structured_content["entries"][0]["source_ref"] == "abc123"


def test_verification_tools_are_local_db_only(monkeypatch):
    """mark_verified and get_verified_refs only touch the local DB. The baseline
    run must work for passing pages without rewriting them on Wiki.js."""
    import server
    from mcp.client import Client

    def _fail(*a, **kw):
        raise AssertionError("verification tools must not construct a WikiJsClient")

    monkeypatch.setattr(server, "_get_client", _fail)

    async def _call():
        async with Client(server.mcp) as client:
            marked = await client.call_tool(
                "wikijs_mark_verified",
                {
                    "path": "mcp/wikijs-plugin", "locale": "de", "sourceRepo": "wikijs-plugin",
                    "sourceRef": "abc123", "pageUpdatedAt": "2026-10-01T10:00:00.000Z",
                },
            )
            listed = await client.call_tool("wikijs_get_verified_refs", {"path": "mcp/wikijs-plugin"})
            return marked, listed

    marked, listed = asyncio.run(_call())
    assert not marked.is_error
    assert not listed.is_error
    entry = listed.structured_content["entries"][0]
    assert entry["source_ref"] == "abc123"
    assert entry["page_updated_at"] == "2026-10-01T10:00:00.000Z"


def _mark_call(**overrides):
    import server
    from mcp.client import Client

    args = {
        "path": "p", "locale": "de", "sourceRepo": "r", "sourceRef": "abc",
        "pageUpdatedAt": "2026-10-01T10:00:00.000Z",
    }
    args.update(overrides)

    async def _call():
        async with Client(server.mcp) as client:
            return await client.call_tool("wikijs_mark_verified", args)

    return asyncio.run(_call())


def test_mark_verified_rejects_empty_ref():
    assert _mark_call(sourceRef="").is_error


def test_mark_verified_rejects_missing_page_state():
    assert _mark_call(pageUpdatedAt="").is_error


def test_mark_verified_rejects_invalid_locale():
    assert _mark_call(locale="not a locale!").is_error


def test_mark_verified_normalizes_leading_slash_to_the_page_path():
    """The URL form '/mcp/foo' and the API form 'mcp/foo' must hit the same row,
    otherwise the baseline keeps reporting a verified page as unchecked."""
    import server
    from mcp.client import Client

    assert not _mark_call(path="/mcp/foo").is_error

    async def _call():
        async with Client(server.mcp) as client:
            return await client.call_tool("wikijs_get_verified_refs", {"path": "mcp/foo"})

    entries = asyncio.run(_call()).structured_content["entries"]
    assert [e["page_path"] for e in entries] == ["mcp/foo"]


def test_mark_verified_rejects_path_traversal_and_double_slash():
    assert _mark_call(path="a/../b").is_error
    assert _mark_call(path="a//b").is_error


def test_mark_verified_rejects_paths_that_could_only_create_orphan_keys():
    """'//foo' must not be stored as '/foo', and 'foo/' or inner whitespace never match
    the path wikijs_list_pages returns, so the baseline would report the page unchecked forever."""
    assert _mark_call(path="//foo").is_error
    assert _mark_call(path="foo/").is_error
    assert _mark_call(path="/foo/ ").is_error
    assert _mark_call(path="foo bar").is_error
    assert _mark_call(path="/").is_error


def test_page_history_tool_describes_the_verified_field():
    import server

    assert "verified" in (server.wikijs_get_page_history.__doc__ or "")


def test_move_page_tool_notes_that_verified_refs_stay_on_the_old_path():
    import server

    doc = server.wikijs_move_page.__doc__ or ""
    assert "verified" in doc.lower()
