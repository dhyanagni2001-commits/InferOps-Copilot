import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  use: { baseURL: "http://127.0.0.1:5173" },
  webServer: [
    { command: "../.venv/bin/uvicorn app.main:app --app-dir ../backend --port 8081", port: 8081, reuseExistingServer: true },
    { command: "npm run dev -- --host 127.0.0.1", port: 5173, reuseExistingServer: true },
  ],
});
