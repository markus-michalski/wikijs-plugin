# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `translation-check` skill: pre-publish gate that checks whether DE (primary) and EN Wiki.js
  content reads naturally instead of like a mechanical translation, with a maintained glossary
  of terms that must stay as loanwords (e.g. "Cronjob"). It also compares the DE and EN versions
  of a page against each other and flags escaped-quote leftovers (backslash before a quote).
  Wired into `docs-wiki` as a mandatory step before every `wikijs_create_page`/`wikijs_update_page` call.
- `source-check` skill: checks the factual claims of a page (paths, class and method names, config
  keys, commands, descriptions) against the project's source code instead of the README. Covers
  `config/**/*.yaml`, `config/services.php` and `templates/**/*.twig`, updates verified pages from
  the git diff only, and has a `baseline` mode that checks all existing pages project by project
  without changing them.
- `wikijs_mark_verified` and `wikijs_get_verified_refs` MCP tools (local DB only). A `sourceRef`
  logged by create/update means "written at"; only a ref set by `wikijs_mark_verified` counts as
  verified and serves as the baseline for diff-based updates. The marker stores the page's
  `updatedAt`, so a page edited afterwards outside the checked flow counts as unverified again.

### Changed
- `docs-wiki` now runs `source-check` and then `translation-check` before publishing. A FAIL verdict
  blocks the publish until the content is revised, a WARN verdict asks the user once for the whole
  page set. After the publish the checked ref is stored as verified.
- The page-history DB schema moves to version 2 (new `verified` and `page_updated_at` columns).
  Existing rows migrate in place and stay unverified; an older plugin version can still read and
  write the migrated DB. Run `/wikijs-plugin:source-check baseline` once after updating.
- `wikijs_get_page_history` entries now include `verified` and `page_updated_at`.

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

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
[Unreleased]: https://github.com/markus-michalski/wikijs-plugin/compare/v1.2.2...HEAD
[1.2.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.0
[1.2.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.1
[1.2.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.2
