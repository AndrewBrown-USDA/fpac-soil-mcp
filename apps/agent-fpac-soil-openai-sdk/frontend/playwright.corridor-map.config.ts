import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/corridor-map',
  use: {
    baseURL: 'http://127.0.0.1:5187',
    headless: true,
    launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader'] },
  },
  webServer: {
    command: 'npm run dev --workspace=@databricks/chatbot-client -- --host 127.0.0.1 --port 5187',
    url: 'http://127.0.0.1:5187/corridor-map-fixture.html',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
