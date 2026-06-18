import { test, expect, Browser, type Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { getKeycloakAdminToken, deleteKeycloakUser } from '../helpers/keycloak';
import {
  PI_USER, PI_PASSWORD, PI_AUTH_FILE,
  SCIENTIST_USER, SCIENTIST_PASSWORD, SCIENTIST_AUTH_FILE,
} from '../helpers/users';

// ── Constants ─────────────────────────────────────────────────────────────────

const AUTH_FILE = path.join(__dirname, '..', 'helpers', '.auth', 'kaapana.json');
const PROJECTS_UI = process.env.KAAPANA_PROJECTS_UI_PATH ?? '/projects-ui';
const TEST_PROJECT = 'pw-testproj';

// Workflow whitelisted during the test — set by one test, read by later ones.
let whitelistedDag = '';

// ── Helpers ───────────────────────────────────────────────────────────────────

async function gotoProjectsList(page: Page) {
  await page.goto(PROJECTS_UI);
  await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
}

async function gotoProjectDetail(page: Page) {
  await gotoProjectsList(page);
  const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
  await row.getByRole('button', { name: 'View' }).click();
  await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });
}

/** Expands a section by its header title text if it is not already expanded. */
async function expandSection(page: Page, sectionTitle: string) {
  const header = page.getByText(sectionTitle, { exact: true });
  // The SectionHeader component emits 'toggle' — find the nearest clickable ancestor
  const sectionRow = header.locator('..').locator('..');
  const content = page.locator(`text=${sectionTitle}`).locator('xpath=ancestor::*[contains(@class,"v-col")]').first();
  // Try clicking the header to expand; if already open the click is a no-op
  await header.click().catch(() => {});
}

async function openNewProjectDialog(page: Page) {
  await gotoProjectsList(page);
  await page.getByRole('button', { name: 'Create New Project' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
}

async function cleanupTestProject(browser: Browser): Promise<void> {
  if (!fs.existsSync(AUTH_FILE)) return;
  const ctx = await browser.newContext({ storageState: AUTH_FILE, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  try {
    await page.goto(PROJECTS_UI);
    await page.waitForLoadState('networkidle');

    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    if ((await row.count()) === 0) return;

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

async function cleanupTestUsers(browser: Browser): Promise<void> {
  const ctx = await browser.newContext({ storageState: AUTH_FILE, ignoreHTTPSErrors: true });
  const { request } = ctx;
  try {
    const token = await getKeycloakAdminToken(request);
    for (const username of [PI_USER, SCIENTIST_USER]) {
      const resp = await request.get(
        `${process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost'}/auth/admin/realms/kaapana/users?username=${encodeURIComponent(username)}&exact=true`,
        { headers: { Authorization: `Bearer ${token}` }, ignoreHTTPSErrors: true },
      );
      const users = await resp.json() as Array<{ id: string }>;
      if (users.length > 0) {
        await deleteKeycloakUser(request, token, users[0].id);
      }
    }
  } finally {
    await ctx.close();
  }
}

// ── Suite ─────────────────────────────────────────────────────────────────────

test.describe.configure({ mode: 'serial' });

test.describe('Project Management UI', () => {
  test.beforeAll(async ({ browser }) => {
    await cleanupTestProject(browser);
  });

  test.afterAll(async ({ browser }) => {
    await cleanupTestProject(browser);
    await cleanupTestUsers(browser);
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 1. PROJECT LIST
  // ─────────────────────────────────────────────────────────────────────────

  test('projects list page renders', async ({ page }) => {
    await gotoProjectsList(page);
    await expect(page.getByText('Available Projects')).toBeVisible();
    await expect(page.locator('tr').filter({ hasText: /^admin/ }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create New Project' })).toBeVisible();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 2. CREATE PROJECT
  // ─────────────────────────────────────────────────────────────────────────

  test('create a new project', async ({ page }) => {
    await openNewProjectDialog(page);
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill(TEST_PROJECT);
    await dialog.getByRole('textbox', { name: 'Description' }).fill('Playwright test project');
    await dialog.getByRole('button', { name: 'Create' }).click();

    await expect(dialog).not.toBeVisible({ timeout: 5_000 });

    if (await page.getByText('Project could not be created').isVisible()) {
      await page.reload();
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
    }

    await expect(page.locator('tr').filter({ hasText: TEST_PROJECT }).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 3. NAME VALIDATION
  // ─────────────────────────────────────────────────────────────────────────

  test('rejects a project name longer than 13 characters', async ({ page }) => {
    await openNewProjectDialog(page);
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('toolongname1234');
    await expect(dialog.getByText('Max 13 characters')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  test('rejects uppercase project names', async ({ page }) => {
    await openNewProjectDialog(page);
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('InvalidName');
    await expect(dialog.getByText('Only lowercase characters are supported')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  test('rejects the reserved name "admin"', async ({ page }) => {
    await openNewProjectDialog(page);
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('textbox', { name: 'Project Name' }).fill('admin');
    await dialog.getByRole('textbox', { name: 'Description' }).fill('should be blocked');
    await expect(dialog.getByText('Name "admin" is reserved')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Create' })).toBeDisabled();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 4. PROJECT DETAIL
  // ─────────────────────────────────────────────────────────────────────────

  test('view project detail page', async ({ page }) => {
    await gotoProjectDetail(page);
    await expect(page.getByRole('button', { name: 'Projects' })).toBeVisible();
    // Both main sections should be present on the page
    await expect(page.getByText('Project Users', { exact: true })).toBeVisible();
    await expect(page.getByText('Project Workflows', { exact: true })).toBeVisible();
  });

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

  // ─────────────────────────────────────────────────────────────────────────
  // 5. WORKFLOW WHITELIST MANAGEMENT (admin)
  // ─────────────────────────────────────────────────────────────────────────

  test('admin: expand Project Workflows section and table loads', async ({ page }) => {
    await gotoProjectDetail(page);

    // Expand the section by clicking its header
    await page.getByText('Project Workflows', { exact: true }).click();

    // Wait for the table (or empty state) to appear
    const table = page.locator('.v-data-table');
    const emptyState = page.getByText('No workflows available');
    await expect(table.or(emptyState)).toBeVisible({ timeout: 15_000 });
  });

  test('admin: whitelist a workflow', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Workflows', { exact: true }).click();

    // Wait for rows to appear
    const table = page.locator('.v-data-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // Find the first row whose checkbox is unchecked
    const rows = table.locator('tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });

    let targetRow = null;
    const rowCount = await rows.count();
    for (let i = 0; i < rowCount; i++) {
      const row = rows.nth(i);
      const checkbox = row.locator('.v-checkbox-btn input[type="checkbox"]');
      if ((await checkbox.count()) > 0 && !(await checkbox.isChecked())) {
        // Capture the DAG name from the monospace span
        const dagName = await row.locator('span[style*="monospace"]').first().textContent();
        if (dagName) {
          whitelistedDag = dagName.trim();
          targetRow = row;
          break;
        }
      }
    }

    if (!targetRow) {
      test.skip(true, 'All workflows are already whitelisted or no workflows available');
      return;
    }

    // Check the checkbox (toggle to enabled)
    await targetRow.locator('.v-checkbox-btn').click();

    // "Save Changes" button should become enabled
    await expect(page.getByRole('button', { name: 'Save Changes' })).toBeEnabled({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Save Changes' }).click();

    // Success snackbar
    await expect(page.getByText(/workflow.*updated/i)).toBeVisible({ timeout: 10_000 });
  });

  test('admin: whitelisted workflow persists after page reload', async ({ page }) => {
    if (!whitelistedDag) {
      test.skip(true, 'No DAG was whitelisted in previous test');
      return;
    }

    await gotoProjectDetail(page);
    await page.getByText('Project Workflows', { exact: true }).click();

    const table = page.locator('.v-data-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // Find the row for our DAG and verify it's checked
    const dagRow = table.locator('tbody tr').filter({ hasText: whitelistedDag });
    await expect(dagRow).toBeVisible({ timeout: 10_000 });
    const checkbox = dagRow.locator('.v-checkbox-btn input[type="checkbox"]');
    await expect(checkbox).toBeChecked();
  });

  test('admin: remove workflow from whitelist', async ({ page }) => {
    if (!whitelistedDag) {
      test.skip(true, 'No DAG was whitelisted in previous test');
      return;
    }

    await gotoProjectDetail(page);
    await page.getByText('Project Workflows', { exact: true }).click();

    const table = page.locator('.v-data-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    const dagRow = table.locator('tbody tr').filter({ hasText: whitelistedDag });
    await expect(dagRow).toBeVisible();

    // Uncheck it
    await dagRow.locator('.v-checkbox-btn').click();
    await expect(page.getByRole('button', { name: 'Save Changes' })).toBeEnabled();
    await page.getByRole('button', { name: 'Save Changes' }).click();
    await expect(page.getByText(/workflow.*updated/i)).toBeVisible({ timeout: 10_000 });

    // Re-whitelist so subsequent tests still have a whitelisted DAG to verify
    await dagRow.locator('.v-checkbox-btn').click();
    await expect(page.getByRole('button', { name: 'Save Changes' })).toBeEnabled();
    await page.getByRole('button', { name: 'Save Changes' }).click();
    await expect(page.getByText(/workflow.*updated/i)).toBeVisible({ timeout: 10_000 });
  });

  test('admin: Discard button reverts pending changes', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Workflows', { exact: true }).click();

    const table = page.locator('.v-data-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    const rows = table.locator('tbody tr');
    const firstRow = rows.first();
    await expect(firstRow).toBeVisible();

    const checkbox = firstRow.locator('.v-checkbox-btn input[type="checkbox"]');
    const wasBefore = await checkbox.isChecked();

    // Stage a change
    await firstRow.locator('.v-checkbox-btn').click();
    await expect(page.getByRole('button', { name: 'Discard' })).toBeVisible();

    // Discard
    await page.getByRole('button', { name: 'Discard' }).click();
    await expect(page.getByRole('button', { name: 'Discard' })).not.toBeVisible({ timeout: 3_000 });

    // Checkbox is back to original state
    const isNow = await checkbox.isChecked();
    expect(isNow).toBe(wasBefore);
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 6. USER MANAGEMENT (admin adds PI and scientist)
  // ─────────────────────────────────────────────────────────────────────────

  test('admin: add PI user to project', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Users', { exact: true }).click();

    await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Add User' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Search for PI user
    await dialog.getByPlaceholder('Type to search...').fill(PI_USER);
    await page.waitForTimeout(500); // debounce
    const userOption = page.getByText(PI_USER, { exact: false }).first();
    await expect(userOption).toBeVisible({ timeout: 10_000 });
    await userOption.click();

    // Select principal-investigator role card
    await dialog.getByText('principal-investigator', { exact: false }).first().click();

    // Submit
    await dialog.getByRole('button', { name: /Add User/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });

    // Verify user appears in the table
    await expect(page.locator('td').filter({ hasText: PI_USER })).toBeVisible({ timeout: 10_000 });
  });

  test('admin: add scientist user to project', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Users', { exact: true }).click();

    await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Add User' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    await dialog.getByPlaceholder('Type to search...').fill(SCIENTIST_USER);
    await page.waitForTimeout(500);
    const userOption = page.getByText(SCIENTIST_USER, { exact: false }).first();
    await expect(userOption).toBeVisible({ timeout: 10_000 });
    await userOption.click();

    // Select scientist role card
    await dialog.getByText('scientist', { exact: false }).first().click();

    await dialog.getByRole('button', { name: /Add User/ }).click();
    await expect(dialog).not.toBeVisible({ timeout: 10_000 });

    await expect(page.locator('td').filter({ hasText: SCIENTIST_USER })).toBeVisible({ timeout: 10_000 });
  });

  test('admin: both test users appear in project users list', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Users', { exact: true }).click();

    await expect(page.locator('td').filter({ hasText: PI_USER })).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('td').filter({ hasText: SCIENTIST_USER })).toBeVisible({ timeout: 10_000 });
  });

  test('admin: user roles show correctly in users table', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Users', { exact: true }).click();

    const piRow = page.locator('tr').filter({ hasText: PI_USER });
    const sciRow = page.locator('tr').filter({ hasText: SCIENTIST_USER });

    await expect(piRow).toBeVisible({ timeout: 10_000 });
    await expect(sciRow).toBeVisible({ timeout: 10_000 });

    await expect(piRow.getByText('principal-investigator')).toBeVisible();
    await expect(sciRow.getByText('scientist')).toBeVisible();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 7. ROLE-BASED ACCESS — PRINCIPAL INVESTIGATOR
  // ─────────────────────────────────────────────────────────────────────────

  test('PI user: can see "Save Changes" button on workflow whitelist', async ({ browser }) => {
    if (!fs.existsSync(PI_AUTH_FILE)) {
      test.skip(true, 'PI user auth state not found — run users.setup.ts first');
      return;
    }
    const ctx = await browser.newContext({ storageState: PI_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });

      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await expect(row).toBeVisible({ timeout: 10_000 });
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Workflows', { exact: true }).click();
      await expect(page.locator('.v-data-table').or(page.getByText('No workflows available'))).toBeVisible({
        timeout: 15_000,
      });

      // PI has manage_workflow_whitelist → Save Changes is rendered (may be disabled but visible)
      await expect(page.getByRole('button', { name: 'Save Changes' })).toBeVisible({ timeout: 5_000 });
    } finally {
      await ctx.close();
    }
  });

  test('PI user: can see "Add User" button in Project Users', async ({ browser }) => {
    if (!fs.existsSync(PI_AUTH_FILE)) {
      test.skip(true, 'PI user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: PI_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Users', { exact: true }).click();
      await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible({ timeout: 10_000 });
    } finally {
      await ctx.close();
    }
  });

  test('PI user: can edit workflow whitelist (toggle and save)', async ({ browser }) => {
    if (!fs.existsSync(PI_AUTH_FILE)) {
      test.skip(true, 'PI user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: PI_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Workflows', { exact: true }).click();
      const table = page.locator('.v-data-table');
      await expect(table).toBeVisible({ timeout: 15_000 });

      // Checkboxes must NOT be disabled for PI user
      const firstCheckbox = table.locator('tbody tr').first().locator('.v-checkbox-btn input[type="checkbox"]');
      await expect(firstCheckbox).not.toBeDisabled({ timeout: 5_000 });

      // Stage a toggle (do not save — just verify UI responds)
      await table.locator('tbody tr').first().locator('.v-checkbox-btn').click();
      await expect(page.getByRole('button', { name: 'Save Changes' })).toBeEnabled();
      // Discard so we don't leave the project in an altered state
      await page.getByRole('button', { name: 'Discard' }).click();
    } finally {
      await ctx.close();
    }
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 8. ROLE-BASED ACCESS — SCIENTIST
  // ─────────────────────────────────────────────────────────────────────────

  test('scientist: cannot see "Save Changes" button on workflow whitelist', async ({ browser }) => {
    if (!fs.existsSync(SCIENTIST_AUTH_FILE)) {
      test.skip(true, 'Scientist user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: SCIENTIST_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Workflows', { exact: true }).click();
      await expect(page.locator('.v-data-table').or(page.getByText('No workflows available'))).toBeVisible({
        timeout: 15_000,
      });

      // Scientist lacks manage_workflow_whitelist → button is absent
      await expect(page.getByRole('button', { name: 'Save Changes' })).not.toBeVisible({ timeout: 3_000 });
    } finally {
      await ctx.close();
    }
  });

  test('scientist: workflow checkboxes are disabled (read-only)', async ({ browser }) => {
    if (!fs.existsSync(SCIENTIST_AUTH_FILE)) {
      test.skip(true, 'Scientist user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: SCIENTIST_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Workflows', { exact: true }).click();
      const table = page.locator('.v-data-table');
      await expect(table).toBeVisible({ timeout: 15_000 });

      const firstCheckbox = table.locator('tbody tr').first().locator('.v-checkbox-btn input[type="checkbox"]');
      await expect(firstCheckbox).toBeDisabled({ timeout: 5_000 });
    } finally {
      await ctx.close();
    }
  });

  test('scientist: cannot see "Add User" button in Project Users', async ({ browser }) => {
    if (!fs.existsSync(SCIENTIST_AUTH_FILE)) {
      test.skip(true, 'Scientist user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: SCIENTIST_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Users', { exact: true }).click();
      await expect(page.getByRole('button', { name: 'Add User' })).not.toBeVisible({ timeout: 5_000 });
    } finally {
      await ctx.close();
    }
  });

  test('scientist: Edit/Remove user buttons are disabled', async ({ browser }) => {
    if (!fs.existsSync(SCIENTIST_AUTH_FILE)) {
      test.skip(true, 'Scientist user auth state not found');
      return;
    }
    const ctx = await browser.newContext({ storageState: SCIENTIST_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      await page.getByText('Project Users', { exact: true }).click();
      await page.waitForLoadState('networkidle');

      const usersTable = page.locator('.v-data-table').last();
      if (await usersTable.locator('tbody tr').count() > 0) {
        const firstRow = usersTable.locator('tbody tr').first();
        await expect(firstRow.locator('button[icon="mdi-link-edit"]').or(firstRow.locator('button:has(.mdi-link-edit)'))).toBeDisabled({ timeout: 5_000 });
        await expect(firstRow.locator('button[icon="mdi-trash-can"]').or(firstRow.locator('button:has(.mdi-trash-can)'))).toBeDisabled({ timeout: 5_000 });
      }
    } finally {
      await ctx.close();
    }
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 9. WORKFLOW FILTERING ON WORKFLOW EXECUTION PAGE
  // ─────────────────────────────────────────────────────────────────────────

  test('whitelisted workflow appears in workflow execution page for scientist', async ({ browser }) => {
    if (!whitelistedDag) {
      test.skip(true, 'No DAG was whitelisted in earlier test');
      return;
    }
    if (!fs.existsSync(SCIENTIST_AUTH_FILE)) {
      test.skip(true, 'Scientist user auth state not found');
      return;
    }

    const ctx = await browser.newContext({ storageState: SCIENTIST_AUTH_FILE, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    try {
      // First, navigate to the projects page and select the test project so
      // the portal sets it as the active project context.
      await page.goto(PROJECTS_UI);
      await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
      const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
      await row.getByRole('button', { name: 'View' }).click();
      await expect(page.getByText(TEST_PROJECT, { exact: true })).toBeVisible({ timeout: 10_000 });

      // Navigate to workflow execution
      await page.goto('/workflow-execution');
      await page.waitForLoadState('networkidle');

      // The DAG selector should be present
      const dagSelector = page.locator('[data-testid="dag-selector"]')
        .or(page.getByLabel(/workflow|dag/i).first())
        .or(page.locator('.v-autocomplete, .v-select').first());
      await expect(dagSelector).toBeVisible({ timeout: 15_000 });

      // Open the dropdown and search for the whitelisted DAG
      await dagSelector.click();
      const input = dagSelector.locator('input').first();
      if (await input.count() > 0) {
        await input.fill(whitelistedDag);
        await page.waitForTimeout(500);
      }
      await expect(page.getByText(whitelistedDag, { exact: false })).toBeVisible({ timeout: 5_000 });
    } finally {
      await ctx.close();
    }
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 10. CLEAN UP USERS FROM PROJECT BEFORE DELETING IT
  // ─────────────────────────────────────────────────────────────────────────

  test('admin: remove PI and scientist users from project', async ({ page }) => {
    await gotoProjectDetail(page);
    await page.getByText('Project Users', { exact: true }).click();
    await page.waitForLoadState('networkidle');

    for (const username of [PI_USER, SCIENTIST_USER]) {
      const userRow = page.locator('tr').filter({ hasText: username });
      if ((await userRow.count()) === 0) continue;
      await userRow.locator('button:has(.mdi-trash-can)').click();
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await dialog.getByRole('button', { name: 'Remove' }).click();
      await expect(dialog).not.toBeVisible({ timeout: 10_000 });
      await page.waitForTimeout(300);
    }
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 11. ARCHIVE / UNARCHIVE
  // ─────────────────────────────────────────────────────────────────────────

  test('archive project', async ({ page }) => {
    await gotoProjectsList(page);
    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-archive-arrow-down)').click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Archive' }).click();
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived'),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('archived project: edit and delete buttons are hidden/disabled', async ({ page }) => {
    await gotoProjectsList(page);
    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await expect(row.getByText('Archived')).toBeVisible();
    // Pencil (edit) and delete buttons should not exist or be disabled for archived projects
    await expect(row.locator('button:has(.mdi-pencil)')).not.toBeVisible({ timeout: 3_000 });
    await expect(row.locator('button:has(.mdi-trash-can)')).not.toBeVisible({ timeout: 3_000 });
  });

  test('unarchive project', async ({ page }) => {
    await gotoProjectsList(page);
    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-archive-arrow-up)').click();
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }).first().getByText('Archived'),
    ).not.toBeVisible({ timeout: 10_000 });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // 12. DELETE
  // ─────────────────────────────────────────────────────────────────────────

  test('delete project', async ({ page }) => {
    await gotoProjectsList(page);
    const row = page.locator('tr').filter({ hasText: TEST_PROJECT }).first();
    await row.locator('button:has(.mdi-trash-can)').click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByText('Are you sure you want to delete')).toBeVisible();
    await dialog.getByRole('button', { name: 'Delete' }).click();
    await expect(
      page.locator('tr').filter({ hasText: TEST_PROJECT }),
    ).not.toBeVisible({ timeout: 10_000 });
  });
});
