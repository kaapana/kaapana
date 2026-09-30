import { defineConfig, devices } from '@playwright/test'

// Port registry for the mock-backed e2e suites (one port per app so suites can
// run in parallel on one machine): portal-ui 4300, views 4301-4309, base-ui 4310.
// base-ui has no app of its own; its suite drives the Storybook stories.
const PORT = 4310

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
    // CI tests a static Storybook build; local runs use the Storybook dev server.
    // --exact-port: without it Storybook silently moves to another free port.
    command: process.env.CI
      ? `npm run build:storybook -- --test --quiet && npx vite preview --outDir storybook-static --port ${PORT} --strictPort`
      : `npx storybook dev -p ${PORT} --ci --exact-port`,
    url: `http://localhost:${PORT}/iframe.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
})
