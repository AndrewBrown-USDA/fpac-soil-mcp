import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/map-legend',
  use: { baseURL: 'http://127.0.0.1:5186', headless: true },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5186',
    url: 'http://127.0.0.1:5186/map-legend-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
