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

- **Read** -> `wikijs_get_page`, `wikijs_list_pages`, `wikijs_search_pages`, `wikijs_list_tags`
- **History/undo** -> `wikijs_list_page_versions` + `wikijs_get_page_version` (roll back by sending the old content to `wikijs_update_page`), `wikijs_list_deleted_pages` + `wikijs_restore_page`
- **Write** -> `wikijs_create_page`, `wikijs_update_page`, `wikijs_move_page`. Create/update queue a render so readers see the change; if the result says `renderQueued: false`, run `wikijs_render_page`
- **Destructive** -> `wikijs_delete_page` (moves the page to the recycle bin, restorable with `wikijs_restore_page` — still confirm with the user first, the page is offline until restored)

## Skill Routing

| User Intent | Skill |
|------------|-------|
| "Wiki-Doku erstellen/aktualisieren", "/docs-wiki" | `/wikijs-plugin:docs-wiki` |
| "Screenshots geliefert", "Screenshot-URLs", "Seiten freigeben/veröffentlichen" (Draft aus einem früheren Lauf) | `/wikijs-plugin:docs-wiki` (Freigabe-Gate) |
| "Doku gegen den Code prüfen", "stimmt die Doku?", "fehlt etwas in der Doku?", "Baseline-Lauf", "/source-check" | `/wikijs-plugin:source-check` |
| "liest sich unnatürlich", "klingt übersetzt", "/translation-check" | `/wikijs-plugin:translation-check` |
| "Plugin not responding", first install | `/wikijs-plugin:setup` |

---

## Neue Doku: Draft-first mit Screenshot-Vorschlägen

Neue Wiki.js-Seiten (Modus "Neue Doku") werden **immer als Draft** angelegt (`isPublished: false`),
mit Screenshot-Vorschlägen und Platzhalter-Markern im Text. Veröffentlicht wird **nie ohne
Freigabe**: erst wenn der User die Screenshots als fertige CDN-URLs geliefert hat (und die Prüfung
besteht) oder ausdrücklich die Veröffentlichung verlangt. Die CDN-URLs sind signiert, nie selbst
erzeugen. Details: `skills/docs-wiki/templates/SCREENSHOTS.md` und "Draft-first" / "Freigabe-Gate"
in `skills/docs-wiki/templates/DOCS_COMMON.md`. Update und Qualitäts-Upgrade lassen live Seiten live.

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
pytest tests/smoke/test_screenshots.py -q
pytest servers/wikijs-mcp-server/tests -q
```
