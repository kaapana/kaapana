import { test, expect, Browser, type Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Path to the saved Keycloak session — produced by auth.setup.ts
const AUTH_FILE = path.join(__dirname, '..', 'playwright', '.auth', 'kaapana.json');

/**
 * Path to the project-management-ui inside the Kaapana portal.
 * Override with KAAPANA_PROJECTS_UI_PATH if your deployment uses a different prefix.
 */
const PROJECTS_UI = process.env.KAAPANA_PROJECTS_UI_PATH ?? '/projects-ui';

/** Unique name used for the test project across this suite. */
const TEST_PROJECT = 'pw-testproj';

// ── helpers ──────────────────────────────────────────────────────────────────

async function gotoProjectsList(page: Page) {
  await page.goto(PROJECTS_UI);
  await expect(page.getByRole('heading', { name: 'Projects', level: 1 })).toBeVisible({
    timeout: 20_000,
  });
}

/** Cancels the create dialog and discards what the test typed into it. */
async function discardCreateDialog(page: Page) {
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
  await page.getByRole('button', { name: 'Discard changes' }).click();
}

/**
 * Opens a fresh authenticated browser context, navigates to the projects list,
 * and deletes TEST_PROJECT if it is present. Used for pre/post-suite cleanup.
 */
async function cleanupTestProject(browser: Browser): Promise<void> {
  if (!fs.existsSync(AUTH_FILE)) return;
  const ctx = await browser.newContext({ storageState: AUTH_FILE, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  try {
    await page.goto(PROJECTS_UI);
    await page.waitForLoadState('networkidle');

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    if ((await row.count()) === 0) return;

    // If archived, unarchive first so the delete button is reachable
    const unarchive = row.getByRole('button', { name: `Unarchive ${TEST_PROJECT}` });
    if (await unarchive.count() > 0) {
      await unarchive.click();
      await page.waitForLoadState('networkidle');
    }

    await row.getByRole('button', { name: `Delete ${TEST_PROJECT}`, exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: 'Delete project' }).click();
    await page.waitForLoadState('networkidle');
  } finally {
    await ctx.close();
  }
}

// ── test suite ────────────────────────────────────────────────────────────────

// Serial mode: tests share implicit state (the project created in one test is
// used by the next). Running in parallel would cause race conditions.
test.describe.configure({ mode: 'serial' });

test.describe('Project Management UI', () => {
  test.beforeAll(async ({ browser }) => {
    await cleanupTestProject(browser);
  });

  test.afterAll(async ({ browser }) => {
    await cleanupTestProject(browser);
  });

  // ── 1. List page ───────────────────────────────────────────────────────────

  test('projects list page renders', async ({ page }) => {
    await gotoProjectsList(page);

    // The built-in 'admin' project must always exist
    await expect(page.locator('tr').filter({ hasText: /^admin/ }).first()).toBeVisible();
    // Admin user sees the Create new project button
    await expect(page.getByRole('button', { name: 'Create new project' })).toBeVisible();
  });

  // ── 2. Create project ──────────────────────────────────────────────────────

  test('create a new project', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create new project' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await dialog.getByRole('textbox', { name: 'Project name' }).fill(TEST_PROJECT);
    await dialog.getByRole('textbox', { name: 'Description' }).fill('Playwright test project');
    await dialog.getByRole('button', { name: 'Create project' }).click();

    // On success the dialog closes. On a backend error it stays open with the
    // error, but the project may still have been created (e.g. the MinIO/K8s
    // setup timed out but the DB record was committed). Reload to get a fresh
    // table state.
    const failure = dialog.getByText('Project not created');
    await expect(failure.or(page.getByText(`Project "${TEST_PROJECT}" created.`))).toBeVisible({
      timeout: 25_000,
    });
    if (await failure.isVisible()) {
      await page.reload();
      await expect(page.getByRole('heading', { name: 'Projects', level: 1 })).toBeVisible({
        timeout: 20_000,
      });
    }

    await expect(page.locator('tr').filter({ hasText: TEST_PROJECT }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  // ── 3. Name validation ─────────────────────────────────────────────────────

  // The dialog checks the form on submit and stays open while a rule fails.

  test('rejects a project name longer than 13 characters', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create new project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project name' }).fill('toolongname1234');
    await dialog.getByRole('button', { name: 'Create project' }).click();

    await expect(dialog.getByText('Use at most 13 characters')).toBeVisible();

    await discardCreateDialog(page);
  });

  test('rejects uppercase project names', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create new project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project name' }).fill('InvalidName');
    await dialog.getByRole('button', { name: 'Create project' }).click();

    await expect(dialog.getByText('Use lowercase')).toBeVisible();

    await discardCreateDialog(page);
  });

  test('rejects the reserved name "admin"', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create new project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project name' }).fill('admin');
    await dialog.getByRole('textbox', { name: 'Description' }).fill('should be blocked');
    await dialog.getByRole('button', { name: 'Create project' }).click();

    await expect(dialog.getByText('The name "admin" is reserved')).toBeVisible();

    await discardCreateDialog(page);
  });

  // ── 4. View project detail ─────────────────────────────────────────────────

  test('view project detail page', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: 'View' }).click();

    await expect(page.getByRole('heading', { name: TEST_PROJECT, level: 1 })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole('button', { name: 'Projects' })).toBeVisible();
  });

  // ── 5. Edit project ────────────────────────────────────────────────────────

  test('edit project description', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: `Edit ${TEST_PROJECT}` }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const descField = dialog.getByRole('textbox', { name: 'Description' });
    await descField.clear();
    await descField.fill('Updated by Playwright');
    await dialog.getByRole('button', { name: 'Save' }).click();

    await expect(page.getByText('Project updated.')).toBeVisible({ timeout: 10_000 });
  });

  // ── 6. Archive / unarchive ─────────────────────────────────────────────────

  test('archive project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: `Archive ${TEST_PROJECT}`, exact: true }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Archive project' }).click();

    // The 'Archived' chip should appear in the project row
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived')
    ).toBeVisible({ timeout: 10_000 });
  });

  test('unarchive project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: `Unarchive ${TEST_PROJECT}` }).click();

    // The 'Archived' chip should disappear
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived')
    ).not.toBeVisible({ timeout: 10_000 });
  });

  // ── 7. Delete project ──────────────────────────────────────────────────────

  test('delete project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: `Delete ${TEST_PROJECT}`, exact: true }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog.getByText(`Delete "${TEST_PROJECT}"?`)).toBeVisible();
    await dialog.getByRole('button', { name: 'Delete project' }).click();

    // The row must disappear from the table
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT })
    ).not.toBeVisible({ timeout: 10_000 });
  });
});
