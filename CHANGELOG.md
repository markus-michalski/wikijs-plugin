# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `localeRelations` on `wikijs_create_page` and `wikijs_update_page` links a page to its
  translation (e.g. DE and EN) so Wiki.js offers the language switcher. The link works in
  both directions; the list is the whole set, an empty list unlinks. `wikijs_get_page` now
  returns `localeRelations` and `publishState`. `docs-wiki` links the EN page to the DE page.
- `wikijs_list_page_versions` and `wikijs_get_page_version`: Wiki.js's own version history
  of a page. A bad `content` update can be rolled back by sending an old version's content
  to `wikijs_update_page`.
- `wikijs_list_deleted_pages` and `wikijs_restore_page`: list the recycle bin and bring a
  page back (optionally under a new path).
- `wikijs_list_tags`: tags already in use, so docs reuse them instead of creating variants.
- `wikijs_move_page` takes `updateLinks` to rewrite internal links that pointed at the old path.

### Changed
- `summary` of `wikijs_create_page` / `wikijs_update_page` is now also stored as the reason
  for change on the Wiki.js version (255 characters at most), not only in the local DB.
- `wikijs_delete_page` documents what actually happens: the page goes to the recycle bin and
  is restorable. The "irreversible" warning is gone from the tool text and the delete message.
- `docs-wiki`: badges are written on one line, separated by spaces (separate source lines
  render as separate lines because of the hard `<br>`).

### Deprecated
- Nothing yet

### Removed
- `docs-wiki` no longer writes a manual language link (`[English Version](...)` /
  `[Deutsche Version](...)`) into the page. The theme's global language switcher does that job,
  which only needs both languages to share the same path. The lines were removed from the
  existing pages as well.
- `docs-wiki` no longer writes a manual link to the parent page (`[Back to overview]`,
  `[All OXID 7 Plugins]`, ...). The theme's breadcrumbs, built from the page path, show that
  way back; the rule now requires a complete path hierarchy (category page and hub exist). The
  lines were removed from the existing pages as well, as was the old `[English version]` link on
  the German `mcp/wikijs` pages.

### Fixed
- `docs-wiki` rules said Wiki.js 3 no longer renders source line breaks as hard `<br>`. It still
  does (checked with a freshly rendered page), so the 2.0.0 removal of the single-line callout
  rule was wrong and the rule is back.
- `wikijs_delete_page` failed with HTTP 400 ("Body cannot be empty") against Wiki.js 3:
  the client sent `Content-Type: application/json` on a request without a body. Found
  in the first live write test with a personal access token.

### Security
- Nothing yet

## [2.0.0] - 2026-11-13

### Changed
- feat(client)!: port Wiki.js client from GraphQL (v2) to REST (v3) (#30)

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
[Unreleased]: https://github.com/markus-michalski/wikijs-plugin/compare/v2.0.0...HEAD
[1.2.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.0
[1.2.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.1
[1.2.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.2
[1.3.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.3.0
[1.4.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.4.0
[1.5.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.0
[1.5.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.1
[1.5.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.5.2
[2.0.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v2.0.0
