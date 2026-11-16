"""Main entrypoint for fpac-soil-mcp server."""

import sys
from pathlib import Path

# Import the package from this checkout's ``src/``, not from an installed copy. Databricks
# Apps can reuse a Python environment whose installed ``fpac_soil_mcp`` was built from an
# older deployment's source (same package version), so the running tools would not match
# the deployed commit.
SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.is_dir():
    src_path = str(SRC_DIR)
    if src_path in sys.path:
        sys.path.remove(src_path)
    sys.path.insert(0, src_path)


def main() -> None:
    """Run the FastMCP server."""
    # Deferred import to allow config testing prior to full app creation
    try:
        from fpac_soil_mcp.core.config import settings
        from fpac_soil_mcp.mcp.app import create_mcp_server

        server = create_mcp_server()
        if settings.mcp_transport.lower() == "sse":
            server.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
        elif settings.mcp_transport.lower() in ("http", "streamable-http"):
            server.run(transport="http", host=settings.mcp_host, port=settings.mcp_port)
        else:
            server.run(transport="stdio")
    except ImportError:
        # Fallback for minimal scaffolding stage before app module is created
        print("fpac-soil-mcp initialized. Run through FastMCP when app is implemented.")
        sys.exit(0)


if __name__ == "__main__":
    main()
