"""Main entrypoint for fpac-soil-mcp server."""

import sys


def main() -> None:
    """Run the FastMCP server."""
    # Deferred import to allow config testing prior to full app creation
    try:
        from fpac_soil_mcp.app import create_mcp_server
        from fpac_soil_mcp.config import settings

        server = create_mcp_server()
        if settings.mcp_transport.lower() == "sse":
            server.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
        else:
            server.run(transport="stdio")
    except ImportError:
        # Fallback for minimal scaffolding stage before app module is created
        print("fpac-soil-mcp initialized. Run through FastMCP when app is implemented.")
        sys.exit(0)


if __name__ == "__main__":
    main()
