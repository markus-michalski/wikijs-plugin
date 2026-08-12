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
