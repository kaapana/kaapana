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
  await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
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
    if (await row.locator('button:has(.mdi-archive-arrow-up)').count() > 0) {
      await row.locator('button:has(.mdi-archive-arrow-up)').click();
      await page.waitForLoadState('networkidle');
    }

    await row.locator('button:has(.mdi-trash-can)').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();
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

    await expect(page.getByText('Available Projects')).toBeVisible();
    // The built-in 'admin' project must always exist
    await expect(page.locator('tr').filter({ hasText: /^admin/ }).first()).toBeVisible();
    // Admin user sees the Create New Project button
    await expect(page.getByRole('button', { name: 'Create New Project' })).toBeVisible();
  });

  // ── 2. Create project ──────────────────────────────────────────────────────

  test('create a new project', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create New Project' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await dialog.getByRole('textbox', { name: 'Project Name' }).fill(TEST_PROJECT);
    await dialog.getByRole('textbox', { name: 'Description' }).fill('Playwright test project');
    await dialog.getByRole('button', { name: 'Create' }).click();

    // Wait for the dialog to close (happens for both success and API error).
    await expect(dialog).not.toBeVisible({ timeout: 5_000 });

    // When the backend returns an error the table is not auto-refreshed, but
    // the project may still have been created (e.g. the MinIO/K8s setup timed
    // out but the DB record was committed). Reload to get a fresh table state.
    if (await page.getByText('Project could not be created').isVisible()) {
      await page.reload();
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
    }

    await expect(page.locator('tr').filter({ hasText: TEST_PROJECT }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  // ── 3. Name validation ─────────────────────────────────────────────────────

  test('rejects a project name longer than 13 characters', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create New Project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('toolongname1234');

    await expect(dialog.getByText('Max 13 characters')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();

    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  test('rejects uppercase project names', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create New Project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('InvalidName');

    await expect(dialog.getByText('Only lowercase characters are supported')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();

    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  test('rejects the reserved name "admin"', async ({ page }) => {
    await gotoProjectsList(page);
    await page.getByRole('button', { name: 'Create New Project' }).click();

    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('admin');
    await dialog.getByRole('textbox', { name: 'Description' }).fill('should be blocked');

    await expect(dialog.getByText('Name "admin" is reserved')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();

    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  // ── 4. View project detail ─────────────────────────────────────────────────

  test('view project detail page', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.getByRole('button', { name: 'View' }).click();

    // Project detail page shows the project name in the header heading.
    // exact:true avoids matching the "Selected project: ..." snackbar that also
    // contains the name as a substring.
    await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: 'Projects' })).toBeVisible();
  });

  // ── 5. Edit project ────────────────────────────────────────────────────────

  test('edit project description', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-pencil)').click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const descField = dialog.getByRole('textbox', { name: 'Description' });
    await descField.clear();
    await descField.fill('Updated by Playwright');
    await dialog.getByRole('button', { name: 'Save' }).click();

    await expect(page.getByText('Project updated successfully')).toBeVisible({ timeout: 10_000 });
  });

  // ── 6. Archive / unarchive ─────────────────────────────────────────────────

  test('archive project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-archive-arrow-down)').click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Archive' }).click();

    // The 'Archived' chip should appear in the project row
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived')
    ).toBeVisible({ timeout: 10_000 });
  });

  test('unarchive project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-archive-arrow-up)').click();

    // The 'Archived' chip should disappear
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived')
    ).not.toBeVisible({ timeout: 10_000 });
  });

  // ── 7. Delete project ──────────────────────────────────────────────────────

  test('delete project', async ({ page }) => {
    await gotoProjectsList(page);

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-trash-can)').click();

    const dialog = page.getByRole('dialog');
    await expect(dialog.getByText('Are you sure you want to delete')).toBeVisible();
    await dialog.getByRole('button', { name: 'Delete' }).click();

    // The row must disappear from the table
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT })
    ).not.toBeVisible({ timeout: 10_000 });
  });
});
