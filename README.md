# wikijs-plugin

**Claude Code plugin for Wiki.js integration** — MCP server for page CRUD/search plus a `docs-wiki` skill that orchestrates documentation sub-agents to publish DE+EN docs.

Combines the previously separate [`wikijs-mcp-server`](https://github.com/markus-michalski/wikijs-mcp-server) (originally TypeScript, ported to Python here — see [CHANGELOG](./CHANGELOG.md)) and `mm-skills/docs-wiki` into a single installable plugin, following the structure of [`mm-dev-toolkit`](https://github.com/markus-michalski/mm-dev-toolkit) and [`project-hub`](https://github.com/markus-michalski/project-hub).

## Documentation

**[Complete Documentation & FAQ](https://faq.markus-michalski.net/plugins/wikijs-plugin)**

## Installation

Install via the Claude Code plugin marketplace mechanism (`marketplace add` + `plugin install`), same as `mm-dev-toolkit`/`project-hub`. Then run `/wikijs-plugin:setup` — it creates a dedicated venv at `~/.wikijs-plugin/venv/` and copies the `.env` template.

Configure Wiki.js credentials in `~/.wikijs-plugin/.env`:

```
WIKIJS_API_URL=https://your-wikijs-installation
WIKIJS_API_TOKEN=your-personal-access-token
```

`WIKIJS_API_URL` is the wiki's base URL (no `/graphql`). `WIKIJS_API_TOKEN` is a
**personal access token** with the `pages` scope; it acts as the user who created
it. The site is resolved automatically from the hostname; set `WIKIJS_SITE_ID`
only if that lookup fails.

> **Upgrading from 1.x (Wiki.js 2):** this version talks to Wiki.js 3 only. See the
> [CHANGELOG](./CHANGELOG.md) for the breaking changes (base URL, token, string page
> IDs, `de-DE`).

## Components

### MCP Server (`servers/wikijs-mcp-server/`)

Python (`mcp[cli]` + `httpx`), dedicated venv — same pattern as `mm-dev-toolkit`/`project-hub`.

| Tool | Description |
|------|-------------|
| `wikijs_create_page` | Create new wiki pages with Markdown or HTML |
| `wikijs_update_page` | Update existing pages (content, title, tags) |
| `wikijs_get_page` | Retrieve full page content and metadata |
| `wikijs_list_pages` | List pages with pagination and filtering (page IDs are UUIDs) |
| `wikijs_search_pages` | Full-text search across wiki pages |
| `wikijs_delete_page` | Permanently delete pages |
| `wikijs_move_page` | Move pages to new paths |
| `wikijs_get_page_history` | Read a page's logged change history (Phase 2, see below) |
| `wikijs_mark_verified` | Record that a page was checked against the source code at a commit (local DB only) |
| `wikijs_get_verified_refs` | Read the newest verified source ref per page and locale (local DB only) |

### Skill (`skills/docs-wiki/`)

`/wikijs-plugin:docs-wiki` — orchestrates documentation sub-agents (docs-architect, mermaid-expert, tutorial-engineer, api-documenter, reference-builder) to create/update Wiki.js pages in DE+EN.

### Skill (`skills/source-check/`)

`/wikijs-plugin:source-check` — checks the factual claims of a page (paths, class and method names,
config keys, commands, descriptions) against the project's source code. The README counts as a
claim, the code wins. `docs-wiki` runs it before `translation-check` and before every publish,
because an error that reads correctly and stands identically in DE and EN is invisible to the
translation check. `/wikijs-plugin:source-check baseline` checks all existing pages project by
project and reports findings without changing any page. Besides wrong claims it also reports what is
missing: an inventory built from the code (what the project itself defines for users: commands,
routes, config keys, environment variables, extension points, Twig hooks, entities, plus categories
per project type) is held against the whole page set, and anything that exists in the code but is
mentioned nowhere is listed as undocumented. That list is a note and never blocks a publish or the
verified marker. The full inventory runs for new docs, for pages without a verified ref and in the
baseline run; for pages with a verified ref an update checks only the delta of the changed files. The
inventory is heuristic, an empty result does not prove the page is complete, and
a "bewusst intern" decision is not stored, so the same items show up again on the next full run.
Verified state is stored in the local history DB and is per machine.

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

A logged `sourceRef` only means "written at". A page counts as verified once `source-check` passed
for it and `wikijs_mark_verified` recorded the ref together with the page's `updatedAt`; only that
verified ref serves as the baseline for diff-based updates, and only while the page still has that
`updatedAt` (an edit in the Wiki.js editor or outside `docs-wiki` makes it unverified again). Existing
refs from before this feature stay as information and are not verified. After updating the plugin, run
`/wikijs-plugin:source-check baseline` once, otherwise each page gets a full check on its first update.

## Requirements

- Python 3.11+ (Windows: the `py` launcher works even where `python`/`python3` are Microsoft Store alias stubs)
- Wiki.js 3.x instance (Wiki.js 2 has no REST API; use plugin 1.x for it)
- Personal access token with the `pages` scope, owned by a user who may read, write and manage pages

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

- [Full Documentation](https://faq.markus-michalski.net/plugins/wikijs-plugin) (English)
- [Vollständige Dokumentation](https://faq.markus-michalski.net/de-DE/plugins/wikijs-plugin) (Deutsch)
- [Changelog](./CHANGELOG.md)
- Original standalone TypeScript MCP server: [wikijs-mcp-server](https://github.com/markus-michalski/wikijs-mcp-server)
