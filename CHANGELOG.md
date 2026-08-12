# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `wikijs_update_page` refuses updates where `content` shrinks the page to under half its
  current length (for pages 200+ chars), guarding against accidental wholesale overwrites
  (content has no diff/merge, it fully replaces the page). Pass `confirmContentShrink: true`
  to confirm an intentional shrink.

### Changed
- `wikijs_update_page` calls that previously succeeded while replacing `content` with something
  under half the current page's length (200+ char pages) now fail with a `ValueError` unless
  `confirmContentShrink: true` is passed — see Added above.

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

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
