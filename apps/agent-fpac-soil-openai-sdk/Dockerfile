FROM node:22-bookworm-slim AS node

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

COPY --from=node /usr/local/ /usr/local/
COPY --from=ghcr.io/astral-sh/uv:python3.11-bookworm-slim /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    FPAC_FRONTEND_PREBUILT=1 \
    NODE_ENV=production \
    CHAT_APP_PORT=3000 \
    PORT=8000

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen && \
    npm --prefix frontend ci && \
    npm --prefix frontend run build

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system --gid 10001 appgroup && \
    useradd --system --uid 10001 --gid appgroup --create-home appuser && \
    chown -R appuser:appgroup /app

USER 10001:10001

EXPOSE 3000 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f "http://localhost:${CHAT_APP_PORT:-3000}/ping" || exit 1

ENTRYPOINT ["uv", "run", "--frozen", "start-app"]
CMD ["--port", "8000"]
