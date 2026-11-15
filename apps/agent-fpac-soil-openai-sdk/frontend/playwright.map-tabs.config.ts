import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/map-tabs',
  use: { baseURL: 'http://127.0.0.1:5184', headless: true },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5184',
    url: 'http://127.0.0.1:5184/map-tabs-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
