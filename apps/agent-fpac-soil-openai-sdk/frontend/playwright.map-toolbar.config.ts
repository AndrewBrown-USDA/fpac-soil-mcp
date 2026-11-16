import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/map-toolbar',
  use: { baseURL: 'http://127.0.0.1:5185', headless: true },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5185',
    url: 'http://127.0.0.1:5185/map-toolbar-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
