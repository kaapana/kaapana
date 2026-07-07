import { test, expect, type Browser } from '@playwright/test';
import { createKeycloakUser, deleteKeycloakUser, loginAsUser } from '../helpers/keycloak-admin';
import { createAuthContext } from '../helpers/project-helper';
import { LandingPage } from '../helpers/LandingPage';
import { gotoProjectDetail, removeUserFromProject, createProjectApi, deleteProjectApi, cleanupProjectApi, addUserToProjectApi } from '../helpers/project-admin';

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';

const TEST_PROJECT = 'pw-removeuser';
const TEST_USER = 'pw-removeuser-user';
const PASSWORD = 'pw-test-1234';

let projectId: string;

test.describe.configure({ mode: 'serial' });

test.describe('Project Management UI — Remove a user from a project', () => {
  test.beforeAll(async ({ browser }) => {
    await createKeycloakUser({
      username: TEST_USER,
      password: PASSWORD,
      firstName: 'Remove',
      lastName: 'User',
      realmRoles: ['user'],
    });

    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await cleanupProjectApi(page, TEST_PROJECT);
    projectId = await createProjectApi(page, TEST_PROJECT, 'Playwright remove-user test project');
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

  test('admin removes the user from the project', async ({ page }) => {
    await gotoProjectDetail(page, TEST_PROJECT);
    // removeUserFromProject already asserts the row disappears from the table.
    await removeUserFromProject(page, TEST_USER);
  });

  test('the removed user no longer sees the project in their project selector', async ({ browser }) => {
    const page = await loginAsUser(browser, BASE_URL, TEST_USER, PASSWORD);
    try {
      const portal = new LandingPage(page);
      await portal.waitForLoad();
      await portal.projectSelector.click();
      await expect(
        page.locator('.v-list-item').filter({ hasText: TEST_PROJECT })
      ).not.toBeVisible({ timeout: 5_000 });
    } finally {
      await page.context().close();
    }
  });
});
