# Build stage
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first for optimal Docker layer caching
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and complete installation
COPY src/ ./src/
COPY main.py ./
RUN uv sync --frozen --no-dev

# Final runtime stage
FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    MCP_TRANSPORT="sse" \
    MCP_HOST="0.0.0.0" \
    MCP_PORT=8000 \
    NASS_CENSUS_YEAR=2022

# Create non-root user for security compliance
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser && \
    chown -R appuser:appgroup /app

# Copy virtualenv and application from builder
COPY --from=builder --chown=appuser:appgroup /app /app

USER 10001:10001

EXPOSE 8000

ENTRYPOINT ["python", "main.py"]

