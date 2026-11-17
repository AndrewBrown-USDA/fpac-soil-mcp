FROM node:22-bookworm-slim

WORKDIR /app

COPY eval/fpac_soil_mcp_harness/package.json eval/fpac_soil_mcp_harness/package-lock.json ./
RUN npm ci --omit=dev

COPY eval/fpac_soil_mcp_harness/server.js ./server.js
COPY eval/fpac_soil_mcp_harness/lib ./lib
COPY eval/fpac_soil_mcp_harness/public ./public
COPY eval/common /common
COPY eval/eval_cases.v1.json ./eval_cases.v1.json

ENV NODE_ENV=production \
    HARNESS_HOST=0.0.0.0 \
    HARNESS_PORT=3030 \
    HARNESS_AUTOCONNECT=true \
    HARNESS_ALLOW_COMMAND_OVERRIDE=false \
    MCP_MODE=http \
    MCP_URL=http://mcp:8000/mcp \
    EVAL_CASES_PATH=/app/eval_cases.v1.json

USER node

EXPOSE 3030

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3030/api/config').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "server.js"]
