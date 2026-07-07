/**
 * Project-detail-page helpers for Playwright tests: navigating to a project,
 * adding/removing/re-roling users, and toggling the workflow/application
 * whitelists. All assume an authenticated admin session (the actions here
 * are gated behind admin-only or PI-only rights in the real UI).
 */
import { type Page, expect } from '@playwright/test';

const PROJECTS_UI = process.env.KAAPANA_PROJECTS_UI_PATH ?? '/projects-ui';

export type ProjectRole = 'principal-investigator' | 'scientist';

// ── Fast API-based fixture setup ──────────────────────────────────────────────
// Use these when a project/user/role-mapping is just fixture setup for a test
// that's actually about something else (e.g. the workflow-whitelist tests
// don't care HOW the user got added). Reserve the slower UI-driven
// addUserToProject/removeUserFromProject/changeUserRole below for tests that
// are specifically exercising those dialogs.

/** Creates a project directly via the API. Returns its id. */
export async function createProjectApi(page: Page, name: string, description: string): Promise<string> {
  // external_id intentionally omitted — the UI's create form leaves it blank
  // by default, and the detail page only renders its caption (duplicating
  // the name's exact text) when external_id is set.
  const res = await page.request.post('/aii/projects', {
    data: { name, description },
  });
  if (!res.ok()) throw new Error(`Create project "${name}" failed: ${res.status()} ${await res.text()}`);
  const project = await res.json();
  return project.id;
}

/** Deletes a project directly via the API. Best-effort — used for cleanup. */
export async function deleteProjectApi(page: Page, projectId: string): Promise<void> {
  await page.request.delete(`/aii/projects/${projectId}`).catch(() => {});
}

/** Deletes a project by name if it exists — idempotent pre/post-test cleanup, in case a prior run left it behind. */
export async function cleanupProjectApi(page: Page, name: string): Promise<void> {
  const res = await page.request.get(`/aii/projects/${encodeURIComponent(name)}`).catch(() => null);
  if (!res || !res.ok()) return;
  const project = await res.json();
  if (project?.id) await deleteProjectApi(page, project.id);
}

/** Looks up a Keycloak user's id by username via the API (used to build role-mapping calls). */
async function getUserId(page: Page, username: string): Promise<string> {
  const res = await page.request.get('/aii/users');
  if (!res.ok()) throw new Error(`GET /aii/users failed: ${res.status()}`);
  const users = await res.json();
  const user = users.find((u: { username: string }) => u.username === username);
  if (!user) throw new Error(`User "${username}" not found via /aii/users`);
  return user.id;
}

/** Adds a user to a project with a role directly via the API — fast fixture setup. */
export async function addUserToProjectApi(page: Page, projectId: string, username: string, role: ProjectRole): Promise<void> {
  const userId = await getUserId(page, username);
  const res = await page.request.post(`/aii/projects/${projectId}/role/${role}/user/${userId}`);
  if (!res.ok()) throw new Error(`Add user "${username}" to project failed: ${res.status()} ${await res.text()}`);
}

// ── UI-driven actions ──────────────────────────────────────────────────────────
// Use these when the test is actually exercising the corresponding dialog.

/** Navigates to the projects list and opens a project's detail page. */
export async function gotoProjectDetail(page: Page, projectName: string) {
  await page.goto(PROJECTS_UI);
  await expect(page.getByText('Available Projects')).toBeVisible({ timeout: 20_000 });
  const row = page.locator('tr').filter({ hasText: projectName }).first();
  await row.getByRole('button', { name: 'View' }).click();
  await expect(page.getByText(projectName, { exact: true })).toBeVisible({ timeout: 10_000 });
}

/** Expands a collapsible detail-page section by its title (Project Users, Project Workflows, ...). */
async function expandSection(page: Page, title: string) {
  const header = page.locator('h5').filter({ hasText: title }).first();
  await header.click();
  await page.waitForTimeout(300);
}

/**
 * Adds a user to the currently-open project with a given role, via the real
 * "Add User" dialog. Assumes `gotoProjectDetail` has already run.
 */
export async function addUserToProject(page: Page, username: string, role: ProjectRole) {
  await expandSection(page, 'Project Users');

  // The empty-state panel also renders a button whose label contains "Add
  // User" as a substring ("Add user to project \"...\""), so match exactly.
  const addUserBtn = page.getByRole('button', { name: 'Add User', exact: true });
  await expect(addUserBtn).toBeVisible({ timeout: 10_000 });
  await addUserBtn.click();

  const dialog = page.getByRole('dialog').filter({ hasText: 'Add Users to Project' });
  await expect(dialog).toBeVisible({ timeout: 5_000 });

  const search = dialog.getByPlaceholder('Type to search...');
  await search.click();
  await search.fill(username);
  await page.locator('.v-list-item').filter({ hasText: username }).first().click();

  await dialog.locator('.v-item-group .v-card').filter({ hasText: role }).first().click();
  await dialog.getByRole('button', { name: /^Add User(s)?$/ }).click();
  await expect(dialog).not.toBeVisible({ timeout: 10_000 });
}

/**
 * Changes an existing project member's role via the edit-role dialog.
 * Assumes `gotoProjectDetail` has already run and the user is already a member.
 */
export async function changeUserRole(page: Page, username: string, newRole: ProjectRole) {
  await expandSection(page, 'Project Users');

  const row = page.locator('tbody tr').filter({ hasText: username }).first();
  await expect(row).toBeVisible({ timeout: 10_000 });
  await row.locator('button:has(.mdi-link-edit)').click();

  const dialog = page.getByRole('dialog').filter({ hasText: `Change Role: @${username}` });
  await expect(dialog).toBeVisible({ timeout: 5_000 });

  await dialog.locator('.v-item-group .v-card').filter({ hasText: newRole }).first().click();
  await dialog.getByRole('button', { name: 'Save Changes' }).click();
  await expect(dialog).not.toBeVisible({ timeout: 10_000 });
}

/**
 * Removes a user from the currently-open project.
 * Assumes `gotoProjectDetail` has already run.
 */
export async function removeUserFromProject(page: Page, username: string) {
  await expandSection(page, 'Project Users');

  const row = page.locator('tbody tr').filter({ hasText: username }).first();
  await expect(row).toBeVisible({ timeout: 10_000 });
  await row.locator('button:has(.mdi-trash-can)').click();

  const dialog = page.getByRole('dialog').filter({ hasText: 'Remove user from project?' });
  await expect(dialog).toBeVisible({ timeout: 5_000 });
  await dialog.getByRole('button', { name: 'Remove' }).click();
  await expect(dialog).not.toBeVisible({ timeout: 10_000 });
  await expect(row).not.toBeVisible({ timeout: 10_000 });
}

/**
 * Sets whether one DAG is whitelisted in the currently-open project (searches
 * for it, so pagination/row-count never matters). New projects are seeded
 * with the *full* default_software.json list already whitelisted — so
 * restricting access means un-whitelisting (allowed=false) specific DAGs,
 * not adding one to an empty list.
 * Assumes `gotoProjectDetail` has already run.
 */
export async function setWorkflowWhitelisted(page: Page, dagName: string, allowed: boolean) {
  await expandSection(page, 'Project Workflows');

  const search = page.getByPlaceholder('Search workflows...');
  await search.fill(dagName);
  const row = page.locator('tbody tr').filter({ hasText: dagName }).first();
  await expect(row).toBeVisible({ timeout: 10_000 });

  const checkbox = row.getByRole('checkbox');
  if ((await checkbox.isChecked()) !== allowed) {
    await checkbox.click();
    // Multiinstallable Applications has its own (currently-disabled)
    // "Save Changes" button elsewhere on the same page — only ours, just
    // enabled by the checkbox click above, should match.
    await page.locator('button:not(.v-btn--disabled)').filter({ hasText: 'Save Changes' }).click();
    await expect(page.getByText(/workflow.*updated/i)).toBeVisible({ timeout: 10_000 });
  }
  await search.fill('');
}

/**
 * Whitelists the first available multiinstallable application in the
 * currently-open project. Returns its display name — the only identifier
 * visible in the DOM — so callers can re-locate the same row by text in a
 * different user's session.
 * Assumes `gotoProjectDetail` has already run.
 */
export async function whitelistFirstApplication(page: Page): Promise<string> {
  await expandSection(page, 'Multiinstallable Applications');

  const table = page.locator('table').filter({ has: page.getByText('Allowed') });
  const firstRow = table.locator('tbody tr').first();
  await expect(firstRow).toBeVisible({ timeout: 10_000 });
  const displayName = (await firstRow.locator('td').nth(1).innerText()).trim();

  const checkbox = firstRow.getByRole('checkbox').last();
  if (!(await checkbox.isChecked())) {
    await checkbox.click();
    // Project Workflows has its own (currently-disabled) "Save Changes"
    // button elsewhere on the same page — only ours, just enabled by the
    // checkbox click above, should match.
    await page.locator('button:not(.v-btn--disabled)').filter({ hasText: 'Save Changes' }).click();
    await expect(page.getByText(/whitelist saved successfully/i)).toBeVisible({ timeout: 10_000 });
  }

  return displayName;
}
