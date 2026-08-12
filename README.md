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

### Skill (`skills/docs-wiki/`)

`/wikijs-plugin:docs-wiki` — orchestrates documentation sub-agents (docs-architect, mermaid-expert, tutorial-engineer, api-documenter, reference-builder) to create/update Wiki.js pages in DE+EN.

## Requirements

- Python 3.11+ (Windows: the `py` launcher works even where `python`/`python3` are Microsoft Store alias stubs)
- Wiki.js instance (v2.x or v3.x)
- Wiki.js API token with page management permissions

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT License — see [LICENSE](./LICENSE) for details

## Author

**Markus Michalski**
- Website: [markus-michalski.net](https://markus-michalski.net)
- GitHub: [@markus-michalski](https://github.com/markus-michalski)

## Links

- [Full Documentation](https://faq.markus-michalski.net/en/mcp/wikijs-plugin) (English)
- [Vollständige Dokumentation](https://faq.markus-michalski.net/de/mcp/wikijs-plugin) (Deutsch)
- [Changelog](./CHANGELOG.md)
- Original standalone TypeScript MCP server: [wikijs-mcp-server](https://github.com/markus-michalski/wikijs-mcp-server)
