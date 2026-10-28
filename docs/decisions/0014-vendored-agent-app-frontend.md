# ADR 0014: Vendor and pin the agent app frontend

## Status

Accepted

## Decision

The agent app owns a copy of the Databricks `e2e-chatbot-app-next` frontend
under `apps/agent-fpac-soil-openai-sdk/frontend`. The copy is pinned to
upstream tree `c7e05c0787909bc6e0b79adf2f162fd0bc2a8edd` and carries a
committed npm lockfile. Runtime startup uses this directory and never clones
from GitHub.

Frontend updates are explicit repository changes, reviewed against the
upstream template, and validated with `npm ci`, lint, typecheck, and build.
The launcher continues to provide `API_PROXY`, preserve the existing port and
readiness behavior, and support `--no-ui`.

## Scope boundary

This decision vendors the existing chat UI only. Map rendering, AOI drawing,
map routes, and result-envelope changes are deferred to later plan work.
