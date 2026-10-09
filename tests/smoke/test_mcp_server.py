"""Smoke: MCP server defines all expected tool handlers."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SERVER_PY = ROOT / "servers" / "wikijs-mcp-server" / "server.py"
SERVER_DIR = ROOT / "servers" / "wikijs-mcp-server"

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


def _get_defined_functions() -> set[str]:
    tree = ast.parse(SERVER_PY.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def test_server_file_exists():
    assert SERVER_PY.exists(), f"server.py not found: {SERVER_PY}"


def test_server_is_valid_python():
    ast.parse(SERVER_PY.read_text(encoding="utf-8"))


def test_all_tools_defined():
    """All expected @mcp.tool() handlers are defined in server.py."""
    defined = _get_defined_functions()
    missing = EXPECTED_TOOLS - defined
    assert not missing, f"Missing tool functions: {sorted(missing)}"


def test_server_module_actually_imports_and_registers_tools_without_credentials(monkeypatch):
    """Real import + tool registration, not just ast.parse — regression guard
    against an import that would only fail at actual `mcp.run()` time (e.g. a
    removed SDK symbol). Deletes any local WIKIJS_API_URL/TOKEN first: import
    must succeed without them, since the client is constructed lazily on
    first tool call (see server._get_client / servers/wikijs-mcp-server/tools/config.py).
    """
    monkeypatch.delenv("WIKIJS_API_URL", raising=False)
    monkeypatch.delenv("WIKIJS_API_TOKEN", raising=False)
    sys.path.insert(0, str(SERVER_DIR))
    sys.modules.pop("server", None)
    import asyncio

    import server

    tool_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    missing = EXPECTED_TOOLS - tool_names
    assert not missing, f"Registered tools missing at runtime: {sorted(missing)}"


def test_claude_md_has_skill_routing_heading():
    """CLAUDE.md must exist and contain the ## Skill Routing heading."""
    claude_md = ROOT / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md not found at repo root"
    assert "## Skill Routing" in claude_md.read_text(encoding="utf-8"), (
        "CLAUDE.md is missing '## Skill Routing' section"
    )
