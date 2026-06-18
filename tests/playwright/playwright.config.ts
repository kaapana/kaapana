import { defineConfig, devices } from '@playwright/test';

export const AUTH_FILE = 'helpers/.auth/kaapana.json';
export const PI_AUTH_FILE = 'helpers/.auth/pi-user.json';
export const SCIENTIST_AUTH_FILE = 'helpers/.auth/scientist-user.json';

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * Required env vars:
 *   KAAPANA_TEST_INSTANCE_UI        — base URL of the running Kaapana instance
 *                                     (default: https://localhost)
 *   KAAPANA_PROJECTS_UI_PATH        — path to project-management UI inside the portal
 *                                     (default: /projects-ui)
 *   KAAPANA_KEYCLOAK_ADMIN_USER     — Keycloak master-realm admin username
 *                                     (default: admin)
 *   KAAPANA_KEYCLOAK_ADMIN_PASSWORD — Keycloak master-realm admin password
 *                                     (default: Kaapana2020)
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
    // Logs in as kaapana/admin and writes the session to helpers/.auth/kaapana.json.
    // Lives in helpers/auth.ts alongside the login() helper function.
    {
      name: 'auth-setup',
      testDir: './helpers',
      testMatch: /auth\.setup\.ts/,
    },

    // ── Step 2: users-setup ───────────────────────────────────────────────
    // Creates two test users in Keycloak (PI and scientist) and saves their
    // auth states to helpers/.auth/. Runs after auth-setup.
    {
      name: 'users-setup',
      testMatch: /users\.setup\.ts/,
      dependencies: ['auth-setup'],
    },

    // ── Step 3: project-management ────────────────────────────────────────
    // End-to-end tests for /projects-ui on a full-HD Chrome window.
    // Depends on auth-setup (admin session) and users-setup (test users).
    {
      name: 'project-management',
      testMatch: /project-management\.spec\.ts/,
      dependencies: ['auth-setup', 'users-setup'],
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
      testIgnore: [
        /first-login\.spec\.ts/,
        /users\.setup\.ts/,
        /project-management\.spec\.ts/,
      ],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      testIgnore: [
        /first-login\.spec\.ts/,
        /users\.setup\.ts/,
        /project-management\.spec\.ts/,
      ],
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      testIgnore: [
        /first-login\.spec\.ts/,
        /users\.setup\.ts/,
        /project-management\.spec\.ts/,
      ],
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
