import { defineConfig, devices } from '@playwright/test';

export const AUTH_FILE = 'playwright/.auth/kaapana.json';

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * Required env vars:
 *   KAAPANA_TEST_INSTANCE_UI   — base URL of the running Kaapana instance
 *                                (default: https://localhost)
 *   KAAPANA_PROJECTS_UI_PATH   — path to project-management UI inside the portal
 *                                (default: /projects-ui)
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // In CI: emit both an HTML report (downloadable) and JUnit XML (shown inline in GitLab).
  // Locally: just the interactive HTML report.
  reporter: process.env.CI
    ? [
        ['html', { open: 'never' }],
        ['junit', { outputFile: 'test-results/junit.xml' }],
      ]
    : [['html']],

  use: {
    baseURL: process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost',
    ignoreHTTPSErrors: true,

    // Keep traces and recordings for every failed test so they can be
    // downloaded from the CI artifact and inspected at trace.playwright.dev.
    trace: 'retain-on-failure',
    video: process.env.CI ? 'retain-on-failure' : 'on',
    screenshot: 'only-on-failure',

    // Slow down every action for manual observation: PLAYWRIGHT_SLOW_MO=500
    launchOptions: {
      slowMo: process.env.PLAYWRIGHT_SLOW_MO ? parseInt(process.env.PLAYWRIGHT_SLOW_MO) : 0,
    },
  },

  projects: [
    // ── Step 1: auth-setup ────────────────────────────────────────────────
    // Logs in with kaapana/admin and writes the browser session to disk.
    // First-login (password change) is handled by the pytest integration test
    // that runs before this suite; the password is already 'admin' here.
    {
      name: 'auth-setup',
      testMatch: /auth\.setup\.ts/,
    },

    // ── Step 2: project-management ────────────────────────────────────────
    // End-to-end tests for /projects-ui. Runs on a single, high-resolution
    // Chrome window (the UI is designed for desktop use, not mobile).
    // Depends on auth-setup so Playwright runs it automatically when you call
    //   npx playwright test --project project-management
    {
      name: 'project-management',
      testMatch: /project-management\.spec\.ts/,
      dependencies: ['auth-setup'],
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
        storageState: AUTH_FILE,
      },
    },

    // ── Generic browser matrix ─────────────────────────────────────────────
    // Runs every other spec file on the three major desktop browsers.
    {
      name: 'chromium',
      testIgnore: [/first-login\.spec\.ts/, /auth\.setup\.ts/, /project-management\.spec\.ts/],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      testIgnore: [/first-login\.spec\.ts/, /auth\.setup\.ts/, /project-management\.spec\.ts/],
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      testIgnore: [/first-login\.spec\.ts/, /auth\.setup\.ts/, /project-management\.spec\.ts/],
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
