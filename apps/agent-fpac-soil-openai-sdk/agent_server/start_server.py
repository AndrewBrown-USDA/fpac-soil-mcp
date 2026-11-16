# Install crash/hang/exception diagnostics before importing agent code so
# startup failures and unhandled exceptions land in the Apps log stream.
from scripts.app_diagnostics import install_diagnostics  # noqa: E402

install_diagnostics()

from pathlib import Path

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env before importing the agent for proper auth
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402
from agent_server import geo  # noqa: E402
from agent_server.config import local_dev_enabled  # noqa: E402

agent_server = AgentServer("ResponsesAgent", enable_chat_proxy=True)
# Define the app as a module level variable to enable multiple workers
app = agent_server.app  # noqa: F841


@app.get("/api/geo/health")
def geo_health() -> dict[str, str]:
    """Expose a bounded probe for custom routes beside the chat proxy."""
    return {"status": "ok"}


async def _read_body(request: Request, too_large_status: int) -> bytes:
    """Read the body up to ``geo.MAX_BODY_BYTES``; stop at the first chunk over it."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > geo.MAX_BODY_BYTES:
            raise geo.GeoRequestError(
                too_large_status, f"Request body exceeds {geo.MAX_BODY_BYTES // 1024} KB."
            )
        body.extend(chunk)
    return bytes(body)


def _error_response(exc: geo.GeoRequestError) -> JSONResponse:
    key = "error" if exc.status_code == 502 else "detail"
    return JSONResponse({key: exc.message}, status_code=exc.status_code)


@app.post("/api/geo/screen")
async def geo_screen(request: Request) -> JSONResponse:
    """Screen one AOI out of band (ADR 0016). Never logs the body; no model, no trace."""
    try:
        screen_request = geo.parse_screen_request(await _read_body(request, 422))
        return JSONResponse(await geo.screen_aoi(screen_request))
    except geo.GeoRequestError as exc:
        return _error_response(exc)


@app.post("/api/geo/corridor")
async def geo_corridor(request: Request) -> JSONResponse:
    """Screen one corridor out of band; never logs the body, invokes the model, or traces."""
    try:
        corridor = geo.parse_corridor_request(await _read_body(request, 413))
        return JSONResponse(await geo.screen_corridor(corridor))
    except geo.GeoRequestError as exc:
        return _error_response(exc)


@app.post("/api/geo/map")
async def geo_map(request: Request) -> JSONResponse:
    """Map layers for one analyze tool call (ADR 0017). Never logs the body; no model, no trace."""
    try:
        tool, arguments = geo.parse_map_request(await _read_body(request, 413))
        return JSONResponse(await geo.map_for_tool(tool, arguments))
    except geo.GeoRequestError as exc:
        return _error_response(exc)


if not local_dev_enabled():
    setup_mlflow_git_based_version_tracking()


def main():
    agent_server.run(app_import_string="agent_server.start_server:app")
