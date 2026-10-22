---
id: "0013"
title: "Pin PyPI as the Default uv Index in Every uv Project"
status: "Accepted"
date: 2026-10-22
authors:
  - "Andrew G. Brown"
supersedes: null
superseded_by: null
source_context: "Commits 1e0f2f4, bcf6626 (root); f27eb3b (agent app, PR #35)"
---

# 13. Pin PyPI as the Default uv Index in Every uv Project

## Context and Problem Statement

Development happens on Databricks compute, where a managed user-level uv config
(`~/.config/uv/uv.toml`, regenerated on attach) sets the workspace package
proxy (`package-proxy.host.local`) as the default index. Any `uv lock` run there
records proxy download URLs in `uv.lock`. GitHub Actions cannot resolve that
host, so CI installs fail with DNS errors. This broke the root project first
(fixed by re-locking in `1e0f2f4` and pinning in `bcf6626`) and then the agent
app (fixed in `f27eb3b`).

## Decision Drivers

* Lock files must install anywhere: Databricks compute, GitHub Actions, and
  developer laptops.
* The managed uv config cannot be edited (it is regenerated on attach).
* The fix must survive future re-locks without anyone remembering a flag.

## Considered Options

1. **Project-level `[[tool.uv.index]]` pinning `https://pypi.org/simple/` as
   `default = true` in every uv project's `pyproject.toml`**, then re-lock.
2. **Pass `--default-index` or set `UV_DEFAULT_INDEX` when locking** -- relies on
   every developer and agent remembering it.
3. **Configure CI to reach the proxy** -- not possible from GitHub-hosted runners.

## Decision Outcome

Chosen option: "Project-level PyPI default index in every uv project", because
project config overrides the managed user config, so every `uv lock` produces
portable PyPI URLs.

The block, identical in each project:

```toml
[[tool.uv.index]]
url = "https://pypi.org/simple/"
default = true
```

Applies today to the root `pyproject.toml` and
`apps/agent-fpac-soil-openai-sdk/pyproject.toml`. Any new uv project in the
repository must add the block before its first `uv lock` on Databricks compute.

### Consequences

* **Positive**: lock files are portable; CI installs from public PyPI; re-locking
  on Databricks compute is safe.
* **Negative**: locking on Databricks compute needs outbound access to PyPI
  (currently available); the convention must be repeated per project.

## Validation & Compliance

* Check: `uv.lock` files contain no `package-proxy` URLs.
* Agent app guard test: `tests/test_deploy_config.py::test_lockfile_uses_public_pypi`.
* CI installs: the root `test` job (`make all`) and the `agent-app` job
  (`make app-check`, which installs with `--frozen` from the committed lock).
