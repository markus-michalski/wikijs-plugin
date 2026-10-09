# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `source-check` inventory check (step 1a): an Explore subagent builds an inventory of what the
  project itself defines for users (console commands, routes, config keys, environment variables,
  extension points, Twig hooks, entities, plus categories per project type such as MCP tool
  parameters or shell options) and holds the whole page set against it. A feature that exists in the
  code but is mentioned nowhere is reported as undocumented. This is a note, not a finding: it changes
  neither the verdict nor whether a page is marked verified, because the verified ref certifies the
  claims on a page, not its completeness. The claim check alone only goes from page to code and
  cannot see a feature the page never names.
- Framework and bundle defaults, internal listeners, dev and release scripts and individual
  migrations are not part of the inventory, and long lists are capped per category, so the report
  stays reviewable on large projects.

### Changed
- `docs-wiki` builds the inventory from the code before it plans new documentation and hands it to
  every doc agent, so the README is no longer the only source for what to document. The check
  rebuilds the inventory independently instead of reusing it.
- Coverage of the inventory check: complete for new documentation, for pages without a verified ref
  and in the baseline run (once per project, also when all of its pages are already verified). For
  verified pages in update mode only the delta of the changed files is checked.
- The baseline run uses two Explore subagents per project (inventory, then claims). Page buckets
  count claims only; undocumented items are reported per project, outside the page totals, because an
  undocumented item is on no page.
- In update mode a command that the diff removes or renames but that an unchanged subpage still
  names is now a wrong claim on that subpage, and the subpage joins the update.

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet

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
[Unreleased]: https://github.com/markus-michalski/wikijs-plugin/compare/v1.3.0...HEAD
[1.2.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.0
[1.2.1]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.1
[1.2.2]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.2.2
[1.3.0]: https://github.com/markus-michalski/wikijs-plugin/releases/tag/v1.3.0
