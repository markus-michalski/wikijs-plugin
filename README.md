# wikijs-plugin

**Claude Code plugin for Wiki.js integration** — MCP server for page CRUD/search plus a `docs-wiki` skill that orchestrates documentation sub-agents to publish DE+EN docs.

Combines the previously separate [`wikijs-mcp-server`](https://github.com/markus-michalski/wikijs-mcp-server) (originally TypeScript, ported to Python here — see [CHANGELOG](./CHANGELOG.md)) and `mm-skills/docs-wiki` into a single installable plugin, following the structure of [`mm-dev-toolkit`](https://github.com/markus-michalski/mm-dev-toolkit) and [`project-hub`](https://github.com/markus-michalski/project-hub).

## Documentation

**[Complete Documentation & FAQ](https://faq.markus-michalski.net/en/mcp/wikijs-plugin)**

## Installation

Install via the Claude Code plugin marketplace mechanism (`marketplace add` + `plugin install`), same as `mm-dev-toolkit`/`project-hub`. Then run `/wikijs-plugin:setup` — it creates a dedicated venv at `~/.wikijs-plugin/venv/` and copies the `.env` template.

Configure Wiki.js credentials in `~/.wikijs-plugin/.env`:

```
WIKIJS_API_URL=https://your-wikijs-installation/graphql
WIKIJS_API_TOKEN=your-api-token-here
```

## Components

### MCP Server (`servers/wikijs-mcp-server/`)

Python (`mcp[cli]` + `httpx`), dedicated venv — same pattern as `mm-dev-toolkit`/`project-hub`.

| Tool | Description |
|------|-------------|
| `wikijs_create_page` | Create new wiki pages with Markdown or HTML |
| `wikijs_update_page` | Update existing pages (content, title, tags) |
| `wikijs_get_page` | Retrieve full page content and metadata |
| `wikijs_list_pages` | List pages with pagination and filtering |
| `wikijs_search_pages` | Full-text search across wiki pages |
| `wikijs_delete_page` | Permanently delete pages |
| `wikijs_move_page` | Move pages to new paths |
| `wikijs_get_page_history` | Read a page's logged change history (Phase 2, see below) |

### Skill (`skills/docs-wiki/`)

`/wikijs-plugin:docs-wiki` — orchestrates documentation sub-agents (docs-architect, mermaid-expert, tutorial-engineer, api-documenter, reference-builder) to create/update Wiki.js pages in DE+EN.

### Skill (`skills/translation-check/`)

`/wikijs-plugin:translation-check` — checks that DE (and optionally EN) page content reads
naturally instead of like a literal translation. `docs-wiki` runs it as a mandatory gate before
publishing: FAIL blocks the publish, WARN asks you, PASS continues. It uses a shipped glossary of
terms that stay as loanwords (e.g. "Cronjob"); add your own entries in
`~/.wikijs-plugin/glossary.local.md` (optional, takes precedence over the shipped glossary).

### Page-History Tracking

`wikijs_create_page`/`wikijs_update_page` accept optional `sourceRepo`/`sourceRef`/`summary`
parameters, logged to a local SQLite DB (`~/.wikijs-plugin/wikijs-plugin.db`) — **never** written
into the visible page content or description, so the project's "no version numbers in body text"
Wiki.js convention stays intact. `docs-wiki` passes the target project's `git rev-parse HEAD` as
`sourceRef` automatically when available. Read the log back with `wikijs_get_page_history`.

## Requirements

- Python 3.11+ (Windows: the `py` launcher works even where `python`/`python3` are Microsoft Store alias stubs)
- Wiki.js instance (v2.x or v3.x)
- Wiki.js API token with page management permissions

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[![License: PolyForm NC 1.0.0](https://img.shields.io/badge/license-PolyForm%20NC%201.0.0-red.svg?style=for-the-badge)](LICENSE.md)

[PolyForm Noncommercial License 1.0.0](LICENSE.md) — source-available,
personal and non-commercial use only. Not OSI Open Source.
Commercial use requires explicit permission; contact the maintainer.

## Author

**Markus Michalski**
- Website: [markus-michalski.net](https://markus-michalski.net)
- GitHub: [@markus-michalski](https://github.com/markus-michalski)

## Links

- [Full Documentation](https://faq.markus-michalski.net/en/mcp/wikijs-plugin) (English)
- [Vollständige Dokumentation](https://faq.markus-michalski.net/de/mcp/wikijs-plugin) (Deutsch)
- [Changelog](./CHANGELOG.md)
- Original standalone TypeScript MCP server: [wikijs-mcp-server](https://github.com/markus-michalski/wikijs-mcp-server)
