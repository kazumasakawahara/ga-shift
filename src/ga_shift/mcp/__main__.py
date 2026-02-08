"""Allow running the MCP server as a module.

Usage:
    python -m ga_shift.mcp        # starts the MCP server in stdio mode
    uv run python -m ga_shift.mcp
"""

from ga_shift.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
