"""Smoke: Windows/POSIX MCP server launch — mandatory per the claude-plugin
project type's "Windows Compatibility" checklist."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
MCP_JSON = ROOT / ".mcp.json"
PLUGIN_JSON = ROOT / ".claude-plugin" / "plugin.json"
RUN_SERVER = ROOT / "bin" / "run-server"
RUN_SERVER_CMD = ROOT / "bin" / "run-server.cmd"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"
SETUP_SKILL = ROOT / "skills" / "setup" / "SKILL.md"

DEV_ONLY_PACKAGES = ["pytest", "ruff", "mypy"]


def test_mcp_json_is_valid_json():
    json.loads(MCP_JSON.read_text(encoding="utf-8"))


def test_plugin_json_is_valid_json():
    json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))


def test_mcp_json_command_has_no_hardcoded_venv_subpath():
    """command must go through the OS-agnostic bin/run-server wrapper, not
    hardcode venv/bin (POSIX) or venv\\Scripts (Windows) directly."""
    config = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    command = config["mcpServers"]["wikijs-mcp"]["command"]
    assert "venv/bin" not in command
    assert "venv\\Scripts" not in command and "venv/Scripts" not in command
    assert command.endswith("bin/run-server")


def test_mcp_json_schema():
    config = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    server = config["mcpServers"]["wikijs-mcp"]
    assert server["type"] == "stdio"
    assert isinstance(server["args"], list) and len(server["args"]) == 1
    assert server["args"][0].endswith("run.py")
    assert "CLAUDE_PLUGIN_ROOT" in server["env"]


def test_run_server_wrapper_exists_and_is_executable():
    assert RUN_SERVER.exists(), "bin/run-server not found"
    assert os.access(RUN_SERVER, os.X_OK), "bin/run-server must have the executable bit set"
    first_line = RUN_SERVER.read_text(encoding="utf-8").splitlines()[0]
    assert first_line in ("#!/bin/sh", "#!/bin/bash"), f"unexpected shebang: {first_line}"


def test_run_server_cmd_wrapper_targets_windows_venv():
    assert RUN_SERVER_CMD.exists(), "bin/run-server.cmd not found"
    content = RUN_SERVER_CMD.read_text(encoding="utf-8")
    assert "%USERPROFILE%" in content
    assert "Scripts\\python.exe" in content


def test_gitattributes_pins_wrapper_line_endings():
    content = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "bin/run-server text eol=lf" in content
    assert "bin/run-server.cmd text eol=crlf" in content


def test_run_server_wrapper_actually_launches_python():
    """Real subprocess spawn through the OS-appropriate wrapper, against a
    real throwaway venv (via the stdlib venv module) rather than a raw
    python.exe byte-copy — copying just the executable loses sibling DLLs
    (python3XX.dll) it needs on Windows and fails with STATUS_DLL_NOT_FOUND,
    unrelated to whether bin/run-server(.cmd) itself resolves correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        venv_dir = home / ".wikijs-plugin" / "venv"
        venv.create(venv_dir, with_pip=False)

        if sys.platform == "win32":
            env = {**os.environ, "USERPROFILE": str(home)}
            cmd = [str(RUN_SERVER_CMD), "-c", "print('OK')"]
        else:
            env = {**os.environ, "HOME": str(home)}
            cmd = [str(RUN_SERVER), "-c", "print('OK')"]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"wrapper failed: {result.stderr}"
        assert "OK" in result.stdout


def test_setup_skill_documents_both_platforms():
    body = SETUP_SKILL.read_text(encoding="utf-8")
    assert "venv/bin/python3" in body or "venv/bin/pip" in body, "missing POSIX venv interpreter path"
    assert "Scripts\\python.exe" in body or "Scripts\\pip.exe" in body, "missing Windows venv interpreter path"


def test_setup_skill_documents_py_launcher_fallback():
    """Regression guard: on managed Windows devices, bare python/python3 can
    resolve to the Microsoft Store app-execution-alias stub (exit code 49)
    even when Python is genuinely installed. `py -3` must be documented as
    a fallback."""
    body = SETUP_SKILL.read_text(encoding="utf-8")
    assert "py -3" in body


def test_setup_skill_uses_write_then_run_for_multiline_python():
    """A `-c "..."` argument spanning multiple lines parses differently
    across bash/PowerShell/cmd and reliably breaks under PowerShell."""
    multiline_c_pattern = re.compile(r'-c\s+"\s*\n')
    body = SETUP_SKILL.read_text(encoding="utf-8")
    assert not multiline_c_pattern.search(body), (
        "found a multi-line `-c \"...` invocation — use the write-then-run pattern instead"
    )


def test_requirements_split_runtime_from_dev_tooling():
    assert REQUIREMENTS.exists() and REQUIREMENTS_DEV.exists()
    runtime_content = REQUIREMENTS.read_text(encoding="utf-8")
    dev_content = REQUIREMENTS_DEV.read_text(encoding="utf-8")
    for pkg in DEV_ONLY_PACKAGES:
        assert pkg not in runtime_content, f"{pkg} must not be in runtime requirements.txt"
        assert pkg in dev_content, f"{pkg} must be in requirements-dev.txt"
    assert "requirements.txt" in dev_content


def test_no_missing_encoding_on_file_io_in_server():
    """Static scan: Path.open()/open()/write_text()/read_text() calls in the
    server source must pass encoding= explicitly — without it, Windows falls
    back to the locale codepage (cp1252 on German Windows) and any non-ASCII
    content (arrows, umlauts, em-dash) crashes on write/read."""
    server_dir = ROOT / "servers" / "wikijs-mcp-server"
    io_call = re.compile(r"\b(open|write_text|read_text)\s*\(")
    failures = []
    for py_file in server_dir.rglob("*.py"):
        if "tests" in py_file.parts:
            continue
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), start=1):
            if io_call.search(line) and "encoding=" not in line:
                failures.append(f"{py_file.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not failures, "File I/O without explicit encoding=:\n" + "\n".join(failures)
