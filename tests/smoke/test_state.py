"""Smoke: state-persistence check for this plugin's shape.

wikijs-plugin is stateless — the MCP server is a thin GraphQL client with no
local DB/session/project registry (unlike mm-dev-toolkit/project-hub, which
this checklist item was written for). This file exists explicitly, rather
than being omitted, so the mandatory 5-file smoke-test checklist stays
satisfiable and the "why" is on record instead of silently missing.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_no_local_state_store_shipped():
    """Documents the current state; update this test (not just delete it) if
    this plugin ever gains local persistence (SQLite DB, session file, etc.)."""
    home_marker = ROOT / ".wikijs-plugin"
    assert not home_marker.exists(), (
        "A local state directory now exists in-repo but tests/smoke/test_state.py "
        "was never updated to validate it"
    )
