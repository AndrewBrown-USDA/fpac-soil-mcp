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

.PHONY: help install sync run run-sse test test-unit test-live test-eval eval lint lint-fix format format-check check clean docker-build docker-run all

help: ## Show this help message with available commands
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Sync dependencies and locked environment via uv
	$(UV) sync

sync: install ## Alias for install

run: ## Run MCP server locally over stdio transport
	$(UV) run fpac-soil-mcp

run-sse: ## Run MCP server locally over SSE network transport
	MCP_TRANSPORT=sse MCP_HOST=$(MCP_HOST) MCP_PORT=$(MCP_PORT) $(UV) run fpac-soil-mcp

test: ## Run unit and mocked test suite (offline)
	$(UV) run pytest -m "not live_network and not agent_eval"

test-unit: test ## Alias for offline test suite

test-live: ## Run live network integration tests (requires network)
	$(UV) run pytest -m live_network

test-eval: ## Run Pi agent evaluation benchmark suite
	$(PYTHON) eval/run_evals.py

eval: test-eval ## Alias for test-eval

lint: ## Run Ruff linter checks
	$(UV) run ruff check .

lint-fix: ## Auto-fix linting issues with Ruff
	$(UV) run ruff check --fix .

format: ## Format codebase using Ruff
	$(UV) run ruff format .

format-check: ## Check code formatting without applying changes
	$(UV) run ruff format --check .

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
