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
 *
 * Optional:
 *   PLAYWRIGHT_BROWSER         — chromium (default) | firefox | webkit
 *                                Install the binary first: npx playwright install <browser>
 */

// ── Browser ────────────────────────────────────────────────────────────────────
// Defaults to Chromium; override with PLAYWRIGHT_BROWSER=firefox|webkit to test
// against a different engine. Applies to every service suite below.
type BrowserName = 'chromium' | 'firefox' | 'webkit';

const BROWSER_NAME: BrowserName = (() => {
  const b = process.env.PLAYWRIGHT_BROWSER;
  if (b === 'firefox' || b === 'webkit' || b === 'chromium') return b;
  return 'chromium';
})();

const BROWSER_DEVICE: Record<BrowserName, (typeof devices)[string]> = {
  chromium: devices['Desktop Chrome'],
  firefox:  devices['Desktop Firefox'],
  webkit:   devices['Desktop Safari'],
};

// ── Service suites ────────────────────────────────────────────────────────────
// Each entry becomes a named project that depends on auth-setup and runs on a
// single, high-resolution browser window (the UI is designed for desktop use).
const SERVICE_SPECS: Array<{ name: string; testMatch: RegExp }> = [
  { name: 'project-management', testMatch: /project-management-ui\/.*\.spec\.ts/ },
  { name: 'landing-page',       testMatch: /landing-page\/.*\.spec\.ts/ },
  { name: 'workflow-ui',        testMatch: /workflow-ui\/.*\.spec\.ts/ },
  { name: 'system-ui',          testMatch: /system-ui\/.*\.spec\.ts/ },
  { name: 'extensions-ui',      testMatch: /extensions-ui\/.*\.spec\.ts/ },
];

export default defineConfig({
  testDir: './tests',
  timeout: 20_000,
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

    // ── Step 2: service suites ──────────────────────────────────────────────
    // Depends on auth-setup so Playwright runs it automatically when you call
    //   npx playwright test --project <suite-name>
    ...SERVICE_SPECS.map(spec => ({
      name: spec.name,
      testMatch: spec.testMatch,
      dependencies: ['auth-setup'],
      use: {
        ...BROWSER_DEVICE[BROWSER_NAME],
        viewport: { width: 1920, height: 1080 },
        storageState: AUTH_FILE,
      },
    })),
  ],
});
