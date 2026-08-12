"""Smoke: knowledge-base check for this plugin's shape.

wikijs-plugin ships no project-type/task-type knowledge base (unlike
mm-dev-toolkit/project-hub) — it's a single-purpose plugin (one MCP server,
one content skill), so there is nothing here to validate. This file exists
(rather than being omitted) so the mandatory 5-file smoke-test checklist from
`project-types/claude-plugin/README.md` stays satisfiable and explicit about
why, instead of silently missing.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_no_knowledge_directory_shipped():
    """Documents the current state; update this test (not just delete it) if
    a knowledge/ directory is ever added to this plugin."""
    assert not (ROOT / "knowledge").exists(), (
        "A knowledge/ directory now exists but tests/smoke/test_knowledge.py "
        "was never updated to validate it"
    )
