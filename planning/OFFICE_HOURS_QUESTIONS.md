# Databricks Office Hours — MCP Server Deployment Questions

## Context

We built an MCP server (USDA FPAC soil/farmland screening, 10 tools) using
FastMCP with Streamable HTTP transport. It is deployed as a Databricks App
(`mcp-fpac-soil`) and is healthy at its HTTPS endpoint. We can reach it from a
browser (OAuth session) and confirmed that 302/401 on unauthenticated requests
is the expected auth-gated behavior.

We know from the Databricks Apps deployment template that bearer token auth
(`Authorization: Bearer <token>` from `databricks auth token`) is the supported
programmatic access path. Transport is confirmed: Streamable HTTP at `/mcp` on
port 8000 with `DATABRICKS_APP_PORT` detection.

### Resolved

- **Transport**: Streamable HTTP at `/mcp` on port 8000 — confirmed correct.
- **Access control**: CAN USE on the app + bearer token is the auth gate.
- **302/401**: expected behavior for auth-gated Apps, not a failure.
- **Service principal**: Databricks injects `DATABRICKS_CLIENT_ID` and
  `DATABRICKS_CLIENT_SECRET` at runtime for tools that call back into Databricks;
  default grants are sufficient for serving MCP traffic.

### Why AI Playground is required

We have no formally approved local coding agent that is allowed to use MCP
(Claude Code, Cursor, VS Code, etc. are not options). AI Playground is the only
approved interactive agent interface available to us, so it is the critical
path for hackathon testing.

## Feature availability probe (Monday 2026-10-19)

Run from a serverless notebook as `andrew.g.brown@usda.gov` against workspace
`dbc-aae0ba16-8727.cloud.databricks.com`:

| Check | Result | Interpretation |
| --- | --- | --- |
| `GET /api/2.1/unity-catalog/model-services?parent=schemas/system.ai` | 200, `system.ai.*` model services listed | Unity Gateway **model** routing is on |
| `GET /api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai` | 200, empty `{}` | No MCP services visible to this user |
| `POST /ai-gateway/mcp-services/system.ai.dbsql` (`tools/list`) | 403, `-32007 Not authorized to invoke MCP service.` | Route exists; MCP not enabled or not granted |
| `POST /ai-gateway/mcp-services/system.ai.web_search` | 403, same error | Same |
| `POST /ai-gateway/mcp-services/system.ai.genie_one_mcp` | 403, same error | Same |
| `POST /api/2.0/mcp/functions/system/ai` (legacy managed MCP) | 200, tools returned | Older managed MCP path works |
| `GET /api/2.0/apps/mcp-fpac-soil` | RUNNING, compute ACTIVE | Our server is healthy |
| Installed `databricks-sdk` | No `w.ai_gateway` attribute | SDK predates Unity Gateway MCP APIs |

**Takeaway:** the MCP side of Unity Gateway does not appear enabled (or granted)
for us as of today. If the expected Monday enablement had happened, we would
expect the built-in `system.ai` MCP services to be listed and callable. A 403
rather than a 404 suggests the feature is deployed but not turned on or not
granted. We could not inspect the account console Previews page or confirm
whether the AI Playground **+ Add tool → MCP Servers** option is present.

## Remaining Questions

### 1. Unity Gateway MCP enablement for AI Playground

We were told features would be enabled by Monday 2026-10-19. Model services
are live, but `system.ai` MCP services return 403 for us (see probe above).

- Is the Unity Gateway preview (including MCP services, not just model
  services) enabled at the account level? If so, why do built-in `system.ai`
  MCPs return `Not authorized to invoke MCP service` for team members?
- Does it require an explicit `EXECUTE` grant on `system.ai` MCP services, and
  who can grant it?
- When will the AI Playground **Tools → MCP Servers** option be available?
  Even scoped enablement for hackathon participants would unblock testing.

### 2. Notebook bearer token for Apps

We know bearer tokens work for programmatic access. From a **serverless
notebook**, can we obtain a valid bearer token to call an Apps-hosted MCP server?
The `databricks-openai` `McpServerToolkit` rejects non-OAuth auth, but raw HTTP
with a bearer token should work if we can get the token. Is there a supported
pattern (e.g., `databricks auth token` equivalent in notebook context, or service
principal M2M)?

### 3. Agent harness for hackathon

Will there be an agent evaluation harness or test framework for the hackathon
where we register our MCP URL and have an agent call our tools? If so, what auth
method does it expect — bearer token, service principal, or OAuth?

### 4. `mcp-` prefix auto-discovery

Does the `mcp-` app name prefix make the server auto-discoverable in AI
Playground once Unity Gateway is enabled, or is a separate registration step
needed? Specifically, will `mcp-fpac-soil` appear under **Tools → MCP Servers**
for users who hold **CAN USE** on the app?

## What we have working

- Databricks App `mcp-fpac-soil` — deployed, RUNNING, health check passes
- App URL: `https://mcp-fpac-soil-7474654188777746.aws.databricksapps.com`
- MCP endpoint: `/mcp` (Streamable HTTP)
- Source: shared prod Git folder on `main`, auto-pulled hourly
- 10 MCP tools, 3 resources, 4 prompts
- Full offline test suite passing
- Bearer token auth confirmed as the programmatic access path
