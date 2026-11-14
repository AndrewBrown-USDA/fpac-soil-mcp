import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/site-assessment',
  use: {
    baseURL: 'http://127.0.0.1:5182',
    headless: true,
  },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5182',
    url: 'http://127.0.0.1:5182/site-assessment-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
