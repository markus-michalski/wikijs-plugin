# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Claude Code plugin scaffold combining `wikijs-mcp-server` and `mm-skills/docs-wiki`
  (`.claude-plugin/`, `.mcp.json`, `bin/run-server`, `skills/setup/`)
- Wiki.js MCP server ported to Python (`mcp[cli]` + `httpx`), matching the
  `mm-dev-toolkit`/`project-hub` venv + `bin/run-server` pattern — all 7
  `wikijs_*` tools preserve the original tool names, parameters, and behavior
  (including the update_page auto-fetch-on-metadata-only-update logic)
- Page-history tracking (Phase 2): SQLite `page_history` table
  (`~/.wikijs-plugin/wikijs-plugin.db`), optional `sourceRepo`/`sourceRef`/`summary`
  parameters on `wikijs_create_page`/`wikijs_update_page` (DB-only, never written
  into visible page content), new `wikijs_get_page_history` tool, `docs-wiki`
  workflow updated to pass the target project's `git rev-parse HEAD` automatically
- BDFL governance scaffold (matching `storyforge`): `CLA.md` (Apache ICLA v2.2
  adapted), `CONTRIBUTING.md` CLA-gate section, `.github/CODEOWNERS`,
  `.github/SECURITY.md`, `.github/dependabot.yml` (pip + github-actions,
  weekly), `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/`
  (bug report, feature request, config)

### Changed
- License switched from MIT to [PolyForm Noncommercial License 1.0.0](LICENSE.md)
  (`LICENSE` → `LICENSE.md`, `plugin.json` `license` field → `"SEE LICENSE.md"`,
  README license section + badge updated)

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet
