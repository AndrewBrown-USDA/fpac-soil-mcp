import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/aoi-state',
  use: {
    baseURL: 'http://127.0.0.1:5188',
    headless: true,
    launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader'] },
  },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5188',
    url: 'http://127.0.0.1:5188/aoi-state-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
