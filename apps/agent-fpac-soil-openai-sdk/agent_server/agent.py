import logging
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack

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

from agent_server.config import (
    agent_model,
    fpac_mcp_timeout_seconds,
    fpac_mcp_url,
    load_system_prompt,
    uses_reasoning_effort_none,
)
from agent_server.history import normalize_history_items
from agent_server.utils import get_session_id, process_agent_stream_events

logger = logging.getLogger(__name__)

# NOTE: this will work for all databricks models OTHER than GPT-OSS, which uses a slightly different API
set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])  # only use mlflow for trace processing
mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)


TOOLS_UNAVAILABLE_NOTE = (
    "The fpac-soil-mcp tools are unavailable for this request. Tell the user you cannot run "
    "the screening right now; do not answer from memory."
)


FPAC_MCP_SERVER_NAME = "fpac-soil-mcp"


def init_fpac_mcp_server(workspace_client: WorkspaceClient) -> McpServer:
    """Build the client for the deployed fpac-soil-mcp server."""
    return McpServer(
        url=fpac_mcp_url(),
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
    mcp_servers: list[McpServer] | None = None, *, tools_unavailable: bool = False
) -> Agent:
    """Build the FPAC Soil agent.

    The model comes from ``AGENT_MODEL``. GPT-5 endpoints get ``reasoning_effort="none"``,
    which they need for tool calling. When ``tools_unavailable`` is set, the instructions
    tell the model to say so instead of answering from memory.
    """
    model = agent_model()
    instructions = load_system_prompt()
    if tools_unavailable:
        instructions = f"{instructions}\n\n{TOOLS_UNAVAILABLE_NOTE}"
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


async def _connect_fpac_agent(stack: AsyncExitStack) -> Agent:
    # WorkspaceClient() authenticates as the app's service principal, not the user.
    # connect_healthy_mcp_servers drops a server that fails (and logs the warning with its
    # traceback), so the request still runs.
    servers, unavailable = await connect_healthy_mcp_servers(
        stack, [init_fpac_mcp_server(WorkspaceClient())]
    )
    if unavailable:
        logger.info("MCP servers unavailable for this request: %s", ", ".join(unavailable))
    return create_agent(mcp_servers=servers, tools_unavailable=bool(unavailable))


@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    if session_id := get_session_id(request):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(stack)
        messages = normalize_history_items([i.model_dump() for i in request.input])
        result = await Runner.run(agent, messages)
        return ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    if session_id := get_session_id(request):
        mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
    # The AsyncExitStack keeps the MCP server open for the whole request.
    async with AsyncExitStack() as stack:
        agent = await _connect_fpac_agent(stack)
        messages = normalize_history_items([i.model_dump() for i in request.input])
        result = Runner.run_streamed(agent, input=messages)

        async for event in process_agent_stream_events(result.stream_events()):
            yield event
