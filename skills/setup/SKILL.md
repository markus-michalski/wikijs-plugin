---
name: setup
description: "First-time setup for wikijs-plugin. Creates venv, installs dependencies, copies .env template. Use when: (1) Plugin just installed, (2) MCP server not responding, (3) User says 'setup' or 'einrichten'."
model: claude-sonnet-5
user-invocable: true
---

# wikijs-plugin Setup

First-time setup and repair for the wikijs-plugin plugin.

## Workflow

**Multi-line Python scripts — write a file, don't inline them.** Several
steps below need multi-line Python. Never pass multi-line content via
`<PY> -c "<script>"` — a `-c` argument containing literal newlines parses
differently across bash, PowerShell, and cmd, and reliably breaks under
PowerShell. Instead, for any script longer than one line:

1. Write the script content to a file using your own file-write capability.
   Reuse `~/.wikijs-plugin/_setup_scratch.py` as the target path from Step 2
   onward, since `~/.wikijs-plugin` is guaranteed to exist by then. For Step
   1, which runs before Step 2 creates that directory, use the OS temp
   directory instead — resolve it with the single-line (newline-free)
   command `<PY> -c "import tempfile; print(tempfile.gettempdir())"`.
2. Run it as `<PY> <path-to-that-file>` — a plain file-path argument. If
   `<PY>` came from Step 0's known-install-path fallback and is a
   space-containing full path (e.g. `C:\Program Files\Python313\python.exe`),
   quote both sides with the call operator: `& "<PY>" "<path-to-that-file>"`,
   not a bare `<PY> <path-to-that-file>`.

### Step 0: Detect Platform and Resolve a Working Python Interpreter

Try each of the following in order and use the **first one that actually runs**
(prints a platform string, doesn't error):

```bash
python3 -c "import sys; print(sys.platform)"
python -c "import sys; print(sys.platform)"
py -3 -c "import sys; print(sys.platform)"
```

**Do not stop at the first failure.** On Windows, `python3`/`python` frequently
fail with **exit code 49 and no output** even when Python is genuinely
installed — this is the Microsoft Store app-execution-alias stub, not a
missing-Python error. `py` (the Python Launcher for Windows) is a separate
executable that always lives in `C:\Windows\` — on `PATH` regardless of how
Python itself was installed — so try it before concluding Python is missing.

If all three fail, check known install locations as a last resort (Windows,
PowerShell syntax): `$env:ProgramFiles\Python3*\python.exe`,
`${env:ProgramFiles(x86)}\Python3*\python.exe`,
`$env:LocalAppData\Programs\Python\Python3*\python.exe` — use the first one
that exists.

Only if *every* option above fails is Python genuinely not installed or not
locatable — see Error Handling.

Call whichever command succeeded `<PY>` — use it verbatim for every
subsequent system-level Python invocation in this skill (Steps 1, 2, 3, 5),
until the venv exists in Step 3. From Step 4 onward the venv's *own*
interpreter is used instead.

**Windows quoting note:** `python3`/`python`/`py -3` need no special handling.
But if `<PY>` came from the known-install-path fallback, it's a full path that
may contain spaces — invoke it via the call operator with quotes: `& "<PY>" -c
"..."`, not bare `<PY> -c "..."`.

Output `win32` means Windows (venv layout: `venv\Scripts\python.exe`,
`venv\Scripts\pip.exe`); any other output means POSIX (venv layout:
`venv/bin/python3`, `venv/bin/pip`). Use this result for every POSIX/Windows
choice below.

### Step 1: Check Current State

Follow the write-then-run pattern above: get the OS temp directory, save the
script below as `<tmp>/wikijs-plugin-setup-step1.py`, then run
`<PY> <tmp>/wikijs-plugin-setup-step1.py`:

```python
from pathlib import Path
base = Path.home() / '.wikijs-plugin'
print('venv:', 'OK' if (base / 'venv').is_dir() else 'MISSING')
print('env-file:', 'OK' if (base / '.env').is_file() else 'MISSING')
print('data-dir:', 'OK' if base.is_dir() else 'MISSING')
```

### Step 2: Create Data Directory (if missing)

```bash
<PY> -c "from pathlib import Path; Path.home().joinpath('.wikijs-plugin').mkdir(parents=True, exist_ok=True)"
```

### Step 3: Create Venv (if missing)

Use `<PY>` — the same interpreter resolved in Step 0, not a hardcoded
`python`/`python3`.

- POSIX: `<PY> -m venv ~/.wikijs-plugin/venv`
- Windows: `<PY> -m venv "$env:USERPROFILE\.wikijs-plugin\venv"`

### Step 4: Sync Dependencies (always)

Always run this, even if venv already existed. `pip` is idempotent and fast
on a warm cache. This ensures new deps added in later releases are never
silently skipped.

- POSIX: `~/.wikijs-plugin/venv/bin/pip install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt -q`
- Windows: `& "$env:USERPROFILE\.wikijs-plugin\venv\Scripts\pip.exe" install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt -q`

### Step 5: Copy .env Template (if missing)

Use `<PY>` (still the Step 0 interpreter — this step doesn't need the venv):

```bash
<PY> -c "import shutil; from pathlib import Path; env = Path.home() / '.wikijs-plugin' / '.env'; env.parent.mkdir(parents=True, exist_ok=True) or None; (not env.exists()) and shutil.copy2(r'${CLAUDE_PLUGIN_ROOT}/servers/wikijs-mcp-server/.env.example', env)"
```

Then tell the user: "Die `.env`-Vorlage wurde nach `~/.wikijs-plugin/.env`
kopiert. Trage dort deine Wiki.js-Zugangsdaten ein:
- `WIKIJS_API_URL` — GraphQL-Endpunkt deiner Wiki.js-Instanz (endet auf `/graphql`)
- `WIKIJS_API_TOKEN` — API-Token aus dem Wiki.js Admin-Panel (Admin -> API Access),
  Berechtigungen: `read:pages`, `write:pages`, `manage:pages`"

### Step 6: Verify MCP Server

Follow the write-then-run pattern (save as `~/.wikijs-plugin/_setup_scratch.py`,
then run via the venv's Python — POSIX:
`~/.wikijs-plugin/venv/bin/python3 "$HOME/.wikijs-plugin/_setup_scratch.py"`,
Windows: `& "$env:USERPROFILE\.wikijs-plugin\venv\Scripts\python.exe"
"$env:USERPROFILE\.wikijs-plugin\_setup_scratch.py"`):

```python
import sys
sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/servers/wikijs-mcp-server')
from mcp.server.mcpserver import MCPServer  # the symbol server.py actually needs
import httpx
import dotenv
print('MCP: OK')
```

This import check does NOT require valid Wiki.js credentials — `server.py`
constructs its API client lazily on first tool call, so a missing/invalid
`.env` only fails an actual `wikijs_*` tool call, not this check or server
startup import.

### Step 7: Report

```
Setup abgeschlossen:
- Daten-Verzeichnis: OK/ERSTELLT  (~/.wikijs-plugin)
- Venv:             OK/ERSTELLT  (~/.wikijs-plugin/venv)
- Dependencies-Sync: SYNCHRONISIERT  (pip)
- .env:             OK/ERSTELLT  (~/.wikijs-plugin/.env)
- MCP:              OK / MISSING

Starte Claude Code neu, damit der MCP Server geladen wird.
```

## Error Handling

- `python3` not found (POSIX), and no other interpreter in Step 0's chain
  works either → Python is genuinely not installed. Tell user to install
  Python 3.11+.
- On Windows, `python`/`python3` exiting with code 49 and no output is
  **not** "Python not found" — it's the Microsoft Store app-execution-alias
  stub. Fall through Step 0's chain (`py -3`, then known install paths).
- Only if **every** entry in Step 0's fallback chain fails is Python actually
  missing on Windows → tell the user to install Python 3.11+ from python.org
  and check "Add python.exe to PATH" during install.
- `pip install` fails → show the exact error and suggest running manually.
- Step 6's import fails (e.g. `ModuleNotFoundError`) → report `MCP: MISSING`
  in Step 7's report, show the exact import error, and suggest re-running
  Step 4's dependency sync manually.
- Actual `wikijs_*` tool calls fail with a credentials error at runtime →
  point the user back to Step 5's `.env` — this is expected until real
  Wiki.js credentials are filled in, not a setup bug.
