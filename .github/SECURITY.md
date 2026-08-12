# Security Policy

## Reporting a Vulnerability

**Do not open public issues for security vulnerabilities.**

Use GitHub's [Private Vulnerability Reporting](https://github.com/markus-michalski/wikijs-plugin/security/advisories/new) feature to report security issues privately. You will receive an acknowledgement within 72 hours.

For non-sensitive security questions, open a [Bug Report](https://github.com/markus-michalski/wikijs-plugin/issues/new?template=bug_report.yml) issue.

## Supported Versions

wikijs-plugin has not yet reached a `1.0.0` release (currently `0.x`, pre-release). Security fixes land on the latest `main` — there is no parallel maintenance of older `0.x` versions.

## Code Review Requirements

### Workflow Files (`.github/workflows/*`)

**Workflow files execute code in CI/CD and require strict security review.**

Requirements for workflow changes:
- Must be reviewed and approved by @markus-michalski
- Manual security audit required (no automated approval)
- Changes must be explained in the PR description
- Do not include executable code in PR descriptions or issue comments

Security considerations:
- Workflows run with `GITHUB_TOKEN` access
- Can read repository contents
- Can create releases and tags
- Can access repository secrets (if configured)

### Plugin Manifest Files

Changes to `.claude-plugin/plugin.json`:
- Trigger version recognition in plugin marketplaces
- Must be reviewed by the maintainer
- Version bumps must match `CHANGELOG.md`

### AI-Assisted Development

This project uses Claude Code (AI pair programming). When contributing:

**DO:**
- Review all code changes carefully before submitting
- Use Conventional Commits format
- Follow existing code patterns
- Test changes locally before opening a PR

**DO NOT:**
- Include prompts or instructions for AI in code comments or docstrings
- Attempt to manipulate AI review via PR descriptions
- Include executable commands or scripts in PR descriptions
- Assume AI-reviewed code is automatically safe

## Secrets and Credentials

**Never commit secrets to this repository.** This includes:
- Wiki.js API tokens (`WIKIJS_API_TOKEN`)
- Access tokens (GitHub PATs, etc.)
- Private keys (`.pem`, `.key` files)
- Credentials (passwords, service accounts)
- Environment files (`.env`)

Wiki.js credentials live at `~/.wikijs-plugin/.env` — outside this repository.

If you accidentally commit a secret:
1. Immediately revoke or rotate the credential
2. Contact the maintainer via Private Vulnerability Reporting
3. Do NOT just delete the commit — it remains in git history

## Dependencies

Python dependencies are declared in `requirements.txt` (runtime) and `requirements-dev.txt` (dev/test tooling). Dependabot scans weekly and opens PRs for updates. When adding dependencies:
- Prefer well-maintained, popular packages
- Check for known vulnerabilities (e.g. via `pip-audit`)
- Add an upper bound in `requirements.txt` if a major bump is known to break this repo

## Security Best Practices for Users

If you're using this plugin:

1. **Keep your credentials secure**: `~/.wikijs-plugin/.env` holds your Wiki.js API token — never share it or commit it
2. **Scope the API token**: use a Wiki.js token with only the page-management permissions this plugin needs
3. **Review generated content**: always review pages before they're published to your Wiki.js instance
4. **Page-history DB**: `~/.wikijs-plugin/wikijs-plugin.db` logs `sourceRepo`/`sourceRef`/`summary` locally — it never leaves your machine

## Attribution

This project uses AI assistance (Claude Code) for development. Commits include the co-author line:
```
Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>
```

This is for transparency. All AI-generated code is reviewed by the maintainer before merging.
