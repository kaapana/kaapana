import { test, expect } from '@playwright/test';
import { createKeycloakUser, deleteKeycloakUser, loginAsUser } from '../helpers/keycloak-admin';
import { createAuthContext } from '../helpers/project-helper';
import { gotoProjectDetail, changeUserRole, createProjectApi, deleteProjectApi, cleanupProjectApi, addUserToProjectApi } from '../helpers/project-admin';

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';

const TEST_PROJECT = 'pw-roleswap';
const TEST_USER = 'pw-roleswap-user';
const PASSWORD = 'pw-test-1234';

let projectId: string;

/** Opens the user's own row in Project Users and reports whether they have manage-user rights. */
async function hasManageUsersRights(page: import('@playwright/test').Page, username: string): Promise<boolean> {
  const usersHeader = page.locator('h5').filter({ hasText: 'Project Users' }).first();
  await usersHeader.click();
  await page.waitForTimeout(300);

  const addUserBtn = page.getByRole('button', { name: 'Add User', exact: true });
  const addUserVisible = await addUserBtn.isVisible({ timeout: 5_000 }).catch(() => false);

  const row = page.locator('tbody tr').filter({ hasText: username }).first();
  await expect(row).toBeVisible({ timeout: 10_000 });
  const editEnabled = await row.locator('button:has(.mdi-link-edit)').isEnabled();

  return addUserVisible && editEnabled;
}

test.describe.configure({ mode: 'serial' });

test.describe("Project Management UI — Change a user's role", { tag: '@functional' }, () => {
  test.beforeAll(async ({ browser }) => {
    // Keycloak user creation + project setup is several sequential API round
    // trips — heavier than the 20s default (see app-whitelist.spec.ts).
    test.setTimeout(40_000);
    await createKeycloakUser({
      username: TEST_USER,
      password: PASSWORD,
      firstName: 'Role',
      lastName: 'Swap',
      realmRoles: ['user'],
    });

    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await cleanupProjectApi(page, TEST_PROJECT);
    projectId = await createProjectApi(page, TEST_PROJECT, 'Playwright role-change test project');
    await addUserToProjectApi(page, projectId, TEST_USER, 'scientist');
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await deleteProjectApi(page, projectId);
    await ctx.close();
    await deleteKeycloakUser(TEST_USER);
  });

  test('as scientist: no user-management rights (Add User hidden, own row actions disabled)', async ({ browser }) => {
    const page = await loginAsUser(browser, BASE_URL, TEST_USER, PASSWORD);
    try {
      await gotoProjectDetail(page, TEST_PROJECT);
      expect(await hasManageUsersRights(page, TEST_USER)).toBe(false);
    } finally {
      await page.context().close();
    }
  });

  test('admin promotes the user to principal-investigator', async ({ page }) => {
    await gotoProjectDetail(page, TEST_PROJECT);
    await changeUserRole(page, TEST_USER, 'principal-investigator');

    const row = page.locator('tbody tr').filter({ hasText: TEST_USER }).first();
    await expect(row.getByText('principal-investigator')).toBeVisible({ timeout: 10_000 });
  });

  test('as principal-investigator: gains user-management rights immediately', async ({ browser }) => {
    const page = await loginAsUser(browser, BASE_URL, TEST_USER, PASSWORD);
    try {
      await gotoProjectDetail(page, TEST_PROJECT);
      expect(await hasManageUsersRights(page, TEST_USER)).toBe(true);
    } finally {
      await page.context().close();
    }
  });

  test('admin demotes the user back to scientist', async ({ page }) => {
    await gotoProjectDetail(page, TEST_PROJECT);
    await changeUserRole(page, TEST_USER, 'scientist');

    const row = page.locator('tbody tr').filter({ hasText: TEST_USER }).first();
    await expect(row.getByText('scientist', { exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('as scientist again: user-management rights are gone', async ({ browser }) => {
    const page = await loginAsUser(browser, BASE_URL, TEST_USER, PASSWORD);
    try {
      await gotoProjectDetail(page, TEST_PROJECT);
      expect(await hasManageUsersRights(page, TEST_USER)).toBe(false);
    } finally {
      await page.context().close();
    }
  });
});
