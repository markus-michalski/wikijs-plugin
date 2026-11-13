# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Optional `WIKIJS_SITE_ID` to skip the hostname lookup via `/_api/bootstrap`.
- `docs-wiki` content rules for Wiki.js 3: Mermaid in `::block-diagram`, tabs as
  `:::block-tabs` / `::block-tab{label="..."}`, unindented HTML blocks, link format
  (English without prefix, German as `/de-DE/...`).

### Changed
- **BREAKING: Wiki.js 3 only.** The client now uses the Wiki.js 3 REST API
  (`/_api/sites/:siteId/pages`) instead of the Wiki.js 2 GraphQL API. Wiki.js 2 is no
  longer supported; stay on 1.x for it.
- **BREAKING: configuration.** `WIKIJS_API_URL` is the wiki's base URL (no `/graphql`;
  a `/graphql` URL is rejected with a hint). `WIKIJS_API_TOKEN` must be a personal
  access token with the `pages` scope.
- **BREAKING: page IDs are strings** (UUIDs) instead of integers: the `id` parameter of
  `wikijs_get_page`, `wikijs_update_page`, `wikijs_delete_page` and `wikijs_move_page`.
- **BREAKING: locales.** German is `de-DE` (was `de`). Rows in the local history DB
  written under `de` do not match `de-DE` queries; verified markers from Wiki.js 2 are
  stale after the migration anyway and are re-created by a baseline run.
- **BREAKING: `isPrivate` removed** from `wikijs_create_page` (no Wiki.js 3 equivalent).
  The `editor` is passed through as given (`markdown` by default) instead of being
  limited to `markdown`/`code`/`ckeditor`.
- `isPublished` maps to Wiki.js 3's `publishState` (`false` -> `draft`, `true` ->
  `published`), so draft-first publishing keeps working. Page results keep an
  `isPublished` flag and add `publishState`.
- `wikijs_update_page` is a true partial update: only the fields you pass are sent, so
  title, description and tags are no longer fetched and resent.
- `wikijs_list_pages` reads through the search endpoint (Wiki.js 3's list route is a
  stub); a second search filtered to drafts supplies the `isPublished` flag of each entry.

### Deprecated
- Nothing yet

### Removed
- The Wiki.js 2 notes in `docs-wiki` (Mermaid 8.8.2 restrictions, single-line callouts
  and hard `<br>` for source line breaks, `{.tabset}`).

### Fixed
- Nothing yet

### Security
- Nothing yet

## [1.5.2] - 2026-11-11

### Added
- add DPR 2 screenshot rule with display width for cropped images (#28)

## [1.5.1] - 2026-11-06

### Fixed
- remove width specification for page screenshots to ensure proper display (#26)

## [1.5.0] - 2026-11-04

### Added
- draft-first new docs with screenshot suggestions and release gate (#25)

### Changed
- Dependabot auf monatlichen Rhythmus umstellen (#23)
- Bump the pip-all group across 1 directory with 4 updates (#17)

## [1.4.0] - 2026-10-09

### Added
- report code features the docs never mention (#21)

### Changed
- added worktrees to .gitignore

## [1.3.0] - 2026-10-09

### Added
- verify wiki page claims against the source code (#19) (#20)
- gate wiki publishing on natural-sounding text (#18)

## [1.2.2] - 2026-10-06

### Added
- add mandatory parent link rule for all wiki pages (#16)

## [1.2.1] - 2026-10-05

### Added
- require hub + subpages for all wiki docs (#15)

## [1.2.0] - 2026-10-05

### Added
- add Sylius plugin template (#14)

### Changed
- Bump the pip-all group across 1 directory with 2 updates (#12)
- Bump the pip-all group with 2 updates (#10)
- Bump the pip-all group with 2 updates (#9)
- Bump the pip-all group with 2 updates (#8)
- Bump the pip-all group with 3 updates (#6)
- Bump the actions-all group with 2 updates (#5)

## [1.1.0] - 2026-08-13

### Changed
- feat(update-page)!: guard against accidental full-page wipes (#7)

## [1.0.0] - 2026-08-12

### Added
- track source repo/ref per Wiki.js page write (#2)

### Changed
- BDFL hardening — PolyForm NC 1.0.0, CLA, .github scaffold (#4)
- forbid manual line-wrapping in callout boxes (#3)
- Initial plugin scaffold: wikijs-mcp-server (ported to Python) + docs-wiki skill

### Fixed
- track bin/run-server's executable bit in git

[1.0.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.0.0
[1.1.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.1.0
[Unreleased]: https://github.com/markus-michalski/wikijs-plugin/compare/v1.5.2...HEAD
[1.2.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.0
[1.2.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.1
[1.2.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.2
[1.3.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.3.0
[1.4.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.4.0
[1.5.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.0
[1.5.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.1
[1.5.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.2
