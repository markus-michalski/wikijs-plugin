"""Entry point for the wikijs-mcp MCP server."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    from tools.config import MissingCredentialsError, load_credentials

    try:
        load_credentials()  # fail fast, before starting the stdio transport
    except MissingCredentialsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    from server import mcp

    mcp.run()
