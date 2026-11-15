import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/chat-export',
  use: { baseURL: 'http://127.0.0.1:5183', headless: true },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5183',
    url: 'http://127.0.0.1:5183/chat-export-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
