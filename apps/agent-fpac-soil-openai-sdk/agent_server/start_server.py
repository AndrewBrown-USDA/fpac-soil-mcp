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

agent_server = AgentServer("ResponsesAgent", enable_chat_proxy=True)
# Define the app as a module level variable to enable multiple workers
app = agent_server.app  # noqa: F841


@app.get("/api/geo/health")
def geo_health() -> dict[str, str]:
    """Expose a bounded probe for custom routes beside the chat proxy."""
    return {"status": "ok"}


@app.post("/api/geo/screen")
async def geo_screen(request: Request) -> JSONResponse:
    """Screen one AOI out of band (ADR 0016). Never logs the body; no model, no trace."""
    try:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > geo.MAX_BODY_BYTES:
                raise geo.GeoRequestError(
                    422, f"Request body exceeds {geo.MAX_BODY_BYTES // 1024} KB."
                )
        screen_request = geo.parse_screen_request(bytes(body))
        return JSONResponse(await geo.screen_aoi(screen_request))
    except geo.GeoRequestError as exc:
        key = "error" if exc.status_code == 502 else "detail"
        return JSONResponse({key: exc.message}, status_code=exc.status_code)


setup_mlflow_git_based_version_tracking()


def main():
    agent_server.run(app_import_string="agent_server.start_server:app")
