import { test, expect } from '@playwright/test';
import { createKeycloakUser, deleteKeycloakUser } from '../helpers/keycloak-admin';
import { createAuthContext } from '../helpers/project-helper';
import { gotoProjectDetail, addUserToProject, createProjectApi, deleteProjectApi, cleanupProjectApi } from '../helpers/project-admin';

const TEST_PROJECT = 'pw-roleproj';
const PI_USER = 'pw-pi-user';
const SCIENTIST_USER = 'pw-scientist-user';

let projectId: string;

// ── test suite ────────────────────────────────────────────────────────────────

test.describe.configure({ mode: 'serial' });

test.describe('Project Management UI — Add user with role', { tag: '@functional' }, () => {
  test.beforeAll(async ({ browser }) => {
    await createKeycloakUser({ username: PI_USER, password: 'pw-test-1234', firstName: 'PI', lastName: 'User', realmRoles: ['user'] });
    await createKeycloakUser({ username: SCIENTIST_USER, password: 'pw-test-1234', firstName: 'Scientist', lastName: 'User', realmRoles: ['user'] });

    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await cleanupProjectApi(page, TEST_PROJECT);
    projectId = await createProjectApi(page, TEST_PROJECT, 'Playwright role-assignment test project');
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await deleteProjectApi(page, projectId);
    await ctx.close();
    await deleteKeycloakUser(PI_USER);
    await deleteKeycloakUser(SCIENTIST_USER);
  });

  test('add a user to the project as principal investigator', async ({ page }) => {
    await gotoProjectDetail(page, TEST_PROJECT);
    await addUserToProject(page, PI_USER, 'principal-investigator');

    const row = page.locator('tbody tr').filter({ hasText: PI_USER }).first();
    await expect(row).toBeVisible({ timeout: 10_000 });
    await expect(row.getByText('principal-investigator')).toBeVisible();
  });

  test('add a user to the project as scientist', async ({ page }) => {
    await gotoProjectDetail(page, TEST_PROJECT);
    await addUserToProject(page, SCIENTIST_USER, 'scientist');

    const row = page.locator('tbody tr').filter({ hasText: SCIENTIST_USER }).first();
    await expect(row).toBeVisible({ timeout: 10_000 });
    await expect(row.getByText('scientist', { exact: true })).toBeVisible();
  });
});
