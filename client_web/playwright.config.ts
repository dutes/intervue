import { defineConfig, devices } from "@playwright/test";

// E2E runs against the real app: the FastAPI backend serving the built SPA on :8000, driven
// through the keyless "mock" provider so no API key or network is needed. The webServer block
// builds nothing itself — CI builds the frontend first; locally, run `npm run build` once so
// the backend has client_web/dist to serve (see README / the e2e npm script).
export default defineConfig({
    testDir: "./e2e",
    timeout: 90_000,
    expect: { timeout: 15_000 },
    fullyParallel: false,
    workers: 1,
    retries: process.env.CI ? 1 : 0,
    reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
    use: {
        baseURL: "http://localhost:8000",
        trace: "on-first-retry",
    },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
    webServer: {
        // cwd is relative to this config (client_web), so ".." is the repo root where the
        // server package lives and where vendored deps resolve.
        command: "python -m uvicorn server.main:app --host 127.0.0.1 --port 8000",
        cwd: "..",
        url: "http://localhost:8000/health",
        timeout: 120_000,
        reuseExistingServer: !process.env.CI,
    },
});
