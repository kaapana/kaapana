import { defineConfig, devices } from '@playwright/test'

// Port registry for the mock-backed e2e suites (one port per app so suites can
// run in parallel on one machine): portal-ui 4300, views 4301-4309.
// extensions-ui = 4303.
const PORT = 4303

// This view is served under a non-root base (`/extensions-ui/`), so both the
// webServer readiness check and page.goto() must target that path, not `/`.
const BASE_PATH = '/extensions-ui/'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [['list'], ['junit', { outputFile: 'test-results/junit.xml' }]]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // CI tests the production bundle (run `npm run build` first); local runs
    // use the dev server so tests iterate without rebuilding.
    command: process.env.CI
      ? `npm run preview -- --port ${PORT} --strictPort`
      : `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}${BASE_PATH}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
