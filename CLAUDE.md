# wikijs-plugin — Claude Instructions

Wiki.js integration: MCP server (page CRUD/search) + a documentation skill that
orchestrates sub-agents to publish DE+EN docs. This file contains workflow
rules and routing that apply every session.

---

## Configuration & Path Resolution

Wiki.js API credentials live at: `~/.wikijs-plugin/.env` (`WIKIJS_API_URL`, `WIKIJS_API_TOKEN`).

First-time setup: `/wikijs-plugin:setup`

---

## MCP Server — Preferred Data Access

The `wikijs-mcp` server is the **preferred way to read/write Wiki.js pages** —
use its tools instead of asking the user to open the Wiki.js admin UI.

- **Read** -> `wikijs_get_page`, `wikijs_list_pages`, `wikijs_search_pages`
- **Write** -> `wikijs_create_page`, `wikijs_update_page`, `wikijs_move_page`
- **Destructive** -> `wikijs_delete_page` (irreversible — confirm with the user first)

## Skill Routing

| User Intent | Skill |
|------------|-------|
| "Wiki-Doku erstellen/aktualisieren", "/docs-wiki" | `/wikijs-plugin:docs-wiki` |
| "Doku gegen den Code prüfen", "stimmt die Doku?", "fehlt etwas in der Doku?", "Baseline-Lauf", "/source-check" | `/wikijs-plugin:source-check` |
| "liest sich unnatürlich", "klingt übersetzt", "/translation-check" | `/wikijs-plugin:translation-check` |
| "Plugin not responding", first install | `/wikijs-plugin:setup` |

---

## Windows Compatibility

Mandatory — see `servers/wikijs-mcp-server/`'s dedicated venv (`~/.wikijs-plugin/venv/`),
`bin/run-server` / `bin/run-server.cmd` OS-agnostic wrapper, and `skills/setup/SKILL.md`'s
`py -3` Store-alias fallback chain. All file I/O uses `encoding="utf-8"` explicitly.

## Mandatory Smoke Tests

```bash
pytest tests/smoke/test_mcp_server.py -q
pytest tests/smoke/test_skills.py -q
pytest tests/smoke/test_knowledge.py -q
pytest tests/smoke/test_state.py -q
pytest tests/smoke/test_cross_platform.py -q
pytest tests/smoke/test_translation_check.py -q
pytest tests/smoke/test_source_check.py -q
pytest tests/smoke/test_source_check_inventory.py -q
pytest servers/wikijs-mcp-server/tests -q
```
