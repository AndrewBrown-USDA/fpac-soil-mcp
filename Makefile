# FPAC Soil MCP Server — Development Makefile
# USDA NRCS Soil Data Access (SDA) Farmland Classification & FPPA Screening MCP Server

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Overridable variables
UV          ?= uv
PYTHON      ?= python
MCP_HOST    ?= 127.0.0.1
MCP_PORT    ?= 8000
IMAGE_NAME  ?= fpac-soil-mcp
EVAL_ARTIFACT_ROOT ?= ../fpac-soil-mcp-eval-artifacts

# Databricks agent app (separate uv project; root Ruff/pytest skip apps/)
APP_DIR     ?= apps/agent-fpac-soil-openai-sdk
APP_PYTHON  ?= 3.11
# Files this repo owns in the app; the remaining template runtime files are not linted.
APP_LINT_PATHS := $(addprefix $(APP_DIR)/,agent_server/agent.py agent_server/config.py agent_server/history.py tests)

.PHONY: help install sync requirements run run-sse run-http test test-unit test-live test-eval eval eval-databricks lint lint-fix format format-check check clean docker-build docker-run all app-test app-lint app-frontend-check app-check

help: ## Show this help message with available commands
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Sync dependencies and locked environment via uv
	$(UV) sync --dev

sync: install ## Alias for install

requirements: ## Regenerate pinned requirements.txt from pyproject.toml
	$(UV) pip compile pyproject.toml -o requirements.txt

run: ## Run MCP server locally over stdio transport
	$(UV) run fpac-soil-mcp

run-sse: ## Run MCP server locally over SSE network transport
	MCP_TRANSPORT=sse MCP_HOST=$(MCP_HOST) MCP_PORT=$(MCP_PORT) $(UV) run fpac-soil-mcp

run-http: ## Run MCP server locally over Streamable HTTP transport
	MCP_TRANSPORT=http MCP_HOST=$(MCP_HOST) MCP_PORT=$(MCP_PORT) $(UV) run fpac-soil-mcp

test: ## Run unit and mocked test suite (offline)
	$(UV) run --group dev pytest -m "not live_network and not agent_eval"

test-unit: test ## Alias for offline test suite

app-test: ## Run the agent app's offline tests (uses the committed uv.lock)
	cd $(APP_DIR) && $(UV) run --frozen --python $(APP_PYTHON) pytest tests -q

app-lint: ## Ruff check + format check on the agent app files this repo owns
	$(UV) run ruff check $(APP_LINT_PATHS)
	$(UV) run ruff format --check $(APP_LINT_PATHS)

app-frontend-check: ## Install and validate the vendored agent app frontend
	cd $(APP_DIR)/frontend && npm ci && npm run lint && npm run typecheck && npm run build

app-check: app-lint app-test app-frontend-check ## Run agent app and frontend validation

test-live: ## Run live network integration tests (requires network)
	$(UV) run --group dev pytest -m live_network

test-eval: ## Run Pi agent evaluation benchmark suite
	$(PYTHON) eval/pi/run_evals.py --capture-artifacts --artifact-root "$(EVAL_ARTIFACT_ROOT)"

eval: test-eval ## Alias for test-eval

eval-databricks: ## Run T1 Databricks-native MLflow evaluation (requires eval-databricks group)
	$(UV) run --group eval-databricks python eval/databricks/run_mlflow_eval.py $(ARGS)

lint: ## Run Ruff linter checks
	$(UV) tool run ruff check .

lint-fix: ## Auto-fix linting issues with Ruff
	$(UV) tool run ruff check --fix .

format: ## Format codebase using Ruff
	$(UV) tool run ruff format .

format-check: ## Check code formatting without applying changes
	$(UV) tool run ruff format --check .

check: lint format-check test ## Run full validation suite (lint, format-check, mocked tests)

clean: ## Remove build artifacts, bytecode, and test caches
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker-build: ## Build the production Docker container image
	docker build -t $(IMAGE_NAME) .

docker-run: ## Run Docker container with stdio transport
	docker run -i --rm -e MCP_TRANSPORT=stdio $(IMAGE_NAME)

all: clean install check ## Clean, install dependencies, and run full test/lint pipeline
	@echo "All checks passed!"
