# Contributing to wikijs-plugin

## Development Setup

```bash
git clone https://github.com/markus-michalski/wikijs-plugin.git
cd wikijs-plugin

python3 -m venv .venv       # or: py -3 -m venv .venv   (Windows)
.venv/bin/pip install -r requirements-dev.txt      # POSIX
# .venv\Scripts\pip.exe install -r requirements-dev.txt   (Windows)

cp servers/wikijs-mcp-server/.env.example ~/.wikijs-plugin/.env
# edit ~/.wikijs-plugin/.env with your Wiki.js API credentials
```

For actually running the plugin inside Claude Code (not just developing the
server in isolation), use `/wikijs-plugin:setup` — it creates the dedicated
`~/.wikijs-plugin/venv/` the shipped `bin/run-server` wrapper expects.

## Code Style

- **Language:** Python 3.11+ (MCP server), Markdown (skills)
- **Type checking:** `mypy servers/wikijs-mcp-server --exclude tests`
- **Linting:** `ruff check servers/wikijs-mcp-server`
- **Comments:** English

## Architecture

```
wikijs-plugin/
├── .claude-plugin/              # plugin.json + marketplace.json (ONLY these two files)
├── .mcp.json                    # MCP server registration
├── bin/                         # OS-agnostic run-server wrapper (POSIX + Windows)
├── requirements.txt             # runtime deps (installed by /wikijs-plugin:setup)
├── requirements-dev.txt         # + pytest/ruff/mypy
├── servers/wikijs-mcp-server/   # Python MCP server (Wiki.js GraphQL client)
│   ├── run.py                   # stdio entry point
│   ├── server.py                # @mcp.tool() registrations
│   └── tools/                   # client.py, pages.py, validation.py, config.py
├── skills/docs-wiki/            # Skill orchestrating documentation sub-agents
├── skills/setup/                # First-time venv + .env setup
└── tests/smoke/                 # Plugin-wide mandatory smoke tests
```

### Adding a New MCP Tool

1. Add the GraphQL query/mutation to `tools/client.py`'s `WikiJsClient`
2. Add the business logic (validation, id/path resolution) to `tools/pages.py`
3. Register the tool in `server.py` with `@mcp.tool(annotations=ToolAnnotations(...))`
4. All tools must use the `wikijs_` prefix — keeps parity with the original
   TypeScript server's documented tool names
5. Write tests first (TDD) in `servers/wikijs-mcp-server/tests/`

### Windows Compatibility

Mandatory for every change touching `bin/`, `.mcp.json`, `skills/setup/`, or
file I/O in the server:
- Never hardcode a POSIX path in `.mcp.json` — go through `bin/run-server`
- Any credential-loading or config-loading code must raise a plain exception
  (never `SystemExit`) when called from inside a tool handler — see
  `tools/config.py`'s `MissingCredentialsError` and the comment on
  `server._get_client()` for why (`SystemExit` is a `BaseException` and
  blows past the MCP framework's per-call exception wrapping)
- All file I/O uses `encoding="utf-8"` explicitly

## Development Commands

Run from the repo root (or point at `servers/wikijs-mcp-server` for
lint/typecheck):

```bash
pytest tests/smoke/ -v                          # plugin-wide smoke tests
pytest servers/wikijs-mcp-server/tests -v        # server unit tests
ruff check servers/wikijs-mcp-server             # lint
mypy servers/wikijs-mcp-server --exclude tests   # type check
```

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new MCP tool
fix: correct a bug
docs: update documentation
refactor: restructure code
test: add or modify tests
```

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes, tests first (TDD)
3. Ensure `pytest`, `ruff check`, and `mypy` all pass
4. Open a PR with a clear description
