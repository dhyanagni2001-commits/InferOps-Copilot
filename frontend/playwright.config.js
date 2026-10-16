import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  timeout: 30_000,
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure" },
  webServer: [
    {
      command: "../.venv/bin/uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8081",
      url: "http://127.0.0.1:8081/health/live",
      env: { DEMO_MODE: "true", API_BEARER_TOKEN: "dev-token", DOCS_INDEX_PATH: "../data/docs-index.json" },
      reuseExistingServer: !process.env.CI,
    },
    { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: !process.env.CI },
  ],
});
