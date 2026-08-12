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

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet
