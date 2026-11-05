import logging
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
from functools import lru_cache

import mlflow
from agents import (
    Agent,
    ModelSettings,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
)
from agents.tracing import set_trace_processors
from databricks.sdk import WorkspaceClient
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import McpServer
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from openai.types.shared import Reasoning

from agent_server.aoi_context import (
    ActiveAoi,
    bind_active_aoi,
    instruction_note,
    read_active_aoi,
)
from agent_server.config import (
    McpServerLookupError,
    agent_model,
    fpac_mcp_timeout_seconds,
    fpac_mcp_url,
    load_system_prompt,
    uses_reasoning_effort_none,
)
from agent_server.history import normalize_history_items
from agent_server.utils import get_session_id, process_agent_stream_events

logger = logging.getLogger(__name__)

set_default_openai_api("chat_completions")
set_trace_processors([])  # only use mlflow for trace processing
mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)


TOOLS_UNAVAILABLE_NOTE = (
    "The fpac-soil-mcp tools are unavailable for this request. Tell the user you cannot run "
    "the screening right now; do not answer from memory."
)


FPAC_MCP_SERVER_NAME = "fpac-soil-mcp"


@lru_cache(maxsize=1)
def configure_openai_client() -> AsyncDatabricksOpenAI:
    """Configure the Databricks client once, when a real request needs it."""
    # This works for all Databricks models other than GPT-OSS, which uses a
    # slightly different API. AI Gateway routes UC model service names through
    # /ai-gateway/mlflow/v1.
    client = AsyncDatabricksOpenAI(use_ai_gateway=True)
    set_default_openai_client(client)
    return client


def init_fpac_mcp_server(workspace_client: WorkspaceClient) -> McpServer:
    """Build the client for the deployed fpac-soil-mcp server."""
    return McpServer(
        # FPAC_MCP_APP (the ``mcp_server`` resource) resolves through the Apps API.
        url=fpac_mcp_url(lambda name: workspace_client.apps.get(name=name).url),
        name=FPAC_MCP_SERVER_NAME,
        workspace_client=workspace_client,
        timeout=fpac_mcp_timeout_seconds(),
    )


async def connect_healthy_mcp_servers(
    stack: AsyncExitStack, servers: list[McpServer]
) -> tuple[list[McpServer], list[str]]:
    """Connect each MCP server and verify it can actually list its tools.

    The Agents SDK lists each server's tools lazily inside ``Runner.run``, so a server that
    connects but fails at list time (e.g. an unauthorized Genie space) would otherwise crash
    the whole request — including unrelated turns. We list tools here, per server: healthy
    servers are kept; any that fails to connect OR to list is dropped and its name returned,
    so the agent runs with whatever is available instead of erroring out.

    Returns (healthy_servers, unavailable_names).
    """
    healthy: list[McpServer] = []
    unavailable: list[str] = []
    for server in servers:
        name = getattr(server, "name", "MCP server")
        try:
            connected = await stack.enter_async_context(server)
            await connected.list_tools()  # forces the connectivity + authorization check now
            healthy.append(connected)
        except Exception:
            logger.warning("MCP server %r unavailable; continuing without it.", name, exc_info=True)
            unavailable.append(name)
    return healthy, unavailable


def create_agent(
    mcp_servers: list[McpServer] | None = None,
    *,
    tools_unavailable: bool = False,
    aoi_note: str | None = None,
) -> Agent:
    """Build the FPAC Soil agent.

    The model comes from ``AGENT_MODEL``. GPT-5 models get ``reasoning_effort="none"``,
    which they need for tool calling. When ``tools_unavailable`` is set, the instructions
    tell the model to say so instead of answering from memory. ``aoi_note`` describes the
    map AOI attached to the conversation (ADR 0016).
    """
    model = agent_model()
    instructions = load_system_prompt()
    if tools_unavailable:
        instructions = f"{instructions}\n\n{TOOLS_UNAVAILABLE_NOTE}"
    elif aoi_note:
        instructions = f"{instructions}\n\n{aoi_note}"
    if uses_reasoning_effort_none(model):
        model_settings = ModelSettings(reasoning=Reasoning(effort="none"))
    else:
        model_settings = ModelSettings()
    return Agent(
        name="FPAC Soil Agent",
        instructions=instructions,
        model=model,
        tools=[],
        mcp_servers=mcp_servers or [],
        model_settings=model_settings,
    )


async def _connect_fpac_agent(stack: AsyncExitStack, aoi: ActiveAoi | None = None) -> Agent:
    # WorkspaceClient() authenticates as the app's service principal, not the user.
    # connect_healthy_mcp_servers drops a server that fails (and logs the warning with its
    # traceback), so the request still runs.
    try:
        server = init_fpac_mcp_server(WorkspaceClient())
    except McpServerLookupError as exc:
        # Same outcome as an unreachable server: the turn runs without tools.
        logger.warning("MCP server lookup failed: %s", exc)
        return create_agent(mcp_servers=[], tools_unavailable=True)
    if aoi is not None:
        bind_active_aoi(server, aoi)
    servers, unavailable = await connect_healthy_mcp_servers(stack, [server])
    if unavailable:
        logger.info("MCP servers unavailable for this request: %s", ", ".join(unavailable))
    if aoi is not None and not unavailable:
        return create_agent(mcp_servers=servers, aoi_note=instruction_note(aoi))
    return create_agent(mcp_servers=servers, tools_unavailable=bool(unavailable))


@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    if session_id := get_session_id(request):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    configure_openai_client()
    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(stack, read_active_aoi(request))
        messages = normalize_history_items([i.model_dump() for i in request.input])
        result = await Runner.run(agent, messages)
        return ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    if session_id := get_session_id(request):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    configure_openai_client()
    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(stack, read_active_aoi(request))
        messages = normalize_history_items([i.model_dump() for i in request.input])
        result = Runner.run_streamed(agent, input=messages)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
