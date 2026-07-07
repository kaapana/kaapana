import { test, expect, type Page } from '@playwright/test';
import { LandingPage } from '../helpers/LandingPage';
import { createKeycloakUser, deleteKeycloakUser, loginAsUser } from '../helpers/keycloak-admin';
import { createAuthContext } from '../helpers/project-helper';
import { createProjectApi, deleteProjectApi, cleanupProjectApi, addUserToProjectApi, gotoProjectDetail, setWorkflowWhitelisted } from '../helpers/project-admin';

const BASE_URL = process.env.KAAPANA_TEST_INSTANCE_UI || 'https://localhost';

const TEST_PROJECT = 'pw-wflist';
const PI_USER = 'pw-wfw-pi';
const SCIENTIST_USER = 'pw-wfw-scientist';
const PASSWORD = 'pw-test-1234';

// New projects are seeded with the *full* default_software.json list already
// whitelisted (see the project-creation route) — restricting access means
// un-whitelisting a DAG, not adding one to an empty list. Both of these are
// in that default set and eligible for the Workflow Execution page's
// kind_of_dags="all" category filter, so they're a valid removed/kept pair.
const REMOVED_DAG = 'send-dicom';
const KEPT_DAG = 'validate-dicoms';

let projectId: string;

/** Opens Workflow Execution's DAG dropdown and returns the visible option names. */
async function listDagDropdownOptions(page: Page): Promise<string[]> {
  const portal = new LandingPage(page);
  await portal.waitForLoad();
  await portal.workflowExecutionLink.click();
  await expect(page).toHaveURL(/\/workflow-execution/, { timeout: 15_000 });

  const dagSelect = page.locator('.v-select').filter({ hasText: /Workflow/i }).first();
  await expect(dagSelect).toBeVisible({ timeout: 15_000 });
  await dagSelect.locator('.v-input__slot').click();
  await page.waitForTimeout(800);

  const options = await page.locator('.v-menu__content:visible .v-list-item').allTextContents();
  return options.map(o => o.trim().toLowerCase()).filter(Boolean);
}

test.describe.configure({ mode: 'serial' });

test.describe('Project Management UI — Restrict access to workflows (whitelist)', () => {
  test.beforeAll(async ({ browser }) => {
    test.setTimeout(60_000);
    await createKeycloakUser({ username: PI_USER, password: PASSWORD, firstName: 'WF', lastName: 'PI', realmRoles: ['user'] });
    await createKeycloakUser({ username: SCIENTIST_USER, password: PASSWORD, firstName: 'WF', lastName: 'Scientist', realmRoles: ['user'] });

    const ctx = await createAuthContext(browser);
    const page = await ctx.newPage();
    await cleanupProjectApi(page, TEST_PROJECT);
    projectId = await createProjectApi(page, TEST_PROJECT, 'Playwright workflow-whitelist test project');
    await addUserToProjectApi(page, projectId, PI_USER, 'principal-investigator');
    await addUserToProjectApi(page, projectId, SCIENTIST_USER, 'scientist');

    await gotoProjectDetail(page, TEST_PROJECT);
    await setWorkflowWhitelisted(page, REMOVED_DAG, false);
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

  test('principal-investigator no longer sees the removed DAG', async ({ browser }) => {
    // Fresh login + project switch + page navigation is heavier than the 20s default.
    test.setTimeout(40_000);
    const page = await loginAsUser(browser, BASE_URL, PI_USER, PASSWORD);
    try {
      const portal = new LandingPage(page);
      await portal.switchProject(TEST_PROJECT);
      const options = await listDagDropdownOptions(page);
      expect(options).not.toContain(REMOVED_DAG);
      expect(options).toContain(KEPT_DAG);
    } finally {
      await page.context().close();
    }
  });

  test('scientist no longer sees the removed DAG', async ({ browser }) => {
    // Fresh login + project switch + page navigation is heavier than the 20s default.
    test.setTimeout(40_000);
    const page = await loginAsUser(browser, BASE_URL, SCIENTIST_USER, PASSWORD);
    try {
      const portal = new LandingPage(page);
      await portal.switchProject(TEST_PROJECT);
      const options = await listDagDropdownOptions(page);
      expect(options).not.toContain(REMOVED_DAG);
      expect(options).toContain(KEPT_DAG);
    } finally {
      await page.context().close();
    }
  });
});
