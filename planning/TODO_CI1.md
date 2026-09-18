# TODO

## Goal
Add a GitHub Actions CI workflow (`.github/workflows/ci.yml`) on `ubuntu-latest` testing Python versions 3.11 and 3.14 that runs `make all` and `make test-live` on push, pull_request, and workflow_dispatch.

## Tasks

### 1. Workflow Configuration
- [x] Create directory `.github/workflows` and GitHub Actions workflow file `.github/workflows/ci.yml` configured for `push`, `pull_request` (targeting `main`), and `workflow_dispatch` on `ubuntu-latest` with a matrix for Python `3.11` and `3.14`.
- [x] Configure `astral-sh/setup-uv` and Python setup in the workflow steps, then execute `make all` and `make test-live`.

### 2. Validation & Documentation
- [x] Verify workflow YAML syntax and ensure compatibility with Makefile targets.
- [x] Update `README.md` to document the CI workflow status and instructions if applicable.

## Discovered Tasks
- [x] Add `.github/dependabot.yml` copied from `../soilDB/.github/dependabot.yml` for github-actions and uv/pip dependencies.

## Notes
- Triggers: `push` (branches: `[main]`), `pull_request` (branches: `[main]`), and `workflow_dispatch`.
- Matrix: `python-version: ["3.11", "3.14"]`.
- Environment: `ubuntu-latest` using `astral-sh/setup-uv` with uv sync/caching.
- `make all` runs `clean`, `install`, `lint`, `format-check`, and offline `test`.
- `make test-live` runs live USDA SDA tests against the live endpoint.
